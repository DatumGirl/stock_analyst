"""Risk metrics: volatility, beta, drawdown, VaR, CVaR, Sharpe, Sortino.

All functions are pure (no I/O) and accept plain Python lists so results
serialise directly to JSON without extra conversion.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats as sp_stats


def annualised_volatility(returns: list[float], trading_days: int = 252) -> float:
    """Annualised standard deviation of log returns.

    Args:
        returns: Daily log returns.
        trading_days: Trading days per year used for annualisation.

    Returns:
        Annualised volatility as a fraction (e.g. 0.20 = 20 %).

    Raises:
        ValueError: If fewer than 2 returns are supplied.
    """
    if len(returns) < 2:
        raise ValueError("at least 2 returns required to compute volatility")
    return float(np.std(returns, ddof=1) * math.sqrt(trading_days))


def beta(asset_returns: list[float], benchmark_returns: list[float]) -> float:
    """OLS beta of asset returns against benchmark returns.

    Args:
        asset_returns: Daily log returns of the asset.
        benchmark_returns: Daily log returns of the benchmark.

    Returns:
        Beta coefficient.

    Raises:
        ValueError: If series lengths differ or benchmark has zero variance.
    """
    if len(asset_returns) != len(benchmark_returns):
        raise ValueError("asset and benchmark return series must be the same length")
    if len(asset_returns) < 2:
        raise ValueError("at least 2 observations required")
    a = np.array(asset_returns, dtype=np.float64)
    b = np.array(benchmark_returns, dtype=np.float64)
    cov = np.cov(a, b, ddof=1)
    bench_var = cov[1, 1]
    if bench_var == 0:
        raise ValueError("benchmark returns have zero variance; beta is undefined")
    return float(cov[0, 1] / bench_var)


def max_drawdown(prices: list[float]) -> float:
    """Maximum peak-to-trough drawdown over a price series.

    Args:
        prices: Chronological prices (at least 1).

    Returns:
        Maximum drawdown as a non-positive fraction (e.g. -0.35 = -35 %).
    """
    arr = np.array(prices, dtype=np.float64)
    peak = np.maximum.accumulate(arr)
    drawdowns = arr / peak - 1
    return float(np.min(drawdowns))


def value_at_risk(returns: list[float], confidence: float = 0.95) -> float:
    """Historical VaR at the given confidence level (non-parametric).

    Args:
        returns: Daily log returns.
        confidence: Confidence level, e.g. 0.95 for 95 % VaR.

    Returns:
        VaR as a non-positive fraction representing the loss threshold.

    Raises:
        ValueError: If fewer than 20 observations or confidence outside (0,1).
    """
    if len(returns) < 20:
        raise ValueError("at least 20 observations required for reliable VaR")
    if not 0 < confidence < 1:
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")
    return float(np.percentile(returns, (1 - confidence) * 100))


def conditional_var(returns: list[float], confidence: float = 0.95) -> float:
    """Expected Shortfall (CVaR) — mean of returns below the VaR threshold.

    Args:
        returns: Daily log returns.
        confidence: Same confidence level as VaR.

    Returns:
        CVaR as a non-positive fraction.
    """
    var = value_at_risk(returns, confidence)
    arr = np.array(returns, dtype=np.float64)
    tail = arr[arr <= var]
    if len(tail) == 0:
        return var
    return float(np.mean(tail))


def sharpe_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> float:
    """Annualised Sharpe ratio.

    Args:
        returns: Daily log returns.
        risk_free_rate: Annualised risk-free rate as a fraction.
        trading_days: Trading days per year.

    Returns:
        Sharpe ratio; returns NaN when volatility is zero.
    """
    if len(returns) < 2:
        raise ValueError("at least 2 returns required")
    arr = np.array(returns, dtype=np.float64)
    daily_rf = risk_free_rate / trading_days
    excess = arr - daily_rf
    vol = float(np.std(excess, ddof=1))
    if vol == 0:
        return float("nan")
    return float(np.mean(excess) / vol * math.sqrt(trading_days))


def sortino_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> float:
    """Annualised Sortino ratio (downside deviation denominator).

    Args:
        returns: Daily log returns.
        risk_free_rate: Annualised risk-free rate as a fraction.
        trading_days: Trading days per year.

    Returns:
        Sortino ratio; returns NaN when downside deviation is zero.
    """
    if len(returns) < 2:
        raise ValueError("at least 2 returns required")
    arr = np.array(returns, dtype=np.float64)
    daily_rf = risk_free_rate / trading_days
    excess = arr - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float("nan")
    downside_std = float(np.std(downside, ddof=1))
    if downside_std == 0:
        return float("nan")
    return float(np.mean(excess) / downside_std * math.sqrt(trading_days))


def correlation_matrix(returns_by_ticker: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    """Pairwise Pearson correlation matrix.

    Args:
        returns_by_ticker: Mapping of ticker to return series.
            All series must be the same length.

    Returns:
        Nested dict {ticker_a: {ticker_b: corr}} for all pairs.

    Raises:
        ValueError: If series lengths differ.
    """
    tickers = list(returns_by_ticker.keys())
    lengths = {len(v) for v in returns_by_ticker.values()}
    if len(lengths) > 1:
        raise ValueError("all return series must be the same length")
    if not tickers:
        return {}
    matrix = np.corrcoef([returns_by_ticker[t] for t in tickers])
    return {
        tickers[i]: {tickers[j]: float(matrix[i, j]) for j in range(len(tickers))}
        for i in range(len(tickers))
    }
