"""A messy data room, FICTITIOUS (synthetic test data), built from a fictitious company's annual accounts.

What a seller really sends, before anyone has tidied it:
  - annual trial balances 2023-2025 with the company's own chart of accounts (ERP codes, abbreviated names);
  - 36 monthly ERP exports in three formats: 2023 CSV with ';' and 1.234,56 and 31.01.2023, a title above the header;
    2024 CSV with ',' and (1,234.56) and 'jan-24'; 2025 Excel with the header on row 5 and two columns whose names are
    swapped ('Saldo' holds the movement, 'Movimento' the closing balance); the customer account renamed (new code)
    from July 2024; the August 2024 export missing;
  - statements of two banks: one in CSV, one in a text PDF;
  - the supplier balances listing at each year-end;
  - and, as before, the annual accounts, sales by customer, management EBITDA adjustments, debt schedule and report.
Every figure ties to the annual accounts: the monthly ledger is split from them, so the year-ends equal them to the
cent. Every file and every sheet says FICTITIOUS.

The Duriva room also carries three distortions, as a seller's ledger might. They are written here because the
generator has to plant them; the answer key (what, where, how much) is written OUTSIDE the project folder, so the
engine and its tests never read it from the project:  python scripts\\duriva_messy.py
"""
from __future__ import annotations

import csv
import io
import json
import math
import random
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dd_assistant.dataroom import files_in, read_data_room  # noqa: E402
from duriva_folder import write_pdf  # noqa: E402

LABEL = "FICTITIOUS, synthetic test data"
KEY_OUTSIDE = ROOT.parent / "Duriva_messy_gabarito.json"      # the answer key: outside the project, never read by it
VAT = 0.23
MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MONTHS_EN = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
SEASON = [0.074, 0.076, 0.085, 0.080, 0.086, 0.090, 0.083, 0.062, 0.085, 0.090, 0.088, 0.101]   # revenue profile


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    key: str            # model line it belongs to (the engine must find it on its own)
    share: float = 1.0  # share of the line (the last account of a line takes the remainder)


# The company's own chart of accounts: ERP codes, abbreviated Portuguese names. Two codes look like the national
# chart (6 digits); the customer account is renamed in July 2024.
PL = [Account("REV100", "Vendas merc. nac.", "vendas", 0.62), Account("REV110", "Vendas merc. grossistas", "vendas"),
      Account("CST200", "CMVMC", "cmv"),
      Account("CST300", "FSE - rendas e alugueres", "fse", 0.35), Account("CST310", "FSE - transportes merc.", "fse", 0.30),
      Account("622100", "Trab. especializ.", "fse"),
      Account("HR400", "Remuner. pessoal", "pess", 0.78), Account("HR410", "Encargos s/ remuner.", "pess"),
      Account("OIN500", "Out. rendim. operac.", "orend"), Account("OIN520", "Mais-val. alien. AFT", "orend"),
      Account("IMP600", "Imparid. clientes", "imp"),
      Account("OGS650", "Out. gastos operac.", "ogast", 0.7), Account("MSC990", "Diversos", "ogast"),
      Account("DEP700", "Amortiz. exerc.", "da"), Account("FIN800", "Juros supor. financ.", "juros"),
      Account("TAX900", "IRC estimado", "irc")]
BS = [Account("FA100", "Equip. básico e transp.", "aft"), Account("FA190", "Amort. acum. AFT", "aft"),
      Account("STK200", "Mercadorias", "inv"), Account("4120", "Clientes c/c", "cli"),
      Account("OAC300", "Out. devedores", "oac", 0.6), Account("OAC310", "Diferim. ativos", "oac"),
      Account("BNK001", "DO Banco Meridiano 4512", "caixa"), Account("BNK002", "DO Banco Norte 7733", "caixa"),
      Account("CX001", "Caixa", "caixa"),
      Account("EQ400", "Capital social", "cp"), Account("EQ410", "Reservas legais", "cp"),
      Account("EQ420", "Result. transitados", "cp"),
      Account("LN500", "Emprést. banc. MLP", "fin_lp"), Account("LN510", "Emprést. banc. CP", "fin_cp", 0.7),
      Account("LN520", "Conta caucionada", "fin_cp"), Account("221100", "Forn. c/c", "forn"),
      Account("OPC600", "Estado - IVA a pagar", "opc", 0.45), Account("OPC610", "Out. credores", "opc", 0.25),
      Account("OPC620", "Acrésc. gastos", "opc"), Account("SUS999", "Conta transit.", "")]
RENAMED = ("4120", "4121", "Clientes c/c nacionais", (2024, 7))   # old code, new code, new name, from (year, month)
MISSING = (2024, 8)                                                # this month's export is not in the data room
ASSETS = ("aft", "oanc", "inv", "cli", "oac", "caixa")
# planted in the Duriva room only: (bank account or 'AP', year, month, amount in euros)
PLANTED = {"receipt_not_in_bank": ("BNK001", 2025, 9, 258_000.00),
           "transfer_counted_twice": ("BNK002", 2025, 11, 232_000.00),
           "supplier_listing_short": ("AP", 2025, 12, 227_000.00)}


def cents(x: float) -> int:
    return int(round(x * 100))


def split(total: int, shares: list[float]) -> list[int]:
    """Integer cents split by shares, the last one taking the remainder (exact sum)."""
    out = [int(round(total * s)) for s in shares[:-1]]
    return out + [total - sum(out)]


class Book:
    """The monthly ledger: closing balance of each account at each month-end, debit positive, in cents."""

    def __init__(self, d, seed: int):
        self.d, self.rng = d, random.Random(seed)
        self.years = d.pl_years                          # 2023-2025
        self.months = [(y, m) for y in self.years for m in range(1, 13)]
        self.close: dict[str, dict[tuple[int, int], int]] = {}
        self.opening: dict[str, int] = {}                # balance at the year-end before the first month (BS only)
        self._pl()
        self._bs()

    def v(self, key, y) -> float:
        return self.d.v(key, y) or 0.0

    def _pl(self):
        d = self.d
        for y in self.years:
            gain = cents(-(d.v("ganho_alien", y) or 0) * 1000)          # a disposal gain sits in other income
            for key in {a.key for a in PL}:
                accts = [a for a in PL if a.key == key]
                total = cents(-self.v(key, y) * 1000)                    # P&L: credit negative, debit positive
                if key == "orend":
                    parts = [total + gain, -gain]
                else:
                    parts = split(total, [a.share for a in accts])
                for a, amount in zip(accts, parts):
                    profile = SEASON if key in ("vendas", "cmv") or a.code == "CST310" else [1 / 12] * 12
                    if a.code == "OIN520":
                        profile = [0] * 5 + [1] + [0] * 6                # the disposal, in June
                    if key == "imp":
                        profile = [0] * 11 + [1]                         # impairment booked at year-end
                    cum = 0.0
                    for m in range(1, 13):
                        cum += profile[m - 1]
                        self.close.setdefault(a.code, {})[(y, m)] = int(round(amount * min(cum / sum(profile), 1.0)))

    def _path(self, start: int, end: int, amp: float, phase: float) -> list[int]:
        out = []
        for m in range(1, 13):
            wave = math.sin(math.pi * m / 12 * 2 + phase) * (1 if m < 12 else 0)
            out.append(int(round(start + (end - start) * m / 12 + amp * wave)))
        out[-1] = end
        return out

    def _bs(self):
        d, ys = self.d, self.years
        first = ys[0] - 1
        year_end: dict[str, dict[int, int]] = {}
        acc = {first: 1_800_000_00}
        for y in ys:
            acc[y] = acc[y - 1] + cents(abs(self.v("da", y)) * 1000) - (40_000_00 if self.v("alien", y) else 0)
        for y in [first] + ys:
            for key in {a.key for a in BS if a.key and a.key not in ("caixa", "cp", "aft")}:
                accts = [a for a in BS if a.key == key]
                total = cents(self.v(key, y) * 1000) * (1 if key in ASSETS else -1)
                for a, amount in zip(accts, split(total, [a.share for a in accts])):
                    year_end.setdefault(a.code, {})[y] = amount
            year_end.setdefault("FA190", {})[y] = -acc[y]
            year_end.setdefault("FA100", {})[y] = cents(self.v("aft", y) * 1000) + acc[y]
            year_end.setdefault("SUS999", {})[y] = 0
        # equity before this year's result: capital and legal reserve fixed, retained earnings take the rest; the
        # dividend of each year is paid in May
        for code, fixed in (("EQ400", -1_000_000_00), ("EQ410", -200_000_00)):
            self.opening[code] = fixed
            for ym in self.months:
                self.close.setdefault(code, {})[ym] = fixed
        self.opening["EQ420"] = -cents(self.v("cp", first) * 1000) + 1_200_000_00
        for y in ys:
            start = -cents(self.v("cp", y - 1) * 1000) + 1_200_000_00
            end = -cents((self.v("cp", y) - self.v("rl_dre", y)) * 1000) + 1_200_000_00
            for m in range(1, 13):
                self.close.setdefault("EQ420", {})[(y, m)] = start if m < 5 else end
        amp = {"4120": 0.03, "STK200": 0.02, "221100": 0.03, "LN520": 0.10, "OPC600": 0.10}
        for code, ends in year_end.items():
            self.opening[code] = ends[first]
            for y in ys:
                a = amp.get(code, 0.01)
                path = self._path(ends[y - 1], ends[y], abs(ends[y]) * a, self.rng.uniform(0, 2 * math.pi))
                if code == "SUS999":
                    path = [0] * 12
                for m, value in enumerate(path, 1):
                    self.close.setdefault(code, {})[(y, m)] = value
        # cash is what makes each month's trial balance balance (all balances sum to zero); petty cash fixed. When
        # cash would fall below a working minimum mid-year, the overdraft line (LN520) is drawn instead (year-ends
        # are never touched: they are the annual accounts)
        others = dict(self.close)
        for ym in self.months:
            total = -sum(c[ym] for code, c in others.items())
            floor = 700_000_00 if ym >= (self.years[-1], 9) else 250_000_00
            if ym[1] != 12 and total < floor:
                self.close["LN520"][ym] -= floor - total
                total = floor
            petty = 2_500_00
            bank1 = int(round((total - petty) * 0.55))
            self.close.setdefault("CX001", {})[ym] = petty
            self.close.setdefault("BNK001", {})[ym] = bank1
            self.close.setdefault("BNK002", {})[ym] = total - petty - bank1
        cash0 = cents(self.v("caixa", first) * 1000)
        self.opening["CX001"] = 2_500_00
        self.opening["BNK001"] = int(round((cash0 - 2_500_00) * 0.55))
        self.opening["BNK002"] = cash0 - 2_500_00 - self.opening["BNK001"]

    def code(self, a: Account, y: int, m: int) -> tuple[str, str]:
        old, new, name, start = RENAMED
        if a.code == old and (y, m) >= start:
            return new, name
        return a.code, a.name

    def prev(self, code: str, y: int, m: int) -> int:
        if m == 1:
            if any(a.code == code for a in PL):
                return 0
            return self.close[code][(y - 1, 12)] if (y - 1, 12) in self.close[code] else self.opening[code]
        return self.close[code][(y, m - 1)]


def fmt_pt(c: int) -> str:
    """1.234,56 and -1.234,56"""
    s = f"{abs(c) / 100:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return ("-" if c < 0 else "") + s


def fmt_en(c: int) -> str:
    """1,234.56 and (1,234.56)"""
    s = f"{abs(c) / 100:,.2f}"
    return f"({s})" if c < 0 else s


def write_exports(book: Book, folder: Path, company: str) -> None:
    out = folder / "ERP - exportações mensais"
    out.mkdir(parents=True, exist_ok=True)
    accounts = PL + BS
    for y, m in book.months:
        if (y, m) == MISSING:
            continue
        rows = []
        for a in accounts:
            code, name = book.code(a, y, m)
            close = book.close[a.code][(y, m)]
            rows.append((code, name, close - book.prev(a.code, y, m), close))
        last = date(y, m, 28)
        while True:
            try:
                last = last.replace(day=last.day + 1)
            except ValueError:
                break
        if y == book.years[0]:            # CSV, ';', 1.234,56, title above the header, 31.01.2023
            buf = io.StringIO()
            w = csv.writer(buf, delimiter=";", lineterminator="\n")
            w.writerow([f"{LABEL} — {company} — ERP export"])
            w.writerow([f"Período: {last:%d.%m.%Y}"])
            w.writerow([])
            w.writerow(["Conta", "Descrição", "Movimento", "Saldo final"])
            for code, name, mov, close in rows:
                w.writerow([code, name, fmt_pt(mov), fmt_pt(close)])
            (out / f"balancete_{MONTHS_PT[m - 1]}{str(y)[2:]}.csv").write_text(buf.getvalue(), encoding="utf-8-sig")
        elif y == book.years[1]:          # CSV, ',', (1,234.56), a period column 'jan-24', Windows encoding
            buf = io.StringIO()
            w = csv.writer(buf, delimiter=",", lineterminator="\r\n")
            w.writerow(["Account", "Description", "Period", "Movement", "Closing balance", LABEL])
            for code, name, mov, close in rows:
                w.writerow([code, name, f"{MONTHS_EN[m - 1]}-{str(y)[2:]}", fmt_en(mov), fmt_en(close), ""])
            (out / f"ERP_TB_{y}{m:02d}.csv").write_bytes(buf.getvalue().encode("cp1252"))
        else:                             # Excel, header on row 5, 'Saldo' and 'Movimento' swapped by the ERP report
            wb = Workbook()
            ws = wb.active
            ws.title = f"{MONTHS_PT[m - 1].capitalize()}{y}"
            ws["A1"], ws["A2"], ws["A3"] = LABEL, f"{company} — Balancete do mês", f"Data: {last:%Y-%m-%d}"
            for c, h in enumerate(["Cód. conta", "Designação", "Mês", "Saldo", "Movimento"], 1):
                ws.cell(5, c, h)
            for r, (code, name, mov, close) in enumerate(rows, 6):
                ws.cell(r, 1, code)
                ws.cell(r, 2, name)
                ws.cell(r, 3, last)
                ws.cell(r, 4, mov / 100)      # the movement, under 'Saldo'
                ws.cell(r, 5, close / 100)    # the closing balance, under 'Movimento'
            wb.save(out / f"Balancete {y}-{m:02d}.xlsx")


def write_trial_balances(book: Book, folder: Path, company: str) -> None:
    out = folder / "Balancetes anuais"
    out.mkdir(parents=True, exist_ok=True)
    for y in book.years:
        wb = Workbook()
        ws = wb.active
        ws.title = f"Balancete {y}"
        ws["A1"], ws["A2"] = LABEL, f"{company} — Balancete geral a 31.12.{y} (antes do apuramento)"
        for c, h in enumerate(["Conta", "Descrição", "Saldo inicial", "Débito", "Crédito", "Saldo final"], 1):
            ws.cell(4, c, h)
        r = 5
        for a in PL + BS:
            code, name = book.code(a, y, 12)
            opening = 0 if a in PL else book.prev(a.code, y, 1)
            close = book.close[a.code][(y, 12)]
            mov = close - opening
            for c, v in enumerate([code, name, opening / 100, max(mov, 0) / 100, max(-mov, 0) / 100, close / 100], 1):
                ws.cell(r, c, v)
            r += 1
        wb.save(out / f"Balancete {y}.xlsx")


def bank_statements(book: Book, folder: Path, company: str, planted: bool, rng: random.Random) -> dict:
    """Two banks; each month opening + receipts - payments = closing. The statement balance is the ledger's, except
    where a distortion is planted (the ledger then shows more cash than the bank)."""
    out = folder / "Extratos bancários"
    out.mkdir(parents=True, exist_ok=True)
    offset = {"BNK001": 0, "BNK002": 0}
    lines = {"BNK001": [], "BNK002": []}
    customers = ["Cliente A", "Cliente B", "Cliente C", "Cliente D", "Outros clientes"]
    for (y, m) in book.months:
        rev = -sum(book.close[a.code][(y, m)] - book.prev(a.code, y, m) for a in PL if a.key == "vendas")
        ar = book.close["4120"][(y, m)] - book.prev("4120", y, m)
        receipts = int(round(rev * (1 + VAT))) - ar                       # customer receipts the ledger implies
        transfers = {"BNK001": 0, "BNK002": 0}
        moves = []
        if m % 3 == 0:
            moves.append(("BNK002", "BNK001", 50_000_00))
        if planted and (y, m) == PLANTED["transfer_counted_twice"][1:3]:
            moves.append(("BNK001", "BNK002", cents(PLANTED["transfer_counted_twice"][3])))
        for src, dst, amount in moves:
            transfers[src] -= amount
            transfers[dst] += amount
        if planted and (y, m) == PLANTED["receipt_not_in_bank"][1:3]:
            offset["BNK001"] += cents(PLANTED["receipt_not_in_bank"][3])
            receipts -= cents(PLANTED["receipt_not_in_bank"][3])
        if planted and (y, m) == PLANTED["transfer_counted_twice"][1:3]:
            offset["BNK002"] += cents(PLANTED["transfer_counted_twice"][3])
        opening = {b: book.prev(b, y, m) - (offset[b] if (y, m) > (2025, 9) else 0) for b in offset}
        # opening uses last month's offsets: recompute exactly from last month's statement closing
        opening = {b: lines[b][-1][4] if lines[b] else book.prev(b, y, m) for b in offset}
        closing = {b: book.close[b][(y, m)] - offset[b] for b in offset}
        payments_total = sum(opening[b] - closing[b] for b in offset) + receipts
        pay = {"BNK001": int(round(payments_total * 0.55))}
        pay["BNK002"] = payments_total - pay["BNK001"]
        rec = {b: pay[b] + closing[b] - opening[b] - transfers[b] for b in offset}
        if min(rec.values()) < 0 or min(pay.values()) < 0:
            shift = -min(rec.values()) + 10_000_00
            low = min(rec, key=rec.get)
            pay[low] += shift
            pay["BNK002" if low == "BNK001" else "BNK001"] -= shift
            rec = {b: pay[b] + closing[b] - opening[b] - transfers[b] for b in offset}
        assert min(rec.values()) >= 0 and min(pay.values()) >= 0 and min(closing.values()) > 0, (y, m, rec, pay, closing)
        for b in offset:
            balance = opening[b]
            day = 2
            entries = []
            for i, part in enumerate(split(rec[b], [0.3, 0.25, 0.2, 0.15, 0.1])):
                entries.append((day + 3 * i, f"Receb. {customers[i]} FT {y}/{rng.randint(100, 999)}", part))
            for src, dst, amount in moves:
                if b in (src, dst):
                    other = "Banco Norte" if b == "BNK001" else "Banco Meridiano"
                    entries.append((15, f"Transf. {'para' if b == src else 'de'} {other}", -amount if b == src else amount))
            kinds = [("Pag. fornecedores", 0.62), ("Processamento salários", 0.17), ("Seg. Social", 0.05),
                     ("AT - IVA e retenções", 0.10), ("Prestação empréstimo", 0.05), ("Comissões bancárias", 0.01)]
            for i, ((what, _), part) in enumerate(zip(kinds, split(pay[b], [s for _, s in kinds]))):
                entries.append((6 + 4 * i, what, -part))
            for d_, what, amount in sorted(entries, key=lambda e: e[0]):
                balance += amount
                lines[b].append((date(y, m, min(d_, 28)), what, amount, opening[b], balance))
            assert balance == closing[b], (b, y, m)
    for y in book.years:      # Banco Meridiano: CSV per year, ';' and 1.234,56
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";", lineterminator="\n")
        w.writerow([f"{LABEL} — Banco Meridiano — extrato da conta 4512 — {company}"])
        w.writerow(["Data", "Descritivo", "Débito", "Crédito", "Saldo"])
        for d_, what, amount, _, bal in lines["BNK001"]:
            if d_.year == y:
                w.writerow([f"{d_:%d/%m/%Y}", what, fmt_pt(-amount) if amount < 0 else "",
                            fmt_pt(amount) if amount > 0 else "", fmt_pt(bal)])
        (out / f"Extrato Banco Meridiano {y}.csv").write_text(buf.getvalue(), encoding="utf-8-sig")
    for y in book.years:      # Banco Norte: a text PDF per year
        rows = [(f"{LABEL}", True), (f"Banco Norte — Extrato de conta à ordem 7733 — {company} — {y}", True)]
        start = next(o for d_, _, _, o, _ in lines["BNK002"] if d_.year == y)
        rows.append((f"Saldo inicial: {fmt_pt(start)}", False))
        for d_, what, amount, _, bal in lines["BNK002"]:
            if d_.year == y:
                rows.append((f"{d_:%d-%m-%Y} | {what} | {fmt_pt(amount)} | {fmt_pt(bal)}", False))
        write_pdf(out / f"Extrato Banco Norte {y}.pdf", rows)
    return offset


def supplier_listings(book: Book, folder: Path, company: str, planted: bool) -> None:
    out = folder / "Fornecedores"
    out.mkdir(parents=True, exist_ok=True)
    for y in book.years[1:]:
        total = -book.close["221100"][(y, 12)]
        if planted and y == PLANTED["supplier_listing_short"][1]:
            total -= cents(PLANTED["supplier_listing_short"][3])
        names = [f"Fornecedor {chr(65 + i)}, Lda" for i in range(12)]
        wb = Workbook()
        ws = wb.active
        ws.title = f"Saldos {y}"
        ws["A1"], ws["A2"] = LABEL, f"{company} — Saldos de fornecedores a 31.12.{y} (mapa auxiliar)"
        ws.cell(4, 1, "Fornecedor")
        ws.cell(4, 2, "Saldo em aberto")
        for r, (n, part) in enumerate(zip(names, split(total, [0.18, 0.14, 0.12, 0.1, 0.09, 0.08, 0.07, 0.06, 0.05,
                                                                0.05, 0.03, 0.03])), 5):
            ws.cell(r, 1, n)
            ws.cell(r, 2, part / 100)
        ws.cell(r + 1, 1, "Total")
        ws.cell(r + 1, 2, total / 100)
        wb.save(out / f"Saldos fornecedores 31.12.{y}.xlsx")


def copy_annual(source: Path, folder: Path) -> None:
    """The annual accounts and schedules, as before, with the FICTITIOUS label on each sheet (a free cell to the right)."""
    out = folder / "Contas anuais e mapas"
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files_in([source]):
        target = out / name
        if name.lower().endswith(".xlsx"):
            wb = load_workbook(io.BytesIO(content))
            for ws in wb.worksheets:
                ws.cell(1, ws.max_column + 2, LABEL)
            wb.save(target)
        elif name.lower().endswith(".pdf"):
            shutil.copyfile(Path(source) / name if Path(source).is_dir() else source, target)
        else:
            target.write_bytes(content)


def build(source: Path, folder: Path, company: str, planted: bool, seed: int = 7) -> dict:
    ext = read_data_room(files_in([source]))
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    book = Book(ext.data, seed)
    write_exports(book, folder, company)
    write_trial_balances(book, folder, company)
    offset = bank_statements(book, folder, company, planted, random.Random(seed))
    supplier_listings(book, folder, company, planted)
    copy_annual(source, folder)
    (folder / "LEIA-ME — FICTITIOUS.txt").write_text(
        f"{LABEL}. {company} does not exist. This data room was generated by scripts/duriva_messy.py from the "
        "fictitious company's annual accounts, to test how the agent reads a messy data room: an own chart of "
        "accounts, monthly ERP exports in mixed formats, bank statements in CSV and PDF, supplier listings.\n",
        encoding="utf-8")
    return offset


def main() -> None:
    build(ROOT / "data" / "Duriva_data_room", ROOT / "data" / "Duriva_messy_data_room",
          "Duriva Distribuição Industrial, S.A.", planted=True)
    key = {"note": f"{LABEL}. Answer key of the messy Duriva data room: keep OUTSIDE the project folder.",
           "distortions": [{"what": what, "where": where, "year": y, "month": m, "amount_eur": amount}
                           for what, (where, y, m, amount) in PLANTED.items()]}
    KEY_OUTSIDE.write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"Data room: data/Duriva_messy_data_room · answer key written outside the project: {KEY_OUTSIDE}")


if __name__ == "__main__":
    main()
