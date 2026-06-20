"""Centralized configuration schema — single source of truth for all tunable parameters.

All "magic numbers" from the codebase are declared here and served via API
so the WebUI can render a dynamic configuration panel.

Environment variable overrides are loaded at startup:
  LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, COMPUTE_NODE_URL
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Any


def _env(key: str, default: Any, type_cast: type = str) -> Any:
    """Read environment variable with optional type cast."""
    val = os.getenv(key)
    if val is None:
        return default
    if type_cast is bool:
        return val.lower() in ("1", "true", "yes", "on")
    return type_cast(val)


@dataclass
class ConfigSchema:
    # ── Agent ──
    agent_max_turns: int = 50
    agent_water_level_threshold: float = 0.8
    agent_offload_threshold_bytes: int = 20_000

    # ── LLM ──
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_deepseek_prompt_cache_block_size: int = 128
    llm_warmup_threshold_chars: int = 5_000
    llm_warmup_prefill_tokens: int = 2
    llm_short_prompt_threshold_chars: int = 2_000

    # ── Tool Executor ──
    tool_max_concurrent_reads: int = 8
    tool_shell_default_timeout_sec: int = 30

    # ── Session / Compactor ──
    session_token_budget: int = 128_000
    session_tokens_per_char: int = 4
    session_soft_limit_bytes: int = 100_000

    # ── MicroCompact (time-aware compression aligned with cache TTL) ──
    microcompact_ttl_seconds: int = 300  # 5 min, matching Anthropic prompt cache TTL
    microcompact_keep_recent: int = 5    # preserve last N assistant + tool entries

    # ── StormBreaker ──
    stormbreaker_max_consecutive_errors: int = 3

    # ── AutoPlan (two-stage planning detection) ──
    autoplan_heuristic_threshold: int = 2  # score >= triggers plan; 1-2 calls LLM classifier
    autoplan_classifier_timeout_sec: int = 3
    autoplan_keywords: str = "refactor,redesign,architect,migrate,implement,design,structur"  # heuristic keywords

    # ── Rust Compute Node ──
    compute_node_url: str = "http://localhost:8080"
    compute_graph_explore_default_depth: int = 5
    compute_impact_rwr_alpha: float = 0.25
    compute_impact_rwr_iterations: int = 100

    # ── Frontend ──
    frontend_message_max_width_pct: int = 80
    frontend_scroll_behavior: str = "smooth"

    # ── Metadata ──
    _meta: dict = field(default_factory=lambda: {
        "description": "Rubbish project runtime configuration",
        "version": "1",
    })

    def apply_env_overrides(self):
        """Override fields from environment variables."""
        self.llm_api_key = _env("LLM_API_KEY", self.llm_api_key)
        self.llm_base_url = _env("LLM_BASE_URL", self.llm_base_url)
        self.llm_model = _env("LLM_MODEL", self.llm_model)
        self.llm_provider = _env("LLM_PROVIDER", self.llm_provider)
        self.compute_node_url = _env("COMPUTE_NODE_URL", self.compute_node_url)
        self.agent_max_turns = _env("AGENT_MAX_TURNS", self.agent_max_turns, int)
        self.tool_shell_default_timeout_sec = _env(
            "TOOL_SHELL_TIMEOUT", self.tool_shell_default_timeout_sec, int
        )

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if not k.startswith("_")}

    @classmethod
    def defaults(cls) -> dict[str, Any]:
        return cls().to_dict()
