"""Known-answer tests for valuation calculations."""

import pytest
from quant_engine.valuation import (
    dcf_range,
    ev_ebitda_range,
    forward_pe_range,
    pe_range,
    peer_implied_range,
    price_to_sales_range,
)


def test_pe_range_known():
    result = pe_range(eps=5.0, pe_low=20.0, pe_base=25.0, pe_high=30.0)
    assert result.low == pytest.approx(100.0)
    assert result.base == pytest.approx(125.0)
    assert result.high == pytest.approx(150.0)
    assert result.method == "pe"


def test_pe_range_rejects_negative_eps():
    with pytest.raises(ValueError, match="positive EPS"):
        pe_range(eps=-1.0, pe_low=20.0, pe_base=25.0, pe_high=30.0)


def test_forward_pe_range_known():
    result = forward_pe_range(fwd_eps=6.0, pe_low=18.0, pe_base=22.0, pe_high=26.0)
    assert result.low == pytest.approx(108.0)
    assert result.base == pytest.approx(132.0)
    assert result.high == pytest.approx(156.0)
    assert result.method == "fwd_pe"


def test_dcf_constant_fcf():
    # $10 FCF for 5 years, terminal growth 2 %, WACC 10 %, 1000 shares, no debt
    result = dcf_range(
        free_cash_flows=[10.0] * 5,
        terminal_growth_rates=(0.01, 0.02, 0.03),
        discount_rates=(0.12, 0.10, 0.08),
        shares=1000,
        net_debt=0.0,
    )
    assert result.method == "dcf"
    assert result.low < result.base < result.high
    # base case sanity: PV of $10 annuity 5yr at 10% + terminal ÷ 1000 shares
    # rough check: base value should be a few dollars per share
    assert 0.05 < result.base < 1.0


def test_dcf_rejects_wacc_below_tgr():
    with pytest.raises(ValueError, match="discount rate"):
        dcf_range(
            free_cash_flows=[10.0],
            terminal_growth_rates=(0.05, 0.05, 0.05),
            discount_rates=(0.03, 0.03, 0.03),
            shares=100,
        )


def test_ev_ebitda_range():
    # EBITDA=1000, net_debt=200, shares=100
    # bear: 1000*8 - 200 = 7800 / 100 = 78
    result = ev_ebitda_range(
        ebitda=1000.0, net_debt=200.0, shares=100,
        multiple_low=8.0, multiple_base=10.0, multiple_high=12.0,
    )
    assert result.low == pytest.approx(78.0)
    assert result.base == pytest.approx(98.0)
    assert result.high == pytest.approx(118.0)


def test_peer_implied_range_single_peer():
    result = peer_implied_range(metric_value=10.0, peer_multiples=[20.0])
    # p25 = p50 = p75 = 20.0 for a single value
    assert result.base == pytest.approx(200.0)


def test_peer_implied_range_ordering():
    result = peer_implied_range(metric_value=1.0, peer_multiples=[10.0, 20.0, 30.0, 40.0])
    assert result.low <= result.base <= result.high
