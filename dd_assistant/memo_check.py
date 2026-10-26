"""Verificação do memo da IA (determinística, sem IA).

Confirma de forma automática parte da lista de verificação de docs/camada_ia_prompt.md:
  - cada número do memo existe no material enviado à IA, ou é um arredondamento dele;
  - todos os alertas aparecem no memo;
  - não há recomendação de investimento nem opinião sobre o preço;
  - cada pergunta à empresa tem um pedido na request list (aviso);
  - frases com mais de 25 palavras (aviso).
Erros = o memo quebra uma regra do prompt. Avisos = a rever por uma pessoa.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

MAX_WORDS = 25

# Números no memo. Não apanha os que fazem parte de R01, §4, DRE!D5, B5:D5, 31/12/2025 ou 1.º.
_NUM = re.compile(r"(?<![\w§/!:.,–-])"
                  r"([-−]?\d{1,3}(?:[.   ]\d{3})+(?:,\d+)?"   # 1.415 · 1 415 · 21.400,5
                  r"|[-−]?\d+(?:[.,]\d+)?)"                             # 1415 · 23,8 · 23.8
                  r"(?![\w/])")
_MATERIAL_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s")
_RECOMMENDATION = re.compile(
    r"recomend\w* (?:a |o )?(?:compra|aquisição|investimento)|\b(?:não )?(?:comprar|investir) (?:a|na) empresa"
    r"|deve(?:m)? (?:comprar|avançar com a (?:compra|aquisição|operação))|preço (?:justo|adequado|atrativo)"
    r"|valor justo|bom investimento|mau investimento", re.I)


@dataclass
class MemoCheck:
    numbers_checked: int
    unmatched_numbers: list[tuple[str, str]]   # (número, linha onde aparece)
    missing_alerts: list[str]
    recommendations: list[str]
    request_list_found: bool
    orphan_questions: list[str]
    long_sentences: list[str]

    @property
    def errors(self) -> list[str]:
        out = [f"Número sem fonte no material: {n} (em: {line})" for n, line in self.unmatched_numbers]
        out += [f"Alerta em falta no memo: {a}" for a in self.missing_alerts]
        out += [f"Linguagem de recomendação de investimento: \"{r}\"" for r in self.recommendations]
        if not self.request_list_found:
            out.append("Não encontrei a request list (tabela com a coluna 'Pergunta associada').")
        return out

    @property
    def warnings(self) -> list[str]:
        out = [f"Pergunta sem pedido correspondente na request list: {q}" for q in self.orphan_questions]
        out += [f"Frase com mais de {MAX_WORDS} palavras ({len(s.split())}): {s[:100]}…" for s in self.long_sentences]
        return out

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------- números
def _readings(token: str) -> list[tuple[float, int]]:
    """Valores possíveis de um número escrito (valor, casas decimais). '1.415' pode ser mil ou decimal."""
    t = token.replace("−", "-")
    if "," in t:                                              # 23,8 · 1.415,5
        whole, dec = t.split(",")
        return [(float(re.sub(r"[.   ]", "", whole) + "." + dec), len(dec))]
    if re.fullmatch(r"-?\d{1,3}(?:[   ]\d{3})+", t):  # 1 415
        return [(float(re.sub(r"\D", "", t)) * (-1 if t.startswith("-") else 1), 0)]
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", t):              # 1.415: milhares (pt) ou decimal (en)
        return [(float(t.replace(".", "")), 0), (float(t), len(t.split(".")[1]))]
    if "." in t:                                               # 23.8
        return [(float(t), len(t.split(".")[1]))]
    return [(float(t), 0)]


def _material_numbers(material: str) -> set[float]:
    return {float(tok.replace(",", ".")) for tok in _MATERIAL_NUM.findall(material)}


def _found(value: float, decimals: int, material: set[float]) -> bool:
    """O valor existe no material, arredondado às mesmas casas; também em %, em milhões ou sem sinal."""
    for m in material:
        for cand in (m, m * 100, m / 1000):   # decimal -> %; € milhares -> milhões
            r = round(cand, decimals)
            if abs(r - value) < 1e-9 or abs(abs(r) - abs(value)) < 1e-9:
                return True
    return False


def _skip(value: float, decimals: int) -> bool:
    """Números que não são dados: anos e inteiros pequenos (3 temas, 2 páginas, 5 documentos)."""
    return decimals == 0 and (1990 <= value <= 2035 or abs(value) <= 10)


def _strip_index_column(memo: str) -> str:
    """Tira a coluna 'Nº' das tabelas e os marcadores de listas numeradas (não são dados)."""
    lines, drop_first = [], False
    for line in memo.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else None
        if cells is None:
            drop_first = False
            lines.append(_LIST_MARKER.sub("", line))
            continue
        if cells and cells[0].lower() in ("nº", "n.º", "#", "n°"):
            drop_first = True
        lines.append("| " + " | ".join(cells[1:] if drop_first else cells) + " |")
    return "\n".join(lines)


def _check_numbers(memo: str, material: str) -> tuple[int, list[tuple[str, str]]]:
    known = _material_numbers(material)
    text = _strip_index_column(memo)
    checked, unmatched = 0, []
    for m in _NUM.finditer(text):
        readings = [(v, d) for v, d in _readings(m.group(1)) if not _skip(v, d)]
        if len(readings) < len(_readings(m.group(1))):
            continue
        checked += 1
        if not any(_found(v, d, known) for v, d in readings):
            line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.start())]
            unmatched.append((m.group(1), line.strip(" |")[:120]))
    return checked, unmatched


# ---------------------------------------------------------------- tabelas e perguntas
def _tables(memo: str) -> list[list[list[str]]]:
    """Tabelas Markdown: lista de linhas (cabeçalho primeiro), sem a linha de separação."""
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
    """Valores da coluna cujo cabeçalho passa no teste, em todas as tabelas; None se não houver."""
    values, seen = [], False
    for t in tables:
        for i, h in enumerate(t[0]):
            if header_test(_norm(h)):
                seen = True
                values += [row[i] for row in t[1:] if i < len(row) and row[i]]
    return values if seen else None


def _check_questions(memo: str) -> tuple[bool, list[str]]:
    tables = _tables(memo)
    asked = _column(tables, lambda h: "pergunta" in h and "associada" not in h) or []
    requested = _column(tables, lambda h: "pergunta associada" in h)
    if requested is None:
        return False, []
    pool = [_norm(q) for cell in requested for q in re.split(r"\?", cell) if q.strip()]
    orphan = []
    for q in asked:
        qn = _norm(q)
        if not any(qn in p or p in qn or SequenceMatcher(None, qn, p).ratio() >= 0.75 for p in pool):
            orphan.append(q)
    return True, orphan


# ---------------------------------------------------------------- forma
def _long_sentences(memo: str) -> list[str]:
    units = [l for l in memo.splitlines() if l.strip() and not l.strip().startswith(("|", "#", "---"))
             and l.count(" · ") < 2]   # linhas de metadados (Memo para … · Valores … · Fontes …)
    units += [c for t in _tables(memo) for row in t[1:] for c in row]
    clean = lambda t: _LIST_MARKER.sub("", re.sub(r"[*_#>]", "", t))
    sentences = [s.strip() for u in units for s in re.split(r"(?<=[.!?])\s+", clean(u))]
    return [s for s in sentences if len(s.split()) > MAX_WORDS]


def check_memo(memo: str, material: str, alert_ids: list[str]) -> MemoCheck:
    """Verifica o memo contra o material enviado à IA e a lista de alertas que dispararam."""
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
    """Resumo legível da verificação (texto simples, também serve como Markdown)."""
    head = "OK" if check.ok else f"{len(check.errors)} erro(s)"
    lines = [f"Verificação automática do memo: {head}, {len(check.warnings)} aviso(s).",
             f"- Números verificados contra o material: {check.numbers_checked}; "
             f"sem fonte: {len(check.unmatched_numbers)}."]
    lines += [f"- ERRO: {e}" for e in check.errors if not e.startswith("Número sem fonte")]
    lines += [f"- ERRO: {e}" for e in check.errors if e.startswith("Número sem fonte")]
    lines += [f"- Aviso: {w}" for w in check.warnings]
    return "\n".join(lines)
