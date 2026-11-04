"""Memo checker: must catch invented figures, missing findings and investment recommendations."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from dd_assistant.__main__ import main
from dd_assistant.ai_memo import build_material
from dd_assistant.extract import extract_excel
from dd_assistant.memo_check import _readings, check_memo
from dd_assistant.metrics import compute_metrics
from dd_assistant.pipeline import analyse
from dd_assistant.rules import alerts, evaluate

DATA = Path(__file__).resolve().parents[1] / "data"
DATA_ROOM = DATA / "Duriva_data_room.xlsx"

# A short, correct memo: every figure comes from Duriva's material, in several formats.
GOOD = """# Duriva — preliminary memo

Reported EBITDA fell from €1,640k to €1,415k; excluding the disposal gain it would be €1 165k (R19, R04).
Adjustments are 32.2% of reported EBITDA (R05, R06). Revenue grew 9,2%; customer A is 23.8% (R01, R02, R03).
Cash conversion was 20.5% (R10, R07, R09). 55.2% of debt is due within 12 months, of €4.35m in total (R11, R20).
The FY24 cash flow statement differs from the balance sheet by €85k (R13, R14). Documents are missing (R18).
Net debt / EBITDA is 2.65x against a 3x limit.

| Evidence (finding and source) | What it may indicate | Question for management |
|---|---|---|
| Other income of €310k in FY25 (R04). | A one-off item. | Please provide a breakdown of other income. |

## Information request list

| # | Area | Request | Related question | Findings | Priority |
|---|---|---|---|---|---|
| 17 | Quality of earnings | Other income ledger | Please provide a breakdown of other income for FY25. | R04 | High |
"""


class MemoCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ext = extract_excel(DATA_ROOM, DATA_ROOM.name)
        m = compute_metrics(ext.data)
        cls.results = evaluate(ext.data, m)
        cls.ids = [r.rule.id for r in alerts(cls.results)]
        cls.material = build_material(ext.data, m, cls.results, ext.source_text)

    def check(self, memo):
        return check_memo(memo, self.material, self.ids)

    def test_good_memo_passes(self):
        c = self.check(GOOD)
        self.assertTrue(c.ok, c.errors)
        self.assertEqual(c.warnings, [])
        self.assertGreater(c.numbers_checked, 10)

    def test_invented_figure_is_an_error(self):
        c = self.check(GOOD + "\nNormalised EBITDA would be €9,876k.\n")
        self.assertFalse(c.ok)
        self.assertEqual([n for n, _ in c.unmatched_numbers], ["9,876"])

    def test_missing_finding_is_an_error(self):
        c = self.check(GOOD.replace("R20", ""))
        self.assertEqual(c.missing_alerts, ["R20"])
        self.assertFalse(c.ok)

    def test_investment_recommendation_is_an_error(self):
        c = self.check(GOOD + "\nWe recommend proceeding with the acquisition.\n")
        self.assertEqual(c.recommendations, ["We recommend proceeding with the acquisition"])

    def test_question_without_request_is_a_warning(self):
        memo = GOOD.replace("| A one-off item. | Please provide a breakdown of other income. |",
                            "| A one-off item. | Please provide a breakdown of other income. |\n"
                            "| Impairment of €160k (R05). | Recurring cost. | Why did the company change auditors? |")
        c = self.check(memo)
        self.assertTrue(c.ok)                                   # only a warning
        self.assertEqual(c.orphan_questions, ["Why did the company change auditors?"])

    def test_missing_request_list_is_an_error(self):
        c = self.check(GOOD.split("## Information request list")[0])
        self.assertFalse(c.request_list_found)
        self.assertFalse(c.ok)

    def test_years_small_numbers_and_index_column_are_not_data(self):
        c = self.check("In 2025, the 3 themes and the 15 findings in FY25.\n\n| # | Related question |\n|---|---|\n| 17 | x? |\n")
        self.assertEqual(c.numbers_checked, 1)                  # only the 15

    def test_long_sentence_is_a_warning(self):
        c = self.check(GOOD + "\n" + " ".join(["word"] * 30) + ".\n")
        self.assertEqual(len(c.long_sentences), 1)

    def test_number_formats(self):
        self.assertEqual(_readings("23,8"), [(23.8, 1)])
        self.assertEqual(_readings("20.5"), [(20.5, 1)])
        self.assertEqual(_readings("1,415"), [(1415.0, 0), (1.415, 3)])    # thousands (en) or decimal (pt)
        self.assertEqual(_readings("1.415"), [(1415.0, 0), (1.415, 3)])    # thousands (pt) or decimal (en)
        self.assertEqual(_readings("21,400.5"), [(21400.5, 1)])
        self.assertEqual(_readings("1 415"), [(1415.0, 0)])
        self.assertEqual(_readings("−114"), [(-114.0, 0)])


class PeriodTest(unittest.TestCase):
    """A figure counts as sourced only for the period cited next to it. Toyota's other income was €27,739k in
    FY23 and €34,747k in FY24 (published income statement, DRE row 8): the FY23 figure cited as FY24 fails."""

    @classmethod
    def setUpClass(cls):
        def material(name):   # as the app and the command line build it, with the deal view
            a = analyse(extract_excel(DATA / name, name))
            return build_material(a.data, a.metrics, a.results, a.ext.source_text, analysis=a)
        cls.toyota = material("Toyota_Caetano_2024_published.xlsx")
        cls.amorim = material("Corticeira_Amorim_2024_published.xlsx")

    def test_a_figure_from_another_year_fails(self):
        c = check_memo("Other income was €27,739k in FY24.", self.toyota, [])
        self.assertEqual([n for n, _, _ in c.misdated_numbers], ["27,739"])
        self.assertIn("FY23 value", c.misdated_numbers[0][2])

    def test_the_right_years_pass(self):
        c = check_memo("Other income was €34,747k in FY24 and €27,739k in FY23. In FY23 other income was €27,739k. "
                       "Cash conversion was 84.2% in FY24, -23.9% in FY23. FY24 operating cash flow: €62,857k.",
                       self.toyota, [])
        self.assertEqual((c.unmatched_numbers, c.misdated_numbers), ([], []))

    def test_the_amorim_example_memo_cites_every_period_right(self):
        memo = (DATA.parent / "docs" / "examples" / "Corticeira_Amorim_FY2024_memo.md").read_text(encoding="utf-8")
        c = check_memo(memo, self.amorim, [])
        self.assertGreater(c.numbers_checked, 50)
        self.assertEqual((c.unmatched_numbers, c.misdated_numbers, c.other_line_numbers), ([], [], []))


class CheckMemoCliTest(unittest.TestCase):
    def run_cli(self, memo_text):
        with tempfile.TemporaryDirectory() as tmp:
            memo = Path(tmp) / "memo.md"
            memo.write_text(memo_text, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = main([str(DATA_ROOM), "--check-memo", str(memo), "--out", tmp])
            report = (Path(tmp) / "memo_check.md").read_text(encoding="utf-8")
        return rc, out.getvalue(), report

    def test_good_memo_exit_code_0(self):
        rc, out, report = self.run_cli(GOOD)
        self.assertEqual(rc, 0)
        self.assertIn("Automatic memo check: passed", out)
        self.assertIn("passed", report)

    def test_bad_memo_exit_code_1(self):
        rc, _, report = self.run_cli(GOOD + "\nNormalised EBITDA would be €9,876k.\n")
        self.assertEqual(rc, 1)
        self.assertIn("9,876", report)


if __name__ == "__main__":
    unittest.main()
