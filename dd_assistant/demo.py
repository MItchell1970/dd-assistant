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
TAGLINE = "A first-pass financial due diligence on published accounts: every figure traced to its source"
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
         "Consolidated accounts FY2025, 2025 Integrated Report",
         pages="2025 Integrated Report, pp. 152–156, notes 10 and 20",
         context="The privatisation is under way: Air France-KLM and Lufthansa submitted binding offers, and the "
                 "Government extended the deadline to complete it to the end of 2026.",
         context_source=("Jornal de Notícias, 6 September 2026",
                         "https://www.jn.pt/economia/artigo/governo-prorroga-ate-final-do-ano-prazo-para-concluir-"
                         "privatizacao-da-tap/18123884")),
    Case("toyota-caetano", "Toyota Caetano Portugal", "Toyota_Caetano_2025_published.xlsx", "PT", "automotive",
         "Other income is 60.5% of FY25 EBITDA, and operating cash flow turned negative in FY25 (−€3,987k).",
         "Consolidated accounts FY2025, 2025 annual report (ESEF)",
         pages="Relatório Anual 2025 (ESEF), consolidated statements"),
    Case("corticeira-amorim", "Corticeira Amorim", "Corticeira_Amorim_2025_published.xlsx", "PT", "materials",
         "Capex runs below depreciation in both years, and short-term debt fell from 56.3% to 28.7% of debt.",
         "Consolidated accounts FY2025, 2025 annual report (ESEF)",
         pages="Relatório Anual 2025 (ESEF), consolidated statements and note 19"),
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
def _extraction(path: Path):
    return read_data_room(files_in([path]))


def analysis(case: Case, decisions: dict | None = None, include: dict | None = None, analyst: list | None = None,
             documents: list | None = None) -> Analysis:
    """The analysis of a demo company, with the visitor's decisions (none = the default the memo was checked on)."""
    return analyse(_extraction(case.path), case.sector, case.country, None, documents, decisions, analyst, include,
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
