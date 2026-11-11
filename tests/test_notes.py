"""The notes to the accounts: read as printed, tied to the statement line behind a finding, never guessed.

Expected figures are the ones printed in the reports (note and page in each test)."""
import io
import unittest

from openpyxl import Workbook

from dd_assistant import demo, notes
from dd_assistant.units import Money


def book(index_rows, sheets) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Index"
    ws.append(["Sheet", "Topic", "Note", "Title as printed", "Page", "Unit", "Status"])
    for r in index_rows:
        ws.append(r)
    for name, unit, header, rows in sheets:
        s = wb.create_sheet(name)
        s.append([f"Note {name}"])
        s.append(["Source: test"])
        s.append([unit])
        s.append([])
        s.append(["Item"] + header)
        for r in rows:
            s.append(r)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


class ReaderTest(unittest.TestCase):
    def setUp(self):
        self.data = book(
            [["N5 Other income", "other_income", 5, "5. Other income", "p.40", "Amounts stated in euros", "read"],
             ["", "leases", "", "", "", "", "not read: not disclosed"]],
            [("N5 Other income", "Amounts stated in euros", ["2025", "2024"],
              [["Grants", 600000, 400000], ["Rents", 300000, "-"], ["Other", 100000, 50000],
               [None, 1000000, 450000], ["Grants relate to a training programme.", None, None]])])
        self.tables = notes.read_notes(self.data)

    def test_tables_units_and_texts(self):
        t = self.tables[0]
        self.assertEqual((t.topic, t.note, t.locator), ("other_income", "5", "note 5 (p.40)"))
        self.assertEqual(t.scale, 0.001)                                # euros -> EUR thousands
        self.assertEqual(t.values(2025), [("Grants", 600.0), ("Rents", 300.0), ("Other", 100.0), ("[Total]", 1000.0)])
        self.assertEqual(t.values(2024)[1], ("Other", 50.0))            # a printed dash is not a figure
        self.assertEqual(t.texts, ["Grants relate to a training programme."])

    def test_a_topic_not_read_stays_not_read(self):
        self.assertEqual(notes.not_read(self.data), [("leases", "not read: not disclosed")])
        ev = notes.explain(self.tables, ("leases",), [500.0], 2025, Money(), "balance")
        self.assertEqual((ev.state, ev.note, ev.text), (notes.OPEN, "", ""))

    def test_explained_when_a_figure_ties(self):
        ev = notes.explain(self.tables, ("other_income",), [1000.0], 2025, Money(), "line")
        self.assertEqual((ev.state, ev.note), (notes.EXPLAINED, "note 5 (p.40)"))
        self.assertIn("Grants €600k, Rents €300k, Other €100k", ev.text)
        self.assertTrue(ev.request)

    def test_partly_when_nothing_ties(self):
        ev = notes.explain(self.tables, ("other_income",), [1234.0], 2025, Money(), "line")
        self.assertEqual(ev.state, notes.PARTLY)
        self.assertIn("no figure in it equals", ev.text)
        self.assertEqual(ev.request, "")

    def test_partly_when_the_largest_line_is_a_residual(self):
        data = book([["N5", "other_income", 5, "5. Other income", "p.40", "thousand euros", "read"]],
                    [("N5", "thousand euros", ["2025"], [["Other", 700], ["Rents", 300], ["Total", 1000]])])
        ev = notes.explain(notes.read_notes(data), ("other_income",), [1000.0], 2025, Money(), "line")
        self.assertEqual(ev.state, notes.PARTLY)
        self.assertIn("residual", ev.text)


class DemoNotesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = {c.slug: demo.analysis(c) for c in demo.CASES}
        cls.issue = lambda cls, slug, key: next(i for i in cls.a[slug].issues if i.key == key)

    def test_every_demo_company_has_its_notes(self):
        for slug, a in self.a.items():
            self.assertGreater(len(a.ext.notes), 20, slug)
            self.assertEqual(a.ext.notes_not_read, [], slug)

    def test_toyota_other_income_is_explained_by_note_33(self):
        """Note 33: Outros rendimentos operacionais 40.035.831 € in 2025, the line of the income statement."""
        i = self.issue("toyota-caetano", "R04")
        self.assertEqual((i.evidence_state, i.evidence_note), (notes.EXPLAINED, "note 33"))
        self.assertIn("€40,036k", i.evidence_text)
        self.assertIn("Recuperação de encargos com garantias e outras despesas operacionais €13,977k", i.evidence_text)
        self.assertIn("Mais-valias na alienação de ativos €4,862k", i.evidence_text)
        self.assertIn("Ledger", i.request)                  # the request moves one level down

    def test_toyota_other_payables_tie_to_the_balance_sheet_line(self):
        """Note 22: Outras dívidas a terceiros, current, 72.707.400 € (Balanço)."""
        i = self.issue("toyota-caetano", "R28")
        self.assertEqual(i.evidence_state, notes.EXPLAINED)
        self.assertIn("'Outras dívidas a terceiros'", i.evidence_text)
        self.assertIn("€72,707k", i.evidence_text)

    def test_tap_provisions_and_leases(self):
        """Note 18 (pp.204–205): sub-total provisions 414,902,016 € at 31 December 2025; redelivery 291,463,620 €."""
        p = self.issue("tap", "ND: Provisions")
        self.assertEqual(p.evidence_state, notes.EXPLAINED)
        self.assertIn("Redelivery costs", p.evidence_text)
        self.assertIn("€291m", p.evidence_text)
        self.assertEqual(self.issue("tap", "ND: Lease liabilities").evidence_note, "note 19 (p.207)")

    def test_amorim_other_income_is_only_partly_explained(self):
        """Note 30: of 17 421, the largest line is an unexplained 'Outros' of 7 051."""
        i = self.issue("corticeira-amorim", "R04")
        self.assertEqual(i.evidence_state, notes.PARTLY)
        self.assertIn("Outros €7,051k", i.evidence_text)

    def test_a_finding_without_a_note_stays_open(self):
        self.assertEqual(self.issue("toyota-caetano", "R10").evidence_state, notes.OPEN)
        self.assertEqual(self.issue("tap", "R18").evidence_state, notes.OPEN)

    def test_material_carries_the_notes_and_the_states(self):
        for c in demo.CASES:
            text = demo.material(c, self.a[c.slug])
            self.assertIn("## 7b. Notes to the accounts", text, c.slug)
            self.assertIn("Evidence from the notes:", text, c.slug)

    def test_without_notes_nothing_is_claimed(self):
        from dd_assistant.dataroom import files_in, read_data_room
        from dd_assistant.pipeline import analyse
        a = analyse(read_data_room(files_in([demo.DATA / "Toyota_Caetano_2025_published.xlsx"])), "automotive", "PT")
        self.assertTrue(all(i.evidence_state == "" for i in a.issues))
        self.assertNotIn("7b. Notes", demo.material(demo.CASE_BY_SLUG["toyota-caetano"], a))


if __name__ == "__main__":
    unittest.main()
