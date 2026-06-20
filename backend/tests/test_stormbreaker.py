"""Tests for enhanced StormBreaker (Firefly-style per-tool tracking)."""

import pytest

from app.core.stormbreaker import StormBreaker


class MockResult:
    def __init__(self, name: str = "tool", error: str | None = None):
        self.tool_call_id = name
        self.error = error


def test_per_tool_tracking():
    """Different tools have independent error counters."""
    sb = StormBreaker(max_consecutive_errors=3)

    # Tool A fails once, Tool B fails 3 times
    sb.record([MockResult(name="read"), MockResult(name="edit", error="err")])
    sb.record([MockResult(name="read"), MockResult(name="edit", error="err")])
    sb.record([MockResult(name="read"), MockResult(name="edit", error="err")])

    assert sb.tripped  # edit has 3 consecutive errors
    assert "edit" in sb.message


def test_success_resets_own_tool_only():
    """Success on one tool does not reset another tool's counter."""
    sb = StormBreaker(max_consecutive_errors=2)

    sb.record([MockResult(name="edit", error="err")])
    sb.record([MockResult(name="read"), MockResult(name="edit", error="err")])

    # read succeeded, edit failed again
    assert sb.tripped
    assert "edit" in sb.message


def test_no_false_positive():
    """Different errors on same tool do not accumulate."""
    sb = StormBreaker(max_consecutive_errors=2)

    sb.record([MockResult(name="edit", error="timeout")])
    sb.record([MockResult(name="edit", error="permission_denied")])

    assert not sb.tripped  # different errors


def test_reset_clears_all():
    """Reset clears all counters."""
    sb = StormBreaker(max_consecutive_errors=2)
    sb.record([MockResult(name="edit", error="err")])
    sb.record([MockResult(name="edit", error="err")])
    assert sb.tripped

    sb.reset()
    assert not sb.tripped
    assert sb.message == ""
