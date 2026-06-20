"""Skill loader: scan .firefly/skills/*.md and inject summaries into system prompt."""

import os
from pathlib import Path


class SkillLoader:
    """Scan and load skill definitions from YAML/Markdown files."""

    SKILL_DIR = ".firefly/skills"

    def __init__(self, project_root: str = "."):
        self._base = Path(project_root) / self.SKILL_DIR

    async def load_summaries(self) -> list[dict]:
        """Load all skill files and return their summaries."""
        if not self._base.exists():
            return []

        summaries = []
        for f in sorted(self._base.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            # Extract first heading as name, first paragraph as summary
            lines = content.strip().split("\n")
            name = lines[0].lstrip("#").strip() if lines else f.stem
            summary = "\n".join(l for l in lines[1:] if l.strip())[:500]
            summaries.append({"name": name, "content": content, "summary": summary})
        return summaries

    async def build_system_prompt(self) -> str:
        """Build a system prompt snippet from all loaded skills."""
        summaries = await self.load_summaries()
        if not summaries:
            return ""
        parts = ["<available_skills>"]
        for s in summaries:
            parts.append(f"<skill name=\"{s['name']}\">\n{s['summary']}\n</skill>")
        parts.append("</available_skills>")
        return "\n".join(parts)
