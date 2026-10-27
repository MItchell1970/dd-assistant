"""Layer 3 — rule catalogue and red flag generation.

Each rule compares one metric with a threshold, year by year. If it fires in at least
one year it becomes a finding, with evidence (figures + data room source), a question for
management and the document to request. The AI never creates findings: it only explains
the ones produced here.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable

from .input_loader import CompanyData
from .metrics import Metrics

SEVERITIES = ("High", "Medium", "Low")


# ---------------------------------------------------------------- formatting
def xround(x, nd: int) -> str:
    """Same as Excel's ROUND(x; nd)&"": rounds half up and drops trailing zeros."""
    if not isinstance(x, (int, float)):
        raise TypeError("not a number")
    q = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    s = format(q.normalize(), "f")
    return "0" if s in ("-0", "") else s


def pct(x) -> str:  # 0.238 -> "23.8%"
    return xround(x * 100, 1) + "%"


def n0(x) -> str:   # 1415.2 -> "1415"
    return xround(x, 0)


def d1(x) -> str:   # 72.01 -> "72"
    return xround(x, 1)


def eur(x) -> str:  # 1415.2 -> "€1,415k" (inputs are in EUR thousands)
    v = int(Decimal(repr(float(x))).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return f"-€{-v:,}k" if v < 0 else f"€{v:,}k"


def fy(year: int) -> str:  # 2025 -> "FY25"
    return f"FY{str(year)[2:]}"


# ---------------------------------------------------------------- rules
@dataclass
class Rule:
    id: str
    area: str
    name: str
    test: str
    op: str            # ">", "<" or "abs>"
    limit: float
    limit_fmt: str     # pct, pp, days, eur, count
    metric: str
    severity: str      # High, Medium, Low
    focus: str         # what to investigate
    question: str      # question for management
    request: str       # document to request
    rationale: str     # why it matters for the buyer
    evidence: Callable[["Ctx"], str]

    def fires(self, value) -> str:
        """'Yes', 'No' or 'n/a' (no value)."""
        if not isinstance(value, (int, float)):
            return "n/a"
        if self.op == ">":
            hit = value > self.limit
        elif self.op == "<":
            hit = value < self.limit
        else:
            hit = abs(value) > self.limit
        return "Yes" if hit else "No"

    def limit_text(self) -> str:
        f = self.limit_fmt
        if f == "pct":
            return xround(self.limit * 100, 0) + "%"
        if f == "pp":
            return xround(self.limit, 10) + " pp"
        if f == "days":
            return xround(self.limit, 10) + " days"
        if f == "eur":
            return "€" + xround(self.limit, 10) + "k"
        return "more than " + xround(self.limit, 10)

    def rule_text(self) -> str:
        return f"{self.id} · {self.name} (threshold: {self.limit_text()})"


class Ctx:
    """Shortcuts to write the evidence: metrics, data and years."""

    def __init__(self, d: CompanyData, m: Metrics):
        self.d, self.m = d, m
        self.Y = d.pl_years[-3:]          # the three years analysed
        self.L = d.pl_years[-1]           # latest year
        self.P = d.pl_years[-2]           # prior year

    def g(self, key, year):
        return self.m[key].get(year)

    def yrs(self, key, f) -> str:
        return "; ".join(f"{fy(y)}: {f(self.g(key, y))}" for y in self.Y)

    def src(self, key) -> str:
        return self.d.sources.get(key, "")


def _r(*a, ev):
    return Rule(*a, evidence=ev)


RULES: list[Rule] = [
    _r("R01", "Revenue", "Customer concentration above threshold", "Largest customer revenue / total revenue",
       ">", 0.20, "pct", "top_share", "High",
       "Dependence on a single customer: risk of loss and of pricing pressure.",
       "Is there a long-term contract with this customer? What are the term, the pricing mechanism and any "
       "change-of-control provisions?",
       "Customer contract; monthly revenue and gross margin by customer",
       "Losing a key customer would materially affect value; a change-of-control clause could allow it to exit "
       "after completion.",
       ev=lambda c: f"Largest customer as % of revenue — {c.yrs('top_share', pct)} ({c.g('top_name', c.L)} in "
                    f"{fy(c.L)}). Source: {c.src('vendas')}; {c.d.clients_source} et seq."),
    _r("R02", "Revenue", "Material revenue from new customers",
       "Revenue from customers with no prior-year sales / total revenue", ">", 0.05, "pct", "new_share", "High",
       "Growth may come from a one-off sale rather than the recurring customer base.",
       "Are sales to this customer recurring? What are the nature and term of the contract, and what is expected "
       "for next year?",
       "Customer contract and invoices; order book",
       "A buyer pays for recurring revenue; a one-off sale inflates both growth and EBITDA.",
       ev=lambda c: f"New customers in {fy(c.L)}: {pct(c.g('new_share', c.L))} of revenue ({c.g('new_name', c.L)}, "
                    f"{eur(c.g('new_sales', c.L))}). Revenue growth: +{pct(c.g('g_vendas', c.L))}; excluding new "
                    f"customers: {pct(c.g('g_ex_new', c.L))}. Source: {c.d.clients_source} et seq."),
    _r("R03", "Margins", "Significant gross margin movement", "Gross margin, year-on-year change (pp)",
       "abs>", 3, "pp", "gm_pp", "High",
       "Changes in pricing, product mix or purchase costs.",
       "What drove the gross margin movement: selling prices, product mix, purchase costs or customer-specific "
       "discounts?",
       "Gross margin by customer and product line; price lists",
       "Every point of gross margin flows straight to EBITDA; if the shift is structural, forward EBITDA changes.",
       ev=lambda c: f"Gross margin — {c.yrs('gm', pct)} ({fy(c.L)} change: {d1(c.g('gm_pp', c.L))} pp). "
                    f"Source: {c.src('vendas')}; {c.src('cmv')}"),
    _r("R04", "Quality of earnings", "Material other income within EBITDA", "Other income / revenue",
       ">", 0.01, "pct", "or_share", "High",
       "One-off gains (asset disposals, grants, compensation) included in EBITDA.",
       "Please provide a breakdown of other income. Does it include disposal gains, grants or other "
       "non-recurring items?",
       "Other income ledger; supporting documents for material items",
       "A non-recurring gain within EBITDA inflates the price paid for something that will not recur.",
       ev=lambda c: "Other income — " + "; ".join(f"{fy(y)}: {eur(c.d.v('orend', y))}" for y in c.Y)
                    + f" ({pct(c.g('or_share', c.L))} of revenue; {pct(c.g('or_var', c.L))} year-on-year). "
                    f"Source: {c.src('orend')}"),
    _r("R05", "Quality of earnings", "Material management adjustments", "Management adjustments / reported EBITDA",
       ">", 0.10, "pct", "adj_pct", "High",
       "Whether the adjustments are genuinely non-recurring and supported by evidence.",
       "What evidence supports each adjustment, and why is each cost considered non-recurring?",
       "Invoices and contracts supporting each adjustment",
       "Adjusted EBITDA anchors the price; every unsupported adjustment transfers value from buyer to seller.",
       ev=lambda c: f"Adjustments as % of reported EBITDA — {c.yrs('adj_pct', pct)}. {fy(c.L)} EBITDA: reported "
                    f"{eur(c.g('ebitda', c.L))}, management-adjusted {eur(c.g('ebitda_adj', c.L))}. "
                    f"Source: {c.d.adjustments_source} et seq.; {c.src('vendas')}"),
    _r("R06", "Quality of earnings", "Recurring 'non-recurring' adjustment",
       "Number of adjustments present in all 3 years", ">", 0, "count", "adj_rec", "Medium",
       "Costs labelled non-recurring that recur in practice.",
       "Why does this cost appear every year, and what ensures it will not recur?",
       "Breakdown of the adjustment by year; plan and costs of the underlying programme",
       "A cost that recurs every year is a recurring cost and should not be added back to EBITDA.",
       ev=lambda c: f"{n0(c.g('adj_rec', c.L))} adjustment(s) appear in {fy(c.Y[0])}, {fy(c.Y[1])} and "
                    f"{fy(c.Y[2])} (e.g., {c.g('adj_rec_name', c.L)}). Source: {c.d.adjustments_source} et seq."),
    _r("R07", "Net working capital", "Receivables growing ahead of revenue",
       "Trade receivables growth − revenue growth (pp)", ">", 10, "pp", "cli_gap", "High",
       "Possible deterioration in collections or extended credit terms.",
       "How have payment terms and overdue balances evolved? Which customers drive the increase? Were credit "
       "terms extended?",
       "AR ageing at the last two year-ends; post year-end cash receipts",
       "Revenue that is not collected does not generate cash and may conceal future losses.",
       ev=lambda c: f"Receivables +{pct(c.g('g_cli', c.L))} vs. revenue +{pct(c.g('g_vendas', c.L))} in {fy(c.L)} "
                    f"(gap of {d1(c.g('cli_gap', c.L))} pp; {fy(c.P)}: {d1(c.g('cli_gap', c.P))} pp). "
                    f"DSO: {d1(c.g('dso', c.P))} → {d1(c.g('dso', c.L))} days. Source: {c.src('cli')}; {c.src('vendas')}"),
    _r("R08", "Net working capital", "Significant increase in DSO", "DSO, year-on-year change (days)",
       ">", 15, "days", "dso_var", "Medium",
       "Customers paying later.",
       "Why are customers paying later? Have credit terms changed?",
       "AR ageing; credit terms by customer",
       "Longer collection periods tie up cash and increase bad-debt risk.",
       ev=lambda c: f"DSO — {c.yrs('dso', d1)} days. Source: {c.src('cli')}; {c.src('vendas')}"),
    _r("R09", "Net working capital", "Inventory build ahead of COGS", "Inventory growth − COGS growth (pp)",
       ">", 10, "pp", "inv_gap", "Medium",
       "Slow-moving or obsolete stock; purchasing ahead of demand.",
       "What is the composition and ageing of inventory? Which orders support current stock levels? What is the "
       "provisioning policy?",
       "Inventory ageing; slow-moving items list; order book",
       "Idle stock ties up cash and may be worth less than its carrying value.",
       ev=lambda c: f"Inventory +{pct(c.g('g_inv', c.L))} vs. COGS +{pct(c.g('g_cmv', c.L))} in {fy(c.L)} "
                    f"(gap of {d1(c.g('inv_gap', c.L))} pp). DIO: {d1(c.g('dio', c.P))} → {d1(c.g('dio', c.L))} "
                    f"days. Source: {c.src('inv')}; {c.src('cmv')}"),
    _r("R10", "Cash generation", "Weak EBITDA-to-cash conversion", "Cash generated from operations / EBITDA",
       "<", 0.70, "pct", "conv", "High",
       "EBITDA that is not converting into cash.",
       "Why did EBITDA not convert into cash? Which working capital items explain the gap?",
       "EBITDA-to-cash bridge; monthly working capital schedule",
       "A buyer values the business on the cash it generates.",
       ev=lambda c: f"Cash conversion — {c.yrs('conv', pct)}. {fy(c.L)} operating cash flow: "
                    f"{eur(c.g('fco', c.L))}. Source: {c.src('cgo')}; {c.src('vendas')}"),
    _r("R11", "Debt", "Short-term debt concentration", "Current borrowings / gross financial debt",
       ">", 0.40, "pct", "st_share", "High",
       "Refinancing requirement within the next 12 months.",
       "Are facilities committed, or are refinancing negotiations under way? On what terms?",
       "Facility agreements; bank term sheets; covenant compliance certificates",
       "Without refinancing, the company may be unable to meet maturing debt.",
       ev=lambda c: f"Debt due within 12 months — {c.yrs('st_share', pct)} ({eur(c.d.v('fin_cp', c.L))} of "
                    f"{eur(c.g('debt', c.L))} in {fy(c.L)}). Source: {c.src('fin_cp')}; {c.src('fin_lp')}"),
    _r("R12", "Consistency", "Balance sheet does not balance", "Assets − (equity + liabilities)",
       "abs>", 1, "eur", "bs_diff", "High",
       "Error in the financial statements.", "Which version of the balance sheet is correct?",
       "Final trial balance and balance sheet",
       "A balance sheet that does not balance invalidates every analysis that relies on it.",
       ev=lambda c: f"Balance sheet difference — {c.yrs('bs_diff', eur)}. Source: balance sheet"),
    _r("R13", "Consistency", "Cash flow statement does not reconcile to balance sheet cash",
       "CFS closing cash − balance sheet cash", "abs>", 1, "eur", "cash_diff", "Medium",
       "Error in the cash flow statement or in the balance sheet.",
       "Which figure is correct? Is the cash flow statement the audited version? Are there other errors?",
       "Corrected cash flow statement; audit report",
       "A basic error casts doubt on the quality of all the financial information.",
       ev=lambda c: f"CFS closing cash − balance sheet cash — {c.yrs('cash_diff', eur)}. "
                    f"Source: {c.src('cx_fim')}; {c.src('caixa')}"),
    _r("R14", "Consistency", "CFS working capital movements do not reconcile to the balance sheet",
       "Sum of differences across the 5 working capital lines", "abs>", 1, "eur", "wc_diff", "Medium",
       "A cash flow line populated with an incorrect figure.",
       "What is the correct movement for each working capital line?",
       "Corrected cash flow statement; opening and closing trial balances",
       "If the cash flow statement is wrong, cash conversion is wrong too.",
       ev=lambda c: f"Difference between CFS and balance sheet working capital movements — "
                    f"{c.yrs('wc_diff', eur)}. Source: {c.src('d_cli')} to {c.src('d_opc')}"),
    _r("R15", "Consistency", "Net income inconsistent across statements",
       "Largest difference between P&L, balance sheet and CFS", "abs>", 1, "eur", "ni_diff", "High",
       "Statements taken from different versions of the accounts.",
       "What is the correct net income for each year?", "Final approved accounts",
       "Inconsistent statements may come from different versions of the accounts.",
       ev=lambda c: f"Net income difference — {c.yrs('ni_diff', eur)}. "
                    f"Source: {c.src('rl_dre')}; {c.src('rl_bs')}; {c.src('rl_dfc')}"),
    _r("R16", "Consistency", "Sales by customer do not reconcile to P&L revenue",
       "Sum of sales by customer − P&L revenue", "abs>", 1, "eur", "cl_diff", "Medium",
       "Incomplete customer listing, or a listing prepared on a different basis.",
       "Why does the sales-by-customer listing not reconcile to the P&L?",
       "Sales-by-customer extract reconciled to the general ledger",
       "Concentration analysis is only reliable if the listing reconciles to the accounts.",
       ev=lambda c: f"Sales by customer − P&L revenue — {c.yrs('cl_diff', eur)}. Source: {c.d.clients_source}"),
    _r("R17", "Consistency", "Debt schedule does not reconcile to the balance sheet",
       "Difference in total and current portion", "abs>", 1, "eur", "map_diff", "Medium",
       "Debt missing from the schedule or from the balance sheet.",
       "Which facilities explain the difference between the debt schedule and the balance sheet?",
       "Reconciled debt schedule; bank statements",
       "Unidentified debt reduces equity value one-for-one.",
       ev=lambda c: f"Debt schedule − balance sheet in {fy(c.L)}: {eur(c.g('map_diff', c.L))}. "
                    f"Source: {c.src('map_tot')}; {c.src('fin_cp')}"),
    _r("R18", "Information", "Key documents not provided", "Number of key documents not provided",
       ">", 0, "count", "docs_miss", "Medium",
       "Without these documents some findings can be neither confirmed nor ruled out.",
       "Could you please provide the outstanding documents?", "The documents listed in the evidence",
       "Missing information is a finding in itself: it limits what the buyer can verify.",
       ev=lambda c: f"{n0(c.g('docs_miss', c.L))} document(s) not provided: {c.g('docs_list', c.L)}. "
                    f"Source: data room review"),
    _r("R19", "Quality of earnings", "Disposal gains within EBITDA", "Disposal gains / reported EBITDA",
       ">", 0.05, "pct", "gain_pct", "High",
       "A non-recurring gain inflating EBITDA.",
       "Which assets were sold? Where was the gain recorded, and is it included in reported EBITDA?",
       "Sale agreement or deed; accounting entry for the gain",
       "A disposal gain does not recur; within EBITDA, the buyer would pay for it at the multiple.",
       ev=lambda c: f"Disposal gains — {c.yrs('gain', eur)} ({pct(c.g('gain_pct', c.L))} of {fy(c.L)} EBITDA). "
                    f"{fy(c.L)} EBITDA excluding these gains: {eur(c.g('ebitda_ex_gain', c.L))}. "
                    f"Source: {c.src('ganho_alien')}; {c.src('orend')}"),
    _r("R20", "Debt", "Limited covenant headroom", "1 − (net debt / EBITDA) / covenant limit",
       "<", 0.15, "pct", "cov_head", "High",
       "Risk of a covenant breach if comparable EBITDA is lower than reported.",
       "How does the facility agreement define covenant EBITDA? What headroom was reported at recent tests? "
       "Have any waivers been requested?",
       "Facility agreement; covenant compliance certificates",
       "A covenant breach can make the debt immediately repayable and shifts negotiating power to the lenders.",
       ev=lambda c: f"Net debt / EBITDA in {fy(c.L)}: {xround(c.g('nd_ebitda', c.L), 2)}x (limit "
                    f"{xround(c.g('cov_lim', c.L), 1)}x); headroom of {pct(c.g('cov_head', c.L))}. Minimum EBITDA "
                    f"to comply: {eur(c.g('ebitda_min', c.L))}. Excluding disposal gains, the ratio is "
                    f"{xround(c.g('nd_ebitda_ex', c.L), 2)}x. Source: {c.src('cov_lim')}; {c.src('fin_cp')}"),
]


@dataclass
class RuleResult:
    rule: Rule
    values: dict[int, object]
    fires: dict[int, str]
    evidence: str

    @property
    def alert(self) -> bool:
        return "Yes" in self.fires.values()

    @property
    def years_text(self) -> str:
        return ", ".join(fy(y) for y, f in self.fires.items() if f == "Yes")


def evaluate(d: CompanyData, m: Metrics, rules: list[Rule] = RULES) -> list[RuleResult]:
    """Apply every rule to the last three years and return the result of each."""
    ctx = Ctx(d, m)
    out = []
    for r in rules:
        values = {y: m[r.metric].get(y) for y in ctx.Y}
        fires = {y: r.fires(v) for y, v in values.items()}
        try:
            ev = r.evidence(ctx)
        except (TypeError, ValueError, ZeroDivisionError):
            ev = "See the Metrics sheet"   # like the spreadsheet's IFERROR
        out.append(RuleResult(r, values, fires, ev))
    return out


def alerts(results: list[RuleResult]) -> list[RuleResult]:
    """Only the rules that fired, in catalogue order."""
    return [r for r in results if r.alert]
