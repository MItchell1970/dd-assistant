"""The public tool (demo mode of app.py): Summary · Findings · Impact · Evidence, as in docs/FASE5_DESIGN.md.

Opens on TAP. Every figure and title comes from the engine (deal_layer.build, charts) and is in the memo material;
the reviewer's decisions live in the session and drive the request list export (accepted findings only). No
recommendation and no view on price: the score is the intensity of the findings.
"""
from __future__ import annotations

import html
import re

import streamlit as st

from dd_assistant import charts, deal_layer as dl, demo
from dd_assistant.deal import cash_steps
from dd_assistant.rules import fy

E = html.escape
SITE_URL = "https://mitchell1970.github.io/dd-assistant/"
VIEWS = ("Summary", "Findings", "Impact", "Evidence")
SHAPE = {"High": "▲", "Medium": "●", "Low": "○"}
SEV_COLOUR = {"High": charts.RED, "Medium": charts.TEXT, "Low": charts.MUTED}
MD_SHAPE = {"High": ":red[▲]", "Medium": "●", "Low": ":gray[○]"}    # theme red and gray are the palette's
STATES = ("Pending", "Accepted", "Dismissed")
EVIDENCE = ("open", "partly explained", "explained")

CSS = f"""<style>
[data-testid="stAppDeployButton"], #MainMenu, [data-testid="stSidebarCollapsedControl"] {{display:none}}
.block-container {{max-width:1120px; padding-top:1.4rem; padding-bottom:2rem}}
[data-testid="stAppViewContainer"] {{font-variant-numeric:tabular-nums lining-nums}}
.t-head {{display:flex; flex-wrap:wrap; gap:4px 16px; align-items:baseline; color:{charts.MUTED}; font-size:13px}}
.t-head b {{color:{charts.TEXT}; font-size:15px}}
.band {{display:flex; gap:20px; align-items:center; background:{charts.CARD}; border:1px solid {charts.LINE};
  border-radius:8px; padding:12px 16px; margin:4px 0 12px}}
.band .s {{font-size:32px; font-weight:600; color:{charts.TEXT}; line-height:1; white-space:nowrap}}
.band .s span {{font-size:15px; color:{charts.MUTED}; font-weight:400}}
.band .l {{font-size:15px; color:{charts.TEXT}; font-weight:600}}
.band .c {{font-size:13px; color:{charts.MUTED}; margin-top:2px}}
.kpis {{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:0 0 12px}}
.kpi {{background:{charts.CARD}; border:1px solid {charts.LINE}; border-radius:8px; padding:12px 16px}}
.kpi .l {{font-size:13px; color:{charts.MUTED}}}
.kpi .v {{font-size:32px; font-weight:600; color:{charts.TEXT}; line-height:1.15; text-align:right}}
.kpi .s {{font-size:13px; color:{charts.MUTED}; text-align:right}}
.sec {{font-size:13px; color:{charts.MUTED}; text-transform:uppercase; letter-spacing:.06em; margin:14px 0 6px}}
.row {{display:grid; grid-template-columns:24px minmax(0,1fr) 110px 220px 140px; gap:12px; align-items:center;
  min-height:40px; border-bottom:1px solid {charts.LINE}; font-size:15px; color:{charts.TEXT}}}
.row .n {{text-align:right; white-space:nowrap}}
.row .m {{color:{charts.MUTED}; font-size:13px}}
.row.h {{min-height:28px; font-size:13px; color:{charts.MUTED}}}
@media (max-width:700px) {{
  .row {{grid-template-columns:24px minmax(0,1fr) auto; padding:8px 0}}
  .row .p, .row .m {{grid-column:2 / span 2; text-align:left}}
  .row.h {{display:none}}
  .band {{flex-direction:column; align-items:flex-start; gap:6px}}
}}
.title {{font-family:'Source Serif 4', Georgia, serif; font-size:24px; line-height:1.3; color:{charts.TEXT};
  font-weight:600; margin:2px 0 8px}}
.q {{border-left:2px solid {charts.LINE}; padding:2px 0 2px 12px; color:{charts.TEXT}; font-size:15px; margin:6px 0}}
.src {{font-size:13px; color:{charts.MUTED}}}
.lab {{font-size:13px; color:{charts.MUTED}; margin-top:10px}}
.grid {{display:flex; flex-wrap:wrap; gap:6px; margin:8px 0}}
.grid span {{font-size:13px; padding:3px 8px; border:1px solid {charts.LINE}; border-radius:8px; color:{charts.MUTED}}}
.grid .on {{color:{charts.GREEN}}}
.foot {{border-top:1px solid {charts.LINE}; margin-top:32px; padding-top:10px; font-size:13px; color:{charts.MUTED}}}
.foot a {{color:{charts.MUTED}}}
div[data-testid="stButton"] button p {{font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}}
[class*="st-key-chip"] button {{padding:4px 8px; min-height:36px}}
</style>"""


def money(a, x) -> str:
    return a.money.fmt(x).replace("-€", "−€") if x is not None else "n/q"


def sev(s: str, word: bool = True) -> str:
    """A severity with its shape and colour (never colour alone)."""
    if not s:
        return f'<span style="color:{charts.MUTED}" title="no rule severity">–</span>'
    return f'<span style="color:{SEV_COLOUR[s]}" title="{s}">{SHAPE[s]}{" " + E(s) if word else ""}</span>'


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
    st.query_params["company"] = st.session_state.company
    st.session_state.open_key = None


# ---------------------------------------------------------------- views
def summary(c, a, layer) -> None:
    s, cov = layer.score, layer.coverage
    issues = [d for d in dl.deal_issues(a) if d.key not in dl.INFORMATION_RULES]
    open_n = sum(not d.evidence.startswith("explained") for d in issues)
    before = len(layer.actions["Before signing"])
    st.markdown(f'<div class="band"><div class="s">{s.score}<span> / 100</span></div><div>'
                f'<div class="l">{E(s.label)}</div><div class="c">{open_n} open issues · {before} actions before '
                f'signing · {E(cov.text)}</div></div></div>', unsafe_allow_html=True)
    with st.popover("How the score is computed"):
        st.caption(s.formula)
    v, L, B = a.view, a.view.pl_years[-1], a.view.bs_years[-1]
    nd, ebitda = v.net_debt_adjusted.get(B), v.ebitda_dd.get(L)
    steps = cash_steps(v, a.data, a.metrics, L)
    fcf = steps[-1] if steps else None
    lev = f"{nd / ebitda:.2f}x" if nd is not None and ebitda and ebitda > 0 else "n/a"
    kpis = [("Adjusted net debt", money(a, nd), f"{fy(B)} · {page_of(c, 'bs')}"),
            ("Leverage", lev, f"on EBITDA of {money(a, ebitda)} · {page_of(c, 'is')}"),
            ("Free cash flow after leases" if fcf and fcf[0].endswith("leases") else "Free cash flow",
             money(a, fcf[1]) if fcf else "n/a", f"{fy(L)} · {page_of(c, 'cf')}"),
            ("Risk score", f"{s.score}", "30 rules · severity × materiality × evidence")]
    st.markdown('<div class="kpis">' + "".join(f'<div class="kpi"><div class="l">{E(l)}</div><div class="v">{E(v_)}'
                                                f'</div><div class="s">{E(src)}</div></div>' for l, v_, src in kpis)
                + "</div>", unsafe_allow_html=True)
    cols = st.columns(len(dl.AREAS))
    for col, area in zip(cols, dl.AREAS):
        mine = [d for d in issues if d.area == area]
        worst = next((x for x in ("High", "Medium", "Low") if any(d.severity == x for d in mine)), "Low")
        col.button(f"{MD_SHAPE[worst]} {area} · {len(mine)}", key=f"chip-{area}", on_click=go_findings, args=(area,),
                   use_container_width=True, help=f"Worst severity: {worst}. Click to see the findings.")
    st.markdown('<div class="sec">Top 5 deal issues, by amount at stake</div>'
                f'<div class="row h"><span></span><span>Issue</span><span class="n">Amount</span>'
                f'<span>{E(dl.COLUMN)}</span><span>When</span></div>', unsafe_allow_html=True)
    for d in layer.top:
        left, right = st.columns([12, 1], vertical_alignment="center")
        left.markdown(f'<div class="row"><span data-nocheck="1">{d.rank}</span><span>{sev(d.severity, False)} '
                      f'{E(d.title)}</span><span class="n">{money(a, d.amount)}</span>'
                      f'<span class="p">{E(d.protection)}</span><span class="m">{E(d.moment)}</span></div>',
                      unsafe_allow_html=True)
        right.button("Open", key=f"top-{d.key}", on_click=go_findings, args=(None, d.key))


def findings(c, a, layer) -> None:
    f1, f2, f3 = st.columns([2, 5, 3])
    f1.pills("Severity", list(SHAPE), selection_mode="multi", key="f_sev",
             format_func=lambda x: f"{SHAPE[x]} {x}")
    f2.pills("Area", list(dl.AREAS), selection_mode="multi", key="f_area")
    f3.pills("Evidence", list(EVIDENCE), selection_mode="multi", key="f_ev")
    sevs, areas, evs = st.session_state.f_sev, st.session_state.f_area, st.session_state.f_ev
    by_issue = {i.key: i for i in a.issues}
    by_rule = {r.rule.id: r for r in a.findings}
    shown = 0
    for d in dl.deal_issues(a):
        state = "explained" if d.evidence.startswith("explained") else \
            "partly explained" if d.evidence.startswith("partly") else "open"
        if (sevs and d.severity not in sevs) or (areas and d.area not in areas) or (evs and state not in evs):
            continue
        shown += 1
        label = (f"{MD_SHAPE.get(d.severity, '–')} {d.key if d.kind == 'Finding' else d.kind} · {d.title} — "
                 f"{money(a, d.amount)} · {state}")
        with st.expander(label, expanded=d.key == st.session_state.get("open_key")):
            i, r = by_issue.get(d.key), by_rule.get(d.key)
            st.markdown(f'<div class="title">{E(dl.issue_title(d, a.money))}</div>'
                        f'<div>{sev(d.severity)} · {E(d.area or "Information")} · {E(d.amount_label)}</div>',
                        unsafe_allow_html=True)
            plain = r.rule.plain if r else (i.treatment if i else "")
            st.markdown(E(plain))
            evidence = (r.evidence if r else "") or (f"Balance at {fy(a.view.bs_years[-1])}: {money(a, d.amount)}"
                                                     f". Source: {i.source}" if i and i.source else "")
            if evidence:
                st.markdown(f'<div class="lab">Evidence</div><div class="q">{E(evidence)}</div>', unsafe_allow_html=True)
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
    vi = layer.impact
    shown = vi.standard + ([vi.nwc] if vi.nwc else [])
    if shown:
        st.markdown('<div class="sec">Shown, not counted</div>', unsafe_allow_html=True)
        for comp in shown:
            st.markdown(f'<div class="row" style="grid-template-columns:minmax(0,1fr) 120px">'
                        f'<span>{E(comp.label)}<br><span class="src">{E(dl.NOT_COUNTED_WHY.get(comp.nature, comp.basis))}'
                        f'</span></span><span class="n">{money(a, comp.amount)}</span></div>', unsafe_allow_html=True)
    cb = charts.cash(a)
    if cb:
        st.markdown(charts.svg(cb, a.money), unsafe_allow_html=True)


def evidence(c, a, layer) -> None:
    cov = layer.coverage
    st.markdown(f'<div class="title">{E(dl.coverage_title(cov))}</div><div class="src">{E(dl.MODE_LINE)}</div>',
                unsafe_allow_html=True)
    marks = []
    for r in a.results:
        status, doc = cov.status(r.rule.id)
        cls = "on" if status.startswith("run") else ""
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
    for col, m in zip(st.columns(4), dl.MOMENTS):
        with col.expander(f"{m} · {len(layer.actions[m])}", expanded=True):
            for x in layer.actions[m]:
                st.markdown(f"- {x}")
    if layer.referrals:
        st.markdown('<div class="sec">Outside the financial scope: routed, not analysed</div>', unsafe_allow_html=True)
        for ref in layer.referrals:
            st.markdown(f"- **{ref.workstream}** · {ref.item}: {ref.question}")
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
    for key, value in (("view", "Summary"), ("f_sev", []), ("f_area", []), ("f_ev", []), ("open_key", None)):
        st.session_state.setdefault(key, value)
    h1, h2, h3 = st.columns([3, 5, 2], vertical_alignment="center")
    h1.selectbox("Company", list(demo.CASE_BY_SLUG), key="company", on_change=change_company,
                 format_func=lambda s: demo.CASE_BY_SLUG[s].company, label_visibility="collapsed")
    c, a, layer = load(st.session_state.company)
    h2.markdown(f'<div class="t-head"><b>{fy(a.view.pl_years[-1])}</b><span>{E(a.money.unit)}</span>'
                f'<span>{E(layer.coverage.mode)}</span></div>', unsafe_allow_html=True)
    h3.download_button("Download databook", c.databook_path.read_bytes(), f"{c.slug}_databook.xlsx",
                       use_container_width=True)
    st.segmented_control("View", VIEWS, key="view", label_visibility="collapsed")
    view = st.session_state.view or "Summary"
    {"Summary": summary, "Findings": findings, "Impact": impact, "Evidence": evidence}[view](c, a, layer)
    st.markdown(f'<div class="foot">Preliminary analysis on published accounts, not an opinion. '
                f'<a href="{SITE_URL}">About this project</a></div>', unsafe_allow_html=True)
