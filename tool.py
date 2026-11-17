"""The public tool (demo mode of app.py): Summary · Findings · Impact · Evidence, as in docs/FASE6_DESIGN.md.

Opens on TAP. Every figure and title comes from the engine (deal_layer.build, charts) and is in the memo material;
the reviewer's decisions live in the session and drive the request list export (accepted findings only). No
recommendation and no view on price: the score is the intensity of the findings of the latest year.

Colour has a meaning and nothing else: red = worse for the buyer, green = better or it checks out, amber = Medium and
the middle band only, blue = interaction only (never a figure), grey = neutral, totals and items already in the price.
"""
from __future__ import annotations

import html
import re

import streamlit as st

from dd_assistant import charts, deal_layer as dl, demo
from dd_assistant.ai_memo import fmt_value
from dd_assistant.deal import cash_steps
from dd_assistant.rules import fy

E = html.escape
SITE_URL = "https://mitchell1970.github.io/dd-assistant/"
VIEWS = ("Summary", "Findings", "Impact", "Evidence")
SHAPE = {"High": "▲", "Medium": "●", "Low": "○"}
SEV_COLOUR = {"High": charts.RED, "Medium": charts.AMBER, "Low": charts.MUTED}
SEV_PLAIN = {"High": "could change price or terms", "Medium": "answer before signing", "Low": "note it"}
MD_SHAPE = {"High": ":red[▲]", "Medium": ":orange[●]", "Low": ":gray[○]"}    # theme colours are the palette's
STATES = ("Pending", "Accepted", "Dismissed")
EVIDENCE = ("open", "partly explained", "explained")
EV_COLOUR = {"open": charts.RED, "partly explained": charts.AMBER, "explained": charts.GREEN}
TAG = {"Net debt item": "Debt-like", "To assess": "To assess", "Working capital item": "Working capital"}
SHORT = {"tap": "TAP", "toyota-caetano": "Toyota", "corticeira-amorim": "Amorim"}


def tint(colour: str, alpha: str = "1f") -> str:
    """The colour at about 12% (fill) or 40% ('66', outline): a tint of a palette colour, never a new one."""
    return colour + alpha


CSS = f"""<style>
[data-testid="stHeader"], [data-testid="stAppDeployButton"], #MainMenu,
[data-testid="stSidebarCollapsedControl"], [data-testid="stToolbar"] {{display:none !important}}
.block-container {{max-width:1120px; padding-top:4px !important; padding-bottom:2rem}}
[data-testid="stElementContainer"]:has(style:only-child) {{display:none}}
[data-testid="stAppViewContainer"] {{font-variant-numeric:tabular-nums lining-nums}}
.brand {{font-family:'Source Serif 4', Georgia, serif; font-size:20px; font-weight:600; color:{charts.TEXT};
  white-space:nowrap; line-height:40px}}
.meta {{color:{charts.MUTED}; font-size:13px; text-align:right; line-height:40px; white-space:nowrap}}
.meta b {{color:{charts.TEXT}}}
.st-key-company div[data-testid="stButtonGroup"] {{flex-wrap:nowrap; overflow-x:auto}}
.st-key-view button[aria-checked="true"], .st-key-view button[kind="segmented_controlActive"] {{
  border-color:{charts.ACCENT} !important; color:{charts.ACCENT} !important}}
.hero {{display:grid; grid-template-columns:200px minmax(0,1fr) 190px; gap:24px; align-items:center;
  border:1px solid; border-radius:12px; padding:16px 24px; margin:6px 0 10px}}
.hero .big {{font-size:56px; font-weight:700; line-height:1; white-space:nowrap}}
.hero .big span {{font-size:18px; color:{charts.MUTED}; font-weight:400}}
.hero .word {{font-size:17px; font-weight:600; margin-top:6px}}
.hero .lab {{font-size:13px; color:{charts.MUTED}; margin-top:4px}}
.hero .lab b {{color:{charts.TEXT}}}
.hero .info {{display:block; cursor:help; text-decoration:underline dotted}}
.bar {{display:flex; height:14px; border-radius:7px; overflow:hidden; background:{charts.LINE}}}
.bar i {{display:block; height:100%; border-right:2px solid {charts.CARD}}}
.segs {{display:flex; flex-wrap:wrap; gap:4px 14px; font-size:13px; color:{charts.MUTED}; margin-top:8px}}
.segs b {{color:{charts.TEXT}; font-weight:600}}
.plain {{font-size:14px; color:{charts.TEXT}; margin:8px 0 0; line-height:1.45}}
.hero details {{margin-top:6px; font-size:13px; color:{charts.ACCENT}}}
.hero details summary {{cursor:pointer}}
.hero details table {{width:100%; font-size:13px; color:{charts.TEXT}; margin-top:6px; border-collapse:collapse}}
.hero details td, .hero details th {{padding:3px 6px; border-bottom:1px solid {charts.LINE}; text-align:left}}
.hero details .f {{color:{charts.MUTED}; margin-top:6px}}
.close {{margin-top:8px; font-size:13px; color:{charts.TEXT}}}
.close b {{color:{charts.GREEN}}}
.close ol {{margin:2px 0 0; padding-left:18px; color:{charts.MUTED}}}
.close li span {{color:{charts.TEXT}}}
.cnt {{display:flex; flex-direction:column; gap:6px}}
.cnt span {{font-size:14px; padding:4px 10px; border-radius:6px; border:1px solid; white-space:nowrap}}
.kpis {{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:0 0 10px}}
.kpi {{background:{charts.CARD}; border:1px solid {charts.LINE}; border-top:3px solid; border-radius:8px;
  padding:10px 16px}}
.kpi .l {{font-size:13px; color:{charts.MUTED}}}
.kpi .v {{font-size:30px; font-weight:700; line-height:1.15; text-align:right}}
.kpi .s {{font-size:13px; color:{charts.MUTED}; text-align:right}}
.legend {{display:flex; flex-wrap:wrap; gap:4px 18px; font-size:13px; color:{charts.MUTED}; margin:6px 0 4px}}
.legend b {{font-weight:600}}
.tag {{display:inline-block; font-size:12px; padding:1px 7px; border-radius:5px; border:1px solid {charts.LINE};
  color:{charts.MUTED}; white-space:nowrap}}
.chip {{display:inline-block; font-size:12px; padding:1px 8px; border-radius:10px; border:1px solid; white-space:nowrap}}
.sec {{font-size:13px; color:{charts.MUTED}; text-transform:uppercase; letter-spacing:.06em; margin:16px 0 6px}}
.row {{display:grid; grid-template-columns:76px minmax(0,1fr) 110px 240px; gap:12px; align-items:center;
  min-height:38px; border-left:3px solid; border-radius:6px; padding:0 12px; margin:0 0 4px; font-size:15px;
  color:{charts.TEXT}}}
.row .n {{text-align:right; white-space:nowrap; font-weight:600}}
.row > span:first-child span[title] {{font-size:18px}}
.row .p {{color:{charts.MUTED}; font-size:13px}}
.row.h {{min-height:22px; font-size:13px; color:{charts.MUTED}; border:none; margin:0}}
.inprice {{display:grid; grid-template-columns:minmax(0,1fr) 110px; gap:12px; align-items:center; padding:6px 12px;
  border-left:3px solid {charts.GREY}; border-radius:6px; background:{tint(charts.GREY, '14')}; margin:0 0 4px}}
.inprice .n {{text-align:right; white-space:nowrap; color:{charts.MUTED}; font-weight:600}}
.inprice .why {{font-size:13px; color:{charts.MUTED}}}
@media (max-width:760px) {{
  .hero {{grid-template-columns:1fr; gap:14px; padding:16px}}
  .cnt {{flex-direction:row; flex-wrap:wrap}}
  .row {{grid-template-columns:70px minmax(0,1fr) auto; padding:8px 10px}}
  .row .p {{grid-column:2 / span 2}}
  .row.h {{display:none}}
  .meta {{text-align:left; line-height:20px}}
  .st-key-view button {{padding:4px 9px; min-height:34px}}
  .st-key-view div[data-testid="stButtonGroup"] {{flex-wrap:nowrap}}
}}
.title {{font-family:'Source Serif 4', Georgia, serif; font-size:22px; line-height:1.3; color:{charts.TEXT};
  font-weight:600; margin:2px 0 8px}}
.q {{border-left:2px solid {charts.LINE}; padding:2px 0 2px 12px; color:{charts.TEXT}; font-size:15px; margin:6px 0}}
.src {{font-size:13px; color:{charts.MUTED}}}
.lab {{font-size:13px; color:{charts.MUTED}; margin-top:10px}}
.grid {{display:flex; flex-wrap:wrap; gap:6px; margin:8px 0}}
.grid span {{font-size:13px; padding:3px 8px; border:1px solid {charts.LINE}; border-radius:8px; color:{charts.MUTED}}}
.grid .on {{color:{charts.TEXT}; border-color:{charts.MUTED}}}
.grid .na {{opacity:.55}}
.acts {{display:flex; flex-wrap:wrap; gap:6px; margin:4px 0 10px}}
.foot {{border-top:1px solid {charts.LINE}; margin-top:32px; padding-top:10px; font-size:13px; color:{charts.MUTED}}}
.foot a {{color:{charts.MUTED}}}
div[data-testid="stButton"] button p {{font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}}
[class*="st-key-chip"] button {{padding:4px 8px; min-height:36px}}
[class*="st-key-card-High"] details {{border-left:3px solid {charts.RED}; background:{tint(charts.RED, '0f')}}}
[class*="st-key-card-Medium"] details {{border-left:3px solid {charts.AMBER}; background:{tint(charts.AMBER, '0f')}}}
[class*="st-key-card-Low"] details, [class*="st-key-card-None"] details {{border-left:3px solid {charts.GREY}}}
</style>"""


def money(a, x) -> str:
    return a.money.fmt(x).replace("-€", "−€") if x is not None else "n/q"


def sev(s: str, word: bool = True) -> str:
    """A severity with its shape and colour (never colour alone)."""
    if not s:
        return f'<span style="color:{charts.MUTED}" title="no rule severity">–</span>'
    return f'<span style="color:{SEV_COLOUR[s]}" title="{s}">{SHAPE[s]}{" " + E(s) if word else ""}</span>'


def mark(d) -> str:
    """Severity for a finding; a tag for a balance sheet item (it has no rule, so no severity)."""
    return sev(d.severity, False) if d.severity else f'<span class="tag">{E(TAG.get(d.kind, d.kind))}</span>'


def chip(text: str, colour: str) -> str:
    return (f'<span class="chip" style="color:{colour};border-color:{tint(colour, "66")};'
            f'background:{tint(colour, "14")}">{E(text)}</span>')


def ev_state(evidence: str) -> str:
    return "explained" if evidence.startswith("explained") else \
        "partly explained" if evidence.startswith("partly") else "open"


def legend(coverage: bool = False) -> str:
    if coverage:
        items = ["<span><b>✓</b> run</span>",
                 "<span><b>□</b> blocked: a document is missing</span>", "<span><b>–</b> not applicable</span>"]
    else:
        items = [f'<span>{sev(s, False)} <b style="color:{SEV_COLOUR[s]}">{s}</b> · {SEV_PLAIN[s]}</span>'
                 for s in SHAPE]
        items.append('<span><span class="tag">Debt-like</span> <span class="tag">To assess</span> balance sheet '
                     "items: no rule fired, no severity</span>")
    return f'<div class="legend">{"".join(items)}</div>'


@st.cache_resource(show_spinner=False)
def load(slug: str):
    c = demo.CASE_BY_SLUG[slug]
    a = demo.analysis(c)
    return c, a, dl.build(a)


def page_of(c, kind: str) -> str:
    pattern = {"bs": r"position|Balan|Posição", "is": r"Income|DRE|Resultados", "cf": r"Cash|DFC|Fluxos"}[kind]
    for sheet, where in (c.page_of or {}).items():
        if re.search(pattern, sheet):
            return f"Source: {where}"
    return "Source: published accounts"


def short_name(c) -> str:
    return c.company.split()[0]


# ---------------------------------------------------------------- navigation (callbacks change the view)
def go_findings(area: str | None = None, key: str | None = None) -> None:
    st.session_state.view = "Findings"
    st.session_state.f_area = [area] if area else []
    st.session_state.f_sev, st.session_state.f_ev = [], []
    st.session_state.open_key = key


def change_company() -> None:
    if not st.session_state.get("company"):          # a second click on the active pill: keep the company
        st.session_state.company = st.session_state.get("last_company", "tap")
    st.session_state.last_company = st.session_state.company
    st.query_params["company"] = st.session_state.company
    st.session_state.open_key = None


# ---------------------------------------------------------------- views
def hero(a, layer) -> None:
    """The first thing seen: the score in the colour of its band, where its points come from, the counts."""
    s, cov = layer.score, layer.coverage
    word, tone = s.band
    colour = charts.TONE[tone]
    segs = [(area, pts) for area, pts in s.by_area.items() if pts]
    shades = ("ff", "cc", "99", "77", "55")
    bar = "".join(f'<i style="width:{pts:.1f}%;background:{colour}{shades[k % 5]}" title="{E(area)}"></i>'
                  for k, (area, pts) in enumerate(sorted(segs, key=lambda x: -x[1])))
    labels = "".join(f"<span>{E(area)} <b>{fmt_value(pts)}</b></span>" for area, pts in sorted(segs, key=lambda x: -x[1]))
    counts = "".join(f'<span style="color:{SEV_COLOUR[x]};border-color:{tint(SEV_COLOUR[x], "66")};'
                     f'background:{tint(SEV_COLOUR[x], "14")}">{s.counts.get(x, 0)} {SHAPE[x]} {x}</span>'
                     for x in SHAPE)
    counts += (f'<span style="color:{charts.MUTED};border-color:{charts.LINE}">'
               f"{len(cov.run)} / {cov.total} rules run</span>")
    rows = "".join(f"<tr><td>{E(k)} · {E(s.titles.get(k, k))}</td><td>{E(why)}</td>"
                   f'<td style="text-align:right">{fmt_value(p)}</td></tr>' for k, _, why, p in s.lines)
    how = (f"<details><summary>How the score is built: every point, by issue</summary><table><tr><th>Issue</th>"
           f"<th>Severity × materiality × evidence</th><th>Points</th></tr>{rows}<tr><td><b>Total</b></td>"
           f"<td>{fmt_value(s.points)} points ÷ 30 × 100</td><td style=\"text-align:right\"><b>{s.score}</b></td></tr>"
           f'</table><div class="f">{E(s.formula)}</div></details>')
    st.markdown(f'<div class="hero" style="border-color:{tint(colour, "66")};background:{tint(colour, "14")}">'
                f'<div><div class="big" style="color:{colour}">{s.score}<span> / 100</span></div>'
                f'<div class="word" style="color:{colour}">{E(word)}</div><div class="lab"><b>{E(s.label)}</b> · '
                f'{E(dl.SCORE_LEGEND.split(" (")[0])} <span class="info" title="{E(dl.SCORE_NOTE)}">ⓘ not a '
                f'recommendation</span></div></div>'
                f'<div><div class="bar">{bar}</div><div class="segs">{labels}</div>'
                f'<p class="plain">{E(dl.SCORE_PLAIN)}</p>{closing(s)}{how}</div>'
                f'<div class="cnt">{counts}</div></div>', unsafe_allow_html=True)


def closing(s) -> str:
    """What closes the gap: the three issues whose answer lowers the score most, and the score after them."""
    if not s.closers:
        return ""
    items = "".join(f"<li>{E(k)} · {E(t)} <span>−{fmt_value(p)} pts</span></li>" for k, t, p in s.closers)
    return (f'<div class="close"><b>{E(dl.closing_text(s))}</b><ol>{items}</ol></div>')


def summary(c, a, layer) -> None:
    hero(a, layer)
    issues = [d for d in dl.deal_issues(a) if d.key not in dl.INFORMATION_RULES and not d.historical]
    cols = st.columns(len(dl.AREAS))
    for col, area in zip(cols, dl.AREAS):
        mine = [d for d in issues if d.area == area and not dl.already_in_price(d)]
        worst = next((x for x in ("High", "Medium", "Low") if any(d.severity == x for d in mine)), "Low")
        col.button(f"{MD_SHAPE[worst]} {area} · {len(mine)}", key=f"chip-{area}", on_click=go_findings, args=(area,),
                   use_container_width=True, help=f"Worst severity: {worst}. Click to see the findings.")
    v, L, B = a.view, a.view.pl_years[-1], a.view.bs_years[-1]
    nd, ebitda = v.net_debt_adjusted.get(B), v.ebitda_dd.get(L)
    steps = cash_steps(v, a.data, a.metrics, L)
    fcf = steps[-1] if steps else None
    r21 = next((r for r in a.findings if r.rule.id == "R21" and not r.historical), None)
    lev = f"{nd / ebitda:.2f}x" if nd is not None and ebitda and ebitda > 0 else "n/a"
    passed, total = sum(bool(x["OK"]) for x in a.checks), len(a.checks)
    kpis = [("Adjusted net debt", money(a, nd), f"{fy(B)} · {page_of(c, 'bs')}", charts.TEXT),
            ("Leverage", lev, f"on EBITDA of {money(a, ebitda)} · {page_of(c, 'is')}",
             charts.RED if r21 else charts.GREEN if lev != "n/a" else charts.TEXT),
            ("Free cash flow after leases" if fcf and fcf[0].endswith("leases") else "Free cash flow",
             money(a, fcf[1]) if fcf else "n/a", f"{fy(L)} · {page_of(c, 'cf')}",
             charts.TEXT if not fcf else charts.RED if fcf[1] < 0 else charts.GREEN),
            ("Reading checks", f"{passed} of {total}", "published subtotals rebuilt from the lines read",
             charts.TEXT if total and passed == total else charts.RED)]
    st.markdown('<div class="kpis">' + "".join(
        f'<div class="kpi" style="border-top-color:{col if col != charts.TEXT else charts.LINE}"><div class="l">'
        f'{E(l)}</div><div class="v" style="color:{col}">{E(v_)}</div><div class="s">{E(src)}</div></div>'
        for l, v_, src, col in kpis) + "</div>", unsafe_allow_html=True)
    st.markdown(f'<div class="sec">Top deal issues · {fy(L)}, by amount at stake</div>{legend()}'
                f'<div class="row h"><span></span><span>Issue</span><span class="n">Amount</span>'
                f'<span>{E(dl.COLUMN)}</span></div>', unsafe_allow_html=True)
    for d in layer.top:
        colour = SEV_COLOUR.get(d.severity, charts.GREY)
        left, right = st.columns([12, 1], vertical_alignment="center")
        left.markdown(f'<div class="row" style="border-left-color:{colour};background:{tint(colour, "14")}">'
                      f'<span data-nocheck="1">{mark(d)}</span><span>{E(d.title)}</span>'
                      f'<span class="n" style="color:{colour if d.severity in ("High", "Medium") else charts.TEXT}">'
                      f'{money(a, d.amount)}</span><span class="p">{E(d.protection)}</span></div>',
                      unsafe_allow_html=True)
        right.button("Open", key=f"top-{d.key}", on_click=go_findings, args=(None, d.key))
    priced = dl.in_price(a)
    if priced:
        st.markdown('<div class="sec">Already in the price · shown, not scored</div>' + "".join(
            f'<div class="inprice"><span>{E(p.label)}<br><span class="why">{E(p.why)}</span></span>'
            f'<span class="n">{money(a, p.amount)}</span></div>' for p in priced), unsafe_allow_html=True)


def findings(c, a, layer) -> None:
    f1, f2, f3 = st.columns([2, 5, 3])
    f1.pills("Severity", list(SHAPE), selection_mode="multi", key="f_sev",
             format_func=lambda x: f"{SHAPE[x]} {x}")
    f2.pills("Area", list(dl.AREAS), selection_mode="multi", key="f_area")
    f3.pills("Evidence", list(EVIDENCE), selection_mode="multi", key="f_ev")
    st.markdown(legend(), unsafe_allow_html=True)
    sevs, areas, evs = st.session_state.f_sev, st.session_state.f_area, st.session_state.f_ev
    by_issue = {i.key: i for i in a.issues}
    by_rule = {r.rule.id: r for r in a.findings}
    shown = 0
    for d in dl.deal_issues(a):
        state = ev_state(d.evidence)
        if (sevs and d.severity not in sevs) or (areas and d.area not in areas) or (evs and state not in evs):
            continue
        shown += 1
        when = f" · historical {fy(d.year)}" if d.historical else ""
        label = (f"{MD_SHAPE.get(d.severity, '–') if d.severity else TAG.get(d.kind, d.kind) + ' ·'} "
                 f"{d.key + ' · ' if d.kind == 'Finding' else ''}{d.title} — {money(a, d.amount)} · {state}{when}")
        with st.container(key=f"card-{d.severity or 'None'}-{re.sub(r'[^A-Za-z0-9]', '', d.key)}"):
            with st.expander(label, expanded=d.key == st.session_state.get("open_key")):
                i, r = by_issue.get(d.key), by_rule.get(d.key)
                chips = [chip(state, EV_COLOUR[state])]
                if d.historical:
                    chips.append(chip(f"Historical · {fy(d.year)}", charts.MUTED))
                if dl.already_in_price(d):
                    chips.append(chip("Already in the price", charts.MUTED))
                st.markdown(f'<div class="title">{E(dl.issue_title(d, a.money))}</div>'
                            f'<div>{sev(d.severity) if d.severity else mark(d)} · {E(d.area or "Information")} · '
                            f'{E(d.amount_label)} {" ".join(chips)}</div>', unsafe_allow_html=True)
                if i and i.note:
                    st.caption(i.note[0].upper() + i.note[1:])
                plain = r.rule.plain if r else (i.treatment if i else "")
                st.markdown(E(plain))
                evidence = (r.evidence if r else "") or (f"Balance at {fy(a.view.bs_years[-1])}: "
                                                         f"{money(a, d.amount)}. Source: {i.source}"
                                                         if i and i.source else "")
                if evidence:
                    st.markdown(f'<div class="lab">Evidence</div><div class="q">{E(evidence)}</div>',
                                unsafe_allow_html=True)
                if i and i.evidence_text:
                    st.markdown(f'<div class="lab">From the notes ({E(d.evidence)})</div><div class="q">'
                                f'{E(i.evidence_text)}</div>', unsafe_allow_html=True)
                question = (r.rule.question if r else (i.question if i else ""))
                st.markdown(f'<div class="lab">Question for management</div><div>{E(question)}</div>'
                            f'<div class="lab">Document to request</div><div>{E(d.request)}</div>'
                            f'<div class="lab">{E(dl.COLUMN)} · when</div><div>{E(d.protection)} · {E(d.moment)}</div>',
                            unsafe_allow_html=True)
                if r:
                    st.caption(f"Rule {r.rule.id}: {r.rule.test} Threshold {r.rule.limit_text()}. {r.rule.practice}")
                k1, k2 = st.columns([2, 3])
                k1.radio("Reviewer", STATES, key=f"rev-{c.slug}-{d.key}", horizontal=True)
                k2.text_input("Comment", key=f"com-{c.slug}-{d.key}", placeholder="Why, and what to ask next")
    if not shown:
        st.info("No finding matches these filters.")


def impact(c, a, layer) -> None:
    b = charts.net_debt(a, company=short_name(c))
    if b:
        st.markdown(charts.svg(b, a.money), unsafe_allow_html=True)
    multiple = st.slider("Illustrative multiple (x EBITDA)", 4.0, 12.0, 8.0, 0.5, key="multiple")
    v = charts.valuation(a, multiple)
    if v:
        st.markdown(charts.svg(v, a.money), unsafe_allow_html=True)
    priced = dl.in_price(a)
    if priced:
        st.markdown('<div class="sec">Already in the price · shown, not counted</div>' + "".join(
            f'<div class="inprice"><span>{E(p.label)}<br><span class="why">{E(p.why)}</span></span>'
            f'<span class="n">{money(a, p.amount)}</span></div>' for p in priced), unsafe_allow_html=True)
    cb = charts.cash(a)
    if cb:
        st.markdown(charts.svg(cb, a.money), unsafe_allow_html=True)


def evidence(c, a, layer) -> None:
    cov = layer.coverage
    st.markdown(f'<div class="title">{E(dl.coverage_title(cov))}</div><div class="src">{E(dl.MODE_LINE)}</div>'
                + legend(coverage=True), unsafe_allow_html=True)
    marks = []
    for r in a.results:
        status, doc = cov.status(r.rule.id)
        cls = "on" if status.startswith("run") else "na" if status.startswith("not") else ""
        marks.append(f'<span class="{cls}" title="{E(r.rule.name + (": " + doc if doc else ""))}">'
                     f'{E(status.split()[-1])} {r.rule.id}</span>')
    st.markdown(f'<div class="grid">{"".join(marks)}</div>', unsafe_allow_html=True)
    with st.expander(f"The documents that unlock the {len(cov.blocked)} blocked rules"):
        for rid, name, doc in cov.blocked:
            st.markdown(f"**{rid}** · {name}: {doc}")
        for rid, name, why in cov.not_applicable:
            st.markdown(f"**{rid}** · {name}: not applicable, {why}")
    st.markdown('<div class="sec">Open items</div>', unsafe_allow_html=True)
    for col, g in zip(st.columns(3), dl.GROUPS):
        items = [o for o in layer.open_items if o.group == g]
        with col.expander(f"{g} · {len(items)}", expanded=False):
            for o in items:
                st.markdown(f"- {o.item}")
    st.markdown('<div class="sec">Action items, by moment of the deal</div>', unsafe_allow_html=True)
    current = [d for d in dl.deal_issues(a) if d.key not in dl.INFORMATION_RULES and not d.historical]
    for col, m in zip(st.columns(4), dl.MOMENTS):
        mine = [d for d in current if d.moment == m]
        with col.container(border=True):
            st.markdown(f"**{m}** · {len(mine)}")
            for action in dict.fromkeys(d.protection for d in mine):     # each action once, its issues as chips
                names = [d.title for d in mine if d.protection == action]
                st.markdown(f'<div class="lab">{E(action)} · {len(names)}</div><div class="acts">'
                            + "".join(f'<span class="tag">{E(n)}</span>' for n in names) + "</div>",
                            unsafe_allow_html=True)
    if layer.referrals:
        st.markdown('<div class="sec">Outside the financial scope: routed, not analysed</div>', unsafe_allow_html=True)
        for col, ws in zip(st.columns(len(dl.WORKSTREAMS)), dl.WORKSTREAMS):
            mine = [ref for ref in layer.referrals if ref.workstream == ws]
            with col.expander(f"{ws} · {len(mine)}"):
                for ref in mine:
                    st.markdown(f"**{ref.item}**: {ref.question}")
    st.markdown('<div class="sec">Downloads</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    d1.download_button("Databook (Excel)", c.databook_path.read_bytes(), f"{c.slug}_databook.xlsx",
                       use_container_width=True)
    pdf = c.folder / "red_flag_report.pdf"
    if pdf.exists():
        d2.download_button("Red flag report (PDF)", pdf.read_bytes(), f"{c.slug}_red_flag_report.pdf",
                           use_container_width=True)
    if c.memo_path.exists():
        d3.download_button("Memo (Markdown)", c.memo_path.read_bytes(), f"{c.slug}_memo.md",
                           use_container_width=True)
    accepted = [d for d in dl.deal_issues(a)
                if st.session_state.get(f"rev-{c.slug}-{d.key}") == "Accepted"]
    text = "\n".join([f"# Request list — {c.company} (accepted findings)", ""] +
                     [f"- {d.request} ({d.key})" for d in accepted])
    d4.download_button(f"Request list · {len(accepted)} accepted", text.encode("utf-8"),
                       f"{c.slug}_request_list.md", disabled=not accepted, use_container_width=True,
                       help="Only the findings you marked Accepted in Findings.")


# ---------------------------------------------------------------- page
def main() -> None:
    st.set_page_config(page_title="DD Assistant · tool", page_icon="✓", layout="wide",
                       initial_sidebar_state="collapsed")
    st.markdown(CSS + f"<style>{charts.CSS}</style>", unsafe_allow_html=True)
    if "company" not in st.session_state:
        wanted = st.query_params.get("company", "tap")
        st.session_state.company = wanted if wanted in demo.CASE_BY_SLUG else "tap"
        st.session_state.last_company = st.session_state.company
    for key, value in (("view", "Summary"), ("f_sev", []), ("f_area", []), ("f_ev", []), ("open_key", None)):
        st.session_state.setdefault(key, value)
    # the app bar: brand and the three companies on the left; year, unit, mode and the databook on the right
    h1, h2, h3, h4 = st.columns([1.5, 3.6, 2.4, 2.1], vertical_alignment="center")
    h1.markdown('<div class="brand">DD Assistant</div>', unsafe_allow_html=True)
    h2.segmented_control("Company", list(demo.CASE_BY_SLUG), key="company", on_change=change_company,
                         format_func=lambda s: SHORT.get(s, demo.CASE_BY_SLUG[s].company),
                         label_visibility="collapsed")
    c, a, layer = load(st.session_state.company or st.session_state.get("last_company", "tap"))
    mode = "Published accounts" if layer.coverage.mode.startswith("outside-in") else "Data room"
    h3.markdown(f'<div class="meta"><b>{fy(a.view.pl_years[-1])}</b> · {E(a.money.unit)} · {mode}</div>',
                unsafe_allow_html=True)
    h4.download_button("Download databook", c.databook_path.read_bytes(), f"{c.slug}_databook.xlsx",
                       use_container_width=True, icon=":material/download:")
    st.segmented_control("View", VIEWS, key="view", label_visibility="collapsed")
    view = st.session_state.view or "Summary"
    {"Summary": summary, "Findings": findings, "Impact": impact, "Evidence": evidence}[view](c, a, layer)
    st.markdown(f'<div class="foot">{E(c.company)} · preliminary analysis on published accounts, not an opinion. '
                f'<a href="{SITE_URL}">About this project</a></div>', unsafe_allow_html=True)
