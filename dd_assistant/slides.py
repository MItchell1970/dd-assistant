"""Layer 5b — the Red Flag Report in slides (PowerPoint), built from an analysis.

Nine slides, as a deal team reads them: cover · key issues · financial overview · quality of earnings · net debt ·
working capital · cash flow · information requests · scope, sources and limits.

Rules of the deck:
- every title states the conclusion with its figure, and is assembled by rule from the engine's values;
- charts are native PowerPoint charts (editable), never pictures; each bar carries its value in its label;
- every slide has the source in its footer; nothing is computed here: bridges come from deal.py as steps.

Needs python-pptx (pip install python-pptx): a tool for producing the deck, not a dependency of the app.
"""
from __future__ import annotations

from pathlib import Path

from .deal import cash_steps, ifrs16_steps, net_debt_steps, qoe_steps
from .rules import fy

NAVY, BLUE, GREY, INK, MUTED = "0B3D91", "5B7FC4", "A9B6CC", "1B2333", "5B6474"
# shorter labels under the bars of a chart (the figures and their meaning do not change)
SHORT = {"Tax, interest and other operating items": "Tax, interest, other",
         "Working capital, tax and other operating items": "Working capital, tax, other",
         "Change in net working capital": "Change in NWC", "Proceeds from asset disposals": "Disposals",
         "Free cash flow after leases": "FCF after leases", "Lease payments (cash flow statement)": "Lease payments",
         "Post-employment benefit obligations": "Pensions", "Diligence-adjusted EBITDA": "Adjusted EBITDA"}
FONT = "Segoe UI"
LIMITS = ("Annual accounts only: no monthly figures, LTM or budget.",
          "Euros only; financial due diligence only (no legal, tax, commercial or IT review).",
          "A first pass for an analyst to review: no investment recommendation and no view on price.")


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def titles(a) -> dict[int, str]:
    """The conclusion of each slide, by rule, from the engine's values (tested against the memo material)."""
    v, m, f, d = a.view, a.metrics, a.money.fmt, a.data
    L, B, Y = v.pl_years[-1], v.bs_years[-1], v.pl_years
    out = {}
    top = a.issues[0] if a.issues else None
    out[2] = (f"{len(a.issues)} key issues; the largest is {top.title[0].lower() + top.title[1:]}, {f(top.amount)}"
              if top and top.amount is not None else "No key issue was raised on the data provided")
    cagr = m["cagr_vendas"].get(L)
    if cagr is not None:
        out[3] = (f"Revenue {'grew' if cagr >= 0 else 'fell'} {abs(cagr) * 100:.1f}% a year over the three years; "
                  f"EBITDA margin was {_pct(m['ebitda_m'][Y[0]])} in {fy(Y[0])} and {_pct(m['ebitda_m'][L])} in "
                  f"{fy(L)}")
    else:
        g = m["g_vendas"].get(L)
        out[3] = (f"Revenue {'grew' if (g or 0) >= 0 else 'fell'} {abs(g or 0) * 100:.1f}% in {fy(L)}; EBITDA margin "
                  f"is {_pct(m['ebitda_m'][L])}")
    pre16 = ifrs16_steps(v, d, L)
    if abs(v.ebitda_dd[L] - v.ebitda[L]) > 0.5:
        out[4] = f"Diligence-adjusted EBITDA is {f(v.ebitda_dd[L])} in {fy(L)}, against {f(v.ebitda[L])} reported"
    elif pre16:
        out[4] = f"EBITDA is {f(v.ebitda[L])} in {fy(L)}; after lease payments it is {f(pre16[-1][1])}"
    else:
        out[4] = f"Reported EBITDA is {f(v.ebitda[L])} in {fy(L)}; no adjustment was identified from the accounts"
    adj, rep = v.net_debt_adjusted.get(B), v.net_debt_reported.get(B)
    if adj is not None and rep is not None:
        times = f" ({adj / v.ebitda_dd[L]:.2f}x EBITDA)" if v.ebitda_dd.get(L, 0) > 0 else ""
        out[5] = f"Adjusted net debt is {f(adj)}{times}, against borrowings less cash of {f(rep)}"
    else:
        out[5] = "Net debt cannot be computed: a figure is missing"
    nwc, rev = v.nwc_values.get(B), d.v("vendas", B)
    if nwc is not None and rev:
        gap = None if v.nwc_average is None else nwc - v.nwc_average
        out[6] = (f"Net working capital is {f(nwc)}, {_pct(nwc / rev)} of revenue"
                  + (f"; {f(abs(gap))} {'above' if gap > 0 else 'below'} the average of the year-ends"
                     if gap is not None and len(v.bs_years) > 1 else ""))
    else:
        out[6] = "Net working capital cannot be computed: a figure is missing"
    cash = dict((label, value) for label, value, _ in cash_steps(v, d, m, L))
    if cash:
        fcf = cash["Free cash flow"]
        out[7] = (f"Free cash flow of {f(fcf)} exceeded EBITDA of {f(v.ebitda[L])} in {fy(L)}, as working capital "
                  "was released" if fcf > v.ebitda[L] and cash.get("Change in net working capital", 0) > 0 else
                  f"Of EBITDA of {f(v.ebitda[L])}, {f(fcf)} became free cash flow in {fy(L)}" if fcf > 0 else
                  f"EBITDA was {f(v.ebitda[L])} in {fy(L)}, but free cash flow was {f(fcf)}")
    else:
        out[7] = "The cash flow bridge cannot be built: a figure is missing"
    return out


def requests(a, limit: int = 10) -> list[tuple[str, str]]:
    """(request, the issues it comes from): the priority requests, in the order of the key issues, without repeats."""
    seen: dict[str, list[str]] = {}
    for i in a.issues:
        for part in (p.strip() for p in i.request.split(";")):
            if part and part.lower() != "the documents listed in the evidence":
                seen.setdefault(part[0].upper() + part[1:], []).append(i.key if i.kind == "Finding" else i.title)
    return [(doc, ", ".join(dict.fromkeys(keys))) for doc, keys in list(seen.items())[:limit]]


def write_slides(a, path, company: str | None = None, source: str = "") -> None:
    """The Red Flag Report of an analysis (pipeline.Analysis) as a .pptx file."""
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_TICK_LABEL_POSITION
    from pptx.enum.text import MSO_ANCHOR
    from pptx.util import Emu, Inches, Pt

    v, m, d, f = a.view, a.metrics, a.data, a.money.fmt
    L, B = v.pl_years[-1], v.bs_years[-1]
    name = company or a.ext.company
    source = source or f"published accounts {fy(v.pl_years[0])}–{fy(L)}"
    head = titles(a)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    rgb = lambda h: RGBColor.from_string(h)

    def text(slide, x, y, w, h, content, size=14, bold=False, colour=INK, anchor=None):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        if anchor:
            tf.vertical_anchor = anchor
        for n, line in enumerate(content if isinstance(content, list) else [content]):
            p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
            run = p.add_run()
            run.text = line
            run.font.size, run.font.bold, run.font.name = Pt(size), bold, FONT
            run.font.color.rgb = rgb(colour)
            p.space_after = Pt(6)
        return box

    def slide(number: int, title: str):
        s = prs.slides.add_slide(blank)
        text(s, 0.6, 0.35, 12.1, 1.1, title, 24, True, NAVY, MSO_ANCHOR.TOP)
        rule = s.shapes.add_shape(1, Inches(0.6), Inches(1.5), Inches(12.1), Emu(19050))
        rule.fill.solid()
        rule.fill.fore_color.rgb = rgb(NAVY)
        rule.line.fill.background()
        text(s, 0.6, 6.95, 11.3, 0.4, f"{name} · Source: {source} · Preliminary: for an analyst to review", 10, False,
             MUTED)
        text(s, 12.1, 6.95, 0.7, 0.4, str(number), 10, False, MUTED)
        return s

    def table(s, x, y, w, rows, widths, size=11, row_height=0.42):
        shape = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w),
                                   Inches(row_height * len(rows)))
        t = shape.table
        for c, share in enumerate(widths):
            t.columns[c].width = Inches(w * share / sum(widths))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                cell = t.cell(r, c)
                cell.text = "" if value is None else str(value)
                cell.margin_left = cell.margin_right = Inches(0.08)
                para = cell.text_frame.paragraphs[0]
                para.runs[0].font.size = Pt(size)
                para.runs[0].font.name = FONT
                para.runs[0].font.bold = r == 0
                para.runs[0].font.color.rgb = rgb("FFFFFF" if r == 0 else INK)
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(NAVY if r == 0 else "FFFFFF" if r % 2 else "F4F6FA")
        return shape

    def waterfall(s, x, y, w, h, steps):
        """A native stacked column chart: an invisible base, then the bar; each bar's value is in its label."""
        if len(steps) < 2:
            text(s, x, y + 1, w, 1, "Not available: a figure this bridge needs is missing.", 14, False, MUTED)
            return None
        cats, base, up, colours, level = [], [], [], [], 0.0
        down = {NAVY: [], BLUE: [], GREY: []}     # the part of a bar below zero, one series per colour
        for label, value, kind in steps:
            lo, hi = (min(0.0, value), max(0.0, value)) if kind == "total" else (min(level, level + value),
                                                                               max(level, level + value))
            level = value if kind == "total" else level + value
            colour = NAVY if kind == "total" else BLUE if value > 0 else GREY
            cats.append(f"{SHORT.get(label, label)}\n"
                        f"{f(value) if kind == 'total' else ('+' if value > 0 else '') + f(value)}")
            below = 0.0
            if lo >= 0:
                base.append(lo), up.append(hi - lo)
            elif hi <= 0:
                base.append(hi), up.append(0.0)
                below = lo - hi
            else:
                base.append(0.0), up.append(hi)
                below = lo
            for c in down:
                down[c].append(below if c == colour else 0.0)
            colours.append(colour)
        data = CategoryChartData()
        data.categories = cats
        data.add_series("base", base)
        data.add_series("up", up)
        for c in down:
            data.add_series(f"down {c}", down[c])
        chart = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(x), Inches(y), Inches(w), Inches(h),
                                   data).chart
        chart.has_legend = False
        chart.has_title = False
        plot = chart.plots[0]
        plot.gap_width, plot.overlap = 55, 100
        hidden = plot.series[0]
        hidden.invert_if_negative = False
        hidden.format.fill.background()
        hidden.format.line.fill.background()
        for n, colour in enumerate(colours):       # above zero: one colour per bar
            point = plot.series[1].points[n]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = rgb(colour)
        for series, colour in zip(list(plot.series)[2:], down):   # below zero: one series per colour
            series.invert_if_negative = False
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = rgb(colour)
        chart.value_axis.visible = False
        chart.value_axis.has_major_gridlines = False
        chart.category_axis.tick_labels.font.size = Pt(12 if len(steps) <= 6 else 10)
        chart.category_axis.tick_labels.font.name = FONT
        chart.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW   # below the bars, also when negative
        chart.category_axis.format.line.color.rgb = rgb(GREY)
        return chart

    # 1 · cover
    s = prs.slides.add_slide(blank)
    band = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(7.5))
    band.fill.solid()
    band.fill.fore_color.rgb = rgb(NAVY)
    band.line.fill.background()
    text(s, 0.9, 1.6, 11.5, 0.5, "RED FLAG REPORT · PRELIMINARY FINANCIAL DUE DILIGENCE", 14, False, "C9D6F2")
    text(s, 0.9, 2.2, 11.5, 1.4, name, 44, True, "FFFFFF")
    text(s, 0.9, 3.9, 11.5, 1.6, [f"Published consolidated accounts {fy(v.pl_years[0])}–{fy(L)}", f"Source: {source}"],
         18, False, "FFFFFF")
    text(s, 0.9, 6.3, 11.5, 0.6, "Preliminary: for an analyst to review. Not an opinion, not a view on price. "
                                 "Built with DD Assistant.", 12, False, "C9D6F2")

    # 2 · key issues
    s = slide(2, head[2])
    rows = [["#", "Issue", "Amount at stake", "Deal implication (typical)", "Evidence from the notes"]]
    for n, i in enumerate(a.issues[:5], 1):
        ev = (i.evidence_state + (f" by {i.evidence_note}" if i.evidence_note else "")) if i.evidence_state else \
            "notes not read"
        rows.append([n, (f"{i.key} · {i.title}" if i.kind == "Finding" else f"{i.title} ({i.kind.lower()})"),
                     f"{f(i.amount)}, {fy(i.year)}" if i.amount is not None else "not quantifiable", i.implication,
                     ev[0].upper() + ev[1:]])
    table(s, 0.6, 1.8, 12.1, rows, [0.4, 4.2, 2.0, 2.6, 2.9], 13, 0.62)
    text(s, 0.6, 5.75, 12.1, 0.9, f"Ordered by amount at stake. Materiality: {a.materiality.text()} "
                                  f"({f(a.thresholds.get('pl'))} and {f(a.thresholds.get('bs'))}). The implication is the "
                                  "typical treatment, for the deal team and its lawyers to decide.", 12, False, MUTED)

    # 3 · financial overview
    s = slide(3, head[3])
    years = v.pl_years
    rows = [[f"{a.money.unit} unless stated"] + [fy(y) for y in years],
            ["Revenue"] + [a.money.amount(m["vendas"].get(y)) for y in years],
            ["Reported EBITDA"] + [a.money.amount(v.ebitda.get(y)) for y in years],
            ["EBITDA margin"] + [_pct(m["ebitda_m"].get(y)) for y in years],
            ["Cash conversion (operating cash / EBITDA)"] + [_pct(m["conv"].get(y)) for y in years],
            ["Adjusted net debt"] + [a.money.amount(v.net_debt_adjusted.get(y)) for y in years],
            ["Net working capital"] + [a.money.amount(v.nwc_values.get(y)) for y in years]]
    table(s, 0.6, 1.9, 12.1, rows, [5] + [2.3] * len(years), 14, 0.58)
    passed = sum(c["OK"] for c in a.checks)
    text(s, 0.6, 6.15, 12.1, 0.6, f"Reading checks: {passed} of {len(a.checks)} published subtotals rebuilt from the "
                                  "lines read." + (f" Earlier years from the prior report; for the year both reports "
                                                   f"give, the latest comparative is used." if d.prior_report else ""),
         12, False, MUTED)

    # 4 · quality of earnings
    s = slide(4, head[4])
    steps = qoe_steps(v, L)
    waterfall(s, 0.6, 1.75, 12.1, 4.5, ifrs16_steps(v, d, L) if len(steps) <= 2 and ifrs16_steps(v, d, L) else steps)
    r04 = next((r for r in a.findings if r.rule.id == "R04"), None)
    note = (f"Other income is {_pct(m['or_ebitda'].get(L))} of EBITDA (R04). " + (r04.evidence_text or "")) if r04 else \
        "No diligence adjustment was identified from the accounts alone: adjustments need the ledger and the contracts."
    text(s, 0.6, 6.25, 12.1, 0.65, f"{fy(L)}, {a.money.unit}. {note}"[:330], 11, False, MUTED)

    # 5 · net debt
    s = slide(5, head[5])
    waterfall(s, 0.6, 1.75, 8.1, 4.9, net_debt_steps(v, B))
    assess = [i for i in a.issues if i.kind == "To assess"][:5]
    text(s, 8.9, 1.8, 3.8, 0.4, "To assess (not in adjusted net debt)", 13, True, NAVY)
    text(s, 8.9, 2.25, 3.8, 4.3, [f"{i.title}: {f(i.amount)}" + (f" ({i.evidence_state} by {i.evidence_note})"
                                                                 if i.evidence_note else "") for i in assess]
         or ["No item to assess was found in the balance sheet."], 12, False, INK)

    # 6 · working capital
    s = slide(6, head[6])
    ys = [y for y in v.bs_years if v.nwc_values.get(y) is not None]
    if ys:
        data = CategoryChartData()
        data.categories = [f"{fy(y)}\n{f(v.nwc_values[y])}" for y in ys]
        data.add_series("Net working capital", [v.nwc_values[y] for y in ys])
        chart = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.75), Inches(7.6), Inches(4.4),
                                   data).chart
        chart.has_legend, chart.has_title = False, False
        chart.plots[0].gap_width = 120
        chart.plots[0].series[0].invert_if_negative = False
        chart.plots[0].series[0].format.fill.solid()
        chart.plots[0].series[0].format.fill.fore_color.rgb = rgb(NAVY)
        chart.value_axis.visible = False
        chart.value_axis.has_major_gridlines = False
        chart.category_axis.tick_labels.font.size = Pt(12)
        chart.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    lines = [f"{ln.label}: {f(ln.values.get(B))}" for ln in v.nwc
             if ln.unit == "money" and ln.values.get(B) is not None and not ln.label.startswith(("Average", "Latest"))]
    if v.nwc_average is not None and len(v.bs_years) > 1:
        lines.append(f"Average of the year-ends: {f(v.nwc_average)} (indicative peg reference only)")
    text(s, 8.5, 1.8, 4.2, 0.4, f"What is inside, {fy(B)}", 13, True, NAVY)
    text(s, 8.5, 2.25, 4.2, 4.3, lines[:9], 11, False, INK)
    text(s, 0.6, 6.45, 12.1, 0.45, "Year-end balances only. A peg is negotiated on 12 to 24 monthly balances.", 11,
         False, MUTED)

    # 7 · cash flow
    s = slide(7, head[7])
    waterfall(s, 0.6, 1.75, 12.1, 4.6, cash_steps(v, d, m, L))
    text(s, 0.6, 6.35, 12.1, 0.55, f"{fy(L)}, {a.money.unit}. The change in working capital comes from the two balance "
                                   "sheets; the remainder to the published operating cash flow is shown as its own bar.",
         11, False, MUTED)

    # 8 · information requests
    reqs = requests(a)
    s = slide(8, f"{len(reqs)} priority requests: the level below what the public report already answers")
    rows = [["#", "Document or analysis to request", "For"]] + [[n, doc, keys] for n, (doc, keys) in enumerate(reqs, 1)]
    table(s, 0.6, 1.75, 12.1, rows, [0.4, 8.6, 3.1], 11, 0.44)

    # 9 · scope, sources and limits
    s = slide(9, "Scope, sources and limits")
    text(s, 0.6, 1.8, 5.9, 0.4, "Scope and sources", 14, True, NAVY)
    text(s, 0.6, 2.3, 5.9, 4.4,
         [f"Consolidated accounts {fy(v.pl_years[0])}–{fy(L)}: {source}.",
          f"Framework: {a.country.framework if a.country else 'not set'}.",
          f"Sector: {a.sector.name}. Purpose: preliminary buy-side review.",
          (f"Notes to the accounts read: yes ({a.ext.notes_file})." if a.ext.notes else
           "Notes to the accounts: not read."),
          f"Reading checks: {passed} of {len(a.checks)} passed."], 12, False, INK)
    text(s, 6.9, 1.8, 5.8, 0.4, "Limits", 14, True, NAVY)
    text(s, 6.9, 2.3, 5.8, 4.4, list(LIMITS) + [
        "Figures are computed by deterministic code from the published lines; each traces to its source cell.",
        "Deal implications are typical treatments, for the deal team and its lawyers to decide."], 12, False, INK)
    prs.save(path if hasattr(path, "write") else str(path))
