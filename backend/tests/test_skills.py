"""Tests for skill loader."""

import pytest
from pathlib import Path

from app.skills.loader import SkillLoader


@pytest.mark.asyncio
async def test_skill_loader_no_dir(tmp_path):
    """SkillLoader returns empty list when dir does not exist."""
    loader = SkillLoader(project_root=str(tmp_path))
    summaries = await loader.load_summaries()
    assert summaries == []


@pytest.mark.asyncio
async def test_skill_loader_reads_markdown(tmp_path):
    """SkillLoader reads .md files and extracts name/summary."""
    skills_dir = tmp_path / ".firefly" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "test_skill.md").write_text(
        "# TestSkill\n\nThis is a test skill description.\n"
    )

    loader = SkillLoader(project_root=str(tmp_path))
    summaries = await loader.load_summaries()
    assert len(summaries) == 1
    assert summaries[0]["name"] == "TestSkill"
    assert "test skill" in summaries[0]["summary"]


@pytest.mark.asyncio
async def test_skill_loader_builds_prompt(tmp_path):
    """SkillLoader builds a system prompt snippet from skill files."""
    skills_dir = tmp_path / ".firefly" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill_a.md").write_text("# Alpha\n\nDoes X.\n")
    (skills_dir / "skill_b.md").write_text("# Beta\n\nDoes Y.\n")

    loader = SkillLoader(project_root=str(tmp_path))
    prompt = await loader.build_system_prompt()
    assert "<available_skills>" in prompt
    assert "Alpha" in prompt
    assert "Beta" in prompt
