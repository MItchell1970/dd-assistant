"""The deal layer (Phase 4B): what a deal team asks after the findings, computed by rule from the engine's output.

- valuation impact bridge: the diligence adjustments to EBITDA × an illustrative multiple and the debt-like and
  cash-like items the diligence identified, one for one; standard EV-to-equity items (leases) and working capital
  against the indicative peg are shown but not counted; never a valuation;
- top five deal issues, each with the typical protection chosen by rule from its deal implication;
- diligence risk score 0–100: what is still open, by severity × materiality × evidence, with its split by area;
- five areas, and the notes that belong to another workstream (Legal, HR, Tax, Regulatory), with the question;
- open items grouped by who answers them, and action items by moment of the deal;
- coverage: the rules run and the rules blocked by missing data, with the document that unblocks each.

Nothing here is a recommendation: the score measures how much the rules found, not whether to invest.
All amounts in EUR thousands, as in the engine.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .deal import qoe_steps
from .issues import WC_ITEM
from .rules import fy

AREAS = ("Quality of earnings", "Net debt", "Working capital", "Cash flow", "Tax")
RULE_AREA = {"Revenue": "Quality of earnings", "Margins": "Quality of earnings",
             "Quality of earnings": "Quality of earnings", "Net working capital": "Working capital",
             "Cash generation": "Cash flow", "Debt": "Net debt", "Tax": "Tax"}
# the consistency checks belong to the statement they test
RULE_AREA_BY_ID = {"R12": "Net debt", "R13": "Cash flow", "R14": "Cash flow", "R15": "Quality of earnings",
                   "R16": "Quality of earnings", "R17": "Net debt", "R30": "Quality of earnings"}
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
                  "R06": "no management adjustments in published accounts"}
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
SCORE_LABEL = "Finding intensity, not a recommendation"
SCORE_FORMULA = ("Score = min(100, 100 × points / 30); points per open issue = severity (High 3, Medium 2, Low 1) "
                 "× materiality (material 1, not quantifiable 0.75, below materiality 0.5) × evidence (open 1, "
                 "partly explained by a note 0.75, explained 0.5). Issues = the findings and the balance sheet items "
                 "still to classify (Medium); items already in adjusted net debt are priced, not scored. 100 = ten "
                 "open, material High findings. R18 (documents missing) is left to coverage.")

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


def top_issues(a, n: int = 5) -> list[DealIssue]:
    """The largest current issues: never a historical finding (one that fired only in an earlier year)."""
    return [d for d in deal_issues(a) if d.key not in INFORMATION_RULES and not d.historical][:n]


# ---------------------------------------------------------------- 3. risk score
@dataclass
class RiskScore:
    score: int
    points: float
    by_area: dict[str, float]          # score points by area (they add up to the score unless it is capped)
    lines: list[tuple[str, str, str, float]]     # (rule, area, why, points)
    label: str = SCORE_LABEL
    formula: str = SCORE_FORMULA


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
    return RiskScore(score, points, {k: round(100 * v / CAP, 1) for k, v in by_area.items()}, lines)


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
                return "blocked ○", doc
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
    mode = "outside-in (published accounts)" if "published" in names.lower() or a.ext.notes else "data room"
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
           f"## Diligence risk score: {s.score} / 100", f"*{s.label}.* {s.formula}", "",
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
