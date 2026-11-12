"""The Red Flag Report in slides: nine slides, titles that state the conclusion with engine figures, native charts
whose bars are the engine's bridge steps, and no figure that is not in the memo material."""
import io
import unittest

from dd_assistant import demo
from dd_assistant.deal import cash_steps, net_debt_steps
from dd_assistant.memo_check import _check_numbers
from dd_assistant.slides import requests, titles

try:
    from pptx import Presentation
    from dd_assistant.slides import write_slides
except ImportError:      # python-pptx is a tool for producing the deck (requirements-dev.txt)
    Presentation = None


def deck(case):
    a = demo.analysis(case)
    out = io.BytesIO()
    write_slides(a, out, case.company, case.pages)
    return a, Presentation(io.BytesIO(out.getvalue()))


def words(prs) -> list[str]:
    out = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                out.append(shape.text_frame.text)
            if getattr(shape, "has_table", False) and shape.has_table:
                out += [cell.text for row in shape.table.rows for cell in row.cells]
            if getattr(shape, "has_chart", False) and shape.has_chart:
                out += [str(c) for c in shape.chart.plots[0].categories]
    return out


@unittest.skipIf(Presentation is None, "python-pptx not installed")
class SlidesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decks = {c.slug: deck(c) for c in demo.CASES}

    def test_nine_slides_with_source_in_the_footer(self):
        for c in demo.CASES:
            _, prs = self.decks[c.slug]
            self.assertEqual(len(prs.slides), 9, c.slug)
            for slide in list(prs.slides)[1:]:
                text = " ".join(s.text_frame.text for s in slide.shapes if s.has_text_frame)
                self.assertIn(f"Source: {c.pages}", text)
                self.assertIn("Preliminary: for an analyst to review", text)

    def test_titles_state_the_conclusion(self):
        a, prs = self.decks["tap"]
        t = titles(a)
        self.assertEqual(t[5], "Adjusted net debt is €2,293m (3.16x EBITDA), against borrowings less cash of -€43m")
        self.assertEqual(t[4], "EBITDA is €726m in FY25; after lease payments it is €262m")
        shown = [s.shapes[0].text_frame.text for s in list(prs.slides)[1:8]]
        self.assertEqual(shown[:6], [t[n] for n in range(2, 8)])
        amorim, _ = self.decks["corticeira-amorim"]
        self.assertIn("exceeded EBITDA", titles(amorim)[7])

    def test_every_figure_is_in_the_material(self):
        for c in demo.CASES:
            a, prs = self.decks[c.slug]
            text = "\n".join(words(prs))
            checked, unmatched, misdated, _ = _check_numbers(text, demo.material(c, a))
            self.assertGreater(checked, 60, c.slug)
            self.assertEqual((unmatched, misdated), ([], []), c.slug)

    def test_charts_are_native_and_carry_the_engine_steps(self):
        a, prs = self.decks["tap"]
        charts = [s.chart for slide in prs.slides for s in slide.shapes if getattr(s, "has_chart", False) and s.has_chart]
        self.assertEqual(len(charts), 4)                       # EBITDA, net debt, working capital, cash flow
        B, L = a.view.bs_years[-1], a.view.pl_years[-1]
        net_debt = [str(c) for c in charts[1].plots[0].categories]
        self.assertEqual(len(net_debt), len(net_debt_steps(a.view, B)))
        self.assertIn("+€2,158m", net_debt[2])
        cash = [str(c) for c in charts[3].plots[0].categories]
        self.assertEqual(len(cash), len(cash_steps(a.view, a.data, a.metrics, L)))
        self.assertTrue(cash[-1].endswith("-€272m"))

    def test_requests_are_the_next_level_and_not_repeated(self):
        a, _ = self.decks["toyota-caetano"]
        docs = [doc for doc, _ in requests(a)]
        self.assertEqual(len(docs), len(set(docs)))
        self.assertLessEqual(len(docs), 10)
        self.assertTrue(any("named in the note" in doc for doc in docs))

    def test_stored_decks_exist_for_the_demo(self):
        for c in demo.CASES:
            self.assertTrue(c.slides_path.exists(), f"run python scripts\\demo_examples.py ({c.slug})")
            self.assertEqual(len(Presentation(str(c.slides_path)).slides), 9)


class CashBridgeTest(unittest.TestCase):
    def test_bridge_reconciles_to_the_cash_flow_statement(self):
        """EBITDA plus every step is the free cash flow of the metrics; operating cash flow is the published one."""
        for c in demo.CASES:
            a = demo.analysis(c)
            for y in a.view.pl_years[1:]:
                steps = cash_steps(a.view, a.data, a.metrics, y)
                got = dict((label, value) for label, value, _ in steps)
                self.assertAlmostEqual(got["Operating cash flow"], a.data.v("fco", y), places=6)
                self.assertAlmostEqual(got["Free cash flow"], a.metrics["fcf"][y], places=6)
                before_ocf = [v for label, v, kind in steps[1:steps.index(("Operating cash flow", got["Operating cash flow"], "total"))]]
                self.assertAlmostEqual(got["Reported EBITDA"] + sum(before_ocf), got["Operating cash flow"], places=6)

    def test_missing_cash_flow_gives_no_bridge(self):
        import copy
        c = demo.CASES[0]
        a = demo.analysis(c)
        d = copy.deepcopy(a.data)
        d.lines["fco"][a.view.pl_years[-1]] = None
        self.assertEqual(cash_steps(a.view, d, a.metrics, a.view.pl_years[-1]), [])


if __name__ == "__main__":
    unittest.main()
