"""Alarmes falsos: a Velmora (empresa "limpa") não deve disparar nenhuma regra.

Se mudar um limite ou uma regra e este teste falhar, a mudança criou um alarme falso
numa empresa saudável: confirme se é isso que quer antes de mudar o teste.
Nota: a Velmora foi desenhada por quem conhece as regras; é um teste de sanidade.
"""
import unittest
from pathlib import Path

from dd_assistant import sectors
from dd_assistant.extract import extract_excel
from dd_assistant.input_loader import load_input
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import alerts, evaluate

DATA = Path(__file__).resolve().parents[1] / "data"
TEMPLATE = DATA / "DD_template_velmora.xlsx"


class CleanCompanyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_input(TEMPLATE)
        cls.results = evaluate(cls.data, compute_metrics(cls.data))

    def test_no_false_alarms(self):
        fired = [f"{r.rule.id} ({r.years_text})" for r in alerts(self.results)]
        self.assertEqual(fired, [], "alarmes falsos na empresa limpa")

    def test_every_rule_was_tested(self):
        """Zero alertas só vale se todas as regras tiveram valor no último ano (nenhuma "n/a")."""
        last = self.data.pl_years[-1]
        untested = [r.rule.id for r in self.results if r.fires[last] == "n/a"]
        self.assertEqual(untested, [])

    def test_no_false_alarms_with_its_sector_thresholds(self):
        """Sector calibration must not create alarms either: Velmora is a distributor (suggested from the file)."""
        ext = extract_excel(DATA / "Velmora_data_room.xlsx")
        sector, _ = sectors.suggest(ext.source_text, ext.company)
        self.assertEqual(sector.key, "distribution")
        fired = [r.rule.id for r in alerts(evaluate(self.data, compute_metrics(self.data), sector=sector))]
        self.assertEqual(fired, [], "alarmes falsos com os limites do setor")


if __name__ == "__main__":
    unittest.main()
