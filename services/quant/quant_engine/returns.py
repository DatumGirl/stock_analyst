"""Pure return calculation functions. No I/O — arrays in, numbers out."""

import numpy as np


def log_returns(prices: np.ndarray) -> np.ndarray:
    """Compute log returns from a price series."""
    if len(prices) < 2:
        return np.array([], dtype=float)
    return np.diff(np.log(prices))


def total_return(prices: np.ndarray) -> float:
    """Total return from first to last price."""
    if len(prices) < 2 or prices[0] == 0:
        return float("nan")
    return float(prices[-1] / prices[0] - 1)


def cagr(prices: np.ndarray, periods_per_year: float = 252.0) -> float:
    """Annualized compound growth rate."""
    if len(prices) < 2 or prices[0] <= 0:
        return float("nan")
    n_periods = len(prices) - 1
    if n_periods == 0:
        return float("nan")
    years = n_periods / periods_per_year
    return float((prices[-1] / prices[0]) ** (1.0 / years) - 1)


def rolling_return(prices: np.ndarray, window: int) -> np.ndarray:
    """Rolling n-period return. First window-1 values are nan."""
    if len(prices) < window + 1:
        return np.full(len(prices), float("nan"))
    result = np.full(len(prices), float("nan"))
    for i in range(window, len(prices)):
        if prices[i - window] != 0:
            result[i] = prices[i] / prices[i - window] - 1
    return result
