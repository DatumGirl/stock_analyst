"""Environment-driven configuration parsing and its failure modes."""

from __future__ import annotations

import pytest

from graph_service.config import (
    DEFAULT_MAX_HOPS,
    DEFAULT_PORT,
    ConfigError,
    load_config,
)

MINIMAL_ENV = {"MEMGRAPH_USERNAME": "analyst", "MEMGRAPH_PASSWORD": "secret"}


def test_load_config_applies_documented_defaults() -> None:
    config = load_config(MINIMAL_ENV)
    assert config.memgraph.port == DEFAULT_PORT
    assert config.memgraph.encrypted is False
    assert config.traversal.max_hops == DEFAULT_MAX_HOPS


def test_load_config_reads_overrides() -> None:
    config = load_config(
        MINIMAL_ENV | {"MEMGRAPH_PORT": "7688", "GRAPH_MAX_HOPS": "2", "MEMGRAPH_ENCRYPTED": "yes"}
    )
    assert config.memgraph.port == 7688
    assert config.memgraph.encrypted is True
    assert config.traversal.max_hops == 2


def test_load_config_names_the_missing_credential() -> None:
    with pytest.raises(ConfigError, match="MEMGRAPH_PASSWORD is required"):
        load_config({"MEMGRAPH_USERNAME": "analyst"})


def test_load_config_treats_empty_credential_as_missing() -> None:
    with pytest.raises(ConfigError, match="MEMGRAPH_USERNAME is required"):
        load_config({"MEMGRAPH_USERNAME": "", "MEMGRAPH_PASSWORD": "secret"})


def test_load_config_rejects_non_integer_port() -> None:
    with pytest.raises(ConfigError, match="MEMGRAPH_PORT must be an integer"):
        load_config(MINIMAL_ENV | {"MEMGRAPH_PORT": "seven"})


def test_load_config_rejects_non_numeric_weight() -> None:
    with pytest.raises(ConfigError, match="GRAPH_MIN_EXPOSURE_WEIGHT must be a number"):
        load_config(MINIMAL_ENV | {"GRAPH_MIN_EXPOSURE_WEIGHT": "low"})


def test_load_config_rejects_unrecognised_boolean() -> None:
    with pytest.raises(ConfigError, match="MEMGRAPH_ENCRYPTED must be a boolean"):
        load_config(MINIMAL_ENV | {"MEMGRAPH_ENCRYPTED": "maybe"})


def test_load_config_falls_back_on_empty_optional_value() -> None:
    config = load_config(MINIMAL_ENV | {"GRAPH_MAX_HOPS": ""})
    assert config.traversal.max_hops == DEFAULT_MAX_HOPS
