"""Real published accounts, copied into Excel as printed (scripts/real_*.py, sources in each file).

The agent must rebuild each company's own EBITDA to the euro, read the right line in the right section,
reconcile the balance sheet and net income, and raise only the findings a reviewer would expect.
"""
import unittest
from pathlib import Path

from dd_assistant.extract import extract_excel
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import alerts, evaluate

DATA = Path(__file__).resolve().parents[1] / "data"


class RealCompany:
    FILE: str

    @classmethod
    def setUpClass(cls):
        cls.ext = extract_excel(DATA / cls.FILE, cls.FILE)
        cls.d = cls.ext.data
        cls.m = compute_metrics(cls.d)
        cls.ids = [r.rule.id for r in alerts(evaluate(cls.d, cls.m))]

    def assertEbitda(self, published: dict):
        for year, value in published.items():
            self.assertAlmostEqual(self.m["ebitda"][year], value, places=3, msg=f"EBITDA {year}")

    def assertReconciles(self):
        for year in self.d.pl_years:
            self.assertLessEqual(abs(self.m["bs_diff"][year]), 1, f"balance sheet {year}")   # published rounding
            self.assertEqual(self.m["ni_diff"][year], 0, f"net income {year}")


class ToyotaCaetanoTest(RealCompany, unittest.TestCase):
    FILE = "Toyota_Caetano_2024_published.xlsx"

    def test_company_and_unit(self):
        self.assertEqual(self.ext.company, "Toyota Caetano Portugal, S.A.")
        self.assertIn("euros, converted to EUR thousands", self.ext.method)

    def test_ebitda_equals_operating_result_plus_depreciation(self):
        # annual report p.87: operating result + depreciation and amortisation, in EUR thousands
        self.assertEbitda({2024: (46509139 + 28125353) / 1000, 2023: (36859922 + 16992177) / 1000})

    def test_lines_in_the_right_section(self):
        self.assertAlmostEqual(self.d.v("cli", 2024), 81055.758)       # current receivables, not the non-current 13
        self.assertAlmostEqual(self.d.v("fin_lp", 2024), 47544.798)
        self.assertAlmostEqual(self.d.v("fin_cp", 2024), 28332.494)
        self.assertAlmostEqual(self.d.v("vendas", 2024), 658170.307)    # sales + services rendered

    def test_reconciles(self):
        self.assertReconciles()

    def test_findings(self):
        self.assertEqual(self.ids, ["R04", "R10", "R11", "R18"])


class CorticeiraAmorimTest(RealCompany, unittest.TestCase):
    FILE = "Corticeira_Amorim_2024_published.xlsx"

    def test_company_and_unit(self):
        self.assertEqual(self.ext.company, "Corticeira Amorim, S.G.P.S., S.A.")
        self.assertIn("EUR thousands", self.ext.method)

    def test_ebitda_equals_operating_profit_before_depreciation(self):
        self.assertEbitda({2024: 157566, 2023: 176985})                 # annual report p.376

    def test_duplicated_labels_split_by_subtotals(self):
        self.assertEqual(self.d.v("fin_lp", 2024), 119053)              # 'Interest-bearing loans', non-current
        self.assertEqual(self.d.v("fin_cp", 2024), 153270)              # 'Interest-bearing loans', current
        self.assertEqual(self.d.v("rl_grupo", 2024), 69699)

    def test_reconciles(self):
        self.assertReconciles()

    def test_findings(self):
        # R13: cash flow statement cash is net of bank overdrafts; the finding asks for the reconciliation
        self.assertEqual(self.ids, ["R04", "R10", "R11", "R13", "R18"])


if __name__ == "__main__":
    unittest.main()
