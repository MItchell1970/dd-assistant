"""The deal layer (Phase 4B): what a deal team asks after the findings, computed by rule from the engine's output.

- valuation impact bridge: the diligence adjustments to EBITDA × an illustrative multiple and the debt-like and
  cash-like items the diligence identified, one for one; standard EV-to-equity items (leases) and working capital
  against the indicative peg are shown but not counted; never a valuation;
- top five deal issues, each with the typical protection chosen by rule from its deal implication;
- Diligence Gap 0–100: what is still open, by severity × materiality × evidence, with its split by area;
- five areas, and the notes that belong to another workstream (Legal, HR, Tax, Regulatory), with the question;
- open items grouped by who answers them, and action items by moment of the deal;
- coverage: the rules run and the rules blocked by missing data, with the document that unblocks each.

Nothing here is a recommendation: the score measures how much the rules found, not whether to invest.
All amounts in EUR thousands, as in the engine.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from .deal import qoe_steps
from .issues import WC_ITEM
from .rules import fy

AREAS = ("Quality of earnings", "Net debt", "Working capital", "Cash flow", "Tax")
RULE_AREA = {"Revenue": "Quality of earnings", "Margins": "Quality of earnings",
             "Quality of earnings": "Quality of earnings", "Net working capital": "Working capital",
             "Cash generation": "Cash flow", "Debt": "Net debt", "Tax": "Tax"}
# the consistency checks belong to the statement they test
RULE_AREA_BY_ID = {"R12": "Net debt", "R13": "Cash flow", "R14": "Cash flow", "R15": "Quality of earnings",
                   "R16": "Quality of earnings", "R17": "Net debt", "R30": "Quality of earnings",
                   "R31": "Cash flow", "R32": "Working capital"}
INFORMATION_RULES = ("R18",)     # missing documents: counted in coverage and open items, not in the score

MULTIPLES = (6.0, 8.0, 10.0)
ILLUSTRATIVE = "Illustrative, not a valuation"

# typical protection and moment of the deal, by the deal implication the engine already gives
PROTECTION = {"Price: EBITDA": "Price adjustment", "Price: net debt": "Debt-like item in the SPA",
              "Price: working capital / peg": "Completion accounts", "SPA protection": "Specific indemnity",
              "Further diligence": "Request more information", "Post-deal": "Request more information"}
MOMENT = {"Price: EBITDA": "Before signing", "Further diligence": "Before signing", "Price: net debt": "SPA",
          "SPA protection": "SPA", "Price: working capital / peg": "Completion accounts", "Post-deal": "Post-closing"}
MOMENTS = ("Before signing", "SPA", "Completion accounts", "Post-closing")

# valuation impact: what counts as an impact of the findings, and what does not
DILIGENCE = "Diligence adjustment"                 # counted: found or reclassified by the diligence
STANDARD = "Standard EV-to-equity item"            # not counted: in any net debt definition consistent with the EBITDA
MECHANISM = "Price mechanism"                      # not counted: settled by completion accounts, not a finding
STANDARD_ITEMS = ("Lease liabilities",)            # reported EBITDA is after IFRS 16, so the multiple already assumes them
PROTECTION_STANDARD = "Net debt definition in the SPA"
PROTECTION_TAX = "Tax indemnity (standard)"
COLUMN = "Protection or next step"       # requesting information is a step, not a protection
NOT_APPLICABLE = {"R05": "no management-adjusted EBITDA in published accounts",
                  "R06": "no management adjustments in published accounts",
                  "R31": "bank statements are not published: needs the data room",
                  "R32": "supplier listings are not published: needs the data room"}
NOT_COUNTED_WHY = {STANDARD: "Standard EV-to-equity item: reported EBITDA is after IFRS 16, so the multiple already "
                             "assumes it is deducted",
                   MECHANISM: "Price mechanism: settled euro for euro by completion accounts; the average of the "
                              "year-ends is not a negotiated peg"}

# risk score: what is still open, weighted by severity, materiality and evidence; normalised, capped
WEIGHT = {"High": 3.0, "Medium": 2.0, "Low": 1.0}
ITEM_SEVERITY = "Medium"                           # a balance sheet item still to classify has no rule severity
FACTOR = {True: 1.0, None: 0.75, False: 0.5}      # material · not quantifiable · below materiality
EVIDENCE = {"explained": 0.5, "partly explained": 0.75}     # a published note explains it; otherwise 1 (open)
CAP = 30.0                                         # points for 100: ten open, material High findings
SCORE_LABEL = "Diligence Gap"
SCORE_LEGEND = "Higher = more to clarify (0 = nothing open, 100 = a lot open)"
SCORE_NOTE = ("Not a recommendation: the Diligence Gap measures what is still open in the diligence, not whether to invest.")
SCORE_FORMULA = ("Score = min(100, 100 × points / 30); points per open issue of the latest year = severity (High 3, "
                 "Medium 2, Low 1) × materiality (material 1, not quantifiable 0.75, below materiality 0.5) × evidence "
                 "(open 1, partly explained by a note 0.75, explained 0.5). Issues = the findings and the balance "
                 "sheet items still to classify (Medium); items already in adjusted net debt are priced, not scored; "
                 "findings of earlier years only are historical, not scored. 100 = ten open, material High findings. "
                 "R18 (documents missing) is left to coverage.")
SCORE_PLAIN = ("Each open question of the latest year gets points: how serious, how big, how unexplained. 30 points "
               "= 100. A to-do meter for the diligence, not a grade for the company.")
BANDS = ((60, "Many open points", "red"), (25, "Several open points", "amber"), (0, "Few open points", "green"))

GROUPS = ("Ask the company", "Confirm with the auditor", "Outside financial scope")
WORKSTREAMS = ("Legal", "HR", "Tax", "Regulatory")
QUESTION = {"Legal": "Please provide the list of litigation, claims and guarantees ({where}), with amounts, provisions "
                     "and the lawyers' assessment.",
            "Related": "Please provide the related-party agreements ({where}) and confirm they are at arm's length.",
            "HR": "Please provide the latest actuarial report and the funding of post-employment benefits ({where}).",
            "Tax": "Please provide the open tax inspections and contingencies ({where}), with amounts and the advisers' "
                   "assessment.",
            "Regulatory": "Please provide the regulatory proceedings and licences at risk ({where})."}
MODE_LINE = ("Published accounts = outside-in mode (before the data room); Duriva = data room mode (fictitious "
             "data).")


def area_of(rule_id: str, rule_area: str) -> str | None:
    if rule_id in INFORMATION_RULES:
        return None
    return RULE_AREA_BY_ID.get(rule_id) or RULE_AREA.get(rule_area)


# ---------------------------------------------------------------- 1. valuation impact
@dataclass
class Component:
    kind: str          # "EBITDA", "Net debt" or "Working capital"
    key: str           # what it comes from: the QoE line, 'ND: <category>' or 'NWC'
    label: str
    amount: float      # EUR thousands: EBITDA change (EBITDA), or effect on equity value (net debt, NWC)
    finding: str = ""  # the rule behind it, when there is one
    source: str = ""
    basis: str = ""
    nature: str = DILIGENCE     # only diligence adjustments count as the impact of the findings


@dataclass
class ValuationImpact:
    ebitda: list[Component]        # diligence adjustments to EBITDA
    net_debt: list[Component]      # debt-like and cash-like items identified by the diligence
    standard: list[Component]      # standard EV-to-equity items (leases): shown, not counted
    nwc: Component | None          # working capital against the indicative peg: shown, not counted
    year: int
    ebitda_change: float
    net_debt_effect: float
    standard_effect: float
    nwc_effect: float

    def at(self, multiple: float) -> float:
        """The impact of the findings: diligence adjustments only."""
        return self.ebitda_change * multiple + self.net_debt_effect

    @property
    def counted(self) -> list[Component]:
        return self.ebitda + self.net_debt

    @property
    def not_counted(self) -> list[Component]:
        return self.standard + ([self.nwc] if self.nwc else [])

    @property
    def components(self) -> list[Component]:
        return self.counted + self.not_counted


def _finding_of(label: str) -> str:
    low = label.lower()
    return "R19" if "disposal" in low else "R05" if low.startswith("reverse") or "management" in low else ""


def valuation_impact(a) -> ValuationImpact:
    """EBITDA: the diligence adjustments after the seller's figure (the management-adjusted EBITDA when presented,
    otherwise the reported one); adjustments still pending stay out (prudent buyer's view). Net debt: the debt-like
    and cash-like items included in adjusted net debt, one for one, negative for the equity. Each source line enters
    once: items in net debt are already out of working capital (deal.py), and no EBITDA line is a balance.

    Two things are shown but are not an impact of the findings. Lease liabilities are a standard EV-to-equity item:
    reported EBITDA is after IFRS 16 (no lease cost in it), so a multiple of that EBITDA gives an enterprise value
    that already assumes the leases are deducted. Working capital against the indicative peg (latest year-end against
    the average of the year-ends, with two year-ends or more) is the completion accounts mechanism: more working
    capital delivered is paid for euro for euro, so it is neither good nor bad news about the company."""
    from .issues import _bridge_items
    v = a.view
    L, B = v.pl_years[-1], v.bs_years[-1]
    steps = qoe_steps(v, L)
    base_label = "Management-adjusted EBITDA" if v.ebitda_mgmt else (steps[0][0] if steps else "")
    ebitda, after = [], False
    for label, value, kind in steps:
        if kind == "total":
            after = after or label.startswith(base_label)
            continue
        if after and value:
            ebitda.append(Component("EBITDA", f"QoE: {label}", label, value, _finding_of(label), "QoE", fy(L)))
    items = [Component("Net debt", f"ND: {cat}", cat, -total, "", source, f"balance at {fy(B)}",
                       STANDARD if cat in STANDARD_ITEMS else DILIGENCE)
             for kind, cat, total, source, _ in _bridge_items(v, B) if kind == "Net debt item"]
    net_debt = [c for c in items if c.nature == DILIGENCE]
    standard = [c for c in items if c.nature == STANDARD]
    nwc = None
    now = v.nwc_values.get(B)
    if now is not None and v.nwc_average is not None and len(v.bs_years) > 1:
        nwc = Component("Working capital", "NWC", "Net working capital against the indicative peg", now - v.nwc_average,
                        "", "NWC", f"{fy(B)} against the average of the year-ends (not a negotiated peg)", MECHANISM)
    return ValuationImpact(ebitda, net_debt, standard, nwc, L, sum(c.amount for c in ebitda),
                           sum(c.amount for c in net_debt), sum(c.amount for c in standard),
                           nwc.amount if nwc else 0.0)


@dataclass
class EquityView:
    """Illustrative, not a valuation: what the chosen multiple means in euros. EV = multiple × reported EBITDA of the
    latest year; equity value = EV − adjusted net debt; the impact of the findings at that multiple, in euros and as a
    share of that equity value."""
    multiple: float
    ebitda: float | None
    ev: float | None
    net_debt: float | None
    equity: float | None
    impact: float
    share: float | None          # impact ÷ equity value (None when equity value is not positive)
    depends: bool                # False: no EBITDA adjustment, so the impact does not move with the multiple


def equity_view(a, multiple: float) -> EquityView:
    vi = valuation_impact(a)
    L, B = a.view.pl_years[-1], a.view.bs_years[-1]
    ebitda = a.metrics["ebitda"].get(L)
    ebitda = ebitda if isinstance(ebitda, (int, float)) else None
    nd = a.view.net_debt_adjusted.get(B)
    ev = multiple * ebitda if ebitda is not None else None
    equity = ev - nd if ev is not None and nd is not None else None
    impact = vi.at(multiple)
    share = impact / equity if equity and equity > 0 else None
    return EquityView(multiple, ebitda, ev, nd, equity, impact, share, bool(vi.ebitda))


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.1%}".replace("-", "−")


def impact_steps(vi: ValuationImpact, multiple: float) -> list[tuple[str, float, str]]:
    """The bridge for the chart, from zero: EBITDA adjustments × multiple, each diligence net debt item, the total.
    Standard EV-to-equity items and working capital against the peg are not steps: they are not findings."""
    steps = [(f"{c.label} (×{multiple:g})", c.amount * multiple, "delta") for c in vi.ebitda]
    steps += [(c.label, c.amount, "delta") for c in vi.net_debt]
    steps.append(("Impact of diligence adjustments", vi.at(multiple), "total"))
    return steps


# ---------------------------------------------------------------- 2. top deal issues
@dataclass
class DealIssue:
    rank: int
    key: str
    title: str
    kind: str
    severity: str
    amount: float | None
    amount_label: str
    area: str | None
    implication: str
    protection: str
    moment: str
    evidence: str
    request: str
    year: int | None = None
    historical: bool = False      # fired only in an earlier year: shown in Findings, out of the top, score and actions


def _protection(i, tax_contingency: bool = True) -> str:
    if i.kind == "Net debt item" and i.title in STANDARD_ITEMS:
        return PROTECTION_STANDARD         # not a finding: the definition must match the EBITDA the multiple uses
    if i.key == "R25" and not tax_contingency:
        return PROTECTION_TAX              # a rate gap alone is not an exposure: nothing held back without a contingency
    p = PROTECTION.get(i.implication, "Request more information")
    if p == "Specific indemnity" and i.material and i.evidence_state in ("", "open"):
        return "Escrow or retention"       # material, unexplained exposure: money held back, not only a promise
    return p


def _area_of_issue(i, rules_by_id) -> str | None:
    if i.kind == "Finding":
        r = rules_by_id.get(i.key)
        return area_of(i.key, r.rule.area if r else "")
    return "Working capital" if i.kind == WC_ITEM else "Net debt"


def deal_issues(a) -> list[DealIssue]:
    """Every key issue (already ordered by amount at stake, not quantifiable last), with protection and moment."""
    by = {r.rule.id: r for r in a.findings}
    tax = any(r.workstream == "Tax" for r in referrals(a))      # a tax contingency or provision in the notes
    out = []
    for n, i in enumerate(a.issues, 1):
        ev = (i.evidence_state + (f" by {i.evidence_note}" if i.evidence_note else "")) or "notes not read"
        out.append(DealIssue(n, i.key, i.title, i.kind, i.severity, i.amount, i.amount_label, _area_of_issue(i, by),
                             i.implication, _protection(i, tax), MOMENT.get(i.implication, "Before signing"), ev,
                             i.request, i.year, getattr(i, "historical", False)))
    return out


def already_in_price(d: DealIssue) -> bool:
    """A standard EV-to-equity item (leases) or an operating working capital item of the sector: not a finding."""
    return d.kind == WC_ITEM or (d.kind == "Net debt item" and d.title in STANDARD_ITEMS)


def top_issues(a, n: int = 5) -> list[DealIssue]:
    """The deal issues of the latest year (never a historical finding, never an item already in the price): every
    open High finding first, then the largest by amount; shown by amount at stake."""
    cand = [d for d in deal_issues(a)
            if d.key not in INFORMATION_RULES and not d.historical and not already_in_price(d)]
    pick = [d for d in cand if d.severity == "High" and not d.evidence.startswith("explained")][:n]
    for d in cand:
        if len(pick) >= n:
            break
        if d not in pick:
            pick.append(d)
    order = {d.key: k for k, d in enumerate(cand)}
    return [replace(d, rank=k) for k, d in enumerate(sorted(pick, key=lambda d: order[d.key]), 1)]


@dataclass
class InPrice:
    label: str
    amount: float
    why: str


def in_price(a) -> list[InPrice]:
    """What a buyer prices anyway, shown apart from the findings: standard EV-to-equity items (leases), the operating
    working capital items of the sector, and working capital against the indicative peg (the price mechanism)."""
    vi = valuation_impact(a)
    out = [InPrice(c.label, abs(c.amount), NOT_COUNTED_WHY[STANDARD]) for c in vi.standard]
    out += [InPrice(i.title, i.amount, i.treatment) for i in a.issues if i.kind == WC_ITEM and i.amount]
    if vi.nwc:
        out.append(InPrice(vi.nwc.label, vi.nwc.amount, NOT_COUNTED_WHY[MECHANISM]))
    return out


# ---------------------------------------------------------------- 3. risk score
@dataclass
class RiskScore:
    score: int
    points: float
    by_area: dict[str, float]          # score points by area (they add up to the score unless it is capped)
    lines: list[tuple[str, str, str, float]]     # (rule, area, why, points)
    label: str = SCORE_LABEL
    formula: str = SCORE_FORMULA
    titles: dict[str, str] = field(default_factory=dict)     # issue key -> its title, for the breakdown table
    counts: dict[str, int] = field(default_factory=dict)     # current findings by severity (High, Medium, Low)
    closers: list[tuple[str, str, float]] = field(default_factory=list)   # (key, title, points): the 3 that weigh most
    after: int | None = None                                 # the score once those three are answered (by the formula)

    @property
    def band(self) -> tuple[str, str]:
        """(word, tone) of the score: a triage band, never a recommendation."""
        return next((word, tone) for floor, word, tone in BANDS if self.score >= floor)


def risk_score(a) -> RiskScore:
    """Every open issue (a finding, or a balance sheet item still to classify) scores severity × materiality ×
    evidence. Items already included in adjusted net debt are quantified and priced: they are not scored."""
    by_rule = {r.rule.id: r for r in a.findings}
    lines, by_area = [], {x: 0.0 for x in AREAS}
    for i in a.issues:
        if getattr(i, "historical", False):
            continue                       # in the past: not an open issue today
        if i.kind == "Finding":
            r = by_rule.get(i.key)
            area, severity = area_of(i.key, r.rule.area if r else ""), i.severity
        elif i.kind == "To assess":
            area, severity = "Net debt", ITEM_SEVERITY
        else:
            continue
        if area is None:
            continue
        pts = WEIGHT[severity] * FACTOR[i.material] * EVIDENCE.get(i.evidence_state, 1.0)
        why = (f"{severity} × {'material' if i.material else 'not quantifiable' if i.material is None else 'below materiality'}"
               f" × {i.evidence_state if i.evidence_state in EVIDENCE else 'open'}")
        lines.append((i.key, area, why, pts))
        by_area[area] += pts
    points = sum(p for *_, p in lines)
    score = min(100, round(100 * points / CAP))
    titles = {i.key: i.title for i in a.issues}
    current = [i for i in a.issues if i.kind == "Finding" and not i.historical and i.key not in INFORMATION_RULES]
    counts = {s: sum(i.severity == s for i in current) for s in WEIGHT}
    # what closes the gap: the three open issues whose answer lowers the score most (the most points), and the
    # score the same formula gives without them; ties keep the order of the issues (by amount at stake)
    top3 = sorted(lines, key=lambda x: -x[3])[:3]
    closers = [(k, titles.get(k, k), p) for k, _, _, p in top3]
    after = min(100, round(100 * (points - sum(p for *_, p in top3)) / CAP))
    return RiskScore(score, points, {k: round(100 * v / CAP, 1) for k, v in by_area.items()}, lines,
                     titles=titles, counts=counts, closers=closers, after=after)


def closing_text(s: RiskScore) -> str:
    """'Answer these 3: 40 → 20', computed by the score's own formula."""
    return f"Answer these {len(s.closers)}: {s.score} → {s.after}" if s.closers else "Nothing open"


# ---------------------------------------------------------------- 4. areas and referrals
@dataclass
class Referral:
    workstream: str
    item: str
    where: str
    question: str


def _where(n) -> str:
    return f"note {n.note}" + (f", {n.page}" if n.page and not n.page.startswith("note") else "")


def referrals(a) -> list[Referral]:
    """Items of the notes (and net debt items) that belong to another workstream. Routed with a question; no legal,
    HR or tax analysis is made here."""
    seen, out = set(), []

    def add(ws: str, item: str, where: str, template: str | None = None):
        if (ws, item) in seen:
            return
        seen.add((ws, item))
        out.append(Referral(ws, item, where, QUESTION[template or ws].format(where=where)))

    for n in a.ext.notes or []:
        text = " ".join([n.title] + [r[0] for r in n.rows] + n.texts).lower()
        where, note = _where(n), f"note {n.note}"
        tax = re.search(r"\btax|fisca", text)
        legal = re.search(r"civil|litig|legal action|legal proceeding|lawsuit|judicia|labou?r court", text)
        if n.topic == "contingencies":       # contingent liabilities and guarantees given
            if tax:
                add("Tax", f"Tax contingencies ({note})", where)
            if re.search(r"regulat", text):
                add("Regulatory", f"Regulatory contingencies ({note})", where)
            if (legal or re.search(r"guarantee|fiança|caução|\bgarantias\b(?! a clientes)", text)) and \
                    not re.search(r"\btax|fisca", n.title.lower()):      # a tax note's court cases stay with Tax
                add("Legal", f"Litigation, claims and guarantees given ({note})", where)
        elif n.topic == "provisions":        # customer warranties are operating provisions: not routed
            if tax:
                add("Tax", f"Tax provisions ({note})", where)
            if legal:
                add("Legal", f"Provisions for litigation ({note})", where)
        elif n.topic == "related_parties":
            add("Legal", f"Related-party balances and transactions ({note})", where, "Related")
        elif legal and re.search(r"legal action|lawsuit", text):
            add("Legal", f"Legal action ({note})", where)
        if re.search(r"environment|ambienta", text):
            add("Regulatory", f"Environmental matters ({note})", where)
    for i in a.issues:
        if "post-employment" in i.title.lower() or "pension" in i.title.lower():
            add("HR", f"{i.title} ({i.amount_label})", i.source or "balance sheet")
    order = {w: k for k, w in enumerate(WORKSTREAMS)}
    return sorted(out, key=lambda r: order[r.workstream])


# ---------------------------------------------------------------- 7. coverage (before 5: open items use it)
@dataclass
class Coverage:
    run: list[str]
    blocked: list[tuple[str, str, str]]     # (rule, name, document that unblocks it)
    total: int
    mode: str
    not_applicable: list[tuple[str, str, str]] = field(default_factory=list)    # (rule, name, why)

    def status(self, rule_id: str) -> tuple[str, str]:
        """(status with its mark, the document that unblocks it or why it does not apply)."""
        for rid, _, doc in self.blocked:
            if rid == rule_id:
                return "blocked □", doc
        for rid, _, why in self.not_applicable:
            if rid == rule_id:
                return "not applicable –", why
        return "run ✓", ""

    @property
    def text(self) -> str:
        return f"{len(self.run)} of {self.total} rules run"


def coverage(a) -> Coverage:
    """A rule is blocked when it has no value for any year: a figure it needs is not in the accounts. Outside-in,
    the rules on management adjustments are not applicable instead: published accounts have no management EBITDA, so
    there is no document to ask for yet."""
    names = " ".join(str(f) for f in getattr(a.ext, "files", []) or [])
    mode = ("outside-in (published accounts)" if "published" in names.lower() or a.ext.notes or a.ext.esef
            else "data room")
    outside = mode.startswith("outside-in") and not a.view.ebitda_mgmt
    run, blocked, na = [], [], []
    for r in a.results:
        if not all(x is None for x in r.values.values()):
            run.append(r.rule.id)
        elif outside and r.rule.id in NOT_APPLICABLE:
            na.append((r.rule.id, r.rule.name, NOT_APPLICABLE[r.rule.id]))
        else:
            blocked.append((r.rule.id, r.rule.name, r.rule.request))
    return Coverage(run, blocked, len(a.results), mode, na)


# ---------------------------------------------------------------- request list (one, without duplicates)
def _parts(request: str) -> list[str]:
    return [p.strip()[0].upper() + p.strip()[1:] for p in request.split(";")
            if p.strip() and p.strip().lower() != "the documents listed in the evidence"]


def request_list(a) -> dict[str, list[str]]:
    """Document → what asks for it (findings, blocked rules, the document checklist, missing figures), with
    duplicates merged. Used by the databook and the open items."""
    out: dict[str, list[str]] = {}
    for r in a.findings:
        for part in _parts(r.next_request or r.rule.request):
            out.setdefault(part, []).append(r.rule.id)
    for rule_id, _, doc in coverage(a).blocked:
        for part in _parts(doc):
            out.setdefault(part, []).append(f"coverage: {rule_id}")
    for doc, ok in a.data.documents:
        if not ok:
            out.setdefault(doc, []).append("document checklist")
    for note in a.view.incomplete:
        out.setdefault(f"Figure missing from the data room: {note.split(' — ')[0]}", []).append("missing figure")
    return out


# ---------------------------------------------------------------- the request list by priority
PRIORITIES = {1: "Before signing", 2: "During the diligence", 3: "To complete the picture"}
PRIORITY_RULE = "Priority set by severity, amount at stake and SPA impact"
PRIORITY_DETAIL = ("Priority 1: linked to a current High finding, a top deal issue, or a material issue that moves the "
                   "price or the SPA; at most 10, by amount at stake (the rest go to priority 2). Priority 2: linked "
                   "to a current Medium finding, a balance sheet item still to classify, or a blocked rule that "
                   "affects value. Priority 3: everything else (Low or historical findings, the document checklist, "
                   "blocked rules with no effect on value).")
MAX_P1 = 10
THEMES = AREAS + ("Documents",)


@dataclass
class Request:
    item: str
    priority: int
    theme: str
    links: list[str]            # the findings, items or rules that ask for it: 'R07 · Receivables growing…'
    amount: float | None        # the largest amount at stake among them (EUR thousands)

    @property
    def level(self) -> str:
        return f"Priority {self.priority} · {PRIORITIES[self.priority]}"


def _moves_price(implication: str) -> bool:
    return implication.startswith("Price") or implication == "SPA protection"


def prioritised_requests(a) -> list[Request]:
    """The request list in three levels, by a written rule (PRIORITY_DETAIL); within a level, by theme and amount.
    Each request keeps every finding, item or rule that asks for it. Requests that a published note fully answers
    stay with the auditor (open items), as in open_items."""
    from .issues import TREATMENT
    top = {d.key for d in top_issues(a)}
    found: dict[str, list[tuple[int, str, str, float | None]]] = {}    # doc -> (level, theme, link, amount)

    def add(doc: str, level: int, theme: str | None, link: str, amount: float | None) -> None:
        found.setdefault(doc, []).append((level, theme or "Documents", link, amount))

    for r in a.findings:
        if r.rule.id in INFORMATION_RULES:
            continue
        if r.evidence_state == "explained":
            continue                          # a published note answers it: confirm with the auditor instead
        theme = area_of(r.rule.id, r.rule.area)
        sev = r.rule.severity
        if r.historical:
            level = 3
        elif sev == "High" or r.rule.id in top or (r.material and _moves_price(r.implication)):
            level = 1
        elif sev == "Medium":
            level = 2
        else:
            level = 3
        link = f"{r.rule.id} · {r.rule.name}" + (f" (historical, {fy(r.amount_year)})" if r.historical else "")
        for part in _parts(r.next_request or r.rule.request):
            add(part, level, theme, link, r.amount)
    for i in a.issues:
        if i.kind not in ("Net debt item", "To assess") or i.title in STANDARD_ITEMS or i.evidence_state == "explained":
            continue
        if i.key in top or (i.kind == "Net debt item" and i.material):
            level = 1
        else:
            level = 2
        add(i.request, level, "Net debt", f"{i.kind}: {i.title}", i.amount)
    for rule_id, name, doc in coverage(a).blocked:
        affects = _moves_price(TREATMENT.get(rule_id, ("", ""))[0])
        r = next((x for x in a.results if x.rule.id == rule_id), None)
        for part in _parts(doc):
            add(part, 2 if affects else 3, area_of(rule_id, r.rule.area if r else ""),
                f"{rule_id} · {name} (blocked)", None)
    for doc, ok in a.data.documents:
        if not ok:
            add(doc, 3, "Documents", "R18 · document checklist", None)
    for note in a.view.incomplete:
        add(f"Figure missing from the data room: {note.split(' — ')[0]}", 3, "Documents", "R18 · figure missing", None)

    out = []
    for doc, links in found.items():
        level = min(x[0] for x in links)
        main = [x for x in links if x[0] == level]
        amounts = [x[3] for x in links if x[3] is not None]
        out.append(Request(doc, level, main[0][1], list(dict.fromkeys(x[2] for x in links)),
                           max(amounts) if amounts else None))
    key = lambda q: (q.amount is None, -(q.amount or 0))
    first = sorted([q for q in out if q.priority == 1], key=key)
    for q in first[MAX_P1:]:                   # at most ten to start with: the smaller ones wait for the diligence
        q.priority = 2
    order = {t: k for k, t in enumerate(THEMES)}
    return sorted(out, key=lambda q: (q.priority, order.get(q.theme, 9), *key(q)))


# ---------------------------------------------------------------- 5. open items and 6. action items
@dataclass
class OpenItem:
    group: str
    item: str
    source: str


def open_items(a) -> list[OpenItem]:
    """Ask the company: every unique request (findings not explained by a note, blocked rules, missing documents).
    Confirm with the auditor: what a published note explains (the figure is public, its treatment is not yet
    confirmed). Outside financial scope: the referrals to Legal, HR, Tax and Regulatory."""
    explained = {r.rule.id for r in a.findings if r.evidence_state == "explained"}
    out = []
    for doc, src in request_list(a).items():
        if all(s in explained for s in src):
            continue
        out.append(OpenItem("Ask the company", doc, ", ".join(dict.fromkeys(src))))
    for i in a.issues:
        if i.evidence_state in ("explained", "partly explained") and i.evidence_note:
            out.append(OpenItem("Confirm with the auditor",
                                f"{i.title}: {i.evidence_state} by {i.evidence_note}", i.key))
    for ref in referrals(a):
        out.append(OpenItem("Outside financial scope", f"{ref.workstream}: {ref.item}", ref.where))
    return out


def action_items(a) -> dict[str, list[str]]:
    """What to do about each key issue, by moment of the deal (from its deal implication)."""
    out = {m: [] for m in MOMENTS}
    for d in deal_issues(a):
        if d.key in INFORMATION_RULES or d.historical:
            continue
        out[d.moment].append(f"{d.title}: {d.protection[:1].lower() + d.protection[1:]}")
    return out


# ---------------------------------------------------------------- everything, for the material, the site and the databook
@dataclass
class DealLayer:
    impact: ValuationImpact
    top: list[DealIssue]
    score: RiskScore
    referrals: list[Referral]
    open_items: list[OpenItem]
    actions: dict[str, list[str]]
    coverage: Coverage
    requests: dict[str, list[str]] = field(default_factory=dict)


def build(a) -> DealLayer:
    return DealLayer(valuation_impact(a), top_issues(a), risk_score(a), referrals(a), open_items(a),
                     action_items(a), coverage(a), request_list(a))


def report_md(a, company: str = "") -> str:
    """The deal layer of a company as Markdown (docs/examples/<company>/deal_layer.md, for review)."""
    layer = build(a)
    s, vi, cov = layer.score, layer.impact, layer.coverage
    f = lambda x: a.money.fmt(x).replace("-€", "−€") if x is not None else "not quantifiable"
    out = [f"# Deal layer — {company or a.ext.company}", "",
           f"Generated by `dd_assistant/deal_layer.py` from the default analysis. {ILLUSTRATIVE} where stated; no "
           "recommendation.", "",
           f"## {s.label}: {s.score} / 100", f"*{SCORE_LEGEND}. {SCORE_NOTE}* {s.formula}", "",
           "| Area | Score points |", "|---|---|"]
    out += [f"| {k} | {v:g} |" for k, v in s.by_area.items()]
    out += ["", "| Issue | Area | Severity × materiality × evidence | Points |", "|---|---|---|---|"]
    out += [f"| {rid} | {area} | {why} | {pts:g} |" for rid, area, why, pts in s.lines]
    out += ["", f"## Valuation impact ({ILLUSTRATIVE.lower()}), {fy(vi.year)}", "",
            "Only diligence adjustments count as the impact of the findings.", "",
            "| Side | Item | Finding | Amount |", "|---|---|---|---|"]
    out += [f"| {c.kind} | {c.label} | {c.finding or '–'} | {f(c.amount)} |" for c in vi.counted]
    out += ["", "| Multiple | Impact of diligence adjustments on equity value |", "|---|---|"]
    out += [f"| {m:g}x | {f(vi.at(m))} |" for m in MULTIPLES]
    if vi.not_counted:
        out += ["", "Shown, not counted (not findings):", "", "| Item | Why it is not counted | Amount |", "|---|---|---|"]
        out += [f"| {c.label} | {NOT_COUNTED_WHY[c.nature]} | {f(c.amount)} |" for c in vi.not_counted]
    out += ["", "## Top 5 deal issues", "", f"| # | Issue | Area | Amount at stake | {COLUMN} | When | "
            "Evidence |", "|---|---|---|---|---|---|---|"]
    out += [f"| {d.rank} | {d.key} · {d.title} | {d.area or '–'} | {f(d.amount)} | {d.protection} | {d.moment} | "
            f"{d.evidence} |" for d in layer.top]
    out += ["", f"## Coverage: {cov.text} ({cov.mode})", MODE_LINE, "",
            "| Rule | Status | Document that unblocks it, or why it does not apply |", "|---|---|---|"]
    out += [f"| {r.rule.id} · {r.rule.name} | {' | '.join(cov.status(r.rule.id))} |" for r in a.results]
    out += ["", "## Open items", ""]
    for g in GROUPS:
        items = [o for o in layer.open_items if o.group == g]
        out += [f"### {g} ({len(items)})"] + [f"- {o.item} *(from {o.source})*" for o in items] + [""]
    out += ["## Action items by moment", ""]
    for m in MOMENTS:
        out += [f"### {m}"] + [f"- {x}" for x in layer.actions[m]] + [""]
    out += ["## Referrals (routed, not analysed)", ""]
    out += [f"- **{r.workstream}** · {r.item}: {r.question}" for r in layer.referrals]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- titles for the signature visuals (Phase 5)
ISSUE_PHRASE = {    # what the amount at stake is, as a sentence (the amount comes from the engine)
    "R04": "Other income of {amt} sits within EBITDA",
    "R07": "Receivables grew {amt} ahead of revenue",
    "R09": "Inventory grew {amt} ahead of cost of sales",
    "R10": "Operating cash fell {amt} short of the conversion threshold",
    "R11": "{amt} of borrowings falls due within 12 months",
    "R22": "Interest of {amt} is covered less than four times by EBITDA",
    "R24": "Capex ran {amt} below depreciation",
    "R28": "{amt} sits in an 'other' working capital line"}
PROTECTION_PHRASE = {"Completion accounts": "completion accounts, not price", "Price adjustment": "a price adjustment",
                     "Debt-like item in the SPA": "debt-like in the SPA",
                     "Net debt definition in the SPA": "net debt definition in the SPA",
                     "Request more information": "more information before signing"}


def issue_title(d: DealIssue, money) -> str:
    """Signature visual 3: the issue in one sentence with its amount, then what a deal team does about it."""
    amt = money.fmt(d.amount).replace("-€", "−€") if d.amount is not None else ""
    head = ISSUE_PHRASE.get(d.key, "{title} of {amt}" if amt else "{title}").format(amt=amt, title=d.title)
    return f"{head}: {PROTECTION_PHRASE.get(d.protection, d.protection[:1].lower() + d.protection[1:])}"


def coverage_title(cov: Coverage) -> str:
    """Signature visual 2: how many rules ran, and what the others need."""
    where = "published accounts" if cov.mode.startswith("outside-in") else "the data room"
    out = f"{len(cov.run)} of {cov.total} rules run on {where}"
    if cov.blocked:
        out += f"; {len(cov.blocked)} name the document that unlocks them"
    if cov.not_applicable:
        out += f", {len(cov.not_applicable)} do not apply"
    return out
