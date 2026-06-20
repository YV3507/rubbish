"""Integration test for file_edit with checkpoint manager."""

import pytest
from pathlib import Path

from app.tools.builtin.file_edit import FileEditTool
from app.session.checkpoint import CheckpointManager


@pytest.mark.asyncio
async def test_file_edit_read_write(tmp_path):
    """FileEditTool reads and edits files."""
    target = tmp_path / "test.py"
    target.write_text("print('hello')")

    cm = CheckpointManager(session_id="test", ckpt_dir=str(tmp_path))
    tool = FileEditTool(checkpoint_manager=cm)

    # Read
    content = await tool.read(str(target))
    assert "hello" in content

    # Edit
    result = await tool.edit(str(target), "hello", "world")
    assert "Diff" in result
    assert target.read_text() == "print('world')"


@pytest.mark.asyncio
async def test_file_edit_old_str_not_found(tmp_path):
    """FileEditTool returns error when old_str is not found."""
    target = tmp_path / "test.py"
    target.write_text("content")

    tool = FileEditTool()
    result = await tool.edit(str(target), "nonexistent", "new")
    assert "not found" in result


@pytest.mark.asyncio
async def test_file_edit_nonexistent_file(tmp_path):
    """FileEditTool returns error for missing file."""
    tool = FileEditTool()
    result = await tool.read(str(tmp_path / "nope.txt"))
    assert "not found" in result


@pytest.mark.asyncio
async def test_checkpoint_rollback_none(tmp_path):
    """Checkpoint rollback returns None when no checkpoints."""
    cm = CheckpointManager(session_id="test", ckpt_dir=str(tmp_path))
    result = await cm.rollback("/nonexistent.txt")
    assert result is None
