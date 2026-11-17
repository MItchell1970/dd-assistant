"""Bridge charts (dd_assistant/charts.py): one model for the site, the app and the slides. Colour by the effect on
the buyer, at most seven columns with every grouped column keeping its parts, titles and annotations from the
engine's figures (checked against the memo material), and the drawing rules of a deal report."""
import re
import unittest

from dd_assistant import charts, demo
from dd_assistant.memo_check import _check_numbers
from dd_assistant.units import Money


class ModelTest(unittest.TestCase):
    money = Money(millions=True)

    def test_colour_follows_the_buyer_not_the_sign(self):
        steps = [("Borrowings less cash", 100.0, "total"), ("Post-employment benefit obligations", 50.0, "delta"),
                 ("Cash-like item", -20.0, "delta"), ("Adjusted net debt", 130.0, "total")]
        nd = charts.make(steps, self.money, "net debt", "s", "t")
        self.assertEqual([c.effect for c in nd.columns], ["", "worse", "better", ""])
        cash = charts.make([("Reported EBITDA", 100.0, "total"), ("Capex", -50.0, "delta"),
                            ("Change in net working capital", 20.0, "delta"), ("Free cash flow", 70.0, "total")],
                           self.money, "cash", "s", "t")
        self.assertEqual([c.effect for c in cash.columns], ["", "worse", "better", ""])
        self.assertEqual([c.lead for c in cash.columns], [False, True, False, False])   # the largest item

    def test_small_items_go_into_others_and_keep_their_parts(self):
        steps = [("A", 1000.0, "total"), ("x", 5.0, "delta"), ("y", 3.0, "delta"), ("z", 200.0, "delta"),
                 ("B", 1208.0, "total")]
        cols = charts.group(steps)
        others = [c for c in cols if c.label == "Others"]
        self.assertEqual(len(others), 1)
        self.assertEqual(others[0].parts, [("x", 5.0), ("y", 3.0)])
        self.assertEqual(others[0].value, 8.0)

    def test_at_most_seven_columns_and_the_bridge_still_adds_up(self):
        for c in demo.CASES:
            a = demo.analysis(c)
            for kind, b in charts.all_bridges(a).items():
                with self.subTest(company=c.slug, chart=kind):
                    self.assertLessEqual(len(b.columns), charts.MAX_COLUMNS)
                    level = 0.0
                    for col in b.columns:
                        if col.kind == "total":
                            self.assertAlmostEqual(level if col is not b.columns[0] else col.value, col.value,
                                                   delta=0.01)
                            level = col.value
                        else:
                            level += col.value
                            if col.parts:
                                self.assertAlmostEqual(col.value, sum(v for _, v in col.parts), delta=0.001)

    def test_titles_and_annotations_are_figures_of_the_engine(self):
        """The action title and the annotation say the conclusion with figures the memo checker finds in the
        material, for the right year."""
        for c in demo.CASES:
            a = demo.analysis(c)
            material = demo.material(c, a)
            for kind, b in charts.all_bridges(a).items():
                with self.subTest(company=c.slug, chart=kind):
                    checked, unmatched, misdated, _ = _check_numbers(f"{b.title}. {b.annotation}.", material)
                    self.assertGreater(checked, 0)
                    self.assertEqual((unmatched, misdated), ([], []))

    def test_tap(self):
        a = demo.analysis(demo.CASE_BY_SLUG["tap"])
        nd, cash = charts.net_debt(a), charts.cash(a)
        self.assertEqual(nd.title, "Leases, a standard item, explain €2,158m of the €2,293m adjusted net debt; "
                                   "diligence adds €177m")
        self.assertEqual(nd.annotation, "3.16x EBITDA")
        self.assertEqual(nd.note, "Differences of €1m are due to rounding.")    # -43 + 173 + 2,158 + 4 = 2,292
        self.assertEqual(cash.title, "After lease payments, free cash flow is −€272m")
        self.assertIn("Net capex", [c.label for c in cash.columns])


class DrawingTest(unittest.TestCase):
    def setUp(self):
        self.a = demo.analysis(demo.CASE_BY_SLUG["tap"])
        self.b = charts.net_debt(self.a)
        self.html = charts.svg(self.b, self.a.money)

    def test_values_signed_on_items_and_full_names_for_screen_readers(self):
        self.assertIn(">+€2,158m<", self.html)
        self.assertIn(">€2,293m<", self.html)
        self.assertIn('aria-label="Lease liabilities: +€2,158m, standard item, not a finding"', self.html)
        self.assertIn("Income tax payable", self.html)          # the part inside "Others"

    def test_connectors_only_in_the_gaps(self):
        drawings = re.findall(r"<svg.*?</svg>", self.html, re.S)
        self.assertEqual(len(drawings), 2)                       # wide (desktop) and narrow (phone)
        for svg in drawings:
            rects = [(float(x), float(w)) for x, w in re.findall(r'<rect class="[^"]*" x="([\d.]+)" y="[\d.]+" '
                                                                 r'width="(\d+)"', svg)]
            links = [(float(a), float(b)) for a, b in re.findall(r'<line class="link" x1="([\d.]+)" x2="([\d.]+)"',
                                                                 svg)]
            self.assertEqual(len(links), len(rects) - 1)
            for (x0, w0), (x1, _), (l0, l1) in zip(rects, rects[1:], links):
                self.assertAlmostEqual(l0, x0 + w0, places=1)
                self.assertLessEqual(l1, x1 + 0.05)

    def test_wide_drawing_fills_the_card(self):
        """Phase 6: on a desktop the bridge spans the card (viewBox about 1,040 units), not a third of it."""
        wide = re.search(r'ddc-wide"><svg viewBox="0 0 (\d+)', self.html)
        self.assertGreaterEqual(int(wide.group(1)), 900)

    def test_bars_are_wide_and_visible(self):
        heights = [float(h) for h in re.findall(r'<rect [^>]*height="([\d.]+)"', self.html)]
        self.assertTrue(all(h >= 6 for h in heights))
        self.assertIn('width="44"', self.html)                   # 60% of the 74-unit column slot

    def test_baseline_only_with_negative_values(self):
        self.assertIn('class="zero"', self.html)                 # TAP starts at −€43m
        amorim = demo.analysis(demo.CASE_BY_SLUG["corticeira-amorim"])
        self.assertNotIn('class="zero"', charts.svg(charts.net_debt(amorim), amorim.money))

    def test_no_colour_outside_the_palette(self):
        colours = set(re.findall(r"#[0-9a-fA-F]{6}", charts.CSS + self.html))
        self.assertLessEqual(colours, charts.PALETTE)


if __name__ == "__main__":
    unittest.main()
