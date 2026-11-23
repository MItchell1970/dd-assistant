"""The local app's tabs for a messy data room (FICTITIOUS test data): Mapping, Proof of cash, Time.

Only display and the reviewer's inputs (decisions on Low accounts, the minutes of the review): every figure comes
from ledger.py, mapping.py, proof_of_cash.py and timing.py.
"""
from __future__ import annotations

import html
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from .ledger_room import LedgerRoom
from .mapping import EXCLUDE, LABEL
from .timing import MANUAL, PUBLIC, SOURCE, AgentTime, comparison, manual_minutes

LINES = ["vendas", "cmv", "fse", "pess", "orend", "own", "imp", "ogast", "da", "juros", "irc", "aft", "oanc", "inv",
         "cli", "oac", "caixa", "cp", "fin_lp", "opnc", "fin_cp", "forn", "opc"]


def _kpis(items: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(items))
    for c, (label, value, note) in zip(cols, items):
        c.metric(label, value, help=note)


def mapping_tab(room: LedgerRoom, decisions: dict) -> None:
    maps = room.maps
    pending = room.pending
    _kpis([("Accounts in the ledger", str(len(maps)), "one series per account; a renamed account is one series"),
           ("High confidence", f"{room.high:.0%}", "found by a rule and the behaviour of the balance agrees"),
           ("Waiting for you", str(len(pending)), "Low accounts: never mapped by the agent"),
           ("Tie to the annual accounts", f"{sum(t['OK'] for t in room.ties)} of {len(room.ties)}",
            "each line from the ledger against the accounts as published, to the euro")])
    if pending:
        st.warning(f"{len(pending)} account(s) wait for your decision. Until then they are left out, and the tie to "
                   "the annual accounts shows the gap: nothing enters in silence.")
        for m in pending:
            with st.container(border=True):
                st.markdown(f"**{html.escape(m.series.code)} · {html.escape(m.series.name)}** — {html.escape(m.reason)}")
                options = LINES + [EXCLUDE]
                c1, c2, c3 = st.columns([2, 4, 1.4], vertical_alignment="bottom")
                key = c1.selectbox("Line", options, index=options.index(m.suggestion) if m.suggestion in options else
                                   len(options) - 1, key=f"dec-line-{m.series.code}",
                                   format_func=lambda k: "Exclude (not in the model)" if k == EXCLUDE else LABEL.get(k, k))
                reason = c2.text_input("Why (recorded)", key=f"dec-why-{m.series.code}",
                                       placeholder="e.g. invoices show small operating costs")
                if c3.button("Record", key=f"dec-go-{m.series.code}", type="primary", disabled=not reason.strip()):
                    decisions[m.series.codes[0]] = {"key": key, "reason": reason.strip(), "who": "reviewer (this app)",
                                                    "when": datetime.now().strftime("%Y-%m-%d %H:%M")}
                    st.rerun()
    st.markdown("<div class='dd-section'>Every account and the line it goes to</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"Code(s)": m.series.code, "Account": m.series.name,
                                "Line": LABEL.get(m.key, "—") if m.key else ("excluded" if m.decision else "—"),
                                "Confidence": m.confidence, "Found by": m.method, "Status": m.status,
                                "Why": (m.decision.get("reason", "") + f" ({m.decision.get('who', '')})") if m.decision
                                else m.reason} for m in maps]),
                 hide_index=True, width="stretch",
                 column_config={"Why": st.column_config.TextColumn(width="large")})
    st.markdown("<div class='dd-section'>What the agent normalised</div>", unsafe_allow_html=True)
    for n in room.ledger.notes:
        st.markdown(f"- {html.escape(n)}")
    off = [t for t in room.ties if not t["OK"]]
    st.markdown("<div class='dd-section'>Tie to the annual accounts (EUR thousands)</div>", unsafe_allow_html=True)
    st.caption("All lines tie to the euro." if not off else f"{len(off)} line(s) do not tie: shown first.")
    st.dataframe(pd.DataFrame([{"Line": t["Line"], "Year": f"FY{str(t['Year'])[2:]}",
                                "From the ledger": t["From the ledger"], "Annual accounts": t["Annual accounts"],
                                "Difference": t["Difference"], "OK": "✓" if t["OK"] else "✗"}
                               for t in sorted(room.ties, key=lambda t: t["OK"])]),
                 hide_index=True, width="stretch")


def proof_tab(room: LedgerRoom) -> None:
    p = room.proof
    end = max(m.ym for m in p.months)
    gap = sum(m.difference or 0 for m in p.months if m.ym == end)
    sup = p.suppliers[-1]["difference"] if p.suppliers else None
    _kpis([("Bank-months proved", f"{len(p.months)}", "two banks × the months of the statements"),
           ("Statements roll forward", f"{sum(m.rolls for m in p.months)} of {len(p.months)}",
            "opening + receipts − payments = closing"),
           (f"Ledger less the banks, {end[0]}-{end[1]:02d}", f"€{gap / 1000:,.0f}k", "all bank accounts"),
           ("Supplier listing less the ledger", "—" if sup is None else
            f"{'−' if sup < 0 else ''}€{abs(sup) / 1000:,.0f}k", "latest year-end")])
    if p.differences:
        st.markdown("<div class='dd-section'>Where the ledger and the bank part, and what it looks like</div>",
                    unsafe_allow_html=True)
        for d in p.differences:
            st.error(f"**{d.bank} ({d.account}), {d.ym[0]}-{d.ym[1]:02d}: €{d.amount:,.0f}** — looks like "
                     f"{d.looks_like}. Source: {d.source}")
    else:
        st.success("Every month-end of the ledger equals the bank statements.")
    df = pd.DataFrame([{"Month": f"{m.ym[0]}-{m.ym[1]:02d}", "Bank": m.bank, "Ledger − bank (EUR)": m.difference or 0}
                       for m in p.months])
    st.altair_chart(alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("Month:N", sort=None, axis=alt.Axis(labelAngle=-60)), y="Ledger − bank (EUR):Q", color="Bank:N")
        .properties(height=230, title="Ledger less the bank statement, each month-end"), use_container_width=True)
    st.markdown("<div class='dd-section'>Customer receipts against revenue + VAT − change in receivables</div>",
                unsafe_allow_html=True)
    off = [r for r in p.receipts if abs(r["difference"]) > 1000]
    st.caption(f"{len(p.receipts)} months; VAT at 23% (an assumption). "
               + ("Every month within €1k." if not off else f"{len(off)} month(s) apart by more than €1k:"))
    if off:
        st.dataframe(pd.DataFrame([{"Month": f"{r['month'][0]}-{r['month'][1]:02d}", "Revenue": r["revenue"],
                                    "Expected receipts": r["expected"], "In the banks": r["bank"],
                                    "Difference": r["difference"]} for r in off]), hide_index=True, width="stretch")
    st.markdown("<div class='dd-section'>Supplier listings against the ledger</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"Year-end": f"FY{str(s['year'])[2:]}", "Listing": s["listing"], "Ledger": s["ledger"],
                                "Difference": s["difference"], "Source": s["source"]} for s in p.suppliers]),
                 hide_index=True, width="stretch")
    with st.expander("Every bank-month"):
        st.dataframe(pd.DataFrame([{"Bank": m.bank, "Month": f"{m.ym[0]}-{m.ym[1]:02d}", "Opening": m.opening,
                                    "Receipts": m.receipts, "Payments": m.payments, "Closing": m.closing,
                                    "Rolls": "✓" if m.rolls else "✗", "Ledger": m.ledger, "Ledger − bank": m.difference}
                                   for m in p.months]), hide_index=True, width="stretch")


def time_tab(room: LedgerRoom, analysis_seconds: float) -> None:
    steps = dict(room.timing)
    steps["Analysis and databook"] = analysis_seconds
    review = st.number_input("Your review time (minutes), when you have timed it", min_value=0.0, value=None,
                             step=5.0, key="review-minutes",
                             help="Deciding the Low accounts, reading the Medium ones, the differences and findings.")
    agent = AgentTime(steps, review)
    manual = manual_minutes()
    st.markdown(f"**{html.escape(comparison(agent))}**")
    _kpis([("Manual (estimated)", f"{manual:.0f} min", f"{manual / 60:.1f} hours; fixed before the agent's run"),
           ("Agent + human review", f"{agent.seconds:.1f} s + review" if review is None else
            f"{agent.seconds / 60 + review:.0f} min",
            "the agent's measured seconds and the review, timed by a person: never the seconds alone"),
           ("Human review", "to be timed" if review is None else f"{review:.0f} min", "timed by a person, never assumed")])
    st.caption(SOURCE)
    st.caption("Public references: " + " · ".join(f"[{what}]({url}) ({who})" for what, who, url, *_ in PUBLIC))
    rows = [{"Task": t.name, "Units": f"{t.count:g} {t.units} × {t.minutes_per_unit:g} min",
             "Manual (min)": round(t.minutes), "Agent step": t.agent_step,
             "Agent (s)": round(steps.get(t.agent_step, 0.0), 2)} for t in MANUAL]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    agent_min = agent.seconds / 60 + (review or 0)
    rows = [("Manual (estimated)", manual, f"{manual:.0f} min ({manual / 60:.1f} h)"),
            ("Agent + human review", agent_min, f"{agent.seconds:.1f} s + human review (to be timed)"
             if review is None else f"{agent.seconds:.1f} s + {review:.0f} min = {agent_min:.0f} min")]
    top = max(manual, agent_min) or 1
    st.markdown("<div class='dd-section'>Manual estimated vs agent</div>" + "".join(
        f"<div style='display:grid;grid-template-columns:260px 1fr;gap:12px;align-items:center;margin:6px 0'>"
        f"<span>{html.escape(who)}</span><span><span style='display:inline-block;height:22px;vertical-align:middle;"
        f"width:{max(minutes / top * 80, 0.4):.2f}%;background:#8b949e;border-radius:3px'></span>"
        f"<span style='margin-left:8px'>{html.escape(label)}</span></span></div>" for who, minutes, label in rows),
        unsafe_allow_html=True)
