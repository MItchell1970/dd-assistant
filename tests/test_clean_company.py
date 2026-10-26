"""Alarmes falsos: a Velmora (empresa "limpa") não deve disparar nenhuma regra.

Se mudar um limite ou uma regra e este teste falhar, a mudança criou um alarme falso
numa empresa saudável: confirme se é isso que quer antes de mudar o teste.
Nota: a Velmora foi desenhada por quem conhece as regras; é um teste de sanidade.
"""
import unittest
from pathlib import Path

from dd_assistant.input_loader import load_input
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import alerts, evaluate

TEMPLATE = Path(__file__).resolve().parents[1] / "data" / "DD_template_velmora.xlsx"


class CleanCompanyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_input(TEMPLATE)
        cls.results = evaluate(cls.data, compute_metrics(cls.data))

    def test_no_false_alarms(self):
        fired = [f"{r.rule.id} ({r.years_text})" for r in alerts(self.results)]
        self.assertEqual(fired, [], "alarmes falsos na empresa limpa")

    def test_every_rule_was_tested(self):
        """Zero alertas só vale se todas as regras tiveram valor no último ano (nenhuma 'n.d.')."""
        last = self.data.pl_years[-1]
        untested = [r.rule.id for r in self.results if r.fires[last] == "n.d."]
        self.assertEqual(untested, [])


if __name__ == "__main__":
    unittest.main()
