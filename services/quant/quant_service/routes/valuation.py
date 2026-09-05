"""Valuation endpoint — deterministic range from provided inputs."""
from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter

from ..engines.valuation import (
    ValuationRange,
    dcf_valuation,
    ev_ebitda_valuation,
    forward_pe_valuation,
    pe_valuation,
    ps_valuation,
)
from ..models import QuantResult, ValuationInput, ValuationOutput

router = APIRouter(prefix="/valuation", tags=["valuation"])


def _output(ticker: str, method: str, rng: ValuationRange, current: Decimal) -> ValuationOutput:
    gap = float((rng.base - current) / current) if current != 0 else 0.0
    return ValuationOutput(
        ticker=ticker,
        method=method,
        low=rng.low.quantize(Decimal("0.01")),
        base=rng.base.quantize(Decimal("0.01")),
        high=rng.high.quantize(Decimal("0.01")),
        bear=rng.bear.quantize(Decimal("0.01")),
        bull=rng.bull.quantize(Decimal("0.01")),
        current_price=current,
        gap_pct=round(gap, 4),
        assumptions_version=datetime.date.today().isoformat(),
        is_forecast=True,
    )


@router.post("/{ticker}", response_model=QuantResult)
async def compute_valuation(ticker: str, body: ValuationInput) -> QuantResult:
    """Compute all applicable valuation methods and return the set."""
    results: list[ValuationOutput] = []
    warnings: list[str] = []

    if body.eps_ttm and body.eps_ttm > 0:
        rng = pe_valuation(body.eps_ttm, peer_pe=22.0)
        results.append(_output(ticker, "pe", rng, body.current_price))
    else:
        warnings.append("P/E skipped: eps_ttm missing or non-positive")

    if body.eps_fwd and body.eps_fwd > 0:
        rng = forward_pe_valuation(body.eps_fwd, peer_fwd_pe=20.0)
        results.append(_output(ticker, "fwd_pe", rng, body.current_price))

    if body.revenue_ttm and body.shares_outstanding and body.shares_outstanding > 0:
        rev_per_share = body.revenue_ttm / body.shares_outstanding
        rng = ps_valuation(rev_per_share, peer_ps=4.0)
        results.append(_output(ticker, "ps", rng, body.current_price))

    if body.ebitda_ttm and body.net_debt is not None and body.shares_outstanding and body.shares_outstanding > 0:
        rng = ev_ebitda_valuation(body.ebitda_ttm, body.net_debt, body.shares_outstanding, peer_ev_ebitda=14.0)
        results.append(_output(ticker, "ev_ebitda", rng, body.current_price))

    if (
        body.fcf_ttm
        and body.shares_outstanding
        and body.fcf_growth_rate is not None
        and body.terminal_growth_rate is not None
        and body.discount_rate is not None
    ):
        rng = dcf_valuation(
            body.fcf_ttm,
            growth_rate=body.fcf_growth_rate,
            terminal_growth_rate=body.terminal_growth_rate,
            discount_rate=body.discount_rate,
            shares=body.shares_outstanding,
        )
        results.append(_output(ticker, "dcf", rng, body.current_price))
    else:
        warnings.append("DCF skipped: one or more inputs missing")

    if not results:
        warnings.append("No valuation methods could be computed — insufficient inputs")

    return QuantResult(
        data=[r.model_dump() for r in results],
        sources=["inputs_provided"],
        as_of=datetime.date.today().isoformat(),
        warnings=warnings,
    )
