"""Known-answer tests for technical indicators."""

import pytest
from quant_engine.indicators import atr, ema, macd, rsi, sma, support_resistance, vwap


def test_sma_known():
    prices = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = sma(prices, period=3)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(2.0)
    assert result[4] == pytest.approx(4.0)


def test_ema_length_preserved():
    prices = list(range(1, 31))
    result = ema(prices, period=10)
    assert len(result) == 30


def test_rsi_range():
    # RSI must be in [0, 100] for every non-None value
    prices = [100.0 + i * (1 if i % 3 else -2) for i in range(50)]
    result = rsi(prices, period=14)
    valid = [v for v in result if v is not None]
    assert all(0 <= v <= 100 for v in valid)


def test_rsi_insufficient_data_returns_all_none():
    prices = [100.0] * 10
    result = rsi(prices, period=14)
    assert all(v is None for v in result)


def test_macd_returns_three_keys():
    prices = [float(i) for i in range(1, 60)]
    result = macd(prices)
    assert set(result.keys()) == {"macd", "signal", "histogram"}
    assert len(result["macd"]) == 59


def test_atr_non_negative():
    n = 20
    highs = [110.0] * n
    lows = [90.0] * n
    closes = [100.0] * n
    result = atr(highs, lows, closes, period=14)
    valid = [v for v in result if v is not None]
    assert all(v >= 0 for v in valid)


def test_vwap_between_low_and_high():
    highs = [105.0, 106.0, 107.0]
    lows = [95.0, 96.0, 97.0]
    closes = [100.0, 101.0, 102.0]
    volumes = [1000, 1000, 1000]
    result = vwap(highs, lows, closes, volumes)
    for i, v in enumerate(result):
        assert lows[i] <= v <= highs[i]


def test_support_resistance_ordering():
    prices = [100.0, 90.0, 110.0, 95.0, 105.0] * 5
    result = support_resistance(prices)
    assert result["support"] <= result["resistance"]
