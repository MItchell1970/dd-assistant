"""Phase 4B, the deal layer (dd_assistant/deal_layer.py): valuation impact without double counting, top deal
issues with their typical protection, the risk score and its formula, areas and referrals to other workstreams,
open items, action items by moment, and the coverage map."""
import re
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
                self.assertAlmostEqual(vi.at(m), vi.ebitda_change * m + vi.net_debt_effect, delta=0.01)
                self.assertAlmostEqual(vi.at(m), sum(c.amount * (m if c.kind == "EBITDA" else 1) for c in vi.counted),
                                       delta=0.01)

    def test_only_diligence_adjustments_count(self):
        """Leases are a standard EV-to-equity item (EBITDA is after IFRS 16) and working capital against the peg is
        the completion accounts mechanism: both are shown, neither is an impact of the findings."""
        for name in ALL:
            vi = dl.valuation_impact(company(name))
            self.assertTrue(all(c.nature == dl.DILIGENCE for c in vi.counted), name)
            self.assertTrue(all(c.nature in (dl.STANDARD, dl.MECHANISM) for c in vi.not_counted), name)
            self.assertNotIn("Lease liabilities", [c.label for c in vi.counted])
            self.assertNotIn("Working capital", [c.kind for c in vi.counted])
        tap = dl.valuation_impact(company("tap"))
        self.assertEqual([c.label for c in tap.standard], ["Lease liabilities"])
        self.assertAlmostEqual(tap.standard_effect, -2158302, delta=1)
        self.assertAlmostEqual(tap.at(8), -(173154 + 3873), delta=2)          # pensions and income tax payable
        self.assertEqual(tap.at(6), tap.at(10))                              # no EBITDA adjustment

    def test_more_working_capital_is_not_good_news(self):
        """Toyota's working capital is above the average of the year-ends (an inventory build): it used to show as a
        positive impact of the findings."""
        vi = dl.valuation_impact(company("toyota-caetano"))
        self.assertGreater(vi.nwc_effect, 0)
        self.assertEqual(vi.nwc.nature, dl.MECHANISM)
        self.assertLess(vi.at(8), 0)
        self.assertAlmostEqual(vi.at(8), -(1377 + 131), delta=2)
        self.assertNotIn("Working capital", " ".join(label for label, *_ in dl.impact_steps(vi, 8)))

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
        self.assertAlmostEqual(-(vi.net_debt_effect + vi.standard_effect),
                               a.view.net_debt_adjusted[B] - a.view.net_debt_reported[B], delta=1)

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
                                             "Escrow or retention", "Completion accounts", "Request more information",
                                             dl.PROTECTION_STANDARD, dl.PROTECTION_TAX))
                self.assertIn(d.moment, dl.MOMENTS)

    def test_protection_follows_the_implication(self):
        top = {d.key: d for d in dl.deal_issues(company("tap"))}
        self.assertEqual(top["ND: Lease liabilities"].protection, dl.PROTECTION_STANDARD)     # standard, not a finding
        self.assertEqual(top["ND: Post-employment benefit obligations"].protection, "Debt-like item in the SPA")
        self.assertEqual(top["R28"].protection, "Completion accounts")
        toyota = {d.key: d for d in dl.deal_issues(company("toyota-caetano"))}
        self.assertEqual(toyota["R04"].protection, "Price adjustment")

    def test_no_escrow_for_a_tax_rate_gap_without_a_tax_contingency(self):
        """R25 alone is not an exposure: money is held back only when the notes disclose a tax contingency."""
        tap, toyota = company("tap"), company("toyota-caetano")
        self.assertTrue(any(r.workstream == "Tax" for r in dl.referrals(tap)))
        self.assertFalse(any(r.workstream == "Tax" for r in dl.referrals(toyota)))
        self.assertEqual({d.key: d for d in dl.deal_issues(tap)}["R25"].protection, "Escrow or retention")
        self.assertEqual({d.key: d for d in dl.deal_issues(toyota)}["R25"].protection, dl.PROTECTION_TAX)

    def test_airline_deferred_revenue_is_working_capital(self):
        """Sector calibration, with the reason in view: unflown tickets are operating, so the item goes to the peg
        and is neither a net debt item to assess nor an open issue in the score."""
        a = company("tap")
        d = {x.key: x for x in dl.deal_issues(a)}["ND: Deferred revenue and customer advances"]
        self.assertEqual((d.kind, d.area, d.protection, d.moment),
                         ("Working capital item", "Working capital", "Completion accounts", "Completion accounts"))
        issue = {i.key: i for i in a.issues}[d.key]
        self.assertIn("not yet flown", issue.treatment)
        self.assertNotIn(d.key, [k for k, *_ in dl.risk_score(a).lines])
        from dd_assistant.issues import key_issues          # without the sector, it is still an item to assess
        plain = key_issues(a.findings, a.view, a.data, a.metrics, a.materiality)
        self.assertEqual({i.key: i for i in plain}[d.key].kind, "To assess")

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
            self.assertEqual(s.label, "Diligence Gap")

    def test_score_counts_what_is_still_open(self):
        """Severity × materiality × evidence: a finding a published note explains scores half; a balance sheet item
        still to classify scores as Medium; an item already in adjusted net debt is priced, not scored."""
        a = company("tap")
        pts = {key: p for key, _, _, p in dl.risk_score(a).lines}
        self.assertEqual(pts["R07"], 3.0)                                        # High, material, open
        self.assertEqual(pts["R22"], 1.0)                                        # Medium, material, explained by note 19
        self.assertNotIn("R11", pts)                                             # historical (FY23 only): not open today
        self.assertEqual(pts["ND: Assets held for sale"], 1.0)                   # to classify, below materiality
        self.assertEqual(pts["ND: Provisions"], 1.0)                             # to classify, explained by note 18
        self.assertNotIn("ND: Lease liabilities", pts)
        self.assertNotIn("ND: Post-employment benefit obligations", pts)
        for name in ALL:                                                         # every line is its three factors
            issues = {i.key: i for i in company(name).issues}
            for key, _, _, p in dl.risk_score(company(name)).lines:
                i = issues[key]
                self.assertAlmostEqual(p, dl.WEIGHT[i.severity or dl.ITEM_SEVERITY] * dl.FACTOR[i.material]
                                       * dl.EVIDENCE.get(i.evidence_state, 1.0))


class CurrentYearTest(unittest.TestCase):
    """Phase 6: a finding that fired only in an earlier year is not a current issue. TAP R11 (short-term debt
    concentration) fired in FY23 (69.3% of debt due within a year) and is 2.8% in FY25: it used to be the 4th top
    issue, with €450m and High, as if it were today."""

    def test_no_historical_finding_in_the_top_or_the_score(self):
        for name in ALL:
            a = company(name)
            latest = {r.rule.id: max(y for y, v in r.values.items() if v is not None)
                      for r in a.findings if any(v is not None for v in r.values.values())}
            for d in dl.top_issues(a):
                self.assertFalse(d.historical, (name, d.key))
                if d.kind == "Finding":
                    self.assertEqual(d.year, latest[d.key], (name, d.key))
            historical = {i.key for i in a.issues if i.historical}
            self.assertFalse(historical & {k for k, *_ in dl.risk_score(a).lines}, name)
            self.assertFalse(any(x.startswith(tuple(f"{d.title}:" for d in dl.deal_issues(a) if d.historical))
                                 for xs in dl.action_items(a).values() for x in xs), name)

    def test_tap_r11_is_historical(self):
        a = company("tap")
        r11 = next(r for r in a.findings if r.rule.id == "R11")
        self.assertTrue(r11.historical)
        self.assertEqual((r11.amount_year, r11.rule.severity, r11.base_severity), (2023, "Low", "High"))
        self.assertIn("historical: fired in FY23, not in FY25", r11.note)
        self.assertNotIn("R11", [d.key for d in dl.top_issues(a)])
        self.assertIn("R11", [d.key for d in dl.deal_issues(a) if d.historical])


class AlreadyInThePriceTest(unittest.TestCase):
    """Phase 6: leases (standard EV-to-equity item) and the airline's unflown tickets (operating working capital) are
    not deal issues; they sit apart, with the working capital against the peg, as 'Already in the price'."""

    def test_tap_top_is_findings_only(self):
        a = company("tap")
        top = [d.key for d in dl.top_issues(a)]
        self.assertEqual(top, ["R28", "ND: Provisions", "R22", "ND: Post-employment benefit obligations", "R07"])
        self.assertEqual([d.rank for d in dl.top_issues(a)], [1, 2, 3, 4, 5])
        self.assertEqual([p.label for p in dl.in_price(a)],
                         ["Lease liabilities", "Deferred revenue and customer advances",
                          "Net working capital against the indicative peg"])

    def test_every_open_high_finding_is_in_the_top(self):
        for name in ALL:
            a = company(name)
            top = {d.key for d in dl.top_issues(a)}
            highs = [d.key for d in dl.deal_issues(a) if d.severity == "High" and not d.historical
                     and d.key not in dl.INFORMATION_RULES and not d.evidence.startswith("explained")]
            self.assertTrue(set(highs[:5]) <= top, name)
            self.assertFalse(any(dl.already_in_price(d) for d in dl.top_issues(a)), name)

    def test_score_band(self):
        self.assertEqual(dl.risk_score(company("velmora")).band, ("Few open points", "green"))
        self.assertEqual(dl.risk_score(company("duriva")).band, ("Many open points", "red"))


class ClosingTheGapTest(unittest.TestCase):
    """What closes the gap: the three issues with the most points, and the score the same formula gives without them."""

    def test_closers_are_the_heaviest_and_after_is_the_formula(self):
        for name in ALL:
            s = dl.risk_score(company(name))
            pts = sorted((p for *_, p in s.lines), reverse=True)
            self.assertEqual([p for *_, p in s.closers], pts[:3], name)
            self.assertEqual(s.after, min(100, round(100 * (s.points - sum(pts[:3])) / dl.CAP)), name)
            self.assertLessEqual(s.after, s.score, name)
        tap = dl.risk_score(company("tap"))
        self.assertEqual(dl.closing_text(tap), "Answer these 3: 40 → 17")
        self.assertEqual([k for k, *_ in tap.closers], ["R07", "R28", "R30"])


class EquityViewTest(unittest.TestCase):
    """The multiple moves numbers: EV, equity value and the impact as a share of equity value."""

    def test_multiple_moves_ev_equity_and_share(self):
        for name in REAL:
            a = company(name)
            six, ten = dl.equity_view(a, 6), dl.equity_view(a, 10)
            self.assertAlmostEqual(ten.ev - six.ev, 4 * six.ebitda, delta=1)
            self.assertAlmostEqual(six.equity, six.ev - six.net_debt, delta=1)
            self.assertNotEqual(six.share, ten.share)
            self.assertEqual(six.impact, ten.impact)                        # no EBITDA adjustment outside-in
            self.assertFalse(six.depends)
        duriva = dl.equity_view(company("duriva"), 6)
        self.assertTrue(duriva.depends)
        self.assertNotEqual(duriva.impact, dl.equity_view(company("duriva"), 10).impact)

    def test_tap_at_eight(self):
        e = dl.equity_view(company("tap"), 8)
        self.assertAlmostEqual(e.impact, -(173154 + 3873), delta=2)
        self.assertAlmostEqual(e.share, e.impact / (8 * e.ebitda - e.net_debt))


class PrioritisedRequestsTest(unittest.TestCase):
    """The request list in three levels: never more than ten to start with; each request has a level and a link."""

    def test_at_most_ten_first_and_every_request_linked(self):
        for name in ALL:
            rs = dl.prioritised_requests(company(name))
            self.assertLessEqual(sum(q.priority == 1 for q in rs), dl.MAX_P1, name)
            for q in rs:
                self.assertIn(q.priority, dl.PRIORITIES, (name, q.item))
                self.assertIn(q.theme, dl.THEMES, (name, q.item))
                self.assertTrue(q.links, (name, q.item))
                self.assertTrue(all(re.match(r"R\d\d · |Net debt item: |To assess: ", l) for l in q.links),
                                (name, q.links))
            self.assertEqual(len({q.item for q in rs}), len(rs), name)        # each request once

    def test_level_follows_the_written_rule(self):
        a = company("tap")
        rs = {q.item: q for q in dl.prioritised_requests(a)}
        self.assertEqual(rs["AR ageing at the last two year-ends"].priority, 1)            # R07, High
        hist = [q for q in rs.values() if any("historical" in l for l in q.links) and len(q.links) == 1]
        self.assertTrue(hist and all(q.priority == 3 for q in hist))                         # R11, R24: FY23, FY24
        first = [q for q in dl.prioritised_requests(a) if q.priority == 1]
        self.assertEqual([t for t in dl.THEMES if any(q.theme == t for q in first)],
                         list(dict.fromkeys(q.theme for q in first)))                        # grouped by theme

    def test_duriva_caps_the_first_level(self):
        rs = dl.prioritised_requests(company("duriva"))
        self.assertEqual(sum(q.priority == 1 for q in rs), dl.MAX_P1)                        # planted problems: >10


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
            self.assertEqual(len(c.run) + len(c.blocked) + len(c.not_applicable), c.total)
            # no management EBITDA published; bank statements and supplier listings are not published (R31, R32)
            self.assertEqual([r for r, *_ in c.not_applicable], ["R05", "R06", "R31", "R32"])
            self.assertEqual(c.status("R05")[0], "not applicable –")
            self.assertFalse([k for k, v in dl.request_list(company(name)).items()
                              if "coverage: R05" in v or "coverage: R06" in v])
        self.assertEqual(duriva.not_applicable, [])

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
        self.assertTrue(any(isinstance(t, str) and t.startswith("Diligence Gap: 100 / 100") for t in texts))
        req = wb["Issues & Requests"]
        cells = [c.value for row in req.iter_rows() for c in row if isinstance(c.value, str)]
        self.assertIn("R30 · Comparatives restated (blocked)", cells)         # a blocked rule asks for its document

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
