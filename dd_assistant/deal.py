"""Layer 3b — Deal view: the numbers a deal team asks for first (deterministic, no AI).

  - Quality of earnings: reported EBITDA → management adjustments → diligence adjustments →
    diligence-adjusted EBITDA. The reviewer accepts or rejects each management adjustment and adds
    adjustments of their own. Adjustments not yet accepted are left out (a prudent buy-side view) and
    shown as the upside.
  - Net debt: financial debt − cash → debt-like and cash-like items found in the balance sheet →
    adjusted net debt. The reviewer decides which items to include.
  - Net working capital: by year-end, as % of revenue and in days, with the average of the year-ends
    as an indicative reference for the peg (a peg is set on monthly balances: request them).
  - Sector benchmarks: the company's ratios next to European listed peers (orientation, not a test).
  - Value at stake: what the adjustments mean in equity value at a multiple the user enters
    (illustrative, not a valuation; shown in the app, never sent to the AI).
Every line keeps its source. The AI never computes these numbers; it only reads them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import sectors
from .input_loader import CompanyData, Named
from .metrics import Metrics, N, div

ADJUSTMENT_STATES = ["Under review", "Accepted", "Rejected"]
_DISPOSAL = re.compile(r"aliena|disposal|gain on sale|mais.valia", re.I)


@dataclass
class Line:
    label: str
    values: dict[int, float | None] = field(default_factory=dict)
    style: str = "item"      # header, item, subtotal, total, memo
    source: str = ""
    note: str = ""
    unit: str = "money"      # money, pct, days, x


@dataclass
class DealView:
    pl_years: list[int]
    bs_years: list[int]
    qoe: list[Line]
    net_debt: list[Line]
    nwc: list[Line]
    ebitda: dict[int, float]                 # reported
    ebitda_mgmt: dict[int, float] | None     # as presented by management (None if not presented)
    ebitda_dd: dict[int, float]              # diligence-adjusted
    upside: dict[int, float]                 # management adjustments still under review (not included)
    net_debt_reported: dict[int, float]
    net_debt_adjusted: dict[int, float]
    nwc_values: dict[int, float]
    nwc_average: float | None


def _neg(values: dict) -> dict:
    return {y: None if v is None else -v for y, v in values.items()}


def deal_view(d: CompanyData, m: Metrics, decisions: dict[str, str] | None = None,
              analyst: list[Named] | None = None, include: dict[int, bool] | None = None) -> DealView:
    """decisions: management adjustment name -> Accepted / Rejected / Under review (default).
    analyst: the reviewer's own adjustments to EBITDA. include: balance item index -> included in net debt."""
    decisions, analyst, include = decisions or {}, analyst or [], include or {}
    v = d.v
    Y = d.pl_years[-3:]
    B = [y for y in d.bs_years if y >= Y[0] - 1][-4:] or d.bs_years[-1:]
    src = d.sources.get

    # ---------------- quality of earnings
    rep = {y: m["ebitda"][y] for y in Y}
    qoe = [Line("Reported EBITDA", rep, "total", "Income statement lines (see Source data)")]
    mgmt = None
    if d.adjustments:
        qoe.append(Line("Management adjustments", style="header"))
        for a in d.adjustments:
            qoe.append(Line(a.name, {y: N(a.values.get(y)) for y in Y}, source=d.adjustments_source,
                            note=decisions.get(a.name, "Under review")))
        mgmt = {y: rep[y] + sum(N(a.values.get(y)) for a in d.adjustments) for y in Y}
        qoe.append(Line("Management-adjusted EBITDA", mgmt, "subtotal", d.adjustments_source))
    header = len(qoe)
    qoe.append(Line("Diligence adjustments", style="header"))
    dd = dict(mgmt or rep)
    upside = {y: 0.0 for y in Y}
    for a in d.adjustments:
        status = decisions.get(a.name, "Under review")
        if status == "Accepted":
            continue
        reverse = {y: -N(a.values.get(y)) for y in Y}
        qoe.append(Line(f"Reverse: {a.name}", reverse, source=d.adjustments_source,
                        note="rejected by the reviewer" if status == "Rejected" else
                        "not accepted yet: support requested"))
        for y in Y:
            dd[y] += reverse[y]
            if status != "Rejected":
                upside[y] -= reverse[y]
    gains = {y: -m["gain"][y] for y in Y}
    if any(gains.values()) and not any(_DISPOSAL.search(a.name) for a in d.adjustments):
        qoe.append(Line("Remove disposal gains within EBITDA", gains, source=src("ganho_alien", ""),
                        note="non-recurring (R19)"))
        for y in Y:
            dd[y] += gains[y]
    for a in analyst:
        vals = {y: N(a.values.get(y)) for y in Y}
        qoe.append(Line(a.name, vals, note="analyst adjustment"))
        for y in Y:
            dd[y] += vals[y]
    if len(qoe) == header + 1:
        qoe[header] = Line("Diligence adjustments: none identified from the data provided", style="header")
    qoe.append(Line("Diligence-adjusted EBITDA", dd, "total"))
    qoe.append(Line("Diligence-adjusted EBITDA margin", {y: div(dd[y], v("vendas", y)) for y in Y}, "memo",
                    unit="pct"))
    if any(upside.values()):
        qoe.append(Line("Upside if the adjustments under review are accepted", upside, "memo"))
    if any(N(v("sbc", y)) for y in Y):
        qoe.append(Line("Memo: share-based compensation in EBITDA (non-cash; kept as an operating cost)",
                        {y: v("sbc", y) for y in Y}, "memo", src("sbc", "")))

    # ---------------- net debt
    debt = {y: m["debt"][y] for y in B}
    reported = {y: m["net_debt"][y] for y in B}
    nd = [Line("Non-current borrowings", {y: v("fin_lp", y) for y in B}, source=src("fin_lp", "")),
          Line("Current borrowings", {y: v("fin_cp", y) for y in B}, source=src("fin_cp", "")),
          Line("Gross financial debt", debt, "subtotal"),
          Line("Cash and cash equivalents", _neg({y: v("caixa", y) for y in B}), source=src("caixa", "")),
          Line("Reported net debt", reported, "subtotal")]
    adjusted = dict(reported)
    included = [(i, b) for i, b in enumerate(d.balance_items) if include.get(i, b.include)]
    assess = [(i, b) for i, b in enumerate(d.balance_items) if not include.get(i, b.include)]
    for nature, title in (("debt", "Debt-like items (included)"), ("cash", "Cash-like items (included)")):
        chosen = [b for _, b in included if b.nature == nature]
        if chosen:
            nd.append(Line(title, style="header"))
        for b in chosen:
            vals = {y: N(b.values.get(y)) * (1 if nature == "debt" else -1) for y in B}
            nd.append(Line(f"{b.label} ({b.kind.replace('noncurrent', 'non-current') or 'balance sheet'})", vals,
                           source=b.source, note=b.category))
            for y in B:
                adjusted[y] += vals[y]
    nd.append(Line("Adjusted net debt", adjusted, "total"))
    nd.append(Line("Adjusted net debt / diligence-adjusted EBITDA",
                   {y: div(adjusted[y], dd[y]) if dd.get(y, 0) > 0 else None for y in B if y in dd}, "memo", unit="x"))
    if assess:
        nd.append(Line("To assess (not included)", style="header"))
        for _, b in assess:
            sign = 1 if b.nature == "debt" else -1
            nd.append(Line(f"{b.label} ({b.kind.replace('noncurrent', 'non-current') or 'balance sheet'})",
                           {y: None if b.values.get(y) is None else sign * b.values[y] for y in B}, "memo",
                           b.source, b.category))

    # ---------------- net working capital
    trade = {y: N(v("inv", y)) + N(v("cli", y)) - N(v("forn", y)) for y in B}
    nwc = {y: trade[y] + N(v("oac", y)) - N(v("opc", y)) for y in B}
    wc = [Line("Inventories", {y: v("inv", y) for y in B}, source=src("inv", "")),
          Line("Trade receivables", {y: v("cli", y) for y in B}, source=src("cli", "")),
          Line("Trade payables", _neg({y: v("forn", y) for y in B}), source=src("forn", "")),
          Line("Trade working capital", trade, "subtotal"),
          Line("Other current assets", {y: v("oac", y) for y in B}, source=src("oac", "")),
          Line("Other current liabilities", _neg({y: v("opc", y) for y in B}), source=src("opc", ""))]
    for _, b in included:   # an item counted in net debt leaves working capital (no double count)
        if b.in_nwc:
            vals = {y: N(b.values.get(y)) * (1 if b.nature == "debt" else -1) for y in B}
            wc.append(Line(f"Excluded: {b.label} (in net debt)", vals, source=b.source))
            for y in B:
                nwc[y] += vals[y]
    wc.append(Line("Net working capital", nwc, "total"))
    wc.append(Line("NWC as % of revenue", {y: div(nwc[y], v("vendas", y)) for y in B}, "memo", unit="pct"))
    wc.append(Line("NWC in days of revenue", {y: None if (r := div(nwc[y], v("vendas", y))) is None else r * 365
                                              for y in B}, "memo", unit="days"))
    average = sum(nwc.values()) / len(nwc) if nwc else None
    L = B[-1]
    if len(B) >= 2:
        wc.append(Line(f"Average of the {len(B)} year-ends (indicative peg reference)", {L: average}, "memo",
                       note="a peg is set on 12–24 monthly balances: request them"))
        gap = nwc[L] - average
        wc.append(Line("Latest year-end less the average", {L: gap}, "memo",
                       note="below the average: check whether working capital was run down before the sale" if gap < 0
                       else "above the average: structural (growth) or a temporary build-up of receivables or stock?"))
    return DealView(Y, B, qoe, nd, wc, rep, mgmt, dd, upside, reported, adjusted, nwc, average)


# ---------------------------------------------------------------- sector benchmarks
_HINTS = {   # metric -> (threshold for a notable difference, if higher than peers, if lower than peers)
    "gross_margin": (0.05, "Higher than peers: check the mix, supplier rebates and costs classified below gross "
                           "profit.", "Lower than peers: check pricing power and purchase costs."),
    "ebitda_margin": (0.03, "Higher than peers: test sustainability (one-offs, related-party pricing, owner "
                            "costs).", "Lower than peers: check the cost base and scale."),
    "receivables_sales": (0.05, "Slower collection than peers: check credit terms, overdue balances and "
                                "recoverability.", "Faster collection than peers: check for factoring or "
                                                   "unusual year-end collections."),
    "inventory_sales": (0.05, "More stock than peers: check ageing and obsolescence.",
                        "Less stock than peers: check consignment stock or year-end destocking."),
    "payables_sales": (0.05, "Longer supplier credit than peers: check overdue payables and reverse factoring "
                             "(confirming).", "Shorter supplier credit than peers: tighter terms or room to "
                                              "improve cash."),
    "nwc_sales": (0.05, "More working capital than peers: cash tied up in the business.",
                  "Less working capital than peers: check whether year-end balances were managed down."),
    "capex_da": (0.3, "Investing more than peers relative to D&A: split growth from maintenance capex.",
                 "Investing less than peers relative to D&A: check for under-investment to catch up after the deal."),
    "debt_ebitda": (1.0, "More leverage than peers: check covenants and refinancing.", "Less leverage than peers."),
}


def benchmark_rows(d: CompanyData, m: Metrics, view: DealView, sector: str | sectors.Sector | None) -> list[dict]:
    """The company's latest ratios next to the sector's European listed peers."""
    s = sectors.get(sector)
    v, L = d.v, d.pl_years[-1]
    ebitda = m["ebitda"][L]
    company = {
        "gross_margin": m["gm"].get(L), "ebitda_margin": m["ebitda_m"].get(L),
        "receivables_sales": div(v("cli", L), v("vendas", L)), "inventory_sales": div(v("inv", L), v("vendas", L)),
        "payables_sales": div(v("forn", L), v("vendas", L)), "nwc_sales": div(view.nwc_values.get(L), v("vendas", L)),
        "capex_da": div(-N(v("capex", L)), -N(v("da", L))) if v("capex", L) is not None else None,
        "debt_ebitda": div(m["debt"].get(L), ebitda) if ebitda > 0 and L in m["debt"] else None,
    }
    rows = []
    for key, (label, unit) in sectors.BENCHMARK_LABELS.items():
        mine, peer = company[key], s.benchmarks[key]
        gap, hi, lo = _HINTS[key]
        reading = "" if mine is None else hi if mine - peer > gap else lo if peer - mine > gap else "In line with peers."
        rows.append({"key": key, "Metric": label, "unit": unit, "Company": mine, "Sector": peer, "Reading": reading})
    return rows


def value_at_stake(view: DealView, multiple: float) -> list[tuple[str, float | None]]:
    """Illustrative only: the equity value the diligence adjustments represent at the multiple entered."""
    L, B = view.pl_years[-1], view.bs_years[-1]
    base = (view.ebitda_mgmt or view.ebitda)[L]
    ebitda_gap = view.ebitda_dd[L] - base
    debt_gap = -(view.net_debt_adjusted[B] - view.net_debt_reported[B])
    return [("EBITDA presented by the seller", base), ("Diligence-adjusted EBITDA", view.ebitda_dd[L]),
            (f"EBITDA difference × {multiple:g}x", ebitda_gap * multiple),
            ("Debt-like items less cash-like items (one for one)", debt_gap),
            ("Equity value at stake", ebitda_gap * multiple + debt_gap)]
