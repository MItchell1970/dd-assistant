"""Demo mode (DD_DEMO=1): three real companies, no upload, no API buttons, no key field, and it runs without the
anthropic library. The stored memo, the databook and the app show the same figures as the engine."""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from dd_assistant import demo

ROOT = Path(__file__).resolve().parents[1]
API_LABELS = ("Write the memo", "Read the statements with Claude")


def app_test(slug: str | None = None):
    from streamlit.testing.v1 import AppTest
    with mock.patch.dict(os.environ, {"DD_DEMO": "1"}):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
        if slug:
            at.query_params["company"] = slug
        return at.run()


def page_text(at) -> str:
    return "\n".join(str(m.value) for m in at.markdown) + "\n".join(str(m.value) for m in at.caption)


class SwitchTest(unittest.TestCase):
    def test_flag(self):
        self.assertTrue(demo.enabled({"DD_DEMO": "1"}, "C:/x"))
        self.assertFalse(demo.enabled({"DD_DEMO": "0"}, "/mount/src/dd-assistant"))
        self.assertFalse(demo.enabled({}, "C:/Users/x/dd-assistant"))

    def test_streamlit_cloud_defaults_to_the_demo(self):
        """A public copy never shows the upload by mistake: on Streamlit Community Cloud the demo is the default."""
        self.assertTrue(demo.enabled({}, "/mount/src/dd-assistant"))

    def test_cases_are_real_published_accounts(self):
        self.assertEqual([c.slug for c in demo.CASES], ["tap", "toyota-caetano", "corticeira-amorim"])
        for c in demo.CASES:
            self.assertTrue(c.path.exists(), c.file)
            self.assertNotIn("Duriva", c.file)
            self.assertNotIn("Velmora", c.file)

    def test_settings_are_the_suggested_ones(self):
        """The demo fixes country and sector; they must be what the engine itself suggests from the accounts."""
        for c in demo.CASES:
            a = demo.analysis(c)
            self.assertEqual((a.country.code, a.sector.key), (c.country, c.sector), c.slug)
            self.assertIs(a.sector, a.suggested, c.slug)
            self.assertTrue(a.checks_ok, c.slug)


class DemoAppTest(unittest.TestCase):
    def test_landing_page(self):
        at = app_test()
        self.assertFalse(at.exception)
        self.assertEqual([b.label for b in at.button], ["Open the analysis"] * 3)
        text = page_text(at)
        self.assertIn(demo.WARNING, text)
        self.assertIn(demo.TAGLINE, text)
        for c in demo.CASES:
            self.assertIn(c.company, text)
        self.assertIn(demo.LINKEDIN, text)
        self.assertFalse(at.get("file_uploader"))

    def test_company_pages(self):
        for c in demo.CASES:
            with self.subTest(c.slug):
                at = app_test(c.slug)
                self.assertFalse(at.exception)
                self.assertFalse(at.get("file_uploader"), "no upload in the demo")
                self.assertFalse(at.get("text_input"), "no key field in the demo")
                labels = [b.label for b in at.button]
                self.assertFalse([x for x in labels if x in API_LABELS], "no API button in the demo")
                self.assertEqual([t.label for t in at.tabs][-1], "Memo")
                downloads = [d.proto.label for d in at.get("download_button")]
                self.assertEqual(downloads[0], "Databook (Excel)")
                self.assertIn("Request list", downloads)
                text = page_text(at)
                self.assertIn(demo.WARNING, text)
                self.assertNotIn("Claude API: not configured", text)
                # net debt card: the ratio sits next to the adjusted figure; borrowings less cash is not "reported"
                self.assertIn("x EBITDA · of which borrowings less cash", text)
                self.assertNotIn("Reported net debt", text)
                self.assertTrue(any("passed" in s.value and "without a source: 0" in s.value for s in at.success),
                                "the Memo tab shows the checker result")

    def test_runs_without_the_anthropic_library(self):
        """The public demo needs no API library: block the import and run the app."""
        code = ("import sys; sys.modules['anthropic'] = None\n"
                "from streamlit.testing.v1 import AppTest\n"
                "at = AppTest.from_file('app.py', default_timeout=180)\n"
                "at.query_params['company'] = 'tap'\n"
                "at.run()\n"
                "assert not at.exception, at.exception\n"
                "assert 'anthropic' not in [m for m in sys.modules if sys.modules[m] is not None]\n"
                "print('OK')\n")
        env = {**os.environ, "DD_DEMO": "1", "PYTHONIOENCODING": "utf-8"}
        env.pop("ANTHROPIC_API_KEY", None)
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                           encoding="utf-8", timeout=300)
        self.assertIn("OK", r.stdout, r.stderr[-2000:])


class SameNumbersTest(unittest.TestCase):
    """The memo, the databook and the app show the figures the engine computes, for each company."""

    def test_stored_memo_passes_the_checker_now(self):
        from dd_assistant.memo_check import report
        for c in demo.CASES:
            with self.subTest(c.slug):
                check = demo.check(c)
                self.assertIsNotNone(check, "memo not stored")
                self.assertTrue(check.ok, report(check))
                self.assertFalse(check.warnings, report(check))
                self.assertGreater(check.numbers_checked, 50)
                self.assertEqual(c.check_path.read_text(encoding="utf-8").strip(), report(check).strip(),
                                 "stored check is stale: run python scripts\\demo_examples.py")

    def test_card_headline_figures_are_in_the_material(self):
        from dd_assistant.memo_check import _check_numbers
        for c in demo.CASES:
            with self.subTest(c.slug):
                checked, unmatched, misdated, _ = _check_numbers(c.headline, demo.material(c))
                self.assertGreater(checked, 0)
                self.assertEqual((unmatched, misdated), ([], []))

    def test_case_note_figures_are_in_the_material(self):
        """The talking points of each case note quote only figures the engine produced, for the right year."""
        from dd_assistant.memo_check import _check_numbers
        for c in demo.CASES:
            with self.subTest(c.slug):
                note = c.case_note_path.read_text(encoding="utf-8")
                points = note[note.index("## Three talking points"):]
                checked, unmatched, misdated, _ = _check_numbers(points, demo.material(c))
                self.assertGreater(checked, 5)
                self.assertEqual((unmatched, misdated), ([], []))

    def test_outside_context_stays_out_of_the_memo(self):
        """The privatisation is context for the visitor only: the memo and its material use the accounts alone."""
        tap = demo.CASE_BY_SLUG["tap"]
        self.assertTrue(tap.context and tap.context_source[1].startswith("https://"))
        for text in (demo.memo(tap), demo.material(tap)):
            for word in ("privatis", "Lufthansa", "Air France"):
                self.assertNotIn(word, text)

    def test_request_list_comes_from_the_memo(self):
        for c in demo.CASES:
            text = demo.request_list(c)
            self.assertTrue(text.startswith("## Information request list"), c.slug)
            self.assertIn("| Related question |", text)
            self.assertNotIn("Notes to improve the template", text)

    def test_stored_databook_equals_the_engine(self):
        """The databook in docs/examples, as recalculated by Excel, gives the engine's EBITDA, net debt and NWC."""
        from openpyxl import load_workbook
        from dd_assistant.databook import control_results
        for c in demo.CASES:
            with self.subTest(c.slug):
                a = demo.analysis(c)
                expected = {"Diligence-adjusted EBITDA": a.view.ebitda_dd, "Adjusted net debt": a.view.net_debt_adjusted,
                            "Net working capital": a.view.nwc_values}
                controls = control_results(c.databook_path)
                self.assertEqual(len(controls), 6)
                for name, year, workbook, _python, status in controls:
                    self.assertTrue(str(status).startswith("OK"), (name, year, status))
                    self.assertAlmostEqual(workbook, expected[name][2000 + int(year[2:])], delta=1, msg=(name, year))
                wb = load_workbook(c.databook_path, data_only=True)
                errors = [(ws.title, x.coordinate) for ws in wb for row in ws.iter_rows() for x in row
                          if isinstance(x.value, str) and x.value.startswith("#") and x.value[-1] in "!?A0"]
                self.assertEqual(errors, [])
                for sheet in ("Financials", "QoE", "NWC", "Net Debt"):
                    self.assertTrue(wb[sheet].freeze_panes, sheet)
                    self.assertIn("EUR thousands", " ".join(str(x.value) for row in wb[sheet].iter_rows(max_row=2)
                                                            for x in row if x.value))

    def test_app_shows_the_memo_figures(self):
        """The headline cards of the app and the stored memo quote the same EBITDA and adjusted net debt."""
        for c in demo.CASES:
            with self.subTest(c.slug):
                a = demo.analysis(c)
                L, B = a.view.pl_years[-1], a.view.bs_years[-1]
                figures = [a.money.fmt(a.view.ebitda_dd[L]), a.money.fmt(a.view.net_debt_adjusted[B])]
                memo = demo.memo(c)
                app = page_text(app_test(c.slug))
                for f in figures:
                    self.assertIn(f, memo)
                    self.assertIn(f, app)


if __name__ == "__main__":
    unittest.main()
