"""Technical indicators — all pure functions returning plain Python lists/floats.

Each function returns NaN where insufficient data exists rather than
raising, so callers can safely zip results with their price series.
"""

from __future__ import annotations

import math

import numpy as np


def sma(prices: list[float], period: int) -> list[float | None]:
    """Simple moving average.

    Returns a list the same length as *prices*; the first ``period-1``
    values are ``None``.
    """
    _check_period(period)
    result: list[float | None] = [None] * (period - 1)
    arr = np.array(prices, dtype=np.float64)
    for i in range(period - 1, len(arr)):
        result.append(float(np.mean(arr[i - period + 1 : i + 1])))
    return result


def ema(prices: list[float], period: int) -> list[float | None]:
    """Exponential moving average using the standard multiplier 2/(period+1)."""
    _check_period(period)
    if len(prices) < period:
        return [None] * len(prices)
    multiplier = 2.0 / (period + 1)
    result: list[float | None] = [None] * (period - 1)
    seed = float(np.mean(prices[:period]))
    result.append(seed)
    for price in prices[period:]:
        result.append(price * multiplier + result[-1] * (1 - multiplier))  # type: ignore[operator]
    return result


def rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index (Wilder smoothing).

    Returns values in [0, 100]; ``None`` for the first ``period`` elements.
    """
    _check_period(period)
    if len(prices) < period + 1:
        return [None] * len(prices)
    arr = np.array(prices, dtype=np.float64)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    result: list[float | None] = [None] * (period + 1)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(float(100 - 100 / (1 + rs)))
    return result


def macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float | None]]:
    """MACD line, signal line, and histogram.

    Returns:
        Dict with keys ``macd``, ``signal``, ``histogram`` — each a list
        aligned with *prices*.
    """
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    macd_line: list[float | None] = []
    for f, s in zip(fast_ema, slow_ema):
        if f is None or s is None:
            macd_line.append(None)
        else:
            macd_line.append(f - s)
    valid = [v for v in macd_line if v is not None]
    if len(valid) < signal:
        signal_line: list[float | None] = [None] * len(macd_line)
    else:
        filled = [0.0 if v is None else v for v in macd_line]
        first_valid = next(i for i, v in enumerate(macd_line) if v is not None)
        sig_ema = ema(filled[first_valid:], signal)
        signal_line = [None] * first_valid + [None] * (signal - 1) + sig_ema[signal - 1:]
    histogram: list[float | None] = []
    for m, s in zip(macd_line, signal_line):
        if m is None or s is None:
            histogram.append(None)
        else:
            histogram.append(m - s)
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    """Average True Range (Wilder smoothing)."""
    _check_period(period)
    n = len(closes)
    if len(highs) != n or len(lows) != n:
        raise ValueError("highs, lows, closes must be the same length")
    tr: list[float] = []
    for i in range(n):
        high_low = highs[i] - lows[i]
        if i == 0:
            tr.append(high_low)
        else:
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            tr.append(max(high_low, high_close, low_close))
    result: list[float | None] = [None] * (period - 1)
    result.append(float(np.mean(tr[:period])))
    for i in range(period, n):
        result.append((result[-1] * (period - 1) + tr[i]) / period)  # type: ignore[operator]
    return result


def vwap(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[int],
) -> list[float]:
    """Cumulative VWAP for a single session (reset each day on the caller's side)."""
    n = len(closes)
    if not (len(highs) == len(lows) == len(volumes) == n):
        raise ValueError("highs, lows, closes, volumes must be the same length")
    typical = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(n)]
    cum_tpv = 0.0
    cum_vol = 0
    result = []
    for tp, vol in zip(typical, volumes):
        cum_tpv += tp * vol
        cum_vol += vol
        result.append(cum_tpv / cum_vol if cum_vol > 0 else tp)
    return result


def support_resistance(prices: list[float], window: int = 20) -> dict[str, float]:
    """Identify the most recent local support and resistance levels.

    Uses rolling-window min/max as a simple approximation suitable for
    the Technical Agent's evidence gathering.

    Returns:
        Dict with keys ``support`` and ``resistance``.
    """
    if len(prices) < window:
        raise ValueError(f"at least {window} prices required for support/resistance")
    arr = np.array(prices[-window:], dtype=np.float64)
    return {
        "support": float(np.min(arr)),
        "resistance": float(np.max(arr)),
    }


def _check_period(period: int) -> None:
    if not isinstance(period, int) or period < 1:
        raise ValueError(f"period must be a positive integer, got {period!r}")
