"""Deal view: quality of earnings, net debt and working capital bridges, with the reviewer's decisions."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from dd_assistant.__main__ import main
from dd_assistant.deal import deal_view, value_at_stake
from dd_assistant.extract import extract_excel
from dd_assistant.input_loader import Named
from dd_assistant.metrics import compute_metrics
from dd_assistant.pipeline import analyse

DATA = Path(__file__).resolve().parents[1] / "data"
START_UP = "Custos de arranque das novas instalações"


class DurivaQualityOfEarningsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = extract_excel(DATA / "Duriva_data_room.xlsx").data
        cls.m = compute_metrics(cls.d)

    def test_prudent_default(self):
        """Nothing accepted yet: management's €455k of adjustments and the €250k disposal gain are left out."""
        v = deal_view(self.d, self.m)
        self.assertEqual(v.ebitda[2025], 1415)
        self.assertEqual(v.ebitda_mgmt[2025], 1870)
        self.assertEqual(v.ebitda_dd[2025], 1415 - 250)
        self.assertEqual(v.upside[2025], 455)

    def test_reviewer_decisions_and_own_adjustments(self):
        v = deal_view(self.d, self.m, {START_UP: "Accepted", "Custos de reestruturação": "Rejected"},
                      [Named("Owner's salary below market", {2025: -50.0})])
        self.assertEqual(v.ebitda_dd[2025], 1415 + 70 - 250 - 50)
        self.assertEqual(v.upside[2025], 85 + 160)            # still under review; the rejected one is not upside
        labels = [l.label for l in v.qoe]
        self.assertNotIn(f"Reverse: {START_UP}", labels)
        self.assertIn("Owner's salary below market", labels)

    def test_net_debt_and_working_capital(self):
        v = deal_view(self.d, self.m)
        self.assertEqual(v.net_debt_reported[2025], 2400 + 1950 - 603)
        self.assertEqual(v.net_debt_adjusted[2025], v.net_debt_reported[2025])   # no debt-like lines in this data room
        self.assertEqual(v.nwc_values[2025], 3531 + 4222 - 2825 + 350 - 690)
        self.assertEqual(v.nwc_average, sum(v.nwc_values.values()) / 4)          # four year-ends, FY22 to FY25

    def test_value_at_stake(self):
        stake = dict(value_at_stake(deal_view(self.d, self.m), 8))
        self.assertEqual(stake["EBITDA difference × 8x"], (1165 - 1870) * 8)
        self.assertEqual(stake["Equity value at stake"], (1165 - 1870) * 8)


class DebtLikeItemsTest(unittest.TestCase):
    def test_toyota_pensions_and_tax_payable_in_net_debt(self):
        d = extract_excel(DATA / "Toyota_Caetano_2024_published.xlsx").data
        v = deal_view(d, compute_metrics(d))
        found = {b.category: b for b in d.balance_items}
        self.assertTrue(found["Post-employment benefit obligations"].include)
        self.assertTrue(found["Income tax payable"].include)
        self.assertFalse(found["Provisions"].include)                            # to assess: depends on the nature
        self.assertAlmostEqual(v.net_debt_adjusted[2024] - v.net_debt_reported[2024], 215.736 + 6248.948)
        # the tax payable sits in other current liabilities: counted in net debt, it leaves working capital
        excluded = next(l for l in v.nwc if l.label.startswith("Excluded: Imposto sobre o rendimento a pagar"))
        self.assertAlmostEqual(excluded.values[2024], 6248.948)

    def test_reviewer_can_include_an_item_to_assess(self):
        d = extract_excel(DATA / "Toyota_Caetano_2024_published.xlsx").data
        provisions = next(i for i, b in enumerate(d.balance_items) if b.category == "Provisions")
        m = compute_metrics(d)
        gap = deal_view(d, m, include={provisions: True}).net_debt_adjusted[2024] - deal_view(d, m).net_debt_adjusted[2024]
        self.assertAlmostEqual(gap, 3466.893)

    def test_amorim_pensions_and_income_tax_in_net_debt(self):
        d = extract_excel(DATA / "Corticeira_Amorim_2024_published.xlsx").data
        v = deal_view(d, compute_metrics(d))
        self.assertEqual(v.net_debt_reported[2024], 119053 + 153270 - 76636)
        self.assertEqual(v.net_debt_adjusted[2024], v.net_debt_reported[2024] + 3210 + 5012)


class CommandLineTest(unittest.TestCase):
    def test_json_with_a_decision(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as out:
            rc = main([str(DATA / "Duriva_data_room.xlsx"), "--out", tmp, "--json",
                       "--adjustment", "Custos de arranque=Accepted", "--received", "AR ageing"])
            result = json.loads((Path(tmp) / "Duriva_data_room_analysis.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertIn("diligence-adjusted €1,235k", out.getvalue())
        self.assertEqual(result["sector"]["key"], "distribution")
        self.assertTrue(result["reading_checks_ok"])
        self.assertEqual(len(result["findings"]), 15)
        self.assertTrue(result["documents_received"]["AR ageing"])
        status = {a["name"]: a["status"] for a in result["management_adjustments"]}
        self.assertEqual(status[START_UP], "Accepted")

    def test_bad_option_is_explained(self):
        with contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            rc = main([str(DATA / "Duriva_data_room.xlsx"), "--out", tempfile.gettempdir(),
                       "--adjustment", "Nothing like this=Accepted"])
        self.assertEqual(rc, 1)
        self.assertIn("Custos de reestruturação", err.getvalue())


class PipelineTest(unittest.TestCase):
    def test_sector_changes_thresholds_not_figures(self):
        ext = extract_excel(DATA / "Toyota_Caetano_2024_published.xlsx")
        general, auto = analyse(ext, "general"), analyse(ext, "automotive")
        self.assertEqual(general.metrics["ebitda"], auto.metrics["ebitda"])
        r11 = lambda a: next(r for r in a.results if r.rule.id == "R11")
        self.assertEqual((r11(general).rule.limit, r11(auto).rule.limit), (0.40, 0.60))
        self.assertIn("floorplan", r11(auto).rule.calibration)
        self.assertEqual(r11(auto).fires[2023], "Yes")       # 71% of debt due within 12 months still fires


if __name__ == "__main__":
    unittest.main()
