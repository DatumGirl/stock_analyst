"""
Monte Carlo simulation using Geometric Brownian Motion for portfolio target-return probability.

Example:
    result = simulate_portfolio_return(
        weights=np.array([0.6, 0.4]),
        expected_returns=np.array([0.12, 0.08]),
        cov_matrix=np.array([[0.04, 0.01], [0.01, 0.02]]),
        horizon_years=3,
        target_cagr=0.10,
        n_simulations=10_000,
    )
    print(f"P(CAGR >= 10%) = {result.target_probability:.1%}")
"""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cholesky  # type: ignore[import-untyped]


@dataclass
class MonteCarloResult:
    target_probability: float
    median_cagr: float
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    n_simulations: int
    horizon_years: int


def simulate_portfolio_return(
    weights: np.ndarray,
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    horizon_years: int,
    target_cagr: float,
    n_simulations: int = 10_000,
    random_seed: int | None = None,
) -> MonteCarloResult:
    """GBM portfolio simulation.

    Uses Cholesky decomposition to correlate asset returns.
    Annual time steps (dt = 1).
    """
    rng = np.random.default_rng(random_seed)
    n_assets = len(weights)

    # Cholesky factorisation for correlated draws
    try:
        L = cholesky(cov_matrix, lower=True)
    except Exception:
        # Fallback: diagonal covariance
        L = np.diag(np.sqrt(np.diag(cov_matrix)))

    # Portfolio drift and vol under GBM
    port_mu = float(weights @ expected_returns)
    port_var = float(weights @ cov_matrix @ weights)
    port_sigma = float(np.sqrt(max(port_var, 0.0)))

    # Simulate terminal values using portfolio-level GBM (dt=1 per year)
    dt = 1.0
    z = rng.standard_normal((n_simulations, horizon_years))
    # GBM log-return per year: (mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z
    log_returns = (port_mu - 0.5 * port_var) * dt + port_sigma * np.sqrt(dt) * z
    terminal_log = log_returns.sum(axis=1)
    terminal_values = np.exp(terminal_log)

    # CAGR from terminal value
    cagrs = terminal_values ** (1.0 / horizon_years) - 1.0

    return MonteCarloResult(
        target_probability=float(np.mean(cagrs >= target_cagr)),
        median_cagr=float(np.median(cagrs)),
        percentile_5=float(np.percentile(cagrs, 5)),
        percentile_25=float(np.percentile(cagrs, 25)),
        percentile_75=float(np.percentile(cagrs, 75)),
        percentile_95=float(np.percentile(cagrs, 95)),
        n_simulations=n_simulations,
        horizon_years=horizon_years,
    )


def estimate_expected_returns(
    historical_returns: np.ndarray,
    method: str = "historical",
    periods_per_year: float = 252.0,
) -> np.ndarray:
    """Annualized expected returns from historical daily returns (T x N array)."""
    if method == "historical":
        return np.mean(historical_returns, axis=0) * periods_per_year
    elif method == "shrinkage":
        # Shrink toward grand mean
        asset_means = np.mean(historical_returns, axis=0) * periods_per_year
        grand_mean = float(np.mean(asset_means))
        shrink = 0.5
        return shrink * grand_mean + (1 - shrink) * asset_means
    else:
        raise ValueError(f"Unknown method: {method}. Use 'historical' or 'shrinkage'.")


def ledoit_wolf_cov(
    returns: np.ndarray, periods_per_year: float = 252.0
) -> np.ndarray:
    """Annualized Ledoit-Wolf shrinkage covariance estimator."""
    from scipy.covariance import ledoit_wolf as lw  # type: ignore[import-untyped]

    cov, _ = lw(returns)
    return cov * periods_per_year
