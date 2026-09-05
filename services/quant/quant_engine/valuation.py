"""Valuation calculations — always returns low/base/high, never a point.

Every method takes assumptions (growth, margins, discount rates) as explicit
parameters rather than fetching them from a database, keeping these functions
pure and directly testable with known-answer cases.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValuationRange:
    """A valuation expressed as a range of three scenarios.

    Attributes:
        low: Bear-case intrinsic value per share.
        base: Base-case intrinsic value per share.
        high: Bull-case intrinsic value per share.
        method: The valuation method used.
    """

    low: float
    base: float
    high: float
    method: str

    def to_dict(self) -> dict[str, object]:
        return {"low": self.low, "base": self.base, "high": self.high, "method": self.method}


def pe_range(
    eps: float,
    pe_low: float,
    pe_base: float,
    pe_high: float,
) -> ValuationRange:
    """Trailing P/E valuation range.

    Args:
        eps: Trailing twelve-month EPS.
        pe_low / pe_base / pe_high: Scenario P/E multiples.
    """
    if eps <= 0:
        raise ValueError("trailing P/E requires positive EPS")
    return ValuationRange(eps * pe_low, eps * pe_base, eps * pe_high, "pe")


def forward_pe_range(
    fwd_eps: float,
    pe_low: float,
    pe_base: float,
    pe_high: float,
) -> ValuationRange:
    """Forward P/E valuation range."""
    if fwd_eps <= 0:
        raise ValueError("forward P/E requires positive forward EPS")
    return ValuationRange(fwd_eps * pe_low, fwd_eps * pe_base, fwd_eps * pe_high, "fwd_pe")


def ev_ebitda_range(
    ebitda: float,
    net_debt: float,
    shares: int,
    multiple_low: float,
    multiple_base: float,
    multiple_high: float,
) -> ValuationRange:
    """EV/EBITDA-derived equity value per share.

    equity_value = EBITDA × multiple − net_debt
    """
    if shares <= 0:
        raise ValueError("shares must be positive")
    results = []
    for multiple in (multiple_low, multiple_base, multiple_high):
        equity_value = ebitda * multiple - net_debt
        results.append(equity_value / shares)
    return ValuationRange(results[0], results[1], results[2], "ev_ebitda")


def dcf_range(
    free_cash_flows: list[float],
    terminal_growth_rates: tuple[float, float, float],
    discount_rates: tuple[float, float, float],
    shares: int,
    net_debt: float = 0.0,
) -> ValuationRange:
    """Multi-scenario DCF valuation.

    Args:
        free_cash_flows: Projected FCF for each forecast year (year 1 first).
        terminal_growth_rates: (bear, base, bull) perpetuity growth rates.
        discount_rates: (bear, base, bull) WACC values.
        shares: Diluted shares outstanding.
        net_debt: Net debt to subtract from enterprise value.

    Returns:
        Equity value per share under bear/base/bull scenarios.
    """
    if shares <= 0:
        raise ValueError("shares must be positive")
    if not free_cash_flows:
        raise ValueError("at least one forecast year of FCF required")

    results = []
    for tgr, wacc in zip(terminal_growth_rates, discount_rates):
        if wacc <= tgr:
            raise ValueError(f"discount rate ({wacc}) must exceed terminal growth rate ({tgr})")
        pv = 0.0
        for year, fcf in enumerate(free_cash_flows, start=1):
            pv += fcf / (1 + wacc) ** year
        # Gordon Growth terminal value
        terminal_fcf = free_cash_flows[-1] * (1 + tgr)
        terminal_value = terminal_fcf / (wacc - tgr)
        horizon = len(free_cash_flows)
        pv += terminal_value / (1 + wacc) ** horizon
        equity_value = pv - net_debt
        results.append(equity_value / shares)

    return ValuationRange(results[0], results[1], results[2], "dcf")


def price_to_sales_range(
    revenue_per_share: float,
    ps_low: float,
    ps_base: float,
    ps_high: float,
) -> ValuationRange:
    """Price/Sales valuation range."""
    if revenue_per_share <= 0:
        raise ValueError("revenue per share must be positive")
    return ValuationRange(
        revenue_per_share * ps_low,
        revenue_per_share * ps_base,
        revenue_per_share * ps_high,
        "ps",
    )


def peer_implied_range(
    metric_value: float,
    peer_multiples: list[float],
) -> ValuationRange:
    """Implied value from a distribution of peer multiples.

    Uses the 25th percentile as bear, median as base, 75th as bull.

    Args:
        metric_value: The per-share metric (e.g. EPS, revenue/share) to apply
            peer multiples to.
        peer_multiples: List of peer P/E, EV/EBITDA, or P/S multiples.
    """
    if not peer_multiples:
        raise ValueError("at least one peer multiple required")
    if metric_value <= 0:
        raise ValueError("metric_value must be positive")
    sorted_m = sorted(peer_multiples)
    n = len(sorted_m)
    p25 = sorted_m[max(0, int(n * 0.25))]
    p50 = sorted_m[n // 2]
    p75 = sorted_m[min(n - 1, int(n * 0.75))]
    return ValuationRange(metric_value * p25, metric_value * p50, metric_value * p75, "peers")
