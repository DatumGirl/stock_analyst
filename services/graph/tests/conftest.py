"""Shared fixtures: a recording fake runner and standard traversal settings."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph_service.config import TraversalSettings  # noqa: E402


@dataclass
class FakeRunner:
    """A :class:`QueryRunner` that records calls and replays canned rows.

    Args:
        rows: Rows every ``run`` call returns.
        calls: Recorded ``(cypher, parameters)`` pairs, in call order.
    """

    rows: list[dict[str, Any]] = field(default_factory=list)
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def run(self, cypher: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        """Record the call and return the canned rows."""
        self.calls.append((cypher, parameters))
        return list(self.rows)


@pytest.fixture
def runner() -> FakeRunner:
    """Return an empty recording runner."""
    return FakeRunner()


@pytest.fixture
def traversal() -> TraversalSettings:
    """Return traversal settings with explicit, non-default values."""
    return TraversalSettings(
        max_hops=3,
        min_shared_positions=2,
        min_exposure_weight=0.05,
        propagation_decay=0.5,
    )
