"""Streamlit app — drop the data room, review the deal view and the red flags, download, write the memo.

Run (with the virtual environment active):
    streamlit run app.py

The app only wires the layers together (dataroom → pipeline: metrics, rules, deal view → report → ai_memo →
memo_check). It does no calculations of its own and creates no findings.
"""
from __future__ import annotations

import hashlib
import html
import io
import os
from pathlib import Path

import anthropic
import pandas as pd
import streamlit as st

from dd_assistant import europe, sectors
from dd_assistant.ai_memo import EFFORT, MODEL, PROMPT_FILE, MemoError, build_material, load_env, write_memo
from dd_assistant.deal import ADJUSTMENT_STATES, Line, value_at_stake
from dd_assistant.dataroom import DOCUMENTS, ESEF, SPREADSHEETS, NeedsPdfReading, files_in, read_data_room
from dd_assistant.extract import ExtractionError, data_room_text
from dd_assistant.input_loader import Named
from dd_assistant.memo_check import MemoCheck, check_memo, report
from dd_assistant.metrics import ALL_LABELS
from dd_assistant.pipeline import PURPOSES, analyse, choice_effects
from dd_assistant.report import REVIEW_STATES, csv_bytes, fmt_metric, fmt_unit, write_excel
from dd_assistant.rules import SEVERITIES, fy

DATA = Path(__file__).parent / "data"
SAMPLES = {"Duriva — data room in 5 documents, planted issues": DATA / "Duriva_data_room",
           "Velmora — clean company": DATA / "Velmora_data_room.xlsx",
           "Toyota Caetano Portugal — real FY24 accounts (PT)": DATA / "Toyota_Caetano_2024_published.xlsx",
           "Corticeira Amorim — real FY24 accounts (EN)": DATA / "Corticeira_Amorim_2024_published.xlsx"}
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SEVERITY_COLOR = {"High": "#d03b3b", "Medium": "#fab219", "Low": "#8a8f98"}   # status palette; always with a label
# Overview: which findings colour each headline figure, and where to look for the detail.
KPI_RULES = {"Revenue": ["R01", "R02", "R16"], "Diligence-adjusted EBITDA": ["R03", "R04", "R05", "R06", "R19", "R26"],
             "Cash conversion": ["R10", "R14", "R24"],
             "Adjusted net debt": ["R11", "R13", "R17", "R20", "R21", "R22"],
             "Net working capital": ["R07", "R08", "R09", "R23"]}
# Within a severity, what moves the price first: EBITDA quality, cash, debt, then revenue, working capital, data.
IMPACT = ["R19", "R05", "R04", "R26", "R10", "R20", "R21", "R11", "R13", "R22", "R01", "R02", "R03", "R07", "R09",
          "R08", "R24", "R06", "R23", "R17", "R12", "R15", "R14", "R16", "R25", "R18"]
WHERE = {"Quality of earnings": "Deal view", "Net working capital": "Deal view", "Debt": "Deal view",
         "Consistency": "Data room", "Information": "Data room"}
SUMMARY_ROWS = ["vendas", "g_vendas", "gm", "ebitda", "ebitda_m", "ebitda_adj", "ebitda_ex_gain", "cgo", "conv",
                "fco", "dso", "dio", "dpo", "net_debt", "nd_ebitda"]

CSS = """
<style>
[data-testid="stAppDeployButton"], #MainMenu {display: none;}
.block-container {padding-top: 3.2rem; max-width: 1240px;}
.dd-eyebrow {font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: #5b6474; font-weight: 600;}
.dd-title {font-size: 2.1rem; font-weight: 700; color: #1b2333; margin: .1rem 0 .2rem;}
.dd-sub {color: #5b6474; font-size: .92rem; margin-bottom: 1rem;}
.dd-kpis {display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: .4rem 0 1.4rem;}
.dd-kpi {border: 1px solid #e3e7ee; border-radius: 12px; padding: 14px 16px; background: #fff;}
.dd-kpi .l {font-size: .8rem; color: #5b6474;}
.dd-kpi .v {font-size: 1.5rem; font-weight: 650; color: #1b2333; margin: 2px 0; white-space: nowrap;}
.dd-kpi .s {font-size: .8rem; color: #5b6474;}
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


st.set_page_config(page_title="Tickmark", page_icon=":material/fact_check:", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
load_env()
has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

# ---------------------------------------------------------------- input
with st.sidebar:
    st.markdown("### Tickmark")
    st.caption("Preliminary financial due diligence · European market · EUR")
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

suggested, words = sectors.suggest(ext.source_text, ext.company)
c_suggested, c_why = europe.suggest(ext.source_text, ext.company)
keys = [s.key for s in sectors.SECTORS]
codes = list(europe.COUNTRY_BY_CODE)
with st.sidebar:
    purpose = st.selectbox("Purpose", list(PURPOSES), format_func=PURPOSES.get, key=f"purpose-{file_key}",
                           help="M&A is the focus; the same analysis serves a lender or an owner. Only the way the "
                                "memo is written changes.")
    purpose_effect = st.empty()
    country = st.selectbox("Country of the target", codes, key=f"country-{file_key}",
                           index=codes.index(c_suggested.code if c_suggested else "EU"),
                           format_func=lambda k: europe.COUNTRY_BY_CODE[k].name,
                           help="Sets the accounting framework and the statutory tax rate (R25).")
    st.caption(f"Suggested from {c_why}." if c_suggested and country == c_suggested.code and c_why else
               "Chosen by you." if c_suggested and country != c_suggested.code else "Nothing points to a country.")
    country_effect = st.empty()
    sector_key = st.selectbox("Sector", keys, index=keys.index(suggested.key), key=f"sector-{file_key}",
                              format_func=lambda k: sectors.SECTOR_BY_KEY[k].name,
                              help="Calibrates a few thresholds, sets the peer benchmarks and adds the sector's "
                                   "questions to the request list.")
    st.caption(f"Suggested from the file: {', '.join(words)}." if words and sector_key == suggested.key else
               "Chosen by you." if sector_key != suggested.key else "No sector keyword found: choose one.")
    sector_effect = st.empty()
    st.divider()
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

a = analyse(ext, sector_key, country, overrides, docs, decisions, analyst, include, purpose)
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
st.markdown(f"<div class='dd-eyebrow'>{html.escape(PURPOSES[a.purpose])} · {html.escape(a.sector.name)} · "
            f"{html.escape(a.country.name if a.country else 'Europe')}</div>"
            f"<div class='dd-title'>{html.escape(ext.company)}</div>"
            f"<div class='dd-sub'>{html.escape(name)} · {fy(years3[0])}–{fy(L)} · {money.unit_long} · "
            f"{html.escape(ext.method)}</div>", unsafe_allow_html=True)
if not a.checks_ok:
    st.warning("Reading check failed: a subtotal rebuilt from the lines read does not match the published one. "
               "A line may be missing or misclassified — see Data room before relying on the figures.")

tab_ov, tab_deal, tab_rf, tab_sec, tab_src, tab_rules, tab_m, tab_ai = st.tabs(
    ["Overview", "Deal view", f"Red flags ({len(al)})", "Sector", "Data room", "Rulebook", "Metrics", "AI memo"])

# ---------------------------------------------------------------- overview
with tab_ov:
    g = lambda key, year=L: metrics[key].get(year)
    nwc_pct = None if not data.v("vendas", B) else view.nwc_values[B] / data.v("vendas", B)
    kpis = [
        ("Revenue", money.fmt(g("vendas")), f"{fmt_metric('g_vendas', g('g_vendas'))} growth vs {fy(data.pl_years[-2])}"),
        ("Diligence-adjusted EBITDA", money.fmt(view.ebitda_dd[L]),
         f"Reported {money.fmt(view.ebitda[L])}" + (f" · mgmt {money.fmt(view.ebitda_mgmt[L])}" if view.ebitda_mgmt
                                                    else "")),
        ("Cash conversion", fmt_metric("conv", g("conv")), "Operating cash / reported EBITDA"),
        ("Adjusted net debt", money.fmt(view.net_debt_adjusted[B]),
         f"Reported {money.fmt(view.net_debt_reported[B])}"
         + (f" · {view.net_debt_adjusted[B] / view.ebitda_dd[L]:.2f}x EBITDA" if view.ebitda_dd[L] > 0 else "")),
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
    for l, v, sub in kpis:
        cls, tag = status(KPI_RULES[l], fired)
        year = fy(L if "EBITDA" in l or l in ("Revenue", "Cash conversion") else B)
        cards.append(f"<div class='dd-kpi {cls}'><div class='l'>{l} · {year}</div><div class='v'>{v}</div>"
                     f"<div class='s'>{sub}</div><span class='dd-tag {cls}'>{html.escape(tag)}</span></div>")
    st.markdown("<div class='dd-kpis'>" + "".join(cards) + "</div>", unsafe_allow_html=True)

    # ---- where it goes wrong: the figure, the threshold, in plain words, and where to look
    st.markdown(f"<div class='dd-section'>Where it goes wrong · {len(al)} red flags</div>"
                + " ".join(f"{pill(k)} <span style='color:#5b6474;font-size:.85rem'>{by[k]}</span>&nbsp;&nbsp;"
                           for k in SEVERITIES), unsafe_allow_html=True)
    if not al:
        st.success("No rule fired: no red flags on the data provided.")
    ordered = sorted(al, key=lambda r: (SEVERITIES.index(r.rule.severity), IMPACT.index(r.rule.id)))
    issues = []
    for r in ordered[:6]:
        big, vs = headline(r, money)
        issues.append(f"<div class='dd-issue {r.rule.severity}'><div><div class='big'>{html.escape(big)}</div>"
                      f"<div class='vs'>{html.escape(vs)}</div></div><div><div class='h'>{pill(r.rule.severity)} "
                      f"{r.rule.id} · {html.escape(r.rule.name)}</div><div class='p'>{html.escape(r.rule.plain)}</div>"
                      f"<div class='w'>Ask: {html.escape(r.rule.question.split('?')[0])}? · "
                      f"See {WHERE.get(r.rule.area, 'Red flags')}</div></div></div>")
    st.markdown("<div class='dd-list'>" + "".join(issues) + "</div>", unsafe_allow_html=True)
    if len(ordered) > 6:
        st.caption(f"…and {len(ordered) - 6} more in the Red flags tab: "
                   + ", ".join(f"{r.rule.id} {r.rule.name}" for r in ordered[6:]) + ".")

    st.markdown("<div class='dd-section'>Financial summary</div>", unsafe_allow_html=True)
    summary = pd.DataFrame([[ALL_LABELS[k]] + [fmt_metric(k, metrics[k].get(y), money) for y in years3]
                            for k in SUMMARY_ROWS], columns=[f"{money.unit} unless stated"] + [fy(y) for y in years3])
    st.dataframe(summary, hide_index=True, width="stretch", height=35 * (len(summary) + 1) + 3)
    found = len(ext.items) - len(ext.missing)
    passed = sum(c["OK"] for c in a.checks)
    st.caption(f"Reading checks: {passed} of {len(a.checks)} passed. Data coverage: {found} of {len(ext.items)} "
               "standard line items identified" + (f". Not found: {', '.join(ext.missing)}." if ext.missing else "."))

# ---------------------------------------------------------------- deal view
with tab_deal:
    st.caption("The three numbers a deal team asks for first, calculated by the code from the lines in Data room. "
               "Your decisions below flow into the Excel download and the AI memo. Hover a line to see its source.")
    st.markdown("<div class='dd-section'>Quality of earnings</div>", unsafe_allow_html=True)
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

    st.markdown("<div class='dd-section'>Net debt</div>", unsafe_allow_html=True)
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

    st.markdown("<div class='dd-section'>Net working capital</div>", unsafe_allow_html=True)
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

# ---------------------------------------------------------------- red flags and review
with tab_rf:
    if al:
        st.caption("Double-click Status or Comment to record your review. Your review flows into the downloads "
                   "and the AI memo.")
        table = pd.DataFrame([{"Severity": r.rule.severity, "Rule": r.rule.id, "Finding": r.rule.name,
                               "Area": r.rule.area, "Years": r.years_text, "Status": "Pending", "Comment": ""}
                              for r in al])
        st.data_editor(
            table, key=review_key, hide_index=True, width="stretch", height=35 * (len(table) + 1) + 3,
            disabled=["Severity", "Rule", "Finding", "Area", "Years"],
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
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Download Excel", buf.getvalue(), f"{stem}_due_diligence.xlsx", mime=XLSX_MIME, type="primary")
    d2.download_button("Download CSV", csv_bytes(results, reviews), f"{stem}_red_flags.csv", mime="text/csv")

    for r in sorted(al, key=lambda r: SEVERITIES.index(r.rule.severity)):
        rule = r.rule
        with st.expander(f"{rule.id} · {rule.name}  —  {rule.severity} · {r.years_text} · {reviews[rule.id][0]}"):
            st.markdown(f"**In plain words**  \n{rule.plain}")
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
        st.caption("These questions go to the AI memo, which adds them to the request list where the data points "
                   "to them.")

# ---------------------------------------------------------------- what the agent read
with tab_src:
    if ext.files:
        st.markdown("<div class='dd-section'>Documents in the data room</div>", unsafe_allow_html=True)
        st.caption("Excel files are read together as one set of statements; every figure keeps its file and cell. "
                   "Documents are read as text for the memo, on this computer.")
        st.dataframe(pd.DataFrame(ext.files), hide_index=True, width="stretch")
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
               f"{data.currency} thousands. Correct any figure here and the whole analysis updates.")
    if ext.missing:
        st.warning("Not found in the file: " + ", ".join(ext.missing) + ". Enter the figures below if available.")
    items = pd.DataFrame([{k: v for k, v in it.items() if k != "key"} for it in ext.items])
    st.data_editor(items, key=src_key, hide_index=True, width="stretch", height=560,
                   disabled=["Statement", "Line item", "Found as", "Source"],
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
