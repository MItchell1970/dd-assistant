"""Layer 3c — from enterprise value to equity value: the price mechanism (deterministic, no AI).

The analyst chooses the mechanism first; nothing is computed until they do:
  - completion accounts: the price is fixed on the balance sheet at closing.
        Equity = EV + eligible cash − financial debt − debt-like items not yet in debt + (NWC at closing − peg)
                 + other contractual adjustments (each with its sign)
    Using adjusted net debt (already net of cash and with the debt-like items) instead of its parts: never add the
    parts again. A configuration of the model, subordinated to the definitions of the SPA, not a universal clause.
  - locked box: the equity price is agreed on a past balance sheet (the locked box date); the buyer is protected by
    the leakage covenant, not by a true-up. Equity at closing = agreed equity price + value accrual or ticking fee
    − confirmed leakage deducted at closing. No NWC or net debt true-up at closing.
Leakage is a screening register, not a legal verdict: only items 'confirmed after review' are deducted or claimed,
and a payment to a related party does not prove prohibited leakage. Without the SPA and a register of payments
the conclusion is 'evidence insufficient to assess leakage'. Equity value is not the amount the seller receives:
escrow, retentions, earn-outs and deferrals are separate lines, only when they exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

MECHANISMS = ("Completion accounts", "Locked box")
LEAKAGE_STATES = ["Candidate", "Permitted by a clause", "Confirmed after review", "Out of scope", "Inconclusive"]
LEAKAGE_TREATMENTS = ("Deduct at closing", "Separate claim")
INSUFFICIENT = "Evidence insufficient to assess leakage: the SPA (leakage and permitted leakage clauses) and a register " \
               "of payments since the locked box date are needed."


@dataclass
class EnterpriseValue:
    """EV entered directly, or derived from a multiple the user chooses × the EBITDA chosen (never a market
    multiple supplied by the tool)."""
    value: float | None = None
    multiple: float | None = None
    ebitda: float | None = None
    ebitda_label: str = ""

    @property
    def derived(self) -> bool:
        return self.value is None and self.multiple is not None

    def amount(self) -> float | None:
        if self.value is not None:
            return self.value
        if self.multiple is not None and self.ebitda is not None:
            return self.multiple * self.ebitda
        return None


@dataclass
class CompletionAccounts:
    ev: EnterpriseValue
    cash: float | None                  # eligible cash (restricted or trapped cash excluded by the analyst)
    debt: float | None                  # financial debt
    debt_like: float = 0.0              # debt-like items not already in financial debt
    nwc: float | None = None            # NWC at closing (estimate before closing, actual in the final accounts)
    peg: float | None = None            # target NWC agreed in the SPA
    other: list[tuple[str, float]] = field(default_factory=list)   # contractual adjustments, sign explicit


@dataclass
class LeakageItem:
    id: str
    description: str
    amount: float
    date: str = ""                      # unknown with annual accounts
    beneficiary: str = ""
    relation: str = ""                  # to the seller
    document: str = ""
    clause: str = ""
    evidence: str = ""
    status: str = "Candidate"
    justification: str = ""


@dataclass
class LockedBox:
    equity_price: float                 # agreed at the locked box date
    locked_box_date: date | None = None
    closing_date: date | None = None
    accrual: float | None = None        # a fixed value accrual, if the SPA sets one
    ticking_rate: float | None = None   # or a ticking fee: annual rate on a base, ACT/365
    ticking_base: float | None = None
    leakage: list[LeakageItem] = field(default_factory=list)
    treatment: str = "Deduct at closing"


def completion_equity(c: CompletionAccounts) -> dict:
    """Equity value at closing under completion accounts, line by line; 'incomplete' names what is missing."""
    ev = c.ev.amount()
    missing = [name for name, x in (("enterprise value", ev), ("eligible cash", c.cash), ("financial debt", c.debt))
               if x is None]
    nwc_adj = None if c.nwc is None or c.peg is None else c.nwc - c.peg
    if nwc_adj is None:
        missing.append("NWC at closing or the peg")
    other = sum(x for _, x in c.other)
    lines = [("Enterprise value", ev), ("+ eligible cash", c.cash), ("− financial debt", None if c.debt is None else -c.debt),
             ("− debt-like items", -c.debt_like), ("+ NWC at closing − peg", nwc_adj)]
    lines += [(f"{'+' if x >= 0 else '−'} {label}", x) for label, x in c.other]
    net_debt = None if c.cash is None or c.debt is None else c.debt + c.debt_like - c.cash
    equity = None if missing else ev - net_debt + nwc_adj + other
    return {"lines": lines, "net_debt_with_debt_like": net_debt, "equity": equity, "incomplete": missing}


def ticking_fee(lb: LockedBox) -> float | None:
    """Annual rate × base × days from the locked box date to closing / 365 (ACT/365), when the SPA sets it."""
    if lb.ticking_rate is None or lb.ticking_base is None or not (lb.locked_box_date and lb.closing_date):
        return None
    return lb.ticking_base * lb.ticking_rate * (lb.closing_date - lb.locked_box_date).days / 365


def locked_box_equity(lb: LockedBox) -> dict:
    """Equity at closing under a locked box: agreed price + accrual − confirmed leakage deducted at closing.
    A confirmed leakage treated as a separate claim is shown apart and never deducted twice."""
    accrual = lb.accrual if lb.accrual is not None else ticking_fee(lb) or 0.0
    confirmed = sum(x.amount for x in lb.leakage if x.status == "Confirmed after review")
    before = lb.equity_price + accrual
    deduct = confirmed if lb.treatment == "Deduct at closing" else 0.0
    claim = confirmed if lb.treatment == "Separate claim" else 0.0
    return {"equity_before_leakage": before, "accrual": accrual, "leakage_deducted": deduct, "equity": before - deduct,
            "leakage_claim": claim, "candidates": sum(1 for x in lb.leakage if x.status == "Candidate"),
            "conclusion": INSUFFICIENT if not lb.leakage or all(x.status in ("Candidate", "Inconclusive")
                                                                for x in lb.leakage) else ""}


def sensitivity(ev: EnterpriseValue, net_debt: float, nwc_adj: float = 0.0, steps=(-1.0, 0.0, 1.0),
                ebitda_steps=(-0.10, 0.0, 0.10)) -> list[list] | None:
    """Equity for multiples and EBITDA around the base — only when EV is derived (a fixed EV does not move)."""
    if not ev.derived or ev.ebitda is None:
        return None
    rows = [["EBITDA \\ multiple"] + [ev.multiple + s for s in steps]]
    for e in ebitda_steps:
        ebitda = ev.ebitda * (1 + e)
        rows.append([ebitda] + [(ev.multiple + s) * ebitda - net_debt + nwc_adj for s in steps])
    return rows
