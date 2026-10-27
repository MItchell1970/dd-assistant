"""Check of the AI memo (deterministic, no AI).

Automatically confirms part of the checklist in docs/ai_memo_prompt.md:
  - every figure in the memo exists in the material sent to the AI, or is a rounding of one;
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

    @property
    def errors(self) -> list[str]:
        out = [f"Figure not found in the material: {n} (in: {line})" for n, line in self.unmatched_numbers]
        out += [f"Finding missing from the memo: {a}" for a in self.missing_alerts]
        out += [f"Investment-recommendation language: \"{r}\"" for r in self.recommendations]
        if not self.request_list_found:
            out.append("Request list not found (a table with a 'Related question' column).")
        return out

    @property
    def warnings(self) -> list[str]:
        out = [f"Question without a matching request: {q}" for q in self.orphan_questions]
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


def _material_numbers(material: str) -> set[float]:
    out = set()
    for tok in _MATERIAL_NUM.findall(material):
        try:
            out.update(v for v, _ in _readings(tok))
        except ValueError:
            out.update(float(p.replace(",", ".")) for p in re.findall(r"-?\d+(?:[.,]\d+)?", tok))
    return out


def _found(value: float, decimals: int, material: set[float]) -> bool:
    """The value exists in the material at the same rounding; also as a %, in millions or unsigned."""
    for m in material:
        for cand in (m, m * 100, m / 1000):   # decimal -> %; EUR thousands -> millions
            r = round(cand, decimals)
            if abs(r - value) < 1e-9 or abs(abs(r) - abs(value)) < 1e-9:
                return True
    return False


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


def _check_numbers(memo: str, material: str) -> tuple[int, list[tuple[str, str]]]:
    known = _material_numbers(material)
    text = _strip_index_column(memo)
    checked, unmatched = 0, []
    for m in _NUM.finditer(text):
        all_readings = _readings(m.group(1))
        readings = [(v, d) for v, d in all_readings if not _skip(v, d)]
        if len(readings) < len(all_readings):
            continue
        checked += 1
        if not any(_found(v, d, known) for v, d in readings):
            line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.start())]
            unmatched.append((m.group(1), line.strip(" |")[:120]))
    return checked, unmatched


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
    checked, unmatched = _check_numbers(memo, material)
    found_list, orphan = _check_questions(memo)
    return MemoCheck(
        numbers_checked=checked,
        unmatched_numbers=unmatched,
        missing_alerts=[a for a in alert_ids if not re.search(rf"\b{a}\b", memo)],
        recommendations=sorted({m.group(0) for m in _RECOMMENDATION.finditer(memo)}),
        request_list_found=found_list,
        orphan_questions=orphan,
        long_sentences=_long_sentences(memo),
    )


def report(check: MemoCheck) -> str:
    """Readable summary of the check (plain text that also renders as Markdown)."""
    head = "passed" if check.ok else f"{len(check.errors)} error(s)"
    lines = [f"Automatic memo check: {head}, {len(check.warnings)} warning(s).",
             f"- Figures checked against the material: {check.numbers_checked}; "
             f"without a source: {len(check.unmatched_numbers)}."]
    lines += [f"- ERROR: {e}" for e in check.errors if not e.startswith("Figure not found")]
    lines += [f"- ERROR: {e}" for e in check.errors if e.startswith("Figure not found")]
    lines += [f"- Warning: {w}" for w in check.warnings]
    return "\n".join(lines)
