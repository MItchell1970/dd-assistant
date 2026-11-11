"""Layer 3b — materiality, the amount at stake of each finding, and what it typically means for the deal.

The rules (rules.py) stay as they are: they say whether a ratio passed a threshold, exactly like the Excel template.
This layer adds what a financial due diligence report adds on top:

- an **amount at stake** in euros for each finding, computed from the lines that made it fire (never estimated);
- a **materiality threshold**, visible and editable: 5% of reported EBITDA for earnings items and 1% of revenue for
  balance sheet items by default. A finding below it is Low, with the note 'below materiality';
- one list of **key issues**, findings and net debt items together, ordered by amount;
- a **deal implication** for each, by rule and editable by the reviewer: price (EBITDA, net debt, working capital),
  SPA protection, further diligence or post-deal. Typical treatment only; never legal advice or a view on price.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from . import notes as notes_
from .deal import DealView
from .input_loader import CompanyData
from .metrics import Metrics
from .rules import SEVERITIES, RuleResult, fy

NOT_QUANTIFIABLE = "not quantifiable from the accounts"
BELOW = "below materiality"
DISCLAIMER = "Typical treatment; for the deal team and its lawyers to decide."
IMPLICATIONS = ("Price: EBITDA", "Price: net debt", "Price: working capital / peg", "SPA protection",
                "Further diligence", "Post-deal")


@dataclass(frozen=True)
class Materiality:
    """Share of reported EBITDA (earnings items) and of revenue (balance sheet items), latest year."""
    pl_pct: float = 0.05
    bs_pct: float = 0.01

    def thresholds(self, d: CompanyData, m: Metrics) -> dict[str, float | None]:
        L = d.pl_years[-1]
        revenue, ebitda = d.v("vendas", L), m["ebitda"].get(L)
        bs = abs(revenue) * self.bs_pct if revenue else None
        pl = ebitda * self.pl_pct if isinstance(ebitda, (int, float)) and ebitda > 0 else bs   # no EBITDA: revenue
        return {"pl": pl, "bs": bs}

    def text(self) -> str:
        return (f"{self.pl_pct:.0%} of reported EBITDA for earnings items; {self.bs_pct:.0%} of revenue for balance "
                "sheet items")


# ---------------------------------------------------------------- amount at stake, by rule
def _prev(d: CompanyData, y: int) -> int | None:
    earlier = [x for x in d.years if x < y]
    return earlier[-1] if earlier else None


def _growth(a, b):
    return None if a is None or not b else a / b - 1


def _recurring_adjustments(d: CompanyData, y: int) -> float | None:
    years = d.pl_years[-3:]
    rec = [a for a in d.adjustments if len(years) == 3 and all(a.values.get(x) for x in years)]
    return sum(abs(a.values[y]) for a in rec) if rec else None


def _tax_gap(d: CompanyData, m: Metrics, y: int) -> float | None:
    etr, gap, tax = m["etr"].get(y), m["etr_gap"].get(y), d.v("irc", y)
    if not etr or gap is None or tax is None:
        return None
    return abs(gap) / 100 * (-tax / etr)   # the gap in points × profit before tax


# rule ID -> (basis, what the amount is, function(d, m, y, p, rule) -> EUR thousands or None)
AMOUNTS = {
    "R01": ("pl", "revenue from the largest customer", lambda d, m, y, p, r: m["top_share"][y] * d.v("vendas", y)),
    "R02": ("pl", "revenue from new customers", lambda d, m, y, p, r: m["new_sales"][y]),
    "R03": ("pl", "gross margin movement × revenue", lambda d, m, y, p, r: abs(m["gm_pp"][y]) / 100 * d.v("vendas", y)),
    "R04": ("pl", "other income within EBITDA", lambda d, m, y, p, r: d.v("orend", y)),
    "R05": ("pl", "management adjustments", lambda d, m, y, p, r: abs(m["adj"][y])),
    "R06": ("pl", "adjustments present in all three years", lambda d, m, y, p, r: _recurring_adjustments(d, y)),
    "R07": ("bs", "receivables above the level implied by revenue growth",
            lambda d, m, y, p, r: d.v("cli", y) - d.v("cli", p) * (1 + m["g_vendas"][y])),
    "R08": ("bs", "increase in DSO × daily revenue", lambda d, m, y, p, r: m["dso_var"][y] / 365 * d.v("vendas", y)),
    "R09": ("bs", "inventory above the level implied by cost of sales growth",
            lambda d, m, y, p, r: d.v("inv", y) - d.v("inv", p) * (1 + m["g_cmv"][y])),
    "R10": ("pl", "operating cash short of the threshold share of EBITDA",
            lambda d, m, y, p, r: (r.limit - m["conv"][y]) * m["ebitda"][y]),
    "R11": ("bs", "borrowings due within 12 months", lambda d, m, y, p, r: d.v("fin_cp", y)),
    "R12": ("bs", "difference between assets and equity plus liabilities", lambda d, m, y, p, r: abs(m["bs_diff"][y])),
    "R13": ("bs", "unexplained difference in closing cash", lambda d, m, y, p, r: abs(m["cash_diff_unexpl"][y])),
    "R14": ("bs", "working capital movements not reconciled", lambda d, m, y, p, r: abs(m["wc_diff"][y])),
    "R15": ("pl", "difference in net income between statements", lambda d, m, y, p, r: abs(m["ni_diff"][y])),
    "R16": ("pl", "customer listing less P&L revenue", lambda d, m, y, p, r: abs(m["cl_diff"][y])),
    "R17": ("bs", "debt schedule less balance sheet debt", lambda d, m, y, p, r: abs(m["map_diff"][y])),
    "R19": ("pl", "disposal gains within EBITDA", lambda d, m, y, p, r: m["gain"][y]),
    "R20": ("bs", "net financial debt under the covenant", lambda d, m, y, p, r: m["net_debt"][y]),
    "R21": ("bs", "net financial debt above the leverage threshold",
            lambda d, m, y, p, r: m["net_debt"][y] - r.limit * m["ebitda"][y]),
    "R22": ("pl", "interest expense", lambda d, m, y, p, r: -d.v("juros", y)),
    "R23": ("bs", "increase in DPO × daily cost of sales", lambda d, m, y, p, r: m["dpo_var"][y] / 365 * -d.v("cmv", y)),
    "R24": ("pl", "capex short of depreciation", lambda d, m, y, p, r: abs(d.v("da", y)) - abs(d.v("capex", y))),
    "R25": ("pl", "tax at the gap between the effective and the statutory rate",
            lambda d, m, y, p, r: _tax_gap(d, m, y)),
    "R26": ("pl", "own work capitalised", lambda d, m, y, p, r: d.v("own", y)),
    "R27": ("pl", "D&A above the level implied by the growth of fixed assets",
            lambda d, m, y, p, r: abs(d.v("da", y)) - abs(d.v("da", p)) * (1 + _growth(d.v("aft", y), d.v("aft", p)))),
    "R28": ("bs", "largest 'other' current line", lambda d, m, y, p, r: m["other_wc"][y] * d.v("vendas", y)),
    "R29": ("bs", "acquisitions of businesses paid", lambda d, m, y, p, r: -d.v("acq", y)),
    "R30": ("bs", "largest restated line", lambda d, m, y, p, r: m["restated_max"][y]),
}

# rule ID -> (implication, the typical treatment in one sentence)
TREATMENT = {
    "R01": ("SPA protection", "Change-of-control and key-customer terms are usually covered by a condition or a "
                              "warranty."),
    "R02": ("Price: EBITDA", "One-off revenue and its margin are usually taken out of the EBITDA that is priced."),
    "R03": ("Further diligence", "A margin bridge by price, volume and mix comes before any EBITDA adjustment."),
    "R04": ("Price: EBITDA", "Other income that is not recurring is usually taken out of the EBITDA that is priced."),
    "R05": ("Price: EBITDA", "An adjustment without support is usually reversed in the EBITDA that is priced."),
    "R06": ("Price: EBITDA", "A cost that recurs every year is usually put back into EBITDA."),
    "R07": ("Price: working capital / peg", "Overdue or disputed receivables are usually taken out of normal "
                                            "working capital, or provided for."),
    "R08": ("Price: working capital / peg", "A longer collection period changes the normal level of working "
                                            "capital used for the peg."),
    "R09": ("Price: working capital / peg", "A stock build at year-end is usually normalised in the peg; slow-moving "
                                            "stock may need a provision."),
    "R10": ("Further diligence", "An EBITDA-to-cash bridge is needed before the weak conversion is priced."),
    "R11": ("Further diligence", "Maturities, renewal terms and change-of-control clauses of the facilities are "
                                 "reviewed before signing."),
    "R12": ("Further diligence", "The statements are tied out before any figure is relied on."),
    "R13": ("Price: net debt", "The definition of cash in the SPA decides whether overdrafts and restricted cash "
                               "count."),
    "R14": ("Further diligence", "The cash flow statement is reconciled to the balance sheet before it is used."),
    "R15": ("Further diligence", "The statements are tied out before any figure is relied on."),
    "R16": ("Further diligence", "The customer listing is reconciled to revenue before concentration is assessed."),
    "R17": ("Price: net debt", "Debt missing from the schedule is usually added to net debt."),
    "R18": ("Further diligence", "The documents are requested; what stays missing is usually covered by warranties."),
    "R19": ("Price: EBITDA", "Disposal gains are non-recurring and are usually taken out of the EBITDA that is "
                             "priced."),
    "R20": ("SPA protection", "A covenant near its limit is usually handled by a waiver, a refinancing condition "
                              "or a repayment at closing."),
    "R21": ("Price: net debt", "Net debt is deducted from enterprise value one for one; the financing structure is "
                               "reset at closing."),
    "R22": ("Further diligence", "Rates, hedging and the post-deal financing structure are reviewed."),
    "R23": ("Price: working capital / peg", "Payables stretched at year-end are usually normalised in the peg, or "
                                            "treated as debt-like when overdue."),
    "R24": ("Post-deal", "Deferred investment is a cash need for the buyer's plan; it may also be argued in the "
                         "price."),
    "R25": ("SPA protection", "Tax exposures are usually covered by a tax indemnity; a rate that will not last "
                              "changes forecast cash tax."),
    "R26": ("Price: EBITDA", "Capitalised own costs are tested; unsupported amounts are usually put back as costs."),
    "R27": ("Further diligence", "The depreciation policy and the asset register are reviewed; EBIT and capex needs "
                                 "may change."),
    "R28": ("Price: working capital / peg", "The line is broken down: operating items go into the peg, debt-like "
                                            "items into net debt."),
    "R29": ("Further diligence", "Growth is split into like-for-like and acquired before it is extrapolated."),
    "R30": ("Further diligence", "The restatement is reconciled and explained before trends are read; a corrected "
                                 "error is usually covered by the accounts warranty."),
}


def amount_at_stake(r: RuleResult, d: CompanyData, m: Metrics) -> tuple[float | None, str, str, int | None]:
    """(amount in EUR thousands or None, what it is, basis 'pl' or 'bs', the year) for a rule that fired."""
    fired = [y for y, f in r.fires.items() if f == "Yes"]
    spec = AMOUNTS.get(r.rule.id)
    if not fired or spec is None:
        return None, NOT_QUANTIFIABLE, "", max(fired) if fired else None
    basis, label, fn = spec
    y = max(fired)
    try:
        amount = fn(d, m, y, _prev(d, y), r.rule)
    except (TypeError, KeyError, ZeroDivisionError):
        amount = None
    if not isinstance(amount, (int, float)) or amount <= 0:
        return None, NOT_QUANTIFIABLE, basis, y
    return float(amount), label, basis, y


def apply(results: list[RuleResult], d: CompanyData, m: Metrics, materiality: Materiality,
          implications: dict[str, str] | None = None, notes: list | None = None, money=None,
          raw: dict | None = None) -> list[RuleResult]:
    """Each fired rule with its amount, its materiality and its deal implication. A finding whose amount is below
    the threshold becomes Low ('below materiality'); one that cannot be quantified keeps the rule's severity."""
    limits = materiality.thresholds(d, m)
    out = []
    for r in results:
        if not r.alert:
            out.append(r)
            continue
        amount, label, basis, year = amount_at_stake(r, d, m)
        limit = limits.get(basis)
        material = None if amount is None or limit is None else amount >= limit
        rule, note = r.rule, ""
        if material is False:
            note = f"{BELOW} ({materiality.pl_pct:.0%} of EBITDA)" if basis == "pl" else \
                f"{BELOW} ({materiality.bs_pct:.0%} of revenue)"
            rule = replace(rule, severity="Low")
        implication, treatment = TREATMENT.get(rule.id, ("Further diligence", ""))
        ev = notes_.for_finding(rule.id, year, notes, d, m, money, (raw or {}).get(year)) if notes else None
        out.append(replace(r, rule=rule, amount=amount, amount_label=label, amount_year=year, material=material,
                           note=note, base_severity=r.rule.severity,
                           implication=(implications or {}).get(rule.id, implication), treatment=treatment,
                           evidence_state=ev.state if ev else "", evidence_note=ev.note if ev else "",
                           evidence_text=ev.text if ev else "", next_request=ev.request if ev else ""))
    return out


def by_amount(findings: list[RuleResult]) -> list[RuleResult]:
    """Largest amount first; findings that cannot be quantified last, by severity."""
    return sorted(findings, key=lambda r: (r.amount is None, -(r.amount or 0), SEVERITIES.index(r.rule.severity)))


# ---------------------------------------------------------------- one list: findings and net debt items
@dataclass
class KeyIssue:
    key: str                  # rule ID, or 'ND: <category>' for a net debt item
    kind: str                 # Finding · Net debt item · To assess
    title: str
    severity: str             # High, Medium, Low; '' for a net debt item
    amount: float | None      # EUR thousands
    amount_label: str
    year: int | None
    material: bool | None
    note: str
    implication: str
    treatment: str
    question: str
    request: str
    source: str
    evidence_state: str = ""      # open · partly explained · explained ('' = no notes were read)
    evidence_note: str = ""
    evidence_text: str = ""


def _bridge_items(view: DealView, year: int) -> list[tuple[str, str, float, str, list]]:
    """(kind, category, signed amount, source) of the net debt bridge, one row per category. The lines an R28
    finding already covers are left out."""
    groups: dict[tuple[str, str], list] = {}
    kind = ""
    for ln in view.net_debt:
        if ln.style == "header":
            kind = "Net debt item" if ln.label.endswith("(included)") else \
                "To assess" if ln.label.startswith("To assess") else ""
            continue
        value = ln.values.get(year)
        if not kind or not value or ln.style not in ("item", "memo") or ln.label.startswith(("Memo:", "Adjusted")):
            continue
        if ln.note.startswith("Material 'other' line"):
            continue
        g = groups.setdefault((kind, ln.note or ln.label), [0.0, [], []])
        g[0] += value
        g[1].append(ln.source)
        g[2].append(abs(value))
    return [(k, cat, total, "; ".join(dict.fromkeys(s for s in src if s)), parts)
            for (k, cat), (total, src, parts) in groups.items()]


def key_issues(findings: list[RuleResult], view: DealView, d: CompanyData, m: Metrics, materiality: Materiality,
               implications: dict[str, str] | None = None, notes: list | None = None, money=None) -> list[KeyIssue]:
    """Findings and net debt items in one list, ordered by amount at stake (not quantifiable last)."""
    implications = implications or {}
    out = [KeyIssue(r.rule.id, "Finding", r.rule.name, r.rule.severity, r.amount, r.amount_label, r.amount_year,
                    r.material, r.note, r.implication, r.treatment, r.rule.question,
                    r.next_request or r.rule.request,
                    r.evidence.split("Source: ")[-1] if "Source: " in r.evidence else "",
                    r.evidence_state, r.evidence_note, r.evidence_text)
           for r in findings]
    B = view.bs_years[-1]
    limit = materiality.thresholds(d, m)["bs"]
    for kind, category, total, source, parts in _bridge_items(view, B):
        key = f"ND: {category}"
        included = kind == "Net debt item"
        nature = "cash-like" if total < 0 else "debt-like"
        default = "Price: net debt" if included else "Further diligence"
        treatment = (f"Included in adjusted net debt as a {nature} item: deducted from the price one for one, if the "
                     "SPA definition agrees." if included and total > 0 else
                     "Included in adjusted net debt as a cash-like item, if the SPA definition agrees." if included
                     else f"Not in adjusted net debt yet: to be classified as {nature}, working capital or neither.")
        material = None if limit is None else abs(total) >= limit
        ev = notes_.for_item(category, [abs(total)] + parts, B, notes, money) if notes else None
        out.append(KeyIssue(key, kind, category, "", abs(total), f"balance at {fy(B)}", B, material,
                            "" if material is not False else f"{BELOW} ({materiality.bs_pct:.0%} of revenue)",
                            implications.get(key, default), treatment,
                            f"Please provide the breakdown, terms and maturity of: {category.lower()}.",
                            (ev.request if ev and ev.request else
                             f"Schedule of {category.lower()} with supporting agreements"), source,
                            ev.state if ev else "", ev.note if ev else "", ev.text if ev else ""))
    order = lambda i: (i.amount is None, -(i.amount or 0), SEVERITIES.index(i.severity) if i.severity else 9)
    return sorted(out, key=order)
