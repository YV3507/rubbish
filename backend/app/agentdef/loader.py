"""Agent definition system: YAML frontmatter + Markdown body format.

Allows defining sub-agents with restricted tool sets,
model selection, and purpose descriptions.

Reference: Firefly pkg/agent/agentdef/, pkg/agent/subagent_gate.go
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentDef:
    """Definition of a reusable sub-agent."""

    name: str
    description: str
    when_to_use: str
    model: str = ""
    tools: list[str] = field(default_factory=list)
    instructions: str = ""
    max_turns: int = 20

    def to_system_prompt(self) -> str:
        """Build the system prompt for this agent."""
        parts = [f"You are the {self.name} agent.", self.instructions]
        if self.description:
            parts.insert(1, f"\nDescription: {self.description}")
        if self.when_to_use:
            parts.append(f"\nUse this agent when: {self.when_to_use}")
        if self.tools:
            parts.append(f"\nAvailable tools: {', '.join(self.tools)}")
        return "\n".join(parts)


class AgentDefLoader:
    """Scan and load agent definitions from .md files with YAML frontmatter."""

    def __init__(self, base_dir: str = ".firefly/agents"):
        self._base = Path(base_dir)

    def scan(self) -> list[AgentDef]:
        """Scan the agents directory and return all definitions."""
        if not self._base.exists():
            return []

        agents: list[AgentDef] = []
        for f in sorted(self._base.glob("*.md")):
            agent = self._parse_file(f)
            if agent:
                agents.append(agent)
        return agents

    def _parse_file(self, path: Path) -> AgentDef | None:
        """Parse a single .md file with YAML frontmatter."""
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return None

        # Extract YAML frontmatter (---\n...\n---)
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not m:
            return None

        yaml_block = m.group(1)
        body = m.group(2).strip()

        metadata = self._parse_yaml_simple(yaml_block)

        return AgentDef(
            name=metadata.get("name", path.stem),
            description=metadata.get("description", ""),
            when_to_use=metadata.get("whenToUse", metadata.get("when_to_use", "")),
            model=metadata.get("model", ""),
            tools=metadata.get("tools", []),
            instructions=body,
            max_turns=int(metadata.get("max_turns", 20)),
        )

    def _parse_yaml_simple(self, text: str) -> dict[str, Any]:
        """Minimal YAML parser (no pyyaml dependency needed at this stage)."""
        result: dict[str, Any] = {}
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Handle list values
                if value.startswith("["):
                    value = json.loads(value.replace("'", '"'))
                result[key] = value
        return result


class SubAgentGate:
    """Runtime tool access gate for sub-agents.

    Instead of filtering the tool list at registration time (which would
    change the system prompt and break cache), allow all tools to be
    registered but deny at execution time.

    Reference: Firefly pkg/agent/subagent_gate.go
    """

    def __init__(self, allowed_tools: list[str] | None = None):
        self._allowed = set(allowed_tools or [])

    def check(self, tool_name: str) -> bool:
        """Check if a tool is allowed for this gate."""
        if not self._allowed:
            return True  # empty = allow all
        return tool_name in self._allowed

    def allowed_list(self) -> str:
        """Return human-readable list of allowed tool names."""
        if not self._allowed:
            return "all tools"
        return ", ".join(sorted(self._allowed))

    def deny_message(self, tool_name: str) -> str:
        """Generate a helpful error message when a tool is denied."""
        return (
            f"Tool '{tool_name}' is not available for this sub-agent. "
            f"Allowed tools: {self.allowed_list()}"
        )
