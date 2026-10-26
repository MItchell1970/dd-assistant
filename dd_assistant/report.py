"""Camada 4 — escrever a tabela de red flags (Excel e CSV) e um resumo para a consola."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import BinaryIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .metrics import LABELS, Metrics
from .rules import RuleResult, alerts

COLUMNS = ["Nº", "Regra", "Área", "Anos", "Evidência (com fonte)", "Cálculo e regra disparada",
           "Ponto a investigar", "Relevância", "Pergunta para a empresa", "Documento a pedir",
           "Estado do revisor", "Comentário do revisor"]
REVIEW_STATES = ["Pendente", "Aceite", "Descartado"]

# Revisão de cada alerta: ID da regra -> (estado, comentário). Sem revisão = ("Pendente", "").
Reviews = dict[str, tuple[str, str]]


def fmt_value(v) -> str:
    """Mostra um valor como na evidência: None = 'n.d.', números com até 4 casas decimais."""
    if v is None:
        return "n.d."
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


def red_flag_rows(results: list[RuleResult], reviews: Reviews | None = None) -> list[list[str]]:
    reviews = reviews or {}
    rows = []
    for i, r in enumerate(alerts(results), 1):
        rule = r.rule
        state, comment = reviews.get(rule.id, ("Pendente", ""))
        rows.append([i, rule.id, rule.area, r.years_text, r.evidence,
                     f"{rule.calc}\nRegra: {rule.rule_text()}", rule.ponto, rule.relevance,
                     rule.pergunta, rule.documento, state, comment])
    return rows


def summary(results: list[RuleResult]) -> str:
    al = alerts(results)
    by = {k: sum(1 for r in al if r.rule.relevance == k) for k in ("Alta", "Média", "Baixa")}
    lines = [f"Alertas: {len(al)}  ·  Alta: {by['Alta']}  ·  Média: {by['Média']}  ·  Baixa: {by['Baixa']}", ""]
    for i, r in enumerate(al, 1):
        lines.append(f"{i:>2}. {r.rule.id} [{r.rule.relevance}] {r.rule.name} ({r.years_text})")
    return "\n".join(lines)


def csv_bytes(results: list[RuleResult], reviews: Reviews | None = None) -> bytes:
    f = io.StringIO(newline="")
    w = csv.writer(f, delimiter=";")
    w.writerow(COLUMNS)
    w.writerows(red_flag_rows(results, reviews))
    return f.getvalue().encode("utf-8-sig")   # utf-8-sig: o Excel abre com acentos


def write_csv(results: list[RuleResult], path: Path, reviews: Reviews | None = None) -> None:
    Path(path).write_bytes(csv_bytes(results, reviews))


def write_excel(results: list[RuleResult], metrics: Metrics, years: list[int],
                path: Path | BinaryIO, reviews: Reviews | None = None) -> None:
    """Grava num ficheiro ou num buffer em memória (a app usa o buffer para o download)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Red Flags"
    head = Font(name="Arial", bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="1F3864")
    for c, h in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font, cell.fill = head, fill
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for r, row in enumerate(red_flag_rows(results, reviews), 2):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    last = ws.max_row
    dv = DataValidation(type="list", formula1='"' + ",".join(REVIEW_STATES) + '"')
    ws.add_data_validation(dv)
    dv.add(f"K2:K{max(last, 2)}")
    for col, w in zip("ABCDEFGHIJKL", [5, 8, 16, 10, 60, 34, 34, 10, 44, 32, 14, 28]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C2"

    wm = wb.create_sheet("Métricas")
    wm.append(["Métrica"] + [str(y) for y in years])
    for key, label in LABELS.items():
        wm.append([label] + [("n.d." if metrics[key].get(y) is None else metrics[key].get(y)) for y in years])
    wm.column_dimensions["A"].width = 52
    wb.save(path)
