"""The findings expected on the real published accounts, each classified.

  true positive      the figures show what the rule says, and a reviewer would ask about it
  known false alarm  the rule fires for a reason that is not a problem of the company (a definition, a layout)
  to review          the figures are right, but whether it matters needs information the accounts do not give

Proposed by Claude Code from the published figures; not yet reviewed by Bernardo (state: proposed). Used by
tests/test_real_companies.py and scripts/validation_report.py (docs/VALIDATION.md).
"""
TRUE, FALSE_ALARM, REVIEW = "true positive", "known false alarm", "to review"
REVIEWED_BY = ""   # the reviewer's name once Bernardo has gone through the list (declared locally, no login)

FINDINGS = {
    "Toyota_Caetano_2024_published.xlsx": {
        "R04": (TRUE, "Other income is about half of EBITDA (51.5% FY23, 46.6% FY24): a breakdown is needed before "
                      "pricing on EBITDA."),
        "R10": (TRUE, "Operating cash was negative in FY23 (conversion −23.9%); the two years together converted 39%."),
        "R11": (REVIEW, "71.4% of debt due within a year in FY23: vehicle distributors finance stock with short-term "
                        "lines; whether it is a refinancing risk depends on the facility terms."),
        "R18": (TRUE, "Published accounts carry no customer listing, ageing or facility agreements."),
        "R24": (REVIEW, "Capex 0.62x and 0.42x of D&A: under-investment, or a rental fleet depreciated in D&A but "
                        "bought outside capex? Needs the fixed asset note."),
        "R27": (TRUE, "D&A grew 65.5% (€16,992k to €28,125k) against 9.5% for PP&E: found by a reviewer before the "
                      "rule existed (useful lives, right-of-use assets or the rental fleet)."),
        "R28": (TRUE, "Other current liabilities are €145,573k, 22% of revenue and seven times trade payables: "
                      "found by a reviewer; content unknown without the trial balance."),
        "R29": (REVIEW, "€12,388k paid for 'financial investments' in FY23 (SNC line): may be acquisitions, but the "
                        "line also holds other financial investments; needs the note."),
    },
    "TAP_2025_published.xlsx": {
        "R07": (REVIEW, "Customers (note 10, gross of impairment) grew 21.7% against revenue +1.2%; DSO 26.5 to 31.8 "
                        "days. Needs the AR ageing: the note gives the impairment for the whole caption only."),
        "R18": (TRUE, "Published accounts carry no customer listing, ageing or facility agreements."),
        "R22": (TRUE, "EBITDA covers interest 3.71x in FY25 and 3.23x in FY24; interest includes lease interest."),
        "R28": (REVIEW, "Other current liabilities, net of leases, tax and unused flight documents, are €630,699k "
                        "(14.8% of revenue): mostly accrued expenses and other payables (note 20)."),
    },
    "Corticeira_Amorim_2024_published.xlsx": {
        "R04": (REVIEW, "Other income is 11% of EBITDA: worth a breakdown, not a problem in itself."),
        "R10": (TRUE, "Cash conversion of 15% in FY23 (cork stock build); the two years together converted 44%."),
        "R11": (REVIEW, "56–68% of debt due within a year: commercial paper programmes are usually rolled; depends "
                        "on the programme terms."),
        "R18": (TRUE, "Published accounts carry no customer listing, ageing or facility agreements."),
    },
}


def counts() -> dict[str, int]:
    out = {TRUE: 0, FALSE_ALARM: 0, REVIEW: 0}
    for findings in FINDINGS.values():
        for kind, _ in findings.values():
            out[kind] += 1
    return out
