"""Bridge charts: one model and one SVG renderer for the site, the Streamlit app and the slides.

The engine (deal.py) gives the steps of a bridge; this module only decides how they are shown:
- colour by the effect on the buyer, not by the arithmetic sign (net debt: an increase is worse; cash and EBITDA:
  a decrease is worse), the largest item in full colour and the others at 45%, totals in grey;
- at most seven columns: items below 1% of the largest total go into "Others", capex and disposal proceeds become
  net capex, then intermediate subtotals are left out, and the smallest items join "Others"; every grouped column
  keeps its parts and their values in its full name;
- an action title and an annotation built by rule from the engine's figures (tested against the memo material),
  a technical subtitle, and a note when the rounded items do not add up to the rounded total.
No figure is computed here except sums of the engine's steps, each listed with its parts.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field

from .units import _round

# the single palette (site, app, charts, slides)
BG, CARD, TEXT, MUTED, LINE = "#0d1117", "#161b22", "#e6edf3", "#8b949e", "#30363d"
RED, GREEN, GREY = "#f85149", "#3fb950", "#8b949e"
FADE = 0.45            # the items other than the largest
MAX_COLUMNS = 7
SMALL = 0.01           # an item below 1% of the largest total goes into "Others"
E = html.escape

SHORT = {   # names under the columns; the full name stays in the column's title and aria-label
    "Reported EBITDA": "Reported EBITDA", "Change in net working capital": "Working capital",
    "Tax, interest and other operating items": "Tax & interest",
    "Working capital, tax and other operating items": "WC, tax & interest", "Operating cash flow": "Operating cash flow",
    "Capex": "Capex", "Proceeds from asset disposals": "Disposals", "Free cash flow": "Free cash flow",
    "Lease payments": "Lease payments", "Lease payments (cash flow statement)": "Lease payments",
    "Free cash flow after leases": "FCF after leases", "EBITDA before IFRS 16": "EBITDA pre-IFRS 16",
    "Borrowings less cash": "Net debt (ex-leases)", "Post-employment benefit obligations": "Pensions",
    "Lease liabilities": "Leases", "Income tax payable": "Tax payable", "Adjusted net debt": "Adjusted net debt",
    "Diligence-adjusted EBITDA": "Adjusted EBITDA", "Net capex": "Net capex", "Others": "Others"}
# what a title calls the largest item ("Leases take net debt from …")
NOUN = {"Lease liabilities": "Leases", "Post-employment benefit obligations": "Pensions",
        "Income tax payable": "Tax payable", "Change in net working capital": "Working capital",
        "Tax, interest and other operating items": "Tax and interest", "Capex": "Capex", "Net capex": "Net capex",
        "Lease payments": "Lease payments", "Lease payments (cash flow statement)": "Lease payments"}


@dataclass
class Column:
    label: str            # full name (title, aria-label)
    value: float          # EUR thousands, from the engine (or the sum of its parts)
    kind: str             # "total" or "delta"
    effect: str = ""      # "worse" or "better" for the buyer (items only)
    lead: bool = False    # the largest item, in full colour
    parts: list = field(default_factory=list)   # (label, value) of a grouped column

    @property
    def short(self) -> str:
        return SHORT.get(self.label, self.label)


@dataclass
class Bridge:
    kind: str             # "net debt", "cash" or "ebitda"
    title: str            # action title: the conclusion with its main figure
    subtitle: str         # technical: "Net debt bridge, FY25 (€m)"
    columns: list[Column]
    annotation: str = ""  # next to the final total
    note: str = ""        # rounding

    def text(self, money, c: Column) -> str:
        """The value shown on a column: signed for items, unsigned for totals, with a typographic minus."""
        s = money.fmt(c.value)
        if c.kind == "delta" and c.value > 0:
            s = "+" + s
        return s.replace("-€", "−€")


# ---------------------------------------------------------------- grouping
def _segments(cols: list[Column]) -> list[list[int]]:
    """Indexes of the items between two totals."""
    out, cur = [], []
    for i, c in enumerate(cols):
        if c.kind == "total":
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def _merge(cols: list[Column], idx: list[int], label: str) -> list[Column]:
    """Replace the items at idx (all in one segment) by one column at the place of the last of them."""
    parts = [p for i in idx for p in (cols[i].parts or [(cols[i].label, cols[i].value)])]
    merged = Column(label, sum(v for _, v in parts), "delta", parts=parts)
    keep = [c for i, c in enumerate(cols) if i not in idx[:-1]]
    keep[keep.index(cols[idx[-1]])] = merged
    return keep


def group(steps: list[tuple[str, float, str]]) -> list[Column]:
    cols = [Column(label, value, kind) for label, value, kind in steps]
    totals = [abs(c.value) for c in cols if c.kind == "total"] or [1.0]
    limit = SMALL * max(totals)
    names = [c.label for c in cols]                             # 1. disposal proceeds next to capex: net capex,
    if "Capex" in names and "Proceeds from asset disposals" in names:   # when too many columns or a small item
        i, j = names.index("Capex"), names.index("Proceeds from asset disposals")
        if j == i + 1 and (len(cols) > MAX_COLUMNS or abs(cols[j].value) < limit):
            cols = _merge(cols, [i, j], "Net capex")
    for seg in reversed(_segments(cols)):                       # 2. items below 1% of the largest total
        small = [i for i in seg if abs(cols[i].value) < limit]
        if small:
            cols = _merge(cols, small, "Others")
    while len(cols) > MAX_COLUMNS:                              # 3. intermediate subtotals, earliest first
        inner = [i for i, c in enumerate(cols) if c.kind == "total" and 0 < i < len(cols) - 1]
        if not inner:
            break
        cols.pop(inner[0])
    while len(cols) > MAX_COLUMNS:                              # 4. the smallest items join "Others"
        seg = max(_segments(cols), key=len)
        if len(seg) < 2:
            break
        two = sorted(sorted(seg, key=lambda i: abs(cols[i].value))[:2])
        cols = _merge(cols, two, "Others")
    return cols


def _style(cols: list[Column], worse_if_up: bool) -> None:
    items = [c for c in cols if c.kind == "delta"]
    for c in items:
        c.effect = "worse" if (c.value > 0) == worse_if_up else "better"
    if items:
        max(items, key=lambda c: abs(c.value)).lead = True


def _rounding(cols: list[Column], money) -> str:
    r = lambda v: _round(v / 1000 if money.millions else v)
    running, diff = None, 0
    for c in cols:
        if c.kind == "total":
            if running is not None and r(c.value) != running:
                diff = max(diff, abs(r(c.value) - running))
            running = r(c.value)
        elif running is not None:
            running += r(c.value)
    unit = "m" if money.millions else "k"
    return f"Differences of {money.symbol}{diff}{unit} are due to rounding." if diff else ""


def _unit(money) -> str:
    return f"{money.symbol}{'m' if money.millions else 'k'}"


def make(steps, money, kind: str, subtitle: str, title: str, annotation: str = "") -> Bridge | None:
    if len(steps) < 2:
        return None
    cols = group(steps)
    _style(cols, worse_if_up=kind == "net debt")
    return Bridge(kind, title, subtitle, cols, annotation, _rounding(cols, money))


# ---------------------------------------------------------------- the three bridges of a company, with their titles
def _noun(c: Column) -> str:
    return NOUN.get(c.label, c.short)


def net_debt(a, year: int | None = None) -> Bridge | None:
    from .deal import net_debt_steps
    from .rules import fy
    v, f = a.view, a.money.fmt
    B = year or v.bs_years[-1]
    L = v.pl_years[-1]
    steps = net_debt_steps(v, B)
    if len(steps) < 2:
        return None
    start, end = steps[0][1], steps[-1][1]
    items = [s for s in steps if s[2] == "delta"]
    m = lambda x: f(x).replace("-€", "−€")
    if items:
        lead = max(items, key=lambda s: abs(s[1]))
        noun = NOUN.get(lead[0], lead[0])
        if abs(lead[1]) >= 0.5 * abs(end - start):
            title = f"{noun} {'take' if noun.endswith('s') else 'takes'} net debt from {m(start)} to {m(end)}"
        else:
            title = f"Debt-like items take net debt from {m(start)} to {m(end)}"
    else:
        title = f"Net debt is {m(end)}; no debt-like item is included"
    ebitda = v.ebitda_dd.get(L)
    annotation = f"{end / ebitda:.2f}x EBITDA" if ebitda and ebitda > 0 and end > 0 else ""
    return make(steps, a.money, "net debt", f"Net debt bridge, {fy(B)} ({_unit(a.money)})", title, annotation)


def cash(a, year: int | None = None) -> Bridge | None:
    from .deal import cash_steps
    from .rules import fy
    v, f, d = a.view, a.money.fmt, a.data
    L = year or v.pl_years[-1]
    steps = cash_steps(v, d, a.metrics, L)
    if len(steps) < 2:
        return None
    m = lambda x: f(x).replace("-€", "−€")
    values = {label: value for label, value, _ in steps}
    ebitda, fcf, final = steps[0][1], values.get("Free cash flow"), steps[-1][1]
    if "Free cash flow after leases" in values:
        title = f"After lease payments, free cash flow is {m(final)}"
    elif fcf is not None and fcf > ebitda:
        title = f"Free cash flow of {m(fcf)} exceeds EBITDA of {m(ebitda)}"
    else:
        title = f"Of {m(ebitda)} of EBITDA, {m(fcf)} becomes free cash flow"
    conv = a.metrics["conv"].get(L) if "conv" in a.metrics else None
    annotation = f"Cash conversion {conv * 100:.1f}%".replace("-", "−") if conv is not None else ""
    return make(steps, a.money, "cash", f"From EBITDA to free cash flow, {fy(L)} ({_unit(a.money)})", title,
                annotation)


def qoe(a, year: int | None = None) -> Bridge | None:
    """Reported EBITDA to diligence-adjusted EBITDA (None when there is no adjustment to show)."""
    from .deal import qoe_steps
    from .rules import fy
    v, f = a.view, a.money.fmt
    L = year or v.pl_years[-1]
    m = lambda x: f(x).replace("-€", "−€")
    steps = qoe_steps(v, L)
    if len(steps) <= 2:
        return None
    return make(steps, a.money, "ebitda", f"EBITDA bridge, {fy(L)} ({_unit(a.money)})",
                f"Diligence adjustments take EBITDA from {m(steps[0][1])} to {m(steps[-1][1])}")


def ifrs16(a, year: int | None = None) -> Bridge | None:
    """Reported EBITDA, less the lease payments of the cash flow statement, to EBITDA before IFRS 16."""
    from .deal import ifrs16_steps
    from .rules import fy
    v, f = a.view, a.money.fmt
    L = year or v.pl_years[-1]
    m = lambda x: f(x).replace("-€", "−€")
    steps = ifrs16_steps(v, a.data, L)
    if len(steps) < 2:
        return None
    return make(steps, a.money, "ebitda", f"EBITDA before and after lease payments, {fy(L)} ({_unit(a.money)})",
                f"Lease payments cut EBITDA from {m(steps[0][1])} to {m(steps[-1][1])}",
                f"IFRS 16 adds {m(-steps[1][1])} to EBITDA")


def ebitda(a, year: int | None = None) -> Bridge | None:
    """The EBITDA chart of a company: the diligence adjustments if there are any, otherwise the lease effect."""
    return qoe(a, year) or ifrs16(a, year)


def all_bridges(a) -> dict[str, Bridge]:
    out = {"ebitda": ebitda(a), "net debt": net_debt(a), "cash": cash(a)}
    return {k: b for k, b in out.items() if b is not None}


# ---------------------------------------------------------------- SVG (site and app)
CSS = f"""
.ddc{{background:{CARD};border:1px solid {LINE};border-radius:12px;padding:20px 20px 16px;color:{TEXT};
font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.ddc-title{{font-size:1.05rem;line-height:1.35;font-weight:600;color:{TEXT};margin:0}}
.ddc-sub{{font-size:.78rem;color:{MUTED};margin:4px 0 14px}}
.ddc-scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}}
.ddc svg{{display:block;width:100%;height:auto;overflow:visible}}
.ddc svg text{{font-family:inherit;font-variant-numeric:tabular-nums;fill:{TEXT}}}
.ddc svg text.val{{font-size:12px;font-weight:700}}
.ddc svg text.lbl{{font-size:12px;fill:{MUTED}}}
.ddc svg text.ann{{font-size:12px;fill:{MUTED};font-weight:600}}
.ddc svg text.axis{{font-size:12px;fill:{MUTED}}}
.ddc svg rect.total{{fill:{GREY}}}
.ddc svg rect.worse{{fill:{RED}}}
.ddc svg rect.better{{fill:{GREEN}}}
.ddc svg rect.fade{{opacity:{FADE}}}
.ddc svg line.link{{stroke:{LINE};stroke-width:1;stroke-dasharray:3 3;shape-rendering:crispEdges}}
.ddc svg line.zero{{stroke:{MUTED};stroke-width:1;opacity:.6;shape-rendering:crispEdges}}
.ddc-foot{{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;color:{MUTED};font-size:.75rem;margin-top:10px}}
.ddc-foot i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}}
"""


def _two_lines(text: str, width: int = 11) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    if len(lines[-1]) > width + 3:
        lines[-1] = lines[-1][:width + 2].rstrip() + "…"
    return lines


def full_name(b: Bridge, money, c: Column) -> str:
    name = f"{c.label}: {b.text(money, c)}"
    if c.parts:
        name += " (" + "; ".join(f"{label} {money.fmt(value).replace('-€', '−€')}" for label, value in c.parts) + ")"
    if c.effect:
        name += f", {c.effect} for the buyer"
    return name


def svg(b: Bridge, money, check: str = "") -> str:
    """The bridge as HTML: action title, subtitle, the SVG, legend and rounding note. The SVG scales with its
    viewBox but never below the width at which its smallest text is 11 px; below that it slides sideways.
    `check` marks the block for the site's figure test (data-check); grouped sums are marked data-nocheck, since
    they are sums of figures listed in their title, not figures of the material."""
    cols = b.columns
    rows, level = [], 0.0
    for c in cols:
        start, end = (0.0, c.value) if c.kind == "total" else (level, level + c.value)
        level = end
        rows.append((c, start, end))
    lo = min([0.0] + [min(s, e) for _, s, e in rows])
    hi = max([0.0] + [max(s, e) for _, s, e in rows])
    span = (hi - lo) or 1.0
    LEFT, SLOT, TOP, PLOT, BELOW, LH = 26, 74, 44, 190, 40, 14
    BAR = round(SLOT * 0.6)
    W, H = LEFT + len(rows) * SLOT + 6, TOP + PLOT + BELOW + 2 * LH + 8
    y = lambda v: TOP + (hi - v) / span * PLOT
    out = [f'<div class="ddc"{f" data-check={chr(34)}{check}{chr(34)}" if check else ""}>'
           f'<p class="ddc-title">{E(b.title)}</p><p class="ddc-sub">{E(b.subtitle)}</p>'
           f'<div class="ddc-scroll"><svg viewBox="0 0 {W} {H}" style="min-width:{W * 11 / 12:.0f}px;'
           f'max-width:{W * 1.25:.0f}px" role="group" aria-label="{E(b.title)}">']
    if lo < 0:
        out.append(f'<line class="zero" x1="{LEFT - 4}" x2="{W}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>'
                   f'<text class="axis" data-nocheck="1" x="{LEFT - 8}" y="{y(0) + 4:.1f}" text-anchor="end">0</text>')
    for i, (c, start, end) in enumerate(rows):
        x = LEFT + i * SLOT + (SLOT - BAR) / 2
        cx = x + BAR / 2
        top, bottom = y(max(start, end)), y(min(start, end))
        if bottom - top < 6:                     # minimum visible height, grown away from the connector
            if c.value >= 0 or c.kind == "total":
                top = bottom - 6 if c.kind == "total" and c.value >= 0 else top
                bottom = top + 6
            else:
                top = bottom - 6
        cls = "total" if c.kind == "total" else c.effect + ("" if c.lead else " fade")
        below = c.value < 0
        ty = bottom + 15 if below else top - 7
        name = full_name(b, money, c)
        nocheck = ' data-nocheck="1"' if len(c.parts) > 1 else ""
        names = "".join(f'<tspan x="{cx:.1f}" dy="{0 if k == 0 else LH}">{E(s)}</tspan>'
                        for k, s in enumerate(_two_lines(c.short)))
        out.append(f'<g role="img" aria-label="{E(name)}"><title>{E(name)}</title>'
                   f'<rect class="{cls}" x="{x:.1f}" y="{top:.1f}" width="{BAR}" height="{bottom - top:.1f}" rx="3"/>'
                   f'<text class="val"{nocheck} x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle">{E(b.text(money, c))}</text>'
                   f'<text class="lbl" x="{cx:.1f}" y="{TOP + PLOT + BELOW + LH - 2}" text-anchor="middle">{names}</text>')
        if i == len(rows) - 1 and b.annotation:      # top right, above the final total, clear of every value
            out.append(f'<text class="ann" x="{W - 6}" y="14" text-anchor="end">{E(b.annotation)}</text>')
        out.append("</g>")
        if i < len(rows) - 1:
            out.append(f'<line class="link" x1="{x + BAR:.1f}" x2="{x + SLOT:.1f}" y1="{y(end):.1f}" y2="{y(end):.1f}"/>')
    out.append("</svg></div>")
    worse, better = ("Increases net debt", "Reduces net debt") if b.kind == "net debt" else \
        ("Reduces cash" if b.kind == "cash" else "Reduces EBITDA", "Adds cash" if b.kind == "cash" else "Adds EBITDA")
    out.append(f'<div class="ddc-foot"><span><i style="background:{GREY}"></i>Total</span>'
               f'<span><i style="background:{RED}"></i>{worse} (worse for the buyer)</span>'
               f'<span><i style="background:{GREEN}"></i>{better}</span>'
               + (f'<span data-nocheck="1">{E(b.note)}</span>' if b.note else "") + "</div></div>")
    return "".join(out)
