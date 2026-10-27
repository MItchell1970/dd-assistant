"""Real published accounts, copied into Excel as printed (scripts/real_*.py, sources in each file).

The agent must rebuild each company's own EBITDA to the euro (or the dollar), read the right line in the
right section, pass its own reading checks, reconcile the balance sheet and net income, and raise only the
findings a reviewer would expect.
"""
import unittest
from pathlib import Path

from dd_assistant.extract import extract_excel
from dd_assistant.metrics import compute_metrics, reading_checks
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
        checks = reading_checks(self.d)
        self.assertTrue(checks, "no published subtotal to check the reading against")
        self.assertEqual([c for c in checks if not c["OK"]], [], "reading checks")


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


class AppleTest(RealCompany, unittest.TestCase):
    """US GAAP: income statement by function, USD millions, quarters beside the full year, '$' columns."""
    FILE = "Apple_FY2024_published.xlsx"

    def test_company_currency_and_format(self):
        self.assertEqual(self.ext.company, "Apple Inc.")
        self.assertEqual((self.d.currency, self.d.pl_format), ("USD", "function"))
        self.assertIn("USD millions, converted to USD thousands", self.ext.method)

    def test_ebitda_equals_operating_income_plus_depreciation(self):
        # operating income (p.1) + depreciation and amortization from the cash flow statement (p.3), in USD k
        self.assertEbitda({2024: (123216 + 11445) * 1000, 2023: (114301 + 11519) * 1000})

    def test_full_year_not_the_quarter(self):
        self.assertEqual(self.d.v("vendas", 2024), 391035 * 1000)     # twelve months, not the fourth quarter
        self.assertEqual(self.d.v("fin_cp", 2024), (10912 + 9967) * 1000)   # term debt + commercial paper

    def test_below_operating_income_is_not_ebitda(self):
        self.assertIsNone(self.d.lines.get("orend"))                    # 'Other income/(expense), net'

    def test_reconciles(self):
        self.assertReconciles()

    def test_findings(self):
        # R07/R09: receivables +13% and inventories +15% against revenue +2%; R13: restricted cash in the CFS
        self.assertEqual(self.ids, ["R07", "R09", "R13", "R18"])


if __name__ == "__main__":
    unittest.main()
