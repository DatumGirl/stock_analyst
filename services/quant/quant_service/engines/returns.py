"""Pure functions for return and risk calculations.

All functions are deterministic: same inputs always produce same outputs.
No I/O permitted here — fetch data before calling these functions.
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def daily_returns(prices: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute simple daily returns from a price series."""
    if len(prices) < 2:
        return np.array([], dtype=np.float64)
    return np.diff(prices) / prices[:-1]


def log_returns(prices: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute log returns from a price series."""
    if len(prices) < 2:
        return np.array([], dtype=np.float64)
    return np.diff(np.log(prices))


def total_return(prices: NDArray[np.float64]) -> float:
    """Total return from first to last price."""
    if len(prices) < 2:
        return 0.0
    return float((prices[-1] - prices[0]) / prices[0])


def annualise(return_: float, n_trading_days: int) -> float:
    """Annualise a period return using 252 trading days."""
    if n_trading_days <= 0:
        return 0.0
    return float((1 + return_) ** (252 / n_trading_days) - 1)


def volatility(returns: NDArray[np.float64], window: int | None = None) -> float:
    """Annualised volatility from daily returns.

    Args:
        returns: Daily return array.
        window: If set, use only the last ``window`` observations.
    """
    r = returns[-window:] if window and len(returns) > window else returns
    if len(r) < 2:
        return 0.0
    return float(np.std(r, ddof=1) * np.sqrt(252))


def max_drawdown(prices: NDArray[np.float64]) -> float:
    """Maximum peak-to-trough drawdown as a negative fraction."""
    if len(prices) < 2:
        return 0.0
    cummax = np.maximum.accumulate(prices)
    drawdowns = (prices - cummax) / cummax
    return float(np.min(drawdowns))


def var_historical(returns: NDArray[np.float64], confidence: float = 0.95) -> float:
    """Historical Value-at-Risk (loss expressed as positive number)."""
    if len(returns) == 0:
        return 0.0
    return float(-np.percentile(returns, (1 - confidence) * 100))


def cvar_historical(returns: NDArray[np.float64], confidence: float = 0.95) -> float:
    """Historical Conditional VaR (Expected Shortfall) as positive number."""
    if len(returns) == 0:
        return 0.0
    threshold = np.percentile(returns, (1 - confidence) * 100)
    tail = returns[returns <= threshold]
    if len(tail) == 0:
        return var_historical(returns, confidence)
    return float(-np.mean(tail))


def sharpe_ratio(
    returns: NDArray[np.float64],
    risk_free_daily: float = 0.05 / 252,
) -> float | None:
    """Annualised Sharpe ratio. Returns None when std dev is zero."""
    excess = returns - risk_free_daily
    std = np.std(excess, ddof=1)
    if std == 0:
        return None
    return float(np.mean(excess) / std * np.sqrt(252))


def sortino_ratio(
    returns: NDArray[np.float64],
    risk_free_daily: float = 0.05 / 252,
) -> float | None:
    """Annualised Sortino ratio (uses downside deviation). Returns None when flat."""
    excess = returns - risk_free_daily
    downside = excess[excess < 0]
    if len(downside) == 0:
        return None
    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return None
    return float(np.mean(excess) / downside_std * np.sqrt(252))


def beta(
    stock_returns: NDArray[np.float64],
    market_returns: NDArray[np.float64],
) -> float | None:
    """Beta of stock against market. Returns None on insufficient data."""
    n = min(len(stock_returns), len(market_returns))
    if n < 10:
        return None
    s, m = stock_returns[-n:], market_returns[-n:]
    cov_matrix = np.cov(s, m)
    mkt_var = cov_matrix[1, 1]
    if mkt_var == 0:
        return None
    return float(cov_matrix[0, 1] / mkt_var)


def correlation_matrix(returns_matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Pearson correlation matrix from a (n_assets × n_days) return matrix."""
    return np.corrcoef(returns_matrix)
