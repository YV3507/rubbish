"""StormBreaker: continuous error injection detection.

Trips when the same (tool, error) pair repeats N consecutive times.
Per-tool tracking: one tool succeeding resets only its own counter.

Configurable via config.stormbreaker_max_consecutive_errors.

Reference: Firefly pkg/agent/stormbreaker.go
"""

from app.config import config


class StormBreaker:
    """Detect repeated errors per tool across tool calls."""

    def __init__(self, max_consecutive_errors: int | None = None):
        self._max_errors = max_consecutive_errors or config.stormbreaker_max_consecutive_errors
        # Key: (tool_name, error_message) → consecutive count
        self._counts: dict[tuple[str, str], int] = {}
        # Per-tool success tracking: tool_name → success_seen
        self._tool_success: dict[str, bool] = {}
        self.tripped = False
        self._last_tripped_msg: str = ""

    def record(self, results: list):
        """Record tool results and detect repeated errors per tool."""
        if not results:
            return

        for r in results:
            tool_name = getattr(r, "tool_call_id", "unknown")
            error = getattr(r, "error", None)

            if error:
                key = (tool_name, str(error))
                self._counts[key] = self._counts.get(key, 0) + 1
                self._tool_success[tool_name] = False

                if self._counts[key] >= self._max_errors:
                    self.tripped = True
                    self._last_tripped_msg = (
                        f'[loop guard] "{tool_name}" has failed '
                        f'{self._counts[key]} times with the same error: {error}. '
                        f"Re-sending with reworded arguments will not help. "
                        f"Change approach: split the work, use a different tool, "
                        f"or explain the blocker."
                    )
            else:
                # Success — reset *this tool's* counters only
                tool_name = getattr(r, "tool_call_id", "unknown")
                self._tool_success[tool_name] = True
                keys_to_remove = [k for k in self._counts if k[0] == tool_name]
                for k in keys_to_remove:
                    del self._counts[k]

        # If all tools succeeded, clear global trip
        if not self.tripped:
            return

        # Re-check: if the problematic tool later succeeded, un-trip
        for key in list(self._counts.keys()):
            tool_name = key[0]
            if self._tool_success.get(tool_name, False):
                del self._counts[key]

        self.tripped = bool(self._counts)
        if not self.tripped:
            self._last_tripped_msg = ""

    @property
    def message(self) -> str:
        return self._last_tripped_msg

    def reset(self):
        self._counts.clear()
        self._tool_success.clear()
        self.tripped = False
        self._last_tripped_msg = ""
