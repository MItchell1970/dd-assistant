"""Layer 1g — a messy data room read whole: ledger exports, trial balances, bank statements, supplier listings, and the
annual accounts and schedules beside them.

The figures of the analysis come from the ledger, not from the annual accounts: each line of the income statement and
the balance sheet is the sum of the accounts mapped to it (mapping.py), with the file and row of each account. The
annual accounts are used to check the mapping (to the euro, every year) and for the cash flow statement and the
schedules a ledger does not have. The months give the working capital peg and the LTM; the bank statements and
supplier listings give the proof of cash (proof_of_cash.py), which rules R31 and R32 test.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, replace

from .extract import FIELD_BY_KEY, Extraction
from .ledger import Ledger, read_export, read_ledger
from .mapping import (ASSETS, PL_KEYS, AccountMap, high_share, map_accounts, mapped_lines, tie_to_accounts)
from .proof_of_cash import Proof, prove, read_listing, read_statement

NWC_KEYS = ("inv", "cli", "oac", "forn", "opc")


@dataclass
class LedgerRoom:
    ledger: Ledger
    maps: list[AccountMap]
    ties: list[dict]                 # each line from the ledger against the annual accounts
    proof: Proof
    timing: dict[str, float]         # seconds, by step
    decisions: dict = field(default_factory=dict)

    @property
    def pending(self) -> list[AccountMap]:
        return [m for m in self.maps if m.key is None and not m.decision]

    @property
    def ties_ok(self) -> bool:
        return all(t["OK"] for t in self.ties)

    @property
    def high(self) -> float:
        return high_share(self.maps)


def is_ledger_room(files: list[tuple[str, bytes]]) -> bool:
    """A data room with ERP exports or trial balances (an account code and description per row)."""
    return any(n.lower().endswith((".csv", ".xlsx")) and read_export(n, c) is not None for n, c in files[:200]
               if "balancete" in n.lower() or "erp" in n.lower() or "trial" in n.lower() or n.lower().endswith(".csv"))


def read_ledger_room(files: list[tuple[str, bytes]], decisions: dict | None = None) -> Extraction:
    from .dataroom import read_data_room
    t0 = time.perf_counter()
    ledger_files, statements, listings, rest, table = [], [], [], [], []
    for name, content in files:
        low = name.lower()
        if low.endswith((".csv", ".xlsx")) and read_export(name, content) is not None:
            ledger_files.append((name, content))
        elif low.endswith((".csv", ".pdf")) and (st := read_statement(name, content)) is not None:
            statements.append(st)
            table.append({"File": name, "Read as": f"Bank statement — {st.bank} {st.number}",
                          "Found": f"{len(st.lines)} movements"})
        elif low.endswith(".xlsx") and (li := read_listing(name, content)) is not None:
            listings.append(li)
            table.append({"File": name, "Read as": "Supplier balances listing",
                          "Found": f"{li['lines']} suppliers, total {li['total']:,.2f}"})
        else:
            rest.append((name, content))
    t1 = time.perf_counter()
    ledger = read_ledger(ledger_files)
    t2 = time.perf_counter()
    maps = map_accounts(ledger, decisions)
    t3 = time.perf_counter()
    ext = read_data_room(rest)
    annual = ext.data
    lines, sources = mapped_lines(ledger, maps, annual.years)
    ties = tie_to_accounts(lines, annual, annual.years)
    t4 = time.perf_counter()
    proof = prove(ledger, maps, statements, listings)
    t5 = time.perf_counter()

    data = replace(annual, lines=dict(annual.lines), sources=dict(annual.sources))
    for key in PL_KEYS + ASSETS + ("cp", "fin_lp", "opnc", "fin_cp", "forn", "opc"):
        if key not in lines:
            continue
        years = annual.pl_years if key in PL_KEYS else annual.bs_years
        data.lines[key] = {y: lines[key].get(y) for y in years}
        data.sources[key] = f"Ledger: {sources.get(key, '')}"
    data.monthly = _monthly(ledger, maps)
    data.proof = proof.by_year()
    data.proof_text = _proof_text(proof)
    for row in ext.items:      # the review table: where each line now comes from
        if row["key"] in lines:
            row["Source"] = data.sources[row["key"]]
            row["Found as"] = f"Ledger: {sum(1 for m in maps if m.key == row['key'])} account(s) mapped"
            for y in data.years:
                col = f"FY{str(y)[2:]}"
                if col in row:
                    row[col] = data.v(row["key"], y)
    for f in ledger.files:
        table.append({"File": f["File"], "Read as": f["Read as"], "Found": f"period {f['Period']}"})
    content = dict(files)
    for row in table:
        row["Size (KB)"] = round(len(content.get(row["File"], b"")) / 1024)
        row["SHA-256"] = hashlib.sha256(content.get(row["File"], b"")).hexdigest()
    method = (f"Messy data room: ledger of {len(ledger.series)} accounts mapped to the model "
              f"({high_share(maps):.0%} High confidence, {sum(1 for m in maps if m.key is None and not m.decision)} "
              f"pending) and tied to the annual accounts; proof of cash on {len({m.account for m in proof.months})} "
              f"bank accounts; annual accounts: {ext.method}")
    room = LedgerRoom(ledger, maps, ties, proof, {"Sort the files": t1 - t0, "Read the ledger": t2 - t1,
                                                   "Map the accounts": t3 - t2,
                                                   "Read the annual accounts and tie": t4 - t3,
                                                   "Proof of cash": t5 - t4}, dict(decisions or {}))
    out = replace(ext, data=data, method=method, files=table + ext.files, ledger_room=room)
    return out


def _monthly(ledger: Ledger, maps: list[AccountMap]) -> dict:
    """EUR thousands by month: the month's figure for profit and loss lines, the month-end balance for the rest."""
    out: dict[str, dict] = {}
    for m in maps:
        if not m.key:
            continue
        sign = 1 if m.key in ASSETS else -1
        for ym, p in m.series.points.items():
            value = (p.movement if m.key in PL_KEYS else p.closing)
            if value is None:
                continue
            out.setdefault(m.key, {}).setdefault(ym, 0.0)
            out[m.key][ym] += sign * value / 1000
    return {k: {ym: round(v, 5) for ym, v in sorted(vals.items())} for k, vals in out.items()}   # to the cent


def _proof_text(proof: Proof) -> dict[int, str]:
    out: dict[int, list[str]] = {}
    for d in proof.differences:
        out.setdefault(d.ym[0], []).append(f"{d.bank} ({d.account}), {d.ym[0]}-{d.ym[1]:02d}: ledger above the bank by "
                                           f"€{d.amount / 1000:,.0f}k from that month — looks like {d.looks_like} "
                                           f"({d.source})")
    for r in proof.receipts:
        if abs(r["difference"]) > 1000:
            out.setdefault(r["month"][0], []).append(
                f"customer receipts in the banks {r['month'][0]}-{r['month'][1]:02d}: €{r['bank'] / 1000:,.0f}k "
                f"against €{r['expected'] / 1000:,.0f}k expected (revenue + VAT − change in receivables)")
    return {y: "; ".join(v) + "." for y, v in out.items()}


def monthly_nwc(d) -> dict[tuple[int, int], float]:
    """Net working capital at each month-end from the ledger, EUR thousands (inventories + receivables + other current
    assets − payables − other current liabilities)."""
    m = d.monthly
    months = sorted(set().union(*(m.get(k, {}).keys() for k in NWC_KEYS))) if m else []
    return {ym: round(sum(m.get(k, {}).get(ym, 0.0) for k in ("inv", "cli", "oac"))
                      - sum(m.get(k, {}).get(ym, 0.0) for k in ("forn", "opc")), 5) for ym in months}


def ltm(d, key_or_keys, end: tuple[int, int]) -> float | None:
    """Last twelve months to `end` of profit and loss lines, EUR thousands."""
    keys = (key_or_keys,) if isinstance(key_or_keys, str) else key_or_keys
    months = [(end[0] - (1 if end[1] - i <= 0 else 0), (end[1] - i - 1) % 12 + 1) for i in range(12)]
    vals = [d.monthly.get(k, {}).get(ym) for k in keys for ym in months]
    return None if any(v is None for v in vals) else round(sum(vals), 5)


EBITDA_KEYS = ("vendas", "cmv", "fse", "pess", "orend", "own", "imp", "ogast")
LABEL = {k: f.label for k, f in FIELD_BY_KEY.items()}
