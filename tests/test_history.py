"""Three years from two annual reports: the earlier year comes from the prior report, the years both give keep the
latest comparative, and a line that changed between the two reports is a restatement (R30), never a silent mix."""
import copy
import unittest
from pathlib import Path

from dd_assistant.dataroom import files_in, read_data_room
from dd_assistant.history import POLICY, add_prior_report
from dd_assistant.pipeline import analyse

DATA = Path(__file__).resolve().parents[1] / "data"


def read(name: str):
    return read_data_room(files_in([DATA / name]))


class ThreeYearsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.latest, cls.prior = read("Toyota_Caetano_2025_published.xlsx"), read("Toyota_Caetano_2024_published.xlsx")
        cls.ext = add_prior_report(cls.latest, cls.prior, "Toyota_Caetano_2024_published.xlsx")
        cls.a = analyse(cls.ext, "automotive", "PT")

    def test_three_years(self):
        d = self.ext.data
        self.assertEqual((d.years, d.prior_years, d.overlap_years), ([2023, 2024, 2025], [2023], [2024]))
        self.assertEqual(self.a.view.pl_years, [2023, 2024, 2025])
        self.assertEqual(self.a.view.bs_years, [2023, 2024, 2025])

    def test_earlier_year_is_the_prior_report_and_later_years_the_latest(self):
        d = self.ext.data
        for key in ("vendas", "inv", "fin_cp", "fco"):
            self.assertEqual(d.v(key, 2023), self.prior.data.v(key, 2023), key)
            self.assertEqual(d.v(key, 2024), self.latest.data.v(key, 2024), key)
            self.assertEqual(d.v(key, 2025), self.latest.data.v(key, 2025), key)
        self.assertIn("Toyota_Caetano_2024_published.xlsx", d.prior_sources["vendas"])

    def test_published_figures_of_the_earlier_year(self):
        """FY23 as printed in the 2024 report: operating result 34,170,405 € + D&A 19,681,905 € (DRE)."""
        self.assertAlmostEqual(self.a.view.ebitda[2023], self.prior.data.v("opinc", 2023) - self.prior.data.v("da", 2023),
                               places=3)
        self.assertTrue(self.a.checks_ok)
        self.assertEqual({c["Year"] for c in self.a.checks}, {2023, 2024, 2025})

    def test_debt_like_items_reach_the_earlier_year(self):
        """Adjusted net debt of FY23 includes the FY23 pension and tax payable lines of the prior report."""
        v = self.a.view
        self.assertAlmostEqual(v.net_debt_adjusted[2023] - v.net_debt_reported[2023], 1211.669 + 3333.158, places=3)

    def test_no_restatement_between_these_two_reports(self):
        self.assertEqual(self.ext.data.restatements, [])
        self.assertEqual(self.a.metrics["restated"], {2023: None, 2024: 0, 2025: None})
        self.assertNotIn("R30", [r.rule.id for r in self.a.findings])

    def test_cagr_needs_the_three_years(self):
        m = self.a.metrics
        self.assertAlmostEqual(m["cagr_vendas"][2025], (self.ext.data.v("vendas", 2025) /
                                                        self.ext.data.v("vendas", 2023)) ** 0.5 - 1)
        self.assertIsNone(m["cagr_vendas"][2024])
        two = analyse(self.latest, "automotive", "PT")
        self.assertIsNone(two.metrics["cagr_vendas"][2025])

    def test_review_table_and_text_carry_the_prior_report(self):
        self.assertIn("FY23", self.ext.items[0])
        self.assertIn(POLICY, self.ext.source_text)


class RestatementTest(unittest.TestCase):
    """A prior report that printed other figures for FY24: inventories €5,000k lower, revenue unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.latest = read("Toyota_Caetano_2025_published.xlsx")
        prior = read("Toyota_Caetano_2024_published.xlsx")
        prior.data = copy.deepcopy(prior.data)
        cls.first = prior.data.v("inv", 2024) - 5000
        prior.data.lines["inv"][2024] = cls.first
        prior.data.lines["cli"][2024] += 0.4            # rounding: not a restatement
        cls.ext = add_prior_report(cls.latest, prior, "prior.xlsx")
        cls.a = analyse(cls.ext, "automotive", "PT")

    def test_the_latest_comparative_is_used(self):
        self.assertEqual(self.ext.data.v("inv", 2024), self.latest.data.v("inv", 2024))

    def test_the_restatement_is_recorded_with_both_sources(self):
        rows = self.ext.data.restatements
        self.assertEqual([(r["key"], r["year"]) for r in rows], [("inv", 2024)])
        r = rows[0]
        self.assertEqual((r["as_first_published"], r["as_restated"]), (self.first, self.latest.data.v("inv", 2024)))
        self.assertAlmostEqual(r["difference"], 5000)
        self.assertTrue(r["source_first"] and r["source_latest"])

    def test_r30_fires_with_its_amount(self):
        r30 = next(r for r in self.a.findings if r.rule.id == "R30")
        self.assertEqual(r30.years_text, "FY24")
        self.assertAlmostEqual(r30.amount, 5000)
        self.assertIn("as first published", r30.evidence)
        self.assertIn("prior.xlsx", r30.evidence)
        self.assertEqual(r30.rule.severity, "Low")       # €5,000k is below 1% of revenue (€6,670k)
        self.assertEqual(r30.implication, "Further diligence")

    def test_without_a_prior_report_the_rule_is_not_applicable(self):
        a = analyse(self.latest, "automotive", "PT")
        r30 = next(r for r in a.results if r.rule.id == "R30")
        self.assertEqual(set(r30.fires.values()), {"n/a"})
        clean = analyse(read("Velmora_data_room.xlsx"))
        self.assertNotIn("R30", [r.rule.id for r in clean.findings])

    def test_different_currencies_are_refused(self):
        other = read("Toyota_Caetano_2024_published.xlsx")
        other.data = copy.deepcopy(other.data)
        other.data.currency = "USD"
        with self.assertRaises(ValueError):
            add_prior_report(self.latest, other)


if __name__ == "__main__":
    unittest.main()
