"""
Equity valuation methods. All methods return ValuationResult with low/base/high
ranges — never a single point price target (CLAUDE.md §9).
"""

from dataclasses import dataclass, field


@dataclass
class ValuationResult:
    method: str
    low: float
    base: float
    high: float
    bear: float
    bull: float
    assumptions_version: str = "v1"

    def __post_init__(self) -> None:
        if self.low > self.base or self.base > self.high:
            raise ValueError(
                f"{self.method}: low ({self.low}) <= base ({self.base}) <= high ({self.high}) required"
            )


def _sorted_range(a: float, b: float, c: float) -> tuple[float, float, float]:
    vals = sorted([a, b, c])
    return vals[0], vals[1], vals[2]


def pe_valuation(
    eps: float,
    pe_low: float,
    pe_base: float,
    pe_high: float,
) -> ValuationResult:
    if eps <= 0:
        raise ValueError("pe_valuation requires positive EPS")
    lo, mid, hi = _sorted_range(eps * pe_low, eps * pe_base, eps * pe_high)
    return ValuationResult("pe", lo, mid, hi, lo * 0.85, hi * 1.15)


def forward_pe_valuation(
    fwd_eps: float,
    pe_low: float,
    pe_base: float,
    pe_high: float,
) -> ValuationResult:
    if fwd_eps <= 0:
        raise ValueError("forward_pe_valuation requires positive forward EPS")
    lo, mid, hi = _sorted_range(fwd_eps * pe_low, fwd_eps * pe_base, fwd_eps * pe_high)
    return ValuationResult("fwd_pe", lo, mid, hi, lo * 0.85, hi * 1.15)


def peg_valuation(
    eps: float,
    growth_rate: float,
    peg_low: float = 1.0,
    peg_base: float = 1.5,
    peg_high: float = 2.0,
) -> ValuationResult:
    if eps <= 0:
        raise ValueError("peg_valuation requires positive EPS")
    growth_pct = growth_rate * 100.0
    lo, mid, hi = _sorted_range(
        eps * growth_pct * peg_low,
        eps * growth_pct * peg_base,
        eps * growth_pct * peg_high,
    )
    return ValuationResult("peg", lo, mid, hi, lo * 0.80, hi * 1.20)


def ps_valuation(
    revenue_per_share: float,
    ps_low: float,
    ps_base: float,
    ps_high: float,
) -> ValuationResult:
    if revenue_per_share <= 0:
        raise ValueError("ps_valuation requires positive revenue per share")
    lo, mid, hi = _sorted_range(
        revenue_per_share * ps_low,
        revenue_per_share * ps_base,
        revenue_per_share * ps_high,
    )
    return ValuationResult("ps", lo, mid, hi, lo * 0.80, hi * 1.20)


def ev_ebitda_valuation(
    ebitda_per_share: float,
    ev_ebitda_low: float,
    ev_ebitda_base: float,
    ev_ebitda_high: float,
    net_debt_per_share: float = 0.0,
) -> ValuationResult:
    if ebitda_per_share <= 0:
        raise ValueError("ev_ebitda_valuation requires positive EBITDA per share")
    lo, mid, hi = _sorted_range(
        ebitda_per_share * ev_ebitda_low - net_debt_per_share,
        ebitda_per_share * ev_ebitda_base - net_debt_per_share,
        ebitda_per_share * ev_ebitda_high - net_debt_per_share,
    )
    return ValuationResult("ev_ebitda", lo, mid, hi, lo * 0.85, hi * 1.15)


def p_fcf_valuation(
    fcf_per_share: float,
    p_fcf_low: float,
    p_fcf_base: float,
    p_fcf_high: float,
) -> ValuationResult:
    if fcf_per_share <= 0:
        raise ValueError("p_fcf_valuation requires positive FCF per share")
    lo, mid, hi = _sorted_range(
        fcf_per_share * p_fcf_low,
        fcf_per_share * p_fcf_base,
        fcf_per_share * p_fcf_high,
    )
    return ValuationResult("p_fcf", lo, mid, hi, lo * 0.80, hi * 1.20)


def dcf_valuation(
    fcf_per_share: float,
    growth_rates: list[float],
    terminal_growth: float = 0.025,
    discount_rates: tuple[float, float, float] = (0.08, 0.10, 0.12),
    assumptions_version: str = "v1",
) -> ValuationResult:
    """Multi-year DCF with Gordon Growth Model terminal value.

    discount_rates = (low_wacc, base_wacc, high_wacc)
    Low WACC → highest value; high WACC → lowest value.
    """
    if fcf_per_share <= 0:
        raise ValueError("dcf_valuation requires positive FCF per share")
    if not growth_rates:
        raise ValueError("dcf_valuation requires at least one growth rate")

    def npv_for_rate(wacc: float) -> float:
        pv = 0.0
        fcf = fcf_per_share
        for i, g in enumerate(growth_rates):
            fcf = fcf * (1 + g)
            pv += fcf / (1 + wacc) ** (i + 1)
        terminal_value = fcf * (1 + terminal_growth) / (wacc - terminal_growth)
        pv += terminal_value / (1 + wacc) ** len(growth_rates)
        return pv

    values = sorted([npv_for_rate(r) for r in discount_rates])
    lo, mid, hi = values[0], values[1], values[2]
    result = ValuationResult("dcf", lo, mid, hi, lo * 0.80, hi * 1.20)
    result.assumptions_version = assumptions_version
    return result


def historical_range_valuation(
    eps: float,
    pe_5yr_low: float,
    pe_5yr_median: float,
    pe_5yr_high: float,
) -> ValuationResult:
    if eps <= 0:
        raise ValueError("historical_range_valuation requires positive EPS")
    lo, mid, hi = _sorted_range(
        eps * pe_5yr_low, eps * pe_5yr_median, eps * pe_5yr_high
    )
    return ValuationResult("historical", lo, mid, hi, lo * 0.85, hi * 1.15)


def peer_valuation(
    metric_value: float,
    peer_multiples_low: float,
    peer_multiples_median: float,
    peer_multiples_high: float,
    metric: str = "eps",
) -> ValuationResult:
    if metric_value <= 0:
        raise ValueError(f"peer_valuation requires positive {metric}")
    lo, mid, hi = _sorted_range(
        metric_value * peer_multiples_low,
        metric_value * peer_multiples_median,
        metric_value * peer_multiples_high,
    )
    return ValuationResult("peers", lo, mid, hi, lo * 0.80, hi * 1.20)


def aggregate_valuation(results: list[ValuationResult]) -> dict[str, float]:
    """Aggregate across methods: min low, mean base, max high."""
    if not results:
        return {}
    return {
        "low": min(r.low for r in results),
        "base": sum(r.base for r in results) / len(results),
        "high": max(r.high for r in results),
        "bear": min(r.bear for r in results),
        "bull": max(r.bull for r in results),
    }
