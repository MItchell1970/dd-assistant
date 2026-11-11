"""Demo mode: the same app on three real companies' published accounts, with no upload and no Claude API.

Turned on by the environment variable DD_DEMO=1 (DD_DEMO=0 turns it off). On Streamlit Community Cloud, where the
repository is cloned under /mount/src, the demo is the default: a public copy never shows the upload or the API
buttons by mistake.

The memo of each company was written beforehand on the author's computer by Claude Code (the due-diligence skill,
no API), passed the automatic checker and is stored in docs/examples/<company>/ with the check and the databook.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .dataroom import files_in, read_data_room
from .memo_check import MemoCheck, check_memo
from .pipeline import Analysis, analyse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXAMPLES = ROOT / "docs" / "examples"

AUTHOR = "Bernardo Espinola"
GITHUB = "https://github.com/MItchell1970/dd-assistant"
LINKEDIN = "https://www.linkedin.com/in/bernardo-mitchell-de-arvellos-espinola/"
TAGLINE = "A first-pass financial due diligence on published accounts. Every figure traced to its source"
BUILT_BY = ("Built by Bernardo Espinola, Economics, University of Porto · former intern in International Tax and "
            "Transaction Services at EY")
FOR_WHOM = ("For deal teams, lenders and analysts who need the first pass of a financial due diligence fast, and "
            "want to check every number.")
DATA_NOTE = ("Nothing is uploaded and no AI is called in this demo. The engine runs on the published accounts stored "
             "in the repository; the memos were written beforehand and checked by code.")
PROCESS = (("description", "Read the accounts", "Every line of the statements, with its sheet and cell"),
           ("fact_check", "Check the reading", "Rebuild the published subtotals before trusting a figure"),
           ("flag", "Flag what matters", "30 rules, each with evidence, source and a question"),
           ("account_balance", "Build the bridges", "EBITDA, net debt and working capital, as a deal team asks"),
           ("table_view", "Export to Excel", "A databook with live formulas and every source"))
NOT_MEASURED = ("Time saved against a manual review: not measured.",
                "Distortions nobody thought of, smaller ones, or several at once: the benchmark plants one known "
                "distortion at a time.",
                "Review by a practitioner: the classification of the findings is proposed by the agent and not yet "
                "reviewed by a person.")
HOW_TO_CHECK = ("Data room tab: every line read, the label it matched and its cell in the published file.",
                "Reading checks: the subtotals rebuilt from those lines against the ones the company printed.",
                "Red flags: each finding gives its figures, the source cell and the threshold.",
                "Databook: open the Excel, follow any total back to its source line; the Checks sheet compares "
                "every total with the code.",
                "Memo tab: the checker's result, run again on the page.")
GLOSSARY = {
    "QoE": "Quality of earnings: how much of the reported profit is recurring and supported by evidence.",
    "EBITDA": "Earnings before interest, tax, depreciation and amortisation: operating profit before the cost of "
              "assets and financing.",
    "Diligence-adjusted EBITDA": "EBITDA after the adjustments the reviewer accepts: what a buyer would price.",
    "Net debt": "What the company owes to lenders, less its cash; a buyer deducts it from the value of the business.",
    "Debt-like item": "An obligation that is not a bank loan but behaves like one (leases, pensions, tax due), so it "
                      "is deducted from the price.",
    "IFRS 16": "The lease standard: future lease payments are shown as debt, and their cost leaves EBITDA.",
    "NWC": "Net working capital: stock plus money owed by customers, less money owed to suppliers and similar items.",
    "Peg": "The normal level of working capital agreed in the sale contract; a difference at closing changes the "
           "price.",
    "Completion accounts": "A price fixed on the balance sheet at closing, with net debt and working capital "
                           "trued up.",
    "Locked box": "A price fixed on a past balance sheet; the buyer is protected against value leaving the "
                  "company (leakage).",
    "Red flag": "A finding a rule raised: a figure beyond a threshold that needs an explanation from management.",
    "Materiality": "The size below which an item does not change the reader's view: here 5% of EBITDA for "
                   "earnings items and 1% of revenue for balance sheet items, and you can change it.",
    "Amount at stake": "The euros behind a finding, computed from the lines that made the rule fire.",
    "Deal implication": "What a deal team typically does with an issue: change the price, protect itself in the "
                        "contract, ask for more, or plan for it after the deal.",
    "SPA": "Share purchase agreement: the contract for the sale of the company.",
    "DSO / DIO / DPO": "Days of sales outstanding, inventory outstanding and payables outstanding: how long "
                       "customers take to pay, stock stays, and the company takes to pay suppliers.",
    "ESEF": "European Single Electronic Format: the tagged annual report EU listed companies must publish.",
}
WARNING = "Demo on published accounts. Preliminary analysis, not an opinion."
LIMITS = ("Annual accounts only (no monthly figures, LTM or budget)", "Euros only",
          "Financial due diligence only (no legal, tax, commercial or IT review)",
          "A first pass for an analyst to review, not a conclusion")


@dataclass(frozen=True)
class Case:
    slug: str             # folder in docs/examples
    company: str          # as shown on the card
    file: str             # published accounts in data/
    country: str
    sector: str
    headline: str         # the most interesting finding, in one sentence (figures from the engine; tested)
    accounts: str         # what the accounts are and where they come from
    purpose: str = "buy"
    pages: str = ""       # where the statements are in the report
    notes: str = ""       # the key notes of the report, transcribed, in data/notes/
    prior: str = ""       # the prior year's published accounts in data/: the third year, and restatements
    page_of: dict = None  # sheet of the data file -> where it is printed in the report (page or statement)
    big: str = ""         # the card's big number (from the engine; tested against the material)
    big_label: str = ""
    context: str = ""     # one sentence of outside context for the visitor, never given to the engine or the memo
    context_source: tuple[str, str] = ("", "")   # (publication and date, URL)

    @property
    def path(self) -> Path:
        return DATA / self.file

    @property
    def folder(self) -> Path:
        return EXAMPLES / self.slug

    @property
    def memo_path(self) -> Path:
        return self.folder / "memo.md"

    @property
    def check_path(self) -> Path:
        return self.folder / "memo_check.md"

    @property
    def databook_path(self) -> Path:
        return self.folder / "databook.xlsx"

    @property
    def case_note_path(self) -> Path:
        return self.folder / "case_note.md"


CASES = (
    Case("tap", "TAP Air Portugal", "TAP_2025_published.xlsx", "PT", "transport",
         "More cash than bank debt, yet €2,293m of net debt (3.16x EBITDA) once the leased aircraft (IFRS 16) and pensions are counted.",
         "Consolidated accounts FY2023 to FY2025, 2025 Integrated Report and 2024 annual report",
         pages="2025 Integrated Report, pp. 152–156, notes 10 and 20",
         prior="TAP_2024_published.xlsx", notes="TAP_2025_notes.xlsx",
         page_of={"Financial position": "p.152", "Income statement": "p.153", "Cash flow": "p.156",
                  "Note 10 Other receivables": "note 10, p.190", "Note 20 Other payables": "note 20, p.208"},
         big="€2,293m", big_label="adjusted net debt, vs −⁠€43m borrowings less cash",
         context="The privatisation is under way: Air France-KLM and Lufthansa submitted binding offers, and the "
                 "Government extended the deadline to complete it to the end of 2026.",
         context_source=("Jornal de Notícias, 6 September 2026",
                         "https://www.jn.pt/economia/artigo/governo-prorroga-ate-final-do-ano-prazo-para-concluir-"
                         "privatizacao-da-tap/18123884")),
    Case("toyota-caetano", "Toyota Caetano Portugal", "Toyota_Caetano_2025_published.xlsx", "PT", "automotive",
         "Other income is 60.5% of FY25 EBITDA; note 22 shows €48,078k of stock financing outside reported debt.",
         "Consolidated accounts FY2023 to FY2025, 2025 and 2024 annual reports (ESEF)",
         pages="Relatório Anual 2025 (ESEF), consolidated statements",
         prior="Toyota_Caetano_2024_published.xlsx", notes="Toyota_Caetano_2025_notes.xlsx",
         page_of={"DRE": "income statement", "Balanço": "statement of financial position",
                  "DFC": "cash flow statement"},
         big="60.5%", big_label="of FY25 EBITDA is other income"),
    Case("corticeira-amorim", "Corticeira Amorim", "Corticeira_Amorim_2025_published.xlsx", "PT", "materials",
         "Cash came from releasing stock as sales fell 8.3%; short-term debt fell from 56.3% to 28.7% of debt.",
         "Consolidated accounts FY2023 to FY2025, 2025 and 2024 annual reports (ESEF)",
         pages="Relatório Anual 2025 (ESEF), consolidated statements and note 19",
         prior="Corticeira_Amorim_2024_published.xlsx", notes="Corticeira_Amorim_2025_notes.xlsx",
         page_of={"Resultados": "income statement", "Posição financeira": "statement of financial position",
                  "Fluxos de caixa": "cash flow statement", "Nota 19 Caixa": "note 19"},
         big="155.3%", big_label="cash conversion, as stock was released"),
)
CASE_BY_SLUG = {c.slug: c for c in CASES}


def enabled(env: dict | None = None, root: Path | str | None = None) -> bool:
    """DD_DEMO=1 turns the demo on and DD_DEMO=0 off; unset, it is on only on Streamlit Community Cloud."""
    flag = (os.environ if env is None else env).get("DD_DEMO", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    return str(ROOT if root is None else root).replace("\\", "/").startswith("/mount/src/")


@lru_cache(maxsize=8)
def _extraction(path: Path, prior: Path | None = None, notes: Path | None = None):
    ext = read_data_room(files_in([path]))
    if prior is not None and prior.exists():
        from .history import add_prior_report
        ext = add_prior_report(ext, read_data_room(files_in([prior])), prior.name)
    if notes is not None and notes.exists():
        from dataclasses import replace
        from .notes import not_read, read_notes
        ext = replace(ext, notes=read_notes(notes), notes_file=notes.name, notes_not_read=not_read(notes))
    return ext


def extraction(case: Case):
    """What was read for a demo company: the latest report, with the earlier year of the prior report if stored."""
    return _extraction(case.path, DATA / case.prior if case.prior else None,
                       DATA / "notes" / case.notes if case.notes else None)


def analysis(case: Case, decisions: dict | None = None, include: dict | None = None, analyst: list | None = None,
             documents: list | None = None) -> Analysis:
    """The analysis of a demo company, with the visitor's decisions (none = the default the memo was checked on)."""
    return analyse(extraction(case), case.sector, case.country, None, documents, decisions, analyst, include,
                   case.purpose)


def material(case: Case, a: Analysis | None = None) -> str:
    """The material the memo is checked against, exactly as the command line writes it."""
    from .ai_memo import build_material
    a = a or analysis(case)
    return build_material(a.data, a.metrics, a.results, a.ext.source_text, name=case.path.name, analysis=a)


def memo(case: Case) -> str | None:
    return case.memo_path.read_text(encoding="utf-8") if case.memo_path.exists() else None


def check(case: Case) -> MemoCheck | None:
    """The stored memo checked again, now, against the default analysis: the result shown in the demo."""
    text = memo(case)
    if text is None:
        return None
    a = analysis(case)
    return check_memo(text, material(case, a), [r.rule.id for r in a.findings])


def section(text: str, title: str) -> str:
    """A '## ' section of the memo, from its heading to the next one at the same level (empty if absent)."""
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line[3:].strip().lower().startswith(title.lower())
        if inside:
            out.append(line)
    return "\n".join(out).strip()


def request_list(case: Case) -> str:
    text = memo(case)
    return section(text, "Information request list") if text else ""


def insights(case: Case) -> list[dict[str, str]]:
    """The three talking points of the case note (title, the number, why it matters, question for management)."""
    import re
    if not case.case_note_path.exists():
        return []
    text = case.case_note_path.read_text(encoding="utf-8")
    part = text[text.index("## Three talking points"):text.index("## Limits")]
    out = []
    for block in re.split(r"\n\*\*\d+\. ", part)[1:]:
        field_ = lambda name: (re.search(rf"- \*{name}:\* (.+)", block) or [None, ""])[1].strip()
        out.append({"title": block.split("**")[0].strip().rstrip("."), "number": field_("The number"),
                    "why": field_("Why it matters in a deal"),
                    "question": field_("Question for management").strip('"“”')})
    return out


def verification() -> dict[str, int]:
    """The three numbers of 'How it is verified', computed now: tests, published subtotals rebuilt on the demo
    companies, and memo figures checked (with those found without a source)."""
    import unittest
    try:
        tests = unittest.TestLoader().discover(str(ROOT / "tests"), top_level_dir=str(ROOT)).countTestCases()
    except Exception:   # noqa: BLE001 — the page still shows the other two numbers
        tests = 0
    checks = passed = figures = unmatched = 0
    for c in CASES:
        a = analysis(c)
        checks += len(a.checks)
        passed += sum(x["OK"] for x in a.checks)
        r = check(c)
        if r is not None:
            figures += r.numbers_checked
            unmatched += len(r.unmatched_numbers)
    return {"tests": tests, "checks": checks, "checks_passed": passed, "figures": figures, "unmatched": unmatched}


def tour_steps(case: Case, a: Analysis) -> list[tuple[str, str]]:
    """The 60-second tour: (title, one sentence) for each of the five steps; every figure comes from the engine."""
    passed, total = sum(c["OK"] for c in a.checks), len(a.checks)
    first = insights(case)[0] if insights(case) else {"title": "", "number": ""}
    order = ("High", "Medium", "Low")
    flag = min(a.findings, key=lambda r: order.index(r.rule.severity)) if a.findings else None
    B = a.view.bs_years[-1]
    return [
        ("Check the reading", f"Before trusting any figure, the agent rebuilt {passed} of {total} subtotals the "
                              "company published from the lines it read."),
        ("The key insight", f"{first['title']}: {first['number'][:1].upper() + first['number'][1:]}"),
        ("The bridge", f"Net debt from borrowings less cash ({a.money.fmt(a.view.net_debt_reported[B])}) to adjusted "
                       f"net debt ({a.money.fmt(a.view.net_debt_adjusted[B])}), one step per debt-like item."),
        ("A red flag, with its source", f"{flag.rule.id} · {flag.rule.name} ({flag.rule.severity}). {flag.rule.plain}"
         if flag else "No rule fired on these accounts."),
        ("Take it to Excel", "The databook holds the same bridges with live formulas, every figure with its source "
                             "cell, and a Checks sheet that compares each total with the code."),
    ]


def detection() -> dict[str, int]:
    """The published result of the detection benchmark (docs/DETECTION.md, written by
    scripts/detection_benchmark.py): planted distortions detected, out of those scored. Empty if not run."""
    import re
    path = ROOT / "docs" / "DETECTION.md"
    if not path.exists():
        return {}
    m = re.search(r"\*\*Detected: (\d+) of (\d+) planted distortions", path.read_text(encoding="utf-8"))
    return {"detected": int(m.group(1)), "scored": int(m.group(2))} if m else {}
