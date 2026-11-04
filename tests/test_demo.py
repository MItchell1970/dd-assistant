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
                self.assertEqual(downloads[0], "Download the databook (Excel)")
                self.assertIn("Request list (.md)", downloads)
                text = page_text(at)
                self.assertIn(demo.WARNING, text)
                self.assertNotIn("Claude API: not configured", text)

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


if __name__ == "__main__":
    unittest.main()
