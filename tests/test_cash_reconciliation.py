"""R13: a cash difference explained by an identified line is a reconciliation, not a red flag.

Under IFRS the cash flow statement may show cash net of bank overdrafts (IAS 7.8); under US GAAP it includes
restricted cash. When the difference equals such a line, it is shown as a reconciled memo line; when nothing
explains it, R13 fires as before. Cases built by hand on Velmora (clean company).
"""
import io
import unittest
from pathlib import Path

from openpyxl import Workbook

from dd_assistant.deal import deal_view
from dd_assistant.extract import apply_edits, extract_excel
from dd_assistant.input_loader import BalanceItem, load_input
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import evaluate

VELMORA = Path(__file__).resolve().parents[1] / "data" / "DD_template_velmora.xlsx"


class CashReconciliationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_input(VELMORA)
        cls.cash = cls.base.v("caixa", 2025)

    def r13(self, d):
        m = compute_metrics(d)
        return m, next(r for r in evaluate(d, m) if r.rule.id == "R13")

    def test_overdrafts_explain_the_difference(self):
        d = apply_edits(self.base, {"cx_fim": {2025: self.cash - 30}, "desc": {2025: 30}})
        m, r13 = self.r13(d)
        self.assertEqual(m["cash_diff"][2025], -30)
        self.assertEqual(m["cash_diff_unexpl"][2025], 0)
        self.assertFalse(r13.alert)
        self.assertIn("bank overdrafts", m["cash_recon"][2025])
        memo = [line for line in deal_view(d, m).net_debt if "reconciled" in line.label]
        self.assertEqual(memo[0].values, {2025: -30})

    def test_an_unexplained_difference_still_fires(self):
        d = apply_edits(self.base, {"cx_fim": {2025: self.cash - 30}})
        _, r13 = self.r13(d)
        self.assertEqual((r13.alert, r13.values[2025]), (True, -30))
        d = apply_edits(self.base, {"cx_fim": {2025: self.cash - 30}, "desc": {2025: 20}})   # explains only part
        self.assertTrue(self.r13(d)[1].alert)

    def test_a_small_error_leaves_only_the_remainder_unexplained(self):
        """Overdrafts of 30,000 explain all but 2 of the difference: R13 fires on the 2, not on the 30,002."""
        d = apply_edits(self.base, {"cx_fim": {2025: self.cash - 30002}, "desc": {2025: 30000}})
        m, r13 = self.r13(d)
        self.assertEqual(m["cash_diff"][2025], -30002)
        self.assertAlmostEqual(m["cash_diff_unexpl"][2025], -2)
        self.assertTrue(r13.alert)
        self.assertIn("remainder is not explained", m["cash_recon"][2025])

    def test_a_line_that_explains_too_little_explains_nothing(self):
        """Overdrafts of 20 against a difference of 30: a third is left over, so the whole difference stands."""
        d = apply_edits(self.base, {"cx_fim": {2025: self.cash - 30}, "desc": {2025: 20}})
        m, r13 = self.r13(d)
        self.assertEqual(m["cash_diff_unexpl"][2025], -30)
        self.assertTrue(r13.alert)

    def test_restricted_cash_included_in_the_cash_flow_statement(self):
        d = apply_edits(self.base, {"cx_fim": {2025: self.cash + 12}})
        d.balance_items = [BalanceItem("Restricted cash", "Restricted cash", "cash", "current", {2025: 12}, "BS!B9",
                                       False)]
        m, r13 = self.r13(d)
        self.assertFalse(r13.alert)
        self.assertIn("restricted cash", m["cash_recon"][2025])

    def test_overdrafts_are_read_from_the_cash_note(self):
        wb = Workbook()
        pl = wb.active
        pl.title = "Income statement"
        for row in (["EUR thousands", 2024, 2025], ["Revenue", 1000, 1100], ["Staff costs", -200, -210]):
            pl.append(row)
        bs = wb.create_sheet("Balance sheet")
        for row in (["EUR thousands", 2024, 2025], ["Cash and cash equivalents", 90, 100], ["Total assets", 90, 100],
                    ["Total equity", 50, 65], ["Borrowings", 40, 35], ["Total equity and liabilities", 90, 100]):
            bs.append(row)
        cf = wb.create_sheet("Cash flow")
        for row in (["EUR thousands", 2024, 2025], ["Net cash from operating activities", 30, 15],
                    ["Cash and cash equivalents at end of period", 50, 65]):
            cf.append(row)
        note = wb.create_sheet("Note 19 Cash")
        for row in (["EUR thousands", 2024, 2025], ["Cash and bank deposits", 90, 100],
                    ["Bank overdrafts", -40, -35], ["Cash in the cash flow statement", 50, 65]):
            note.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        d = extract_excel(buf, "group.xlsx").data
        self.assertEqual(d.lines["desc"], {2024: 40, 2025: 35})
        self.assertEqual(d.sources["desc"], "Note 19 Cash!B3:C3")
        m, r13 = self.r13(d)                               # 65 − 100 = −35, the overdrafts of FY25
        self.assertEqual((m["cash_diff"][2025], m["cash_diff_unexpl"][2025], r13.alert), (-35, 0, False))


if __name__ == "__main__":
    unittest.main()
