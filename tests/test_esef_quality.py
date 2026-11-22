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
from dd_assistant.extract import ExtractionError
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
