"""Phase 4B, the deal layer (dd_assistant/deal_layer.py): valuation impact without double counting, top deal
issues with their typical protection, the risk score and its formula, areas and referrals to other workstreams,
open items, action items by moment, and the coverage map."""
import unittest
from functools import lru_cache

from dd_assistant import deal_layer as dl
from dd_assistant import demo
from dd_assistant.dataroom import files_in, read_data_room
from dd_assistant.pipeline import analyse


@lru_cache(maxsize=None)
def company(name: str):
    if name in demo.CASE_BY_SLUG:
        return demo.analysis(demo.CASE_BY_SLUG[name])
    path = {"duriva": "data/Duriva_data_room", "velmora": "data/Velmora_data_room.xlsx"}[name]
    return analyse(read_data_room(files_in([path])), None, "PT")


ALL = ("tap", "toyota-caetano", "corticeira-amorim", "duriva", "velmora")
REAL = ("tap", "toyota-caetano", "corticeira-amorim")


class ValuationImpactTest(unittest.TestCase):
    def test_formula_at_each_multiple(self):
        for name in ALL:
            vi = dl.valuation_impact(company(name))
            for m in dl.MULTIPLES:
                self.assertAlmostEqual(vi.at(m), vi.ebitda_change * m + vi.net_debt_effect + vi.nwc_effect, delta=0.01)

    def test_no_double_counting_between_ebitda_and_net_debt(self):
        """A source line or a finding enters the EBITDA side or the net debt side, never both."""
        for name in ALL:
            with self.subTest(name):
                vi = dl.valuation_impact(company(name))
                e_keys, n_keys = {c.key for c in vi.ebitda}, {c.key for c in vi.net_debt}
                self.assertFalse(e_keys & n_keys)
                e_find = {c.finding for c in vi.ebitda if c.finding}
                n_find = {c.finding for c in vi.net_debt if c.finding}
                self.assertFalse(e_find & n_find)
                self.assertEqual(len(vi.components), len({c.key for c in vi.components}))

    def test_net_debt_side_is_the_bridge(self):
        a = company("tap")
        vi = dl.valuation_impact(a)
        B = a.view.bs_years[-1]
        self.assertAlmostEqual(-vi.net_debt_effect, a.view.net_debt_adjusted[B] - a.view.net_debt_reported[B],
                               delta=1)

    def test_duriva_ebitda_side_is_the_diligence_adjustment(self):
        a = company("duriva")
        vi = dl.valuation_impact(a)
        L = a.view.pl_years[-1]
        base = (a.view.ebitda_mgmt or a.view.ebitda)[L]
        self.assertAlmostEqual(vi.ebitda_change, a.view.ebitda_dd[L] - base, delta=0.01)
        self.assertIn("R19", {c.finding for c in vi.ebitda})

    def test_bridge_steps_add_up(self):
        vi = dl.valuation_impact(company("duriva"))
        steps = dl.impact_steps(vi, 8)
        self.assertAlmostEqual(sum(v for _, v, k in steps if k == "delta"), steps[-1][1], delta=0.01)


class TopIssuesAndScoreTest(unittest.TestCase):
    def test_top_five_by_amount_with_protection(self):
        for name in ALL:
            top = dl.top_issues(company(name))
            self.assertLessEqual(len(top), 5)
            amounts = [d.amount for d in top]
            known = [x for x in amounts if x is not None]
            self.assertEqual(known, sorted(known, reverse=True))
            for d in top:
                self.assertIn(d.protection, ("Price adjustment", "Debt-like item in the SPA", "Specific indemnity",
                                             "Escrow or retention", "Completion accounts", "Request more information"))
                self.assertIn(d.moment, dl.MOMENTS)

    def test_protection_follows_the_implication(self):
        top = {d.key: d for d in dl.deal_issues(company("tap"))}
        self.assertEqual(top["ND: Lease liabilities"].protection, "Debt-like item in the SPA")
        self.assertEqual(top["R28"].protection, "Completion accounts")
        toyota = {d.key: d for d in dl.deal_issues(company("toyota-caetano"))}
        self.assertEqual(toyota["R04"].protection, "Price adjustment")

    def test_clean_company_scores_low_and_planted_problems_score_high(self):
        self.assertLessEqual(dl.risk_score(company("velmora")).score, 10)
        self.assertGreaterEqual(dl.risk_score(company("duriva")).score, 70)
        for name in REAL:
            self.assertTrue(10 < dl.risk_score(company(name)).score < 100, name)

    def test_score_is_its_formula(self):
        for name in ALL:
            s = dl.risk_score(company(name))
            self.assertEqual(s.score, min(100, round(100 * s.points / dl.CAP)))
            self.assertAlmostEqual(s.points, sum(p for *_, p in s.lines))
            if s.score < 100:
                self.assertAlmostEqual(sum(s.by_area.values()), 100 * s.points / dl.CAP, delta=0.3)
            self.assertNotIn("R18", [r for r, *_ in s.lines])
            self.assertEqual(s.label, "Finding intensity, not a recommendation")


class AreasOpenItemsCoverageTest(unittest.TestCase):
    def test_areas_and_referrals(self):
        for name in ALL:
            a = company(name)
            for d in dl.deal_issues(a):
                self.assertIn(d.area, dl.AREAS + (None,))
            for r in dl.referrals(a):
                self.assertIn(r.workstream, dl.WORKSTREAMS)
                self.assertTrue(r.question.startswith("Please provide"))
        tap = {(r.workstream, r.item.split(" (")[0]) for r in dl.referrals(company("tap"))}
        self.assertIn(("HR", "Post-employment benefit obligations"), tap)
        self.assertIn(("Legal", "Litigation, claims and guarantees given"), tap)
        amorim = dl.referrals(company("corticeira-amorim"))
        self.assertFalse([r for r in amorim if r.workstream == "Legal" and "note 15" in r.item])  # a tax note

    def test_open_items_are_grouped_and_unique(self):
        for name in ALL:
            items = dl.open_items(company(name))
            for o in items:
                self.assertIn(o.group, dl.GROUPS)
            asks = [o.item for o in items if o.group == "Ask the company"]
            self.assertEqual(len(asks), len(set(asks)))

    def test_action_items_by_moment(self):
        actions = dl.action_items(company("tap"))
        self.assertEqual(tuple(actions), dl.MOMENTS)
        self.assertTrue(any("Lease liabilities" in x for x in actions["SPA"]))

    def test_data_room_runs_more_rules_than_published_accounts(self):
        duriva = dl.coverage(company("duriva"))
        self.assertEqual(duriva.mode, "data room")
        for name in REAL:
            c = dl.coverage(company(name))
            self.assertGreater(len(duriva.run), len(c.run), name)
            self.assertEqual(c.mode, "outside-in (published accounts)")
            self.assertEqual(len(c.run) + len(c.blocked), c.total)

    def test_every_blocked_rule_has_a_request(self):
        for name in ALL:
            a = company(name)
            requests = dl.request_list(a)
            for rule_id, _, doc in dl.coverage(a).blocked:
                for part in dl._parts(doc):
                    self.assertIn(f"coverage: {rule_id}", requests[part], (name, rule_id))
            self.assertEqual(len(requests), len({k.lower() for k in requests}))     # no duplicate request


class OutputsTest(unittest.TestCase):
    def test_databook_sheets(self):
        import io
        from openpyxl import load_workbook
        from dd_assistant.databook import write_databook
        a = company("duriva")
        buf = io.BytesIO()
        write_databook(a, buf)
        wb = load_workbook(io.BytesIO(buf.getvalue()))
        vi = wb["Valuation Impact"]
        formulas = [c.value for row in vi.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]
        self.assertEqual(sum("*B" in f for f in formulas), 3)              # one per illustrative multiple
        amounts = [vi.cell(r, 6).value for r in range(5, 5 + len(dl.valuation_impact(a).components))]
        self.assertEqual(amounts, [c.amount for c in dl.valuation_impact(a).components])
        top = wb["Top Issues"]
        texts = [c.value for row in top.iter_rows() for c in row if c.value is not None]
        self.assertTrue(any(isinstance(t, str) and t.startswith("=MIN(100,ROUND(100*SUM(") for t in texts))
        self.assertTrue(any(isinstance(t, str) and t.startswith("Diligence risk score: 100 / 100") for t in texts))
        req = wb["Issues & Requests"]
        cells = [c.value for row in req.iter_rows() for c in row if isinstance(c.value, str)]
        self.assertIn("coverage: R30", cells)                                # a blocked rule asks for its document

    def test_material_has_the_new_figures(self):
        from dd_assistant.memo_check import _check_numbers
        a = company("tap")
        material = demo.material(demo.CASE_BY_SLUG["tap"], a)
        self.assertIn("## 1c. Deal layer", material)
        layer = dl.build(a)
        text = (f"Risk score {layer.score.score} out of 100. {layer.coverage.text}. At 8x the equity value impact is "
                f"{a.money.fmt(layer.impact.at(8))}.")
        checked, unmatched, misdated, _ = _check_numbers(text, material)
        self.assertGreaterEqual(checked, 3)
        self.assertEqual((unmatched, misdated), ([], []))


if __name__ == "__main__":
    unittest.main()
