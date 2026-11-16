"""The static site (site/, built by scripts/build_site.py): every figure on the company parts of the pages exists in
that company's memo material for the year it cites, the verification figures are the ones the code counts now, and
the stored pages are the ones the script builds today."""
import importlib.util
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from dd_assistant import demo
from dd_assistant.memo_check import _check_numbers

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts" / "build_site.py")
build_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_site)


class _Checked(HTMLParser):
    """The text inside each element marked data-check="<slug>", by slug, one block per element (tags and SVG
    titles become line breaks, so a label and its value stay one clause)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.text = [], {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)   # data-nocheck: the chart's "0" and the rounding note, not figures of the accounts
        slug = "" if "data-nocheck" in attrs else attrs.get("data-check")
        self.stack.append((tag, slug))
        if self.current():
            self.text.setdefault(self.current(), []).append("\n")

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop()[0] == tag:
                break

    def handle_data(self, data):
        if self.current() and not any(t == "title" for t, _ in self.stack):
            self.text[self.current()].append(data)

    def current(self):
        if any(s == "" for _, s in self.stack):
            return None
        return next((s for _, s in reversed(self.stack) if s), None)


def checked_text(page: str) -> dict[str, str]:
    p = _Checked()
    p.feed(page)
    return {slug: re.sub(r"[ \t]+", " ", "".join(parts)) for slug, parts in p.text.items()}


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build_site.render()
        cls.material = {c.slug: demo.material(c) for c in demo.CASES}

    def test_pages(self):
        self.assertEqual(set(self.pages), {"index.html", "tap.html", "toyota.html", "amorim.html"})

    def test_every_figure_is_in_the_material(self):
        for name, page in self.pages.items():
            parts = checked_text(page)
            expected = set(demo.CASE_BY_SLUG) if name == "index.html" else \
                {s for s, p in build_site.PAGES.items() if p == name}
            self.assertEqual(set(parts), expected, name)
            for slug, text in parts.items():
                with self.subTest(page=name, company=slug):
                    checked, unmatched, misdated, _ = _check_numbers(text, self.material[slug])
                    self.assertGreater(checked, 3)
                    self.assertEqual((unmatched, misdated), ([], []))

    def test_verification_figures_are_counted_now(self):
        v, d = demo.verification(), demo.detection()
        page = self.pages["index.html"]
        self.assertIn(f">{v['tests']}<", page)
        self.assertIn(f">{v['checks_passed']} of {v['checks']}<", page)
        self.assertIn(f">{d['detected']} of {d['scored']}<", page)
        self.assertIn(f">{v['figures']}<", page)

    def test_downloads_and_images_exist(self):
        for page in self.pages.values():
            for link in re.findall(r'(?:href|src)="((?:files|img)/[^"]+)"', page):
                folder, rest = link.split("/", 1)
                source = ROOT / ("docs/examples" if folder == "files" else "docs/images") / rest
                self.assertTrue(source.exists(), link)

    def test_open_graph_and_no_third_party_requests(self):
        for name, page in self.pages.items():
            with self.subTest(name):
                self.assertIn('property="og:image" content="https://', page)
                self.assertIn('name="twitter:card"', page)
                external = re.findall(r'(?:src|href)="(https?://[^"]+)"', page)
                loaded = [u for u in re.findall(r'<(?:script|img|link)[^>]+(?:src|href)="(https?://[^"]+)"', page)
                          if "fonts.g" not in u and 'rel="canonical"' not in u]
                self.assertEqual([u for u in loaded if not u.startswith(build_site.SITE_URL)], [], name)
                self.assertNotIn("<script", page)
                self.assertTrue(external)

    def test_design_criteria(self):
        """docs/FASE5_DESIGN.md: only the palette (3), no investment wording (7), no table the tool also shows and
        the company page limited to its five blocks (9)."""
        from dd_assistant import charts
        palette = {charts.BG, charts.CARD, charts.TEXT, charts.MUTED, charts.LINE, charts.RED, charts.GREEN}
        for name, page in self.pages.items():
            with self.subTest(name):
                self.assertLessEqual({x.lower() for x in re.findall(r"#[0-9a-fA-F]{6}", page)}, palette)
                visible = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|head)>.*?</>", " ", page, flags=re.S))
                self.assertIsNone(re.search(r"no-go|go|recommend|should buy", visible, re.I))
                self.assertNotIn("<table", page)
                if name != "index.html":
                    self.assertEqual(page.count('class="ddc"'), 1)          # one chart: the net debt bridge
                    self.assertEqual(page.count('class="issue-card"'), 3)   # top three

    def test_stored_site_is_current(self):
        for name, text in self.pages.items():
            with self.subTest(name):
                stored = (SITE / name).read_text(encoding="utf-8")
                self.assertEqual(stored, text, "stored site is stale: run python scripts\\build_site.py")


if __name__ == "__main__":
    unittest.main()
