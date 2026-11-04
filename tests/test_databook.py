"""The databook: sheets, inputs vs formulas, text safety, and totals recalculated by Excel equal to Python.

The recalculation tests run only where Excel is installed (Bernardo's PC); elsewhere they are skipped with the
reason, and the Checks sheet keeps saying PENDING.
"""
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

from dd_assistant.databook import _put, adjusted_ebitda, control_results, excel_available, recalculate, write_databook
from dd_assistant.dataroom import files_in, read_data_room
from dd_assistant.pipeline import analyse

DATA = Path(__file__).resolve().parents[1] / "data"
SHEETS = ["Read Me", "Executive Summary", "Source Register", "Financials", "QoE", "NWC", "Net Debt", "EV to Equity",
          "Leakage", "Monthly & LTM", "Issues & Requests", "Checks"]


class QoeCaseTest(unittest.TestCase):
    """Spec phase 2, section 6: reported EBITDA 10; extraordinary expense approved +2; extraordinary income
    approved −1 → 11. Rejecting the +2 → 9. Proposed or needing evidence stays out."""

    def test_spec_case(self):
        ok = "Approved by the analyst"
        self.assertEqual(adjusted_ebitda(10, [(2, ok), (-1, ok)]), 11)
        self.assertEqual(adjusted_ebitda(10, [(2, "Rejected"), (-1, ok)]), 9)
        self.assertEqual(adjusted_ebitda(10, [(2, "Proposed"), (-1, "Needs evidence")]), 10)


class DatabookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.a = analyse(read_data_room(files_in([DATA / "Duriva_data_room"])))
        cls.path = Path(cls.tmp.name) / "duriva.xlsx"
        write_databook(cls.a, cls.path)
        cls.wb = load_workbook(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_sheets_in_order(self):
        self.assertEqual(self.wb.sheetnames, SHEETS)

    def test_totals_are_formulas_and_figures_are_inputs(self):
        qoe = self.wb["QoE"]
        reported = qoe["E5"].value
        self.assertTrue(str(reported).startswith("=Financials!"), reported)
        total = next(r for r in qoe.iter_rows(min_row=5) if str(r[1].value).startswith("Diligence-adjusted EBITDA —"))
        self.assertIn("SUMIFS", total[4].value)
        status = next(r for r in qoe.iter_rows(min_row=6) if str(r[0].value).startswith("QOE-M"))[3]
        self.assertFalse(status.protection.locked)               # the analyst decides here
        self.assertTrue(qoe["E5"].protection.locked)             # a formula is locked
        self.assertTrue(qoe.protection.sheet)

    def test_every_file_has_its_hash(self):
        ws = self.wb["Source Register"]
        hashes = [ws.cell(r, 5).value for r in range(5, 5 + len(self.a.ext.files))]
        self.assertTrue(all(isinstance(h, str) and len(h) == 64 for h in hashes), hashes)

    def test_synthetic_data_is_said(self):
        texts = [str(c.value) for row in self.wb["Read Me"].iter_rows() for c in row if c.value]
        self.assertTrue(any("SYNTHETIC DEMO DATA" in t for t in texts))

    def test_checks_say_pending_until_recalculated(self):
        self.assertTrue(self.wb["Checks"]["B3"].value.startswith("PENDING"))

    def test_requests_are_merged(self):
        ws = self.wb["Issues & Requests"]
        docs = [ws.cell(r, 2).value for r in range(1, ws.max_row + 1)
                if str(ws.cell(r, 1).value or "").startswith("REQ-")]
        self.assertEqual(len(docs), len(set(docs)))               # each request once, with its findings

    def test_text_from_the_data_room_stays_text(self):
        wb = Workbook()
        _put(wb.active, 1, 1, "=HYPERLINK(\"http://example.com\")")
        with tempfile.TemporaryDirectory() as tmp:
            wb.save(Path(tmp) / "t.xlsx")
            cell = load_workbook(Path(tmp) / "t.xlsx")["Sheet"]["A1"]
        self.assertEqual(cell.data_type, "s")


@unittest.skipUnless(excel_available(), "Excel is not installed: the databook is not recalculated here")
class RecalculationTest(unittest.TestCase):
    def test_excel_totals_equal_python(self):
        for name in ("Duriva_data_room", "Toyota_Caetano_2024_published.xlsx"):
            a = analyse(read_data_room(files_in([DATA / name])))
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "book.xlsx"
                write_databook(a, path)
                self.assertTrue(recalculate(path))
                controls = control_results(path)
                self.assertGreaterEqual(len(controls), 5)
                self.assertEqual([c for c in controls if c[4] != "OK"], [], name)
                self.assertTrue(load_workbook(path)["Checks"]["B3"].value.startswith("Recalculated by Microsoft Excel"))

    def test_a_decision_changed_in_the_workbook_flows_to_the_total(self):
        """Approving every management adjustment in the workbook gives the EBITDA Python computes with the same
        decisions: the formulas follow the yellow cells."""
        room = read_data_room(files_in([DATA / "Duriva_data_room"]))
        a = analyse(room)
        approved = analyse(room, decisions={x.name: "Accepted" for x in room.data.adjustments})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book.xlsx"
            write_databook(a, path)
            wb = load_workbook(path)
            qoe = wb["QoE"]
            for row in qoe.iter_rows(min_row=6):
                if str(row[0].value).startswith("QOE-M"):
                    row[3].value = "Approved by the analyst"
            wb.save(path)
            recalculate(path)
            ws = load_workbook(path, data_only=True)["QoE"]
            total = next(r for r in ws.iter_rows(min_row=5) if str(r[1].value).startswith("Diligence-adjusted EBITDA —"))
            L = a.view.pl_years[-1]
            self.assertAlmostEqual(total[4 + len(a.view.pl_years) - 1].value, approved.view.ebitda_dd[L], places=6)
            self.assertNotAlmostEqual(approved.view.ebitda_dd[L], a.view.ebitda_dd[L])


if __name__ == "__main__":
    unittest.main()
