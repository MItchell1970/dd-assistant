"""The detection benchmark and the review sheet: the published numbers are the ones a rerun gives, misses included.

The benchmark does not assert a detection rate: it asserts that docs/DETECTION.md is what the script produces now,
that nothing was dropped from the denominator, and that the published files are never changed."""
import hashlib
import sys
import unittest
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import detection_benchmark as bench  # noqa: E402
import review_sheet  # noqa: E402

from dd_assistant import demo  # noqa: E402
from dd_assistant.rules import RULES  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = [c.path for c in demo.CASES] + [demo.DATA / c.prior for c in demo.CASES if c.prior]
        cls.before = {f: digest(f) for f in cls.files}
        cls.rows = bench.run()
        cls.summary = bench.summary(cls.rows)

    def test_published_files_are_untouched(self):
        self.assertEqual({f: digest(f) for f in self.files}, self.before)
        base = demo.analysis(demo.CASES[0])                 # and the cached reading is not mutated either
        self.assertTrue(base.checks_ok)

    def test_every_mutation_names_a_real_expectation(self):
        ids = {r.id for r in RULES}
        for m in bench.MUTATIONS:
            self.assertTrue(m.control or m.expected == bench.READING or m.expected in ids, m.key)
            self.assertEqual(m.control, m.expected == "", m.key)
        self.assertEqual(len({m.key for m in bench.MUTATIONS}), len(bench.MUTATIONS))

    def test_nothing_leaves_the_denominator(self):
        s = self.summary
        planted = [m for m in bench.MUTATIONS if not m.control]
        self.assertEqual(s["planted"], len(planted) * len(demo.CASES))
        self.assertEqual(s["detected"] + s["missed"] + s["already_flagged"] + s["not_applicable"], s["planted"])
        self.assertEqual(s["scored"], s["detected"] + s["missed"])

    def test_stored_report_is_current(self):
        stored = (ROOT / "docs" / "DETECTION.md").read_text(encoding="utf-8")
        self.assertEqual(stored.strip(), bench.markdown(self.rows).strip(),
                         "docs/DETECTION.md is stale: run python scripts\\detection_benchmark.py")

    def test_misses_are_listed(self):
        text = bench.markdown(self.rows)
        for r in self.rows:
            if r["result"] in ("missed", "false alert"):
                self.assertIn(f"**{r['company']}, {r['mutation']}**", text)

    def test_demo_reads_the_published_numbers(self):
        d = demo.detection()
        self.assertEqual((d["detected"], d["scored"]), (self.summary["detected"], self.summary["scored"]))


class ReviewSheetTest(unittest.TestCase):
    def test_every_finding_has_a_proposal_and_no_decision_is_prefilled(self):
        rows = review_sheet.rows()
        findings = [r for r in rows if r[2] == "Finding"]
        self.assertEqual(len(findings), sum(len(demo.analysis(c).findings) for c in demo.CASES))
        for r in findings:
            self.assertIn(r[11], (review_sheet.TRUE, review_sheet.REVIEW), (r[0], r[1]))
            self.assertTrue(r[12])
        self.assertTrue(all(r[13] is None and r[14] is None for r in rows), "the reviewer's columns start empty")

    def test_stored_sheet_matches(self):
        ws = load_workbook(review_sheet.OUT)["Review"]
        stored = [(r[0], r[1]) for r in ws.iter_rows(min_row=5, values_only=True) if r[0]]
        self.assertEqual(stored, [(r[0], r[1]) for r in review_sheet.rows()],
                         "docs/REVIEW_SHEET.xlsx is stale: run python scripts\\review_sheet.py")


if __name__ == "__main__":
    unittest.main()
