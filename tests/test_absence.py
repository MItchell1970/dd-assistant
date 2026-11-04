"""Absence is not zero: a figure the statements do not give makes the results that depend on it unknown,
says what is missing, and leaves the other results valid (spec phase 2, section 4 and case 'Ausência').

Base case: Velmora (clean company, data/DD_template_velmora.xlsx), FY25: EBITDA €1,449k; the other figures as
in its template. The expected values are written by hand from the template, not taken from the code.
"""
import unittest
from pathlib import Path

from dd_assistant.deal import deal_view
from dd_assistant.extract import apply_edits
from dd_assistant.input_loader import load_input
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import evaluate

VELMORA = Path(__file__).resolve().parents[1] / "data" / "DD_template_velmora.xlsx"


class AbsenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_input(VELMORA)

    def run_with(self, edits):
        d = apply_edits(self.base, edits)
        m = compute_metrics(d)
        return d, m, deal_view(d, m), {r.rule.id: r for r in evaluate(d, m)}

    def test_cash_not_disclosed_blocks_net_debt_only(self):
        d, m, view, rules = self.run_with({"caixa": {2025: None}})
        self.assertIsNone(m["net_debt"][2025])                 # not debt − 0
        self.assertIsNone(view.net_debt_reported[2025])
        self.assertIsNone(view.net_debt_adjusted[2025])
        self.assertTrue(any("FY25 net debt" in n and "cash and cash equivalents" in n for n in view.incomplete))
        self.assertEqual(rules["R21"].fires[2025], "n/a")      # leverage cannot be tested, not passed
        self.assertEqual(rules["R12"].fires[2025], "n/a")      # the balance sheet gap would be the cash itself
        self.assertEqual(m["ebitda"][2025], 1449)              # what does not depend on cash stays valid
        self.assertIsNotNone(view.net_debt_reported[2024])

    def test_receivables_not_found_blocks_working_capital(self):
        _, _, view, _ = self.run_with({"cli": {2025: None}})
        self.assertIsNone(view.nwc_values[2025])
        self.assertIsNone(view.nwc_average)                    # no peg reference from an incomplete series
        self.assertTrue(any("FY25 working capital: trade receivables" in n for n in view.incomplete))
        self.assertIsNotNone(view.nwc_values[2024])

    def test_a_second_borrowings_line_not_presented_is_nil(self):
        d, m, _, _ = self.run_with({"fin_cp": {2025: None}})
        self.assertEqual(m["debt"][2025], d.v("fin_lp", 2025))
        d, m, _, _ = self.run_with({"fin_cp": {2025: None}, "fin_lp": {2025: None}})
        self.assertIsNone(m["debt"][2025])                     # no borrowings line at all: unknown

    def test_free_cash_flow_needs_the_operating_cash_flow(self):
        _, m, _, _ = self.run_with({"fco": {2025: None}})
        self.assertIsNone(m["fcf"][2025])

    def test_working_capital_check_skips_movements_not_presented(self):
        _, m, _, rules = self.run_with({"d_oac": {2025: None}})
        self.assertEqual(rules["R14"].fires[2025], "No")       # compared with nothing, not with a zero movement

    def test_a_complete_analysis_is_unchanged(self):
        _, _, view, _ = self.run_with({})
        self.assertEqual(view.incomplete, [])


if __name__ == "__main__":
    unittest.main()
