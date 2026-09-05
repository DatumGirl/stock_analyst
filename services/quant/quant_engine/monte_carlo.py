"""Monte Carlo simulation for portfolio target-return probability.

The simulation is reproducible given a fixed seed, so results are auditable.
All randomness is seeded by the caller; the function itself is deterministic
given the same inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    """Output of a portfolio simulation run.

    Attributes:
        target_probability: Fraction of paths that meet or exceed the target CAGR.
        mean_cagr: Mean CAGR across all simulation paths.
        percentile_5: 5th-percentile CAGR (worst-case estimate).
        percentile_50: Median CAGR.
        percentile_95: 95th-percentile CAGR (best-case estimate).
        n_paths: Number of simulation paths run.
    """

    target_probability: float
    mean_cagr: float
    percentile_5: float
    percentile_50: float
    percentile_95: float
    n_paths: int

    def to_dict(self) -> dict[str, object]:
        return {
            "target_probability": self.target_probability,
            "mean_cagr": self.mean_cagr,
            "percentile_5": self.percentile_5,
            "percentile_50": self.percentile_50,
            "percentile_95": self.percentile_95,
            "n_paths": self.n_paths,
        }


def simulate_portfolio_cagr(
    annual_mean_return: float,
    annual_volatility: float,
    horizon_years: int,
    target_cagr: float,
    n_paths: int = 10_000,
    seed: int = 42,
) -> MonteCarloResult:
    """Simulate portfolio terminal CAGR distribution using GBM.

    Args:
        annual_mean_return: Expected annualised return (fraction, e.g. 0.08).
        annual_volatility: Annualised volatility (fraction, e.g. 0.18).
        horizon_years: Investment horizon in years.
        target_cagr: The CAGR objective (e.g. 0.12 for 12 %).
        n_paths: Number of Monte Carlo paths.
        seed: Random seed for reproducibility.

    Returns:
        Simulation result including target probability and percentile CAGRs.
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")
    if annual_volatility < 0:
        raise ValueError("volatility must be non-negative")
    if n_paths < 100:
        raise ValueError("n_paths must be at least 100 for reliable estimates")

    rng = np.random.default_rng(seed)
    dt = 1.0 / 252
    steps = horizon_years * 252
    drift = (annual_mean_return - 0.5 * annual_volatility**2) * dt
    diffusion = annual_volatility * np.sqrt(dt)

    # Shape: (n_paths, steps)
    z = rng.standard_normal((n_paths, steps))
    log_returns = drift + diffusion * z
    terminal_log = np.sum(log_returns, axis=1)
    terminal_value = np.exp(terminal_log)

    cagrs = terminal_value ** (1.0 / horizon_years) - 1

    return MonteCarloResult(
        target_probability=float(np.mean(cagrs >= target_cagr)),
        mean_cagr=float(np.mean(cagrs)),
        percentile_5=float(np.percentile(cagrs, 5)),
        percentile_50=float(np.percentile(cagrs, 50)),
        percentile_95=float(np.percentile(cagrs, 95)),
        n_paths=n_paths,
    )
