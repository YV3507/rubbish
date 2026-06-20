"""Shell tool: execute shell commands asynchronously.

Configurable via config.tool_shell_default_timeout_sec.
"""

import asyncio

from app.config import config
from app.tools.registry import Tool, ToolRegistry


class ShellTool:
    """Execute shell commands via asyncio subprocess."""

    def __init__(self, timeout: int | None = None):
        self.timeout = timeout or config.tool_shell_default_timeout_sec

    async def run(self, command: str) -> str:
        """Run a shell command and return output."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            output = stdout.decode()
            if stderr:
                output += f"\n[stderr]\n{stderr.decode()}"
            return output
        except asyncio.TimeoutError:
            return f"Error: command timed out after {self.timeout}s"
        except Exception as e:
            return f"Error: {str(e)}"

    def register(self, registry: ToolRegistry):
        registry.register(
            Tool(
                name="bash",
                description="Execute a shell command",
                handler=self.run,
                schema={
                    "name": "bash",
                    "description": "Run a shell command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"}
                        },
                        "required": ["command"],
                    },
                },
            )
        )
