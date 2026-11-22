"""Mapping a company's own chart of accounts to the model (FICTITIOUS, synthetic test data).

The annual accounts of Duriva are the reference: the ledger, mapped, must give them to the euro in every year. A Low
account never enters on the agent's say: without the reviewer's decision it is left out and the tie shows the gap.
"""
import tempfile
import unittest
from pathlib import Path

from dd_assistant.dataroom import files_in, read_data_room
from dd_assistant.ledger import read_ledger
from dd_assistant.mapping import high_share, map_accounts, mapped_lines, tie_to_accounts
from tests.test_ledger import room_files

DATA = Path(__file__).resolve().parents[1] / "data"
DECISIONS = {"MSC990": {"key": "ogast", "reason": "Miscellaneous operating costs (test decision)"},
             "SUS999": {"key": "exclude", "reason": "Transit account, nil at every month-end (test decision)"}}


class DurivaMappingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = read_ledger(room_files())
        cls.data = read_data_room(files_in([DATA / "Duriva_data_room"])).data

    def tie(self, decisions):
        maps = map_accounts(self.L, decisions)
        lines, _ = mapped_lines(self.L, maps, self.data.years)
        return maps, tie_to_accounts(lines, self.data, self.data.years)

    def test_parity_to_the_euro_in_every_year(self):
        _, checks = self.tie(DECISIONS)
        self.assertEqual(len(checks), 78)          # 11 P&L lines x 3 years, 12 balance sheet lines x 4 year-ends
        self.assertEqual([c for c in checks if not c["OK"]], [])

    def test_at_least_ninety_percent_high(self):
        maps = map_accounts(self.L)
        self.assertGreaterEqual(high_share(maps), 0.90)
        self.assertEqual(sorted((m.series.code, m.confidence) for m in maps if m.confidence != "High"),
                         [("MSC990", "Low"), ("OIN520", "Medium"), ("SUS999", "Low")])

    def test_a_low_account_waits_for_the_reviewer(self):
        maps, checks = self.tie(None)
        pending = [m for m in maps if m.key is None]
        self.assertEqual([m.series.code for m in pending], ["MSC990", "SUS999"])
        self.assertTrue(all(m.status == "Pending the reviewer" for m in pending))
        self.assertEqual([m.suggestion for m in pending], ["ogast", None])     # a nil account suggests nothing
        self.assertIn("balance sheet, nil", pending[1].reason)
        off = {(c["key"], c["Year"]): c["Difference"] for c in checks if not c["OK"]}
        self.assertEqual(off, {("ogast", 2023): 15.0, ("ogast", 2024): 13.5, ("ogast", 2025): 16.5,
                               ("cp", 2023): 15.0, ("cp", 2024): 13.5, ("cp", 2025): 16.5})

    def test_every_account_is_mapped_or_decided(self):
        maps = map_accounts(self.L, DECISIONS)
        self.assertEqual([m.series.code for m in maps if m.key is None and not m.decision], [])
        decided = {m.series.code: (m.status, m.decision["reason"]) for m in maps if m.decision}
        self.assertEqual(decided["SUS999"][0], "Decided by the reviewer (excluded)")
        self.assertIn("test decision", decided["MSC990"][1])

    def test_medium_says_why(self):
        m = next(m for m in map_accounts(self.L) if m.series.code == "OIN520")
        self.assertEqual(m.key, "orend")
        self.assertIn("the words point to Other income and Property, plant and equipment", m.reason)


class MessyVelmoraTest(unittest.TestCase):
    """Velmora, the clean fictitious company, made messy the same way: the ledger gives its accounts to the euro."""

    def test_same_way_same_accounts(self):
        import sys
        sys.path.insert(0, str(DATA.parent / "scripts"))
        from duriva_messy import build
        folder = Path(tempfile.mkdtemp()) / "Velmora_messy"
        build(DATA / "Velmora_data_room.xlsx", folder, "Velmora Material Elétrico, S.A.", planted=False)
        L = read_ledger(room_files(folder))
        data = read_data_room(files_in([DATA / "Velmora_data_room.xlsx"])).data
        maps = map_accounts(L, DECISIONS)
        lines, _ = mapped_lines(L, maps, data.years)
        self.assertEqual([c for c in tie_to_accounts(lines, data, data.years) if not c["OK"]], [])
        self.assertGreaterEqual(high_share(maps), 0.90)


if __name__ == "__main__":
    unittest.main()
