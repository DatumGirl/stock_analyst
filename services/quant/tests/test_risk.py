import numpy as np
import pytest
from quant_engine import risk


def test_annualized_volatility_known():
    # Daily returns with daily std = 0.01 -> annualized vol ≈ 0.01 * sqrt(252)
    rng = np.random.default_rng(42)
    rets = rng.normal(0, 0.01, 500)
    vol = risk.annualized_volatility(rets)
    expected = np.std(rets, ddof=1) * np.sqrt(252)
    np.testing.assert_allclose(vol, expected, rtol=1e-6)


def test_annualized_volatility_insufficient():
    assert np.isnan(risk.annualized_volatility(np.array([0.01])))


def test_beta_double_market():
    market = np.array([0.01, -0.02, 0.015, -0.005, 0.02])
    asset = 2.0 * market
    np.testing.assert_allclose(risk.beta(asset, market), 2.0, rtol=1e-6)


def test_beta_uncorrelated():
    rng = np.random.default_rng(0)
    market = rng.normal(0, 0.01, 1000)
    asset = rng.normal(0, 0.01, 1000)  # independent
    b = risk.beta(asset, market)
    assert abs(b) < 0.15  # near zero with high probability


def test_beta_zero_market_variance():
    market = np.ones(10) * 0.01
    asset = np.random.default_rng(0).normal(0, 0.01, 10)
    assert np.isnan(risk.beta(asset, market))


def test_max_drawdown_known():
    prices = np.array([100.0, 110.0, 105.0, 90.0, 95.0])
    # Peak 110 -> trough 90: drawdown = (90-110)/110
    dd = risk.max_drawdown(prices)
    np.testing.assert_allclose(dd, (90 - 110) / 110, rtol=1e-6)


def test_max_drawdown_monotone_increase():
    prices = np.array([100.0, 101.0, 102.0, 103.0])
    assert risk.max_drawdown(prices) >= -0.01  # essentially 0


def test_var_95_basic():
    rng = np.random.default_rng(7)
    rets = rng.normal(0, 0.01, 1000)
    var = risk.var_historical(rets, 0.95)
    # 5% of 1000 = 50 worst returns; var should be positive loss
    assert var > 0
    # VaR at 95% means 5% of returns are worse
    fraction_worse = np.mean(rets <= -var)
    np.testing.assert_allclose(fraction_worse, 0.05, atol=0.01)


def test_cvar_geq_var():
    rng = np.random.default_rng(99)
    rets = rng.normal(0, 0.02, 500)
    var = risk.var_historical(rets)
    cvar = risk.cvar_historical(rets)
    assert cvar >= var - 1e-10


def test_sharpe_zero_vol():
    rets = np.zeros(100)
    assert np.isnan(risk.sharpe_ratio(rets))


def test_portfolio_volatility_perfect_correlation():
    # Two assets with same vol, perfectly correlated -> portfolio vol = vol
    vol = 0.20
    cov = np.array([[vol**2, vol**2], [vol**2, vol**2]])
    weights = np.array([0.5, 0.5])
    port_vol = risk.portfolio_volatility(weights, cov)
    np.testing.assert_allclose(port_vol, vol, rtol=1e-6)


def test_portfolio_volatility_uncorrelated():
    # Two equal-weight uncorrelated assets with same vol -> portfolio vol = vol / sqrt(2)
    vol = 0.20
    cov = np.array([[vol**2, 0.0], [0.0, vol**2]])
    weights = np.array([0.5, 0.5])
    port_vol = risk.portfolio_volatility(weights, cov)
    np.testing.assert_allclose(port_vol, vol / np.sqrt(2), rtol=1e-6)
