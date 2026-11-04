"""Layer 4b — the databook: the Excel a transaction team works in (deterministic, no AI).

One workbook, readable and auditable:
  Read Me · Executive Summary · Source Register · Financials · QoE · NWC · Net Debt · EV to Equity · Leakage ·
  Monthly & LTM · Issues & Requests · Checks
  - figures from the data room are inputs (blue), totals and bridges are formulas (black), links to another
    sheet are green; the cells the analyst decides (status, include, owner) are the only unlocked ones;
  - every line keeps its source and its nature: reported, calculated, corrected, assumed nil or not found;
  - text from the data room is written as text: a label starting with '=' never becomes a formula;
  - a formula written by openpyxl is not calculated: recalculate() asks Excel to calculate the workbook, and
    the Checks sheet compares each total with the value computed in Python.
All amounts in EUR thousands, whatever the display scale of the app.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties

from . import __version__
from .deal import _DISPOSAL
from .extract import FIELDS, STATEMENTS
from .metrics import EBITDA_LINES
from .rules import alerts, fy

# QoE register: the statuses of an adjustment, and those that enter the diligence-adjusted EBITDA
QOE_STATES = ["Proposed", "Needs evidence", "Approved by the analyst", "Rejected", "Applied by rule"]
QOE_INCLUDED = ("Approved by the analyst", "Applied by rule")
_FROM_DECISION = {"Accepted": "Approved by the analyst", "Rejected": "Rejected", "Under review": "Proposed"}

FONT = "Arial"
_NUM = '#,##0;(#,##0);"–"'
_PCT = '0.0%;(0.0%);"–"'
_INPUT = Font(name=FONT, size=10, color="0000FF")              # figure from the data room
_FORMULA = Font(name=FONT, size=10, color="000000")
_LINK = Font(name=FONT, size=10, color="008000")               # formula pointing to another sheet
_BOLD = Font(name=FONT, size=10, bold=True)
_HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
_HEAD_FILL = PatternFill("solid", fgColor="1F3864")
_DECISION = PatternFill("solid", fgColor="FFF2CC")             # the analyst decides here (unlocked)
_TOTAL_LINE = Border(top=Side(style="thin"))
LEGEND = [("Blue figure", "From the data room (input; see Source Register)", _INPUT, None),
          ("Black figure", "Formula in this sheet", _FORMULA, None),
          ("Green figure", "Formula linking another sheet", _LINK, None),
          ("Yellow cell", "Decision of the analyst: the only cells you can edit", _FORMULA, _DECISION)]


def adjusted_ebitda(reported: float, adjustments: list[tuple[float, str]]) -> float:
    """Reported EBITDA plus the adjustments approved by the analyst or applied by rule (a prudent buyer's view:
    proposed adjustments, or ones needing evidence, stay out)."""
    return reported + sum(amount for amount, state in adjustments if state in QOE_INCLUDED)


# ---------------------------------------------------------------- cell helpers
def _put(ws, row: int, col: int, value, font=_FORMULA, fmt: str | None = None, fill=None, unlocked=False):
    """Write a cell. Text is always text: a value starting with '=' from the data room stays a label."""
    cell = ws.cell(row=row, column=col)
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"      # formulas are written by _formula only
    cell.font = font
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill
    if unlocked:
        cell.protection = Protection(locked=False)
    return cell


def _formula(ws, row, col, text, link=False, fmt=_NUM, bold=False):
    cell = ws.cell(row=row, column=col)
    cell.value = text
    cell.font = Font(name=FONT, size=10, bold=bold, color="008000" if link else "000000")
    cell.number_format = fmt
    return cell


def _link(ref: str, sign: int = 1) -> str:
    """A link to another sheet that stays empty when the source is empty (a link to an empty cell gives 0 in
    Excel, which would hide a missing figure)."""
    return f'=IF(ISBLANK({ref}),"",{"-" if sign < 0 else ""}{ref})'


def _header(ws, row: int, labels: list[str]) -> None:
    for c, label in enumerate(labels, 1):
        cell = _put(ws, row, c, label, _HEAD)
        cell.fill = _HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def _title(ws, title: str, note: str) -> None:
    _put(ws, 1, 1, title, Font(name=FONT, size=12, bold=True))
    _put(ws, 2, 1, note, Font(name=FONT, size=9, italic=True, color="595959"))


def _finish(ws, widths: list[int], freeze: str, header_row: int, last_col: int) -> None:
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = freeze
    if ws.max_row > header_row:
        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(last_col)}{ws.max_row}"
    ws.print_area = f"A1:{get_column_letter(last_col)}{ws.max_row}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.protection.sheet = True                       # only the yellow cells are editable
    ws.protection.autoFilter = False
    ws.protection.sort = False


def _validation(ws, options: list[str], ref: str) -> None:
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(ref)


def _quoted(sheet: str) -> str:
    return f"'{sheet}'"


# ---------------------------------------------------------------- sheets
def _nature(key: str, a) -> str:
    src = a.data.sources.get(key, "")
    original, now = a.ext.data.lines.get(key), a.data.lines.get(key)
    if original != now:
        return "corrected by the analyst (original kept in Source Register)"
    if src.startswith("Not in data room"):
        return "assumed nil (not in the data room)"
    if "less the lines identified" in src:
        return "calculated (published total less the lines identified)"
    return "reported" if key in a.data.lines else "not found"


def _source_register(ws, a) -> None:
    _title(ws, "Source Register", "Every document of the data room and every line of the standard model, with its "
                                  "locator (sheet!cell, page, or XBRL tag) and nature.")
    _header(ws, 4, ["File", "Read as", "Found", "Size (KB)", "SHA-256"])
    r = 5
    for f in a.ext.files or [{"File": a.ext.company, "Read as": a.ext.method, "Found": ""}]:
        for c, key in enumerate(["File", "Read as", "Found", "Size (KB)", "SHA-256"], 1):
            _put(ws, r, c, f.get(key, ""))
        r += 1
    r += 1
    _put(ws, r, 1, "Lines of the standard model", _BOLD)
    r += 1
    years = a.data.years
    _header(ws, r, ["Statement", "Line", "Found as", "Locator", "Nature"] + [f"Original {fy(y)}" for y in years])
    start = r
    for it in a.ext.items:
        r += 1
        key = it["key"]
        for c, value in enumerate([it["Statement"], it["Line item"], it["Found as"], it["Source"], _nature(key, a)], 1):
            _put(ws, r, c, value)
        for c, y in enumerate(years, 6):
            v = a.ext.data.lines.get(key, {}).get(y)
            _put(ws, r, c, v, _INPUT, _NUM)
    _finish(ws, [22, 44, 44, 40, 34] + [12] * len(years), "B5", start, 5 + len(years))


def _financials(ws, a) -> dict[str, int]:
    """The normalised statements; returns the row of each line (for links) and of the EBITDA formula."""
    d, years = a.data, a.data.years
    _title(ws, "Financials", "Normalised statements, EUR thousands. Costs and payments negative. Nature: reported, "
                             "calculated, corrected or not found (see Source Register).")
    _header(ws, 4, ["Line", "Nature", "Source"] + [fy(y) for y in years])
    rows, r = {}, 4
    for st, title in STATEMENTS.items():
        r += 1
        _put(ws, r, 1, title, _BOLD)
        for f in (f for f in FIELDS if f.statement == st and f.key in d.lines):
            r += 1
            rows[f.key] = r
            _put(ws, r, 1, f.label)
            _put(ws, r, 2, _nature(f.key, a))
            _put(ws, r, 3, d.sources.get(f.key, ""))
            for c, y in enumerate(years, 4):
                _put(ws, r, c, d.v(f.key, y), _INPUT, _NUM)
        if st == "pl":
            r += 1
            rows["ebitda"] = r
            parts = [k for k in EBITDA_LINES if k in rows]
            _put(ws, r, 1, "EBITDA (calculated: " + ", ".join(FIELDS_BY_KEY[k].label.lower() for k in parts)
                 + (" less D&A, which sits inside the functions" if d.pl_format == "function" else "") + ")", _BOLD)
            _put(ws, r, 2, "calculated")
            for c, y in enumerate(years, 4):
                col = get_column_letter(c)
                terms = "+".join(f"N({col}{rows[k]})" for k in parts) or "0"
                if d.pl_format == "function" and "da" in rows:
                    terms += f"-N({col}{rows['da']})"
                cell = _formula(ws, r, c, f"={terms}", bold=True)
                cell.border = _TOTAL_LINE
            if "opinc" in rows and "da" in rows:
                r += 1
                rows["opinc_check"] = r
                _put(ws, r, 1, "Check: EBITDA + D&A − operating profit as published (0 = the D&A deducted is the one "
                               "added back)")
                for c, y in enumerate(years, 4):
                    col = get_column_letter(c)
                    _formula(ws, r, c, f'=IF(ISNUMBER({col}{rows["opinc"]}),{col}{rows["ebitda"]}+N({col}{rows["da"]})'
                                       f'-{col}{rows["opinc"]},"n/a")')
        r += 1
    _finish(ws, [58, 30, 34] + [13] * len(years), "D5", 4, 3 + len(years))
    return rows


FIELDS_BY_KEY = {f.key: f for f in FIELDS}


def _qoe(ws, a, fin_rows: dict[str, int]) -> dict:
    v, d = a.view, a.data
    years = v.pl_years
    cols = {y: 5 + i for i, y in enumerate(years)}
    fin_col = {y: 4 + i for i, y in enumerate(d.years)}
    _title(ws, "QoE — quality of earnings", "EUR thousands. Reported EBITDA → adjustments → diligence-adjusted EBITDA (scenario: "
                                            "only adjustments approved by the analyst or applied by rule). Change a "
                                            "status in yellow and the totals follow. 'One-off' in a description "
                                            "proves nothing: each adjustment needs its document.")
    head = ["ID", "Line", "Type", "Status"] + [fy(y) for y in years] + ["Reason", "Recurrence", "Document",
                                                                          "Effect", "Source"]
    _header(ws, 4, head)
    last = 4 + len(years)
    r = 5
    _put(ws, r, 1, "QOE-00")
    _put(ws, r, 2, "Reported EBITDA (Financials)", _BOLD)
    _put(ws, r, 3, "Reported")
    for y, c in cols.items():
        _formula(ws, r, c, f"=Financials!{get_column_letter(fin_col[y])}{fin_rows['ebitda']}", link=True, bold=True)
    reported_row = r
    entries = []
    for i, adj in enumerate(d.adjustments, 1):
        entries.append((f"QOE-M{i:02d}", adj.name, "Management adjustment",
                        _FROM_DECISION.get(a.decisions.get(adj.name, "Under review"), "Proposed"),
                        {y: adj.values.get(y) for y in years}, "Presented by management",
                        "Not assessed: request the evidence", "Invoices, contracts, ledger detail",
                        d.adjustments_source))
    gains = {y: -a.metrics["gain"][y] for y in years}
    if any(gains.values()) and not any(_DISPOSAL.search(x.name) for x in d.adjustments):
        entries.append(("QOE-R19", "Remove disposal gains within EBITDA", "Diligence adjustment (rule R19)",
                        "Applied by rule", gains, "A gain on selling assets does not recur", "Non-recurring",
                        "Sale agreement; accounting entry of the gain", d.sources.get("ganho_alien", "")))
    for i, adj in enumerate(a.analyst, 1):
        entries.append((f"QOE-A{i:02d}", adj.name, "Analyst adjustment", "Approved by the analyst",
                        {y: adj.values.get(y) for y in years}, "Entered by the analyst", "", "", ""))
    first = r + 1
    for entry in entries:
        r += 1
        ident, label, kind, state, values, reason, recurrence, document, source = entry
        _put(ws, r, 1, ident)
        _put(ws, r, 2, label)
        _put(ws, r, 3, kind)
        _put(ws, r, 4, state, fill=_DECISION, unlocked=True)
        for y, c in cols.items():
            _put(ws, r, c, values.get(y), _INPUT, _NUM)
        _put(ws, r, last + 1, reason)
        _put(ws, r, last + 2, recurrence)
        _put(ws, r, last + 3, document)
        _formula(ws, r, last + 4, f'=IF(OR(D{r}="{QOE_INCLUDED[0]}",D{r}="{QOE_INCLUDED[1]}"),"Included",'
                                  f'"Excluded")', fmt="@")
        _put(ws, r, last + 5, source)
    end = max(r, first)
    if entries:
        _validation(ws, QOE_STATES, f"D{first}:D{end}")
    else:
        r += 1
        _put(ws, r, 2, "No adjustment identified from the data provided: with annual accounts only, adjustments "
                       "need the trial balance, the ledger, the cost detail and the contracts (see Issues & Requests).")
    totals = {}
    for label, kind in (("Management-adjusted EBITDA (as presented)", "mgmt"),
                        ("Diligence-adjusted EBITDA — scenario: approved and applied only", "dd"),
                        ("Upside: adjustments proposed or needing evidence (not included)", "upside")):
        if kind == "mgmt" and not d.adjustments:
            continue
        r += 1
        totals[kind] = r
        _put(ws, r, 2, label, _BOLD)
        for y, c in cols.items():
            col = get_column_letter(c)
            rng = f"{col}{first}:{col}{end}"
            status = f"$D${first}:$D${end}"
            kinds = f"$C${first}:$C${end}"
            if kind == "mgmt":
                text = f'={col}{reported_row}+SUMIFS({rng},{kinds},"Management adjustment")'
            elif kind == "dd":
                text = (f'={col}{reported_row}+SUMIFS({rng},{status},"{QOE_INCLUDED[0]}")'
                        f'+SUMIFS({rng},{status},"{QOE_INCLUDED[1]}")')
            else:
                text = f'=SUMIFS({rng},{status},"Proposed")+SUMIFS({rng},{status},"Needs evidence")'
            cell = _formula(ws, r, c, text if entries else (f"={col}{reported_row}" if kind != "upside" else "=0"),
                            bold=kind != "upside")
            cell.border = _TOTAL_LINE
    r += 1
    if "lease_pay" in fin_rows:
        r += 1
        _put(ws, r, 2, "Memo: reported EBITDA before IFRS 16 (less lease payments in the cash flow statement)")
        for y, c in cols.items():
            fc = get_column_letter(fin_col[y])
            _formula(ws, r, c, f'=IF(ISBLANK(Financials!{fc}{fin_rows["lease_pay"]}),"n/a",'
                               f'{get_column_letter(c)}{reported_row}+Financials!{fc}{fin_rows["lease_pay"]})', link=True)
    _put(ws, r, 2, "Diligence-adjusted EBITDA margin")
    for y, c in cols.items():
        col = get_column_letter(c)
        _formula(ws, r, c, f"=IF(Financials!{get_column_letter(fin_col[y])}{fin_rows['vendas']}=0,\"n/a\","
                           f"{col}{totals['dd']}/Financials!{get_column_letter(fin_col[y])}{fin_rows['vendas']})",
                 link=True, fmt=_PCT)
    _finish(ws, [10, 52, 30, 24] + [13] * len(years) + [34, 26, 34, 12, 30], "E5", 4, last + 5)
    return {"cols": cols, "dd": totals["dd"]}


def _net_debt(ws, a, fin_rows: dict[str, int]) -> dict:
    v, d = a.view, a.data
    years = v.bs_years
    cols = {y: 5 + i for i, y in enumerate(years)}
    fin_col = {y: 4 + i for i, y in enumerate(d.years)}
    _title(ws, "Net Debt", "EUR thousands. Financial debt − cash, then the debt-like and cash-like items, each with its "
                           "classification. Include 'Yes' adds it to adjusted net debt. An item included here is taken "
                           "out of NWC (no double count). Subordinated to the definitions of the SPA.")
    _header(ws, 4, ["Line", "Classification", "Include", "Why"] + [fy(y) for y in years] + ["Source"])
    last = 4 + len(years)
    r = 4
    base = []
    for key, label, cls, sign in (("fin_lp", "Non-current borrowings", "Financial debt", 1),
                                  ("fin_cp", "Current borrowings", "Financial debt", 1),
                                  ("caixa", "Cash and cash equivalents", "Cash", -1)):
        r += 1
        base.append(r)
        _put(ws, r, 1, label)
        _put(ws, r, 2, cls)
        _put(ws, r, 3, "Yes")
        _put(ws, r, 4, "Always in net debt" if sign > 0 else "Cash as reported; restricted cash is assessed below")
        for y, c in cols.items():
            if key in fin_rows:
                _formula(ws, r, c, _link(f"Financials!{get_column_letter(fin_col[y])}{fin_rows[key]}", sign), link=True)
        _put(ws, r, last + 1, d.sources.get(key, "not found"))
    r += 1
    reported_row = r
    _put(ws, r, 1, "Reported net debt", _BOLD)
    for y, c in cols.items():
        col = get_column_letter(c)
        lp, cp, cash = (f"{col}{x}" for x in base)
        cell = _formula(ws, r, c, f'=IF(AND(ISNUMBER({cash}),OR(ISNUMBER({lp}),ISNUMBER({cp}))),N({lp})+N({cp})+{cash},'
                                  f'"incomplete")', bold=True)
        cell.border = _TOTAL_LINE
    item_rows = {}
    first = r + 1
    for i, b in enumerate(d.balance_items):
        r += 1
        item_rows[i] = r
        sign = 1 if b.nature == "debt" else -1
        included = a.include.get(i, b.include)
        _put(ws, r, 1, f"{b.label} ({b.kind or 'balance sheet'})")
        _put(ws, r, 2, f"{'Debt-like' if b.nature == 'debt' else 'Cash-like'}: {b.category}")
        _put(ws, r, 3, "Yes" if included else "No", fill=_DECISION, unlocked=True)
        _put(ws, r, 4, "Included by default (prudent buyer's view)" if b.include else "To assess: include only if "
                                                                                          "the SPA treats it as debt")
        for y, c in cols.items():
            x = b.values.get(y)
            _put(ws, r, c, None if x is None else sign * x, _INPUT, _NUM)
        _put(ws, r, last + 1, b.source)
    end = max(r, first)
    if d.balance_items:
        _validation(ws, ["Yes", "No"], f"C{first}:C{end}")
    r += 1
    adjusted_row = r
    _put(ws, r, 1, "Adjusted net debt", _BOLD)
    for y, c in cols.items():
        col = get_column_letter(c)
        items = f'+SUMIFS({col}{first}:{col}{end},$C${first}:$C${end},"Yes")' if d.balance_items else ""
        cell = _formula(ws, r, c, f'=IF(ISNUMBER({col}{reported_row}),{col}{reported_row}{items},{col}{reported_row})',
                        bold=True)
        cell.border = _TOTAL_LINE
    if "lease_pay" in d.lines and not any(b.category == "Lease liabilities" for b in d.balance_items):
        r += 2
        _put(ws, r, 1, "IFRS 16: the cash flow statement shows lease payments, but the balance sheet shows no separate "
                       "lease liability (it may sit in borrowings). Ask for the IFRS 16 note: keep EBITDA and net debt "
                       "on the same basis (see the QoE memo line, EBITDA before IFRS 16).")
    if any(b.category == "Lease liabilities" for b in d.balance_items):
        r += 2
        _put(ws, r, 1, "IFRS 16: EBITDA is after IFRS 16 (lease costs sit in D&A and interest). Lease liabilities in "
                       "net debt keep EBITDA and debt coherent; excluding them needs a pre-IFRS 16 EBITDA, which the "
                       "statements do not give.")
    _finish(ws, [52, 40, 10, 44] + [13] * len(years) + [34], "E5", 4, last + 1)
    return {"cols": cols, "reported": reported_row, "adjusted": adjusted_row, "items": item_rows}


def _nwc(ws, a, fin_rows: dict[str, int], nd: dict) -> dict:
    v, d = a.view, a.data
    years = v.bs_years
    cols = {y: 4 + i for i, y in enumerate(years)}
    fin_col = {y: 4 + i for i, y in enumerate(d.years)}
    _title(ws, "NWC — net working capital", "EUR thousands. Operating NWC = operating assets included − operating liabilities "
                                             "included (never current assets − current liabilities unfiltered). "
                                             "Include in yellow. Excluded by policy: cash, financial debt, and any "
                                             "item classified in Net Debt.")
    _header(ws, 4, ["Line", "Include", "Policy"] + [fy(y) for y in years] + ["Source"])
    last = 3 + len(years)
    r, first = 4, 5
    for key, label, sign, policy in (
            ("inv", "Inventories", 1, "Operating asset"), ("cli", "Trade receivables", 1, "Operating asset"),
            ("forn", "Trade payables", -1, "Operating liability"),
            ("oac", "Other current assets", 1, "Operating unless classified elsewhere; may hold tax, related "
                                               "parties or accruals: request the trial balance"),
            ("opc", "Other current liabilities", -1, "Operating unless classified elsewhere; may hold tax, "
                                                      "contract liabilities or accruals: request the trial balance")):
        r += 1
        _put(ws, r, 1, label)
        _put(ws, r, 2, "Yes", fill=_DECISION, unlocked=True)
        _put(ws, r, 3, policy)
        for y, c in cols.items():
            if key in fin_rows:
                _formula(ws, r, c, _link(f"Financials!{get_column_letter(fin_col[y])}{fin_rows[key]}", sign), link=True)
        _put(ws, r, last + 1, d.sources.get(key, "not found"))
    _validation(ws, ["Yes", "No"], f"B{first}:B{r}")
    end = r
    linked = []
    for i, b in enumerate(d.balance_items):
        if not b.in_nwc:
            continue
        r += 1
        linked.append(r)
        sign = 1 if b.nature == "debt" else -1
        _put(ws, r, 1, f"Less: {b.label} (if included in Net Debt)")
        _put(ws, r, 2, "linked")
        _put(ws, r, 3, "Follows Net Debt: an item counted there leaves NWC")
        for y, c in cols.items():
            ndc = get_column_letter(nd["cols"][y])
            _formula(ws, r, c, f"=IF('Net Debt'!$C${nd['items'][i]}=\"Yes\",'Net Debt'!{ndc}{nd['items'][i]},0)",
                     link=True)
        _put(ws, r, last + 1, b.source)
    r += 1
    total = r
    _put(ws, r, 1, "Net working capital", _BOLD)
    for y, c in cols.items():
        col = get_column_letter(c)
        links = "".join(f"+{col}{x}" for x in linked)
        needed = [f"ISNUMBER({col}{first + k})" for k in (1, 2, 3, 4)]   # receivables, payables, other lines
        cell = _formula(ws, r, c, f'=IF(AND({",".join(needed)}),SUMIFS({col}{first}:{col}{end},$B${first}:$B${end},'
                                  f'"Yes"){links},"incomplete")', bold=True)
        cell.border = _TOTAL_LINE
    r += 1
    _put(ws, r, 1, "NWC as % of revenue")
    for y, c in cols.items():
        col = get_column_letter(c)
        if "vendas" in fin_rows and y in fin_col:
            _formula(ws, r, c, f'=IFERROR({col}{total}/Financials!{get_column_letter(fin_col[y])}{fin_rows["vendas"]},'
                               f'"n/a")', link=True, fmt=_PCT)
    r += 1
    _put(ws, r, 1, f"Average of the {len(years)} year-ends — indicative peg reference only (a peg is set on 12–24 "
                   "monthly balances; see Monthly & LTM)")
    L = years[-1]
    span = f"{get_column_letter(cols[years[0]])}{total}:{get_column_letter(cols[L])}{total}"
    _formula(ws, r, cols[L], f'=IF(COUNT({span})={len(years)},AVERAGE({span}),"incomplete")')
    _finish(ws, [52, 10, 50] + [13] * len(years) + [34], "D5", 4, last + 1)
    return {"cols": cols, "total": total}


def _ev_to_equity(ws, a, qoe: dict, nd: dict, nwc: dict, price) -> dict:
    """Enterprise value to equity value. The mechanism cell decides which block is computed; nothing is computed
    until it is chosen. Links to QoE, Net Debt and NWC; inputs in yellow."""
    from .price import MECHANISMS, LEAKAGE_TREATMENTS
    v = a.view
    L, B = v.pl_years[-1], v.bs_years[-1]
    ndc, nwcc, qc = (get_column_letter(x["cols"][y]) for x, y in ((nd, B), (nwc, B), (qoe, L)))
    _title(ws, "EV to Equity", f"Balance sheet {fy(B)}, EUR thousands. Choose the mechanism of the SPA first. A model "
                               "configuration subordinated to the SPA definitions, not a clause; equity value is not "
                               "the amount the seller receives (escrow, retentions, earn-out and deferrals apart).")
    p = price
    lb = p.locked_box if p else None
    rows: dict[str, int] = {}

    def line(key, label, value=None, formula=None, decide=False, fmt=_NUM, link=False, bold=False):
        r = ws.max_row + 1
        rows[key] = r
        _put(ws, r, 1, label, _BOLD if bold else _FORMULA)
        if formula:
            _formula(ws, r, 2, formula, link=link, fmt=fmt, bold=bold)
        else:
            _put(ws, r, 2, value, _INPUT if not decide else _FORMULA, fmt, fill=_DECISION if decide else None,
                 unlocked=decide)
        return r

    line("mech", "Price mechanism (choose)", p.mechanism if p and p.mechanism else "", decide=True, fmt="@")
    _validation(ws, list(MECHANISMS), f"B{rows['mech']}")
    mech = f"$B${rows['mech']}"
    ws.append([])
    line("h1", "Completion accounts", bold=True, value=None)
    line("ev_direct", "Enterprise value entered directly", p.ev.value if p else None, decide=True)
    line("multiple", "…or multiple chosen by the user (no market multiple is supplied)", p.ev.multiple if p else None,
         decide=True, fmt="0.0x")
    line("ebitda", f"× EBITDA chosen: diligence-adjusted {fy(L)} (QoE)", formula=f"=QoE!{qc}{qoe['dd']}", link=True)
    line("ev", "Enterprise value used",
         formula=f'=IF(ISNUMBER(B{rows["ev_direct"]}),B{rows["ev_direct"]},IF(ISNUMBER(B{rows["multiple"]}),'
                 f'B{rows["multiple"]}*B{rows["ebitda"]},"enter EV"))', bold=True)
    line("debt", "− financial debt (Net Debt)", formula=f"=-(N('Net Debt'!{ndc}5)+N('Net Debt'!{ndc}6))", link=True)
    line("cash", "+ eligible cash (Net Debt; restricted cash is assessed there)", formula=f"=-N('Net Debt'!{ndc}7)",
         link=True)
    line("items", "− debt-like / + cash-like items included (Net Debt)",
         formula=f"=-IF(AND(ISNUMBER('Net Debt'!{ndc}{nd['adjusted']}),ISNUMBER('Net Debt'!{ndc}{nd['reported']})),"
                 f"'Net Debt'!{ndc}{nd['adjusted']}-'Net Debt'!{ndc}{nd['reported']},0)", link=True)
    nwc_default = p.nwc_closing if p and p.nwc_closing is not None else None
    line("nwc", f"NWC at closing (estimate; blank = {fy(B)} year-end from NWC)", nwc_default, decide=True)
    line("nwc_used", "NWC at closing used",
         formula=f'=IF(ISNUMBER(B{rows["nwc"]}),B{rows["nwc"]},NWC!{nwcc}{nwc["total"]})', link=True)
    line("peg", "Peg (target NWC of the SPA; blank = indicative average of the year-ends, not a peg)",
         p.peg if p and p.peg is not None else None, decide=True)
    line("peg_used", "Peg used", formula=f'=IF(ISNUMBER(B{rows["peg"]}),B{rows["peg"]},NWC!{nwcc}{nwc["total"] + 2})',
         link=True)
    line("nwc_adj", "+ NWC at closing − peg",
         formula=f'=IF(AND(ISNUMBER(B{rows["nwc_used"]}),ISNUMBER(B{rows["peg_used"]})),'
                 f'B{rows["nwc_used"]}-B{rows["peg_used"]},"incomplete")')
    others = list(p.other) if p else []
    first_other = ws.max_row + 1
    for i in range(max(2, len(others))):
        label, amount = others[i] if i < len(others) else ("", None)
        r = ws.max_row + 1
        _put(ws, r, 1, label or "Other contractual adjustment (label; amount with its sign)", fill=_DECISION,
             unlocked=True)
        _put(ws, r, 2, amount, _FORMULA, _NUM, fill=_DECISION, unlocked=True)
    last_other = ws.max_row
    line("equity_ca", "Equity value — completion accounts",
         formula=f'=IF({mech}<>"Completion accounts","",IF(AND(ISNUMBER(B{rows["ev"]}),ISNUMBER(B{rows["nwc_adj"]})),'
                 f'B{rows["ev"]}+B{rows["debt"]}+B{rows["cash"]}+B{rows["items"]}+B{rows["nwc_adj"]}'
                 f'+SUM(B{first_other}:B{last_other}),"incomplete"))', bold=True)
    line("nd_dl", "Memo: net debt with the debt-like items (counted once above)",
         formula=f"=-(B{rows['debt']}+B{rows['cash']}+B{rows['items']})")
    _put(ws, ws.max_row + 1, 1, "Escrow, retentions, earn-out, deferred consideration: none in the data room; add them "
                                "only from the SPA. Estimated price at closing, final completion accounts and true-up "
                                "are separate steps.")
    ws.append([])
    line("h2", "Locked box", bold=True, value=None)
    line("lb_price", "Equity price agreed at the locked box date", lb.equity_price if lb else None, decide=True)
    line("lb_date", "Locked box date", lb.locked_box_date if lb else None, decide=True, fmt="yyyy-mm-dd")
    line("close_date", "Closing date", lb.closing_date if lb else None, decide=True, fmt="yyyy-mm-dd")
    line("accrual", "Value accrual fixed in the SPA (blank: ticking fee below, or none)",
         lb.accrual if lb else None, decide=True)
    line("rate", "Ticking fee: annual rate (ACT/365)", lb.ticking_rate if lb else None, decide=True, fmt="0.00%")
    line("base", "Ticking fee: base", lb.ticking_base if lb else None, decide=True)
    line("fee", "Ticking fee",
         formula=f'=IF(AND(ISNUMBER(B{rows["rate"]}),ISNUMBER(B{rows["base"]}),ISNUMBER(B{rows["lb_date"]}),'
                 f'ISNUMBER(B{rows["close_date"]})),B{rows["base"]}*B{rows["rate"]}*(B{rows["close_date"]}'
                 f'-B{rows["lb_date"]})/365,0)')
    line("acc_used", "Accrual used", formula=f'=IF(ISNUMBER(B{rows["accrual"]}),B{rows["accrual"]},B{rows["fee"]})')
    line("leak", "Leakage confirmed after review (Leakage)",
         formula='=SUMIFS(Leakage!E:E,Leakage!J:J,"Confirmed after review")', link=True)
    line("treat", "Treatment of confirmed leakage", lb.treatment if lb else LEAKAGE_TREATMENTS[0], decide=True, fmt="@")
    _validation(ws, list(LEAKAGE_TREATMENTS), f"B{rows['treat']}")
    line("equity_lb", "Equity value — locked box, at closing",
         formula=f'=IF({mech}<>"Locked box","",IF(ISNUMBER(B{rows["lb_price"]}),B{rows["lb_price"]}+B{rows["acc_used"]}'
                 f'-IF(B{rows["treat"]}="Deduct at closing",B{rows["leak"]},0),"enter the agreed price"))', bold=True)
    line("claim", "Leakage claim, separate from the price",
         formula=f'=IF(B{rows["treat"]}="Separate claim",B{rows["leak"]},0)')
    _put(ws, ws.max_row + 1, 1, "Locked box: no true-up of NWC or net debt at closing; the buyer relies on the leakage "
                                "covenant.")
    ws.append([])
    line("h3", "Sensitivity (only when EV is derived from a multiple)", bold=True, value=None)
    r0 = ws.max_row + 1
    _put(ws, r0, 1, "EBITDA \\ multiple")
    for j, step in enumerate((-1, 0, 1), 2):
        _formula(ws, r0, j, f'=IF(ISNUMBER($B${rows["multiple"]}),$B${rows["multiple"]}{step:+d},"")', fmt="0.0x")
    for i, e in enumerate((-0.1, 0, 0.1), 1):
        r = r0 + i
        _formula(ws, r, 1, f'=IF(ISNUMBER($B${rows["multiple"]}),$B${rows["ebitda"]}*{1 + e},"EV fixed: no sensitivity")')
        for j in range(2, 5):
            col = get_column_letter(j)
            _formula(ws, r, j, f'=IF(AND(ISNUMBER({col}${r0}),ISNUMBER($A{r}),ISNUMBER($B${rows["nwc_adj"]})),'
                               f'{col}${r0}*$A{r}+$B${rows["debt"]}+$B${rows["cash"]}+$B${rows["items"]}'
                               f'+$B${rows["nwc_adj"]}+SUM($B${first_other}:$B${last_other}),"")')
    for col, w in zip("ABCD", [78, 16, 16, 16]):
        ws.column_dimensions[col].width = w
    ws.print_area = f"A1:D{ws.max_row}"
    ws.protection.sheet = True
    return rows


def _leakage(ws, a, price) -> None:
    from .price import INSUFFICIENT, LEAKAGE_STATES, leakage_candidates
    lb = price.locked_box if price else None
    items = (lb.leakage if lb and lb.leakage else leakage_candidates(a.data))
    _title(ws, "Leakage", "EUR thousands. Screening register, not a legal verdict. Only 'Confirmed after review' counts in EV to "
                          "Equity. A payment to a related party does not prove prohibited leakage; finding no candidate "
                          "does not prove there is none.")
    head = ["ID", "Date", "Beneficiary", "Relation to the seller", "Amount", "Description", "Document", "Clause",
            "Evidence", "Status", "Justification", "Treatment"]
    _header(ws, 4, head)
    r = 4
    for x in items:
        r += 1
        values = [x.id, x.date, x.beneficiary, x.relation, x.amount, x.description, x.document, x.clause, x.evidence]
        for c, value in enumerate(values, 1):
            if c == 5:
                _put(ws, r, c, value, _INPUT, _NUM)
            else:
                _put(ws, r, c, value)
        _put(ws, r, 10, x.status, fill=_DECISION, unlocked=True)
        _put(ws, r, 11, x.justification, fill=_DECISION, unlocked=True)
        _put(ws, r, 12, "", fill=_DECISION, unlocked=True)
    for _ in range(5):                                   # rows for payments found in the ledger or the SPA review
        r += 1
        _put(ws, r, 1, f"LK-{r - 4:02d}")
        for c in range(2, 13):
            _put(ws, r, c, None, _FORMULA, _NUM if c == 5 else None, fill=_DECISION, unlocked=True)
    _validation(ws, LEAKAGE_STATES, f"J5:J{r}")
    r += 2
    _put(ws, r, 1, "Conclusion", _BOLD)
    _formula(ws, r, 2, f'=IF(COUNTIF(J5:J{r - 2},"Confirmed after review")+COUNTIF(J5:J{r - 2},"Permitted by a clause")'
                       f'+COUNTIF(J5:J{r - 2},"Out of scope")=0,"{INSUFFICIENT}","Reviewed: see each status")', fmt="@")
    r += 1
    _put(ws, r, 1, "Coverage", _BOLD)
    _put(ws, r, 2, f"Documents: {len(a.ext.files) or 1} file(s) of the data room (Source Register); period: "
                   f"{', '.join(fy(y) for y in a.data.pl_years)} (annual cash flow statements only, no payment dates); "
                   f"entity: {a.ext.company}, as reported (consolidated where so presented). Not covered: the ledger, "
                   "related-party payments, management fees, the SPA.")
    for col, w in zip("ABCDEFGHIJKL", [8, 11, 16, 20, 13, 50, 18, 12, 22, 20, 44, 16]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "B5"
    ws.auto_filter.ref = f"A4:L{r - 3}"
    ws.print_area = f"A1:L{ws.max_row}"
    ws.protection.sheet = True
    ws.protection.autoFilter = False


def _placeholder(ws, title: str, lines: list[str]) -> None:
    _title(ws, title, lines[0])
    for i, line in enumerate(lines[1:], 4):
        _put(ws, i, 1, line)
    ws.column_dimensions["A"].width = 120
    ws.protection.sheet = True


def _issues(ws, a, reviews) -> None:
    reviews = reviews or {}
    _title(ws, "Issues & Requests", "Findings (observation, evidence, question, document) and the request list, with "
                                    "duplicate requests merged and every finding they come from kept.")
    _header(ws, 4, ["Finding", "Rule", "Area", "Severity", "Years", "Evidence (observation and source)",
                    "Question for management", "Document to request", "Status", "Owner", "Comment"])
    r = 4
    found = alerts(a.results)
    for i, res in enumerate(found, 1):
        r += 1
        state, comment = reviews.get(res.rule.id, ("Pending", ""))
        for c, value in enumerate([f"F-{i:02d}", res.rule.id, res.rule.area, res.rule.severity, res.years_text,
                                   res.evidence, res.rule.question, res.rule.request], 1):
            _put(ws, r, c, value).alignment = Alignment(wrap_text=True, vertical="top")
        _put(ws, r, 9, state, fill=_DECISION, unlocked=True)
        _put(ws, r, 10, "", fill=_DECISION, unlocked=True)
        _put(ws, r, 11, comment, fill=_DECISION, unlocked=True)
    if found:
        _validation(ws, ["Pending", "Accepted", "Dismissed"], f"I5:I{r}")
    requests: dict[str, list] = {}
    order = {s: i for i, s in enumerate(("High", "Medium", "Low"))}
    for res in found:
        for part in (p.strip() for p in res.rule.request.split(";")):
            if part and part.lower() != "the documents listed in the evidence":
                requests.setdefault(part[0].upper() + part[1:], []).append(res)
    for doc, ok in a.data.documents:
        if not ok:
            requests.setdefault(doc, [])
    for note in a.view.incomplete:
        requests.setdefault(f"Figure missing from the data room: {note.split(' — ')[0]}", [])
    r += 2
    _put(ws, r, 1, "Request list (duplicates merged)", _BOLD)
    r += 1
    _header(ws, r, ["Request", "Document", "From findings", "Priority", "", "", "", "", "Status"])
    for i, (doc, src) in enumerate(requests.items(), 1):
        r += 1
        prio = min((x.rule.severity for x in src), key=lambda s: order[s]) if src else "Medium"
        _put(ws, r, 1, f"REQ-{i:02d}")
        _put(ws, r, 2, doc).alignment = Alignment(wrap_text=True, vertical="top")
        _put(ws, r, 3, ", ".join(sorted({x.rule.id for x in src})) or "document checklist")
        _put(ws, r, 4, prio)
        _put(ws, r, 9, "Open", fill=_DECISION, unlocked=True)
    for col, w in zip("ABCDEFGHIJK", [9, 34, 18, 9, 10, 60, 44, 36, 11, 14, 28]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C5"
    if found:
        ws.auto_filter.ref = f"A4:K{4 + len(found)}"
    ws.print_area = f"A1:K{ws.max_row}"
    ws.protection.sheet = True
    ws.protection.autoFilter = False


def _checks(ws, a, qoe: dict, nd: dict, nwc: dict, ev: dict | None = None, price=None) -> int:
    """Reconciliations and the databook's own controls; returns the row of the recalculation status."""
    _title(ws, "Checks", "Reading checks, consistency rules and the databook's own controls: each total of this "
                         "workbook against the value computed in Python. Tolerance €1k (rounding of the source).")
    _put(ws, 3, 1, "Recalculation")
    _put(ws, 3, 2, "PENDING: formulas written by the tool, not yet calculated by a spreadsheet engine. Excel "
                   "calculates them when the file opens; compare each total with the Python value below.", Font(name=FONT, size=10, bold=True,
                                                                                   color="C00000"))
    _header(ws, 5, ["Control", "Year", "Workbook", "Python", "Difference", "Tolerance", "Status"])
    r = 5

    def control(label, year, workbook_ref, python):
        nonlocal r
        r += 1
        _put(ws, r, 1, label)
        _put(ws, r, 2, fy(year))
        _formula(ws, r, 3, f"={workbook_ref}", link=True)
        _put(ws, r, 4, python, _INPUT, _NUM)
        _formula(ws, r, 5, f'=IF(AND(ISNUMBER(C{r}),ISNUMBER(D{r})),C{r}-D{r},"n/a")')
        _put(ws, r, 6, 1, fmt=_NUM)
        _formula(ws, r, 7, f'=IF(E{r}="n/a",IF(AND(NOT(ISNUMBER(C{r})),NOT(ISNUMBER(D{r}))),"OK (both incomplete)",'
                           f'"CHECK"),IF(ABS(E{r})<=F{r},"OK","CHECK"))', fmt="@")

    v = a.view
    for y in v.pl_years:
        control("Diligence-adjusted EBITDA", y, f"QoE!{get_column_letter(qoe['cols'][y])}{qoe['dd']}", v.ebitda_dd[y])
    for y in v.bs_years:
        control("Adjusted net debt", y, f"'Net Debt'!{get_column_letter(nd['cols'][y])}{nd['adjusted']}",
                v.net_debt_adjusted[y])
        control("Net working capital", y, f"NWC!{get_column_letter(nwc['cols'][y])}{nwc['total']}", v.nwc_values[y])
    if price and price.mechanism:
        from .price import completion_equity, completion_from_analysis, locked_box_equity
        if price.mechanism == "Completion accounts":
            value = completion_equity(completion_from_analysis(a, price))["equity"]
            ref = f"'EV to Equity'!B{ev['equity_ca']}"
        else:
            value = locked_box_equity(price.locked_box)["equity"] if price.locked_box else None
            ref = f"'EV to Equity'!B{ev['equity_lb']}"
        control(f"Equity value — {price.mechanism.lower()}", v.bs_years[-1], ref, value)
    r += 2
    _put(ws, r, 1, "Reading checks (subtotals rebuilt from the lines vs as published)", _BOLD)
    for c in a.checks:
        r += 1
        _put(ws, r, 1, c["Check"])
        _put(ws, r, 2, fy(c["Year"]))
        _put(ws, r, 3, c["Rebuilt from the lines"], _INPUT, _NUM)
        _put(ws, r, 4, c["As published"], _INPUT, _NUM)
        _put(ws, r, 5, c["Difference"], fmt=_NUM)
        _put(ws, r, 6, c.get("Tolerance", 1), fmt="#,##0.0")
        _put(ws, r, 7, "OK" if c["OK"] else "FAILED")
    r += 2
    _put(ws, r, 1, "Consistency rules of the statements (R12–R17)", _BOLD)
    for res in a.results:
        if res.rule.area != "Consistency":
            continue
        for y, value in res.values.items():
            r += 1
            _put(ws, r, 1, f"{res.rule.id} · {res.rule.name}")
            _put(ws, r, 2, fy(y))
            _put(ws, r, 3, value if isinstance(value, (int, float)) else "n/a", _INPUT, _NUM)
            _put(ws, r, 6, res.rule.limit, fmt=_NUM)
            _put(ws, r, 7, {"Yes": "EXCEPTION", "No": "OK", "n/a": "not testable"}[res.fires[y]])
    for note in v.incomplete:
        r += 1
        _put(ws, r, 1, f"Incomplete: {note}")
    for col, w in zip("ABCDEFG", [70, 8, 14, 14, 12, 10, 22]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A6"
    ws.print_area = f"A1:G{ws.max_row}"
    ws.protection.sheet = True
    return 3


def _read_me(ws, a, stamp: str) -> None:
    from .pipeline import PURPOSES
    c = a.country
    _title(ws, f"Databook — {a.ext.company}", f"DD Assistant {__version__} · generated {stamp} · preliminary "
                                              "financial due diligence from the data room provided; not an audit, "
                                              "not a valuation, no investment recommendation.")
    rows = [("Company", a.ext.company), ("Purpose", PURPOSES[a.purpose]),
            ("Country and framework", f"{c.name} — {c.framework}" if c else "not set"),
            ("Sector", a.sector.name), ("Years", ", ".join(fy(y) for y in a.data.years)),
            ("Currency and unit", "EUR thousands in every sheet (negatives in brackets)"),
            ("How the figures were read", a.ext.method),
            ("Data", "SYNTHETIC DEMO DATA (fictitious company built to test the rules)"
             if any(n in a.ext.company for n in ("Duriva", "Velmora")) else
             "As provided in the data room: say whether it is real, synthetic or mixed when sharing this file"),
            ("Reviewer (declared locally, no login)", ""),
            ("Review date", ""),
            ("Version", f"DD Assistant {__version__}, {stamp}. A databook from an older run is outdated: regenerate "
                        "it after any change to the data room or to a decision.")]
    for i, (k, value) in enumerate(rows, 4):
        _put(ws, i, 1, k, _BOLD)
        unlocked = k.startswith("Reviewer") or k == "Review date"
        _put(ws, i, 2, value, fill=_DECISION if unlocked else None, unlocked=unlocked)
    r = 4 + len(rows) + 1
    _put(ws, r, 1, "Legend", _BOLD)
    for label, meaning, font, fill in LEGEND:
        r += 1
        _put(ws, r, 1, label, font, fill=fill)
        _put(ws, r, 2, meaning)
    r += 2
    _put(ws, r, 1, "Instructions", _BOLD)
    for line in ("Start with Executive Summary, then Checks: a failed check means a figure was misread.",
                 "Decide in the yellow cells: adjustment status (QoE), items in net debt (Net Debt), lines in NWC.",
                 "Every figure links to its source: Source Register gives the file, its SHA-256 and the locator.",
                 "Recalculate in Excel (F9 or open and save) before reading totals if Checks says PENDING."):
        r += 1
        _put(ws, r, 2, line)
    r += 2
    _put(ws, r, 1, "Limits", _BOLD)
    for line in ("Annual accounts only: no monthly data, so no LTM and no defensible peg (indicative reference only).",
                 "Adjustments are not invented: without the ledger and contracts, the QoE lists what to request.",
                 "EV to Equity computes nothing until the price mechanism is chosen; leakage is a screening "
                 "register, not a legal verdict.",
                 "Thresholds and calibrations are visible in the app's Rulebook and in `python -m dd_assistant --rules`."):
        r += 1
        _put(ws, r, 2, line)
    for col, w in zip("AB", [38, 120]):
        ws.column_dimensions[col].width = w
    ws.protection.sheet = True


def _summary(ws, a, fin_rows, qoe, nd, nwc) -> None:
    v = a.view
    L, B = v.pl_years[-1], v.bs_years[-1]
    fin_col = {y: 4 + i for i, y in enumerate(a.data.years)}
    _title(ws, "Executive Summary", f"Latest year {fy(L)} (balance sheet {fy(B)}). EUR thousands. Each figure links "
                                    "to its sheet.")
    _header(ws, 4, ["Indicator", fy(L), "Where"])
    rows = [("Revenue", f"Financials!{get_column_letter(fin_col[L])}{fin_rows['vendas']}", "Financials"),
            ("Reported EBITDA", f"QoE!{get_column_letter(qoe['cols'][L])}5", "QoE"),
            ("Diligence-adjusted EBITDA (approved and applied only)",
             f"QoE!{get_column_letter(qoe['cols'][L])}{qoe['dd']}", "QoE"),
            ("Adjusted net debt", f"'Net Debt'!{get_column_letter(nd['cols'][B])}{nd['adjusted']}", "Net Debt"),
            ("Net working capital", f"NWC!{get_column_letter(nwc['cols'][B])}{nwc['total']}", "NWC")]
    for i, (label, ref, sheet) in enumerate(rows, 5):
        _put(ws, i, 1, label)
        _formula(ws, i, 2, f"={ref}", link=True)
        cell = _put(ws, i, 3, f"→ {sheet}")
        cell.hyperlink = f"#{_quoted(sheet)}!A1"
        cell.font = Font(name=FONT, size=10, color="0563C1", underline="single")
    r = 5 + len(rows) + 1
    _put(ws, r, 1, "Findings", _BOLD)
    for sev in ("High", "Medium", "Low"):
        r += 1
        _put(ws, r, 1, f"{sev} severity")
        _formula(ws, r, 2, f"=COUNTIF('Issues & Requests'!D:D,\"{sev}\")", link=True, fmt="0")
    r += 2
    _put(ws, r, 1, "Pending", _BOLD)
    r += 1
    _put(ws, r, 1, "Adjustments proposed or needing evidence")
    _formula(ws, r, 2, '=COUNTIF(QoE!D:D,"Proposed")+COUNTIF(QoE!D:D,"Needs evidence")', link=True, fmt="0")
    r += 1
    _put(ws, r, 1, "Controls to check")
    _formula(ws, r, 2, '=COUNTIF(Checks!G:G,"CHECK")+COUNTIF(Checks!G:G,"FAILED")', link=True, fmt="0")
    for note in v.incomplete:
        r += 1
        _put(ws, r, 1, f"Incomplete: {note}")
    for col, w in zip("ABC", [62, 16, 16]):
        ws.column_dimensions[col].width = w
    ws.protection.sheet = True


def write_databook(a, path: str | Path | BinaryIO, reviews: dict | None = None, price=None) -> None:
    """The databook of an analysis (pipeline.Analysis). price (price.PriceInputs): what the analyst entered for the
    price mechanism; without it the EV to Equity sheet waits for the mechanism to be chosen."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    wb = Workbook()
    sheets = {name: (wb.active if i == 0 else wb.create_sheet(name)) for i, name in enumerate(
        ["Read Me", "Executive Summary", "Source Register", "Financials", "QoE", "NWC", "Net Debt", "EV to Equity",
         "Leakage", "Monthly & LTM", "Issues & Requests", "Checks"])}
    sheets["Read Me"].title = "Read Me"
    fin_rows = _financials(sheets["Financials"], a)
    qoe = _qoe(sheets["QoE"], a, fin_rows)
    nd = _net_debt(sheets["Net Debt"], a, fin_rows)
    nwc = _nwc(sheets["NWC"], a, fin_rows, nd)
    _source_register(sheets["Source Register"], a)
    ev = _ev_to_equity(sheets["EV to Equity"], a, qoe, nd, nwc, price)
    _leakage(sheets["Leakage"], a, price)
    _placeholder(sheets["Monthly & LTM"], "Monthly & LTM", [
        "Not available: the data room has no monthly figures.",
        "Without 12–24 monthly balances there is no LTM, no seasonality and no defensible working capital peg.",
        "Request: monthly management accounts (P&L) and month-end balances of receivables, inventories and payables "
        "for the last 24 months."])
    _issues(sheets["Issues & Requests"], a, reviews)
    _checks(sheets["Checks"], a, qoe, nd, nwc, ev, price)
    _read_me(sheets["Read Me"], a, stamp)
    _summary(sheets["Executive Summary"], a, fin_rows, qoe, nd, nwc)
    wb.calculation.fullCalcOnLoad = True     # Excel calculates every formula when the file opens
    wb.properties.title = f"Databook — {a.ext.company}"
    wb.properties.creator = f"DD Assistant {__version__}"
    wb.save(path)


# ---------------------------------------------------------------- recalculation
_PS_RECALC = r"""
$ErrorActionPreference = 'Stop'
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($env:DD_BOOK)
    $ws = $wb.Worksheets.Item('Checks')
    $ws.Unprotect()
    $ws.Range('B3').Value2 = "Recalculated by Microsoft Excel on " + (Get-Date -Format 'yyyy-MM-dd HH:mm')
    $ws.Range('B3').Font.Color = 32768
    $ws.Protect()
    $xl.CalculateFull()
    $wb.Save()
    $wb.Close($false)
} finally {
    $xl.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
}
"""


def excel_available() -> bool:
    if os.name != "nt":
        return False
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                              "[bool](Get-ItemProperty 'Registry::HKEY_CLASSES_ROOT\\Excel.Application' "
                              "-ErrorAction SilentlyContinue)"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() == "True"
    except (OSError, subprocess.TimeoutExpired):
        return False


def recalculate(path: str | Path) -> bool:
    """Ask Excel to calculate the workbook in place (Windows with Excel). False when no engine is available: the
    Checks sheet then keeps saying PENDING."""
    if not excel_available():
        return False
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "databook.xlsx"
        shutil.copyfile(path, work)
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_RECALC],
                       env={**os.environ, "DD_BOOK": str(work)}, check=True, timeout=300)
        shutil.copyfile(work, path)
    return True


def control_results(path: str | Path) -> list[tuple[str, str, object, object, str]]:
    """After recalculation: (control, year, workbook value, Python value, status) of each control of Checks."""
    ws = load_workbook(path, data_only=True)["Checks"]
    out = []
    for row in ws.iter_rows(min_row=6, values_only=True):
        if not row[0] or row[0].startswith(("Reading checks", "Consistency", "Incomplete")):
            break
        out.append((row[0], row[1], row[2], row[3], row[6]))
    return out
