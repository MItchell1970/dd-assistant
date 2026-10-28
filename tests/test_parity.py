"""Parity test: Python must give exactly the same numbers as the Excel template.

Reads the values already calculated by Excel (Métricas, Regras and Red Flags sheets) and
compares them with what the code calculates from the Input sheet. Runs on both sample
companies: Duriva (planted issues) and Velmora (clean company).

What is compared: every metric, every rule value, whether each rule fires, the thresholds,
the severities and the order of the findings. What is not compared: the wording of the
evidence and of the rule names, because the code writes them in English while the
reference spreadsheet stays in Portuguese; and the rules and metrics beyond the template
(R21–R26, metrics.EXTENDED_LABELS), which have no reference in the spreadsheet and are
tested in tests/test_rules.py.

Run:  python -m unittest -v
Note: the template must have been saved by a program that calculates formulas (Excel or
LibreOffice); if the calculated cells are empty, the test is skipped with a message.
"""
from __future__ import annotations

import math
import unittest
from pathlib import Path

from openpyxl import load_workbook

from dd_assistant.input_loader import load_input
from dd_assistant.metrics import LABELS, compute_metrics
from dd_assistant.rules import RULES, alerts, evaluate

TEMPLATE_RULES = [r for r in RULES if r.in_template]

DATA = Path(__file__).resolve().parents[1] / "data"
YEAR_COLS = {"B": 2022, "C": 2023, "D": 2024, "E": 2025}

# Metric key -> column A label in the template's Métricas sheet (Portuguese).
SHEET_LABELS = {
    "vendas": "Vendas", "g_vendas": "Crescimento das vendas", "new_sales": "Vendas a clientes novos",
    "new_share": "Clientes novos (% das vendas)", "new_name": "Maior cliente novo",
    "g_ex_new": "Crescimento das vendas sem clientes novos", "top_share": "Maior cliente (% das vendas)",
    "top_name": "Maior cliente", "ex_top_new": "Vendas sem o maior cliente e sem clientes novos",
    "g_ex_top_new": "Crescimento das vendas sem o maior cliente e sem novos", "gm": "Margem bruta",
    "gm_pp": "Variação da margem bruta", "ebitda": "EBITDA reportado", "ebitda_m": "Margem EBITDA",
    "or_share": "Outros rendimentos (% das vendas)", "or_ebitda": "Outros rendimentos (% do EBITDA)",
    "or_var": "Variação dos outros rendimentos",
    "gain": "Ganhos na alienação de ativos (dentro do EBITDA)", "gain_pct": "Ganhos na alienação (% do EBITDA)",
    "ebitda_ex_gain": "EBITDA sem ganhos na alienação", "adj": "Ajustes da gestão ao EBITDA",
    "ebitda_adj": "EBITDA ajustado (gestão)", "adj_pct": "Ajustes (% do EBITDA reportado)",
    "adj_rec": "Ajustes 'não recorrentes' presentes nos 3 anos", "adj_rec_name": "Exemplo de ajuste repetido",
    "g_cli": "Crescimento de clientes (contas a receber)", "cli_gap": "Clientes vs. vendas (diferença de crescimento)",
    "dso": "DSO (prazo médio de recebimento)", "dso_var": "Variação do DSO", "g_inv": "Crescimento dos inventários",
    "g_cmv": "Crescimento do CMV", "inv_gap": "Inventários vs. CMV (diferença de crescimento)",
    "dio": "DIO (dias de stock)", "dpo": "DPO (prazo médio de pagamento)", "dpo_var": "Variação do DPO",
    "cgo": "Caixa gerada pelas operações", "conv": "Conversão de caixa",
    "conv_cum": "Conversão de caixa acumulada (anos analisados)", "fco": "Fluxo de caixa operacional (FCO)",
    "fcf": "Free cash flow", "capex_pct": "Capex (% das vendas)", "debt": "Dívida financeira",
    "st_share": "Dívida a vencer em 12 meses (% do total)", "net_debt": "Dívida líquida",
    "nd_ebitda": "Dívida líquida / EBITDA", "nd_ebitda_ex": "Dívida líquida / EBITDA sem ganhos na alienação",
    "cov_lim": "Limite do covenant (dívida líquida / EBITDA)", "cov_head": "Folga do covenant",
    "ebitda_min": "EBITDA mínimo para cumprir o covenant", "bs_diff": "Ativo − (capital próprio + passivo)",
    "cash_diff": "Caixa final da DFC − caixa do balanço", "wc_diff": "Variações de capital de giro: DFC vs. balanço",
    "ni_diff": "Resultado líquido: maior diferença DRE / balanço / DFC", "cl_diff": "Vendas por cliente − vendas da DRE",
    "map_diff": "Mapa da dívida − balanço", "docs_miss": "Documentos obrigatórios em falta",
    "docs_list": "Lista de documentos em falta",
}
SEVERITY = {"Alta": "High", "Média": "Medium", "Baixa": "Low"}
FIRES = {"Sim": "Yes", "Não": "No", "n.d.": "n/a"}


def same(a, b) -> bool:
    """Compare a spreadsheet value with a Python one ('n.d.' and blank = None)."""
    a = None if a in ("n.d.", "", None) else a
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return str(a) == str(b)


class Parity:
    """The parity tests; each subclass names the template (not a TestCase on its own)."""
    TEMPLATE: Path

    @classmethod
    def setUpClass(cls):
        cls.data = load_input(cls.TEMPLATE)
        cls.metrics = compute_metrics(cls.data)
        cls.results = [r for r in evaluate(cls.data, cls.metrics) if r.rule.in_template]
        cls.wb = load_workbook(cls.TEMPLATE, data_only=True)
        if cls.wb["Métricas"]["C6"].value is None:
            raise unittest.SkipTest("The template has no calculated values: open it in Excel and save it.")

    def test_every_metric_has_a_sheet_label(self):
        self.assertEqual(set(SHEET_LABELS), set(LABELS))

    def test_metrics_match_sheet(self):
        ws = self.wb["Métricas"]
        rows = {}
        for r in range(5, ws.max_row + 1):
            label = ws[f"A{r}"].value
            if label in SHEET_LABELS.values() and label not in rows:
                rows[label] = r
        missing = [l for l in SHEET_LABELS.values() if l not in rows]
        self.assertEqual(missing, [], "metrics without a row in the Métricas sheet")
        for key, label in SHEET_LABELS.items():
            for col, year in YEAR_COLS.items():
                sheet = ws[f"{col}{rows[label]}"].value
                py = self.metrics[key].get(year)
                if key == "docs_list":          # document names: Portuguese in the sheet, English in the code
                    continue
                with self.subTest(metric=label, year=year):
                    self.assertTrue(same(sheet, py), f"sheet={sheet!r}  python={py!r}")

    def test_rules_match_sheet(self):
        ws = self.wb["Regras"]
        by_id = {ws[f"A{r}"].value: r for r in range(5, ws.max_row + 1) if ws[f"A{r}"].value}
        self.assertEqual(sorted(by_id), sorted(r.id for r in TEMPLATE_RULES), "rule catalogue differs from the sheet")
        for res in self.results:
            r = by_id[res.rule.id]
            with self.subTest(rule=res.rule.id):
                self.assertTrue(same(ws[f"F{r}"].value, res.rule.limit), "different threshold")
                self.assertEqual(SEVERITY[ws[f"O{r}"].value], res.rule.severity, "different severity")
                for (col_v, col_f), year in zip([("G", "J"), ("H", "K"), ("I", "L")], sorted(res.values)):
                    self.assertTrue(same(ws[f"{col_v}{r}"].value, res.values[year]), f"value {year}")
                    self.assertEqual(FIRES[ws[f"{col_f}{r}"].value], res.fires[year], f"fires {year}")
                self.assertEqual(ws[f"M{r}"].value == "Sim", res.alert)

    def test_red_flags_order(self):
        ws = self.wb["Red Flags"]
        sheet_ids = [ws[f"B{r}"].value for r in range(6, ws.max_row + 1) if ws[f"B{r}"].value]
        self.assertEqual(sheet_ids, [r.rule.id for r in alerts(self.results)])


class DurivaParityTest(Parity, unittest.TestCase):
    TEMPLATE = DATA / "DD_template_modulo1.xlsx"


class VelmoraParityTest(Parity, unittest.TestCase):
    TEMPLATE = DATA / "DD_template_velmora.xlsx"


if __name__ == "__main__":
    unittest.main()
