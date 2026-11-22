"""The databook of the messy Duriva data room (FICTITIOUS) and the manual-against-agent time."""
import re
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from dd_assistant.databook import control_results, excel_available, recalculate, write_databook
from dd_assistant.dataroom import files_in, read_data_room
from dd_assistant.pipeline import analyse
from dd_assistant.timing import MANUAL, manual_minutes
from tests.test_proof_of_cash import DECISIONS, ROOM

ESTIMATE = Path(__file__).resolve().parents[1] / "docs" / "examples" / "duriva-messy" / "manual_estimate.md"


class LedgerDatabookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = analyse(read_data_room(files_in([ROOM]), mapping_decisions=DECISIONS))
        cls.path = Path(tempfile.mkdtemp()) / "duriva_messy_databook.xlsx"
        write_databook(cls.a, cls.path)
        cls.wb = load_workbook(cls.path)

    def test_the_ledger_sheets_are_there(self):
        names = self.wb.sheetnames
        self.assertEqual(names[names.index("Source Register") + 1:names.index("Source Register") + 3],
                         ["Mapping", "Proof of Cash"])
        self.assertIn("FICTITIOUS", self.wb["Mapping"]["A2"].value)
        self.assertIn("FICTITIOUS", self.wb["Proof of Cash"]["A2"].value)

    def test_mapping_rows_say_confidence_status_and_source(self):
        ws = self.wb["Mapping"]
        rows = {ws.cell(r, 1).value: [ws.cell(r, c).value for c in range(2, 9)] for r in range(5, 41)}
        self.assertEqual(rows["MSC990"][3:6], ["Low", "behaviour only", "Decided by the reviewer"])
        self.assertIn("test decision", rows["MSC990"][6])
        self.assertEqual(rows["4120 → 4121"][1:4], ["cli", "Trade receivables", "High"])
        tie = [ws.cell(r, 4).value for r in range(41, ws.max_row + 1) if ws.cell(r, 2).value == "vendas"]
        self.assertTrue(all(str(f).startswith("=SUMIFS(") for f in tie) and len(tie) == 3)

    def test_monthly_and_ltm_has_data_and_formulas(self):
        ws = self.wb["Monthly & LTM"]
        self.assertEqual(ws["A5"].value, "2023-01")
        self.assertEqual(ws["A40"].value, "2025-12")
        self.assertEqual(ws["B42"].value, "=SUM(B29:B40)")

    @unittest.skipUnless(excel_available(), "needs Microsoft Excel to recalculate")
    def test_excel_equals_python_on_every_control(self):
        recalculate(self.path)
        controls = control_results(self.path)
        self.assertEqual(len(controls), 25)
        self.assertEqual([c for c in controls if not str(c[4]).startswith("OK")], [])


class TimingTest(unittest.TestCase):
    def test_the_estimate_in_the_code_is_the_one_fixed_before_the_run(self):
        text = ESTIMATE.read_text(encoding="utf-8")
        self.assertIn("**620 minutes ≈ 10.3 hours**", text)
        self.assertEqual(manual_minutes(), 620)
        minutes = [int(m) for m in re.findall(r"\| (\d+) \|\n", text)]
        self.assertEqual(minutes, [round(t.minutes) for t in MANUAL])


if __name__ == "__main__":
    unittest.main()
