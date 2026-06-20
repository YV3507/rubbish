"""Prefix cache alignment and warmup for prompt caching."""

import hashlib


class CacheAlignment:
    """Manage prompt cache alignment for provider-level caching."""

    def __init__(self):
        self._cached_fingerprint = ""

    def split_boundary(self, messages: list) -> tuple[list, list]:
        """Split messages into static (system) and dynamic (user/assistant) parts."""
        static = [m for m in messages if m.get("role") == "system"]
        dynamic = [m for m in messages if m.get("role") != "system"]
        return static, dynamic

    def fingerprint(self, messages: list) -> str:
        """Compute a fingerprint for cache comparison."""
        raw = "".join(
            m.get("content", "") for m in messages if m.get("role") == "system"
        )
        return hashlib.md5(raw.encode()).hexdigest()

    def is_cache_hit(self, messages: list) -> bool:
        """Check if the static portion matches the cached one."""
        return self.fingerprint(messages) == self._cached_fingerprint

    def mark_cached(self, messages: list):
        self._cached_fingerprint = self.fingerprint(messages)
