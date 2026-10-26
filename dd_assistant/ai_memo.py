"""Camada 5 — IA: escreve o memo, a request list e as notas para o template (Claude API).

A IA não faz contas nem cria alertas. Recebe o que as camadas 1–4 já produziram (alertas
com evidência e fonte, o catálogo de regras, as métricas, os dados de origem) e o texto
integral do data room, e segue o prompt de docs/camada_ia_prompt.md (o system prompt).

A chave da Claude API vem da variável de ambiente ANTHROPIC_API_KEY ou do ficheiro .env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable

import anthropic
from openpyxl import load_workbook

from .input_loader import LINE_LABELS, CompanyData
from .metrics import LABELS, Metrics
from .report import Reviews, fmt_value
from .rules import RuleResult, alerts

ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILE = ROOT / "docs" / "camada_ia_prompt.md"

MODEL = "claude-opus-5-5"
MAX_TOKENS = 64000      # com streaming não há timeout; o memo fica muito abaixo deste limite
EFFORT = "high"         # trabalho de análise (o valor por defeito do Opus 5.5 é "medium")
# Preço por milhão de tokens do Claude Opus 5.5 (outubro de 2026), só para estimar o custo.
PRICE_IN, PRICE_OUT = 4.00, 20.00


class MemoError(Exception):
    """A chamada correu, mas não devolveu um memo (o modelo recusou o pedido)."""


@dataclass
class Memo:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    truncated: bool     # True se a resposta parou no limite de tokens

    @property
    def cost_usd(self) -> float:
        """Estimativa ao preço do Opus 5.5 (se o modelo de recurso respondeu, o preço pode ser outro)."""
        return (self.input_tokens * PRICE_IN + self.output_tokens * PRICE_OUT) / 1_000_000


def load_env(path: Path = ROOT / ".env") -> None:
    """Lê variáveis de um ficheiro .env (CHAVE=valor) sem sobrepor as que já existem."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value:   # uma chave vazia (copiada do .env.example) não conta
                os.environ.setdefault(key.strip(), value)


def system_prompt() -> str:
    """O prompt de docs/camada_ia_prompt.md a partir de '## Papel' (o cabeçalho é nota para humanos)."""
    text = PROMPT_FILE.read_text(encoding="utf-8")
    start = text.find("## Papel")
    return text[start:] if start >= 0 else text


# ---------------------------------------------------------------- material enviado à IA
def _row(cells) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _table(head: list, rows: list[list]) -> list[str]:
    return [_row(head), _row(["---"] * len(head))] + [_row(r) for r in rows]


def _alerts_section(results: list[RuleResult], reviews: Reviews) -> list[str]:
    out = ["## 1. Red Flags (alertas que dispararam, pela ordem da folha)"]
    al = alerts(results)
    if not al:
        out.append("Nenhuma regra disparou.")
    for i, r in enumerate(al, 1):
        rule = r.rule
        state, comment = reviews.get(rule.id, ("Pendente", ""))
        out += ["",
                f"### {i}. {rule.id} · {rule.name} — {rule.area}; relevância {rule.relevance}; anos {r.years_text}",
                f"- Evidência (com fonte): {r.evidence}",
                f"- Cálculo e regra disparada: {rule.calc}. Regra: {rule.rule_text()}",
                f"- Ponto a investigar: {rule.ponto}",
                f"- Porque importa: {rule.porque}",
                f"- Pergunta-modelo: {rule.pergunta}",
                f"- Documento a pedir: {rule.documento}",
                f"- Estado do revisor: {state}" + (f" — {comment}" if comment else "")]
    return out


def _rules_section(results: list[RuleResult]) -> list[str]:
    years = sorted(results[0].values)
    rows = [[r.rule.id, r.rule.name, r.rule.limit_text()]
            + [f"{fmt_value(r.values[y])} ({r.fires[y]})" for y in years] + ["Sim" if r.alert else "Não"]
            for r in results]
    head = ["Regra", "Nome", "Limite"] + [f"{y} (dispara?)" for y in years] + ["Alerta"]
    return ["## 2. Regras (catálogo completo: valor de cada ano e se disparou)"] + _table(head, rows)


def _metrics_section(metrics: Metrics, years: list[int]) -> list[str]:
    rows = [[label] + [fmt_value(metrics[key].get(y)) for y in years] for key, label in LABELS.items()]
    return ["## 3. Métricas (calculadas pelo template)"] + _table(["Métrica"] + years, rows)


def _input_section(d: CompanyData) -> list[str]:
    ys = d.years
    vals = lambda values: [fmt_value(values.get(y)) for y in ys]
    rows = [[label] + vals(d.lines[key]) + [d.sources.get(key, "")]
            for label, key in LINE_LABELS.items() if key in d.lines]
    rows += [[f"Vendas ao cliente: {c.name}"] + vals(c.values) + [d.clients_source if i == 0 else ""]
             for i, c in enumerate(d.clients)]
    if d.other_clients:
        rows.append(["Vendas a outros clientes"] + vals(d.other_clients) + [""])
    rows += [[f"Ajuste da gestão ao EBITDA: {a.name}"] + vals(a.values) + [d.adjustments_source if i == 0 else ""]
             for i, a in enumerate(d.adjustments)]
    docs = "; ".join(f"{name}: {'Sim' if ok else 'Não'}" for name, ok in d.documents)
    return (["## 4. Input (dados de origem e fonte no data room)"]
            + _table(["Rubrica"] + ys + ["Fonte no data room"], rows)
            + ["", f"Documentos recebidos: {docs}"])


def data_room_text(path: str | Path | BinaryIO) -> str:
    """Todas as folhas do data room em texto, com a referência de cada célula (ex.: B5: 18400)."""
    wb = load_workbook(path, data_only=True)
    out = []
    for ws in wb.worksheets:
        out += ["", f"### Folha '{ws.title}'"]
        for row in ws.iter_rows():
            cells = [f"{c.coordinate}: {fmt_value(c.value)}" for c in row if c.value not in (None, "")]
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out)


def build_material(d: CompanyData, metrics: Metrics, results: list[RuleResult],
                   data_room: str | Path | BinaryIO, reviews: Reviews | None = None, name: str = "") -> str:
    """O texto enviado à IA: as quatro folhas do template e o data room. Fica gravado para auditoria."""
    parts = [f"# Material para a análise preliminar{' — ' + name if name else ''}", "",
             "Notas de leitura: valores em € milhares; percentagens em decimal (0.238 = 23,8%); variações de margem "
             "e diferenças de crescimento em pontos percentuais; DSO, DIO e DPO em dias; 'n.d.' = não disponível. "
             "As referências do data room seguem a forma Folha!Célula (ex.: DRE!D5).", ""]
    parts += _alerts_section(results, reviews or {}) + [""]
    parts += _rules_section(results) + [""]
    parts += _metrics_section(metrics, d.years) + [""]
    parts += _input_section(d) + [""]
    parts += ["## 5. Data room (texto integral)", data_room_text(data_room), "",
              "Escreve os três entregáveis (memo de duas páginas, information request list e notas para melhorar "
              "o template) em Markdown e em português de Portugal. Revê-os com a lista de verificação antes de "
              "responder e responde só com os entregáveis."]
    return "\n".join(parts)


# ---------------------------------------------------------------- chamada à Claude API
def write_memo(material: str, client: anthropic.Anthropic | None = None,
               on_text: Callable[[str], None] | None = None) -> Memo:
    """Envia o material à Claude API e devolve o memo. on_text recebe o texto à medida que chega."""
    client = client or anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",     # se o modelo recusar, a API tenta o modelo de recurso recomendado
            system=system_prompt(),
            messages=[{"role": "user", "content": material}],
        ) as stream:
            for text in stream.text_stream:
                if on_text:
                    on_text(text)
            msg = stream.get_final_message()
    except TypeError as e:
        if "authentication method" in str(e):   # o SDK não encontrou chave nenhuma
            raise MemoError("Não encontrei a chave da Claude API. Copie o ficheiro .env.example para .env "
                            "e cole lá a chave (ANTHROPIC_API_KEY=...).") from e
        raise

    if msg.stop_reason == "refusal":
        raise MemoError("O modelo recusou o pedido (e o modelo de recurso também). Reveja o material enviado.")
    text = "".join(b.text for b in msg.content if b.type == "text")
    return Memo(text, msg.model, msg.usage.input_tokens, msg.usage.output_tokens,
                truncated=msg.stop_reason == "max_tokens")
