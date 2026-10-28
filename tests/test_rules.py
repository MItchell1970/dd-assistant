"""Small tests of the rule logic and formatting, without Excel."""
import unittest

from dd_assistant.rules import RULES, pct, xround

R = {r.id: r for r in RULES}


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

    def test_excel_rounding(self):
        self.assertEqual(xround(2.5, 0), "3")              # Excel rounds half up
        self.assertEqual(xround(15.0, 1), "15")
        self.assertEqual(pct(0.2383), "23.8%")


if __name__ == "__main__":
    unittest.main()
