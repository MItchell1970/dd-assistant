"""Amounts and display scale (euros only: the European market).

The model always works in EUR thousands, as the Excel template does. Large groups (revenue of
€1 billion or more) are shown in millions so the figures stay readable: €1,415k for a mid-market
target, €939m for a listed group.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

CURRENCIES = {"EUR": "€"}


def _round(x: float) -> int:
    """Half up, like Excel's ROUND(x; 0)."""
    return int(Decimal(repr(float(x))).quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Money:
    currency: str = "EUR"
    millions: bool = False     # display in millions; the figures stay in thousands

    @classmethod
    def for_data(cls, d) -> "Money":
        revenue = [abs(v) for v in d.lines.get("vendas", {}).values() if v]
        return cls(d.currency, bool(revenue) and max(revenue) >= 1_000_000)

    @property
    def symbol(self) -> str:
        return CURRENCIES.get(self.currency, self.currency + " ")

    @property
    def unit(self) -> str:
        """Short unit for table headers: 'EUR k', 'EUR m'."""
        return f"{self.currency} {'m' if self.millions else 'k'}"

    @property
    def unit_long(self) -> str:
        return f"{self.currency} {'millions' if self.millions else 'thousands'}"

    def amount(self, x) -> str:
        """The number in the display unit, without symbol: 1,415 · 939 · −250."""
        if x is None:
            return "n/a"
        return f"{_round(x / 1000 if self.millions else x):,}".replace("-", "−")

    def fmt(self, x) -> str:
        """With symbol and unit: €1,415k · €939m · -€250k."""
        if x is None:
            return "n/a"
        v = _round(x / 1000 if self.millions else x)
        s = f"{self.symbol}{abs(v):,}{'m' if self.millions else 'k'}"
        return "-" + s if v < 0 else s
