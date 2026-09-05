"""Known-answer tests for return calculations."""

import math
import pytest
from quant_engine.returns import daily_returns, total_return, annualised_return, cagr


def test_daily_returns_known_values():
    prices = [100.0, 110.0, 99.0]
    rets = daily_returns(prices)
    assert len(rets) == 2
    assert math.isclose(rets[0], math.log(110 / 100), rel_tol=1e-9)
    assert math.isclose(rets[1], math.log(99 / 110), rel_tol=1e-9)


def test_total_return_flat():
    assert total_return([100.0, 100.0]) == pytest.approx(0.0)


def test_total_return_positive():
    assert total_return([100.0, 150.0]) == pytest.approx(0.5)


def test_total_return_negative():
    assert total_return([100.0, 80.0]) == pytest.approx(-0.2)


def test_annualised_return_one_year():
    # 100 → 108 over 252 days → 8 % annualised
    prices = [100.0] + [100.0] * 251 + [108.0]
    result = annualised_return(prices)
    assert result == pytest.approx(0.08, abs=0.005)


def test_cagr_known():
    # 100 → 121 over 2 years = 10 % CAGR
    assert cagr(100.0, 121.0, 2.0) == pytest.approx(0.10, rel_tol=1e-6)


def test_daily_returns_requires_two_prices():
    with pytest.raises(ValueError, match="at least 2"):
        daily_returns([100.0])


def test_daily_returns_rejects_nonpositive():
    with pytest.raises(ValueError, match="positive"):
        daily_returns([100.0, 0.0, 110.0])
