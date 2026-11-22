"""Proof of cash and the messy data room read whole (FICTITIOUS, synthetic test data).

The three distortions planted in the messy Duriva room must be found: their answer key is written by the generator
OUTSIDE the project folder (../Duriva_messy_gabarito.json); the test that reads it is skipped when it is not there.
The original Duriva answer key (Duriva_gabarito.xlsx) also stays outside: give its path in DD_GABARITO to run that
test too. Without either key, the same detections are tested against the clean Duriva and the messy Velmora.
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

from dd_assistant.dataroom import files_in, read_data_room
from dd_assistant.pipeline import analyse

ROOT = Path(__file__).resolve().parents[1]
ROOM = ROOT / "data" / "Duriva_messy_data_room"
DECISIONS = {"MSC990": {"key": "ogast", "reason": "Miscellaneous operating costs (test decision)"},
             "SUS999": {"key": "exclude", "reason": "Transit account, nil at every month-end (test decision)"}}
MESSY_KEY = ROOT.parent / "Duriva_messy_gabarito.json"


def found(a) -> list[tuple]:
    return sorted((r.rule.id, r.years_text, r.rule.severity) for r in a.findings)


class MessyDurivaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ext = read_data_room(files_in([ROOM]), mapping_decisions=DECISIONS)
        cls.a = analyse(cls.ext)
        cls.room = cls.ext.ledger_room
        cls.proof = cls.room.proof

    def test_every_statement_rolls_forward(self):
        self.assertEqual(len(self.proof.months), 72)                 # two banks, 36 months
        self.assertTrue(all(m.rolls for m in self.proof.months))

    def test_the_two_cash_differences_and_what_they_look_like(self):
        d = [(x.account, x.ym, x.amount, x.looks_like.split(":")[0]) for x in self.proof.differences]
        self.assertEqual(d, [("BNK001", (2025, 9), 258000.0, "a receipt recorded in the ledger that is not in the bank"),
                             ("BNK002", (2025, 11), 232000.0,
                              "an inter-bank transfer of 232,000.00 in the statement that month, counted twice in "
                              "the ledger")])
        off = [(r["month"], r["difference"]) for r in self.proof.receipts if abs(r["difference"]) > 1]
        self.assertEqual(off, [((2025, 9), -258000.0)])               # the receipt is missing in the bank too

    def test_the_supplier_listing_does_not_add_up(self):
        self.assertEqual([(s["year"], s["difference"]) for s in self.proof.suppliers], [(2024, 0.0), (2025, -227000.0)])

    def test_the_findings_are_those_of_the_clean_duriva_plus_the_proof_of_cash(self):
        clean = analyse(read_data_room(files_in([ROOT / "data" / "Duriva_data_room"])))
        extra = [f for f in found(self.a) if f not in found(clean)]
        self.assertEqual(extra, [("R31", "FY25", "High"), ("R32", "FY25", "Medium")])
        self.assertEqual([f for f in found(clean) if f not in found(self.a)], [])
        r31 = next(r for r in self.a.findings if r.rule.id == "R31")
        self.assertEqual(r31.values[2025], 490.0)
        self.assertIn("Banco Meridiano (BNK001), 2025-09", r31.evidence)
        self.assertTrue(r31.material)

    def test_figures_come_from_the_ledger_with_file_and_row(self):
        self.assertTrue(self.room.ties_ok)
        self.assertTrue(self.a.data.sources["forn"].startswith("Ledger: 221100 (ERP - exportações mensais/Balancete "
                                                               "2025-12.xlsx › row 37)"))
        self.assertIn("Messy data room", self.ext.method)

    def test_monthly_data_gives_the_peg_and_the_ltm(self):
        memo = {l.label.split(" (")[0]: l.values for l in self.a.view.nwc + self.a.view.qoe if l.style == "memo"}
        self.assertIn("Average of the last 12 month-ends", memo)
        self.assertEqual(memo["Memo: LTM revenue to 2025-12"][2025], 21400.0)
        self.assertEqual(memo["Memo: LTM EBITDA to 2025-12"][2025], self.a.metrics["ebitda"][2025])

    @unittest.skipUnless(MESSY_KEY.exists(), "the answer key of the messy room is not on this computer")
    def test_against_the_answer_key_kept_outside_the_project(self):
        key = json.loads(MESSY_KEY.read_text(encoding="utf-8"))
        cash = {(x.account, x.ym, x.amount) for x in self.proof.differences}
        for d in key["distortions"]:
            with self.subTest(d["what"]):
                if d["where"] == "AP":
                    self.assertIn((d["year"], -d["amount_eur"]), {(s["year"], s["difference"])
                                                                   for s in self.proof.suppliers})
                else:
                    self.assertIn((d["where"], (d["year"], d["month"]), d["amount_eur"]), cash)

    def test_without_the_reviewer_nothing_enters_in_silence(self):
        ext = read_data_room(files_in([ROOM]))
        room = ext.ledger_room
        self.assertEqual([m.series.code for m in room.pending], ["MSC990", "SUS999"])
        self.assertFalse(room.ties_ok)
        self.assertIn("2 pending", ext.method)


class OriginalAnswerKeyTest(unittest.TestCase):
    """The planted issues of Duriva, from its answer key kept outside the project (path in DD_GABARITO)."""

    @unittest.skipUnless(os.environ.get("DD_GABARITO") and Path(os.environ["DD_GABARITO"]).exists(),
                         "Duriva_gabarito.xlsx is not on this computer (set DD_GABARITO to its path)")
    def test_every_planted_rule_is_found_through_the_messy_room(self):
        from openpyxl import load_workbook
        wb = load_workbook(os.environ["DD_GABARITO"], read_only=True, data_only=True)
        ids = sorted({m for ws in wb for row in ws.iter_rows(values_only=True) for c in row if c
                      for m in re.findall(r"\bR\d{2}\b", str(c))})
        a = analyse(read_data_room(files_in([ROOM]), mapping_decisions=DECISIONS))
        self.assertEqual([i for i in ids if i not in {r.rule.id for r in a.findings}], [])


class MessyVelmoraTest(unittest.TestCase):
    """The clean company made messy the same way, with nothing planted: no difference, no finding."""

    def test_no_difference_no_alarm(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from duriva_messy import build
        folder = Path(tempfile.mkdtemp()) / "Velmora_messy"
        build(ROOT / "data" / "Velmora_data_room.xlsx", folder, "Velmora Material Elétrico, S.A.", planted=False)
        a = analyse(read_data_room(files_in([folder]), mapping_decisions=DECISIONS))
        proof = a.ext.ledger_room.proof
        self.assertEqual(proof.differences, [])
        self.assertEqual([r for r in proof.receipts if abs(r["difference"]) > 1], [])
        self.assertTrue(all(s["difference"] == 0 for s in proof.suppliers))
        # zero analytical alarms; R18 (documents not provided) is information, and the same on the clean data room
        self.assertEqual([r.rule.id for r in a.findings if r.rule.id != "R18"], [])
        self.assertEqual({r.rule.id: r.fires[2025] for r in a.results if r.rule.id in ("R31", "R32")},
                         {"R31": "No", "R32": "No"})


if __name__ == "__main__":
    unittest.main()
