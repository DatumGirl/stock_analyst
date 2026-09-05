"""Pure technical analysis indicators. No I/O."""

import numpy as np


def sma(prices: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average. First period-1 values are nan."""
    result = np.full(len(prices), float("nan"))
    for i in range(period - 1, len(prices)):
        result[i] = float(np.mean(prices[i - period + 1 : i + 1]))
    return result


def ema(prices: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average with alpha = 2/(period+1)."""
    result = np.full(len(prices), float("nan"))
    if len(prices) < period:
        return result
    alpha = 2.0 / (period + 1)
    result[period - 1] = float(np.mean(prices[:period]))
    for i in range(period, len(prices)):
        result[i] = alpha * prices[i] + (1 - alpha) * result[i - 1]
    return result


def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index using Wilder's smoothing (alpha = 1/period)."""
    result = np.full(len(prices), float("nan"))
    if len(prices) < period + 1:
        return result
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    # seed with simple average
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for i in range(period, len(prices)):
        idx = i - 1  # index into deltas
        avg_gain = (avg_gain * (period - 1) + gains[idx]) / period
        avg_loss = (avg_loss * (period - 1) + losses[idx]) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - 100.0 / (1.0 + rs)
    return result


def macd(
    prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD line, signal line, and histogram."""
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Average True Range using Wilder's smoothing."""
    result = np.full(len(close), float("nan"))
    if len(close) < period + 1:
        return result
    tr = np.zeros(len(close))
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    avg = float(np.mean(tr[1 : period + 1]))
    result[period] = avg
    for i in range(period + 1, len(close)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def vwap(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
) -> np.ndarray:
    """Cumulative Volume Weighted Average Price."""
    typical = (high + low + close) / 3.0
    cum_vol = np.cumsum(volume)
    cum_tpv = np.cumsum(typical * volume)
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(cum_vol > 0, cum_tpv / cum_vol, float("nan"))
    return result


def relative_volume(volume: np.ndarray, period: int = 20) -> np.ndarray:
    """Current volume / average volume over period."""
    result = np.full(len(volume), float("nan"))
    avg = sma(volume.astype(float), period)
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(avg > 0, volume / avg, float("nan"))
    return result


def bollinger_bands(
    prices: np.ndarray, period: int = 20, num_std: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Upper, middle, lower Bollinger Bands."""
    middle = sma(prices, period)
    result_upper = np.full(len(prices), float("nan"))
    result_lower = np.full(len(prices), float("nan"))
    for i in range(period - 1, len(prices)):
        std = float(np.std(prices[i - period + 1 : i + 1], ddof=1))
        result_upper[i] = middle[i] + num_std * std
        result_lower[i] = middle[i] - num_std * std
    return result_upper, middle, result_lower


def support_resistance(
    prices: np.ndarray, window: int = 10
) -> tuple[float, float]:
    """Recent support (low) and resistance (high) from last window prices."""
    recent = prices[-window:]
    return float(np.min(recent)), float(np.max(recent))
