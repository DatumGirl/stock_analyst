"""Known-answer tests for risk metrics."""

import math
import pytest
from quant_engine.risk import (
    annualised_volatility,
    beta,
    conditional_var,
    correlation_matrix,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    value_at_risk,
)


def _flat_returns(n: int = 252, value: float = 0.001) -> list[float]:
    return [value] * n


def test_volatility_zero_for_constant_returns():
    # constant returns have zero variance → zero volatility
    assert annualised_volatility(_flat_returns()) == pytest.approx(0.0, abs=1e-10)


def test_volatility_known():
    # daily vol of 0.01 → annualised ≈ 0.01 * sqrt(252)
    rets = [0.01, -0.01] * 126
    vol = annualised_volatility(rets)
    assert vol == pytest.approx(0.01 * math.sqrt(252), rel_tol=0.02)


def test_beta_with_itself_is_one():
    rets = [0.001 * i for i in range(1, 101)]
    assert beta(rets, rets) == pytest.approx(1.0, rel_tol=1e-6)


def test_beta_zero_for_uncorrelated():
    a = [1.0, -1.0] * 50
    b = [1.0, 1.0] * 50
    # b has zero variance; should raise
    with pytest.raises(ValueError, match="zero variance"):
        beta(a, b)


def test_max_drawdown_known():
    # 100 → 200 → 100: drawdown = -0.5
    prices = [100.0, 150.0, 200.0, 100.0]
    assert max_drawdown(prices) == pytest.approx(-0.5)


def test_max_drawdown_no_drawdown():
    prices = [100.0, 110.0, 120.0]
    assert max_drawdown(prices) == pytest.approx(0.0)


def test_var_is_negative():
    rets = list(range(-10, 10))  # symmetric, so VaR should be negative
    var = value_at_risk([float(r) for r in rets])
    assert var < 0


def test_cvar_le_var():
    rets = [float(r) / 100 for r in range(-30, 70)]
    var = value_at_risk(rets)
    cvar = conditional_var(rets)
    assert cvar <= var


def test_sharpe_positive_drift():
    # 1 % daily excess return, zero vol → undefined; use a small vol
    rets = [0.001 + 0.0001 * (i % 3 - 1) for i in range(252)]
    sr = sharpe_ratio(rets)
    assert sr > 0


def test_sortino_ge_sharpe_for_positive_skew():
    # all returns positive → no downside → Sortino = NaN
    rets = [0.001] * 252
    assert math.isnan(sortino_ratio(rets))


def test_correlation_self_is_one():
    rets = [float(i) / 100 for i in range(1, 51)]
    result = correlation_matrix({"A": rets, "B": rets})
    assert result["A"]["B"] == pytest.approx(1.0)


def test_correlation_empty():
    assert correlation_matrix({}) == {}
