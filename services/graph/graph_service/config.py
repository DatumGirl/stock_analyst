"""Configuration for the graph service, read from the environment.

Nothing tunable is baked into code. Missing or malformed configuration fails at
startup with a message naming the offending variable.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

ENV_HOST = "MEMGRAPH_HOST"
ENV_PORT = "MEMGRAPH_PORT"
ENV_USERNAME = "MEMGRAPH_USERNAME"
ENV_PASSWORD = "MEMGRAPH_PASSWORD"
ENV_ENCRYPTED = "MEMGRAPH_ENCRYPTED"
ENV_QUERY_TIMEOUT = "MEMGRAPH_QUERY_TIMEOUT_SECONDS"
ENV_MAX_HOPS = "GRAPH_MAX_HOPS"
ENV_MIN_SHARED_POSITIONS = "GRAPH_MIN_SHARED_POSITIONS"
ENV_MIN_EXPOSURE_WEIGHT = "GRAPH_MIN_EXPOSURE_WEIGHT"
ENV_PROPAGATION_DECAY = "GRAPH_PROPAGATION_DECAY"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7687
DEFAULT_ENCRYPTED = False
DEFAULT_QUERY_TIMEOUT_SECONDS = 30.0

#: Traversal depth for event propagation and hidden-concentration searches.
#: Beyond three hops, relationships stop carrying usable investment signal.
DEFAULT_MAX_HOPS = 3
#: A concentration is only "hidden" once several positions share the dependency.
DEFAULT_MIN_SHARED_POSITIONS = 2
#: Exposure fractions below this are noise rather than dependency.
DEFAULT_MIN_EXPOSURE_WEIGHT = 0.05
#: Per-hop attenuation applied to event impact as it propagates.
DEFAULT_PROPAGATION_DECAY = 0.5


class ConfigError(RuntimeError):
    """Raised when environment configuration is missing or malformed."""


@dataclass(frozen=True, slots=True)
class MemgraphSettings:
    """Connection settings for the Memgraph instance."""

    host: str
    port: int
    username: str
    password: str
    encrypted: bool
    query_timeout_seconds: float


@dataclass(frozen=True, slots=True)
class TraversalSettings:
    """Tunable limits shared by every relationship query."""

    max_hops: int
    min_shared_positions: int
    min_exposure_weight: float
    propagation_decay: float


@dataclass(frozen=True, slots=True)
class GraphConfig:
    """Everything the graph service needs to run."""

    memgraph: MemgraphSettings
    traversal: TraversalSettings


def load_config(env: Mapping[str, str] | None = None) -> GraphConfig:
    """Build the graph service configuration from environment variables.

    Args:
        env: Environment mapping to read; defaults to ``os.environ``.

    Returns:
        The populated configuration.

    Raises:
        ConfigError: If a variable is present but cannot be parsed, or if a
            required credential is absent.
    """
    source = os.environ if env is None else env
    memgraph = MemgraphSettings(
        host=source.get(ENV_HOST, DEFAULT_HOST),
        port=_read_int(source, ENV_PORT, DEFAULT_PORT),
        username=_require(source, ENV_USERNAME),
        password=_require(source, ENV_PASSWORD),
        encrypted=_read_bool(source, ENV_ENCRYPTED, DEFAULT_ENCRYPTED),
        query_timeout_seconds=_read_float(
            source, ENV_QUERY_TIMEOUT, DEFAULT_QUERY_TIMEOUT_SECONDS
        ),
    )
    traversal = TraversalSettings(
        max_hops=_read_int(source, ENV_MAX_HOPS, DEFAULT_MAX_HOPS),
        min_shared_positions=_read_int(
            source, ENV_MIN_SHARED_POSITIONS, DEFAULT_MIN_SHARED_POSITIONS
        ),
        min_exposure_weight=_read_float(
            source, ENV_MIN_EXPOSURE_WEIGHT, DEFAULT_MIN_EXPOSURE_WEIGHT
        ),
        propagation_decay=_read_float(
            source, ENV_PROPAGATION_DECAY, DEFAULT_PROPAGATION_DECAY
        ),
    )
    return GraphConfig(memgraph=memgraph, traversal=traversal)


def _require(env: Mapping[str, str], name: str) -> str:
    """Read a mandatory variable, or fail naming it.

    Raises:
        ConfigError: If the variable is unset or empty.
    """
    value = env.get(name, "")
    if not value:
        raise ConfigError(f"{name} is required but unset; set it in the environment")
    return value


def _read_int(env: Mapping[str, str], name: str, fallback: int) -> int:
    """Read an integer variable, falling back when unset.

    Raises:
        ConfigError: If the value is present but not an integer.
    """
    raw = env.get(name)
    if raw is None or raw == "":
        return fallback
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _read_float(env: Mapping[str, str], name: str, fallback: float) -> float:
    """Read a float variable, falling back when unset.

    Raises:
        ConfigError: If the value is present but not a number.
    """
    raw = env.get(name)
    if raw is None or raw == "":
        return fallback
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _read_bool(env: Mapping[str, str], name: str, fallback: bool) -> bool:
    """Read a boolean variable, falling back when unset.

    Raises:
        ConfigError: If the value is not a recognised boolean spelling.
    """
    raw = env.get(name)
    if raw is None or raw == "":
        return fallback
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be a boolean, got {raw!r}")
