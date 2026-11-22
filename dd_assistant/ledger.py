"""Layer 1e — the general ledger of a messy data room: monthly ERP exports and annual trial balances, as sent.

A seller's ERP exports are not tidy: CSV with ';' or ',', decimal commas or brackets for negatives, the header a few
rows down, dates as 31.01.2024, 'jan-24' or an Excel date, columns whose names do not say what is in them, an account
renamed half-way, a month missing. This module turns them into one ledger:
  - every account, every month-end: the closing balance (debit positive, euros) and the month's movement, each with
    its file and row;
  - the columns are told apart by their content when the names are unreliable: the closing balance is the column
    that continues last month's closing (closing − movement = last month's closing);
  - an account that disappears when another appears, with the new one opening exactly at the old one's closing, is
    the same account renamed: one series, with both codes;
  - a missing month is rebuilt from the next one (its closing less its movement), marked as derived;
  - the annual trial balances are read too and tied to the December exports.
Everything that was normalised is listed in `notes`, so the reviewer sees what the agent assumed.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import PurePath

from openpyxl import load_workbook

MONTHS = {m: i for i, names in enumerate([("jan", "janeiro", "january"), ("fev", "feb", "fevereiro", "february"),
                                          ("mar", "marco", "march"), ("abr", "apr", "abril", "april"),
                                          ("mai", "may", "maio"), ("jun", "junho", "june"),
                                          ("jul", "julho", "july"), ("ago", "aug", "agosto", "august"),
                                          ("set", "sep", "setembro", "september"), ("out", "oct", "outubro", "october"),
                                          ("nov", "novembro", "november"), ("dez", "dec", "dezembro", "december")], 1)
          for m in names}
CODE = ("conta", "account", "cod conta", "codigo", "cod", "code", "account code")
NAME = ("descricao", "description", "designacao", "nome", "name")
MOVEMENT = ("movimento", "movement", "movimento do mes", "mov periodo", "net movement")
CLOSING = ("saldo final", "closing balance", "saldo", "closing", "balance")
TB_OPENING = ("saldo inicial", "opening balance", "opening")


def norm(text) -> str:
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def number(text) -> float | None:
    """'1.234,56', '-1.234,56', '(1,234.56)', '1,234.56', 1234.56 -> float (euros); '' -> None."""
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text or "").strip().replace("€", "").replace(" ", "").replace(" ", "")
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")") or s.startswith("-")
    s = s.strip("()-")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.rsplit(",", 1)[1]) != 3 else s.replace(",", "")
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if neg else value


def month_of(value) -> tuple[int, int] | None:
    """31.01.2024, 31/01/2024, 2024-01-31, 'jan-24', 'Janeiro 2024', a date -> (2024, 1)."""
    if isinstance(value, (datetime, date)):
        return value.year, value.month
    s = norm(value)
    if m := re.search(r"\b(\d{1,2}) (\d{1,2}) (\d{4})\b", s):
        return int(m.group(3)), int(m.group(2))
    if m := re.search(r"\b(\d{4}) (\d{1,2}) (\d{1,2})\b", s):
        return int(m.group(1)), int(m.group(2))
    if m := re.search(r"\b([a-z]+) (\d{2}|\d{4})\b", s):
        if m.group(1) in MONTHS:
            y = int(m.group(2))
            return (y + 2000 if y < 100 else y), MONTHS[m.group(1)]
    return None


def _is(header: str, names) -> bool:
    return norm(header) in names


@dataclass
class Point:
    closing: float
    movement: float | None
    source: str
    derived: str = ""            # why the figure was rebuilt, when it was not read


@dataclass
class Series:
    """One account over time (several codes when it was renamed)."""
    codes: list[str]
    names: list[str]
    points: dict[tuple[int, int], Point] = field(default_factory=dict)

    @property
    def code(self) -> str:
        return " → ".join(self.codes)

    @property
    def name(self) -> str:
        return self.names[-1]

    def closing(self, ym) -> float | None:
        p = self.points.get(ym)
        return p.closing if p else None


@dataclass
class Ledger:
    series: list[Series]
    months: list[tuple[int, int]]
    tb: dict[int, dict[str, tuple[float, float, str]]]     # year -> code -> (opening, closing, source)
    notes: list[str] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)       # each file and how it was read

    def by_code(self, code: str) -> Series | None:
        return next((s for s in self.series if code in s.codes), None)


# ---------------------------------------------------------------- reading one export
def _rows_of(name: str, content: bytes) -> tuple[list[list], str]:
    """The rows of a CSV or an Excel sheet, and how they were read."""
    low = name.lower()
    if low.endswith((".xlsx", ".xlsm")):
        wb = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
        ws = wb.worksheets[0]
        return [list(r) for r in ws.iter_rows(values_only=True)], f"Excel (sheet '{ws.title}')"
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = "\n".join(text.splitlines()[:12])
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    return list(csv.reader(io.StringIO(text), delimiter=delimiter)), f"CSV ('{delimiter}', {enc})"


def _header(rows: list[list]) -> int | None:
    for i, row in enumerate(rows[:15]):
        cells = [norm(c) for c in row]
        if any(c in CODE for c in cells) and any(c in NAME for c in cells):
            return i
    return None


@dataclass
class _Export:
    name: str
    how: str
    month: tuple[int, int]
    lines: list[tuple[str, str, float | None, float | None, int]]   # code, name, a, b, row number
    cols: tuple[str, str]                                           # header of a and b
    trial_balance: bool = False
    opening: dict[str, float] = field(default_factory=dict)


def read_export(name: str, content: bytes) -> _Export | None:
    """A monthly ERP export or an annual trial balance; None when the file is not one."""
    rows, how = _rows_of(name, content)
    h = _header(rows)
    if h is None:
        return None
    header = [norm(c) for c in rows[h]]
    col = lambda names: next((i for i, c in enumerate(header) if c in names), None)
    code_c, name_c = col(CODE), col(NAME)
    open_c = col(TB_OPENING)
    trial = open_c is not None and "debito" in header
    if trial:
        a_c, b_c = None, header.index("saldo final")
    else:
        numeric = [i for i, c in enumerate(header) if c in MOVEMENT + CLOSING]
        if len(numeric) < 2:
            return None
        a_c, b_c = numeric[0], numeric[1]
    # the month: a period column, else a date above the header, else the file name
    period_c = next((i for i, c in enumerate(header) if c in ("period", "periodo", "mes", "month", "data", "date")),
                    None)
    month = None
    if period_c is not None and len(rows) > h + 1:
        month = month_of(rows[h + 1][period_c])
    for row in rows[:h]:
        month = month or next((m for c in row if c and (m := month_of(c))), None)
    month = month or month_of(re.sub(r"[_\-]", " ", PurePath(name).stem)) or _month_in_name(name)
    if month is None:
        return None
    lines = []
    for i, row in enumerate(rows[h + 1:], h + 2):
        if code_c >= len(row) or not str(row[code_c] or "").strip():
            continue
        code = str(row[code_c]).strip()
        a = number(row[a_c]) if a_c is not None else None
        b = number(row[b_c]) if b_c < len(row) else None
        lines.append((code, str(row[name_c] or "").strip(), a, b, i))
    exp = _Export(name, how, month, lines, (rows[h][a_c] if a_c is not None else "", rows[h][b_c]), trial)
    if trial:
        exp.opening = {code: number(rows[i - 1][open_c]) or 0.0 for code, _, _, _, i in lines}
    return exp


def _month_in_name(name: str) -> tuple[int, int] | None:
    stem = PurePath(name).stem.lower()
    if m := re.search(r"(20\d\d)[-_ ]?(\d\d)\b", stem):
        return int(m.group(1)), int(m.group(2))
    if m := re.search(r"([a-z]{3})(\d{2})\b", stem):
        if m.group(1) in MONTHS:
            return 2000 + int(m.group(2)), MONTHS[m.group(1)]
    if m := re.search(r"(20\d\d)", stem):
        return int(m.group(1)), 12
    return None


def _source(exp: _Export, row: int) -> str:
    return f"{exp.name} › row {row}"


# ---------------------------------------------------------------- the whole ledger
def read_ledger(files: list[tuple[str, bytes]]) -> Ledger:
    exports, tbs, notes, table = [], [], [], []
    for name, content in files:
        exp = read_export(name, content)
        if exp is None:
            continue
        (tbs if exp.trial_balance else exports).append(exp)
        table.append({"File": name, "Read as": f"{'Trial balance' if exp.trial_balance else 'Monthly export'}, "
                                               f"{exp.how}", "Period": f"{exp.month[0]}-{exp.month[1]:02d}"})
    exports.sort(key=lambda e: e.month)
    series: dict[str, Series] = {}
    last_closing: dict[str, float] = {}
    for exp in exports:
        movement_first = _which_is_movement(exp, last_closing, notes)
        seen = set()
        for code, name, a, b, row in exp.lines:
            movement, closing = (a, b) if movement_first else (b, a)
            s = series.get(code)
            if s is None:
                s = series[code] = Series([code], [name])
            elif name and name != s.names[-1]:
                s.names.append(name)
            s.points[exp.month] = Point(round(closing or 0.0, 2), None if movement is None else round(movement, 2),
                                        _source(exp, row))
            last_closing[code] = closing or 0.0
            seen.add(code)
    swapped = [n.split("|") for n in notes if n.startswith("SWAPPED|")]
    notes[:] = [n for n in notes if not n.startswith("SWAPPED|")]
    if swapped:
        notes.append(f"{len(swapped)} export(s) ({swapped[0][1]} … {swapped[-1][1]}) name the columns '{swapped[0][2]}' "
                     f"and '{swapped[0][3]}' the wrong way round: read by content (the closing balance is the column "
                     f"that continues last month's closing; e.g. {swapped[-1][4]} of {swapped[-1][5]} accounts).")
    months = sorted({e.month for e in exports})
    full = _all_months(months)
    _link_renamed(series, full, notes)
    _fill_missing(series, full, notes)
    tb = {exp.month[0]: {code: (exp.opening.get(code, 0.0), b or 0.0, _source(exp, row))
                         for code, _, _, b, row in exp.lines} for exp in tbs}
    _tie_trial_balances(series, tb, notes)
    return Ledger(sorted(series.values(), key=lambda s: s.codes[0]), full, tb, notes, table)


def _all_months(months):
    if not months:
        return []
    out, (y, m) = [], months[0]
    while (y, m) <= months[-1]:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _prev(ym):
    y, m = ym
    return (y - 1, 12) if m == 1 else (y, m - 1)


def _which_is_movement(exp: _Export, last: dict[str, float], notes: list[str]) -> bool:
    """True when the first numeric column is the movement. Decided by content: the closing balance continues last
    month's closing (closing − movement = last closing). In January the profit and loss accounts start again, so
    only balance sheet accounts (a non-zero last closing that is not reset) are used; without a previous month the
    header names decide."""
    first, second = (norm(c) for c in exp.cols)
    by_name = first in MOVEMENT and second in CLOSING
    tests = [(a, b, last[code]) for code, _, a, b, _ in exp.lines if code in last and a is not None and b is not None]
    if not tests:
        return by_name
    as_named = sum(abs((b - a) - prev) < 0.01 for a, b, prev in tests)
    swapped = sum(abs((a - b) - prev) < 0.01 for a, b, prev in tests)
    movement_first = as_named >= swapped
    if movement_first != by_name:
        notes.append(f"SWAPPED|{exp.name}|{exp.cols[0]}|{exp.cols[1]}|{max(as_named, swapped)}|{len(tests)}")
    return movement_first


def _link_renamed(series: dict[str, Series], months, notes: list[str]) -> None:
    """An account that stops when another starts, the new one opening at the old one's closing: one series."""
    for new in list(series.values()):
        start = min(new.points)
        if start == months[0]:
            continue
        p = new.points[start]
        opening = p.closing - (p.movement or 0.0)
        for old in list(series.values()):
            if old is new or max(old.points) >= start or abs(old.closing(_prev(start)) or 0.0) < 0.01:
                continue
            gap = [ym for ym in months if max(old.points) < ym < start]
            if abs((old.closing(_prev(start)) or 0.0) - opening) < 0.01 and len(gap) <= 1:
                old.points.update(new.points)
                old.codes += new.codes
                old.names += [n for n in new.names if n not in old.names]
                del series[new.codes[0]]
                notes.append(f"Account {old.codes[0]} '{old.names[0]}' continues as {new.codes[0]} '{new.names[0]}' "
                             f"from {start[0]}-{start[1]:02d}: the new account opens at the old one's closing "
                             f"({opening:,.2f}). One series.")
                break


def _fill_missing(series: dict[str, Series], months, notes: list[str]) -> None:
    """A month without an export: closing = next month's closing − next month's movement (exact), marked derived."""
    for ym in months:
        missing = [s for s in series.values() if ym not in s.points and min(s.points) < ym < max(s.points)]
        if not missing:
            continue
        nxt = months[months.index(ym) + 1]
        for s in missing:
            p = s.points.get(nxt)
            if p is None or p.movement is None:
                continue
            closing = round(p.closing - p.movement, 2) if not (nxt[1] == 1) else 0.0
            s.points[ym] = Point(closing, None, f"derived from {p.source}",
                                 f"no export for {ym[0]}-{ym[1]:02d}: closing of {nxt[0]}-{nxt[1]:02d} less its movement")
            prev = s.points.get(_prev(ym))
            if prev is not None:
                s.points[ym].movement = round(closing - (prev.closing if ym[1] != 1 else 0.0), 2)
        notes.append(f"No export for {ym[0]}-{ym[1]:02d}: every balance rebuilt from {nxt[0]}-{nxt[1]:02d} (closing "
                     "less the month's movement), marked as derived.")


def _tie_trial_balances(series: dict[str, Series], tb, notes: list[str]) -> None:
    for year, accounts in sorted(tb.items()):
        off = []
        for code, (_, closing, _) in accounts.items():
            s = series.get(code) or next((x for x in series.values() if code in x.codes), None)
            dec = s.closing((year, 12)) if s else None
            if dec is None or abs(dec - closing) > 0.01:
                off.append(code)
        notes.append(f"Trial balance {year}: {len(accounts) - len(off)} of {len(accounts)} accounts equal the December "
                     "export" + (f"; different: {', '.join(off)}" if off else "") + ".")
