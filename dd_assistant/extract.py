"""Layer 1b — read the company's own financial statements (no template needed).

Upload the financial data room as it comes from the company and the agent maps each line
to the standard model:
  - Excel: a dictionary of Portuguese and English terms recognises each line ("Vendas e
    serviços prestados", "Revenue" and "Turnover" are all revenue). The figures are read
    straight from the cells and every line keeps its cell reference as the source. Free,
    instant and fully auditable.
  - PDF: Claude reads the statements (vision) and returns each figure exactly as printed,
    with its page. The code, not the AI, converts units and signs; the consistency rules
    (R12–R17) and the review table then check what was read.
"""
from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import BinaryIO, Literal

import anthropic
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from pydantic import BaseModel

from .input_loader import KEY_DOCUMENTS, CompanyData, Named, load_input


class ExtractionError(Exception):
    """The file could not be read as financial statements."""


def _norm(text) -> str:
    """Lower case, no accents, punctuation as spaces: '(Ganhos)/perdas' -> 'ganhos perdas'."""
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9&%]+", " ", t)).strip()


@dataclass(frozen=True)
class Field:
    key: str
    label: str              # English name in the review table
    statement: str          # pl, bs or cf
    synonyms: tuple[str, ...]
    sign: int = 0           # -1: negative in the model (costs and payments), whatever the file shows
    zero_if_missing: bool = False


def _f(key, label, statement, synonyms, sign=0, zero=False) -> Field:
    return Field(key, label, statement, tuple(_norm(s) for s in synonyms), sign, zero)


FIELDS = [
    # income statement
    _f("vendas", "Revenue", "pl", ["vendas e servicos prestados", "volume de negocios", "vendas", "revenue",
                                   "turnover", "net sales", "sales"]),
    _f("cmv", "Cost of goods sold", "pl", ["custo das mercadorias vendidas e das materias consumidas",
                                           "custo das mercadorias vendidas", "cmvmc", "cmv", "cost of goods sold",
                                           "cost of sales", "cogs"], -1),
    _f("fse", "External supplies and services", "pl", ["fornecimentos e servicos externos", "fse",
                                                        "external supplies and services", "external services"], -1),
    _f("pess", "Staff costs", "pl", ["gastos com o pessoal", "gastos com pessoal", "custos com o pessoal",
                                     "custos com pessoal", "staff costs", "personnel costs", "employee costs",
                                     "employee benefits expense"], -1),
    _f("imp", "Impairment of receivables", "pl", ["imparidade de dividas a receber", "imparidades de dividas a receber",
                                                  "imparidade de clientes", "impairment of trade receivables",
                                                  "impairment of receivables", "expected credit losses",
                                                  "bad debt expense"], -1),
    _f("orend", "Other income", "pl", ["outros rendimentos e ganhos", "outros rendimentos", "other operating income",
                                       "other income"]),
    _f("ogast", "Other expenses", "pl", ["outros gastos e perdas", "outros gastos", "other operating expenses",
                                         "other expenses"], -1),
    _f("da", "Depreciation and amortisation", "pl", ["gastos de depreciacao e de amortizacao",
                                                     "depreciacoes e amortizacoes", "depreciacao e amortizacao",
                                                     "depreciation and amortisation", "depreciation and amortization",
                                                     "depreciation"], -1),
    _f("juros", "Interest expense", "pl", ["juros e gastos similares suportados", "juros e gastos similares",
                                           "juros suportados", "interest expense", "finance costs",
                                           "financial expenses"], -1),
    _f("irc", "Income tax", "pl", ["imposto sobre o rendimento do periodo", "imposto sobre o rendimento", "irc",
                                   "income tax expense", "income tax", "tax expense"], -1),
    _f("rl_dre", "Net income", "pl", ["resultado liquido do periodo", "resultado liquido do exercicio",
                                      "resultado liquido", "net income", "net profit", "profit for the year",
                                      "profit for the period"]),
    # balance sheet
    _f("aft", "Property, plant and equipment", "bs", ["ativos fixos tangiveis", "activos fixos tangiveis",
                                                      "property plant and equipment", "tangible fixed assets",
                                                      "fixed assets"]),
    _f("oanc", "Other non-current assets", "bs", ["outros ativos nao correntes", "other non current assets"], zero=True),
    _f("inv", "Inventories", "bs", ["inventarios", "existencias", "inventories", "inventory", "stocks"]),
    _f("cli", "Trade receivables", "bs", ["clientes", "contas a receber de clientes", "trade receivables",
                                          "accounts receivable", "trade debtors"]),
    _f("oac", "Other current assets", "bs", ["outros ativos correntes", "other current assets"]),
    _f("caixa", "Cash and cash equivalents", "bs", ["caixa e depositos bancarios", "caixa e equivalentes de caixa",
                                                    "cash and cash equivalents", "cash at bank", "cash"]),
    _f("cp", "Total equity", "bs", ["total do capital proprio", "capital proprio", "total equity",
                                    "shareholders equity", "equity"]),
    _f("rl_bs", "Net income (balance sheet)", "bs", ["resultado liquido do periodo", "resultado liquido do exercicio",
                                                     "resultado liquido", "net income", "profit for the year"]),
    _f("fin_lp", "Non-current borrowings", "bs", ["financiamentos obtidos nao corrente",
                                                  "financiamentos obtidos nao correntes", "non current borrowings",
                                                  "long term borrowings", "long term debt"]),
    _f("opnc", "Other non-current liabilities", "bs", ["outros passivos nao correntes",
                                                       "other non current liabilities"], zero=True),
    _f("forn", "Trade payables", "bs", ["fornecedores", "trade payables", "accounts payable", "trade creditors"]),
    _f("fin_cp", "Current borrowings", "bs", ["financiamentos obtidos corrente", "financiamentos obtidos correntes",
                                              "current borrowings", "short term borrowings", "short term debt"]),
    _f("opc", "Other current liabilities", "bs", ["outros passivos correntes", "other current liabilities"]),
    # cash flow statement
    _f("rl_dfc", "Net income (cash flow)", "cf", ["resultado liquido do periodo", "resultado liquido", "net income",
                                                  "profit for the year"]),
    _f("ganho_alien", "(Gains)/losses on disposals", "cf", ["ganhos perdas na alienacao", "perdas ganhos na alienacao",
                                                            "ganhos na alienacao", "gain loss on disposal",
                                                            "loss gain on disposal", "gain on disposal",
                                                            "profit on disposal"]),
    _f("d_cli", "Change in trade receivables", "cf", ["variacao de clientes", "variacao das contas a receber",
                                                      "change in trade receivables", "change in receivables",
                                                      "increase decrease in trade receivables",
                                                      "decrease increase in trade receivables"]),
    _f("d_inv", "Change in inventories", "cf", ["variacao de inventarios", "variacao de existencias",
                                                "change in inventories", "increase decrease in inventories",
                                                "decrease increase in inventories"]),
    _f("d_forn", "Change in trade payables", "cf", ["variacao de fornecedores", "change in trade payables",
                                                    "change in payables", "increase decrease in trade payables"]),
    _f("d_oac", "Change in other current assets", "cf", ["variacao de outros ativos correntes",
                                                         "change in other current assets"]),
    _f("d_opc", "Change in other current liabilities", "cf", ["variacao de outros passivos correntes",
                                                              "change in other current liabilities"]),
    _f("cgo", "Cash generated from operations", "cf", ["caixa gerada pelas operacoes", "cash generated from operations"]),
    _f("fco", "Net cash from operating activities", "cf", ["fluxo de caixa das atividades operacionais",
                                                           "fluxos de caixa das atividades operacionais",
                                                           "net cash from operating activities",
                                                           "net cash generated from operating activities",
                                                           "cash flow from operating activities", "operating cash flow"]),
    _f("capex", "Capital expenditure", "cf", ["pagamentos de ativos fixos tangiveis",
                                              "pagamentos respeitantes a ativos fixos tangiveis",
                                              "pagamentos de ativos fixos", "capital expenditure",
                                              "purchase of property plant and equipment",
                                              "purchases of property plant and equipment", "capex"], -1),
    _f("alien", "Proceeds from asset disposals", "cf", ["recebimentos da alienacao de ativos fixos",
                                                        "recebimentos de ativos fixos", "proceeds from disposal",
                                                        "proceeds from sale of property plant and equipment"]),
    _f("cx_ini", "Cash at beginning of period", "cf", ["caixa no inicio do periodo",
                                                       "caixa e equivalentes no inicio do periodo",
                                                       "cash and cash equivalents at beginning of", "cash at beginning of",
                                                       "opening cash"]),
    _f("cx_fim", "Cash at end of period", "cf", ["caixa no fim do periodo", "caixa e equivalentes no fim do periodo",
                                                 "cash and cash equivalents at end of", "cash at end of",
                                                 "closing cash"]),
]
FIELD_BY_KEY = {f.key: f for f in FIELDS}
STATEMENTS = {"pl": "Income statement", "bs": "Balance sheet", "cf": "Cash flow statement"}

# Sheet type from its name (or title), checked in this order.
SHEET_TYPES = [
    ("customers", ["vendas por cliente", "sales by customer", "revenue by customer", "customers", "clientes"]),
    ("adjustments", ["ebitda ajustado", "adjusted ebitda", "normalised ebitda", "normalized ebitda", "ajustamentos"]),
    ("debt", ["divida", "debt", "financiamentos", "borrowings", "facilities", "loans"]),
    ("cf", ["dfc", "fluxos de caixa", "fluxo de caixa", "cash flow"]),
    ("bs", ["balanco", "balance sheet", "posicao financeira", "financial position"]),
    ("pl", ["dre", "demonstracao de resultados", "income statement", "profit and loss", "p&l", "p l"]),
]
NOT_ADJUSTMENTS = ("vendas", "revenue", "sales", "volume de negocios", "ebitda", "total", "margem", "margin")
OTHER_CUSTOMERS = ("outros", "other", "others", "remaining", "restantes", "demais")


@dataclass
class Extraction:
    """What the agent read: the standard model plus everything needed to review it."""
    data: CompanyData
    company: str
    method: str                                  # how the figures were read
    items: list[dict] = field(default_factory=list)   # review table: one row per standard line
    missing: list[str] = field(default_factory=list)  # standard lines not found
    source_text: str = ""                        # full text of the data room, for the AI memo


# ---------------------------------------------------------------- Excel helpers
def _as_year(value) -> int | None:
    """Year in a column header: 2023, '2023', 'FY2023', 'FY23', '2023A', '31/12/2023' or a date."""
    if isinstance(value, (datetime, date)):
        return value.year
    if isinstance(value, (int, float)) and float(value).is_integer() and 1990 <= value <= 2100:
        return int(value)
    if not isinstance(value, str) or "%" in value:
        return None
    t = value.strip().lower()
    m = (re.fullmatch(r"(?:fy\s*)?(\d{4})\s*[aeb]?", t) or re.fullmatch(r"\d{1,2}[/.-]\d{1,2}[/.-](\d{4})", t))
    if m:
        y = int(m.group(1))
        return y if 1990 <= y <= 2100 else None
    m = re.fullmatch(r"fy\s*'?(\d{2})", t)
    return 2000 + int(m.group(1)) if m else None


def _year_header(ws) -> tuple[int | None, dict[int, int]]:
    """Header row and {column number: year}: the first row with at least two year headers."""
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 25)):
        cols = {c.column: y for c in row if (y := _as_year(c.value))}
        if len(cols) >= 2:
            return row[0].row, cols
    return None, {}


def _num(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):   # "(1,234)" or "1 234" written as text
        t = value.strip().replace(" ", "").replace(" ", "")
        neg = t.startswith("(") and t.endswith(")")
        t = t.strip("()").replace(",", "")
        if re.fullmatch(r"-?\d+(\.\d+)?", t):
            return -float(t) if neg else float(t)
    return None


@dataclass
class _Row:
    sheet: str
    row: int
    label: str
    norm: str
    values: dict[int, float | None]
    source: str


def _rows(ws, header: int, cols: dict[int, int]) -> list[_Row]:
    """Rows below the header that have a text label and at least one number."""
    first, last = min(cols), max(cols)
    out = []
    for cells in ws.iter_rows(min_row=header + 1, max_row=ws.max_row):
        label = next((c.value for c in cells if c.column < first and isinstance(c.value, str) and c.value.strip()), None)
        if label is None:
            continue
        values = {cols[c.column]: _num(c.value) for c in cells if c.column in cols}
        if all(v is None for v in values.values()):
            continue
        r = cells[0].row
        source = f"{ws.title}!{get_column_letter(first)}{r}:{get_column_letter(last)}{r}"
        out.append(_Row(ws.title, r, label.strip(), _norm(label), values, source))
    return out


def _sheet_type(ws) -> str | None:
    names = [_norm(ws.title), _norm(ws["A1"].value or "")]
    for kind, hints in SHEET_TYPES:
        for name in names:
            if any(re.search(rf"(^| ){re.escape(h)}($| )", name) for h in hints):
                return kind
    return None


def _match(rows: list[_Row], f: Field, used: set) -> _Row | None:
    """First exact match, then the first row whose label starts with a synonym."""
    for exact in (True, False):
        for syn in f.synonyms:
            for r in rows:
                if (r.sheet, r.row) in used:
                    continue
                if r.norm == syn if exact else r.norm.startswith(syn + " "):
                    return r
    return None


def _signed(values: dict[int, float | None], sign: int) -> dict[int, float | None]:
    """Costs and payments are negative in the model, whether the file shows them as negative or not."""
    if sign < 0 and sum(v for v in values.values() if v) > 0:
        return {y: (None if v is None else -v) for y, v in values.items()}
    return dict(values)


def _company(wb, fallback: str) -> str:
    title = wb.worksheets[0]["A1"].value
    if isinstance(title, str) and title.strip():
        return re.split(r"\s+[—–-]\s+|:", title.strip())[0].strip()
    return fallback


def _covenant(wb, debt_sheet) -> tuple[float | None, str]:
    """Maximum net debt / EBITDA written in the debt schedule (e.g. '≤ 3,0x')."""
    sheets = [debt_sheet] if debt_sheet is not None else []
    for ws in sheets + [s for s in wb.worksheets if s is not debt_sheet]:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and "ebitda" in c.value.lower():
                    m = re.search(r"(\d+(?:[.,]\d+)?)\s*x\b", c.value)
                    if m:
                        return float(m.group(1).replace(",", ".")), f"{ws.title}!{c.coordinate}"
    return None, ""


def _debt_schedule(ws) -> tuple[float | None, float | None, str, str]:
    """Total and current portion from the debt schedule's total row, at the latest date."""
    total_col = header = None
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 15)):
        years, current_col = {}, None
        for c in row:
            n = _norm(c.value or "")
            if not n:
                continue
            if re.match(r"(corrente|current|curto prazo|short term|due within)", n):
                current_col = c.column
            elif (m := re.search(r"(20\d{2})", n)):
                years[c.column] = int(m.group(1))
        if current_col and years:
            total_col, header = max(years, key=years.get), row[0].row
            break
    if not header:
        return None, None, "", ""
    for cells in ws.iter_rows(min_row=header + 1, max_row=ws.max_row):
        if _norm(cells[0].value or "").startswith("total"):
            r = cells[0].row
            tot, cur = _num(ws.cell(r, total_col).value), _num(ws.cell(r, current_col).value)
            return (tot, cur, f"{ws.title}!{get_column_letter(total_col)}{r}",
                    f"{ws.title}!{get_column_letter(current_col)}{r}")
    return None, None, "", ""


def data_room_text(path: str | BinaryIO) -> str:
    """Every sheet of an Excel data room as text, with each cell reference (e.g. B5: 18400)."""
    from .report import fmt_value
    wb = load_workbook(path, data_only=True)
    out = []
    for ws in wb.worksheets:
        out += ["", f"### Sheet '{ws.title}'"]
        for row in ws.iter_rows():
            cells = [f"{c.coordinate}: {fmt_value(c.value)}" for c in row if c.value not in (None, "")]
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out)


# ---------------------------------------------------------------- Excel
def extract_excel(file: str | BinaryIO, name: str = "") -> Extraction:
    """Map the company's own Excel financial statements to the standard model."""
    wb = load_workbook(file, data_only=True)
    sheets = {}   # type -> list of (worksheet, header row, year columns)
    for ws in wb.worksheets:
        header, cols = _year_header(ws)
        kind = _sheet_type(ws)
        if kind:
            sheets.setdefault(kind, []).append((ws, header, cols))
        elif cols:
            sheets.setdefault("other", []).append((ws, header, cols))

    lines, sources, found_as, used = {}, {}, {}, set()
    for st in STATEMENTS:
        candidates = [s for s in sheets.get(st, []) if s[2]] or sheets.get("other", [])
        rows = [r for ws, header, cols in candidates for r in _rows(ws, header, cols)]
        for f in (f for f in FIELDS if f.statement == st):
            r = _match(rows, f, used)
            if r:
                used.add((r.sheet, r.row))
                lines[f.key], sources[f.key], found_as[f.key] = _signed(r.values, f.sign), r.source, r.label
    if "vendas" not in lines:
        raise ExtractionError("No revenue line found. Is this a financial statements file (P&L, balance sheet, "
                              "cash flow)?")

    pl_years = sorted(y for y, v in lines["vendas"].items() if v is not None)
    bs_years = sorted({y for k in ("cli", "cp", "caixa") for y, v in lines.get(k, {}).items() if v is not None})
    years = sorted(set(pl_years) | set(bs_years))
    latest = pl_years[-1]
    for f in FIELDS:
        if f.key not in lines and f.zero_if_missing:
            lines[f.key] = {y: 0.0 for y in bs_years}
            sources[f.key], found_as[f.key] = "Not in data room (0)", "—"

    data = CompanyData(years=years, lines=lines, sources=sources)

    for ws, header, cols in sheets.get("customers", []):
        if not cols:
            continue
        for r in _rows(ws, header, cols):
            if r.norm.startswith("total"):
                continue
            if r.norm.startswith(OTHER_CUSTOMERS):
                data.other_clients = r.values
            else:
                data.clients.append(Named(r.label, r.values))
                data.clients_source = data.clients_source or r.source
        break
    for ws, header, cols in sheets.get("adjustments", []):
        if not cols:
            continue
        for r in _rows(ws, header, cols):
            if not r.norm.startswith(NOT_ADJUSTMENTS):
                data.adjustments.append(Named(r.label, r.values))
                data.adjustments_source = data.adjustments_source or r.source
        break

    debt_ws = sheets["debt"][0][0] if sheets.get("debt") else None
    if debt_ws is not None:
        tot, cur, s_tot, s_cur = _debt_schedule(debt_ws)
        if tot is not None:
            lines["map_tot"], sources["map_tot"], found_as["map_tot"] = {latest: tot}, s_tot, "Total"
            lines["map_cur"], sources["map_cur"], found_as["map_cur"] = {latest: cur}, s_cur, "Total, current"
    cov, s_cov = _covenant(wb, debt_ws)
    if cov is not None:
        lines["cov_lim"], sources["cov_lim"], found_as["cov_lim"] = {latest: cov}, s_cov, f"{cov:g}x"

    sheet_names = " | ".join(_norm(ws.title) for ws in wb.worksheets)
    ageing = lambda *words: bool(re.search(r"aging|ageing|antiguidade", sheet_names)) and any(w in sheet_names for w in words)
    received = {
        "Income statement": True, "Balance sheet": "cli" in lines, "Cash flow statement": "fco" in lines,
        "Sales by customer": bool(data.clients), "Debt schedule": "map_tot" in lines,
        "Support for EBITDA adjustments (invoices, contracts)": False,
        "Breakdown of other income and expenses": any(w in sheet_names for w in ("outros rendimentos", "other income")),
        "AR ageing": ageing("client", "receiv", "devedor"), "Inventory ageing": ageing("invent", "stock", "existenc"),
        "Facility agreements": False,
    }
    data.documents = [(doc, received[doc]) for doc in KEY_DOCUMENTS]

    if hasattr(file, "seek"):
        file.seek(0)
    ext = Extraction(data, _company(wb, name), "Excel — dictionary mapping, figures read from the cells",
                     source_text=data_room_text(file))
    _fill_review(ext, found_as)
    return ext


def _fill_review(ext: Extraction, found_as: dict[str, str]) -> None:
    """Review table: every standard line, what it was matched to, its source and its values."""
    d = ext.data
    extra = [("map_tot", "Debt schedule — total outstanding", "Debt"),
             ("map_cur", "Debt schedule — due within 12 months", "Debt"),
             ("cov_lim", "Covenant — maximum net debt / EBITDA", "Debt")]
    rows = [(f.key, f.label, STATEMENTS[f.statement]) for f in FIELDS] + extra
    for key, label, statement in rows:
        values = d.lines.get(key)
        item = {"key": key, "Statement": statement, "Line item": label, "Found as": found_as.get(key, "—"),
                "Source": d.sources.get(key, "—")}
        item.update({f"FY{str(y)[2:]}": (values or {}).get(y) for y in d.years})
        ext.items.append(item)
        if values is None:
            ext.missing.append(label)


def apply_edits(data: CompanyData, edits: dict[str, dict[int, float | None]]) -> CompanyData:
    """A copy of the data with the reviewer's corrections to some lines."""
    lines = {k: dict(v) for k, v in data.lines.items()}
    for key, values in edits.items():
        lines.setdefault(key, {}).update(values)
    return replace(data, lines=lines)


# ---------------------------------------------------------------- PDF (Claude reads it)
MODEL = "claude-opus-5-5"
_KEYS = tuple(f.key for f in FIELDS)


class _YearValue(BaseModel):
    year: int
    value: float


class _Line(BaseModel):
    key: Literal[_KEYS]
    label_in_document: str
    page: int
    values: list[_YearValue]


class _NamedLine(BaseModel):
    name: str
    page: int
    values: list[_YearValue]


class _Excerpt(BaseModel):
    title: str
    page: int
    text: str


class _PdfStatements(BaseModel):
    company_name: str
    unit: Literal["units", "thousands", "millions"]
    line_items: list[_Line]
    customers: list[_NamedLine]
    other_customers: list[_YearValue]
    adjustments: list[_NamedLine]
    debt_total_latest_year: float | None
    debt_current_portion_latest_year: float | None
    covenant_max_net_debt_to_ebitda: float | None
    narrative_excerpts: list[_Excerpt]


_PDF_PROMPT = """You are reading a company's financial statements for a buy-side financial due diligence model.

Return, for every line item below that the document presents, the figures EXACTLY as printed: no calculations,
no rounding, no sign changes, no unit conversion. Give the page where you read each item and the label used in
the document. Omit items the document does not present. Use one entry per fiscal year shown.

Line items (key: meaning):
{fields}

Also return, when presented: sales by customer (named customers and the 'other customers' line), management's
EBITDA adjustments (one entry per adjustment, as positive add-backs if presented that way), the debt schedule's
total and current portion for the latest year, and the maximum net debt / EBITDA covenant.

Finally, copy verbatim (do not paraphrase) the narrative passages a buyer would need: management report,
outlook, financing and refinancing, covenants, going concern, auditor's opinion, subsequent events, related
parties. At most 15 excerpts.

State the unit of the figures (units, thousands or millions)."""


def extract_pdf(pdf: bytes, name: str = "", client: anthropic.Anthropic | None = None) -> Extraction:
    """Claude reads the PDF statements; the code converts units and signs and builds the standard model."""
    client = client or anthropic.Anthropic()
    fields = "\n".join(f"- {f.key}: {f.label} ({STATEMENTS[f.statement]})" for f in FIELDS)
    try:
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",     # if the model declines, the API retries on the recommended fallback model
            output_format=_PdfStatements,
            messages=[{"role": "user", "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                "data": base64.standard_b64encode(pdf).decode()}},
                {"type": "text", "text": _PDF_PROMPT.format(fields=fields)},
            ]}],
        )
    except TypeError as e:
        if "authentication method" in str(e):
            raise ExtractionError("Reading PDFs uses the Claude API: add ANTHROPIC_API_KEY to the .env file.") from e
        raise
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise ExtractionError("Claude could not read this PDF (refused or truncated). Try the Excel version.")
    return _from_pdf(response.parsed_output, name)


def _from_pdf(p: _PdfStatements, name: str) -> Extraction:
    scale = {"units": 0.001, "thousands": 1.0, "millions": 1000.0}[p.unit]   # the model works in EUR thousands
    vals = lambda yv: {v.year: v.value * scale for v in yv}
    lines, sources, found_as = {}, {}, {}
    for line in p.line_items:
        f = FIELD_BY_KEY[line.key]
        if f.key not in lines:
            lines[f.key] = _signed(vals(line.values), f.sign)
            sources[f.key], found_as[f.key] = f"{name} p.{line.page}", line.label_in_document
    if "vendas" not in lines:
        raise ExtractionError("No revenue line found in the PDF.")
    pl_years = sorted(lines["vendas"])
    bs_years = sorted({y for k in ("cli", "cp", "caixa") for y in lines.get(k, {})})
    latest = pl_years[-1]
    for f in FIELDS:
        if f.key not in lines and f.zero_if_missing:
            lines[f.key], sources[f.key], found_as[f.key] = {y: 0.0 for y in bs_years}, "Not in document (0)", "—"
    for key, value, label in [("map_tot", p.debt_total_latest_year, "Debt schedule total"),
                              ("map_cur", p.debt_current_portion_latest_year, "Debt schedule current"),
                              ("cov_lim", p.covenant_max_net_debt_to_ebitda, "Covenant")]:
        if value is not None:
            lines[key] = {latest: value if key == "cov_lim" else value * scale}
            sources[key], found_as[key] = f"{name}", label

    data = CompanyData(years=sorted(set(pl_years) | set(bs_years)), lines=lines, sources=sources)
    data.clients = [Named(c.name, vals(c.values)) for c in p.customers]
    data.clients_source = f"{name} p.{p.customers[0].page}" if p.customers else ""
    data.other_clients = vals(p.other_customers)
    data.adjustments = [Named(a.name, vals(a.values)) for a in p.adjustments]
    data.adjustments_source = f"{name} p.{p.adjustments[0].page}" if p.adjustments else ""
    received = {"Income statement": True, "Balance sheet": "cli" in lines, "Cash flow statement": "fco" in lines,
                "Sales by customer": bool(p.customers), "Debt schedule": "map_tot" in lines}
    data.documents = [(doc, received.get(doc, False)) for doc in KEY_DOCUMENTS]

    text = "\n".join(f"[{name} p.{e.page}] {e.title}: {e.text}" for e in p.narrative_excerpts)
    ext = Extraction(data, p.company_name or name, "PDF — read by Claude (vision); verify the figures",
                     source_text=f"### Narrative excerpts copied from {name}\n{text}")
    _fill_review(ext, found_as)
    return ext


# ---------------------------------------------------------------- entry point
def read_financials(file: BinaryIO, name: str, client: anthropic.Anthropic | None = None) -> Extraction:
    """Any supported upload: company financial statements (Excel or PDF) or a completed DD template."""
    if name.lower().endswith(".pdf"):
        return extract_pdf(file.read(), name, client)
    if not name.lower().endswith((".xlsx", ".xlsm")):
        raise ExtractionError("Upload an Excel (.xlsx) or PDF file.")
    wb = load_workbook(file, read_only=True)
    is_template = "Input" in wb.sheetnames
    wb.close()
    file.seek(0)
    if not is_template:
        return extract_excel(file, name)
    data = load_input(file)
    ext = Extraction(data, name, "Completed DD template (Input sheet)")
    _fill_review(ext, {k: "Input sheet" for k in data.lines})
    return ext
