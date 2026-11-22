"""The net debt definition: what goes into the net debt deducted from the price, item by item.

In a deal the definition is negotiated in the SPA: the buyer wants every debt-like item in and only cash it can use;
the seller wants the opposite. This module lists the components of net debt (borrowings, cash and each debt-like or
cash-like balance sheet item), gives two presets — the buyer's (conservative, the engine's own default) and the
seller's — and computes, for any choice of components, the net debt, the leverage, the equity value at a multiple and
the impact of the findings. The user only chooses; the engine does every sum. Latest balance sheet date, EUR thousands;
a debt-like item adds to net debt, a cash-like item deducts from it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .extract import PRESUMED_DEBT
from .metrics import N

BUYER, SELLER, CUSTOM = "Buyer (conservative)", "Seller", "Custom"
PRESETS = (BUYER, SELLER, CUSTOM)
GROUPS = ("Borrowings", "Cash", "Leases", "Pensions", "Taxes", "Provisions", "Other debt-like", "Other cash-like",
          "To assess")
MATERIAL_OTHER = "Material 'other' line (R28): break it down"


@dataclass(frozen=True)
class Rule:
    """One line of the presets table. buyer / seller: True (in), False (out) or 'current' (in when current)."""
    group: str
    buyer: bool | str
    seller: bool | str
    why: str


# The presets, one line per component and the reason. The buyer's column is the engine's default (extract.DEBT_LIKE
# and CASH_LIKE; tests/test_net_debt_definition.py checks that they agree), so 'Buyer' reproduces adjusted net debt.
RULES: dict[str, Rule] = {
    "Borrowings": Rule("Borrowings", True, True, "Financial debt: in any definition."),
    "Cash": Rule("Cash", True, True, "Cash and equivalents: deducted in any definition (the buyer then tests how much "
                                     "is trapped or needed to run the business)."),
    "Lease liabilities": Rule("Leases", True, True, "Both: reported EBITDA is after IFRS 16 (no rent in it), so the "
                                                    "lease liabilities belong in net debt for the multiple to agree."),
    "Post-employment benefit obligations": Rule("Pensions", True, False, "Buyer: an unfunded obligation is a debt. "
                                                "Seller: the service cost is in EBITDA; at most net of tax."),
    "Income tax payable": Rule("Taxes", True, False, "Buyer: tax on profits earned before closing. Seller: an "
                                                     "ordinary working capital balance, paid in the normal course."),
    "Taxes and social security payable": Rule("Taxes", False, False, "Both out: recurring balances of working "
                                                                     "capital; in only if overdue."),
    "Provisions": Rule("Provisions", False, False, "Both out until classified: a provision for a past event is "
                                                   "debt-like, one for normal operations is not (to assess)."),
    "Dividends payable": Rule("Other debt-like", True, True, "Both: declared to the owners, a cash outflow owed."),
    "Shareholder loans": Rule("Other debt-like", True, True, "Both: usually repaid or assigned at closing."),
    "Deferred or contingent consideration": Rule("Other debt-like", True, False, "Buyer: owed for a past acquisition. "
                                                 "Seller: contingent, it may never be paid."),
    "Factoring and confirming": Rule("Other debt-like", True, False, "Buyer: financing of working capital, a debt. "
                                     "Seller: part of the normal working capital cycle."),
    PRESUMED_DEBT: Rule("Other debt-like", True, False, "Buyer: no current borrowings line, so presumed to be the "
                                                        "current debt. Seller: operating until the note shows debt."),
    "Other financial liabilities": Rule("To assess", False, False, "Both out until the note says what they are "
                                                                   "(derivatives, payables for assets, debt?)."),
    "Tax equity and institutional partnerships": Rule("To assess", False, False, "Both out until classified: "
                                                      "financing in form, repaid from the projects' tax benefits."),
    "Liabilities held for sale": Rule("To assess", False, False, "Both out: they leave with the disposal group."),
    "Deferred revenue and customer advances": Rule("To assess", False, False, "Both out: working capital (the "
                                                   "service is still owed); debt-like only if cash was paid out."),
    MATERIAL_OTHER: Rule("To assess", False, False, "Both out until broken down: the content of the line is unknown."),
    "Marketable securities and short-term investments": Rule("Other cash-like", "current", True, "Buyer: only current "
                                                             "and liquid ones. Seller: all of them are cash."),
    "Other financial assets": Rule("Other cash-like", False, True, "Buyer: not cash until shown liquid. Seller: "
                                                                   "financial assets, as good as cash."),
    "Restricted cash": Rule("Other cash-like", False, True, "Buyer: not available to repay debt. Seller: it is the "
                                                            "company's cash."),
    "Assets held for sale": Rule("Other cash-like", False, True, "Buyer: not cash until sold. Seller: the proceeds "
                                                                 "are as good as cash."),
}


def _rule_in(flag: bool | str, kind: str) -> bool:
    return kind == flag if isinstance(flag, str) else flag


@dataclass
class Component:
    key: str                     # 'fin_lp', 'fin_cp', 'caixa' or 'item:<index in data.balance_items>'
    label: str
    group: str
    category: str
    value: float | None          # EUR thousands, signed: + adds to net debt, − deducts from it
    source: str
    buyer: bool
    seller: bool
    why: str
    index: int | None = None     # the balance item behind it
    standard: bool = False       # a standard EV-to-equity item (leases): not an impact of the findings


def components(a) -> list[Component]:
    """Borrowings, cash and every debt-like or cash-like balance sheet item, at the latest balance sheet date."""
    d, B = a.data, a.view.bs_years[-1]
    out = []
    for key, label, group, sign in (("fin_lp", "Non-current borrowings", "Borrowings", 1),
                                    ("fin_cp", "Current borrowings", "Borrowings", 1),
                                    ("caixa", "Cash and cash equivalents", "Cash", -1)):
        value = d.v(key, B)
        r = RULES[group]
        out.append(Component(key, label, group, group, None if value is None else sign * value,
                             d.sources.get(key, ""), r.buyer, r.seller, r.why))
    for i, b in enumerate(d.balance_items):
        r = RULES.get(b.category, Rule("To assess", b.include, b.include, "Not in the presets table: kept as the "
                                                                          "engine classifies it."))
        kind = b.kind.replace("noncurrent", "non-current") or "balance sheet"
        out.append(Component(f"item:{i}", f"{b.label} ({kind})", r.group, b.category,
                             N(b.values.get(B)) * (1 if b.nature == "debt" else -1), b.source,
                             _rule_in(r.buyer, b.kind), _rule_in(r.seller, b.kind), r.why, i,
                             b.category == "Lease liabilities"))
    return out


def preset(cs: list[Component], name: str) -> dict[str, bool]:
    """The choice of a preset: component key -> included."""
    return {c.key: c.seller if name == SELLER else c.buyer for c in cs}


def net_debt(cs: list[Component], chosen: dict[str, bool]) -> float | None:
    """Sum of the components included. Unknown (None), never zero, when cash is included but not found, or borrowings
    are included and neither line was found (as for borrowings less cash in metrics.py)."""
    inc = [c for c in cs if chosen.get(c.key, c.buyer)]
    if any(c.key == "caixa" and c.value is None for c in inc):
        return None
    loans = [c for c in inc if c.group == "Borrowings"]
    if loans and all(c.value is None for c in loans):
        return None
    return sum(c.value or 0.0 for c in inc)


@dataclass
class Result:
    multiple: float
    net_debt: float | None
    leverage: float | None       # net debt / diligence-adjusted EBITDA
    ebitda: float | None         # reported, latest year: the base of the illustrative EV
    ev: float | None
    equity: float | None
    impact: float                # impact of the findings at the multiple, under this definition
    share: float | None          # impact / equity value


def evaluate(a, cs: list[Component], chosen: dict[str, bool], multiple: float) -> Result:
    """Everything that moves with the definition. The same formulas as deal_layer.equity_view (EV = multiple ×
    reported EBITDA, equity value = EV − net debt) and valuation_impact (EBITDA adjustments × multiple + the debt-like
    and cash-like items found by the diligence; borrowings, cash and leases are not findings)."""
    from .deal_layer import valuation_impact
    v, L = a.view, a.view.pl_years[-1]
    nd = net_debt(cs, chosen)
    dd = v.ebitda_dd.get(L)
    ebitda = a.metrics["ebitda"].get(L)
    ebitda = ebitda if isinstance(ebitda, (int, float)) else None
    ev = multiple * ebitda if ebitda is not None else None
    equity = ev - nd if ev is not None and nd is not None else None
    items = -sum(c.value or 0.0 for c in cs if c.index is not None and not c.standard and chosen.get(c.key, c.buyer))
    impact = valuation_impact(a).ebitda_change * multiple + items
    return Result(multiple, nd, nd / dd if nd is not None and dd and dd > 0 else None, ebitda, ev, equity, impact,
                  impact / equity if equity and equity > 0 else None)


@dataclass
class Negotiation:
    buyer: float | None
    seller: float | None

    @property
    def gap(self) -> float | None:
        """Buyer's net debt less the seller's: what the two definitions are apart, in euros of price."""
        return None if self.buyer is None or self.seller is None else self.buyer - self.seller


def negotiation(cs: list[Component]) -> Negotiation:
    return Negotiation(net_debt(cs, preset(cs, BUYER)), net_debt(cs, preset(cs, SELLER)))


@dataclass
class Change:
    """One change of the definition, as the user made it."""
    key: str
    label: str
    included: bool               # after the change
    reason: str = ""
    when: str = ""


@dataclass
class Definition:
    """The choice to carry into the databook: the preset it started from, the components included, the changes."""
    name: str = BUYER
    chosen: dict[str, bool] = field(default_factory=dict)
    changes: list[Change] = field(default_factory=list)

    def reason(self, key: str) -> str:
        """The latest reason given for a component."""
        return next((c.reason for c in reversed(self.changes) if c.key == key and c.reason), "")
