"""Testes pequenos das regras e da formatação, sem precisar do Excel."""
import unittest

from dd_assistant.rules import RULES, pct, xround

R = {r.id: r for r in RULES}


class RuleLogicTest(unittest.TestCase):
    def test_greater_than(self):
        self.assertEqual(R["R01"].fires(0.21), "Sim")
        self.assertEqual(R["R01"].fires(0.20), "Não")      # no limite não dispara

    def test_less_than(self):
        self.assertEqual(R["R10"].fires(0.69), "Sim")
        self.assertEqual(R["R10"].fires(0.70), "Não")

    def test_absolute(self):
        self.assertEqual(R["R03"].fires(-3.5), "Sim")      # queda de margem também conta
        self.assertEqual(R["R03"].fires(2.9), "Não")

    def test_missing_value(self):
        self.assertEqual(R["R07"].fires(None), "n.d.")

    def test_excel_rounding(self):
        self.assertEqual(xround(2.5, 0), "3")              # o Excel arredonda meio para cima
        self.assertEqual(xround(15.0, 1), "15")
        self.assertEqual(pct(0.2383), "23.8%")


if __name__ == "__main__":
    unittest.main()
