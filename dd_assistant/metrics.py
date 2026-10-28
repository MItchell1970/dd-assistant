"""Layer 2 — compute the metrics (deterministic, no AI).

Each metric is a dict {year: value}. None means "n/a": the prior year or the input is
missing. The formulas mirror the Métricas sheet of the Excel template; the parity test
(tests/test_parity.py) confirms both give the same numbers.
"""
from __future__ import annotations

from . import europe
from .input_loader import CompanyData

# Key -> display label (reports, app and AI material).
LABELS = {
    "vendas": "Revenue",
    "g_vendas": "Revenue growth",
    "new_sales": "Revenue from new customers",
    "new_share": "New customers (% of revenue)",
    "new_name": "Largest new customer",
    "g_ex_new": "Revenue growth excl. new customers",
    "top_share": "Largest customer (% of revenue)",
    "top_name": "Largest customer",
    "ex_top_new": "Revenue excl. largest and new customers",
    "g_ex_top_new": "Growth excl. largest and new customers",
    "gm": "Gross margin",
    "gm_pp": "Gross margin change",
    "ebitda": "Reported EBITDA",
    "ebitda_m": "EBITDA margin",
    "or_share": "Other income (% of revenue)",
    "or_var": "Other income growth",
    "gain": "Disposal gains within EBITDA",
    "gain_pct": "Disposal gains (% of EBITDA)",
    "ebitda_ex_gain": "EBITDA excl. disposal gains",
    "adj": "Management adjustments to EBITDA",
    "ebitda_adj": "Management-adjusted EBITDA",
    "adj_pct": "Adjustments (% of reported EBITDA)",
    "adj_rec": "'Non-recurring' adjustments in all 3 years",
    "adj_rec_name": "Example of recurring adjustment",
    "g_cli": "Trade receivables growth",
    "cli_gap": "Receivables vs. revenue growth gap",
    "dso": "DSO",
    "dso_var": "DSO change",
    "g_inv": "Inventory growth",
    "g_cmv": "COGS growth",
    "inv_gap": "Inventory vs. COGS growth gap",
    "dio": "DIO",
    "dpo": "DPO",
    "dpo_var": "DPO change",
    "cgo": "Cash generated from operations",
    "conv": "Cash conversion (operating cash / EBITDA)",
    "fco": "Operating cash flow",
    "fcf": "Free cash flow",
    "capex_pct": "Capex (% of revenue)",
    "debt": "Gross financial debt",
    "st_share": "Debt due within 12 months (% of total)",
    "net_debt": "Net debt",
    "nd_ebitda": "Net debt / EBITDA",
    "nd_ebitda_ex": "Net debt / EBITDA excl. disposal gains",
    "cov_lim": "Covenant limit (net debt / EBITDA)",
    "cov_head": "Covenant headroom",
    "ebitda_min": "Minimum EBITDA to meet covenant",
    "bs_diff": "Assets − (equity + liabilities)",
    "cash_diff": "CFS closing cash − balance sheet cash",
    "wc_diff": "Working capital movements: CFS vs. balance sheet",
    "ni_diff": "Net income: largest gap P&L / BS / CFS",
    "cl_diff": "Sales by customer − P&L revenue",
    "map_diff": "Debt schedule − balance sheet",
    "docs_miss": "Key documents not provided",
    "docs_list": "Documents not provided",
}

# Metrics beyond the Excel template (rules R21–R26). Kept apart: the parity test covers LABELS exactly.
EXTENDED_LABELS = {
    "int_cover": "Interest cover (EBITDA / interest expense)",
    "capex_da": "Capex / D&A",
    "capex_da_2y": "Capex / D&A, higher of the last two years",
    "etr": "Effective tax rate",
    "etr_gap": "Effective tax rate − statutory rate",
    "own_share": "Own work capitalised (% of EBITDA)",
}
ALL_LABELS = LABELS | EXTENDED_LABELS

# Key -> unit, used only to display the values (pct = decimal shown as %; eur = EUR k).
_UNIT_GROUPS = {
    "pct": "g_vendas new_share g_ex_new top_share g_ex_top_new gm ebitda_m or_share or_var gain_pct adj_pct "
           "g_cli g_inv g_cmv conv capex_pct st_share cov_head etr own_share",
    "pp": "gm_pp cli_gap inv_gap etr_gap",
    "days": "dso dso_var dio dpo dpo_var",
    "x": "nd_ebitda nd_ebitda_ex cov_lim int_cover capex_da capex_da_2y",
    "count": "adj_rec docs_miss",
    "text": "new_name top_name adj_rec_name docs_list",
}
UNITS = {k: unit for unit, keys in _UNIT_GROUPS.items() for k in keys.split()}
UNITS.update({k: "eur" for k in ALL_LABELS if k not in UNITS})

Metrics = dict[str, dict[int, object]]


def N(x) -> float:
    """Like Excel's N(): blank counts as 0."""
    return x if isinstance(x, (int, float)) else 0.0


def div(a, b):
    """Division that returns None instead of raising."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def growth(cur, prev):
    r = div(cur, prev)
    return None if r is None else r - 1


def sub(a, b):
    """Difference that returns None when either side is missing."""
    return None if a is None or b is None else a - b


def days(num, den):
    """num / den in days (DSO, DIO, DPO); None when a figure is missing."""
    r = div(num, den)
    return None if r is None else r * 365


# EBITDA lines: by nature (SNC, IFRS) or by function (opex_fn: R&D, SG&A, distribution, administrative);
# 'own' is own work capitalised (trabalhos para a própria entidade, aktivierte Eigenleistungen).
EBITDA_LINES = ["vendas", "cmv", "fse", "pess", "imp", "orend", "own", "ogast", "opex_fn"]


def ebitda_of(d: CompanyData, y: int) -> float:
    """Revenue less operating costs before D&A. By function, D&A sits inside cost of sales and the functions,
    so it is added back (EBITDA = operating profit + D&A from the cash flow statement)."""
    e = sum(N(d.v(k, y)) for k in EBITDA_LINES)
    return e - N(d.v("da", y)) if d.pl_format == "function" else e


def compute_metrics(d: CompanyData) -> Metrics:
    P = d.pl_years                      # years with a P&L
    B = d.bs_years                      # years with a balance sheet
    L = P[-1]                           # latest year
    prev = {y: (P[i - 1] if i > 0 else None) for i, y in enumerate(P)}
    prev_bs = {y: (B[B.index(y) - 1] if y in B and B.index(y) > 0 else None) for y in B}
    m: Metrics = {k: {} for k in ALL_LABELS}
    v = d.v

    def put(key, years, fn):
        for y in years:
            m[key][y] = fn(y)

    Pp = [y for y in P if prev[y] is not None]   # P&L years with a prior year

    # ---------------- Revenue
    put("vendas", P, lambda y: v("vendas", y))
    put("g_vendas", Pp, lambda y: growth(v("vendas", y), v("vendas", prev[y])))

    # customer metrics only when the data room has a sales-by-customer listing
    def new_by_client(y):
        p = prev[y]
        return [(c.name, N(c.values.get(y)))
                for c in d.clients if N(c.values.get(p)) == 0 and N(c.values.get(y)) > 0]

    if d.clients:
        put("new_sales", Pp, lambda y: sum(x for _, x in new_by_client(y)))
        put("new_share", Pp, lambda y: div(m["new_sales"][y], v("vendas", y)))

    def new_name(y):
        lst = new_by_client(y)
        if not lst:
            return "—"
        best = max(x for _, x in lst)
        return next(n for n, x in lst if x == best)

    if d.clients:
        put("new_name", Pp, new_name)
        put("g_ex_new", Pp, lambda y: growth(v("vendas", y) - m["new_sales"][y], v("vendas", prev[y])))

    def top(y):
        vals = [(c.name, N(c.values.get(y))) for c in d.clients]
        best = max(x for _, x in vals)
        return next(n for n, x in vals if x == best), best

    if d.clients:
        put("top_share", P, lambda y: div(top(y)[1], v("vendas", y)))
        put("top_name", P, lambda y: top(y)[0])
        put("ex_top_new", P, lambda y: v("vendas", y) - top(y)[1] - (m["new_sales"][y] if y in Pp else 0))
        put("g_ex_top_new", Pp, lambda y: growth(m["ex_top_new"][y], m["ex_top_new"][prev[y]]))

    # ---------------- Margins and quality of earnings
    put("gm", P, lambda y: None if v("cmv", y) is None else div(v("vendas", y) + v("cmv", y), v("vendas", y)))
    put("gm_pp", Pp, lambda y: None if (x := sub(m["gm"][y], m["gm"][prev[y]])) is None else x * 100)
    put("ebitda", P, lambda y: ebitda_of(d, y))
    put("ebitda_m", P, lambda y: div(m["ebitda"][y], v("vendas", y)))
    put("or_share", P, lambda y: div(v("orend", y), v("vendas", y)))
    put("or_var", Pp, lambda y: None if N(v("orend", prev[y])) == 0 else growth(v("orend", y), v("orend", prev[y])))
    put("gain", P, lambda y: -N(v("ganho_alien", y)))
    put("gain_pct", P, lambda y: None if m["ebitda"][y] <= 0 else m["gain"][y] / m["ebitda"][y])
    put("ebitda_ex_gain", P, lambda y: m["ebitda"][y] - m["gain"][y])
    if d.adjustments:   # only when management presents an adjusted EBITDA
        put("adj", P, lambda y: sum(N(a.values.get(y)) for a in d.adjustments))
        put("ebitda_adj", P, lambda y: m["ebitda"][y] + m["adj"][y])
        put("adj_pct", P, lambda y: None if m["ebitda"][y] <= 0 else m["adj"][y] / m["ebitda"][y])
    last3 = P[-3:]
    repeated = [a.name for a in d.adjustments if all(N(a.values.get(y)) != 0 for y in last3)]
    if len(P) >= 3 and d.adjustments:
        m["adj_rec"][L] = len(repeated)
        m["adj_rec_name"][L] = repeated[0] if repeated else "—"

    # ---------------- Net working capital
    Pb = [y for y in P if prev_bs.get(y) is not None]   # years with a prior-year balance sheet
    put("g_cli", Pb, lambda y: growth(v("cli", y), v("cli", prev_bs[y])))
    put("cli_gap", Pp, lambda y: None if m["g_cli"].get(y) is None or m["g_vendas"].get(y) is None
        else (m["g_cli"][y] - m["g_vendas"][y]) * 100)
    neg = lambda x: None if x is None else -x
    put("dso", P, lambda y: days(v("cli", y), v("vendas", y)))
    put("dso_var", Pp, lambda y: sub(m["dso"][y], m["dso"][prev[y]]))
    put("g_inv", Pb, lambda y: growth(v("inv", y), v("inv", prev_bs[y])))
    put("g_cmv", Pp, lambda y: growth(v("cmv", y), v("cmv", prev[y])))
    put("inv_gap", Pp, lambda y: None if m["g_inv"].get(y) is None or m["g_cmv"].get(y) is None
        else (m["g_inv"][y] - m["g_cmv"][y]) * 100)
    put("dio", P, lambda y: days(v("inv", y), neg(v("cmv", y))))
    put("dpo", P, lambda y: days(v("forn", y), neg(v("cmv", y))))
    put("dpo_var", Pp, lambda y: sub(m["dpo"][y], m["dpo"][prev[y]]))

    # ---------------- Cash generation
    put("cgo", P, lambda y: v("cgo", y))
    # cash generated from operations; when the statements do not present it (direct method), operating cash flow
    cash = lambda y: m["cgo"][y] if m["cgo"][y] is not None else v("fco", y)
    put("conv", P, lambda y: None if m["ebitda"][y] <= 0 or cash(y) is None else cash(y) / m["ebitda"][y])
    put("fco", P, lambda y: v("fco", y))
    put("fcf", P, lambda y: N(v("fco", y)) + N(v("capex", y)) + N(v("alien", y)))
    put("capex_pct", P, lambda y: div(-N(v("capex", y)), v("vendas", y)))

    # ---------------- Debt
    put("debt", B, lambda y: N(v("fin_lp", y)) + N(v("fin_cp", y)))
    put("st_share", B, lambda y: div(N(v("fin_cp", y)), m["debt"][y]))
    put("net_debt", B, lambda y: m["debt"][y] - N(v("caixa", y)))
    put("nd_ebitda", P, lambda y: None if m["ebitda"][y] <= 0 or y not in m["net_debt"]
        else m["net_debt"][y] / m["ebitda"][y])
    put("nd_ebitda_ex", P, lambda y: None if m["ebitda_ex_gain"][y] <= 0 or y not in m["net_debt"]
        else m["net_debt"][y] / m["ebitda_ex_gain"][y])
    lim = v("cov_lim", L)
    if lim:
        m["cov_lim"][L] = lim
        nd = m["nd_ebitda"].get(L)
        m["cov_head"][L] = None if nd is None else 1 - nd / lim
        m["ebitda_min"][L] = None if L not in m["net_debt"] else m["net_debt"][L] / lim

    # ---------------- Consistency (0 = everything reconciles)
    assets = ["aft", "oanc", "inv", "cli", "oac", "caixa"]
    liabs = ["cp", "fin_lp", "opnc", "forn", "fin_cp", "opc"]
    put("bs_diff", B, lambda y: sum(N(v(k, y)) for k in assets) - sum(N(v(k, y)) for k in liabs))
    put("cash_diff", P, lambda y: sub(v("cx_fim", y), v("caixa", y)))

    def wc(y):
        if all(v(k, y) is None for k in ("d_cli", "d_inv", "d_forn", "d_oac", "d_opc")):
            return None   # direct-method cash flow statement: no working capital movements to compare
        p = prev_bs[y]
        delta = lambda k: N(v(k, y)) - N(v(k, p))
        # assets: the CFS movement has the opposite sign to the balance sheet increase
        return (abs(N(v("d_cli", y)) + delta("cli")) + abs(N(v("d_inv", y)) + delta("inv"))
                + abs(N(v("d_forn", y)) - delta("forn")) + abs(N(v("d_oac", y)) + delta("oac"))
                + abs(N(v("d_opc", y)) - delta("opc")))

    put("wc_diff", Pb, wc)
    def ni(y):
        # the P&L may show net income in total and attributable to the group; the balance sheet often shows the latter
        pl = [x for x in (v("rl_dre", y), v("rl_grupo", y)) if x is not None]
        others = [x for x in (v("rl_bs", y), v("rl_dfc", y)) if x is not None]
        return None if not pl or not others else min(max(abs(p - x) for x in others) for p in pl)

    put("ni_diff", P, ni)
    if d.clients:
        put("cl_diff", P, lambda y: sum(N(c.values.get(y)) for c in d.clients) + N(d.other_clients.get(y)) - v("vendas", y))
    if v("map_tot", L) is not None:
        m["map_diff"][L] = abs(N(v("map_tot", L)) - m["debt"][L]) + abs(N(v("map_cur", L)) - N(v("fin_cp", L)))

    # ---------------- Information
    missing = [name for name, ok in d.documents if not ok]
    m["docs_miss"][L] = len(missing)
    m["docs_list"][L] = "; ".join(missing) if missing else "—"

    # ---------------- Beyond the template: credit, investment, tax and capitalised costs (R21–R26)
    put("int_cover", P, lambda y: None if not v("juros", y) else div(m["ebitda"][y], -v("juros", y)))
    put("capex_da", P, lambda y: None if v("capex", y) is None or not v("da", y) else div(-v("capex", y), -v("da", y)))
    put("capex_da_2y", Pp, lambda y: None if m["capex_da"][y] is None or m["capex_da"][prev[y]] is None
        else max(m["capex_da"][y], m["capex_da"][prev[y]]))

    def etr(y):   # profit before tax as published, else net income + tax
        tax = v("irc", y)
        pbt = v("pbt", y) if v("pbt", y) is not None else sub(v("rl_dre", y), tax)
        return None if tax is None or pbt is None or pbt <= 0 else -tax / pbt

    put("etr", P, etr)
    rate = (europe.get(d.country) or europe.COUNTRY_BY_CODE["EU"]).tax_rate
    put("etr_gap", P, lambda y: None if rate is None or m["etr"][y] is None else (m["etr"][y] - rate) * 100)
    put("own_share", P, lambda y: None if m["ebitda"][y] <= 0 else N(v("own", y)) / m["ebitda"][y])
    return m


# ---------------------------------------------------------------- reading checks
def reading_checks(d: CompanyData, tolerance: float = 1.0) -> list[dict]:
    """Did the agent read the statements correctly? Subtotals rebuilt from the lines it identified are
    compared with the subtotals the company published. A failed check means a line is missing or
    misclassified: correct it in the review table before relying on the analysis. (Different from the
    consistency rules R12–R17, which test the company's own figures.)"""
    checks = []

    def check(name, published_key, rebuilt):
        for y in d.pl_years:
            pub = d.v(published_key, y)
            if pub is None:
                continue
            value = rebuilt(y)
            checks.append({"Check": name, "Year": y, "Rebuilt from the lines": value, "As published": pub,
                           "Difference": value - pub, "OK": abs(value - pub) <= tolerance})

    check("Gross profit = revenue + cost of sales", "gp_pub", lambda y: N(d.v("vendas", y)) + N(d.v("cmv", y)))
    check("EBITDA = revenue less operating costs before D&A", "ebitda_pub", lambda y: ebitda_of(d, y))
    check("Operating profit = EBITDA − D&A", "opinc", lambda y: ebitda_of(d, y) + N(d.v("da", y)))
    if d.pl_format == "function":
        check("Operating expenses = sum of the functions", "opex_tot", lambda y: N(d.v("opex_fn", y)))
    return checks
