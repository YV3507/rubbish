"""Composer: cache-optimized prompt construction.

Core insight: LLM providers (DeepSeek, Anthropic) use automatic prefix caching.
The system prompt + tool descriptions must remain byte-identical across turns
for cache hits. All variable content should be appended to the *user message tail*
rather than modifying the system prompt.

Reference: Firefly pkg/agent/compose.go
"""

import hashlib
from typing import Any


class Composer:
    """Build messages while maximizing prompt cache hits.

    Usage:
        composer = Composer(system_prompt="You are...")
        composer.add_tools(tool_schemas)

        # Per-turn: add variable content to user message, not system prompt
        messages = composer.build(user_input="fix bug",
                                  plan_mode=False,
                                  memory_updates=[])
    """

    def __init__(self, system_prompt: str = ""):
        self._static_blocks: list[dict] = []
        self._dynamic_blocks: list[dict] = []
        self._cached_fingerprint: str = ""
        self._cached_static_messages: list[dict] = []

        if system_prompt:
            self._static_blocks.append({"role": "system", "content": system_prompt})

    def set_system_prompt(self, prompt: str):
        """Set or replace the system prompt (triggers cache re-fingerprint)."""
        self._static_blocks = [b for b in self._static_blocks if b["role"] != "system"]
        self._static_blocks.insert(0, {"role": "system", "content": prompt})
        self._invalidate_cache()

    def add_tools(self, tool_schemas: list[dict]):
        """Register tool schemas into the system block (static, cacheable)."""
        idx = next(
            (i for i, b in enumerate(self._static_blocks) if b["role"] == "system"),
            None,
        )
        tool_block = {"role": "system", "content": self._format_tools(tool_schemas)}
        if idx is not None:
            self._static_blocks.insert(idx + 1, tool_block)
        else:
            self._static_blocks.insert(0, tool_block)
        self._invalidate_cache()

    def add_static(self, role: str, content: str):
        """Add a static block that's the same every turn (high cache priority)."""
        self._static_blocks.append({"role": role, "content": content})
        self._invalidate_cache()

    def compose_user(self, user_input: str, **decorations: Any) -> str:
        """Decorate user input with variable context (plan mode, memory, etc).

        All decorations are appended to the user message *tail*,
        leaving the system prompt prefix byte-identical for cache hits.
        """
        parts = [user_input]

        if decorations.get("plan_mode"):
            parts.append("\n\n[Plan Mode: You must first create a plan before writing any code.]")

        if decorations.get("memory_updates"):
            updates = decorations["memory_updates"]
            parts.append(f"\n\n<memory-update>{updates}</memory-update>")

        if decorations.get("background_notifications"):
            parts.append(f"\n\n[Background tasks completed: {decorations['background_notifications']}]")

        return "\n".join(parts)

    def build(
        self,
        user_input: str,
        history: list[dict] | None = None,
        **decorations: Any,
    ) -> list[dict]:
        """Build the full messages list for an LLM call.

        Returns messages with:
        - Static blocks first (system prompt, tool descriptions) → cacheable
        - History (if provided) → partially cacheable
        - Current user message (decorated) at the end → dynamic
        """
        decorated_input = self.compose_user(user_input, **decorations)

        messages = list(self._static_blocks)

        if history:
            messages.extend(history)

        # Current turn: always last
        messages.append({"role": "user", "content": decorated_input})

        return messages

    @property
    def static_fingerprint(self) -> str:
        """MD5 hash of all static blocks for cache comparison."""
        raw = "".join(
            b.get("content", "") for b in self._static_blocks
        )
        return hashlib.md5(raw.encode()).hexdigest()

    @property
    def is_cache_hit(self) -> bool:
        """True if static blocks haven't changed since last build."""
        return self.static_fingerprint == self._cached_fingerprint

    def mark_cached(self):
        """Mark current static state as cached (call after first LLM request)."""
        self._cached_fingerprint = self.static_fingerprint

    def _invalidate_cache(self):
        self._cached_fingerprint = ""

    def _format_tools(self, schemas: list[dict]) -> str:
        """Format tool schemas into a cacheable string block."""
        import json
        lines = ["<tools>"]
        for s in schemas:
            lines.append(json.dumps(s, indent=2))
        lines.append("</tools>")
        return "\n".join(lines)
