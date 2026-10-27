"""Streamlit app — upload a company's financials, review the red flags, download, write the memo.

Run (with the virtual environment active):
    streamlit run app.py

The app only wires the layers together (extract → metrics → rules → report → ai_memo → memo_check).
It does no calculations of its own and creates no findings.
"""
from __future__ import annotations

import hashlib
import html
import io
import os
from dataclasses import replace
from pathlib import Path

import anthropic
import pandas as pd
import streamlit as st

from dd_assistant.ai_memo import EFFORT, MODEL, PROMPT_FILE, MemoError, build_material, load_env, write_memo
from dd_assistant.extract import ExtractionError, apply_edits, data_room_text, read_financials
from dd_assistant.memo_check import MemoCheck, check_memo, report
from dd_assistant.metrics import LABELS, compute_metrics
from dd_assistant.report import REVIEW_STATES, csv_bytes, fmt_metric, write_excel
from dd_assistant.rules import SEVERITIES, alerts, evaluate, fy

DATA = Path(__file__).parent / "data"
SAMPLES = {"Duriva — data room with planted issues": DATA / "Duriva_data_room.xlsx",
           "Velmora — clean company": DATA / "Velmora_data_room.xlsx"}
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
.dd-kpis {display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: .4rem 0 1.4rem;}
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
</style>
"""


def pill(severity: str) -> str:
    return (f"<span class='dd-pill'><span class='dd-dot' style='background:{SEVERITY_COLOR[severity]}'></span>"
            f"{severity}</span>")


def money(v) -> str:
    return "n/a" if v is None else f"€{fmt_metric('vendas', v)}k"


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
             "adjusted EBITDA, debt schedule. Excel or PDF. No template needed.")
    sample = st.radio("…or open a sample data room", list(SAMPLES), disabled=uploaded is not None)
    st.divider()
    st.caption("Claude API: connected" if has_key else
               "Claude API: not configured. Needed only to read PDFs and to write the memo.")
    st.caption("Excel files are read and analysed on this computer. Data goes to the Claude API only when you "
               "read a PDF or write the memo.")

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

# ---------------------------------------------------------------- reviewer input (read before the analysis)
src_key, docs_key = f"src-{file_key}", f"docs-{file_key}"
overrides: dict[str, dict[int, float | None]] = {}
for idx, changes in st.session_state.get(src_key, {}).get("edited_rows", {}).items():
    key = ext.items[int(idx)]["key"]
    for col, val in changes.items():
        if col.startswith("FY"):
            overrides.setdefault(key, {})[2000 + int(col[2:])] = None if val is None or pd.isna(val) else float(val)
data = apply_edits(ext.data, overrides) if overrides else ext.data
doc_edits = st.session_state.get(docs_key, {}).get("edited_rows", {})
if doc_edits:
    docs = list(data.documents)
    for idx, ch in doc_edits.items():
        if "Received" in ch:
            docs[int(idx)] = (docs[int(idx)][0], bool(ch["Received"]))
    data = replace(data, documents=docs)

metrics = compute_metrics(data)
results = evaluate(data, metrics)
al = alerts(results)
review_key = f"review-{file_key}-{'-'.join(r.rule.id for r in al)}"
reviews = {r.rule.id: ("Pending", "") for r in al}
for idx, ch in st.session_state.get(review_key, {}).get("edited_rows", {}).items():
    rid = al[int(idx)].rule.id
    status, comment = reviews[rid]
    reviews[rid] = (ch.get("Status", status), ch.get("Comment", comment) or "")

# ---------------------------------------------------------------- header
L = data.pl_years[-1]
years3 = data.pl_years[-3:]
st.markdown(f"<div class='dd-eyebrow'>Preliminary financial due diligence</div>"
            f"<div class='dd-title'>{html.escape(ext.company)}</div>"
            f"<div class='dd-sub'>{html.escape(name)} · {fy(years3[0])}–{fy(L)} · EUR thousands · "
            f"{html.escape(ext.method)}</div>", unsafe_allow_html=True)

tab_ov, tab_rf, tab_src, tab_m, tab_ai = st.tabs(
    ["Overview", f"Red flags ({len(al)})", "Source data", "Metrics", "AI memo"])

# ---------------------------------------------------------------- overview
with tab_ov:
    g = lambda key, year=L: metrics[key].get(year)
    kpis = [
        ("Revenue", money(g("vendas")), f"{fmt_metric('g_vendas', g('g_vendas'))} growth vs {fy(data.pl_years[-2])}"),
        ("Reported EBITDA", money(g("ebitda")), f"{fmt_metric('ebitda_m', g('ebitda_m'))} margin"),
        ("Adjusted EBITDA (mgmt)", money(g("ebitda_adj")),
         f"Adjustments {fmt_metric('adj_pct', g('adj_pct'))} of reported"),
        ("Cash conversion", fmt_metric("conv", g("conv")), "Cash generated from operations / EBITDA"),
        ("Net debt / EBITDA", fmt_metric("nd_ebitda", g("nd_ebitda")),
         f"Covenant {fmt_metric('cov_lim', g('cov_lim'))} · headroom {fmt_metric('cov_head', g('cov_head'))}"
         if g("cov_lim") else f"Net debt {money(g('net_debt'))}"),
    ]
    st.markdown("<div class='dd-kpis'>" + "".join(
        f"<div class='dd-kpi'><div class='l'>{l} · {fy(L)}</div><div class='v'>{v}</div><div class='s'>{s}</div></div>"
        for l, v, s in kpis) + "</div>", unsafe_allow_html=True)

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
    summary = pd.DataFrame([[LABELS[k]] + [fmt_metric(k, metrics[k].get(y)) for y in years3] for k in SUMMARY_ROWS],
                           columns=["EUR k unless stated"] + [fy(y) for y in years3])
    st.dataframe(summary, hide_index=True, width="stretch", height=35 * (len(summary) + 1) + 3)
    found = len(ext.items) - len(ext.missing)
    st.caption(f"Data coverage: {found} of {len(ext.items)} standard line items identified"
               + (f". Not found: {', '.join(ext.missing)}." if ext.missing else "."))

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
    write_excel(results, metrics, data.years, buf, reviews, items=ext.items)
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Download Excel", buf.getvalue(), f"{stem}_red_flags.xlsx", mime=XLSX_MIME, type="primary")
    d2.download_button("Download CSV", csv_bytes(results, reviews), f"{stem}_red_flags.csv", mime="text/csv")

    for r in sorted(al, key=lambda r: SEVERITIES.index(r.rule.severity)):
        rule = r.rule
        with st.expander(f"{rule.id} · {rule.name}  —  {rule.severity} · {r.years_text} · {reviews[rule.id][0]}"):
            st.markdown(f"**Evidence**  \n{r.evidence}")
            st.markdown(f"**Test**  \n{rule.test} · threshold {rule.limit_text()}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**What to investigate**  \n{rule.focus}")
            c2.markdown(f"**Why it matters**  \n{rule.rationale}")
            c1.markdown(f"**Question for management**  \n{rule.question}")
            c2.markdown(f"**Document to request**  \n{rule.request}")

# ---------------------------------------------------------------- what the agent read
with tab_src:
    st.caption("Every standard line item the agent identified, the label it matched in your file and the cell it "
               "read. Correct any figure here and the whole analysis updates.")
    if ext.missing:
        st.warning("Not found in the file: " + ", ".join(ext.missing) + ". Enter the figures below if available.")
    items = pd.DataFrame([{k: v for k, v in it.items() if k != "key"} for it in ext.items])
    st.data_editor(items, key=src_key, hide_index=True, width="stretch", height=560,
                   disabled=["Statement", "Line item", "Found as", "Source"],
                   column_config={"Line item": st.column_config.TextColumn(width="medium"),
                                  "Found as": st.column_config.TextColumn(width="medium")})
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("<div class='dd-section'>Key documents received</div>", unsafe_allow_html=True)
        st.caption("Tick what the company has provided outside this file. Missing documents raise R18.")
        st.data_editor(pd.DataFrame(ext.data.documents, columns=["Document", "Received"]), key=docs_key,
                       hide_index=True, width="stretch", disabled=["Document"])
    with c2:
        if data.clients:
            st.markdown("<div class='dd-section'>Sales by customer</div>", unsafe_allow_html=True)
            rows = [[c.name] + [fmt_metric("vendas", c.values.get(y)) for y in years3] for c in data.clients]
            st.dataframe(pd.DataFrame(rows, columns=["Customer"] + [fy(y) for y in years3]), hide_index=True,
                         width="stretch")
        if data.adjustments:
            st.markdown("<div class='dd-section'>Management EBITDA adjustments</div>", unsafe_allow_html=True)
            rows = [[a.name] + [fmt_metric("vendas", a.values.get(y)) for y in years3] for a in data.adjustments]
            st.dataframe(pd.DataFrame(rows, columns=["Adjustment"] + [fy(y) for y in years3]), hide_index=True,
                         width="stretch")

# ---------------------------------------------------------------- metrics
with tab_m:
    rows = [[label] + [fmt_metric(key, metrics[key].get(y)) for y in data.years] for key, label in LABELS.items()]
    st.dataframe(pd.DataFrame(rows, columns=["Metric (EUR k unless stated)"] + [fy(y) for y in data.years]),
                 hide_index=True, width="stretch", height=35 * (len(rows) + 1) + 3)

# ---------------------------------------------------------------- AI memo
with tab_ai:
    st.markdown("Claude reads the findings (with your review), the metrics and the full data room, and writes a "
                "two-page memo, the information request list and notes to improve the template. "
                "**It does no calculations and creates no findings**; every figure is then checked automatically.")
    source_text = ext.source_text
    if not source_text:   # a completed template carries no data room text
        room = st.file_uploader("Data room (Excel) for the memo", type=["xlsx", "xlsm"], key="data_room")
        source_text = data_room_text(io.BytesIO(room.getvalue())) if room is not None else ""
    material = build_material(data, metrics, results, source_text, reviews, ext.company)
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
                "Without a key, use the option below.")

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
