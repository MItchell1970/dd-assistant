"""Manual estimate against the agent's time, for a messy data room.

The manual estimate is the table fixed in docs/examples/duriva-messy/manual_estimate.md before the agent's run (a
test keeps the two the same). The agent's time is measured: the pipeline's clock from the files to the databook, plus
the reviewer's time to decide the Low accounts and read the differences — timed by a person, and shown as "not yet
timed" until it is, never assumed. Both are shown side by side, never as a ratio alone.
"""
from __future__ import annotations

from dataclasses import dataclass

SOURCE = ("Hypothesis of this project, per task (no public study gives minutes per task for a first-pass financial "
          "due diligence); low end, one experienced associate in Excel; to be reviewed by Bernardo. Fixed before the "
          "agent's run: docs/examples/duriva-messy/manual_estimate.md.")


@dataclass(frozen=True)
class Task:
    name: str
    units: str
    count: float
    minutes_per_unit: float
    why: str
    agent_step: str          # the step of the agent's clock that does the same work

    @property
    def minutes(self) -> float:
        return self.count * self.minutes_per_unit


MANUAL = [
    Task("Open and normalise the monthly ERP exports", "files", 35, 3,
         "Open, clean, paste into one sheet; the 2025 files need the swap spotted once", "Read the ledger"),
    Task("Rebuild the missing month and link the renamed account", "issues", 2, 15,
         "Notice the gap and the new code, work out the derivation, check it", "Read the ledger"),
    Task("Map the chart of accounts to the template lines", "accounts", 36, 2,
         "Read the name, decide the line, note doubtful ones", "Map the accounts"),
    Task("Tie the mapped trial balances to the annual accounts", "years", 3, 20,
         "Build the tie-out, chase the residual to an account", "Read the annual accounts and tie"),
    Task("Proof of cash, two banks", "bank-months", 72, 2,
         "Key the PDF lines or copy the CSV, roll forward, compare with the ledger", "Proof of cash"),
    Task("Receipts against revenue + VAT − change in receivables", "months", 36, 1.5,
         "One formula row per month once the data is in place", "Proof of cash"),
    Task("Supplier listings against the ledger", "year-ends", 2, 10, "Sum the listing, compare, note the difference",
         "Proof of cash"),
    Task("Monthly working capital, LTM and a peg reference", "table", 1, 45, "Build the monthly table and averages",
         "Analysis and databook"),
    Task("Analytical tests (red flags) with their sources", "rulebook", 1, 90,
         "The 32 tests of the rulebook by hand on the mapped figures", "Analysis and databook"),
]


def manual_minutes() -> float:
    return sum(t.minutes for t in MANUAL)


@dataclass
class AgentTime:
    steps: dict[str, float]            # seconds, measured
    review_minutes: float | None       # timed by a person; None = not yet timed

    @property
    def seconds(self) -> float:
        return sum(self.steps.values())

    def text(self) -> str:
        review = "not yet timed" if self.review_minutes is None else f"{self.review_minutes:.0f} min"
        return f"agent {self.seconds:.1f} s + reviewer {review}"
