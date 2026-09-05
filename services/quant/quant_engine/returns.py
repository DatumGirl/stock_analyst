"""Return and performance calculations.

All inputs are plain Python sequences or floats; numpy is an implementation
detail. Callers should not depend on ndarray outputs — results are plain lists
or floats so they serialise directly to JSON.
"""

from __future__ import annotations

import numpy as np


def daily_returns(prices: list[float]) -> list[float]:
    """Compute log returns from a price series.

    Args:
        prices: Chronological daily close prices, length >= 2.

    Returns:
        Log returns of length len(prices) - 1.

    Raises:
        ValueError: If fewer than 2 prices are supplied or any price <= 0.
    """
    if len(prices) < 2:
        raise ValueError("at least 2 prices required to compute returns")
    arr = np.array(prices, dtype=np.float64)
    if np.any(arr <= 0):
        raise ValueError("all prices must be positive")
    return np.log(arr[1:] / arr[:-1]).tolist()


def total_return(prices: list[float]) -> float:
    """Compute the total return over the price series.

    Args:
        prices: Chronological daily close prices, length >= 2.

    Returns:
        Total return as a fraction (e.g. 0.12 = 12 %).
    """
    if len(prices) < 2:
        raise ValueError("at least 2 prices required")
    return float(prices[-1] / prices[0] - 1)


def annualised_return(prices: list[float], trading_days: int = 252) -> float:
    """Compound annualised return from a price series.

    Args:
        prices: Chronological daily close prices.
        trading_days: Number of trading days per year.

    Returns:
        CAGR as a fraction.
    """
    n = len(prices) - 1
    if n <= 0:
        raise ValueError("at least 2 prices required")
    tr = prices[-1] / prices[0]
    return float(tr ** (trading_days / n) - 1)


def cagr(start_value: float, end_value: float, years: float) -> float:
    """Compound annual growth rate between two portfolio values.

    Args:
        start_value: Value at the start of the period.
        end_value: Value at the end of the period.
        years: Length of the period in years.

    Returns:
        CAGR as a fraction.
    """
    if start_value <= 0 or years <= 0:
        raise ValueError("start_value and years must be positive")
    return float((end_value / start_value) ** (1.0 / years) - 1)
