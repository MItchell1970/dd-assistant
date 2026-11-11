"""Write docs/REVIEW_SHEET.xlsx: every key issue of the three demo companies, with its evidence and the classification
the agent proposes, and empty columns for the reviewer's own decision.

    python scripts\\review_sheet.py

The decision columns are for Bernardo. Nothing here fills them: docs/VALIDATION.md may say 'reviewed by a person'
only after he has. Running the script again keeps what he wrote (matched by company and key).
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dd_assistant import demo  # noqa: E402
from dd_assistant.rules import fy  # noqa: E402

OUT = ROOT / "docs" / "REVIEW_SHEET.xlsx"
TRUE, REVIEW = "true positive", "to review"
DECISIONS = ["true positive", "known false alarm", "to review", "not relevant"]
# Proposed by Claude Code from the published figures and notes. (company slug, rule) -> (classification, why)
PROPOSED = {
    ("tap", "R28"): (REVIEW, "The unclassified 'other' current lines are real and large, but the notes read do not "
                             "break them down: content unknown."),
    ("tap", "R11"): (REVIEW, "Fired on FY23 only (69.3% due within a year); by FY25 it is 2.8% after the bond issue. "
                             "Historic, not a current refinancing risk."),
    ("tap", "R22"): (TRUE, "EBITDA covers interest 3.7x in FY25, below 4x in all three years; interest includes "
                           "lease interest."),
    ("tap", "R24"): (REVIEW, "Fired on FY23–FY24 (capex 0.42x and 0.75x of D&A); FY25 is 0.88x. Fleet is mostly "
                             "leased, so capex understates investment."),
    ("tap", "R07"): (REVIEW, "Customers +21.7% against revenue +1.2%: the figures are right, but receivables are small "
                             "for an airline (DSO 32 days); needs the ageing."),
    ("tap", "R30"): (TRUE, "The 2025 report itself states that the 2024 balance sheet is restated."),
    ("tap", "R25"): (TRUE, "Effective tax rate of 96.9% in FY25: tax of €66m on profit before tax of €68m."),
    ("tap", "R18"): (TRUE, "Published accounts carry no customer listing, ageing or facility agreements."),
    ("toyota-caetano", "R28"): (TRUE, "Other current liabilities are 21.5% of revenue; note 22 shows they include "
                                      "€48,078k of stock financing owed to Toyota Kreditbank."),
    ("toyota-caetano", "R11"): (REVIEW, "Fired on FY23 only (71.4%); 46.4% in FY25, under the 60% threshold for car "
                                        "distributors. Depends on the facility terms."),
    ("toyota-caetano", "R10"): (TRUE, "Operating cash flow was negative in FY23 and FY25; the three years together "
                                      "converted 23.6% of EBITDA."),
    ("toyota-caetano", "R04"): (TRUE, "Other income is 60.5% of FY25 EBITDA; note 33 gives the lines, including a "
                                      "disposal gain of €4,862k."),
    ("toyota-caetano", "R09"): (TRUE, "Inventory +25.8% against cost of sales +4.5% in FY25; DIO 98 to 118 days."),
    ("toyota-caetano", "R24"): (REVIEW, "Capex 0.42x and 0.32x of D&A: under-investment, or a fleet depreciated in D&A "
                                        "but bought outside capex? Needs the fixed asset register."),
    ("toyota-caetano", "R29"): (REVIEW, "€12,388k paid for 'financial investments' in FY23: may be acquisitions or "
                                        "other financial investments; needs the note."),
    ("toyota-caetano", "R27"): (TRUE, "D&A rose to €28,125k in FY24; note 5 explains it (a project's development "
                                      "costs fully amortised that year)."),
    ("toyota-caetano", "R25"): (REVIEW, "Effective tax rate of 33.3% in FY23; the gap is below materiality."),
    ("toyota-caetano", "R18"): (TRUE, "Published accounts carry no customer listing, ageing or facility agreements."),
    ("corticeira-amorim", "R11"): (TRUE, "67.6% and 56.3% of debt due within a year in FY23 and FY24; note 22 shows "
                                         "commercial paper and a bond, refinanced by FY25 (28.7%)."),
    ("corticeira-amorim", "R10"): (TRUE, "Operating cash was 14.9% of EBITDA in FY23, when stock was built; 155.3% in "
                                         "FY25, when it was released."),
    ("corticeira-amorim", "R04"): (REVIEW, "Other income is 12.4% of EBITDA; note 30 leaves its largest line "
                                           "(€7,051k) as an unexplained 'Outros'."),
    ("corticeira-amorim", "R24"): (REVIEW, "Capex 0.72x and 0.71x of D&A after 1.83x in FY23: a pause after heavy "
                                           "investment, or deferred maintenance?"),
    ("corticeira-amorim", "R18"): (TRUE, "Published accounts carry no customer listing, ageing or facility agreements."),
}
HEAD = ["Company", "Key", "Type", "Issue", "Severity", "Years", "Amount at stake (EUR k)", "What the amount is",
        "Evidence (figures and source)", "Evidence from the notes", "Deal implication (typical)",
        "Proposed classification (agent)", "Why (agent)", "YOUR DECISION", "YOUR COMMENT", "Reviewed on"]
WIDTHS = [20, 10, 14, 36, 9, 14, 14, 30, 70, 50, 24, 20, 60, 20, 40, 14]


def rows() -> list[list]:
    out = []
    for c in demo.CASES:
        a = demo.analysis(c)
        by_id = {r.rule.id: r for r in a.findings}
        for i in a.issues:
            r = by_id.get(i.key)
            proposed, why = PROPOSED.get((c.slug, i.key), ("", "")) if r else (
                "in adjusted net debt" if i.kind == "Net debt item" else "to assess", i.treatment)
            notes = (i.evidence_state + (f" by {i.evidence_note}. {i.evidence_text}" if i.evidence_note else ""))
            out.append([c.company, i.key, i.kind, i.title, i.severity or "–", r.years_text if r else fy(i.year),
                        i.amount, i.amount_label + (f" ({i.note})" if i.note else ""),
                        r.evidence if r else f"Balance sheet line(s): {i.source}", notes, i.implication, proposed, why,
                        None, None, None])
    return out


def main() -> None:
    kept = {}
    if OUT.exists():        # keep what the reviewer already wrote
        for row in load_workbook(OUT)["Review"].iter_rows(min_row=5, values_only=True):
            if row[0] and any(row[13:16]):
                kept[(row[0], row[1])] = row[13:16]
    wb = Workbook()
    ws = wb.active
    ws.title = "Review"
    ws["A1"] = "DD Assistant — review sheet for the findings on the three demo companies"
    ws["A1"].font = Font(bold=True, size=12)
    ws["A2"] = ("For each row, read the evidence, then choose YOUR DECISION (true positive: the figures show what the "
                "rule says and a reviewer would ask about it · known false alarm: the rule fires for a reason that is "
                "not a problem of the company · to review: it needs information the accounts do not give · not "
                "relevant) and add a comment. The yellow columns are yours: the agent does not fill them.")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A2:M2")
    ws.row_dimensions[2].height = 48
    yellow = PatternFill("solid", fgColor="FFF2CC")
    for c, h in enumerate(HEAD, 1):
        cell = ws.cell(4, c, h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0B3D91")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    data = rows()
    for n, row in enumerate(data, 5):
        row[13:16] = kept.get((row[0], row[1]), (None, None, None))
        for c, value in enumerate(row, 1):
            cell = ws.cell(n, c, value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if c == 7 and isinstance(value, (int, float)):
                cell.number_format = "#,##0"
            if c >= 14:
                cell.fill = yellow
    dv = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"N5:N{4 + len(data)}")
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[ws.cell(4, i).column_letter].width = w
    ws.freeze_panes = "E5"
    ws.auto_filter.ref = f"A4:P{4 + len(data)}"
    wb.save(OUT)
    findings = sum(r[2] == "Finding" for r in data)
    done = sum(bool(r[13]) for r in data)
    print(f"{OUT}: {len(data)} rows ({findings} findings, {len(data) - findings} net debt items); "
          f"{done} with a decision of the reviewer")


if __name__ == "__main__":
    main()
