"""Materiality, the amount at stake of each finding, the single list of key issues and the deal implication.

Expected amounts are worked by hand from the published statements (cells quoted), not taken from the engine."""
import io
import unittest
from pathlib import Path

from openpyxl import load_workbook

from dd_assistant import demo, issues
from dd_assistant.dataroom import files_in, read_data_room
from dd_assistant.pipeline import analyse

ROOT = Path(__file__).resolve().parents[1]


def run(path: str, **kw):
    return analyse(read_data_room(files_in([ROOT / "data" / path])), **kw)


class TapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = demo.analysis(demo.CASE_BY_SLUG["tap"])
        cls.by_key = {i.key: i for i in cls.a.issues}

    def test_thresholds(self):
        """5% of reported EBITDA (725,810.631) and 1% of revenue (4,270,948.846), EUR thousands."""
        self.assertAlmostEqual(self.a.thresholds["pl"], 0.05 * 725810.631, places=2)
        self.assertAlmostEqual(self.a.thresholds["bs"], 0.01 * 4270948.846, places=2)

    def test_leases_come_first(self):
        """The four lease liability lines of the balance sheet (C44, C45, C50, C51) are the largest issue."""
        first = self.a.issues[0]
        self.assertEqual((first.key, first.kind, first.implication), ("ND: Lease liabilities", "Net debt item",
                                                                      "Price: net debt"))
        self.assertAlmostEqual(first.amount, 742539.672 + 1033575.276 + 117102.021 + 265084.936, places=3)

    def test_receivables_amount(self):
        """R07: customers of 372,247.352 against 305,984.780 grown at the revenue rate (4,270,948.846 /
        4,220,120.062): the excess is about €62.6m, above 1% of revenue, so the finding stays High."""
        r07 = self.by_key["R07"]
        expected = 372247.352 - 305984.780 * (4270948.846 / 4220120.062)
        self.assertAlmostEqual(r07.amount, expected, places=2)
        self.assertTrue(r07.material)
        self.assertEqual((r07.severity, r07.implication), ("High", "Price: working capital / peg"))
        self.assertLess(self.a.issues.index(r07), len(self.a.issues))
        self.assertGreater(self.a.issues.index(r07), self.a.issues.index(self.by_key["R22"]))

    def test_interest_and_small_items(self):
        self.assertAlmostEqual(self.by_key["R22"].amount, 195726.548, places=3)       # Income statement!C26
        tax = self.by_key["ND: Income tax payable"]                                    # Financial position!C53
        self.assertAlmostEqual(tax.amount, 3873.215, places=3)
        self.assertFalse(tax.material)
        self.assertIn(issues.BELOW, tax.note)

    def test_documents_are_not_quantifiable_and_last(self):
        last = self.a.issues[-1]
        self.assertEqual((last.key, last.amount, last.amount_label), ("R18", None, issues.NOT_QUANTIFIABLE))

    def test_order_is_by_amount(self):
        amounts = [i.amount for i in self.a.issues if i.amount is not None]
        self.assertEqual(amounts, sorted(amounts, reverse=True))
        self.assertEqual([r.rule.id for r in self.a.findings],
                         [i.key for i in self.a.issues if i.kind == "Finding"])

    def test_r28_lines_are_not_listed_twice(self):
        self.assertIn("R28", self.by_key)
        self.assertFalse([k for k in self.by_key if "Material 'other' line" in k])


class MaterialityTest(unittest.TestCase):
    def test_below_materiality_becomes_low(self):
        """Duriva: the cash difference of R13 (€85k) is below 1% of revenue (€214k): Medium in the rule, Low here."""
        a = run("Duriva_data_room")
        r13 = next(r for r in a.findings if r.rule.id == "R13")
        self.assertEqual((r13.base_severity, r13.rule.severity, r13.material), ("Medium", "Low", False))
        self.assertIn(issues.BELOW, r13.note)

    def test_a_high_finding_needs_a_material_amount(self):
        for path in ("Duriva_data_room", "TAP_2025_published.xlsx", "Toyota_Caetano_2025_published.xlsx"):
            for r in run(path).findings:
                if r.rule.severity == "High":
                    self.assertIsNot(r.material, False, (path, r.rule.id))

    def test_threshold_is_editable(self):
        """With a 30% threshold on revenue, Duriva's receivables finding (R07, €528k) is no longer material."""
        strict = run("Duriva_data_room", materiality=issues.Materiality(0.05, 0.30))
        r07 = next(r for r in strict.findings if r.rule.id == "R07")
        self.assertEqual((r07.base_severity, r07.rule.severity), ("High", "Low"))
        zero = run("Duriva_data_room", materiality=issues.Materiality(0.0, 0.0))
        self.assertFalse([r for r in zero.findings if r.note])

    def test_the_rules_themselves_do_not_change(self):
        """Materiality sits above the rules: evaluate() still gives the template's severities (parity)."""
        from dd_assistant.metrics import compute_metrics
        from dd_assistant.rules import evaluate
        a = run("Duriva_data_room")
        raw = {r.rule.id: r.rule.severity for r in evaluate(a.data, compute_metrics(a.data), sector=a.sector)}
        for r in a.findings:
            self.assertEqual(r.base_severity, raw[r.rule.id])

    def test_clean_company_has_no_analytical_issue(self):
        a = run("Velmora_data_room.xlsx")
        self.assertEqual([i.key for i in a.issues if i.kind == "Finding"], ["R18"])


class ImplicationTest(unittest.TestCase):
    def test_every_rule_has_an_amount_rule_and_an_implication(self):
        from dd_assistant.rules import RULES
        for rule in RULES:
            self.assertIn(rule.id, issues.TREATMENT)
            self.assertIn(issues.TREATMENT[rule.id][0], issues.IMPLICATIONS)
            if rule.id != "R18":
                self.assertIn(rule.id, issues.AMOUNTS)

    def test_no_advice_language(self):
        text = " ".join(t for _, t in issues.TREATMENT.values()).lower()
        for word in ("must", "should", "we recommend", "fair price"):
            self.assertNotIn(word, text)

    def test_reviewer_can_change_an_implication(self):
        a = run("TAP_2025_published.xlsx", implications={"R07": "Further diligence", "ND: Provisions": "Price: net debt"})
        by_key = {i.key: i for i in a.issues}
        self.assertEqual(by_key["R07"].implication, "Further diligence")
        self.assertEqual(by_key["ND: Provisions"].implication, "Price: net debt")
        self.assertEqual(next(r for r in a.findings if r.rule.id == "R07").implication, "Further diligence")

    def test_databook_and_material_carry_the_list(self):
        from dd_assistant.databook import write_databook
        c = demo.CASE_BY_SLUG["tap"]
        a = demo.analysis(c)
        book = io.BytesIO()
        write_databook(a, book)
        ws = load_workbook(book)["Key Issues"]
        rows = [[x.value for x in row] for row in ws.iter_rows(min_row=5, max_row=4 + len(a.issues))]
        self.assertEqual(rows[0][1], "Lease liabilities")
        self.assertAlmostEqual(rows[0][5], a.issues[0].amount, places=3)
        self.assertEqual([r[8] for r in rows], [i.implication for i in a.issues])
        self.assertFalse(ws.cell(5, 9).protection.locked)        # the implication is the reviewer's to change
        material = demo.material(c, a)
        self.assertIn("## 1b. Key issues, ordered by amount at stake", material)
        self.assertIn("ND: Lease liabilities", material)
        self.assertIn("Deal implication (typical treatment, not advice): Price: working capital / peg", material)


if __name__ == "__main__":
    unittest.main()
