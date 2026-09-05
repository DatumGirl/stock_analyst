"""Pure valuation functions.

Every function returns a (low, base, high, bear, bull) tuple.
All inputs are plain Python numbers — no I/O, no LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ValuationRange:
    low: Decimal
    base: Decimal
    high: Decimal
    bear: Decimal
    bull: Decimal


# Sensitivity multipliers applied around the base case
BEAR_FACTOR = Decimal("0.80")
BULL_FACTOR = Decimal("1.25")
LOW_FACTOR = Decimal("0.90")
HIGH_FACTOR = Decimal("1.10")


def _range_from_base(base: Decimal) -> ValuationRange:
    return ValuationRange(
        low=base * LOW_FACTOR,
        base=base,
        high=base * HIGH_FACTOR,
        bear=base * BEAR_FACTOR,
        bull=base * BULL_FACTOR,
    )


def pe_valuation(eps: Decimal, peer_pe: float) -> ValuationRange:
    """Trailing P/E — base = EPS × peer median P/E."""
    base = eps * Decimal(str(peer_pe))
    return _range_from_base(base)


def forward_pe_valuation(fwd_eps: Decimal, peer_fwd_pe: float) -> ValuationRange:
    """Forward P/E."""
    base = fwd_eps * Decimal(str(peer_fwd_pe))
    return _range_from_base(base)


def ps_valuation(revenue_per_share: Decimal, peer_ps: float) -> ValuationRange:
    """Price-to-Sales."""
    base = revenue_per_share * Decimal(str(peer_ps))
    return _range_from_base(base)


def ev_ebitda_valuation(
    ebitda: Decimal,
    net_debt: Decimal,
    shares: Decimal,
    peer_ev_ebitda: float,
) -> ValuationRange:
    """EV/EBITDA implied equity value per share."""
    ev_base = ebitda * Decimal(str(peer_ev_ebitda))
    equity_base = ev_base - net_debt
    base = equity_base / shares if shares != 0 else Decimal("0")
    return _range_from_base(base)


def dcf_valuation(
    fcf: Decimal,
    growth_rate: float,
    terminal_growth_rate: float,
    discount_rate: float,
    shares: Decimal,
    projection_years: int = 5,
) -> ValuationRange:
    """Simple DCF: project FCF for N years then terminal value.

    Bear/bull scenarios use ±200 bps on growth rate.
    """
    def _dcf(g: float) -> Decimal:
        pv = Decimal("0")
        cf = fcf
        for i in range(1, projection_years + 1):
            cf = cf * Decimal(str(1 + g))
            pv += cf / Decimal(str((1 + discount_rate) ** i))
        # Gordon growth terminal value
        terminal_cf = cf * Decimal(str(1 + terminal_growth_rate))
        terminal_value = terminal_cf / Decimal(str(discount_rate - terminal_growth_rate))
        pv += terminal_value / Decimal(str((1 + discount_rate) ** projection_years))
        return pv / shares if shares != 0 else Decimal("0")

    base = _dcf(growth_rate)
    bear = _dcf(max(growth_rate - 0.02, 0.0))
    bull = _dcf(growth_rate + 0.02)
    low = base * LOW_FACTOR
    high = base * HIGH_FACTOR
    return ValuationRange(low=low, base=base, high=high, bear=bear, bull=bull)
