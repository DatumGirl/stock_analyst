"""Pure technical indicator functions — no I/O, deterministic outputs."""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def sma(prices: NDArray[np.float64], period: int) -> float:
    """Simple moving average of the last `period` prices."""
    if len(prices) == 0:
        return float("nan")
    return float(np.mean(prices[-period:] if len(prices) >= period else prices))


def ema(prices: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Exponential moving average series (same length as input)."""
    if len(prices) == 0:
        return np.array([], dtype=np.float64)
    alpha = 2.0 / (period + 1)
    result = np.empty(len(prices), dtype=np.float64)
    result[0] = prices[0]
    for i in range(1, len(prices)):
        result[i] = alpha * prices[i] + (1.0 - alpha) * result[i - 1]
    return result


def rsi(prices: NDArray[np.float64], period: int = 14) -> float:
    """Wilder RSI, returns 0–100. Returns nan when insufficient data."""
    if len(prices) < period + 1:
        return float("nan")
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 2)


def macd_histogram(
    prices: NDArray[np.float64],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> float:
    """MACD histogram (MACD line − signal line).

    Positive value indicates bullish momentum; negative bearish.
    Returns nan when insufficient data.
    """
    if len(prices) < slow + signal:
        return float("nan")
    macd_line = ema(prices, fast) - ema(prices, slow)
    signal_line = ema(macd_line, signal)
    return float(macd_line[-1] - signal_line[-1])
