import pytest
from quant_engine.valuation import (
    ValuationResult,
    aggregate_valuation,
    dcf_valuation,
    forward_pe_valuation,
    historical_range_valuation,
    p_fcf_valuation,
    pe_valuation,
    peer_valuation,
    peg_valuation,
    ps_valuation,
)


def test_pe_valuation_known():
    result = pe_valuation(eps=5.0, pe_low=15.0, pe_base=20.0, pe_high=25.0)
    assert result.method == "pe"
    assert pytest.approx(result.low, rel=1e-6) == 75.0
    assert pytest.approx(result.base, rel=1e-6) == 100.0
    assert pytest.approx(result.high, rel=1e-6) == 125.0


def test_pe_negative_eps_raises():
    with pytest.raises(ValueError):
        pe_valuation(eps=0.0, pe_low=15.0, pe_base=20.0, pe_high=25.0)


def test_dcf_low_wacc_higher_value():
    result_low_wacc = dcf_valuation(
        fcf_per_share=10.0,
        growth_rates=[0.10] * 5,
        terminal_growth=0.025,
        discount_rates=(0.07, 0.10, 0.12),
    )
    result_high_wacc = dcf_valuation(
        fcf_per_share=10.0,
        growth_rates=[0.10] * 5,
        terminal_growth=0.025,
        discount_rates=(0.10, 0.12, 0.15),
    )
    # Lower WACC range -> higher valuations
    assert result_low_wacc.base > result_high_wacc.base


def test_dcf_ordering():
    result = dcf_valuation(
        fcf_per_share=8.0,
        growth_rates=[0.12, 0.10, 0.08, 0.06, 0.05],
        terminal_growth=0.025,
    )
    assert result.low <= result.base <= result.high
    assert result.bear <= result.low


def test_valuation_result_ordering_all_methods():
    results = [
        pe_valuation(5.0, 15.0, 20.0, 25.0),
        forward_pe_valuation(5.5, 14.0, 18.0, 23.0),
        peg_valuation(5.0, 0.15, 2.0),
        ps_valuation(30.0, 3.0, 5.0, 8.0),
        p_fcf_valuation(8.0, 15.0, 22.0, 30.0),
        dcf_valuation(8.0, [0.10] * 5),
        historical_range_valuation(5.0, 14.0, 20.0, 28.0),
        peer_valuation(5.0, 16.0, 21.0, 27.0),
    ]
    for r in results:
        assert r.low <= r.base, f"{r.method}: low > base"
        assert r.base <= r.high, f"{r.method}: base > high"
        assert r.bear <= r.low, f"{r.method}: bear > low"
        assert r.high <= r.bull, f"{r.method}: high > bull"


def test_aggregate_valuation():
    r1 = pe_valuation(5.0, 15.0, 20.0, 25.0)   # base=100
    r2 = forward_pe_valuation(5.5, 14.0, 18.0, 23.0)  # base=99
    agg = aggregate_valuation([r1, r2])
    assert agg["low"] == min(r1.low, r2.low)
    assert agg["high"] == max(r1.high, r2.high)
    assert pytest.approx(agg["base"], rel=1e-6) == (r1.base + r2.base) / 2
