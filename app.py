"""Streamlit app — upload a company's financials, review the deal view and the red flags, download, write the memo.

Run (with the virtual environment active):
    streamlit run app.py

The app only wires the layers together (extract → pipeline: metrics, rules, deal view → report → ai_memo →
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

from dd_assistant import sectors
from dd_assistant.ai_memo import EFFORT, MODEL, PROMPT_FILE, MemoError, build_material, load_env, write_memo
from dd_assistant.deal import ADJUSTMENT_STATES, Line, value_at_stake
from dd_assistant.extract import ExtractionError, data_room_text, read_financials
from dd_assistant.input_loader import Named
from dd_assistant.memo_check import MemoCheck, check_memo, report
from dd_assistant.metrics import LABELS
from dd_assistant.pipeline import analyse
from dd_assistant.report import REVIEW_STATES, csv_bytes, fmt_metric, fmt_unit, write_excel
from dd_assistant.rules import SEVERITIES, fy
from dd_assistant.units import CURRENCIES

DATA = Path(__file__).parent / "data"
SAMPLES = {"Duriva — data room with planted issues": DATA / "Duriva_data_room.xlsx",
           "Velmora — clean company": DATA / "Velmora_data_room.xlsx",
           "Toyota Caetano Portugal — real, FY24 published (PT, €)": DATA / "Toyota_Caetano_2024_published.xlsx",
           "Corticeira Amorim — real, FY24 published (EN, €)": DATA / "Corticeira_Amorim_2024_published.xlsx",
           "Apple — real, FY24 published (US GAAP, $)": DATA / "Apple_FY2024_published.xlsx"}
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SEVERITY_COLOR = {"High": "#d03b3b", "Medium": "#fab219", "Low": "#8a8f98"}   # status palette; always with a label
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
.dd-section {font-weight: 650; font-size: 1.05rem; color: #1b2333; margin: 1.2rem 0 .4rem;}
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
def read_file(content: bytes, name: str):
    """Layer 1: read the upload (cached by content, so a PDF is only sent to Claude once)."""
    return read_financials(io.BytesIO(content), name)


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


st.set_page_config(page_title="DD Assistant", page_icon=":material/fact_check:", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
load_env()
has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

# ---------------------------------------------------------------- input
with st.sidebar:
    st.markdown("### DD Assistant")
    st.caption("Preliminary financial due diligence for M&A")
    uploaded = st.file_uploader(
        "Company financials", type=["xlsx", "xlsm", "pdf"],
        help="The data room as received: income statement, balance sheet, cash flow, sales by customer, "
             "adjusted EBITDA, debt schedule. Excel or PDF, by nature or by function, in EUR, USD, GBP or BRL. "
             "No template needed.")
    sample = st.radio("…or open a sample data room", list(SAMPLES), disabled=uploaded is not None)

if uploaded is not None:
    name, content = uploaded.name, uploaded.getvalue()
else:
    name, content = SAMPLES[sample].name, SAMPLES[sample].read_bytes()
file_key = hashlib.sha1(content).hexdigest()[:12]

if name.lower().endswith(".pdf") and not st.session_state.get(f"pdf-{file_key}"):
    st.markdown("<div class='dd-eyebrow'>PDF financial statements</div>"
                f"<div class='dd-title'>{html.escape(name)}</div>", unsafe_allow_html=True)
    st.info("Claude reads the PDF (vision) and returns every figure exactly as printed, with its page. "
            "Units and signs are converted by the code, and you review every line before relying on it. "
            "Typical cost: USD 0.10–0.40 per document.")
    if st.button("Read the PDF with Claude", type="primary", disabled=not has_key):
        st.session_state[f"pdf-{file_key}"] = True
        st.rerun()
    if not has_key:
        st.warning("Add ANTHROPIC_API_KEY to the .env file (see .env.example) and restart the app to read PDFs.")
    st.stop()

try:
    with st.spinner("Reading the financial statements…"):
        ext = read_file(content, name)
except ExtractionError as e:
    st.error(str(e))
    st.stop()
except anthropic.AnthropicError as e:
    st.error(f"Claude API error while reading the PDF: {e}")
    st.stop()

suggested, words = sectors.suggest(ext.source_text, ext.company)
keys = [s.key for s in sectors.SECTORS]
with st.sidebar:
    sector_key = st.selectbox("Sector", keys, index=keys.index(suggested.key), key=f"sector-{file_key}",
                              format_func=lambda k: sectors.SECTOR_BY_KEY[k].name,
                              help="Calibrates a few thresholds, sets the peer benchmarks and adds the sector's "
                                   "questions to the request list.")
    st.caption(f"Suggested from the file: {', '.join(words)}." if words and sector_key == suggested.key else
               "Chosen by you." if sector_key != suggested.key else "No sector keyword found: choose one.")
    currency = st.selectbox("Reporting currency", list(CURRENCIES), index=list(CURRENCIES).index(ext.data.currency),
                            key=f"cur-{file_key}", help="Found in the file; change it if the file does not say.")
    st.divider()
    st.caption("Claude API: connected" if has_key else
               "Claude API: not configured. Needed only to read PDFs and to write the memo.")
    st.caption("Excel files are read and analysed on this computer. Data goes to the Claude API only when you "
               "read a PDF or write the memo.")

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

a = analyse(ext, sector_key, currency, overrides, docs, decisions, analyst, include)
data, metrics, results, al, view, money = a.data, a.metrics, a.results, a.findings, a.view, a.money
review_key = f"review-{file_key}-{'-'.join(r.rule.id for r in al)}"
reviews = {r.rule.id: ("Pending", "") for r in al}
for idx, ch in edited(review_key).items():
    rid = al[int(idx)].rule.id
    status, comment = reviews[rid]
    reviews[rid] = (ch.get("Status", status), ch.get("Comment", comment) or "")

# ---------------------------------------------------------------- header
L = data.pl_years[-1]
B = view.bs_years[-1]
years3 = data.pl_years[-3:]
st.markdown(f"<div class='dd-eyebrow'>Preliminary financial due diligence · {html.escape(a.sector.name)}</div>"
            f"<div class='dd-title'>{html.escape(ext.company)}</div>"
            f"<div class='dd-sub'>{html.escape(name)} · {fy(years3[0])}–{fy(L)} · {money.unit_long} · "
            f"{html.escape(ext.method)}</div>", unsafe_allow_html=True)
if not a.checks_ok:
    st.warning("Reading check failed: a subtotal rebuilt from the lines read does not match the published one. "
               "A line may be missing or misclassified — see Source data before relying on the figures.")

tab_ov, tab_deal, tab_rf, tab_sec, tab_src, tab_m, tab_ai = st.tabs(
    ["Overview", "Deal view", f"Red flags ({len(al)})", "Sector", "Source data", "Metrics", "AI memo"])

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
    st.markdown("<div class='dd-kpis'>" + "".join(
        f"<div class='dd-kpi'><div class='l'>{l} · {fy(L if 'EBITDA' in l or l in ('Revenue', 'Cash conversion') else B)}"
        f"</div><div class='v'>{v}</div><div class='s'>{s}</div></div>" for l, v, s in kpis) + "</div>",
        unsafe_allow_html=True)

    by = {k: sum(r.rule.severity == k for r in al) for k in SEVERITIES}
    st.markdown(f"<div class='dd-section'>Key findings · {len(al)} red flags</div>"
                + " ".join(f"{pill(k)} <span style='color:#5b6474;font-size:.85rem'>{by[k]}</span>&nbsp;&nbsp;"
                           for k in SEVERITIES), unsafe_allow_html=True)
    if not al:
        st.success("No rule fired: no red flags on the data provided.")
    ordered = sorted(al, key=lambda r: SEVERITIES.index(r.rule.severity))
    st.markdown("<div class='dd-list'>" + "".join(
        f"<div class='dd-find'>{pill(r.rule.severity)}<span class='id'>{r.rule.id}</span>"
        f"<span>{html.escape(r.rule.name)}</span><span class='area'>{r.rule.area}</span>"
        f"<span class='yr'>{r.years_text}</span></div>" for r in ordered) + "</div>", unsafe_allow_html=True)

    st.markdown("<div class='dd-section'>Financial summary</div>", unsafe_allow_html=True)
    summary = pd.DataFrame([[LABELS[k]] + [fmt_metric(k, metrics[k].get(y), money) for y in years3]
                            for k in SUMMARY_ROWS], columns=[f"{money.unit} unless stated"] + [fy(y) for y in years3])
    st.dataframe(summary, hide_index=True, width="stretch", height=35 * (len(summary) + 1) + 3)
    found = len(ext.items) - len(ext.missing)
    passed = sum(c["OK"] for c in a.checks)
    st.caption(f"Reading checks: {passed} of {len(a.checks)} passed. Data coverage: {found} of {len(ext.items)} "
               "standard line items identified" + (f". Not found: {', '.join(ext.missing)}." if ext.missing else "."))

# ---------------------------------------------------------------- deal view
with tab_deal:
    st.caption("The three numbers a deal team asks for first, calculated by the code from the lines in Source data. "
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
        pending = sum(status == "Pending" for status, _ in reviews.values())
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
            st.markdown(f"**Evidence**  \n{r.evidence}")
            st.markdown(f"**Test**  \n{rule.test} · threshold {rule.limit_text()}"
                        + (f"  \n_{rule.calibration[0].upper() + rule.calibration[1:]}._" if rule.calibration else ""))
            c1, c2 = st.columns(2)
            c1.markdown(f"**What to investigate**  \n{rule.focus}")
            c2.markdown(f"**Why it matters**  \n{rule.rationale}")
            c1.markdown(f"**Question for management**  \n{rule.question}")
            c2.markdown(f"**Document to request**  \n{rule.request}")

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
        st.caption("Tick what the company has provided outside this file. Missing documents raise R18.")
        st.data_editor(pd.DataFrame(ext.data.documents, columns=["Document", "Received"]), key=docs_key,
                       hide_index=True, width="stretch", disabled=["Document"])
    with c2:
        if data.clients:
            st.markdown("<div class='dd-section'>Sales by customer</div>", unsafe_allow_html=True)
            rows = [[c.name] + [fmt_metric("vendas", c.values.get(y), money) for y in years3] for c in data.clients]
            st.dataframe(pd.DataFrame(rows, columns=["Customer"] + [fy(y) for y in years3]), hide_index=True,
                         width="stretch")

# ---------------------------------------------------------------- metrics
with tab_m:
    rows = [[label] + [fmt_metric(key, metrics[key].get(y), money) for y in data.years] for key, label in LABELS.items()]
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
