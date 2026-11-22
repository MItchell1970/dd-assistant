"""How far an ESEF reading can be relied on: one warning, shown in the app, the databook and the memo material.

Three levels for a report that was read, from the worst:
  - 'Reading check failed, do not rely': a published subtotal is not rebuilt from the lines read, the balance sheet
    does not balance, no depreciation and amortisation is found (EBITDA would equal operating profit), a statement tag carries two different figures for the same period (a mis-tagged line, as in
    Toyota Caetano's FY2025 filing), or there is no published subtotal to check the reading against;
  - 'Notes missing: …': the statements read well, but the report does not tag the notes a first pass leans on
    (borrowings, provisions, leases, related parties, other income, segments) as IFRS text blocks, so the memo
    cannot quote them from the tags;
  - 'Complete': both of the above are fine.
A report that could not be read at all (download refused, unsafe .zip, another currency, no statements) is
'Not analysed', with the reason: a failure is a quality warning, never hidden.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .rules import fy

COMPLETE, NOTES_MISSING, FAILED, NOT_ANALYSED = ("Complete", "Notes missing", "Reading check failed, do not rely",
                                                 "Not analysed")
# the notes a first pass reads, and the IFRS text blocks (ESEF block tagging, mandatory from FY2022) that carry them
TOPICS = {
    "borrowings": r"Borrowings",
    "provisions": r"Provisions",
    "leases": r"Leases",
    "related parties": r"RelatedParty",
    "other income": r"OtherOperatingIncome|OtherIncome",
    "segments": r"Segments",
}


@dataclass
class Quality:
    level: str
    reasons: list[str] = field(default_factory=list)
    notes_found: list[str] = field(default_factory=list)    # topics of TOPICS tagged in the report

    @property
    def headline(self) -> str:
        if self.level == NOTES_MISSING:
            return f"{NOTES_MISSING}: " + ", ".join(t for t in TOPICS if t not in self.notes_found)
        return self.level

    @property
    def ok(self) -> bool:
        return self.level in (COMPLETE, NOTES_MISSING)

    def text(self) -> str:
        """One line for the memo material and the databook."""
        return f"ESEF data quality: {self.headline}." + "".join(f" {r}" for r in self.reasons)


def notes_found(blocks: list[str]) -> list[str]:
    return [t for t, pattern in TOPICS.items() if any(re.search(pattern, b) for b in blocks)]


def assess(ext, data, checks: list[dict], metrics) -> Quality | None:
    """The warning for an analysis read from an ESEF report; None for any other data room."""
    if not ext.esef:
        return None
    reasons = []
    failed = [c for c in checks if not c["OK"]]
    reasons += [f"{c['Check']} {fy(c['Year'])}: rebuilt {c['Rebuilt from the lines']:,.0f} vs published "
                f"{c['As published']:,.0f} (EUR thousands)." for c in failed]
    if not checks:
        reasons.append("No published subtotal (gross profit, EBITDA or operating profit) to check the reading against.")
    no_da = [y for y in data.pl_years if data.v("da", y) is None]
    if no_da:   # the checks would still pass: EBITDA would simply equal operating profit
        reasons.append("No depreciation and amortisation found (" + ", ".join(fy(y) for y in no_da) + "): EBITDA "
                       "cannot be rebuilt and would equal operating profit.")
    off = {y: v for y, v in (metrics.get("bs_diff") or {}).items() if v is not None and abs(v) > 1}
    reasons += [f"Balance sheet {fy(y)} does not balance: difference {v:,.0f} (EUR thousands)."
                for y, v in sorted(off.items())]
    if ext.esef.get("conflicts"):
        shown = ext.esef["conflicts"][:5]
        more = len(ext.esef["conflicts"]) - len(shown)
        reasons.append("Same tag, same period, different figures (a mis-tagged line): " + "; ".join(shown)
                       + (f"; and {more} more" if more > 0 else "") + ".")
    found = notes_found(ext.esef.get("blocks", []))
    if reasons:
        return Quality(FAILED, reasons, found)
    if len(found) < len(TOPICS):
        why = ("The report tags no note as an IFRS text block (block tagging is mandatory from FY2022)."
               if not ext.esef.get("blocks") else
               "Notes tagged: " + (", ".join(found) or "none of these") + ".")
        return Quality(NOTES_MISSING, [why], found)
    return Quality(COMPLETE, [], found)


def not_analysed(reason: str) -> Quality:
    return Quality(NOT_ANALYSED, [reason])
