"""Layer 1b — the notes to the accounts, and what they settle.

A screening of the three statements leaves questions the notes of the same report already answer: what is inside
other income, how the debt falls due, what the provisions are for. The key notes are transcribed as printed into a
workbook (one sheet per table, with the note number and the page), read here, and matched to the findings:

- `explained by note N`: the note was read and one of its figures ties to the statement line behind the finding;
- `partly explained`: a note on the subject was read, but nothing in it ties to that line;
- `open`: no note on the subject was read.

The explanation is one sentence built from the note's own figures (its largest components). Nothing is inferred:
a note that is missing or unreadable is 'not read', and the finding stays open.

Workbook format (scripts/notes_*.py write it): a sheet 'Index' (Sheet · Topic · Note · Title as printed · Page · Unit
· Status) and one sheet per table: A1 title, A2 source, A3 unit, row 5 header ('Item' and the columns as printed),
then one row per printed line; a row with text only is a sentence copied from the note.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

TOPICS = {"other_income": "other income", "other_expenses": "other expenses", "borrowings": "borrowings",
          "borrowings_maturity": "maturity of borrowings", "leases": "leases", "provisions": "provisions",
          "contingencies": "contingencies and guarantees", "related_parties": "related parties",
          "segments": "segments", "staff": "staff", "other_payables": "other payables",
          "other_financial": "other financial assets and liabilities", "depreciation": "depreciation"}
OPEN, PARTLY, EXPLAINED = "open", "partly explained", "explained"

# what answers each finding or net debt item: the topics to look in, and the statement lines a note figure must
# equal for the note to 'tie' (model keys; 'debt' = current + non-current borrowings)
FOR_RULE = {
    "R04": (("other_income",), ("orend",)),
    "R11": (("borrowings_maturity", "borrowings"), ("fin_cp", "debt")),
    "R20": (("borrowings_maturity", "borrowings"), ("debt", "fin_cp", "fin_lp")),
    "R21": (("borrowings", "borrowings_maturity"), ("debt", "fin_cp", "fin_lp")),
    "R22": (("borrowings", "borrowings_maturity"), ("debt", "fin_cp", "fin_lp")),
    "R24": (("depreciation",), ("da",)),
    "R27": (("depreciation",), ("da",)),
    "R28": (("other_payables", "other_financial"), ()),
}
FOR_ITEM = {"Lease liabilities": ("leases",), "Provisions": ("provisions",),
            "Other financial liabilities": ("other_financial",), "Other financial assets": ("other_financial",)}
# once the public report has answered the first question, the request goes one level down
NEXT_REQUEST = {
    "other_income": "Ledger of the largest components of other income named in the note; the contracts, grant "
                    "decisions or sale agreements behind them",
    "borrowings": "Facility agreements of the lines named in the note; covenant compliance certificates",
    "borrowings_maturity": "Facility agreements with the repayment schedules; renewal terms of the lines falling due",
    "leases": "Lease register by asset with terms, options and return conditions",
    "provisions": "Provision-by-provision file: nature, legal opinion, expected timing of the outflow",
    "other_payables": "Trial balance behind the components named in the note; ageing and counterparties",
    "other_financial": "Contracts behind the components named in the note (derivatives, grants, put options)",
    "depreciation": "Fixed asset register with useful lives; any change of estimate in the year",
}
_TOTAL = re.compile(r"total|\bsoma\b", re.I)
_THOUSANDS = re.compile(r"milhares|thousand|\bmiles\b|milliers|migliaia|tausend|\bk€|\bkeur", re.I)
_MILLIONS = re.compile(r"milh[oõ]es|million", re.I)
_RESIDUAL = re.compile(r"^(outros|outras|other|others|diversos|sundry)\b[^a-zA-Z]*$", re.I)


@dataclass
class NoteTable:
    sheet: str
    topic: str
    note: str                 # the note number, as printed
    title: str
    page: str                 # 'p.203' or 'note 30 (ESEF report, no page)'
    unit: str
    scale: float              # multiply a printed figure by this to get EUR thousands
    header: list[str] = field(default_factory=list)
    rows: list[tuple[str, list]] = field(default_factory=list)   # (label as printed, values as printed)
    texts: list[str] = field(default_factory=list)               # sentences copied from the note

    @property
    def locator(self) -> str:
        page = self.page if self.page.startswith("p") else ""
        return f"note {self.note}" + (f" ({page})" if page else "")

    @property
    def year(self) -> int | None:
        """The year a table belongs to when its columns are not years ('N20f Maturidade 2025')."""
        if any(re.search(r"(19|20)\d\d", h) for h in self.header):
            return None
        m = re.search(r"((?:19|20)\d\d)", self.sheet)
        return int(m.group(1)) if m else None

    def columns(self, year: int) -> list[int]:
        """The columns that give figures for a year: those whose header names it ('2025', 'Current 2025',
        '31/12/2025'), or every column when the whole table is that year's."""
        named = [i for i, h in enumerate(self.header) if re.search(rf"(?<!\d){year}(?!\d)", str(h))]
        if named:
            return named
        return list(range(len(self.header))) if self.year == year else []

    def column_values(self, col: int) -> list[tuple[str, float]]:
        """(label, EUR thousands) of each numeric line of one column."""
        return [(label, vals[col] * self.scale) for label, vals in self.rows
                if col < len(vals) and isinstance(vals[col], (int, float)) and not isinstance(vals[col], bool)]

    def series(self, year: int) -> list[tuple[str, list[tuple[str, float]]]]:
        """Every run of figures a table gives for a year, as (name, [(label, EUR thousands)]): one per year column,
        or, when the years are in the rows ('31 December 2025'), one per such row with the headers as labels."""
        cols = self.columns(year)
        if cols:
            return [(self.header[c], self.column_values(c)) for c in cols]
        out = []
        for label, vals in self.rows:
            if re.search(rf"(?<!\d){year}(?!\d)", label) and not re.search(r"1 (january|janeiro)|inicial", label, re.I):
                out.append((label, [(self.header[i], v * self.scale) for i, v in enumerate(vals)
                                    if isinstance(v, (int, float)) and i < len(self.header)]))
        return out

    def values(self, year: int) -> list[tuple[str, float]]:
        """(label, EUR thousands) of the first column of a year; empty when the table has no such column."""
        cols = self.columns(year)
        return self.column_values(cols[0]) if cols else []


def _scale(unit: str) -> float:
    return 1000.0 if _MILLIONS.search(unit or "") else 1.0 if _THOUSANDS.search(unit or "") else 0.001


def read_notes(source: str | Path | bytes) -> list[NoteTable]:
    """The tables of a notes workbook. A topic the transcriber could not read has no table: it is 'not read'."""
    wb = load_workbook(io.BytesIO(source) if isinstance(source, bytes) else source, data_only=True)
    out = []
    for row in wb["Index"].iter_rows(min_row=2, values_only=True):
        sheet, topic, note, title, page, unit, status = (list(row) + [None] * 7)[:7]
        if not sheet or sheet not in wb.sheetnames or not str(status or "").startswith("read"):
            continue
        ws = wb[sheet]
        unit = str(ws["A3"].value or unit or "")
        header = [str(c) if c is not None else "" for c in next(ws.iter_rows(min_row=5, max_row=5, values_only=True))][1:]
        t = NoteTable(sheet, str(topic), str(note), str(title or ws["A1"].value or ""), str(page or ""), unit,
                      _scale(unit), header)
        for r in ws.iter_rows(min_row=6, values_only=True):
            label, vals = r[0], list(r[1:])
            numeric = any(isinstance(v, (int, float)) for v in vals)
            if label is None and not numeric:
                continue
            label = "[Total]" if label is None else label     # a total printed without a label
            if numeric or any(v in ("-", "–") for v in vals):
                t.rows.append((str(label), vals))
            else:
                t.texts.append(str(label))
        out.append(t)
    return out


def not_read(source: str | Path | bytes) -> list[tuple[str, str]]:
    """(topic, reason) for the topics the transcriber could not find or read."""
    wb = load_workbook(io.BytesIO(source) if isinstance(source, bytes) else source, data_only=True)
    return [(str(r[1]), str(r[6])) for r in wb["Index"].iter_rows(min_row=2, values_only=True)
            if r[1] and not str(r[6] or "").startswith("read")]


# ---------------------------------------------------------------- what a note settles
@dataclass
class Evidence:
    state: str = OPEN             # open · partly explained · explained
    note: str = ""                # 'note 30' or 'note 25 (p.214)'
    text: str = ""                # one sentence with the note's own figures
    request: str = ""             # the next-level request, when the note answered the first one

    @property
    def label(self) -> str:
        return f"{self.state} by {self.note}" if self.note else self.state


def _components(rows: list[tuple[str, float]], tied: float | None) -> list[tuple[str, float]]:
    """The lines of a column, largest first, without totals (by label, or the line that tied)."""
    out, seen = [], set()
    for label, v in rows:
        if _TOTAL.search(label) or (tied is not None and abs(v - tied) <= 1.0) or label in seen or not v:
            continue
        seen.add(label)        # a label printed twice (current and non-current) is listed once, its first figure
        out.append((label, v))
    return sorted(out, key=lambda r: -abs(r[1]))


def explain(notes: list[NoteTable], topics: tuple[str, ...], targets: list, year: int, money, what: str) -> Evidence:
    """Look for the topics in order. A table 'ties' when one of its figures for the year equals a target (±€1k).
    targets: figures, or (name of the statement line, figure). Tables with year columns are tried first."""
    tables = [t for topic in topics for t in notes if t.topic == topic]
    if not tables:
        return Evidence()
    tables = sorted(tables, key=lambda t: (topics.index(t.topic), t.year is not None))
    named = [x if isinstance(x, tuple) else ("", x) for x in targets if x is not None]
    tied = None                                   # (table, name of the series, its figures, value, statement line)
    for t in tables:
        for name, figures in t.series(year):
            for _, v in figures:
                hit = next(((n, x) for n, x in named if x and abs(abs(v) - abs(x)) <= 1.0), None)
                if hit:
                    tied = (t, name, figures, v, hit[0])
                    break
            if tied:
                break
        if tied:
            break
    fy = f"FY{str(year)[2:]}"
    if tied:
        t, name, figures, value, line = tied
        parts = _components(figures, value)[:3]
    else:
        t = next((x for x in tables if x.columns(year) and x.year is None), None)
        parts = _components(t.values(year), None)[:3] if t else []
        t = t or tables[0]
        name = ""
    listing = ", ".join(f"{label.strip()} {money.fmt(v)}" for label, v in parts)
    topic = TOPICS.get(t.topic, t.topic)
    where = t.locator[0].upper() + t.locator[1:]
    series = f", '{name}'" if name and not re.fullmatch(r"\D*(19|20)\d\d\D*", name) else ""
    if tied:
        to = f"the line '{line}' of the statements" if line else "the statements"
        text = (f"{where} gives the {topic} of {fy} and ties to {to} ({money.fmt(value)}{series})"
                + (f"; the largest lines are {listing}" if parts else "") + ".")
        if parts and _RESIDUAL.match(parts[0][0].strip()):   # the largest line is itself an unexplained 'other'
            return Evidence(PARTLY, t.locator, text + " The largest line is a residual the note does not break down.",
                            NEXT_REQUEST.get(t.topic, ""))
        return Evidence(EXPLAINED, t.locator, text, NEXT_REQUEST.get(t.topic, ""))
    text = (f"{where} covers {topic}, but no figure in it equals the {what} of the statements"
            + (f"; its largest {fy} lines are {listing}" if parts else "") + ".")
    return Evidence(PARTLY, t.locator, text, "")


def _targets(keys: tuple[str, ...], d, m, year: int) -> list[float]:
    out = []
    for k in keys:
        out.append(m["debt"].get(year) if k == "debt" else d.v(k, year))
    return [x for x in out if x is not None]


def for_finding(rule_id: str, year: int | None, notes: list[NoteTable], d, m, money, raw: list | None = None) -> Evidence:
    """raw: (label, figure) of the balance sheet lines the model does not use, for the findings about 'other'
    lines: a note that breaks one of them down ties to it."""
    spec = FOR_RULE.get(rule_id)
    if not spec or not notes or year is None:
        return Evidence()
    topics, keys = spec
    targets = _targets(keys, d, m, year) if keys else [x for x in (raw or []) if abs(x[1]) >= 1000]
    return explain(notes, topics, targets, year, money, "line")


def for_item(category: str, amounts: list[float], year: int | None, notes: list[NoteTable], money) -> Evidence:
    """amounts: the balance of the item and of each balance sheet line inside it (current, non-current)."""
    topics = FOR_ITEM.get(category)
    if not topics or not notes or year is None:
        return Evidence()
    return explain(notes, topics, [x for x in amounts if x], year, money, "balance")


def as_text(notes: list[NoteTable]) -> str:
    """The notes as text for the memo material: every table with its locator, in the unit printed."""
    out = []
    for t in notes:
        out += [f"### Note sheet '{t.sheet}' — {t.title} ({t.locator}; topic: {TOPICS.get(t.topic, t.topic)}; "
                f"unit as printed: {t.unit})",
                "| Item | " + " | ".join(t.header) + " |", "| --- | " + " | ".join("---" for _ in t.header) + " |"]
        out += ["| " + label + " | " + " | ".join("" if v is None else str(v) for v in vals) + " |"
                for label, vals in t.rows]
        out += [f"- {s}" for s in t.texts] + [""]
    return "\n".join(out)
