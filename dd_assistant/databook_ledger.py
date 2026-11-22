"""Layer 4c — the databook sheets of a messy data room: Mapping, Proof of Cash and Monthly & LTM.

Written like the rest of the databook (databook.py): inputs in blue, formulas in black, the reviewer's cells in
yellow; every total is a formula, and Checks compares it with the value computed in Python. EUR thousands in the tie
to the annual accounts; euros in the ledger and the bank statements (as the files give them).
"""
from __future__ import annotations

from openpyxl.utils import get_column_letter as col

from .databook import _BOLD, _DECISION, _INPUT, _NUM, _finish, _formula, _header, _put, _title
from .ledger_room import EBITDA_KEYS, ltm, monthly_nwc
from .mapping import ASSETS, LABEL, PL_KEYS
from .proof_of_cash import VAT
from .rules import fy

_EUR = '#,##0.00;(#,##0.00);"–"'


def mapping_sheet(ws, a) -> list[tuple]:
    """Every account, its line, confidence and status, its December balances; the tie to the annual accounts by
    SUMIFS. Returns the controls: (label, year, cell, Python value)."""
    room, d = a.ext.ledger_room, a.data
    years = d.years
    first = min(room.ledger.months)[0]
    _title(ws, "Mapping", "FICTITIOUS, synthetic test data. Each account of the ledger and the line of the model it "
                          "goes to, with the confidence and why; Low accounts wait for the reviewer. December balances "
                          "in euros (debit positive); model values in EUR thousands.")
    head = ["Code(s)", "Account", "Line (key)", "Line", "Confidence", "Found by", "Status", "Reason / reviewer's "
            "decision", "Sign", "P&L"] + [f"Ledger {fy(y)} (EUR)" for y in years] + [f"Model {fy(y)} (EUR k)"
                                                                                      for y in years]
    _header(ws, 4, head)
    r = 5
    for m in room.maps:
        key = m.key or ""
        sign = 1 if key in ASSETS else -1
        decision = f"{m.decision.get('reason', '')} ({m.decision.get('who', 'reviewer')})" if m.decision else ""
        cells = [m.series.code, m.series.name, key, LABEL.get(key, ""), m.confidence, m.method, m.status,
                 decision or m.reason, sign, "Yes" if key in PL_KEYS else "No"]
        for c, value in enumerate(cells, 1):
            _put(ws, r, c, value, fill=_DECISION if m.confidence == "Low" and c in (3, 8) else None)
        for i, y in enumerate(years):
            p = m.series.points.get((y, 12))
            value = p.closing if p else (next((room.ledger.tb[first][c][0] for c in m.series.codes
                                               if c in room.ledger.tb.get(first, {})), None)
                                         if y == first - 1 and key not in PL_KEYS else None)
            _put(ws, r, 11 + i, value, _INPUT, _EUR)
            bal = f"{col(11 + i)}{r}"
            _formula(ws, r, 11 + len(years) + i, f'=IF(OR($C{r}="",ISBLANK({bal})),"",$I{r}*{bal}/1000)')
        r += 1
    last = r - 1
    r += 2
    _put(ws, r, 1, "Tie to the annual accounts (EUR thousands): each line from the mapped accounts against the "
                   "accounts as published", _BOLD)
    r += 1
    _header(ws, r, ["Line", "Key", "Year", "From the ledger", "Annual accounts", "Difference"])
    controls = []
    tie = {(t["key"], t["Year"]): t for t in room.ties}
    for (key, y), t in tie.items():
        r += 1
        mcol = col(11 + len(years) + years.index(y))
        formula = f'=SUMIFS({mcol}5:{mcol}{last},$C$5:$C${last},"{key}")'
        if key == "cp" and y >= first:     # equity includes the year's result, still in the P&L accounts
            formula += f'+SUMIFS({mcol}5:{mcol}{last},$J$5:$J${last},"Yes")'
        _put(ws, r, 1, t["Line"])
        _put(ws, r, 2, key)
        _put(ws, r, 3, fy(y))
        _formula(ws, r, 4, formula)
        _put(ws, r, 5, t["Annual accounts"], _INPUT, _NUM)
        _formula(ws, r, 6, f"=D{r}-E{r}")
        if key in ("vendas", "cp") and y in d.pl_years:
            controls.append((f"Mapping: {LABEL[key].lower()} from the ledger", y, f"Mapping!D{r}",
                             t["From the ledger"]))
    _finish(ws, [14, 28, 8, 26, 10, 26, 22, 60, 6, 6] + [16] * (2 * len(years)), "C5", 4, 10 + 2 * len(years))
    return controls


def proof_sheet(ws, a) -> list[tuple]:
    room = a.ext.ledger_room
    p = room.proof
    _title(ws, "Proof of Cash", "FICTITIOUS, synthetic test data. Each bank, each month: opening + receipts − payments "
                                "= closing, and the ledger's cash against the statement. Euros.")
    _header(ws, 4, ["Bank", "Ledger account", "Month", "Opening", "Receipts", "Payments", "Closing (statement)",
                    "Roll-forward check", "Ledger closing", "Ledger − bank", "Statement file"])
    r = 5
    for m in p.months:
        for c, v in enumerate([m.bank, m.account, f"{m.ym[0]}-{m.ym[1]:02d}"], 1):
            _put(ws, r, c, v)
        for c, v in ((4, m.opening), (5, m.receipts), (6, m.payments), (7, m.closing), (9, m.ledger)):
            _put(ws, r, c, v, _INPUT, _EUR)
        _formula(ws, r, 8, f"=D{r}+E{r}-F{r}-G{r}", fmt=_EUR)
        _formula(ws, r, 10, f'=IF(ISBLANK(I{r}),"",I{r}-G{r})', fmt=_EUR)
        _put(ws, r, 11, m.source)
        r += 1
    last = r - 1
    end = max(m.ym for m in p.months)
    total_row = r + 1
    _put(ws, total_row, 1, f"Ledger less the banks at {end[0]}-{end[1]:02d} (all accounts)", _BOLD)
    _formula(ws, total_row, 10, f'=SUMIFS(J5:J{last},C5:C{last},"{end[0]}-{end[1]:02d}")', fmt=_EUR, bold=True)
    controls = [("Proof of cash: ledger less the banks", end[0], f"'Proof of Cash'!J{total_row}",
                 round(sum(m.difference or 0 for m in p.months if m.ym == end), 2))]
    r = total_row + 2
    _put(ws, r, 1, "Where a difference appears, and what it looks like", _BOLD)
    r += 1
    _header(ws, r, ["Bank", "Ledger account", "Month", "Amount", "Looks like", "Source"])
    for x in p.differences or []:
        r += 1
        for c, v in enumerate([x.bank, x.account, f"{x.ym[0]}-{x.ym[1]:02d}", x.amount, x.looks_like, x.source], 1):
            _put(ws, r, c, v, _INPUT if c == 4 else None, _EUR if c == 4 else None)
    if not p.differences:
        r += 1
        _put(ws, r, 1, "None: every month-end of the ledger equals the bank statements.")
    r += 2
    _put(ws, r, 1, "Customer receipts against revenue + VAT − change in receivables (euros)", _BOLD)
    r += 1
    _put(ws, r, 1, "VAT rate (assumption)")
    _put(ws, r, 2, VAT, fill=_DECISION, unlocked=True, fmt="0%")
    vat = f"$B${r}"
    r += 1
    _header(ws, r, ["Month", "Revenue", "VAT", "Change in receivables", "Expected receipts", "Receipts in the banks",
                    "Difference"])
    for x in p.receipts:
        r += 1
        _put(ws, r, 1, f"{x['month'][0]}-{x['month'][1]:02d}")
        _put(ws, r, 2, x["revenue"], _INPUT, _EUR)
        _formula(ws, r, 3, f"=B{r}*{vat}", fmt=_EUR)
        _put(ws, r, 4, x["change_ar"], _INPUT, _EUR)
        _formula(ws, r, 5, f"=B{r}+C{r}-D{r}", fmt=_EUR)
        _put(ws, r, 6, x["bank"], _INPUT, _EUR)
        _formula(ws, r, 7, f"=F{r}-E{r}", fmt=_EUR)
    r += 2
    _put(ws, r, 1, "Supplier listings against the ledger (euros)", _BOLD)
    r += 1
    _header(ws, r, ["Year-end", "Listing total", "Ledger (supplier account)", "Difference", "Listing file"])
    for s in p.suppliers:
        r += 1
        _put(ws, r, 1, fy(s["year"]))
        _put(ws, r, 2, s["listing"], _INPUT, _EUR)
        _put(ws, r, 3, s["ledger"], _INPUT, _EUR)
        _formula(ws, r, 4, f"=B{r}-C{r}", fmt=_EUR)
        _put(ws, r, 5, s["source"])
        controls.append(("Supplier listing less the ledger", s["year"], f"'Proof of Cash'!D{r}", s["difference"]))
    _finish(ws, [18, 14, 10, 16, 16, 16, 18, 16, 16, 16, 60], "D5", 4, 11)
    ws.auto_filter.ref = f"A4:K{last}"
    return controls


def monthly_sheet(ws, a) -> list[tuple]:
    d = a.data
    _title(ws, "Monthly & LTM", "FICTITIOUS, synthetic test data. From the monthly ledger: revenue and EBITDA before "
                                "adjustments by month, net working capital at each month-end; LTM and the average of "
                                "the last 12 month-ends (a basis for the peg, still to normalise). EUR thousands.")
    _header(ws, 4, ["Month", "Revenue", "EBITDA (before adjustments)", "Net working capital"])
    nwc = monthly_nwc(d)
    months = sorted(nwc)
    keys = [k for k in EBITDA_KEYS if k in d.monthly]
    r = 5
    for ym in months:
        _put(ws, r, 1, f"{ym[0]}-{ym[1]:02d}")
        _put(ws, r, 2, d.monthly.get("vendas", {}).get(ym), _INPUT, _NUM)
        _put(ws, r, 3, round(sum(d.monthly.get(k, {}).get(ym, 0.0) for k in keys), 5), _INPUT, _NUM)
        _put(ws, r, 4, nwc[ym], _INPUT, _NUM)
        r += 1
    last = r - 1
    end = months[-1]
    r += 1
    rows = {}
    for label, c, fn in (("LTM revenue", "B", "SUM"), ("LTM EBITDA (before adjustments)", "C", "SUM"),
                         ("Average net working capital, last 12 month-ends", "D", "AVERAGE")):
        _put(ws, r, 1, f"{label} to {end[0]}-{end[1]:02d}", _BOLD)
        _formula(ws, r, 2, f"={fn}({c}{last - 11}:{c}{last})", bold=True)
        rows[label] = r
        r += 1
    _finish(ws, [44, 16, 22, 20], "B5", 4, 4)
    last12 = [nwc[ym] for ym in months[-12:]]
    return [("LTM revenue (ledger)", end[0], f"'Monthly & LTM'!B{rows['LTM revenue']}", ltm(d, "vendas", end)),
            ("Average NWC, last 12 month-ends", end[0],
             f"'Monthly & LTM'!B{rows['Average net working capital, last 12 month-ends']}", sum(last12) / 12)]
