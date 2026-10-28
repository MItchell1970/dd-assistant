"""Small tests of the rule logic and formatting, without Excel."""
import unittest
from pathlib import Path

from dd_assistant.extract import apply_edits
from dd_assistant.input_loader import load_input
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import RULES, evaluate, pct, xround

R = {r.id: r for r in RULES}
VELMORA = Path(__file__).resolve().parents[1] / "data" / "DD_template_velmora.xlsx"


class RuleLogicTest(unittest.TestCase):
    def test_greater_than(self):
        self.assertEqual(R["R01"].fires(0.21), "Yes")
        self.assertEqual(R["R01"].fires(0.20), "No")      # at the threshold it does not fire

    def test_less_than(self):
        self.assertEqual(R["R10"].fires(0.69), "Yes")
        self.assertEqual(R["R10"].fires(0.70), "No")

    def test_absolute(self):
        self.assertEqual(R["R03"].fires(-3.5), "Yes")      # a margin fall also counts
        self.assertEqual(R["R03"].fires(2.9), "No")

    def test_missing_value(self):
        self.assertEqual(R["R07"].fires(None), "n/a")

    def test_rules_beyond_the_template(self):
        self.assertEqual(R["R21"].fires(3.6), "Yes")       # leverage above 3.5x
        self.assertEqual(R["R22"].fires(3.9), "Yes")       # interest cover below 4x
        self.assertEqual(R["R24"].fires(0.79), "Yes")      # capex below 80% of D&A in both years
        self.assertEqual(R["R25"].fires(-10.5), "Yes")     # effective tax rate 10.5 pp below the statutory rate
        self.assertEqual(R["R26"].fires(0.05), "No")
        self.assertEqual([r.id for r in RULES if not r.in_template], ["R21", "R22", "R23", "R24", "R25", "R26"])

    def test_every_rule_is_explained(self):
        for r in RULES:
            with self.subTest(rule=r.id):
                self.assertTrue(r.plain.endswith(".") and len(r.plain.split()) <= 25, r.plain)
                self.assertTrue(r.practice)

    def test_graded_rules_say_when_they_are_high(self):
        self.assertIn("High above 25%", R["R04"].rule_text())
        self.assertEqual([r.id for r in RULES if r.grade], ["R04", "R10"])

    def test_excel_rounding(self):
        self.assertEqual(xround(2.5, 0), "3")              # Excel rounds half up
        self.assertEqual(xround(15.0, 1), "15")
        self.assertEqual(pct(0.2383), "23.8%")


class GradedSeverityTest(unittest.TestCase):
    """R04 and R10 are High only when the problem is large or lasting: other income above a quarter of EBITDA;
    cash conversion below 70% over the years analysed together, not in one year only (working capital timing)."""

    @classmethod
    def setUpClass(cls):
        cls.velmora = load_input(VELMORA)            # clean: other income 4.5% of EBITDA, conversion around 90%

    def result(self, rule, edits):
        d = apply_edits(self.velmora, edits)
        return next(r for r in evaluate(d, compute_metrics(d)) if r.rule.id == rule)

    def test_other_income_medium_then_high(self):
        medium = self.result("R04", {"orend": {2025: 250}})        # 250 / 1,634 = 15.3% of EBITDA
        self.assertEqual((medium.alert, medium.rule.severity), (True, "Medium"))
        self.assertIn("15.3% of EBITDA", medium.evidence)
        high = self.result("R04", {"orend": {2025: 600}})          # 600 / 1,984 = 30.2%
        self.assertEqual((high.alert, high.rule.severity), (True, "High"))

    def test_one_weak_year_is_medium_a_weak_period_is_high(self):
        one_year = self.result("R10", {"cgo": {2025: 500}})        # FY25 34.5%; the three years 71.5%
        self.assertEqual((one_year.years_text, one_year.rule.severity), ("FY25", "Medium"))
        self.assertIn("the years analysed together: 71.5%", one_year.evidence)
        lasting = self.result("R10", {"cgo": {2025: 300}})         # FY25 20.7%; the three years 66.7%
        self.assertEqual(lasting.rule.severity, "High")


if __name__ == "__main__":
    unittest.main()
