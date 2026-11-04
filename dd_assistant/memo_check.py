"""Check of the AI memo (deterministic, no AI).

Automatically confirms part of the checklist in docs/ai_memo_prompt.md:
  - every figure in the memo exists in the material sent to the AI, or is a rounding of one, for the period
    cited next to it ('€27,739k in FY24' fails when that is the FY23 value);
  - every finding appears in the memo;
  - there is no investment recommendation and no view on price;
  - every question for management has a request in the request list (warning);
  - sentences longer than 25 words (warning).
Errors = the memo breaks a rule of the prompt. Warnings = for a person to review.
Limitation: a small invented figure (e.g. 37%) can match another figure by chance; large
figures (amounts in €k) are checked reliably.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

MAX_WORDS = 25

# Figures in the memo; skips those inside R01, §4, DRE!D5, B5:D5, FY25, 31/12/2025 or 1.º.
# Accepts 1,415 · 1.415 · 1 415 · 23.8 · 23,8 and unit suffixes such as €1,415k, 2.65x, 3.5pp.
_NUM = re.compile(r"(?<![\w§/!:.,–-])"
                  r"([-−]?\d{1,3}(?:[.,   ]\d{3})+(?:[.,]\d+)?"
                  r"|[-−]?\d+(?:[.,]\d+)?)"
                  r"(?:(?![\w/])|(?=(?:k|m|bn|x|pp)\b))")
_MATERIAL_NUM = re.compile(r"-?\d+(?:[.,]\d+)*")
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s")
_RECOMMENDATION = re.compile(
    r"(?:we )?recommend\w* (?:to )?(?:acquir\w*|buy\w*|invest\w*|proceed\w* with the (?:acquisition|transaction|deal)|"
    r"the acquisition)|should (?:acquire|buy|invest in) the (?:company|target|business)|fair (?:price|value)|"
    r"attractive (?:price|valuation)|(?:good|bad|sound|poor) investment|walk away from the (?:deal|transaction)|"
    r"recomend\w* (?:a |o )?(?:compra|aquisição|investimento)|preço (?:justo|adequado|atrativo)|valor justo",
    re.I)


@dataclass
class MemoCheck:
    numbers_checked: int
    unmatched_numbers: list[tuple[str, str]]   # (figure, line where it appears)
    missing_alerts: list[str]
    recommendations: list[str]
    request_list_found: bool
    orphan_questions: list[str]
    long_sentences: list[str]
    misdated_numbers: list[tuple[str, str, str]] = ()    # (figure, line, the period it belongs to)
    other_line_numbers: list[tuple[str, str, str]] = ()  # (figure, line, the material line it matches)

    @property
    def errors(self) -> list[str]:
        out = [f"Figure not found in the material: {n} (in: {line})" for n, line in self.unmatched_numbers]
        out += [f"Figure cited for the wrong period: {n} is the {why} (in: {line})"
                for n, line, why in self.misdated_numbers]
        out += [f"Finding missing from the memo: {a}" for a in self.missing_alerts]
        out += [f"Investment-recommendation language: \"{r}\"" for r in self.recommendations]
        if not self.request_list_found:
            out.append("Request list not found (a table with a 'Related question' column).")
        return out

    @property
    def warnings(self) -> list[str]:
        out = [f"Question without a matching request: {q}" for q in self.orphan_questions]
        out += [f"Figure found for that period under another line, {what}: check it is the line cited: {n} "
                f"(in: {line})" for n, line, what in self.other_line_numbers]
        out += [f"Sentence over {MAX_WORDS} words ({len(s.split())}): {s[:100]}…" for s in self.long_sentences]
        return out

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------- figures
def _readings(token: str) -> list[tuple[float, int]]:
    """Possible values of a written figure (value, decimals). '1,415' and '1.415' are ambiguous."""
    t = re.sub(r"[   ]", " ", token.replace("−", "-"))
    if re.fullmatch(r"-?\d{1,3}(?: \d{3})+", t):                         # 1 415
        return [(float(t.replace(" ", "")), 0)]
    m = re.fullmatch(r"(-?\d{1,3}(?:([.,])\d{3})+)(?:([.,])(\d+))?", t)  # 1,415 · 21,400.5 · 1.415,5
    if m and (m.group(3) is None or m.group(3) != m.group(2)):
        whole = float(m.group(1).replace(m.group(2), ""))
        if m.group(4):
            return [(float(f"{int(whole)}.{m.group(4)}"), len(m.group(4)))]
        out = [(whole, 0)]
        if m.group(1).count(m.group(2)) == 1:                            # could also be a decimal: 1.415
            out.append((float(m.group(1).replace(",", ".")), 3))
        return out
    if "," in t:                                                         # 23,8
        return [(float(t.replace(",", ".")), len(t.split(",")[1]))]
    if "." in t:                                                         # 23.8
        return [(float(t), len(t.split(".")[1]))]
    return [(float(t), 0)]


@dataclass(frozen=True)
class Fact:
    """A figure of the material with the period and the line it belongs to (year None: not stated)."""
    value: float
    year: int | None
    label: str


_YEAR = re.compile(r"\bFY ?(\d{4}|\d{2})\b|(?<![\d.,])((?:19|20)\d{2})(?![\d.,])")
_COL_YEAR = re.compile(r"\bFY ?(\d{4}|\d{2})\b|^\s*((?:19|20)\d{2})\s*$")
_CELL = re.compile(r"([A-Z]{1,3})(\d+): (.*)")
_CLAUSE = re.compile(r"[^;.!?]+(?:[.!?](?=\d)[^;.!?]*)*")   # a clause; '23.8' does not end it


def _year_of(match: re.Match) -> int:
    y = match.group(1) or match.group(2)
    return 2000 + int(y) if len(y) == 2 else int(y)


def _values(token: str) -> list[float]:
    try:
        return [v for v, _ in _readings(token)]
    except ValueError:
        return [float(p.replace(",", ".")) for p in re.findall(r"-?\d+(?:[.,]\d+)?", token)]


def _cited_year(text: str, start: int, end: int) -> int | None:
    """The period a figure is cited for, in its clause: the year right after it with no other figure in between
    ('67.6% in FY23'), else the nearest year before it ('FY23: €27,739k', 'In FY23 … €27,739k'), else the
    nearest year after it."""
    years = [y for y in _YEAR.finditer(text) if not y.start() <= start < y.end()]
    after = [y for y in years if y.start() >= end]
    before = [y for y in years if y.end() <= start]
    plain = lambda a, b: not re.search(r"\d", _YEAR.sub("", text[a:b]))
    if after and plain(end, after[0].start()):
        return _year_of(after[0])
    if before:
        return _year_of(before[-1])
    return _year_of(after[0]) if after else None


def _prose_facts(text: str) -> list[Fact]:
    out = []
    for clause in _CLAUSE.finditer(text):
        c = clause.group(0)
        for tok in _MATERIAL_NUM.finditer(c):
            if _YEAR.fullmatch(tok.group(0)):
                continue
            year = _cited_year(c, tok.start(), tok.end())
            out += [Fact(v, year, c) for v in _values(tok.group(0))]
    return out


def _material_facts(material: str) -> list[Fact]:
    """Every figure of the material with its year and line: tables with year columns (or a Year column),
    evidence written as 'FY23: €27,739k', and the data room's cells under their sheet's year header."""
    facts: list[Fact] = []
    header: list[str] | None = None
    sheet_years: dict[str, int] = {}
    for line in material.splitlines():
        s = line.strip()
        if s.startswith("### Sheet"):
            sheet_years = {}
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            if header is None:
                header = cells
                continue
            label = cells[0]
            row_year = next((_year_of(m) for c in cells[1:] if (m := _COL_YEAR.fullmatch(c))), None)
            for i, cell in enumerate(cells[1:], 1):
                col = _COL_YEAR.search(header[i]) if i < len(header) else None
                year = _year_of(col) if col else row_year
                if _COL_YEAR.fullmatch(cell):
                    continue
                facts += [Fact(v, year, label) for tok in _MATERIAL_NUM.findall(cell) for v in _values(tok)]
            continue
        header = None
        parts = [_CELL.fullmatch(p) for p in s.split(" | ")]
        cells = [p.groups() for p in parts] if s and all(parts) else []
        if cells:                                    # a data room row: 'A8: Other income | C8: 34746983'
            years = {col: _year_of(m) for col, _, val in cells if (m := _COL_YEAR.fullmatch(val.strip()))}
            if len(years) >= 2:
                sheet_years = years
                continue
            label = next((val for col, _, val in cells if not _MATERIAL_NUM.fullmatch(val.strip())), "")
            for col, _, val in cells:
                if _MATERIAL_NUM.fullmatch(val.strip()):
                    facts += [Fact(v, sheet_years.get(col), label) for v in _values(val.strip())]
            if any(not _MATERIAL_NUM.fullmatch(val.strip()) for _, _, val in cells):
                facts += [f for _, _, val in cells for f in _prose_facts(val)
                          if not _MATERIAL_NUM.fullmatch(val.strip())]
            continue
        facts += _prose_facts(s)
    return facts


def _same(value: float, decimals: int, m: float) -> bool:
    """The written value is the material's figure at the same rounding; also as a %, in millions or unsigned."""
    for cand in (m, m * 100, m / 1000):   # decimal -> %; EUR thousands -> millions
        r = round(cand, decimals)
        if abs(r - value) < 1e-9 or abs(abs(r) - abs(value)) < 1e-9:
            return True
    return False


_STOP = {"total", "from", "with", "that", "this", "were", "than", "into", "over", "year", "years", "eur", "euros",
         "thousands", "which", "their", "after", "before", "within", "rule", "source", "evidence"}


def _words(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-zà-ÿ]{4,}", text.lower()) if w not in _STOP}


def _skip(value: float, decimals: int) -> bool:
    """Figures that are not data: years and small integers (3 themes, 2 pages, 5 documents)."""
    return decimals == 0 and (1990 <= value <= 2035 or abs(value) <= 10)


def _strip_index_column(memo: str) -> str:
    """Drop the '#' column of tables and the numbers of numbered lists (they are not data)."""
    lines, drop_first = [], False
    for line in memo.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else None
        if cells is None:
            drop_first = False
            lines.append(_LIST_MARKER.sub("", line))
            continue
        if cells and cells[0].lower() in ("#", "no", "no.", "nº", "n.º", "n°"):
            drop_first = True
        lines.append("| " + " | ".join(cells[1:] if drop_first else cells) + " |")
    return "\n".join(lines)


def _check_numbers(memo: str, material: str) -> tuple[int, list, list, list]:
    """Each figure must exist in the material for the period cited next to it: '€27,739k in FY24' fails
    when €27,739k is the FY23 value. A figure found for that period but under another line is a warning
    (labels in prose vary: 'operating cash' for 'cash generated from operations')."""
    facts = _material_facts(material)
    text = _strip_index_column(memo)
    checked, unmatched, misdated, other_line = 0, [], [], []
    for line in text.splitlines():
        cells = [c for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else [line]
        for cell in cells:
            for clause in _CLAUSE.finditer(cell):
                c = clause.group(0)
                for m in _NUM.finditer(c):
                    all_readings = _readings(m.group(1))
                    readings = [(v, d) for v, d in all_readings if not _skip(v, d)]
                    if len(readings) < len(all_readings):
                        continue
                    checked += 1
                    hits = [f for f in facts if any(_same(v, d, f.value) for v, d in readings)]
                    where = line.strip(" |")[:120]
                    if not hits:
                        unmatched.append((m.group(1), where))
                        continue
                    year = _cited_year(c, m.start(), m.end())
                    if year is None:
                        continue
                    in_year = [f for f in hits if f.year in (year, None)]
                    if not in_year:
                        f = hits[0]
                        misdated.append((m.group(1), where, f"FY{str(f.year)[2:]} value of '{f.label[:60]}', "
                                                           f"cited for FY{str(year)[2:]}"))
                    elif not any(_words(f.label) & _words(c) for f in in_year) and \
                            not any(f.year is None for f in in_year):
                        other_line.append((m.group(1), where, f"'{in_year[0].label[:60]}'"))
    return checked, unmatched, misdated, other_line


# ---------------------------------------------------------------- tables and questions
def _tables(memo: str) -> list[list[list[str]]]:
    """Markdown tables: list of rows (header first), without the separator row."""
    tables, current = [], []
    for line in memo.splitlines() + [""]:
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip(" ?.*")


def _column(tables, header_test) -> list[str] | None:
    """Values of the column whose header passes the test, across all tables; None if there is none."""
    values, seen = [], False
    for t in tables:
        for i, h in enumerate(t[0]):
            if header_test(_norm(h)):
                seen = True
                values += [row[i] for row in t[1:] if i < len(row) and row[i]]
    return values if seen else None


def _check_questions(memo: str) -> tuple[bool, list[str]]:
    tables = _tables(memo)
    related = lambda h: "related question" in h or "pergunta associada" in h
    asked = _column(tables, lambda h: ("question" in h or "pergunta" in h) and not related(h)) or []
    requested = _column(tables, related)
    if requested is None:
        return False, []
    pool = [_norm(q) for cell in requested for q in re.split(r"\?", cell) if q.strip()]
    orphan = []
    for q in asked:
        qn = _norm(q)
        if not any(qn in p or p in qn or SequenceMatcher(None, qn, p).ratio() >= 0.75 for p in pool):
            orphan.append(q)
    return True, orphan


# ---------------------------------------------------------------- form
def _long_sentences(memo: str) -> list[str]:
    units = [l for l in memo.splitlines() if l.strip() and not l.strip().startswith(("|", "#", "---"))
             and l.count(" · ") < 2]   # metadata lines (Memo for … · Amounts … · Sources …)
    units += [c for t in _tables(memo) for row in t[1:] for c in row]
    clean = lambda t: _LIST_MARKER.sub("", re.sub(r"[*_#>]", "", t))
    sentences = [s.strip() for u in units for s in re.split(r"(?<=[.!?])\s+", clean(u))]
    return [s for s in sentences if len(s.split()) > MAX_WORDS]


def check_memo(memo: str, material: str, alert_ids: list[str]) -> MemoCheck:
    """Check the memo against the material sent to the AI and the findings that fired."""
    checked, unmatched, misdated, other_line = _check_numbers(memo, material)
    found_list, orphan = _check_questions(memo)
    return MemoCheck(
        numbers_checked=checked,
        unmatched_numbers=unmatched,
        missing_alerts=[a for a in alert_ids if not re.search(rf"\b{a}\b", memo)],
        recommendations=sorted({m.group(0) for m in _RECOMMENDATION.finditer(memo)}),
        request_list_found=found_list,
        orphan_questions=orphan,
        long_sentences=_long_sentences(memo),
        misdated_numbers=misdated,
        other_line_numbers=other_line,
    )


def report(check: MemoCheck) -> str:
    """Readable summary of the check (plain text that also renders as Markdown)."""
    head = "passed" if check.ok else f"{len(check.errors)} error(s)"
    lines = [f"Automatic memo check: {head}, {len(check.warnings)} warning(s).",
             f"- Figures checked against the material: {check.numbers_checked}; "
             f"without a source: {len(check.unmatched_numbers)}."]
    lines += [f"- ERROR: {e}" for e in check.errors if not e.startswith("Figure ")]
    lines += [f"- ERROR: {e}" for e in check.errors if e.startswith("Figure ")]
    lines += [f"- Warning: {w}" for w in check.warnings]
    return "\n".join(lines)
