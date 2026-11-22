"""The net debt definition: presets, switches and the SPA net debt schedule of the databook.

TAP Air Portugal FY2025, EUR thousands, as published in the 2025 Integrated Report (statement of financial position,
p.152): pensions 173,153.669; income tax payable 3,873.215; other financial assets 680.947 (non-current) and
13,178.431 (current); non-current assets held for sale 28,869.179.
"""
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from dd_assistant import deal_layer as dl
from dd_assistant import demo
from dd_assistant import net_debt_definition as ndd
from dd_assistant.databook import control_results, excel_available, recalculate, write_databook
from dd_assistant.extract import CASH_LIKE, DEBT_LIKE, PRESUMED_DEBT


class TapPresetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = demo.analysis(demo.CASE_BY_SLUG["tap"])
        cls.cs = ndd.components(cls.a)

    def test_buyer_is_the_engine(self):
        self.assertAlmostEqual(ndd.net_debt(self.cs, ndd.preset(self.cs, ndd.BUYER)), 2_292_544.633, places=2)
        self.assertAlmostEqual(ndd.net_debt(self.cs, ndd.preset(self.cs, ndd.BUYER)),
                               self.a.view.net_debt_adjusted[2025], places=2)

    def test_seller_leaves_out_pensions_and_tax_and_counts_more_cash(self):
        seller = 2_292_544.633 - 173_153.669 - 3_873.215 - 680.947 - 13_178.431 - 28_869.179
        n = ndd.negotiation(self.cs)
        self.assertAlmostEqual(n.seller, seller, places=2)                 # 2,072,789.192
        self.assertAlmostEqual(n.gap, 2_292_544.633 - seller, places=2)    # 219,755.441 in negotiation

    def test_borrowings_less_cash_when_everything_else_is_out(self):
        only = {c.key: c.group in ("Borrowings", "Cash") for c in self.cs}
        self.assertAlmostEqual(ndd.net_debt(self.cs, only), self.a.view.net_debt_reported[2025], places=2)
        self.assertAlmostEqual(ndd.net_debt(self.cs, only), -42_784.156, places=2)

    def test_a_switch_moves_net_debt_leverage_equity_and_impact(self):
        buyer = ndd.preset(self.cs, ndd.BUYER)
        pensions = next(c.key for c in self.cs if c.group == "Pensions")
        before = ndd.evaluate(self.a, self.cs, buyer, 8.0)
        after = ndd.evaluate(self.a, self.cs, {**buyer, pensions: False}, 8.0)
        self.assertAlmostEqual(before.net_debt - after.net_debt, 173_153.669, places=2)
        self.assertAlmostEqual(after.equity - before.equity, 173_153.669, places=2)
        self.assertAlmostEqual(after.impact - before.impact, 173_153.669, places=2)   # a diligence item less
        self.assertAlmostEqual(after.leverage, after.net_debt / self.a.view.ebitda_dd[2025])
        self.assertEqual(after.ev, before.ev)                                         # EV does not move

    def test_buyer_gives_the_figures_of_the_tool_today(self):
        """The Impact view before this feature: equity view of the engine at 6x, 8x and 10x, for the three cases."""
        for c in demo.CASES:
            a = demo.analysis(c)
            cs = ndd.components(a)
            for m in (6.0, 8.0, 10.0):
                with self.subTest(case=c.slug, multiple=m):
                    r, e = ndd.evaluate(a, cs, ndd.preset(cs, ndd.BUYER), m), dl.equity_view(a, m)
                    self.assertAlmostEqual(r.net_debt, e.net_debt, places=3)
                    self.assertAlmostEqual(r.equity, e.equity, places=3)
                    self.assertAlmostEqual(r.impact, e.impact, places=3)


class RulesTableTest(unittest.TestCase):
    def test_buyer_column_is_the_engine_default(self):
        engine = {category: include for category, _, include in DEBT_LIKE + CASH_LIKE}
        engine[PRESUMED_DEBT] = True
        engine[ndd.MATERIAL_OTHER] = False
        for category, include in engine.items():
            with self.subTest(category=category):
                self.assertIn(category, ndd.RULES)
                self.assertEqual(ndd.RULES[category].buyer, include)

    def test_every_line_has_a_group_and_a_reason(self):
        for category, rule in ndd.RULES.items():
            with self.subTest(category=category):
                self.assertIn(rule.group, ndd.GROUPS)
                self.assertGreater(len(rule.why), 20)


class ScheduleTest(unittest.TestCase):
    """The 'SPA net debt schedule' sheet: the choice and its reason, SUMIFS totals, and Excel = Python."""

    @classmethod
    def setUpClass(cls):
        cls.a = demo.analysis(demo.CASE_BY_SLUG["tap"])
        cs = ndd.components(cls.a)
        chosen = ndd.preset(cs, ndd.BUYER)
        cls.pensions = next(c for c in cs if c.group == "Pensions")
        chosen[cls.pensions.key] = False
        cls.definition = ndd.Definition(ndd.CUSTOM, chosen, [ndd.Change(cls.pensions.key, cls.pensions.label, False,
                                                                        "Seller: service cost already in EBITDA",
                                                                        "2026-11-22 18:00")])
        cls.path = Path(tempfile.mkdtemp()) / "tap_databook.xlsx"
        write_databook(cls.a, cls.path, definition=cls.definition)

    def test_the_sheet_lists_each_component_with_the_choice_and_the_reason(self):
        ws = load_workbook(self.path)["SPA net debt schedule"]
        rows = {}
        for r in range(5, ws.max_row + 1):    # the first row of a label: the schedule (the change log comes below)
            rows.setdefault(ws.cell(r, 1).value, [ws.cell(r, c).value for c in range(2, 9)])
        group, value, source, buyer, seller, choice, reason = rows[self.pensions.label]
        self.assertEqual((group, buyer, seller, choice), ("Pensions", "Yes", "No", "No"))
        self.assertAlmostEqual(value, 173_153.669, places=2)
        self.assertEqual(reason, "Seller: service cost already in EBITDA")
        self.assertTrue(source)
        totals = {ws.cell(r, 1).value: ws.cell(r, 3).value for r in range(5, ws.max_row + 1)}
        self.assertTrue(str(totals["Net debt — buyer's view"]).startswith("=SUMIFS("))
        self.assertIn("Changes made by the analyst", totals)

    @unittest.skipUnless(excel_available(), "needs Microsoft Excel to recalculate")
    def test_excel_equals_python(self):
        recalculate(self.path)
        spa = [c for c in control_results(self.path) if c[0].startswith("SPA net debt")]
        self.assertEqual(len(spa), 3)
        self.assertEqual([c[4] for c in spa], ["OK"] * 3, spa)
        chosen = next(c for c in spa if "chosen" in c[0])
        self.assertAlmostEqual(chosen[2], 2_292_544.633 - 173_153.669, places=2)


if __name__ == "__main__":
    unittest.main()
