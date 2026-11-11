"""Streamlit app — drop the data room, review the deal view and the red flags, download, write the memo.

Run (with the virtual environment active):
    streamlit run app.py
Demo on three real companies' published accounts (no upload, no API):
    $env:DD_DEMO=1; streamlit run app.py

The app only wires the layers together (dataroom → pipeline: metrics, rules, deal view → report → ai_memo →
memo_check). It does no calculations of its own and creates no findings.
"""
from __future__ import annotations

import hashlib
import html
import io
import os
import re
import types
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from dd_assistant import demo, europe, sectors
from dd_assistant.ai_memo import EFFORT, MODEL, PROMPT_FILE, MemoError, build_material, load_env, write_memo
from dd_assistant.deal import ADJUSTMENT_STATES, Line, ifrs16_steps, net_debt_steps, qoe_steps, value_at_stake
from dd_assistant.databook import write_databook
from dd_assistant.price import (LEAKAGE_STATES, LEAKAGE_TREATMENTS, MECHANISMS, EnterpriseValue,
                               LeakageItem, LockedBox, PriceInputs, completion_equity,
                               completion_from_analysis, leakage_candidates, locked_box_equity,
                               sensitivity)
from dd_assistant.dataroom import DOCUMENTS, ESEF, SPREADSHEETS, NeedsPdfReading, files_in, read_data_room
from dd_assistant.extract import ExtractionError, data_room_text
from dd_assistant.input_loader import Named
from dd_assistant.issues import DISCLAIMER, IMPLICATIONS, NOT_QUANTIFIABLE, Materiality
from dd_assistant.memo_check import MemoCheck, check_memo, report
from dd_assistant.metrics import ALL_LABELS
from dd_assistant.pipeline import PURPOSES, analyse, choice_effects
from dd_assistant.report import REVIEW_STATES, csv_bytes, fmt_metric, fmt_unit, write_excel
from dd_assistant.rules import SEVERITIES, fy

try:
    import anthropic
except ImportError:   # the demo, and every analysis without a PDF or the memo, runs without the library
    class _NoApi(Exception):
        """Never raised: stands in for the API errors when the library is not installed."""
    anthropic = types.SimpleNamespace(**{n: _NoApi for n in ("AnthropicError", "AuthenticationError", "RateLimitError",
                                                             "APIStatusError", "APIConnectionError")})

DEMO = demo.enabled()   # DD_DEMO=1: three real companies, no upload, no API (see dd_assistant/demo.py)
DATA = Path(__file__).parent / "data"
SAMPLES = {"Duriva — data room in 5 documents, planted issues": DATA / "Duriva_data_room",
           "Velmora — clean company": DATA / "Velmora_data_room.xlsx",
           "TAP Air Portugal — real FY25 accounts (EN)": DATA / "TAP_2025_published.xlsx",
           "Toyota Caetano Portugal — real FY25 accounts (PT)": DATA / "Toyota_Caetano_2025_published.xlsx",
           "Corticeira Amorim — real FY25 accounts (PT)": DATA / "Corticeira_Amorim_2025_published.xlsx",
           "Toyota Caetano Portugal — real FY24 accounts (PT)": DATA / "Toyota_Caetano_2024_published.xlsx",
           "Corticeira Amorim — real FY24 accounts (EN)": DATA / "Corticeira_Amorim_2024_published.xlsx"}
MD_MIME = "text/markdown"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SEVERITY_COLOR = {"High": "#d03b3b", "Medium": "#fab219", "Low": "#8a8f98"}   # status palette; always with a label
# Overview: which findings colour each headline figure, and where to look for the detail.
KPI_RULES = {"Revenue": ["R01", "R02", "R16", "R29"],
             "Diligence-adjusted EBITDA": ["R03", "R04", "R05", "R06", "R19", "R26", "R27"],
             "Cash conversion": ["R10", "R14", "R24"],
             "Adjusted net debt": ["R11", "R13", "R17", "R20", "R21", "R22"],
             "Net working capital": ["R07", "R08", "R09", "R23", "R28"]}
# Within a severity, what moves the price first: EBITDA quality, cash, debt, then revenue, working capital, data.
IMPACT = ["R19", "R05", "R04", "R26", "R27", "R10", "R20", "R21", "R11", "R13", "R22", "R28", "R01", "R02", "R29",
          "R03", "R07", "R09", "R08", "R24", "R06", "R23", "R17", "R12", "R15", "R14", "R16", "R30", "R25", "R18"]
WHERE = {"Quality of earnings": "Deal view", "Net working capital": "Deal view", "Debt": "Deal view",
         "Consistency": "Data room", "Information": "Data room"}
SUMMARY_ROWS = ["vendas", "g_vendas", "cagr_vendas", "gm", "ebitda", "ebitda_m", "ebitda_adj", "ebitda_ex_gain", "cgo", "conv",
                "fco", "dso", "dio", "dpo", "net_debt", "nd_ebitda"]

CSS = """
<style>
[data-testid="stAppDeployButton"], #MainMenu {display: none;}
.block-container {padding-top: 3.2rem; max-width: 1240px;}
.dd-eyebrow {font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: #5b6474; font-weight: 600;}
.dd-title {font-size: 2.1rem; font-weight: 700; color: #1b2333; margin: .1rem 0 .2rem;}
.dd-sub {color: #5b6474; font-size: .92rem; margin-bottom: 1rem;}
.dd-legal {color: #5b6474; font-size: .85rem; margin: -.2rem 0 .3rem;}
.dd-kpis {display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: .4rem 0 1.4rem;}
.dd-kpi {border: 1px solid #e3e7ee; border-radius: 12px; padding: 14px 16px; background: #fff;}
.dd-kpi .l {font-size: .8rem; color: #5b6474;}
.dd-kpi .v {font-size: 1.5rem; font-weight: 650; color: #1b2333; margin: 2px 0; white-space: nowrap;}
.dd-kpi .s {font-size: .8rem; color: #5b6474;}
.dd-kpi .n {font-size: .76rem; color: #1d6b3e; margin-top: 4px;}
.dd-pill {display: inline-flex; align-items: center; gap: 6px; border: 1px solid #e3e7ee; border-radius: 999px;
          padding: 1px 10px; font-size: .78rem; font-weight: 600; color: #1b2333; background: #fff; white-space: nowrap;}
.dd-dot {width: 8px; height: 8px; border-radius: 50%; display: inline-block;}
.dd-find {display: grid; grid-template-columns: 92px 44px 1fr 180px 64px; gap: 12px; align-items: center;
          padding: 9px 4px; border-bottom: 1px solid #eef1f5; font-size: .92rem;}
.dd-find .id {color: #5b6474; font-variant-numeric: tabular-nums;}
.dd-find .area, .dd-find .yr {color: #5b6474; font-size: .84rem;}
.dd-find .plain {display: block; color: #5b6474; font-size: .8rem; margin-top: 1px;}
.dd-section {font-weight: 650; font-size: 1.05rem; color: #1b2333; margin: 1.2rem 0 .4rem;}
.dd-kpi.bad {border-color: #efb3b3; background: #fff7f7;}
.dd-kpi.warn {border-color: #f3d48b; background: #fffbf0;}
.dd-kpi.ok {border-color: #bfe2cc;}
.dd-tag {display: inline-block; font-size: .72rem; font-weight: 650; border-radius: 6px; padding: 1px 7px; margin-top: 6px;}
.dd-tag.bad {background: #fbe1e1; color: #8f1f1f;} .dd-tag.warn {background: #fcefcc; color: #7a5200;}
.dd-tag.ok {background: #e3f4ea; color: #1d6b3e;} .dd-tag.muted {background: #eef0f4; color: #5b6474;}
.dd-steps {display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin: .3rem 0 1.2rem;}
.dd-step {border: 1px solid #e3e7ee; border-radius: 12px; padding: 10px 14px; background: #fff;}
.dd-step.ok {border-color: #bfe2cc; background: #f5fbf7;} .dd-step.warn {border-color: #f3d48b; background: #fffbf0;}
.dd-step.bad {border-color: #efb3b3; background: #fff7f7;}
.dd-step .n {font-size: .72rem; color: #5b6474; text-transform: uppercase; letter-spacing: .06em; font-weight: 650;}
.dd-step .t {font-weight: 650; color: #1b2333; margin: 2px 0;} .dd-step .d {font-size: .8rem; color: #5b6474;}
.dd-issue {display: grid; grid-template-columns: 150px 1fr; gap: 14px; align-items: start; padding: 12px 14px;
           border: 1px solid #e3e7ee; border-left: 4px solid #8a8f98; border-radius: 10px; margin-bottom: 8px; background: #fff;}
.dd-issue.High {border-left-color: #d03b3b;} .dd-issue.Medium {border-left-color: #fab219;}
.dd-issue.Item {border-left-color: #0b3d91;}
.dd-issue .big {font-size: 1.35rem; font-weight: 700; color: #1b2333; line-height: 1.2; font-variant-numeric: tabular-nums;}
.dd-issue .vs {font-size: .76rem; color: #5b6474;}
.dd-issue .h {font-weight: 650; color: #1b2333;} .dd-issue .p {font-size: .88rem; color: #3b4457; margin: 2px 0;}
.dd-issue .w {font-size: .78rem; color: #0b3d91; font-weight: 600;}
.dd-effect {background: #eef4ff; border: 1px solid #d6e2fb; border-radius: 8px; padding: 6px 9px; font-size: .78rem;
            color: #1b2b4d; margin: -2px 0 12px; line-height: 1.4;}
@container (max-width: 620px) {.dd-issue {grid-template-columns: 1fr;}}
.dd-list {container-type: inline-size;}
@container (max-width: 620px) {.dd-find {grid-template-columns: 88px 1fr;} .dd-find .id, .dd-find .area, .dd-find .yr {display: none;}}
.dd-wrap {overflow-x: auto;}
.dd-br {width: 100%; border-collapse: collapse; font-size: .9rem; font-variant-numeric: tabular-nums; margin-bottom: .6rem;}
.dd-br th {text-align: right; color: #5b6474; font-weight: 600; border-bottom: 1px solid #c9d0db; padding: 6px 8px;}
.dd-br th:first-child, .dd-br td.l, .dd-br th.note, .dd-br td.note {text-align: left;}
.dd-br td {padding: 5px 8px; border-bottom: 1px solid #f1f3f6; text-align: right; white-space: nowrap; color: #1b2333;}
.dd-br td.l {white-space: normal; min-width: 240px;}
.dd-br tr.item td.l {padding-left: 20px;}
.dd-br tr.header td {font-weight: 650; color: #0b3d91; padding-top: 12px; border-bottom: none;}
.dd-br tr.subtotal td {font-weight: 650; border-top: 1px solid #c9d0db;}
.dd-br tr.total td {font-weight: 700; border-top: 1.5px solid #1b2333; background: #f5f7fb;}
.dd-br tr.memo td {color: #5b6474; font-style: italic;}
.dd-br td.note {color: #5b6474; font-size: .8rem; white-space: normal; min-width: 160px;}
.dd-banner {border: 1px solid #f3d48b; background: #fffbf0; color: #5c4300; border-radius: 10px; padding: 8px 14px;
            font-size: .9rem; font-weight: 600; margin: .4rem 0 1rem;}
.dd-card-co {font-weight: 700; font-size: 1.15rem; color: #1b2333;}
.dd-card-acc {font-size: .8rem; color: #5b6474; margin-bottom: .5rem;}
.dd-card-find {font-size: .95rem; color: #1b2333; min-height: 4.4em;}
.dd-insights {display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin: .2rem 0 1.2rem;}
.dd-insight {border: 1px solid #d6e2fb; border-top: 4px solid #0b3d91; border-radius: 12px; padding: 12px 16px; background: #fff;}
.dd-insight .t {font-weight: 700; color: #1b2333; font-size: 1rem; margin-bottom: 4px;}
.dd-insight .num {color: #1b2333; font-size: .9rem; margin-bottom: 6px;}
.dd-insight .why {color: #3b4457; font-size: .84rem; margin-bottom: 6px;}
.dd-insight .q {color: #0b3d91; font-size: .82rem; font-weight: 600;}
.dd-chart-title {font-weight: 600; color: #1b2333; font-size: .9rem; margin: .6rem 0 0;}
.dd-hero {font-size: 1.3rem; color: #1b2333; font-weight: 600; margin: .2rem 0 .3rem; max-width: 900px;}
.dd-by {font-size: .85rem; color: #0b3d91; font-weight: 600; margin-bottom: .5rem;}
.dd-co {display: flex; gap: 10px; align-items: center; margin-bottom: .4rem;}
.dd-initial {width: 38px; height: 38px; border-radius: 50%; background: #0b3d91; color: #fff; display: inline-flex;
             align-items: center; justify-content: center; font-weight: 700; flex: none;}
.dd-big {font-size: 2rem; font-weight: 750; color: #0b3d91; line-height: 1.1; margin-top: .3rem;}
.dd-big-l {font-size: .85rem; color: #3b4457; margin-bottom: .5rem;}
.dd-tiles {display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: .3rem 0 1rem;}
.dd-tile {border: 1px solid #d6e2fb; border-radius: 12px; padding: 12px 16px; background: #f7f9fe;}
.dd-tile .v {font-size: 1.7rem; font-weight: 750; color: #0b3d91;} .dd-tile .l {font-size: .84rem; color: #3b4457;}
abbr.dd-term {text-decoration: underline dotted #8a8f98; text-underline-offset: 3px; cursor: help;}
.dd-src {display: block; font-size: .72rem; color: #5b6474; margin-top: 4px;}
.dd-nav {font-size: .85rem; margin-bottom: .6rem;} .dd-nav a {color: #0b3d91; text-decoration: none;}
.dd-foot {border-top: 1px solid #e3e7ee; margin-top: 2.4rem; padding-top: .8rem; font-size: .8rem; color: #5b6474;}
.dd-foot a {color: #0b3d91;}
</style>
"""


def pill(severity: str) -> str:
    return (f"<span class='dd-pill'><span class='dd-dot' style='background:{SEVERITY_COLOR[severity]}'></span>"
            f"{severity}</span>")


@st.cache_resource(max_entries=8, show_spinner=False)
def read_room(files: tuple[tuple[str, bytes], ...], read_pdf: str | None):
    """Layer 1: read the data room (cached by content, so a PDF is only sent to Claude once)."""
    return read_data_room(list(files), read_pdf=read_pdf)


def show_check(check: MemoCheck) -> None:
    """Result of the memo checker: green if there are no errors, red with the detail otherwise."""
    first, _, details = report(check).partition("\n")
    (st.success if check.ok else st.error)(first)
    if details:
        with st.expander("Check details", expanded=not check.ok):
            st.markdown(details)


def cell(line: Line, value, money) -> str:
    if value is None:
        return ""
    if line.unit == "money":
        return f"({money.amount(-value)})" if value < 0 else money.amount(value)
    return fmt_unit(line.unit, value)


def bridge(lines: list[Line], years: list[int], money) -> str:
    """A bridge as a compact table: totals in bold, the source of each line on hover."""
    head = "".join(f"<th>{fy(y)}</th>" for y in years)
    rows = []
    for ln in lines:
        title = f" title='Source: {html.escape(ln.source)}'" if ln.source else ""
        vals = "".join(f"<td>{cell(ln, ln.values.get(y), money)}</td>" for y in years)
        rows.append(f"<tr class='{ln.style}'><td class='l'{title}>{html.escape(ln.label)}</td>{vals}"
                    f"<td class='note'>{html.escape(ln.note)}</td></tr>")
    return (f"<div class='dd-wrap'><table class='dd-br'><tr><th>{money.unit}</th>{head}<th class='note'>Note</th></tr>"
            + "".join(rows) + "</table></div>")


def edited(key: str) -> dict:
    return st.session_state.get(key, {}).get("edited_rows", {})


def headline(r, money) -> tuple[str, str]:
    """The figure that made a rule fire (latest year it fired) and its threshold, for people."""
    year = max(y for y, f in r.fires.items() if f == "Yes")
    value = r.values[year]
    shown = money.fmt(value) if r.rule.limit_fmt == "eur" else fmt_metric(r.rule.metric, value, money)
    return shown, f"{fy(year)} · threshold {r.rule.limit_text()}"


def status(ids: list[str], fired: dict) -> tuple[str, str]:
    """Card colour and tag from the worst finding among the rules behind a figure."""
    hits = [fired[i] for i in ids if i in fired]
    if not hits:
        return "ok", "No flag"
    worst = min(hits, key=lambda r: SEVERITIES.index(r.rule.severity))
    return ("bad" if worst.rule.severity == "High" else "warn"), f"{', '.join(r.rule.id for r in hits)} · {worst.rule.severity}"


@st.cache_resource(max_entries=4, show_spinner=False)
def stored_memo(slug: str):
    """Demo: the stored memo, the material it is checked against and the check, run again now (no AI)."""
    c = demo.CASE_BY_SLUG[slug]
    return demo.memo(c), demo.material(c), demo.check(c)


def show_stored_memo(c: demo.Case) -> None:
    text, material, check = stored_memo(c.slug)
    if text is None:
        st.info("The memo for this company is not stored yet.")
        return
    st.markdown("**Written by the agent and checked automatically, before publication.** Claude Code, running the "
                "project's due-diligence skill, wrote this memo on the author's computer from the material the "
                "engine produced, with no API call. Then `memo_check.py`, which uses no AI, confirmed every figure "
                "against that material, for the year it is cited. The check runs again here, now.")
    first, figures, *rest = report(check).split("\n")
    (st.success if check.ok else st.error)(f"{first} {figures.lstrip('- ')}")
    if rest:
        with st.expander("Check details"):
            st.markdown("\n".join(rest))
    st.caption("The memo reflects the default analysis: findings pending and the default debt-like items. Your "
               "decisions in this session change the Deal view and the databook, not the stored memo.")
    m1, m2, _ = st.columns([1, 1, 3])
    m1.download_button("Download memo (.md)", text.encode("utf-8"), f"{c.slug}_memo.md", mime=MD_MIME)
    m2.download_button("Material (.md)", material.encode("utf-8"), f"{c.slug}_material.md", mime=MD_MIME,
                       help="The material the memo was written from and is checked against.")
    st.divider()
    st.markdown(re.sub(r"^(#+) ", lambda h: "#" * min(len(h.group(1)) + 2, 6) + " ", text, flags=re.M))


NAVY, BLUE, GREY = "#0b3d91", "#5b7fc4", "#a9b6cc"


def waterfall(steps: list[tuple[str, float, str]], money, title: str, key: str) -> None:
    """A bridge as a waterfall: totals in navy, increases in blue, decreases in grey, each bar labelled with its
    value. The steps come from the engine (deal.py); the chart only places the bars."""
    if len(steps) < 2:
        return
    def wrap(text: str, width: int = 14) -> str:   # axis labels on two or three short lines, joined by '|'
        lines, cur = [], ""
        for word in text.split():
            if cur and len(cur) + 1 + len(word) > width:
                lines.append(cur)
                cur = word
            else:
                cur = f"{cur} {word}".strip()
        return "|".join(lines + [cur])

    rows, level = [], 0.0
    for i, (label, value, kind) in enumerate(steps):
        start, end = (0.0, value) if kind == "total" else (level, level + value)
        level = end
        rows.append({"order": i, "label": wrap(label), "name": label, "start": start, "end": end,
                     "text": money.fmt(value) if kind == "total" else
                     ("+" if value > 0 else "") + money.fmt(value),
                     "colour": NAVY if kind == "total" else BLUE if value > 0 else GREY,
                     "top": max(start, end)})
    df = pd.DataFrame(rows)
    x = alt.X("label:N", sort=list(df["label"]), title=None,
              axis=alt.Axis(labelAngle=0, labelLimit=160, labelExpr="split(datum.label, '|')", labelFontSize=11))
    bars = alt.Chart(df).mark_bar(cornerRadius=3).encode(
        x=x, y=alt.Y("start:Q", axis=None), y2="end:Q", color=alt.Color("colour:N", scale=None),
        tooltip=[alt.Tooltip("name:N", title=" "), alt.Tooltip("text:N", title="Value")])
    labels = alt.Chart(df).mark_text(dy=-8, fontSize=12, fontWeight=600, color="#1b2333").encode(
        x=x, y=alt.Y("top:Q", axis=None), text="text:N")
    st.markdown(f"<div class='dd-chart-title'>{html.escape(title)}</div>", unsafe_allow_html=True)
    st.altair_chart((bars + labels).properties(height=260).configure_view(stroke=None), width="stretch", key=key)


def nwc_chart(view, money, key: str) -> None:
    """Net working capital at each year-end, with the average of the year-ends as the indicative peg line."""
    years = [y for y in view.bs_years if view.nwc_values.get(y) is not None]
    if len(years) < 2 or view.nwc_average is None:
        return
    df = pd.DataFrame([{"year": fy(y), "nwc": view.nwc_values[y], "text": money.fmt(view.nwc_values[y])}
                       for y in years])
    base = alt.Chart(df).encode(x=alt.X("year:N", title=None, axis=alt.Axis(labelAngle=0)))
    bars = base.mark_bar(color=NAVY, cornerRadius=3, size=48).encode(y=alt.Y("nwc:Q", axis=None))
    text = base.mark_text(dy=-8, fontSize=12, fontWeight=600, color="#1b2333").encode(y="nwc:Q", text="text:N")
    avg = alt.Chart(pd.DataFrame([{"avg": view.nwc_average}])).mark_rule(color="#fab219", strokeDash=[6, 4],
                                                                          size=2).encode(y="avg:Q")
    st.markdown(f"<div class='dd-chart-title'>Net working capital at year-end ({money.unit}); dashed line: "
                f"average of the year-ends, {html.escape(money.fmt(view.nwc_average))} (indicative peg reference)"
                "</div>", unsafe_allow_html=True)
    st.altair_chart((bars + text + avg).properties(height=220).configure_view(stroke=None), width="stretch",
                    key=key)


def key_insights(c: "demo.Case") -> None:
    """The three talking points of the case note, first thing on the company page."""
    cards = demo.insights(c)
    if not cards:
        return
    up = lambda t: t[:1].upper() + t[1:]
    st.markdown("<div class='dd-section'>Key insights</div><div class='dd-insights'>" + "".join(
        f"<div class='dd-insight'><div class='t'>{html.escape(i['title'])}</div>"
        f"<div class='num'>{html.escape(up(i['number']))}</div>"
        f"<div class='why'><b>Why it matters in a deal.</b> {html.escape(up(i['why']))}</div>"
        f"<div class='q'>Ask management: “{html.escape(i['question'])}”</div></div>" for i in cards)
        + "</div>", unsafe_allow_html=True)


def tour_move(step: int) -> None:
    st.session_state["tour-step"] = step


@st.dialog("The 60-second tour", width="large")
def tour(c: "demo.Case", a) -> None:
    """Five steps, one sentence each: reading check, key insight, bridge, a red flag with its source, the Excel."""
    steps = demo.tour_steps(c, a)
    i = min(st.session_state.get("tour-step", 0), len(steps) - 1)
    title, text = steps[i]
    st.progress((i + 1) / len(steps), text=f"Step {i + 1} of {len(steps)} · {title}")
    st.markdown(text)
    B, L = a.view.bs_years[-1], a.view.pl_years[-1]
    if i == 0:
        st.dataframe(pd.DataFrame([{"Check": x["Check"], "Year": fy(x["Year"]),
                                    "Rebuilt": a.money.amount(x["Rebuilt from the lines"]),
                                    "Published": a.money.amount(x["As published"]),
                                    "Result": "✓ matches" if x["OK"] else "✗ does not match"} for x in a.checks]),
                     hide_index=True, width="stretch")
    elif i == 1:
        first = demo.insights(c)[0]
        st.info(f"**Why it matters in a deal.** {first['why'][:1].upper() + first['why'][1:]}")
    elif i == 2:
        waterfall(net_debt_steps(a.view, B), a.money, f"Net debt bridge, {fy(B)} ({a.money.unit})", "tour-nd")
    elif i == 3 and a.findings:
        flag = min(a.findings, key=lambda r: SEVERITIES.index(r.rule.severity))
        st.markdown(f"**Evidence.** {flag.evidence}")
        pages = [f"{sheet}: {page}" for sheet, page in (c.page_of or {}).items() if f"{sheet}!" in flag.evidence]
        if pages:
            st.markdown("**Where it is in the report.** " + "; ".join(pages) + ".")
        st.markdown(f"**Question for management.** {flag.rule.question}")
    elif i == 4 and c.databook_path.exists():
        st.download_button("Download the databook (Excel)", c.databook_path.read_bytes(), f"{c.slug}_databook.xlsx",
                           mime=XLSX_MIME, type="primary", key="tour-book")
    b1, b2, _ = st.columns([1, 1, 3])
    if i > 0:
        b1.button("Back", on_click=tour_move, args=(i - 1,), width="stretch", key="tour-back")
    if i < len(steps) - 1:
        b2.button("Next", on_click=tour_move, args=(i + 1,), type="primary", width="stretch", key="tour-next")
    elif b2.button("Finish", type="primary", width="stretch", key="tour-end"):
        st.session_state["tour-step"] = 0
        st.rerun()


def term(text: str, key: str | None = None) -> str:
    """A term with its plain-words definition on hover (the glossary at the bottom says the same)."""
    meaning = demo.GLOSSARY.get(key or text)
    return (f"<abbr class='dd-term' title='{html.escape(meaning, quote=True)}'>{html.escape(text)}</abbr>"
            if meaning else html.escape(text))


def where(source: str) -> str:
    """Where a figure comes from, for people: the report page in the demo (TAP), else the statement and cell."""
    if not source:
        return ""
    sheet = source.split("!")[0].strip()
    label = case.page_of.get(sheet, "") if DEMO and case else ""
    return f"<span class='dd-src' title='{html.escape(source, quote=True)}'>Source: {html.escape(label or source)}</span>"


def footer() -> None:
    st.markdown(f"<div class='dd-foot'>Built by {demo.AUTHOR} · <a href='{demo.GITHUB}'>GitHub</a> · "
                f"<a href='{demo.LINKEDIN}'>LinkedIn</a><br>Limits: " + " · ".join(demo.LIMITS) + ".</div>",
                unsafe_allow_html=True)


def open_case(slug: str | None) -> None:
    if slug:
        st.query_params["company"] = slug
    else:
        st.query_params.clear()


@st.cache_resource(show_spinner=False)
def verification() -> dict:
    return demo.verification()


def glossary() -> None:
    with st.expander("Glossary: the terms on this site, in one sentence each"):
        st.markdown("\n".join(f"- **{term}**: {text}" for term, text in demo.GLOSSARY.items()))


def landing() -> None:
    """Demo home page: what it does and for whom, three real companies, what you get, how it is verified."""
    tap = demo.CASE_BY_SLUG["tap"]
    st.markdown("<div class='dd-eyebrow'>Live demo · published accounts</div><div class='dd-title'>DD Assistant</div>"
                f"<div class='dd-hero'>{html.escape(demo.TAGLINE)}.</div>"
                f"<div class='dd-by'>{html.escape(demo.BUILT_BY)}</div>"
                f"<div class='dd-sub'>{html.escape(demo.FOR_WHOM)} <b>Limits:</b> "
                + html.escape("; ".join(x[0].lower() + x[1:] for x in demo.LIMITS)) + ".</div>",
                unsafe_allow_html=True)
    b1, b2, b3, _ = st.columns([1.2, 1.3, 1, 1.5])
    b1.button("Open the TAP analysis", type="primary", width="stretch", on_click=open_case, args=("tap",))
    if tap.databook_path.exists():
        b2.download_button("Download the TAP databook (Excel)", tap.databook_path.read_bytes(), "tap_databook.xlsx",
                           mime=XLSX_MIME, width="stretch")
    b3.link_button("See the code", demo.GITHUB, width="stretch")
    st.markdown(f"<div class='dd-banner'>{html.escape(demo.WARNING)} {html.escape(demo.DATA_NOTE)}</div>",
                unsafe_allow_html=True)
    tour = Path(__file__).parent / "docs" / "images" / "demo-tour.gif"
    if tour.exists():
        st.image(str(tour), caption="20 seconds on TAP: the headline figures with their pages, the net debt bridge, a red flag with its source, the Excel.")

    st.markdown("<div class='dd-section'>How it works</div>", unsafe_allow_html=True)
    for col, (icon, title, text) in zip(st.columns(len(demo.PROCESS)), demo.PROCESS):
        with col.container(border=True):
            st.markdown(f":material/{icon}: **{title}**")
            st.caption(text)

    st.markdown("<div class='dd-section'>Three real companies, published accounts FY2023 to FY2025</div>",
                unsafe_allow_html=True)
    for col, c in zip(st.columns(len(demo.CASES), gap="medium"), demo.CASES):
        with col.container(border=True):
            st.markdown(f"<div class='dd-co'><span class='dd-initial'>{html.escape(c.company[0])}</span>"
                        f"<span><div class='dd-card-co'>{html.escape(c.company)}</div>"
                        f"<div class='dd-card-acc'>{html.escape(c.accounts)}</div></span></div>"
                        f"<div class='dd-big'>{html.escape(c.big)}</div><div class='dd-big-l'>"
                        f"{html.escape(c.big_label)}</div><div class='dd-card-find'>{html.escape(c.headline)}</div>",
                        unsafe_allow_html=True)
            st.button("Open the analysis", key=f"open-{c.slug}", type="primary", width="stretch",
                      on_click=open_case, args=(c.slug,))

    st.markdown("<div class='dd-section'>What you get: the databook, in Excel</div>", unsafe_allow_html=True)
    g1, g2 = st.columns([3, 2], gap="large")
    image = Path(__file__).parent / "docs" / "images" / "databook-net-debt.png"
    if image.exists():
        g1.image(str(image), caption="The Net Debt sheet of TAP's databook, as Excel draws it.")
    g2.markdown("- **QoE:** reported to diligence-adjusted EBITDA, each adjustment with its status and document.\n"
                "- **Net debt:** borrowings less cash, then every debt-like item with its classification.\n"
                "- **NWC:** the lines in working capital, by policy, with the average as the peg reference.\n"
                "- **Issues & requests:** each finding with its evidence, question and document to request.\n"
                "- **Live formulas:** figures in blue with their source cell, decisions in yellow; Excel recalculates, "
                "and a Checks sheet compares every total with the code.")

    v = verification()
    st.markdown("<div class='dd-section'>How it is verified</div>", unsafe_allow_html=True)
    tiles = [(f"{v['tests']}" if v["tests"] else "—", "automated tests, run on every change"),
             (f"{v['checks_passed']} of {v['checks']}", "published subtotals rebuilt from the lines read, on the "
                                                        "three companies"),
             (f"{v['figures']}", f"memo figures checked against the engine's material; {v['unmatched']} without a "
                                 "source")]
    det = demo.detection()
    if det:
        tiles.append((f"{det['detected']} of {det['scored']}", "known distortions planted one at a time in the real "
                                                               "accounts were detected; the misses are published"))
    st.markdown("<div class='dd-tiles'>" + "".join(f"<div class='dd-tile'><div class='v'>{html.escape(a)}</div>"
                                                     f"<div class='l'>{html.escape(b)}</div></div>" for a, b in tiles)
                + "</div>", unsafe_allow_html=True)
    m1, m2 = st.columns(2, gap="large")
    with m1:
        st.markdown("**Measured** (on this page, now)")
        st.markdown("\n".join(f"- {x}" for x in (
            "The tests above pass on every change, including parity with a hand-built Excel template.",
            "Every subtotal the companies published is rebuilt from the lines read.",
            "Every figure of the stored memos is found in the engine's material, for the year it is cited.",
            "A benchmark plants known distortions in the real accounts and counts the ones the rules catch "
            "(docs/DETECTION.md in the repository lists every run, misses included).")))
    with m2:
        st.markdown("**Not measured**")
        st.markdown("\n".join(f"- {x}" for x in demo.NOT_MEASURED))
    with st.expander("How you check it yourself"):
        st.markdown("\n".join(f"{i}. {x}" for i, x in enumerate(demo.HOW_TO_CHECK, 1)))
    glossary()
    footer()


st.set_page_config(page_title="DD Assistant · first-pass financial due diligence" if DEMO else "DD Assistant",
                   page_icon=":material/fact_check:", layout="wide",
                   initial_sidebar_state="collapsed" if DEMO else "auto")
st.markdown(CSS, unsafe_allow_html=True)
if not DEMO:
    load_env()
has_key = not DEMO and bool(os.environ.get("ANTHROPIC_API_KEY"))
case = demo.CASE_BY_SLUG.get(st.query_params.get("company", "")) if DEMO else None
if DEMO and case is None:
    landing()
    st.stop()

# ---------------------------------------------------------------- input
with st.sidebar:
    st.markdown("### DD Assistant")
    st.caption("Preliminary financial due diligence · European market · EUR")
if DEMO:   # no upload: the visitor picks one of the three companies
    with st.sidebar:
        st.markdown("**About this demo**")
        st.caption("Three real companies, on their published FY2025 accounts. Nothing is uploaded and no AI is "
                   "called. A first pass for an analyst to review, not an opinion.")
        st.button("← All companies", on_click=open_case, args=(None,), width="stretch")
        slugs = [c.slug for c in demo.CASES]
        st.radio("Company", slugs, index=slugs.index(case.slug), format_func=lambda k: demo.CASE_BY_SLUG[k].company,
                 key="demo-company", on_change=lambda: open_case(st.session_state["demo-company"]))
    uploaded = None
    files = tuple(files_in([case.path]))
    name = case.path.name
else:
    with st.sidebar:
        uploaded = st.file_uploader(
            "Data room", type=[x.strip(".") for x in SPREADSHEETS + DOCUMENTS + ESEF], accept_multiple_files=True,
            help="Drop every document at once: Excel statements and schedules (in one file or many), the management "
                 "report, the audit report, contracts (PDF, Word, text). Portuguese, Spanish, French, German, Italian "
                 "or English statements, in euros. No template needed. A listed company: drop its ESEF annual report "
                 "package (.zip, from filings.xbrl.org) and every figure is read from its IFRS tag.")
        sample = st.radio("…or open a sample data room", list(SAMPLES), disabled=bool(uploaded))
    if uploaded:
        files = tuple((f.name, f.getvalue()) for f in uploaded)
        name = files[0][0] if len(files) == 1 else f"{len(files)} documents"
    else:
        files = tuple(files_in([SAMPLES[sample]]))
        name = SAMPLES[sample].name
file_key = hashlib.sha1(b"".join(n.encode() + c for n, c in files)).hexdigest()[:12]

try:
    with st.spinner("Reading the data room…"):
        ext = read_room(files, st.session_state.get(f"pdf-{file_key}"))
except NeedsPdfReading as e:
    st.markdown("<div class='dd-eyebrow'>Data room without Excel statements</div>"
                f"<div class='dd-title'>{html.escape(name)}</div>", unsafe_allow_html=True)
    st.info("The financial statements are only in a PDF. Claude reads it (vision) and returns every figure exactly "
            "as printed, with its page; units and signs are converted by the code, and you review every line before "
            "relying on it. The other documents are read on this computer, for free. Typical cost: USD 0.10–0.40.")
    pdf = st.selectbox("PDF with the financial statements", e.pdfs)
    if st.button("Read the statements with Claude", type="primary", disabled=not has_key):
        st.session_state[f"pdf-{file_key}"] = pdf
        st.rerun()
    if not has_key:
        st.warning("Add ANTHROPIC_API_KEY to the .env file (see .env.example) and restart the app to read PDFs.")
    st.stop()
except ExtractionError as e:
    st.error(str(e))
    st.stop()
except anthropic.AnthropicError as e:
    st.error(f"Claude API error while reading the PDF: {e}")
    st.stop()

if DEMO and case.prior:   # three years: the earlier one from the prior year's report (history.py)
    ext = demo.extraction(case)
suggested, words = sectors.suggest(ext.source_text, ext.company)
c_suggested, c_why = europe.suggest(ext.source_text, ext.company)
keys = [s.key for s in sectors.SECTORS]
codes = list(europe.COUNTRY_BY_CODE)
with (st.sidebar.expander("Settings of this analysis (fixed in the demo)") if DEMO else st.sidebar):
    if DEMO:
        st.caption("The stored memo was written and checked with these three settings.")
    purpose = st.selectbox("Purpose", list(PURPOSES), format_func=PURPOSES.get, key=f"purpose-{file_key}",
                           index=list(PURPOSES).index(case.purpose) if DEMO else 0, disabled=DEMO,
                           help="M&A is the focus; the same analysis serves a lender or an owner. Only the way the "
                                "memo is written changes.")
    purpose_effect = st.empty()
    country = st.selectbox("Country of the target", codes, key=f"country-{file_key}",
                           index=codes.index(case.country if DEMO else c_suggested.code if c_suggested else "EU"),
                           disabled=DEMO,
                           format_func=lambda k: europe.COUNTRY_BY_CODE[k].name,
                           help="Sets the accounting framework and the statutory tax rate (R25).")
    st.caption(f"Suggested from {c_why}." if c_suggested and country == c_suggested.code and c_why else
               "Chosen by you." if c_suggested and country != c_suggested.code else "Nothing points to a country.")
    country_effect = st.empty()
    sector_key = st.selectbox("Sector", keys, index=keys.index(case.sector if DEMO else suggested.key),
                              key=f"sector-{file_key}", disabled=DEMO,
                              format_func=lambda k: sectors.SECTOR_BY_KEY[k].name,
                              help="Calibrates a few thresholds, sets the peer benchmarks and adds the sector's "
                                   "questions to the request list.")
    st.caption(f"Suggested from the file: {', '.join(words)}." if words and sector_key == suggested.key else
               "Chosen by you." if sector_key != suggested.key else "No sector keyword found: choose one.")
    sector_effect = st.empty()
    st.divider()
    if DEMO:
        st.caption("Demo: no upload and no AI call. The engine runs here on the published accounts stored in the "
                   "repository; your decisions stay in this browser session.")
    else:
        st.caption("Claude API: connected" if has_key else
                   "Claude API: not configured. Needed only to read statements from a PDF and to write the memo.")
        st.caption("Every document is read and analysed on this computer. Data goes to the Claude API only when you "
                   "read statements from a PDF or write the memo.")

# ---------------------------------------------------------------- reviewer input (read before the analysis)
src_key, docs_key = f"src-{file_key}", f"docs-{file_key}"
adj_key, own_key, inc_key = f"adj-{file_key}", f"own-{file_key}", f"inc-{file_key}"
overrides: dict[str, dict[int, float | None]] = {}
for idx, changes in edited(src_key).items():
    key = ext.items[int(idx)]["key"]
    for col, val in changes.items():
        if col.startswith("FY"):
            overrides.setdefault(key, {})[2000 + int(col[2:])] = None if val is None or pd.isna(val) else float(val)
docs = list(ext.data.documents)
for idx, ch in edited(docs_key).items():
    if "Received" in ch:
        docs[int(idx)] = (docs[int(idx)][0], bool(ch["Received"]))
decisions = {ext.data.adjustments[int(i)].name: ch["Status"] for i, ch in edited(adj_key).items() if "Status" in ch}
analyst = []
for row in st.session_state.get(own_key, {}).get("added_rows", []):
    label = (row.get("Adjustment") or "").strip()
    if label:
        analyst.append(Named(label, {y: float(row[f"FY{str(y)[2:]}"]) for y in ext.data.pl_years[-3:]
                                     if row.get(f"FY{str(y)[2:]}") not in (None, "") and not pd.isna(row[f"FY{str(y)[2:]}"])}))
include = {int(i): bool(ch["Include"]) for i, ch in edited(inc_key).items() if "Include" in ch}

mat_key, imp_key = f"mat-{file_key}", f"imp-{file_key}"
materiality = Materiality(st.session_state.get(f"{mat_key}-pl", 5.0) / 100, st.session_state.get(f"{mat_key}-bs", 1.0) / 100)
a = analyse(ext, sector_key, country, overrides, docs, decisions, analyst, include, purpose, materiality)
chosen = {a.issues[int(i)].key: ch["Deal implication"] for i, ch in edited(imp_key).items()
          if "Deal implication" in ch and int(i) < len(a.issues)}
if chosen:   # the reviewer changed an implication: it flows to the databook and the memo material
    a = analyse(ext, sector_key, country, overrides, docs, decisions, analyst, include, purpose, materiality, chosen)
data, metrics, results, al, view, money = a.data, a.metrics, a.results, a.findings, a.view, a.money
review_key = f"review-{file_key}-{'-'.join(r.rule.id for r in al)}"
reviews = {r.rule.id: ("Pending", "") for r in al}
for idx, ch in edited(review_key).items():
    rid = al[int(idx)].rule.id
    state, comment = reviews[rid]
    reviews[rid] = (ch.get("Status", state), ch.get("Comment", comment) or "")
effects = choice_effects(a)   # what the choices in the sidebar change, shown right under each of them
for box, key in ((purpose_effect, "purpose"), (country_effect, "country"), (sector_effect, "sector")):
    box.markdown(f"<div class='dd-effect'><b>What this changes:</b> {html.escape(effects[key])}</div>",
                 unsafe_allow_html=True)

# ---------------------------------------------------------------- header
L = data.pl_years[-1]
B = view.bs_years[-1]
years3 = data.pl_years[-3:]
if DEMO:
    st.markdown("<div class='dd-nav'><a href='./' target='_self'>← All companies</a> · " + " · ".join(
        f"<a href='?company={c.slug}' target='_self'>{html.escape(c.company)}</a>" for c in demo.CASES if c is not case)
        + "</div>", unsafe_allow_html=True)
st.markdown(f"<div class='dd-eyebrow'>{html.escape(PURPOSES[a.purpose])} · {html.escape(a.sector.name)} · "
            f"{html.escape(a.country.name if a.country else 'Europe')}</div>"
            + (f"<div class='dd-title'>{html.escape(case.company)}</div>"
               f"<div class='dd-legal'>{html.escape(ext.company)}</div>"
               f"<div class='dd-sub'>Consolidated accounts {fy(years3[0])}–{fy(L)} · Source: "
               f"{html.escape(case.pages)} · figures in {money.unit_long}</div>" if DEMO else
               f"<div class='dd-title'>{html.escape(ext.company)}</div>"
               f"<div class='dd-sub'>{html.escape(name)} · {fy(years3[0])}–{fy(L)} · figures in {money.unit_long}"
               "</div>"), unsafe_allow_html=True)
if DEMO:
    st.markdown(f"<div class='dd-banner'>{html.escape(demo.WARNING)} Figures as published; the Data room tab "
                "shows the source of each line.</div>", unsafe_allow_html=True)
    if case.context:
        source, url = case.context_source
        st.caption(f"Context, not used in the analysis or the memo: {case.context} Source: [{source}]({url}).")
    downloads = st.container()   # filled after Deal view, so the databook carries the visitor's price inputs
if not a.checks_ok:
    st.warning("Reading check failed: a subtotal rebuilt from the lines read does not match the published one. "
               "A line may be missing or misclassified — see Data room before relying on the figures.")

if DEMO:
    if st.button("Take the 60-second tour", icon=":material/play_circle:", key="tour-open"):
        st.session_state["tour-step"] = 0
        tour(case, a)   # a dialog reruns on its own when its buttons are used
    key_insights(case)

tab_ov, tab_ki, tab_deal, tab_rf, tab_sec, tab_src, tab_rules, tab_m, tab_ai = st.tabs(
    ["Overview", f"Key issues ({len(a.issues)})", "Deal view", f"Red flags ({len(al)})", "Sector", "Data room",
     "Rulebook", "Metrics", "Memo" if DEMO else "AI memo"])

# ---------------------------------------------------------------- overview
with tab_ov:
    g = lambda key, year=L: metrics[key].get(year)
    nwc_pct = None if not data.v("vendas", B) or view.nwc_values[B] is None else view.nwc_values[B] / data.v("vendas", B)
    kpis = [
        ("Revenue", money.fmt(g("vendas")), f"{fmt_metric('g_vendas', g('g_vendas'))} growth vs {fy(data.pl_years[-2])}"),
        ("Diligence-adjusted EBITDA", money.fmt(view.ebitda_dd[L]),
         f"Before adjustments {money.fmt(view.ebitda[L])}" + (f" · mgmt {money.fmt(view.ebitda_mgmt[L])}"
                                                              if view.ebitda_mgmt else "")),
        ("Cash conversion", fmt_metric("conv", g("conv")), "Operating cash / reported EBITDA"),
        ("Adjusted net debt", money.fmt(view.net_debt_adjusted[B]),
         (f"{view.net_debt_adjusted[B] / view.ebitda_dd[L]:.2f}x EBITDA · "
          if view.ebitda_dd[L] > 0 and view.net_debt_adjusted[B] is not None else "")
         + f"of which borrowings less cash {money.fmt(view.net_debt_reported[B])}"),
        ("Net working capital", money.fmt(view.nwc_values[B]),
         f"{fmt_unit('pct', nwc_pct)} of revenue" + (f" · average {money.fmt(view.nwc_average)}"
                                                    if len(view.bs_years) > 1 else "")),
    ]
    fired = {r.rule.id: r for r in al}
    by = {k: sum(r.rule.severity == k for r in al) for k in SEVERITIES}

    # ---- start here: the four things to look at, in order
    failed = [c for c in a.checks if not c["OK"]]
    under_review = [x for x in data.adjustments if a.decisions.get(x.name, "Under review") == "Under review"]
    missing_docs = [d for d, ok in data.documents if not ok]
    steps = [
        ("bad" if failed else "ok", "1 · Reading", f"{len(failed)} subtotal(s) do not match" if failed else
         f"All {len(a.checks)} subtotals match" if a.checks else "No subtotal to check",
         "Correct the line in Data room before relying on the figures" if failed else
         "The figures read add up to what the company published"),
        ("bad" if by["High"] else "warn" if al else "ok", "2 · Red flags",
         f"{len(al)} to review · {by['High']} high" if al else "No red flag",
         "Start with the high ones below, then the Red flags tab" if al else "No rule fired on the data provided"),
        ("warn" if under_review else "ok" if data.adjustments else "muted", "3 · Management adjustments",
         f"{len(under_review)} to decide · {money.fmt(view.upside[L])} not yet accepted" if under_review else
         "All decided" if data.adjustments else "None presented",
         "Accept or reject each one in Deal view" if under_review else "EBITDA bridge in Deal view"),
        ("warn" if missing_docs else "ok", "4 · Documents", f"{len(missing_docs)} of {len(data.documents)} missing"
         if missing_docs else "All key documents received", "Ask for them (request list) or tick them in Data room"
         if missing_docs else "Nothing outstanding"),
    ]
    st.markdown("<div class='dd-steps'>" + "".join(
        f"<div class='dd-step {c}'><div class='n'>{n}</div><div class='t'>{html.escape(t)}</div>"
        f"<div class='d'>{html.escape(d)}</div></div>" for c, n, t, d in steps) + "</div>", unsafe_allow_html=True)

    # ---- the headline figures, coloured by the findings behind them
    cards = []
    sources = {"Revenue": data.sources.get("vendas", ""), "Diligence-adjusted EBITDA": data.sources.get("opinc", "")
               or data.sources.get("vendas", ""), "Cash conversion": data.sources.get("cgo", "")
               or data.sources.get("fco", ""), "Adjusted net debt": data.sources.get("fin_lp", ""),
               "Net working capital": data.sources.get("inv", "") or data.sources.get("cli", "")}
    notes = {"Net working capital": a.sector.negative_nwc_note
             if view.nwc_values[B] is not None and view.nwc_values[B] < 0 else ""}
    for l, v, sub in kpis:
        cls, tag = status(KPI_RULES[l], fired)
        year = fy(L if "EBITDA" in l or l in ("Revenue", "Cash conversion") else B)
        why = "; ".join(f"{i} {fired[i].rule.name}" for i in KPI_RULES[l] if i in fired)   # what the colour means
        note = f"<div class='n'>{html.escape(notes[l])}</div>" if notes.get(l) else ""
        label = {"Diligence-adjusted EBITDA": term(l), "Adjusted net debt": term(l, "Net debt"),
                 "Net working capital": term(l, "NWC")}.get(l, html.escape(l))
        cards.append(f"<div class='dd-kpi {cls}'><div class='l'>{label} · {year}</div><div class='v'>{v}</div>"
                     f"<div class='s'>{sub}</div>{note}{where(sources.get(l, ''))}"
                     f"<span class='dd-tag {cls}' title='{html.escape(why)}'>{html.escape(tag)}</span></div>")
    st.markdown("<div class='dd-kpis'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    w1, w2 = st.columns(2, gap="large")
    with w1:
        waterfall(net_debt_steps(view, B), money, f"Net debt bridge, {fy(B)} ({money.unit})", "ov-nd")
    with w2:
        steps = qoe_steps(view, L)
        if len(steps) <= 2 and ifrs16_steps(view, data, L):   # no adjustment to show: show the lease effect
            waterfall(ifrs16_steps(view, data, L), money, f"EBITDA and the lease payments, {fy(L)} ({money.unit})",
                      "ov-16")
        else:
            waterfall(steps, money, f"EBITDA bridge, {fy(L)} ({money.unit})", "ov-qoe")

    # ---- where it goes wrong: the figure, the threshold, in plain words, and where to look
    st.markdown(f"<div class='dd-section'>Key issues, by amount at stake · {len(al)} "
                f"{term('red flags', 'Red flag')} and {len(a.issues) - len(al)} net debt items</div>"
                + " ".join(f"{pill(k)} <span style='color:#5b6474;font-size:.85rem'>{by[k]}</span>&nbsp;&nbsp;"
                           for k in SEVERITIES), unsafe_allow_html=True)
    if not a.issues:
        st.success("No rule fired: no red flags on the data provided.")
    cards = []
    for i in a.issues[:6]:
        r = fired.get(i.key)
        big = money.fmt(i.amount) if i.amount is not None else "n/q"
        vs = (NOT_QUANTIFIABLE if i.amount is None else f"{i.amount_label}, {fy(i.year)}" if r else i.amount_label)
        head = (f"{pill(i.severity)} {i.key} · {html.escape(i.title)}" if r else
                f"<span class='dd-pill'>{html.escape(i.kind)}</span> {html.escape(i.title)}")
        plain = (r.rule.plain + (f" The ratio: {' · '.join(headline(r, money))}." if r else "")) if r else i.treatment
        cards.append(f"<div class='dd-issue {i.severity or 'Item'}'><div><div class='big'>{html.escape(big)}</div>"
                     f"<div class='vs'>{html.escape(vs)}</div></div><div><div class='h'>{head}</div>"
                     f"<div class='p'>{html.escape(plain)}"
                     + (f" <i>{html.escape(i.note[0].upper() + i.note[1:])}.</i>" if i.note else "") + "</div>"
                     f"<div class='w'>{html.escape(i.implication)} · Ask: {html.escape(i.question.split('?')[0])}"
                     f"{'?' if '?' in i.question else ''}</div></div></div>")
    st.markdown("<div class='dd-list'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    if len(a.issues) > 6:
        st.caption(f"…and {len(a.issues) - 6} more in the Key issues tab. Materiality: {materiality.text()} "
                   f"({money.fmt(a.thresholds.get('pl'))} and {money.fmt(a.thresholds.get('bs'))}).")

    st.markdown("<div class='dd-section'>Financial summary</div>", unsafe_allow_html=True)
    summary = pd.DataFrame([[ALL_LABELS[k]] + [fmt_metric(k, metrics[k].get(y), money) for y in years3]
                            for k in SUMMARY_ROWS if not k.startswith("cagr") or metrics[k].get(L) is not None], columns=[f"{money.unit} unless stated"] + [fy(y) for y in years3])
    st.dataframe(summary, hide_index=True, width="stretch", height=35 * (len(summary) + 1) + 3)
    found = len(ext.items) - len(ext.missing)
    passed = sum(c["OK"] for c in a.checks)
    st.caption(f"Reading checks: {passed} of {len(a.checks)} passed. Data coverage: {found} of {len(ext.items)} "
               "standard line items identified" + (f". Not found: {', '.join(ext.missing)}." if ext.missing else "."))

# ---------------------------------------------------------------- key issues
with tab_ki:
    st.caption("Findings and net debt items in one list, ordered by the amount at stake, as a due diligence report "
               "lists its key issues. The amount is computed from the lines that made each rule fire.")
    k1, k2, k3 = st.columns([1, 1, 3])
    k1.number_input("Materiality: % of reported EBITDA (earnings items)", min_value=0.0, max_value=50.0, value=5.0,
                    step=0.5, key=f"{mat_key}-pl")
    k2.number_input("Materiality: % of revenue (balance sheet items)", min_value=0.0, max_value=20.0, value=1.0,
                    step=0.25, key=f"{mat_key}-bs")
    k3.markdown(f"<div class='dd-effect' style='margin-top:1.7rem'><b>What this changes:</b> in {fy(L)} the "
                f"thresholds are {money.fmt(a.thresholds.get('pl'))} and {money.fmt(a.thresholds.get('bs'))}. A "
                "finding below its threshold becomes Low, with the note 'below materiality'.</div>",
                unsafe_allow_html=True)
    if a.issues:
        table = pd.DataFrame([{"Issue": f"{i.key} · {i.title}" if i.kind == "Finding" else i.title, "Type": i.kind,
                               "Severity": i.severity or "–",
                               "Amount at stake": money.fmt(i.amount) if i.amount is not None else "n/q",
                               "What the amount is": (f"{i.amount_label}, {fy(i.year)}" if i.kind == "Finding"
                                                      and i.amount is not None else i.amount_label)
                               + (f" — {i.note}" if i.note else ""),
                               "Deal implication": i.implication,
                               "Evidence from the notes": (i.evidence_state + (f" by {i.evidence_note}"
                                                                               if i.evidence_note else ""))
                               if ext.notes else "notes not read",
                               "What the note says": i.evidence_text, "Typical treatment": i.treatment,
                               "Question for management": i.question, "Document to request": i.request}
                              for i in a.issues])
        st.data_editor(table, key=imp_key, hide_index=True, width="stretch", height=35 * (len(table) + 1) + 3,
                       disabled=[c for c in table.columns if c != "Deal implication"],
                       column_config={"Issue": st.column_config.TextColumn(width="medium"),
                                      "Deal implication": st.column_config.SelectboxColumn(
                                          options=list(IMPLICATIONS), required=True, width="medium"),
                                      "What the note says": st.column_config.TextColumn(width="large"),
                                      "Typical treatment": st.column_config.TextColumn(width="large"),
                                      "Question for management": st.column_config.TextColumn(width="large")})
        st.caption(f"Deal implication: change it in the table (yellow cells in the databook's Key Issues sheet). "
                   f"{DISCLAIMER} Nothing here is legal advice or a view on price. 'n/q': {NOT_QUANTIFIABLE}.")
    else:
        st.success("No rule fired and no net debt item was found.")

# ---------------------------------------------------------------- deal view
price = None   # the price mechanism the analyst sets in Deal view (carried into the databook)
with tab_deal:
    st.caption("The three numbers a deal team asks for first, calculated by the code from the lines in Data room. "
               + ("Your decisions below flow into the databook download. " if DEMO else
                  "Your decisions below flow into the Excel download and the AI memo. ")
               + "Hover a line to see its source.")
    for note in view.incomplete:
        st.warning(note)
    st.markdown(f"<div class='dd-section'>{term('Quality of earnings', 'QoE')}</div>", unsafe_allow_html=True)
    q1, q2 = st.columns(2, gap="large")
    with q1:
        waterfall(qoe_steps(view, L), money, f"EBITDA bridge, {fy(L)} ({money.unit})", "dv-qoe")
    with q2:
        waterfall(ifrs16_steps(view, data, L), money, f"EBITDA before IFRS 16, {fy(L)} ({money.unit})", "dv-16")
    st.markdown(bridge(view.qoe, view.pl_years, money), unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        if data.adjustments:
            st.markdown("**Management adjustments — your decision**")
            st.caption("Not accepted yet = left out of diligence-adjusted EBITDA (prudent) and shown as upside.")
            adj = pd.DataFrame([{"Adjustment": x.name, **{fy(y): x.values.get(y) for y in years3},
                                 "Status": "Under review"} for x in ext.data.adjustments])
            st.data_editor(adj, key=adj_key, hide_index=True, width="stretch",
                           disabled=["Adjustment"] + [fy(y) for y in years3],
                           column_config={"Status": st.column_config.SelectboxColumn(options=ADJUSTMENT_STATES,
                                                                                     required=True)})
        else:
            st.info("Management presents no adjusted EBITDA: the bridge starts from reported EBITDA.")
    with c2:
        st.markdown("**Your own adjustments**")
        st.caption(f"Add a row: owner costs, run-rate effects, pro forma items ({money.currency} thousands; "
                   "negative reduces EBITDA).")
        own = pd.DataFrame({"Adjustment": pd.Series(dtype="str"),
                            **{fy(y): pd.Series(dtype="float") for y in years3}})
        st.data_editor(own, key=own_key, num_rows="dynamic", hide_index=True, width="stretch",
                       column_config={"Adjustment": st.column_config.TextColumn(width="medium")})

    st.markdown(f"<div class='dd-section'>{term('Net debt')}</div>", unsafe_allow_html=True)
    waterfall(net_debt_steps(view, B), money, f"Net debt bridge, {fy(B)} ({money.unit}): borrowings less cash, "
              "then the debt-like items included below", "dv-nd")
    st.markdown(bridge(view.net_debt, view.bs_years, money), unsafe_allow_html=True)
    if data.balance_items:
        st.markdown("**Debt-like and cash-like items found in the balance sheet**")
        st.caption("Defaults follow a prudent buy-side view: clearly owed items in, cash-like items only when "
                   "current; tick or untick to change. Items in net debt leave working capital (no double count).")
        items = pd.DataFrame([{"Line in the file": b.label, "Category": b.category,
                               "Type": "Debt-like" if b.nature == "debt" else "Cash-like",
                               fy(B): b.values.get(B), "Include": b.include} for b in data.balance_items])
        st.data_editor(items, key=inc_key, hide_index=True, width="stretch",
                       disabled=["Line in the file", "Category", "Type", fy(B)])
    else:
        st.caption("No debt-like or cash-like lines found in the balance sheet (leases, pensions, tax payable, "
                   "marketable securities…). Check the notes: they are often presented there.")

    st.markdown(f"<div class='dd-section'>{term('Net working capital', 'NWC')}</div>", unsafe_allow_html=True)
    nwc_chart(view, money, "dv-nwc")
    st.markdown(bridge(view.nwc, view.bs_years, money), unsafe_allow_html=True)
    st.caption("Year-end balances only. A peg is negotiated on 12–24 monthly balances: request the monthly balance "
               "sheets before relying on the average.")

    if a.purpose in ("buy", "sell"):
        st.markdown("<div class='dd-section'>Value at stake (illustrative)</div>", unsafe_allow_html=True)
        multiple = st.number_input("EV / EBITDA multiple you want to test", min_value=1.0, max_value=30.0, value=8.0,
                                   step=0.5, help="Your assumption. Used only for this sensitivity; never sent to the AI.")
        stake = value_at_stake(view, multiple)
        st.dataframe(pd.DataFrame([[label, money.fmt(x)] for label, x in stake], columns=["", f"{fy(L)}"]),
                     hide_index=True, width="stretch")
        st.caption("What the diligence adjustments represent in equity value at the multiple you chose. Arithmetic, "
                   "not a valuation or a view on price.")

    if a.purpose in ("buy", "sell"):
        st.markdown("<div class='dd-section'>Price: enterprise value to equity</div>", unsafe_allow_html=True)
        mech = st.radio("Price mechanism of the SPA", MECHANISMS, index=None, horizontal=True, key=f"mech-{file_key}",
                        help="Completion accounts fix the price on the balance sheet at closing (NWC against a peg). "
                             "A locked box fixes it on a past balance sheet; the buyer is protected by the leakage "
                             "covenant, with no true-up.")
        if mech is None:
            st.info("Choose the price mechanism first: nothing is computed, and nothing is assumed, until you do.")
        elif mech == "Completion accounts":
            st.caption("EUR thousands. A model configuration subordinated to the SPA definitions, not a clause.")
            e1, e2, e3 = st.columns(3)
            how = e1.radio("Enterprise value", ["Entered directly", "Multiple × EBITDA"], key=f"evhow-{file_key}")
            if how == "Entered directly":
                ev = EnterpriseValue(e2.number_input("EV (EUR thousands)", min_value=0.0, value=None, step=100.0,
                                                     key=f"ev-{file_key}"))
            else:
                choices = {"Diligence-adjusted": view.ebitda_dd[L], "Reported": view.ebitda[L]}
                if view.ebitda_mgmt:
                    choices["Management-adjusted"] = view.ebitda_mgmt[L]
                pick = e2.selectbox(f"EBITDA ({fy(L)})", list(choices), key=f"evb-{file_key}")
                ev = EnterpriseValue(multiple=e3.number_input("Your multiple (x)", min_value=0.0, value=None,
                                                              step=0.5, key=f"evm-{file_key}",
                                                              help="Your assumption: no market multiple is supplied."),
                                     ebitda=choices[pick], ebitda_label=pick)
            n1, n2 = st.columns(2)
            nwc_close = n1.number_input(f"NWC at closing (estimate; default {fy(B)} year-end)", value=view.nwc_values[B],
                                        step=10.0, key=f"nwcc-{file_key}")
            peg = n2.number_input("Peg (target NWC in the SPA)", value=view.nwc_average, step=10.0, key=f"peg-{file_key}",
                                  help="Default: the average of the year-ends, an indicative reference only, not a "
                                       "negotiated peg (that needs 12 to 24 monthly balances).")
            other = st.data_editor(pd.DataFrame({"Contractual adjustment": pd.Series(dtype="str"),
                                                 "Amount (sign explicit)": pd.Series(dtype="float")}),
                                   key=f"other-{file_key}", num_rows="dynamic", hide_index=True, width="stretch")
            others = [(str(r["Contractual adjustment"]), float(r["Amount (sign explicit)"]))
                      for _, r in other.iterrows() if pd.notna(r["Amount (sign explicit)"])]
            price = PriceInputs(mech, ev, nwc_close, peg, others)
            res = completion_equity(completion_from_analysis(a, price))
            st.dataframe(pd.DataFrame([[label, money.fmt(x)] for label, x in res["lines"]]
                                      + [["= Equity value at closing (estimate)", money.fmt(res["equity"])]],
                                      columns=["", fy(B)]), hide_index=True, width="stretch")
            for missing in res["incomplete"]:
                st.warning(f"Enter or find: {missing}. Equity is not computed without it.")
            st.caption(f"Net debt with the debt-like items: {money.fmt(res['net_debt_with_debt_like'])}, counted once. "
                       "Equity value is not what the seller receives: escrow, retentions, earn-out and deferrals are "
                       "separate, from the SPA.")
            if res["equity"] is not None:
                grid = sensitivity(ev, res["net_debt_with_debt_like"], res["lines"][4][1] + sum(x for _, x in others))
                if grid:
                    st.markdown("**Sensitivity of equity to the multiple and EBITDA** (EV derived)")
                    st.dataframe(pd.DataFrame([[money.fmt(r[0])] + [money.fmt(x) for x in r[1:]] for r in grid[1:]],
                                              columns=["EBITDA"] + [f"{m:g}x" for m in grid[0][1:]]), hide_index=True)
        else:
            st.caption("EUR thousands. No true-up of NWC or net debt at closing: the buyer relies on the leakage "
                       "covenant.")
            l1, l2, l3 = st.columns(3)
            agreed = l1.number_input("Equity price agreed at the locked box date", min_value=0.0, value=None,
                                     step=100.0, key=f"lbp-{file_key}")
            lb_date = l2.date_input("Locked box date", value=None, key=f"lbd-{file_key}")
            close = l3.date_input("Closing date", value=None, key=f"lbc-{file_key}")
            a1, a2, a3 = st.columns(3)
            accrual = a1.number_input("Value accrual fixed in the SPA", value=None, step=10.0, key=f"lba-{file_key}")
            rate = a2.number_input("Or ticking fee, annual rate (%)", min_value=0.0, value=None, step=0.5,
                                   key=f"lbr-{file_key}")
            base_tf = a3.number_input("Ticking fee base", min_value=0.0, value=None, step=100.0, key=f"lbb-{file_key}")
            st.markdown("**Leakage register** (screening, not a legal verdict)")
            cands = leakage_candidates(data)
            rows = [{"ID": x.id, "Description": x.description, "Amount": x.amount, "Status": x.status,
                     "Justification": x.justification} for x in cands]
            reg = st.data_editor(pd.DataFrame(rows or [{"ID": "LK-01", "Description": "", "Amount": None,
                                                        "Status": "Candidate", "Justification": ""}]),
                                 key=f"leak-{file_key}", num_rows="dynamic", hide_index=True, width="stretch",
                                 column_config={"Status": st.column_config.SelectboxColumn(options=LEAKAGE_STATES,
                                                                                           required=True)})
            treat = st.radio("Confirmed leakage", LEAKAGE_TREATMENTS, horizontal=True, key=f"lbt-{file_key}")
            items = [LeakageItem(str(r["ID"]), str(r["Description"]), float(r["Amount"]), status=str(r["Status"]),
                                 justification=str(r["Justification"] or "")) for _, r in reg.iterrows()
                     if pd.notna(r["Amount"])]
            if agreed is None:
                st.info("Enter the equity price agreed at the locked box date.")
            else:
                lb = LockedBox(agreed, lb_date, close, accrual, None if rate is None else rate / 100, base_tf, items,
                               treat)
                price = PriceInputs(mech, locked_box=lb)
                res = locked_box_equity(lb)
                st.dataframe(pd.DataFrame([["Equity price agreed", money.fmt(agreed)],
                                           ["+ value accrual or ticking fee", money.fmt(res["accrual"])],
                                           ["- confirmed leakage deducted at closing",
                                            money.fmt(-res["leakage_deducted"])],
                                           ["= Equity value at closing", money.fmt(res["equity"])],
                                           ["Leakage claim, separate from the price", money.fmt(res["leakage_claim"])]],
                                          columns=["", " "]), hide_index=True, width="stretch")
                if res["conclusion"]:
                    st.warning(res["conclusion"])

# ---------------------------------------------------------------- red flags and review
with tab_rf:
    if al:
        st.caption("Double-click Status or Comment to record your review. Your review flows into the downloads"
                   + ("." if DEMO else " and the AI memo."))
        table = pd.DataFrame([{"Severity": r.rule.severity, "Rule": r.rule.id, "Finding": r.rule.name,
                               "Amount": money.fmt(r.amount) if r.amount is not None else "n/q",
                               "Area": r.rule.area, "Years": r.years_text, "Status": "Pending", "Comment": ""}
                              for r in al])
        st.data_editor(
            table, key=review_key, hide_index=True, width="stretch", height=35 * (len(table) + 1) + 3,
            disabled=["Severity", "Rule", "Finding", "Amount", "Area", "Years"],
            column_config={
                "Severity": st.column_config.TextColumn(width="small"),
                "Rule": st.column_config.TextColumn(width="small"),
                "Finding": st.column_config.TextColumn(width="large"),
                "Years": st.column_config.TextColumn(width="small"),
                "Status": st.column_config.SelectboxColumn(options=REVIEW_STATES, required=True, width="small"),
                "Comment": st.column_config.TextColumn(width="medium"),
            })
        pending = sum(state == "Pending" for state, _ in reviews.values())
        st.caption(f"{len(al) - pending} of {len(al)} reviewed.")
    else:
        st.success("No rule fired: no red flags on the data provided.")

    stem = Path(name).stem
    buf = io.BytesIO()
    write_excel(results, metrics, data.years, buf, reviews, items=ext.items, analysis=a)
    book = io.BytesIO()
    write_databook(a, book, reviews, price=price)
    book_help = ("The Excel a transaction team works in: QoE, NWC and net debt with formulas, the source register, "
                 "issues and requests, and checks. Edit only the yellow cells.")
    if DEMO:
        st.caption("The downloads are at the top of the page.")
        with downloads:
            requests = demo.request_list(case)
            d1, d2, d3, d4 = st.columns(4)
            d1.download_button("Databook (Excel)", book.getvalue(), f"{case.slug}_databook.xlsx",
                               mime=XLSX_MIME, type="primary", width="stretch", help=book_help + " Includes your decisions.")
            d2.download_button("Red flags (Excel)", buf.getvalue(), f"{case.slug}_red_flags.xlsx", mime=XLSX_MIME,
                               width="stretch",
                               help="Every finding with its evidence, source, question and document to request.")
            d3.download_button("Request list", requests.encode("utf-8"), f"{case.slug}_request_list.md", width="stretch",
                               mime=MD_MIME, disabled=not requests, help="From the stored memo (tab Memo).")
            d4.download_button("Red flags (CSV)", csv_bytes(results, reviews), f"{case.slug}_red_flags.csv",
                               mime="text/csv", width="stretch")
    else:
        d1, d2, d3, _ = st.columns([1, 1, 1, 2])
        d1.download_button("Download databook", book.getvalue(), f"{stem}_databook.xlsx", mime=XLSX_MIME,
                           type="primary", help=book_help)
        d2.download_button("Download report", buf.getvalue(), f"{stem}_due_diligence.xlsx", mime=XLSX_MIME)
        d3.download_button("Download CSV", csv_bytes(results, reviews), f"{stem}_red_flags.csv", mime="text/csv")

    for r in al:   # by amount at stake
        rule = r.rule
        amount = (f"{money.fmt(r.amount)} in {fy(r.amount_year)} ({r.amount_label})" if r.amount is not None
                  else NOT_QUANTIFIABLE)
        with st.expander(f"{rule.id} · {rule.name}  —  {rule.severity} · {r.years_text} · {reviews[rule.id][0]}"):
            st.markdown(f"**In plain words**  \n{rule.plain}")
            st.markdown(f"**Amount at stake**  \n{amount[0].upper() + amount[1:]}"
                        + (f". {r.note[0].upper() + r.note[1:]}: severity lowered from {r.base_severity} to Low"
                           if r.note else "") + f".  \n**Deal implication**  \n{r.implication}. {r.treatment} "
                        f"_{DISCLAIMER}_")
            if r.evidence_state:
                st.markdown(f"**Evidence from the notes**  \n{r.evidence_state.capitalize()}"
                            + (f" by {r.evidence_note}. {r.evidence_text}" if r.evidence_note else
                               ": no note on this subject was read.")
                            + (f"  \n**Next request**  \n{r.next_request}" if r.next_request else ""))
            st.markdown(f"**Evidence**  \n{r.evidence}")
            st.markdown(f"**Test**  \n{rule.test} · threshold {rule.limit_text()}"
                        + (f" · graded severity: {rule.grade_text[0].lower()}{rule.grade_text[1:]}"
                           if rule.grade_text else "")
                        + (f"  \n_{rule.calibration[0].upper() + rule.calibration[1:]}._" if rule.calibration else ""))
            c1, c2 = st.columns(2)
            c1.markdown(f"**What to investigate**  \n{rule.focus}")
            c2.markdown(f"**Why it matters**  \n{rule.rationale}")
            c1.markdown(f"**Question for management**  \n{rule.question}")
            c2.markdown(f"**Document to request**  \n{rule.request}")
            st.caption(f"Practice: {rule.practice}")

# ---------------------------------------------------------------- sector
with tab_sec:
    s = a.sector
    st.markdown(f"<div class='dd-section'>{html.escape(s.name)}</div>", unsafe_allow_html=True)
    b = s.benchmarks
    st.caption(f"Peers: {b['industry']} — {b['firms']} European listed companies ({sectors.BENCHMARK_SOURCE}). "
               "Listed groups are larger than most targets: a gap is a question to ask, not a finding.")
    bench = pd.DataFrame([{"Metric": x["Metric"], f"Company {fy(L)}": fmt_unit(x["unit"], x["Company"]),
                           "Sector": fmt_unit(x["unit"], x["Sector"]), "Reading": x["Reading"]} for x in a.benchmarks])
    st.dataframe(bench, hide_index=True, width="stretch",
                 column_config={"Reading": st.column_config.TextColumn(width="large")})
    st.markdown("<div class='dd-section'>Thresholds calibrated for the sector</div>", unsafe_allow_html=True)
    calibrated = [r.rule for r in results if r.rule.calibration]
    if calibrated:
        for rule in calibrated:
            st.markdown(f"- **{rule.id} · {rule.name}**: {rule.limit_text()} — {rule.calibration}.")
    else:
        st.caption("None: the general thresholds apply to this sector.")
    if s.lens:
        st.markdown("<div class='dd-section'>Sector lens — what a sector specialist would also ask</div>",
                    unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Area": i.area, "Question for management": i.question,
                                    "Document to request": i.request} for i in s.lens]),
                     hide_index=True, width="stretch",
                     column_config={"Question for management": st.column_config.TextColumn(width="large"),
                                    "Document to request": st.column_config.TextColumn(width="medium")})
        st.caption(("These questions went to the memo, which" if DEMO else "These questions go to the AI memo, which")
                   + " adds them to the request list where the data points to them.")

# ---------------------------------------------------------------- what the agent read
with tab_src:
    st.caption(f"How the statements were read: {ext.method}.")
    if ext.files:
        st.markdown("<div class='dd-section'>Documents in the data room</div>", unsafe_allow_html=True)
        st.caption("Excel files are read together as one set of statements; every figure keeps its file and cell. "
                   "Documents are read as text for the memo, on this computer.")
        st.dataframe(pd.DataFrame(ext.files), hide_index=True, width="stretch")
    if ext.notes:
        st.markdown("<div class='dd-section'>Notes to the accounts read</div>", unsafe_allow_html=True)
        st.caption("The key notes of the same report, transcribed as printed. Each finding says whether one of them "
                   "explains it (Key issues tab). A note that was not read is listed as such, never guessed.")
        st.dataframe(pd.DataFrame([{"Note": t.note, "Title as printed": t.title, "Where": t.page,
                                    "Subject": t.topic.replace("_", " "), "Lines": len(t.rows), "Unit": t.unit}
                                   for t in ext.notes]
                                  + [{"Note": "–", "Title as printed": "not read", "Where": reason,
                                      "Subject": topic.replace("_", " "), "Lines": 0, "Unit": ""}
                                     for topic, reason in ext.notes_not_read]), hide_index=True, width="stretch")
    if data.prior_report:
        st.markdown("<div class='dd-section'>Two annual reports, three years</div>", unsafe_allow_html=True)
        st.caption(f"{', '.join(fy(y) for y in data.prior_years)} comes from the prior report "
                   f"({data.prior_report}). {', '.join(fy(y) for y in data.overlap_years)} is in both reports: the "
                   "comparative of the latest report is used, and every line that differs between the two is listed "
                   "here (rule R30), never mixed in silence.")
        if data.restatements:
            st.dataframe(pd.DataFrame([{"Line": r["line"], "Year": fy(r["year"]),
                                        "As first published": money.amount(r["as_first_published"]),
                                        "As comparative (used)": money.amount(r["as_restated"]),
                                        "Difference": money.amount(r["difference"]),
                                        "Source, prior report": r["source_first"],
                                        "Source, latest report": r["source_latest"]} for r in data.restatements]),
                         hide_index=True, width="stretch")
        else:
            st.success(f"No line was restated: the {', '.join(fy(y) for y in data.overlap_years)} figures of the two "
                       "reports are the same, within €1k.")
    st.markdown("<div class='dd-section'>Reading checks</div>", unsafe_allow_html=True)
    if a.checks:
        st.caption("Subtotals rebuilt from the lines the agent read, compared with the subtotals the company "
                   "published. A failed check means a line is missing or misclassified.")
        st.dataframe(pd.DataFrame([{"Check": c["Check"], "Year": fy(c["Year"]),
                                    "Rebuilt": money.amount(c["Rebuilt from the lines"]),
                                    "Published": money.amount(c["As published"]),
                                    "Result": "✓ matches" if c["OK"] else "✗ does not match"} for c in a.checks]),
                     hide_index=True, width="stretch")
    else:
        st.caption("The file publishes no subtotal (gross profit, EBITDA, operating profit) to check the reading "
                   "against: review the lines below.")
    st.markdown("<div class='dd-section'>What the agent read</div>", unsafe_allow_html=True)
    st.caption(f"Every standard line item, the label it matched in your file and the cell it read, in "
               f"{data.currency} thousands. " + ("Figures as published: locked in the demo." if DEMO else
                                                 "Correct any figure here and the whole analysis updates."))
    if ext.missing:
        st.warning("Not found in the file: " + ", ".join(ext.missing) + ". Enter the figures below if available.")
    items = pd.DataFrame([{k: v for k, v in it.items() if k != "key"} for it in ext.items])
    st.data_editor(items, key=src_key, hide_index=True, width="stretch", height=560,
                   disabled=True if DEMO else ["Statement", "Line item", "Found as", "Source"],
                   column_config={"Line item": st.column_config.TextColumn(width="medium"),
                                  "Found as": st.column_config.TextColumn(width="medium")})
    if ext.unmapped:
        with st.expander(f"Lines in your file the analysis does not use ({len(ext.unmapped)})"):
            st.caption("Subtotals, financial results, equity reserves and other lines outside the standard model. "
                       "Check that nothing here belongs in EBITDA, debt or working capital.")
            st.dataframe(pd.DataFrame(ext.unmapped), hide_index=True, width="stretch")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("<div class='dd-section'>Key documents received</div>", unsafe_allow_html=True)
        st.caption("Ticked from the documents in the data room; tick what the company provided otherwise. "
                   "Missing documents raise R18.")
        st.data_editor(pd.DataFrame(ext.data.documents, columns=["Document", "Received"]), key=docs_key,
                       hide_index=True, width="stretch", disabled=["Document"])
    with c2:
        if data.clients:
            st.markdown("<div class='dd-section'>Sales by customer</div>", unsafe_allow_html=True)
            rows = [[c.name] + [fmt_metric("vendas", c.values.get(y), money) for y in years3] for c in data.clients]
            st.dataframe(pd.DataFrame(rows, columns=["Customer"] + [fy(y) for y in years3]), hide_index=True,
                         width="stretch")

# ---------------------------------------------------------------- the rules, in plain words
with tab_rules:
    st.caption("Every rule the agent applies: what it checks in plain words, the threshold (calibrated for the sector "
               "where it says so), whether it fired here, and where the practice comes from. R01–R20 match the Excel "
               "template; R21–R26 go beyond it.")
    rulebook = pd.DataFrame([{"Rule": r.rule.id, "Area": r.rule.area, "Name": r.rule.name, "In plain words": r.rule.plain,
                              "Threshold": r.rule.limit_text() + (" (sector)" if r.rule.calibration else "")
                              + (f"; {r.rule.grade_text}" if r.rule.grade_text else ""),
                              "Here": "Fired" if r.alert else "n/a" if all(f == "n/a" for f in r.fires.values())
                              else "Passed", "Practice": r.rule.practice} for r in results])
    st.dataframe(rulebook, hide_index=True, width="stretch", height=35 * (len(rulebook) + 1) + 3,
                 column_config={"In plain words": st.column_config.TextColumn(width="large"),
                                "Practice": st.column_config.TextColumn(width="large")})

# ---------------------------------------------------------------- metrics
with tab_m:
    rows = [[label] + [fmt_metric(key, metrics[key].get(y), money) for y in data.years] for key, label in ALL_LABELS.items()]
    st.dataframe(pd.DataFrame(rows, columns=[f"Metric ({money.unit} unless stated)"] + [fy(y) for y in data.years]),
                 hide_index=True, width="stretch", height=35 * (len(rows) + 1) + 3)

# ---------------------------------------------------------------- AI memo
with tab_ai:
    if DEMO:
        show_stored_memo(case)
    else:
        st.markdown("Claude reads the findings (with your review), the deal view, the sector lens, the metrics and the "
                    "full data room, and writes a two-page memo, the information request list and notes to improve the "
                    "template. **It does no calculations and creates no findings**; every figure is then checked "
                    "automatically.")
        source_text = ext.source_text
        if not source_text:   # a completed template carries no data room text
            room = st.file_uploader("Data room (Excel) for the memo", type=["xlsx", "xlsm"], key="data_room")
            source_text = data_room_text(io.BytesIO(room.getvalue())) if room is not None else ""
        material = build_material(data, metrics, results, source_text, reviews, ext.company, analysis=a)
        alert_ids = [r.rule.id for r in al]
        st.caption(f"Model {MODEL}, effort {EFFORT}. Typical cost USD 0.20–0.50 per memo; the actual cost is shown "
                   "at the end.")

        memo_key = f"memo-{file_key}"
        if st.button("Write the memo", type="primary", disabled=not has_key):
            box, parts = st.empty(), []

            def show(text: str) -> None:
                parts.append(text)
                box.markdown("".join(parts))

            with st.spinner("Writing the memo. The model thinks first; this can take a few minutes…"):
                try:
                    memo = write_memo(material, on_text=show)
                    st.session_state[memo_key] = (memo, material, check_memo(memo.text, material, alert_ids))
                except anthropic.AuthenticationError:
                    st.error("The Claude API key is invalid. Check ANTHROPIC_API_KEY in the .env file.")
                except anthropic.RateLimitError:
                    st.error("Rate limit reached. Wait a minute and try again.")
                except anthropic.APIStatusError as e:
                    st.error(f"Claude API error ({e.status_code}): {e.message}")
                except anthropic.APIConnectionError:
                    st.error("Cannot reach the Claude API. Check the internet connection.")
                except MemoError as e:
                    st.error(str(e))
                except anthropic.AnthropicError as e:
                    st.error(f"Could not call the Claude API: {e}")
            box.empty()
        if not has_key:
            st.info("To write the memo here, add ANTHROPIC_API_KEY to the .env file and restart the app. "
                    "Without a key, use the option below, or ask Claude Code to run the due-diligence skill.")

        stem = Path(name).stem
        if memo_key in st.session_state:
            memo, sent, check = st.session_state[memo_key]
            st.caption(f"{memo.model} · {memo.input_tokens:,} input tokens, {memo.output_tokens:,} output tokens "
                       f"· estimated cost ≈ USD {memo.cost_usd:.2f}")
            if memo.truncated:
                st.warning("The answer stopped at the token limit and may be incomplete.")
            show_check(check)
            m1, m2, _ = st.columns([1, 1, 3])
            m1.download_button("Download memo (.md)", memo.text.encode("utf-8"), f"{stem}_memo.md", mime="text/markdown")
            m2.download_button("Material sent to the AI", sent.encode("utf-8"), f"{stem}_ai_material.md",
                               mime="text/markdown")
            st.divider()
            st.markdown(memo.text)

        with st.expander("No API key? Write the memo elsewhere and check it here"):
            st.markdown("1. Download the material and the prompt.  \n"
                        "2. In a new claude.ai conversation, paste the prompt, then the material.  \n"
                        "3. Save the answer as a `.md` file and upload it below: the app checks the figures, the "
                        "findings and the request list.")
            e1, e2, _ = st.columns([1, 1, 3])
            e1.download_button("Material (.md)", material.encode("utf-8"), f"{stem}_ai_material.md", mime="text/markdown")
            e2.download_button("Prompt (.md)", PROMPT_FILE.read_bytes(), "ai_memo_prompt.md", mime="text/markdown")
            outside = st.file_uploader("Memo written outside the app (.md)", type=["md", "txt"], key="memo_upload")
            if outside is not None:
                show_check(check_memo(outside.getvalue().decode("utf-8"), material, alert_ids))

if DEMO:
    glossary()
    footer()
