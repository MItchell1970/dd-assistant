"""How far an ESEF reading can be relied on, and the .zip limits that protect the reader.

Packages are the small one of tests/test_esef.py, changed one thing at a time: notes tagged as IFRS text blocks
(Complete), none (Notes missing), a subtotal changed (Reading check failed), the same tag with two figures (a
mis-tagged line). The zip bomb and the unsafe path are built here, in memory.
"""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from openpyxl import load_workbook

from dd_assistant import esef, esef_quality
from dd_assistant.ai_memo import build_material
from dd_assistant.databook import write_databook
from dd_assistant.dataroom import read_data_room
from dd_assistant.extract import PRESUMED_DEBT, ExtractionError
from dd_assistant.pipeline import analyse
from tests.test_esef import _fact, package

BLOCKS = ["DisclosureOfBorrowingsExplanatory", "DisclosureOfProvisionsExplanatory", "DisclosureOfLeasesExplanatory",
          "DisclosureOfRelatedPartyExplanatory", "DisclosureOfOtherOperatingIncomeExplanatory",
          "DisclosureOfEntitysReportableSegmentsExplanatory"]


def with_blocks(names):
    tags = "".join(f'<ix:nonNumeric name="ifrs-full:{n}" contextRef="c-1"><p>Note {i}</p></ix:nonNumeric>'
                   for i, n in enumerate(names, 1))
    return lambda text: text.replace("</body>", f"{tags}</body>")


def analysed(edit=None):
    return analyse(read_data_room([("acme-2025-12-31.zip", package(edit=edit))]))


class LevelsTest(unittest.TestCase):
    def test_complete(self):
        q = analysed(with_blocks(BLOCKS)).quality
        self.assertEqual((q.level, q.headline, q.reasons), ("Complete", "Complete", []))
        self.assertTrue(q.ok)

    def test_notes_missing_names_them(self):
        q = analysed(with_blocks(BLOCKS[:2])).quality
        self.assertEqual(q.headline, "Notes missing: leases, related parties, other income, segments")
        self.assertEqual(q.notes_found, ["borrowings", "provisions"])
        self.assertTrue(q.ok)
        none = analysed().quality
        self.assertIn("tags no note as an IFRS text block", none.reasons[0])

    def test_a_subtotal_that_does_not_close(self):
        swap = lambda t: t.replace(_fact("acme:OperatingResult", "c-1", 1540), _fact("acme:OperatingResult", "c-1", 1640))
        q = analysed(swap).quality
        self.assertEqual(q.level, "Reading check failed, do not rely")
        self.assertFalse(q.ok)
        self.assertTrue(any("FY25" in r and "1,640" in r for r in q.reasons), q.reasons)

    def test_the_same_tag_with_two_figures(self):
        # a second Revenue for FY25, as precise as the first: a line tagged with the wrong concept
        twice = lambda t: t.replace("</table>", f"<tr><td>{_fact('Revenue', 'c-1', 300)}</td></tr></table>")
        q = analysed(twice).quality
        self.assertEqual(q.level, "Reading check failed, do not rely")
        self.assertTrue(any("ifrs-full:Revenue FY25: 300 vs 10040" in r for r in q.reasons), q.reasons)

    def test_a_rounded_duplicate_is_not_a_conflict(self):
        # the fixture already tags revenue as '10.0 million' in the highlights: rounding, not a second figure
        self.assertNotIn("Same tag", " ".join(analysed(with_blocks(BLOCKS)).quality.reasons))

    def test_other_data_rooms_have_no_esef_warning(self):
        a = analyse(read_data_room([("Duriva_data_room.xlsx", Path("data/Duriva_data_room.xlsx").read_bytes())]))
        self.assertIsNone(a.quality)

    def test_a_failure_is_a_warning_with_its_reason(self):
        q = esef_quality.not_analysed("This ESEF report is in USD.")
        self.assertEqual(q.text(), "ESEF data quality: Not analysed. This ESEF report is in USD.")
        self.assertFalse(q.ok)


class WhereItShowsTest(unittest.TestCase):
    def test_memo_material_and_databook(self):
        a = analysed(with_blocks(BLOCKS[:5]))
        material = build_material(a.data, a.metrics, a.results, a.ext.source_text, analysis=a)
        self.assertIn("ESEF data quality: Notes missing: segments.", material)
        path = Path(tempfile.mkdtemp()) / "acme_databook.xlsx"
        write_databook(a, path)
        ws = load_workbook(path)["Read Me"]
        rows = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(1, 30)}
        self.assertTrue(rows["ESEF data quality"].startswith("Notes missing: segments."))


def renamed(package_bytes: bytes, old: str, new: str) -> bytes:
    """The same package with one IFRS concept tagged as another, in the report and the presentation."""
    src = zipfile.ZipFile(io.BytesIO(package_bytes))
    return zipped({n: src.read(n).replace(old.encode(), new.encode()) for n in src.namelist()})


class UnclassifiedFinancialLiabilitiesTest(unittest.TestCase):
    """Short-term debt tagged as 'other current financial liabilities' (Schneider Electric, FY2025) is never left out
    in silence: with no current borrowings line it is presumed debt and included, with its question; the warning
    says no note classifies it."""

    @classmethod
    def setUpClass(cls):
        cls.base = analysed(with_blocks(BLOCKS))
        moved = renamed(package(edit=with_blocks(BLOCKS)), "ShorttermBorrowings", "OtherCurrentFinancialLiabilities")
        cls.a = analyse(read_data_room([("acme-2025-12-31.zip", moved)]))

    def test_presumed_current_debt_is_included(self):
        items = [b for b in self.a.data.balance_items if b.kind == "current" and b.nature == "debt"
                 and b.category == PRESUMED_DEBT]
        self.assertEqual([(b.values[2025], b.include, b.source) for b in items],
                         [(600, True, "ifrs-full:OtherCurrentFinancialLiabilities")])
        self.assertIsNone(self.a.data.v("fin_cp", 2025))
        # the same adjusted net debt as when the line is tagged as borrowings: nothing is lost
        self.assertEqual(self.a.view.net_debt_adjusted[2025], self.base.view.net_debt_adjusted[2025])

    def test_it_comes_with_a_question_and_its_source(self):
        issue = next(i for i in self.a.issues if i.title == PRESUMED_DEBT)
        self.assertEqual((issue.kind, issue.amount, issue.source),
                         ("Net debt item", 600, "ifrs-full:OtherCurrentFinancialLiabilities"))
        self.assertIn("No current borrowings line is presented", issue.question)

    def test_the_warning_drops_to_notes_missing(self):
        q = self.a.quality
        self.assertEqual(q.level, "Notes missing")
        self.assertEqual(q.headline, "Notes missing: classification of other financial liabilities (600 EUR thousands)")
        self.assertIn("presumed current debt", q.reasons[0])
        self.assertEqual(self.base.quality.level, "Complete")

    def test_with_a_current_borrowings_line_they_stay_to_assess(self):
        """Corticeira Amorim FY2025: bank debt on its own line; its other financial liabilities stay to assess."""
        ext = read_data_room([("Corticeira_Amorim_2025_published.xlsx",
                               Path("data/Corticeira_Amorim_2025_published.xlsx").read_bytes())])
        current = [(b.category, b.include) for b in ext.data.balance_items
                   if b.kind == "current" and b.category.endswith("financial liabilities")]
        self.assertEqual(current, [("Other financial liabilities", False)])


def zipped(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


class ZipLimitsTest(unittest.TestCase):
    def test_a_zip_bomb_is_refused(self):
        bomb = zipped({"x/reports/x.xhtml": b"<ix:header>" + b"0" * 30_000_000})   # 30 MB in about 30 KB
        with self.assertRaisesRegex(ExtractionError, "zip bomb"):
            read_data_room([("bomb.zip", bomb)])

    def test_too_large_once_expanded(self):
        with mock.patch.object(esef, "MAX_EXPANDED", 10_000):
            with self.assertRaisesRegex(ExtractionError, "above the 0 MB limit"):
                read_data_room([("acme.zip", package())])

    def test_a_path_out_of_the_folder_is_refused(self):
        evil = zipped({"x/reports/x.xhtml": b"<ix:header>", "../../outside.txt": b"x"})
        with self.assertRaisesRegex(ExtractionError, "unsafe path"):
            read_data_room([("evil.zip", evil)])

    def test_a_normal_package_opens(self):
        self.assertEqual(read_data_room([("acme.zip", package())]).data.v("opinc", 2025), 1540)


if __name__ == "__main__":
    unittest.main()
