"""Tests for config schema and config store."""

import json
import pytest

from app.config.schema import ConfigSchema
from app.config.store import ConfigStore


def test_config_defaults():
    """ConfigSchema returns sensible default values."""
    cfg = ConfigSchema()
    d = cfg.to_dict()
    assert d["agent_max_turns"] == 50
    assert d["stormbreaker_max_consecutive_errors"] == 3
    assert d["tool_max_concurrent_reads"] == 8


def test_config_types():
    """ConfigSchema fields have correct types."""
    cfg = ConfigSchema()
    d = cfg.to_dict()
    assert isinstance(d["agent_max_turns"], int)
    assert isinstance(d["agent_water_level_threshold"], float)
    assert isinstance(d["compute_impact_rwr_alpha"], float)


def test_config_overrides():
    """ConfigStore correctly applies overrides."""
    store = ConfigStore()
    overrides = {"agent_max_turns": 10, "stormbreaker_max_consecutive_errors": 5}
    cfg = store.save(overrides)
    assert cfg.agent_max_turns == 10
    assert cfg.stormbreaker_max_consecutive_errors == 5


def test_config_store_persists(tmp_path):
    """ConfigStore persists overrides to disk and loads them back."""
    store = ConfigStore(path=str(tmp_path / "cfg.json"))
    store.save({"agent_max_turns": 99})

    cfg = ConfigSchema()
    loaded = store.load(cfg)
    assert loaded.agent_max_turns == 99


def test_config_defaults_class_method():
    """ConfigSchema.defaults() returns a dict of all defaults."""
    d = ConfigSchema.defaults()
    assert isinstance(d, dict)
    assert d["agent_max_turns"] == 50
