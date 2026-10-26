"""Teste de paridade: o Python tem de dar exatamente o mesmo resultado que a planilha.

Lê os valores já calculados pelo Excel (folhas Métricas, Regras e Red Flags) e compara
com o que o código calcula a partir da folha Input.

Correr:  python -m unittest -v
Nota: o template tem de ter sido gravado por um programa que calcula fórmulas
(Excel ou LibreOffice); se as células calculadas estiverem vazias, o teste avisa.
"""
from __future__ import annotations

import math
import unittest
from pathlib import Path

from openpyxl import load_workbook

from dd_assistant.input_loader import load_input
from dd_assistant.metrics import LABELS, compute_metrics
from dd_assistant.rules import RULES, alerts, evaluate

TEMPLATE = Path(__file__).resolve().parents[1] / "data" / "DD_template_modulo1.xlsx"
YEAR_COLS = {"B": 2022, "C": 2023, "D": 2024, "E": 2025}


def same(a, b) -> bool:
    """Compara um valor da planilha com um do Python ('n.d.' e vazio = None)."""
    a = None if a in ("n.d.", "", None) else a
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return str(a) == str(b)


def norm(text: str) -> str:
    """O Excel em português escreve 23,8 e o LibreOffice 23.8: tratamos os dois como iguais."""
    return str(text).replace(",", ".")


class ParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_input(TEMPLATE)
        cls.metrics = compute_metrics(cls.data)
        cls.results = evaluate(cls.data, cls.metrics)
        cls.wb = load_workbook(TEMPLATE, data_only=True)
        if cls.wb["Métricas"]["C6"].value is None:
            raise unittest.SkipTest("O template não tem valores calculados: abra-o no Excel e grave.")

    def test_metrics_match_sheet(self):
        ws = self.wb["Métricas"]
        rows = {}
        for r in range(5, ws.max_row + 1):
            label = ws[f"A{r}"].value
            if label in LABELS.values() and label not in rows:
                rows[label] = r
        missing = [l for l in LABELS.values() if l not in rows]
        self.assertEqual(missing, [], "métricas sem linha na folha Métricas")
        for key, label in LABELS.items():
            for col, year in YEAR_COLS.items():
                sheet = ws[f"{col}{rows[label]}"].value
                py = self.metrics[key].get(year)
                with self.subTest(metrica=label, ano=year):
                    self.assertTrue(same(sheet, py), f"planilha={sheet!r}  python={py!r}")

    def test_rules_match_sheet(self):
        ws = self.wb["Regras"]
        by_id = {ws[f"A{r}"].value: r for r in range(5, ws.max_row + 1) if ws[f"A{r}"].value}
        self.assertEqual(sorted(by_id), sorted(r.id for r in RULES), "catálogo diferente da planilha")
        for res in self.results:
            r = by_id[res.rule.id]
            with self.subTest(regra=res.rule.id):
                self.assertTrue(same(ws[f"F{r}"].value, res.rule.limit), "limite diferente")
                self.assertEqual(ws[f"O{r}"].value, res.rule.relevance, "relevância diferente")
                for (col_v, col_f), year in zip([("G", "J"), ("H", "K"), ("I", "L")], sorted(res.values)):
                    self.assertTrue(same(ws[f"{col_v}{r}"].value, res.values[year]), f"valor {year}")
                    self.assertEqual(ws[f"{col_f}{r}"].value, res.fires[year], f"dispara {year}")
                self.assertEqual(ws[f"M{r}"].value == "Sim", res.alert)
                self.assertEqual(ws[f"N{r}"].value or "", res.years_text)
                self.assertEqual(norm(ws[f"Q{r}"].value), norm(res.evidence), "evidência diferente")
                self.assertEqual(ws[f"V{r}"].value, res.rule.rule_text(), "texto da regra diferente")

    def test_red_flags_order(self):
        ws = self.wb["Red Flags"]
        sheet_ids = [ws[f"B{r}"].value for r in range(6, ws.max_row + 1) if ws[f"B{r}"].value]
        self.assertEqual(sheet_ids, [r.rule.id for r in alerts(self.results)])


if __name__ == "__main__":
    unittest.main()
