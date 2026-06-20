"""Tests for Agent definition system and SubAgentGate."""

import pytest
from app.agentdef.loader import AgentDef, SubAgentGate


def test_agent_def_to_system_prompt():
    """AgentDef generates a complete system prompt."""
    agent = AgentDef(
        name="explore",
        description="Code exploration agent",
        when_to_use="When needing to search the codebase",
        tools=["read", "grep", "glob"],
        instructions="Search carefully and report findings.",
    )
    prompt = agent.to_system_prompt()
    assert "explore" in prompt
    assert "read, grep, glob" in prompt
    assert "Search carefully" in prompt


def test_gate_blocks_unauthorized_tool():
    """SubAgentGate denies tools not in allowed list."""
    gate = SubAgentGate(allowed_tools=["read", "grep"])
    assert gate.check("read")
    assert gate.check("grep")
    assert not gate.check("edit")
    assert not gate.check("shell")


def test_gate_allows_all_when_empty():
    """Empty allowed list = allow all."""
    gate = SubAgentGate()
    assert gate.check("read")
    assert gate.check("edit")
    assert gate.check("anything")


def test_gate_deny_message():
    """Deny message includes allowed tools."""
    gate = SubAgentGate(allowed_tools=["read"])
    msg = gate.deny_message("edit")
    assert "edit" in msg
    assert "read" in msg


def test_agent_def_defaults():
    """AgentDef has sensible defaults."""
    agent = AgentDef(
        name="test",
        description="test agent",
        when_to_use="testing",
    )
    assert agent.max_turns == 20
    assert agent.tools == []
    assert agent.model == ""
