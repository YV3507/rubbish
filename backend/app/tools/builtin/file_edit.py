"""File edit tool with Myers diff (using difflib) and checkpoint before write."""

import difflib
from pathlib import Path

from app.tools.registry import Tool, ToolRegistry


class FileEditTool:
    """Read and edit files with checkpoint support."""

    def __init__(self, checkpoint_manager=None):
        self._checkpoints = checkpoint_manager

    async def read(self, file_path: str) -> str:
        """Read the contents of a file."""
        path = Path(file_path)
        if not path.exists():
            return f"Error: file not found: {file_path}"
        return path.read_text(encoding="utf-8")

    async def edit(self, file_path: str, old_str: str, new_str: str) -> str:
        """Edit file by replacing old_str with new_str."""
        path = Path(file_path)
        if not path.exists():
            return f"Error: file not found: {file_path}"

        content = path.read_text(encoding="utf-8")

        # Create checkpoint before edit
        if self._checkpoints:
            await self._checkpoints.save(file_path, content)

        if old_str not in content:
            return "Error: old_str not found in file"

        new_content = content.replace(old_str, new_str, 1)

        # Compute diff for preview
        diff = list(
            difflib.unified_diff(
                content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=file_path,
                tofile=file_path,
            )
        )

        path.write_text(new_content, encoding="utf-8")
        return f"Applied edit. Diff:\n{''.join(diff)}"

    def register(self, registry: ToolRegistry):
        registry.register(
            Tool(
                name="read",
                description="Read the contents of a file",
                handler=self.read,
                schema={
                    "name": "read",
                    "description": "Read file contents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"}
                        },
                        "required": ["file_path"],
                    },
                },
            )
        )
        registry.register(
            Tool(
                name="edit",
                description="Edit a file by replacing text",
                handler=self.edit,
                schema={
                    "name": "edit",
                    "description": "Edit file content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "old_str": {"type": "string"},
                            "new_str": {"type": "string"},
                        },
                        "required": ["file_path", "old_str", "new_str"],
                    },
                },
            )
        )
