import numpy as np
import pytest
from quant_engine import indicators


def test_sma_basic():
    prices = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = indicators.sma(prices, 3)
    assert np.isnan(result[0])
    assert np.isnan(result[1])
    np.testing.assert_allclose(result[2], 2.0)
    np.testing.assert_allclose(result[3], 3.0)
    np.testing.assert_allclose(result[4], 4.0)


def test_ema_convergence():
    prices = np.ones(50) * 100.0
    result = indicators.ema(prices, 10)
    # After enough periods, EMA of constant series = constant
    np.testing.assert_allclose(result[-1], 100.0, rtol=1e-4)


def test_rsi_overbought():
    # 20 days of strongly increasing prices -> RSI close to 100
    prices = np.linspace(100, 150, 30)
    result = indicators.rsi(prices, 14)
    assert result[-1] > 80


def test_rsi_oversold():
    prices = np.linspace(150, 100, 30)
    result = indicators.rsi(prices, 14)
    assert result[-1] < 20


def test_macd_structure():
    prices = np.random.default_rng(42).normal(100, 5, 100).cumsum() + 100
    macd_line, signal_line, histogram = indicators.macd(prices)
    # histogram = macd - signal at all finite points
    finite = np.isfinite(macd_line) & np.isfinite(signal_line)
    np.testing.assert_allclose(histogram[finite], (macd_line - signal_line)[finite], rtol=1e-9)


def test_vwap_uniform_volume():
    # Single typical price with uniform volume -> vwap = typical price
    high = np.array([110.0, 110.0, 110.0])
    low = np.array([90.0, 90.0, 90.0])
    close = np.array([100.0, 100.0, 100.0])
    volume = np.array([1000.0, 1000.0, 1000.0])
    result = indicators.vwap(high, low, close, volume)
    # typical = (110+90+100)/3 = 100
    np.testing.assert_allclose(result[-1], 100.0, rtol=1e-6)


def test_bollinger_middle_is_sma():
    prices = np.random.default_rng(5).normal(100, 5, 60)
    upper, middle, lower = indicators.bollinger_bands(prices, period=20)
    sma_vals = indicators.sma(prices, 20)
    finite = np.isfinite(middle) & np.isfinite(sma_vals)
    np.testing.assert_allclose(middle[finite], sma_vals[finite], rtol=1e-9)


def test_support_resistance_window():
    prices = np.array([50.0, 60.0, 55.0, 70.0, 65.0])
    support, resistance = indicators.support_resistance(prices, window=3)
    # last 3: [55, 70, 65] -> support=55, resistance=70
    np.testing.assert_allclose(support, 55.0)
    np.testing.assert_allclose(resistance, 70.0)
