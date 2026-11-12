"""Detection benchmark by mutation: plant one known distortion at a time in real published accounts and count how
many the engine catches.

For each company of the demo (three years, its sector and country), every mutation below is applied to a copy of the
figures in memory; the published files are never changed. The table of mutations and the rule each one must trigger
was written by hand BEFORE the first run (docs/PROGRESS.md, Fase 3, B1); the thresholds were not tuned afterwards.

    python scripts\\detection_benchmark.py            # prints the result and writes docs/DETECTION.md

Result per (company, mutation):
  detected        the expected rule fires, and it did not fire for that year before the mutation
                  (for 'reading check': a check that passed now fails)
  missed          the expected rule does not fire
  already flagged the expected rule already fired for the latest year on the real accounts: the mutation cannot
                  show anything, so it is left out of the rate
  not applicable  the accounts lack the line the mutation needs
Mutations marked 'below materiality by design' are controls: the right answer is no new High or Medium finding.
"""
from __future__ import annotations

import copy
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dd_assistant import demo  # noqa: E402
from dd_assistant.input_loader import CompanyData, Named  # noqa: E402
from dd_assistant.metrics import compute_metrics  # noqa: E402
from dd_assistant.pipeline import Analysis, analyse  # noqa: E402

READING = "reading check"
NET_INCOME = ("rl_dre", "rl_grupo", "rl_bs", "rl_dfc")


class NotApplicable(Exception):
    """The accounts do not have the line this mutation needs."""


def _v(d: CompanyData, key: str, y: int) -> float:
    x = d.v(key, y)
    if x is None:
        raise NotApplicable(key)
    return x


def _add(d: CompanyData, key: str, y: int, delta: float) -> None:
    d.lines.setdefault(key, {})[y] = (d.v(key, y) or 0.0) + delta


def _through_pl(d: CompanyData, y: int, delta: float, operating: bool = True) -> None:
    """Carry a change of profit down the income statement, so the accounts stay consistent: the planted distortion
    is in the business, not in the reading."""
    for key in (("opinc", "ebitda_pub") if operating else ()) + ("pbt",) + NET_INCOME:
        if d.v(key, y) is not None:
            _add(d, key, y, delta)


def _ebitda(d: CompanyData, y: int) -> float:
    return compute_metrics(d)["ebitda"][y]


# ---------------------------------------------------------------- the mutations (L: latest year, P: prior year)
def receivables_up_25(d, L, P):
    _add(d, "cli", L, 0.25 * _v(d, "cli", L))


def inventories_up_30(d, L, P):
    _add(d, "inv", L, 0.30 * _v(d, "inv", L))


def half_of_long_debt_to_short(d, L, P):
    x = 0.5 * _v(d, "fin_lp", L)
    _add(d, "fin_lp", L, -x)
    _add(d, "fin_cp", L, x)


def disposal_gain_in_other_income(d, L, P):
    x = 0.10 * _ebitda(d, L)
    _add(d, "orend", L, x)
    d.lines.setdefault("ganho_alien", {})[L] = -x      # the cash flow statement shows the gain
    _through_pl(d, L, x)


def cash_flow_cash_does_not_reconcile(d, L, P):
    _add(d, "cx_fim", L, 0.05 * _v(d, "vendas", L))


def depreciation_halved(d, L, P):
    _add(d, "da", L, -0.5 * _v(d, "da", L))            # da is negative: half of it is removed; nothing else moves


def cost_line_dropped(d, L, P):
    _v(d, "fse", L)
    d.lines["fse"][L] = None


def recurring_one_off_adjustment(d, L, P):
    years = d.pl_years[-3:]
    if len(years) < 3:
        raise NotApplicable("three years")
    d.adjustments = list(d.adjustments) + [Named("Restructuring costs (non-recurring)",
                                                 {y: 0.04 * _ebitda(d, y) for y in years})]
    d.adjustments_source = d.adjustments_source or "planted"


def total_assets_up_1(d, L, P):
    _add(d, "tot_at", L, 0.01 * _v(d, "tot_at", L))


def balance_sheet_net_income_differs(d, L, P):
    _add(d, "rl_bs", L, 0.10 * abs(_v(d, "rl_bs", L)) + 100)


def interest_a_third_of_ebitda(d, L, P):
    target = -_ebitda(d, L) / 3
    delta = target - _v(d, "juros", L)
    _add(d, "juros", L, delta)
    _through_pl(d, L, delta, operating=False)


def no_income_tax(d, L, P):
    tax = _v(d, "irc", L)
    d.lines["irc"][L] = 0.0
    for key in NET_INCOME:
        if d.v(key, L) is not None:
            _add(d, key, L, -tax)


def capex_cut_70(d, L, P):
    for y in (P, L):
        _add(d, "capex", y, -0.7 * _v(d, "capex", y))


def other_income_from_revenue(d, L, P):
    x = 0.15 * _ebitda(d, L)
    _add(d, "orend", L, x)
    _add(d, "vendas", L, -x)


def borrowings_to_four_times_ebitda(d, L, P):
    m = compute_metrics(d)
    if m["net_debt"].get(L) is None:
        raise NotApplicable("net debt")
    _add(d, "fin_lp", L, 4.0 * m["ebitda"][L] - m["net_debt"][L])


def acquisition_paid(d, L, P):
    d.lines.setdefault("acq", {})[L] = -0.03 * _v(d, "vendas", L)


def own_work_capitalised(d, L, P):
    x = 0.08 * _ebitda(d, L)
    _add(d, "own", L, x)
    _add(d, "pess", L, -x)      # staff costs are negative: the cost stays, its capitalisation is shown as income


def payables_twenty_days_longer(d, L, P):
    _add(d, "forn", L, 20 / 365 * -_v(d, "cmv", L))


def cost_of_sales_up(d, L, P):
    x = 0.08 * _v(d, "vendas", L)
    _add(d, "cmv", L, -x)
    _through_pl(d, L, -x)


def receivables_up_3(d, L, P):
    _add(d, "cli", L, 0.03 * _v(d, "cli", L))


def cash_two_thousand_out(d, L, P):
    _add(d, "cx_fim", L, 2.0)


@dataclass(frozen=True)
class Mutation:
    key: str
    what: str                 # the distortion, in words
    expected: str             # the rule that must fire, or 'reading check', or '' for a control
    apply: Callable
    control: bool = False     # below materiality by design: no new High or Medium finding is the right answer


# Written by hand before the first run. Do not edit the expected column to match a result.
MUTATIONS = (
    Mutation("M01", "Trade receivables 25% higher at the latest year-end", "R07", receivables_up_25),
    Mutation("M02", "Inventories 30% higher at the latest year-end", "R09", inventories_up_30),
    Mutation("M03", "Half of the non-current borrowings moved to current", "R11", half_of_long_debt_to_short),
    Mutation("M04", "A disposal gain of 10% of EBITDA recorded in other income", "R19", disposal_gain_in_other_income),
    Mutation("M05", "Closing cash of the cash flow statement off by 5% of revenue", "R13",
             cash_flow_cash_does_not_reconcile),
    Mutation("M06", "Depreciation halved, operating profit left as published", READING, depreciation_halved),
    Mutation("M07", "The external services cost line dropped", READING, cost_line_dropped),
    Mutation("M08", "A 'non-recurring' adjustment of 4% of EBITDA in each of the three years", "R06",
             recurring_one_off_adjustment),
    Mutation("M09", "Total assets 1% higher than equity and liabilities", "R12", total_assets_up_1),
    Mutation("M10", "Net income in the balance sheet different from the income statement", "R15",
             balance_sheet_net_income_differs),
    Mutation("M11", "Interest expense raised to a third of EBITDA", "R22", interest_a_third_of_ebitda),
    Mutation("M12", "No income tax charge in the latest year", "R25", no_income_tax),
    Mutation("M13", "Capex cut by 70% in the last two years", "R24", capex_cut_70),
    Mutation("M14", "15% of EBITDA moved from revenue to other income", "R04", other_income_from_revenue),
    Mutation("M15", "Borrowings raised until net debt is 4x EBITDA", "R21", borrowings_to_four_times_ebitda),
    Mutation("M16", "An acquisition of 3% of revenue paid in the cash flow statement", "R29", acquisition_paid),
    Mutation("M17", "Own work of 8% of EBITDA capitalised out of staff costs", "R26", own_work_capitalised),
    Mutation("M18", "Trade payables 20 days of cost of sales higher", "R23", payables_twenty_days_longer),
    Mutation("M19", "Cost of sales higher by 8% of revenue", "R03", cost_of_sales_up),
    Mutation("C01", "Trade receivables 3% higher (control)", "", receivables_up_3, control=True),
    Mutation("C02", "Closing cash of the cash flow statement off by €2k (control)", "", cash_two_thousand_out,
             control=True),
)


# What changed in the engine because of this benchmark, and what did not. Kept by hand, never rewritten.
HISTORY = (
    "- **First run, 11 November 2026:** 48 of 49 detected; 5 of 6 controls correct. Control C02 on Corticeira Amorim "
    "(closing cash off by €2k) raised R13 as Medium: the overdraft reconciliation was all-or-nothing, so a €2k "
    "error left the whole €29,451k difference unexplained.\n"
    "- **12 November 2026, with the reviewer's approval:** R13 changed. A line that explains at least 90% of the "
    "cash difference now leaves only the remainder unexplained; the remainder still fires when above €1k. Rerun: "
    "6 of 6 controls correct, the same 48 of 49.\n"
    "- **Not changed:** R23 on TAP (M18). The rule compares DPO year on year, and TAP's real DPO fell 96 days, "
    "which hides 20 planted days. The planted amount is about €12m, below TAP's balance sheet materiality of "
    "€43m. It stays in the rate as a miss.")


def _fired(a: Analysis) -> dict[str, set[int]]:
    return {r.rule.id: {y for y, f in r.fires.items() if f == "Yes"} for r in a.results if r.alert}


def run_one(case: demo.Case, base: Analysis, mutation: Mutation) -> dict:
    ext = copy.deepcopy(demo.extraction(case))
    d = ext.data
    L, P = d.pl_years[-1], d.pl_years[-2]
    out = {"company": case.company, "mutation": mutation.key, "what": mutation.what, "expected": mutation.expected,
           "control": mutation.control, "new_alerts": []}
    try:
        mutation.apply(d, L, P)
    except NotApplicable as e:
        return {**out, "result": "not applicable", "detail": f"no '{e}' line in these accounts"}
    a = analyse(ext, case.sector, case.country, purpose=case.purpose)
    before, after = _fired(base), _fired(a)
    new = sorted(k for k in after if after[k] - before.get(k, set()))
    severity = {r.rule.id: r.rule.severity for r in a.findings}
    if mutation.control:
        serious = [k for k in new if severity.get(k) in ("High", "Medium")]
        out.update(result="no alert, as expected" if not serious else "false alert",
                   new_alerts=new, detail=", ".join(f"{k} {severity.get(k)}" for k in new))
        return out
    if mutation.expected == READING:
        failed = [c for c in a.checks if not c["OK"]]
        out.update(result="detected" if base.checks_ok and failed else "missed",
                   new_alerts=new, detail=f"{len(failed)} of {len(a.checks)} reading checks fail")
        return out
    e = mutation.expected
    out["new_alerts"] = [k for k in new if k != e]
    if L in before.get(e, set()):
        out.update(result="already flagged", detail=f"{e} fires for FY{str(L)[2:]} on the real accounts")
    elif after.get(e, set()) - before.get(e, set()):
        out.update(result="detected", detail=f"{e} {severity.get(e, '')}".strip())
    else:
        value = next((r.values.get(L) for r in a.results if r.rule.id == e), None)
        limit = next((r.rule.limit_text() for r in a.results if r.rule.id == e), "")
        shown = f"{value:.4g}" if isinstance(value, (int, float)) else "n/a"
        out.update(result="missed", detail=f"{e} value {shown} against threshold {limit}")
    return out


def run() -> list[dict]:
    rows = []
    for case in demo.CASES:
        base = demo.analysis(case)
        rows += [run_one(case, base, m) for m in MUTATIONS]
    return rows


def summary(rows: list[dict]) -> dict:
    tests = [r for r in rows if not r["control"]]
    scored = [r for r in tests if r["result"] in ("detected", "missed")]
    controls = [r for r in rows if r["control"]]
    return {"planted": len(tests), "scored": len(scored),
            "detected": sum(r["result"] == "detected" for r in scored),
            "missed": sum(r["result"] == "missed" for r in scored),
            "already_flagged": sum(r["result"] == "already flagged" for r in tests),
            "not_applicable": sum(r["result"] == "not applicable" for r in tests),
            "unexpected_alerts": sum(len(r["new_alerts"]) for r in tests),
            "controls": len(controls), "controls_ok": sum(r["result"].startswith("no alert") for r in controls)}


def markdown(rows: list[dict]) -> str:
    s = summary(rows)
    rate = f"{s['detected'] / s['scored']:.0%}" if s["scored"] else "n/a"
    out = ["# Detection benchmark by mutation", "",
           "Generated by `scripts/detection_benchmark.py`. One known distortion at a time is planted in a copy of the "
           "published figures of the three demo companies (three years, each with its sector and country), and the "
           "engine is run. The expected rule of each mutation was written before the first run and no threshold was "
           "changed afterwards. The published files are never changed.", "",
           f"**Detected: {s['detected']} of {s['scored']} planted distortions ({rate}).** Missed: {s['missed']}. "
           f"Left out of the rate: {s['already_flagged']} where the rule already fired on the real accounts, and "
           f"{s['not_applicable']} where the accounts lack the line. Other rules that newly fired alongside: "
           f"{s['unexpected_alerts']}. Controls below materiality by design: {s['controls_ok']} of {s['controls']} "
           "raised no High or Medium finding.", "",
           "What this measures: whether a distortion of this size, planted in real accounts, trips the rule built "
           "for it. What it does not measure: distortions nobody thought of, smaller ones, or several at once.", ""]
    out += ["## History", "", HISTORY, ""]
    missed = [r for r in rows if r["result"] in ("missed", "false alert")]
    out += ["## Not detected", ""]
    out += [f"- **{r['company']}, {r['mutation']}** ({r['what']}): expected {r['expected'] or 'no alert'}; "
            f"{r['detail']}." for r in missed] or ["None."]
    out += ["", "## Every run", "", "| Company | Mutation | Distortion planted | Expected | Result | Detail | "
            "Other new alerts |", "|---|---|---|---|---|---|---|"]
    out += [f"| {r['company']} | {r['mutation']} | {r['what']} | {r['expected'] or 'none (control)'} | {r['result']} | "
            f"{r['detail']} | {', '.join(r['new_alerts']) if not r['control'] else '—'} |" for r in rows]
    return "\n".join(out) + "\n"


def main() -> None:
    rows = run()
    text = markdown(rows)
    (ROOT / "docs" / "DETECTION.md").write_text(text, encoding="utf-8")
    s = summary(rows)
    print(f"detected {s['detected']} of {s['scored']}; missed {s['missed']}; already flagged {s['already_flagged']}; "
          f"not applicable {s['not_applicable']}; other new alerts {s['unexpected_alerts']}; controls "
          f"{s['controls_ok']} of {s['controls']}")
    for r in rows:
        if r["result"] in ("missed", "false alert", "not applicable"):
            print(f"  {r['result']:15} {r['company'][:14]:14} {r['mutation']} {r['what'][:55]:55} {r['detail']}")


if __name__ == "__main__":
    main()
