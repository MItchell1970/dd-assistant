"""Price mechanism: the acceptance cases of docs/FASE2_SPEC.md, section 6. Expected values are those written in
the spec, by hand; none comes from the functions tested."""
import unittest
from datetime import date

from dd_assistant.price import (INSUFFICIENT, CompletionAccounts, EnterpriseValue, LeakageItem, LockedBox,
                                completion_equity, locked_box_equity, sensitivity, ticking_fee)


def base(nwc=12):
    return CompletionAccounts(EnterpriseValue(100), cash=8, debt=30, debt_like=4, nwc=nwc, peg=10)


class CompletionAccountsTest(unittest.TestCase):
    def test_spec_case(self):
        """EV 100; eligible cash 8; financial debt 30; additional debt-like 4; NWC 12; peg 10 → equity 76;
        net debt with debt-like 26; nothing counted twice."""
        r = completion_equity(base())
        self.assertEqual(r["equity"], 76)
        self.assertEqual(r["net_debt_with_debt_like"], 26)
        self.assertEqual(sum(x for _, x in r["lines"]), 76)            # the lines add up to equity: no part twice

    def test_nwc_below_the_peg(self):
        self.assertEqual(completion_equity(base(nwc=8))["equity"], 72)

    def test_a_missing_figure_blocks_the_price(self):
        c = base()
        c.peg = None
        r = completion_equity(c)
        self.assertIsNone(r["equity"])
        self.assertEqual(r["incomplete"], ["NWC at closing or the peg"])

    def test_negative_net_debt_and_negative_nwc_are_legitimate(self):
        c = CompletionAccounts(EnterpriseValue(100), cash=40, debt=10, nwc=-5, peg=-3)
        r = completion_equity(c)
        self.assertEqual((r["net_debt_with_debt_like"], r["equity"]), (-30, 128))   # 100 + 40 − 10 − 2

    def test_other_adjustments_carry_their_sign(self):
        c = base()
        c.other = [("Transaction bonus to managers", -1.5)]
        self.assertEqual(completion_equity(c)["equity"], 74.5)


class EnterpriseValueTest(unittest.TestCase):
    def test_fixed_ev_does_not_move_with_ebitda(self):
        self.assertEqual(EnterpriseValue(100, multiple=8, ebitda=20).amount(), 100)
        self.assertIsNone(sensitivity(EnterpriseValue(100), net_debt=26))

    def test_derived_ev_shows_the_relation(self):
        ev = EnterpriseValue(multiple=8, ebitda=12.5)
        self.assertEqual(ev.amount(), 100)
        grid = sensitivity(ev, net_debt=26, nwc_adj=2)
        self.assertEqual(grid[0][1:], [7, 8, 9])
        self.assertEqual(grid[2][2], 76)                                # base: 8 × 12.5 − 26 + 2


class LockedBoxTest(unittest.TestCase):
    def test_spec_case_before_leakage(self):
        """Agreed equity 75; contractual value accrual 1 → 76 before leakage."""
        r = locked_box_equity(LockedBox(75, accrual=1))
        self.assertEqual((r["equity_before_leakage"], r["equity"]), (76, 76))

    def test_no_true_up_of_nwc(self):
        """Changing NWC afterwards gives no true-up: the locked box has no NWC input at all."""
        self.assertFalse(hasattr(LockedBox(75), "nwc"))

    def test_leakage_deducted_at_closing(self):
        """Confirmed leakage 0.4 to be compensated, deducted at closing → 75.6."""
        lb = LockedBox(75, accrual=1, leakage=[LeakageItem("LK-01", "Dividend after the locked box", 0.4,
                                                           status="Confirmed after review")])
        r = locked_box_equity(lb)
        self.assertAlmostEqual(r["equity"], 75.6)
        self.assertEqual(r["leakage_claim"], 0)

    def test_leakage_as_a_separate_claim(self):
        """Same leakage as a separate claim → price 76 and claim 0.4, no double deduction."""
        lb = LockedBox(75, accrual=1, treatment="Separate claim",
                       leakage=[LeakageItem("LK-01", "Dividend after the locked box", 0.4,
                                            status="Confirmed after review")])
        r = locked_box_equity(lb)
        self.assertEqual((r["equity"], r["leakage_claim"], r["leakage_deducted"]), (76, 0.4, 0))

    def test_a_candidate_is_not_leakage(self):
        lb = LockedBox(75, leakage=[LeakageItem("LK-01", "Payment to a related party", 3)])
        r = locked_box_equity(lb)
        self.assertEqual((r["equity"], r["candidates"]), (75, 1))
        self.assertEqual(r["conclusion"], INSUFFICIENT)                 # no verdict without the SPA

    def test_ticking_fee(self):
        lb = LockedBox(75, locked_box_date=date(2025, 12, 31), closing_date=date(2026, 3, 31), ticking_rate=0.05,
                       ticking_base=75)
        self.assertAlmostEqual(ticking_fee(lb), 75 * 0.05 * 90 / 365)


if __name__ == "__main__":
    unittest.main()
