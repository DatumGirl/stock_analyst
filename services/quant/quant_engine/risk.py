"""
Pure financial risk calculations. All functions return nan (not raise) when inputs
are insufficient or degenerate. No I/O.
"""

import numpy as np


def annualized_volatility(
    returns: np.ndarray, periods_per_year: float = 252.0
) -> float:
    """Annualized standard deviation of returns."""
    clean = returns[np.isfinite(returns)]
    if len(clean) < 2:
        return float("nan")
    return float(np.std(clean, ddof=1) * np.sqrt(periods_per_year))


def rolling_volatility(
    returns: np.ndarray, window: int = 30, periods_per_year: float = 252.0
) -> np.ndarray:
    """Rolling annualized volatility."""
    result = np.full(len(returns), float("nan"))
    for i in range(window - 1, len(returns)):
        window_slice = returns[i - window + 1 : i + 1]
        clean = window_slice[np.isfinite(window_slice)]
        if len(clean) >= 2:
            result[i] = float(np.std(clean, ddof=1) * np.sqrt(periods_per_year))
    return result


def beta(asset_returns: np.ndarray, market_returns: np.ndarray) -> float:
    """Beta of asset relative to market. Returns nan if market variance is zero."""
    mask = np.isfinite(asset_returns) & np.isfinite(market_returns)
    a, m = asset_returns[mask], market_returns[mask]
    if len(a) < 2:
        return float("nan")
    market_var = float(np.var(m, ddof=1))
    if market_var == 0:
        return float("nan")
    return float(np.cov(a, m, ddof=1)[0, 1] / market_var)


def max_drawdown(prices: np.ndarray) -> float:
    """Maximum peak-to-trough decline as a negative fraction."""
    clean = prices[np.isfinite(prices)]
    if len(clean) < 2:
        return float("nan")
    running_max = np.maximum.accumulate(clean)
    drawdowns = (clean - running_max) / running_max
    return float(np.min(drawdowns))


def var_historical(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Historical VaR at given confidence level (returned as a positive loss magnitude)."""
    clean = returns[np.isfinite(returns)]
    if len(clean) < 10:
        return float("nan")
    quantile = (1.0 - confidence) * 100.0
    return float(-np.percentile(clean, quantile))


def cvar_historical(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Conditional VaR (expected shortfall) beyond the VaR threshold."""
    clean = returns[np.isfinite(returns)]
    if len(clean) < 10:
        return float("nan")
    var = var_historical(clean, confidence)
    if np.isnan(var):
        return float("nan")
    tail = clean[clean <= -var]
    if len(tail) == 0:
        return var
    return float(-np.mean(tail))


def sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.05,
    periods_per_year: float = 252.0,
) -> float:
    """Annualized Sharpe ratio."""
    clean = returns[np.isfinite(returns)]
    if len(clean) < 2:
        return float("nan")
    vol = annualized_volatility(clean, periods_per_year)
    if vol == 0 or np.isnan(vol):
        return float("nan")
    annualized_mean = float(np.mean(clean)) * periods_per_year
    return (annualized_mean - risk_free_rate) / vol


def sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.05,
    periods_per_year: float = 252.0,
) -> float:
    """Annualized Sortino ratio using downside deviation."""
    clean = returns[np.isfinite(returns)]
    if len(clean) < 2:
        return float("nan")
    downside = clean[clean < 0]
    if len(downside) < 2:
        return float("nan")
    downside_vol = float(np.std(downside, ddof=1) * np.sqrt(periods_per_year))
    if downside_vol == 0:
        return float("nan")
    annualized_mean = float(np.mean(clean)) * periods_per_year
    return (annualized_mean - risk_free_rate) / downside_vol


def correlation_matrix(returns_matrix: np.ndarray) -> np.ndarray:
    """NxN correlation matrix from N x T returns array."""
    return np.corrcoef(returns_matrix)


def portfolio_volatility(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """Portfolio volatility: sqrt(w^T * Sigma * w)."""
    variance = float(weights @ cov_matrix @ weights)
    if variance < 0:
        return float("nan")
    return float(np.sqrt(variance))
