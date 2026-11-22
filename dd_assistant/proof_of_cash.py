"""Layer 2b — proof of cash: the ledger's cash against the bank's, month by month, and two related tie-outs.

  1. Each bank statement rolls forward: opening + receipts − payments = closing, every month.
  2. The cash in the ledger (each bank account, at each month-end) against the statement's closing balance. A
     difference that appears in a month and stays is a movement the ledger has and the bank does not. The engine
     says what it looks like, never more: when its amount is an inter-bank transfer of that month, a transfer counted
     twice; when the bank's customer receipts of that month fall short by about that amount, a receipt recorded
     without the cash (revenue or collection not supported by the bank).
  3. Customer receipts in the banks against revenue × (1 + VAT) − the change in receivables, month by month.
  4. The supplier listings (the payables sub-ledger at a year-end) against the ledger's supplier account.
Amounts in euros here; the rules (R31, R32) receive EUR thousands, and the materiality layer decides what is
material. A difference is shown with its month, its amount and the files it comes from.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date

from openpyxl import load_workbook

from .ledger import Ledger, month_of, norm, number

VAT = 0.23          # standard rate in Portugal: an assumption (exempt or reduced-rate sales change it), shown with it
TRIVIAL = 1.0       # euros: below this, a difference is rounding


@dataclass
class BankLine:
    day: date
    text: str
    amount: float        # receipt positive, payment negative
    balance: float
    source: str


@dataclass
class Statement:
    bank: str            # as printed
    number: str          # the account number found in the title
    opening: float
    lines: list[BankLine]
    files: list[str]


def _account_number(text: str) -> str:
    m = re.search(r"\b(?:conta|account|acc)\w*\D{0,20}(\d{4,})\b|\b(\d{4})\b(?=\D*$)", norm(text))
    nums = re.findall(r"\b\d{4,}\b", norm(text))
    return nums[0] if nums else ""


def read_statement(name: str, content: bytes) -> Statement | None:
    """A bank statement in CSV (date, description, debit, credit, balance) or a text PDF ('dd-mm-yyyy | text |
    amount | balance' lines); None when the file is not one."""
    low = name.lower()
    if low.endswith(".pdf"):
        from .dataroom import read_document
        text = read_document(name, content).text
        if not re.search(r"extrato|statement", text, re.I):
            return None
        title = next((l for l in text.splitlines() if re.search(r"extrato|statement", l, re.I)), name)
        opening = number(m.group(1)) if (m := re.search(r"Saldo inicial:\s*([-\d.,()]+)", text)) else None
        lines = []
        # a long line of a PDF may be wrapped in two: the text is read as one stream, entry by entry
        flat = re.sub(r"\s*\n\s*", " ", re.sub(r"\[p\.\d+\]", " ", text))
        entry = re.compile(r"(\d{2}-\d{2}-\d{4}) \| (.+?) \| (-?[\d.]+,\d{2}) \| (-?[\d.]+,\d{2})")
        for i, m in enumerate(entry.finditer(flat), 1):
            lines.append(BankLine(_day(m.group(1)), m.group(2).strip(), number(m.group(3)) or 0.0,
                                  number(m.group(4)) or 0.0, f"{name} › entry {i}"))
        if not lines:
            return None
        if opening is None:
            opening = lines[0].balance - lines[0].amount
        return Statement(_bank(title), _account_number(title), opening, lines, [name])
    if not low.endswith(".csv"):
        return None
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.reader(io.StringIO(text), delimiter=";" if text.count(";") > text.count(",") else ","))
    head = next((i for i, r in enumerate(rows[:10]) if any(norm(c) in ("data", "date") for c in r)
                 and any(norm(c) in ("saldo", "balance") for c in r)), None)
    if head is None:
        return None
    h = [norm(c) for c in rows[head]]
    col = lambda *names: next((i for i, c in enumerate(h) if c in names), None)
    dc, tc, deb, cred, bal = (col("data", "date"), col("descritivo", "descricao", "description"),
                              col("debito", "debit"), col("credito", "credit"), col("saldo", "balance"))
    title = " ".join(" ".join(r) for r in rows[:head]) or name
    lines = []
    for i, r in enumerate(rows[head + 1:], head + 2):
        if len(r) <= bal or not (d := _day(r[dc])):
            continue
        amount = (number(r[cred]) or 0.0) - (number(r[deb]) or 0.0)
        lines.append(BankLine(d, r[tc], amount, number(r[bal]) or 0.0, f"{name} › line {i}"))
    if not lines:
        return None
    return Statement(_bank(title), _account_number(title), lines[0].balance - lines[0].amount, lines, [name])


def _day(text) -> date | None:
    m = re.fullmatch(r"\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\s*", str(text or ""))
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def _bank(title: str) -> str:
    m = re.search(r"(Banco\s+\w+|Bank\s+\w+)", title)
    return m.group(1) if m else title[:40]


def merge(statements: list[Statement]) -> list[Statement]:
    """One statement per account: the yearly files joined in date order."""
    out: dict[str, Statement] = {}
    for s in sorted(statements, key=lambda s: s.lines[0].day):
        key = s.number or s.bank
        if key in out:
            out[key].lines += s.lines
            out[key].files += s.files
        else:
            out[key] = Statement(s.bank, s.number, s.opening, list(s.lines), list(s.files))   # a copy
    return list(out.values())


@dataclass
class Month:
    bank: str
    account: str            # ledger account
    ym: tuple[int, int]
    opening: float
    receipts: float
    payments: float
    closing: float          # statement
    ledger: float | None    # ledger closing
    rolls: bool             # opening + receipts − payments = closing
    source: str

    @property
    def difference(self) -> float | None:
        return None if self.ledger is None else round(self.ledger - self.closing, 2)


@dataclass
class Difference:
    """A difference between the ledger and the bank that appears in a month (and how much it moved)."""
    bank: str
    account: str
    ym: tuple[int, int]
    amount: float
    looks_like: str
    source: str


@dataclass
class Proof:
    months: list[Month]
    differences: list[Difference]
    receipts: list[dict]                  # per month: expected, in the banks, difference
    suppliers: list[dict]                 # per listing: total, ledger, difference
    notes: list[str] = field(default_factory=list)

    def by_year(self) -> dict[int, dict]:
        """For the rules, EUR thousands: the largest month-end difference ledger − bank (all banks together) and the
        supplier listing difference, per year."""
        out: dict[int, dict] = {}
        for ym in sorted({m.ym for m in self.months}):
            total = sum(m.difference or 0.0 for m in self.months if m.ym == ym)
            y = out.setdefault(ym[0], {"cash": 0.0, "cash_month": None, "ap": None})
            if abs(total) > abs(y["cash"]):
                y["cash"], y["cash_month"] = round(total, 2), ym
        for s in self.suppliers:
            out.setdefault(s["year"], {"cash": 0.0, "cash_month": None, "ap": None})["ap"] = s["difference"]
        return {y: {**v, "cash_k": round(v["cash"] / 1000, 3),
                    "ap_k": None if v["ap"] is None else round(v["ap"] / 1000, 3)} for y, v in out.items()}


def _prev(ym):
    return (ym[0] - 1, 12) if ym[1] == 1 else (ym[0], ym[1] - 1)


def prove(ledger: Ledger, maps, statements: list[Statement], listings: list[dict]) -> Proof:
    notes = []
    cash = [m for m in maps if m.key == "caixa"]
    months: list[Month] = []
    for st in merge(statements):
        acct = next((m for m in cash if st.number and st.number in norm(m.series.name)), None) or \
            next((m for m in cash if norm(st.bank) in norm(m.series.name)), None)
        if acct is None:
            notes.append(f"{st.bank} {st.number}: no cash account of the ledger names it; not proved.")
            continue
        balance = st.opening
        for ym in sorted({(l.day.year, l.day.month) for l in st.lines}):
            ls = [l for l in st.lines if (l.day.year, l.day.month) == ym]
            rec = round(sum(l.amount for l in ls if l.amount > 0), 2)
            pay = round(-sum(l.amount for l in ls if l.amount < 0), 2)
            closing = ls[-1].balance
            rolls = abs(balance + rec - pay - closing) <= TRIVIAL
            months.append(Month(st.bank, acct.series.code, ym, round(balance, 2), rec, pay, closing,
                                acct.series.closing(ym), rolls, f"{ls[0].source.split(' › ')[0]}"))
            balance = closing
    # where a difference appears, and what it looks like
    transfers = {}
    for st in statements:
        for l in st.lines:
            if re.search(r"transf", l.text, re.I):
                transfers.setdefault((l.day.year, l.day.month), []).append((st.bank, l.amount, l.source))
    rec_short = {}
    differences = []
    for acct in sorted({m.account for m in months}):
        series = sorted((m for m in months if m.account == acct), key=lambda m: m.ym)
        last = 0.0
        for m in series:
            d = m.difference or 0.0
            step = round(d - last, 2)
            if abs(step) > TRIVIAL:
                twin = [t for t in transfers.get(m.ym, []) if t[0] == m.bank and abs(t[1] - step) <= TRIVIAL]
                looks = (f"an inter-bank transfer of {step:,.2f} in the statement that month, counted twice in the ledger"
                         if twin else "a receipt recorded in the ledger that is not in the bank: revenue or a "
                                      "collection without the cash" if step > 0 else
                         "a payment in the ledger that is not in the bank (or a receipt in the bank not booked)")
                differences.append(Difference(m.bank, acct, m.ym, step, looks, m.source + (f"; {twin[0][2]}" if twin
                                                                                          else "")))
            last = d
    # customer receipts against revenue + VAT − change in receivables
    revenue = [m for m in maps if m.key == "vendas"]
    receivables = [m for m in maps if m.key == "cli"]
    receipts = []
    for ym in ledger.months:
        rev = -sum((m.series.points[ym].movement or 0.0) for m in revenue if ym in m.series.points)
        ar = sum((m.series.closing(ym) or 0.0) - (m.series.closing(_prev(ym)) or (0.0 if ym == ledger.months[0]
                                                                                else 0.0))
                 for m in receivables) if _prev(ym) in ledger.months else None
        bank = sum(l.amount for st in statements for l in st.lines if (l.day.year, l.day.month) == ym
                   and l.amount > 0 and not re.search(r"transf", l.text, re.I))
        if ar is None or not bank:
            continue
        expected = round(rev * (1 + VAT) - ar, 2)
        receipts.append({"month": ym, "revenue": round(rev, 2), "vat": round(rev * VAT, 2), "change_ar": round(ar, 2),
                         "expected": expected, "bank": round(bank, 2), "difference": round(bank - expected, 2)})
    # supplier listings against the ledger
    payables = [m for m in maps if m.key == "forn"]
    suppliers = []
    for li in listings:
        led = -sum(m.series.closing(li["ym"]) or 0.0 for m in payables)
        suppliers.append({"year": li["ym"][0], "date": li["ym"], "listing": li["total"], "ledger": round(led, 2),
                          "difference": round(li["total"] - led, 2), "source": li["source"]})
    return Proof(months, differences, receipts, suppliers, notes)


def read_listing(name: str, content: bytes) -> dict | None:
    """A supplier balances listing (supplier, open balance, a total): its total and date."""
    if not name.lower().endswith((".xlsx", ".xlsm")):
        return None
    ws = load_workbook(io.BytesIO(content), data_only=True, read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    title = " ".join(str(c) for r in rows[:4] for c in r if c)
    if not re.search(r"fornecedor|supplier|payable", norm(title)):
        return None
    head = next((i for i, r in enumerate(rows[:10]) if any(norm(c) in ("fornecedor", "supplier") for c in r)), None)
    if head is None:
        return None
    total_row = next((i for i, r in enumerate(rows) if r and norm(r[0]) in ("total", "total geral")), None)
    amounts = [(i, number(r[1])) for i, r in enumerate(rows[head + 1:], head + 1) if r and len(r) > 1
               and number(r[1]) is not None and (total_row is None or i < total_row)]
    total = number(rows[total_row][1]) if total_row is not None else sum(a for _, a in amounts)
    ym = month_of(title) or month_of(name)
    if ym is None:
        return None
    parts = round(sum(a for _, a in amounts), 2)
    return {"ym": ym, "total": round(total, 2), "lines": len(amounts), "parts_add_up": abs(parts - total) <= TRIVIAL,
            "source": f"{name} › row {total_row + 1 if total_row is not None else '?'}"}
