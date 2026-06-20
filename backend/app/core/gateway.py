"""Gateway: unified entry point facade for agent operations.

Wires up real LLM provider, tool registry, compute client, checkpoint manager,
MCP manager, and task manager.
"""

from app.config import config
from app.config.schema import ConfigSchema
from app.core.agent import Agent
from app.core.emitter import EventBus
from app.core.background import TaskManager
from app.session.session import Session
from app.session.checkpoint import CheckpointManager
from app.tools.registry import Tool, ToolRegistry
from app.tools.executor import ToolExecutor
from app.tools.builtin.file_edit import FileEditTool
from app.tools.builtin.shell import ShellTool
from app.tools.builtin.agent_tool import AgentTool
from app.tools.compute_client import ComputeClient
from app.mcp.manager import MCPManager
from app.llm.base import LLMProvider
from app.llm.openai_compat import DeepSeekProvider
from app.llm.anthropic import AnthropicProvider
from app.llm.composer import Composer
from app.headroom.router import create_default_router
from app.workspace import WorkspaceManager


def create_llm_provider(cfg: ConfigSchema | None = None) -> LLMProvider:
    """Create the configured LLM provider from the given config (or module-level)."""
    cfg = cfg or config
    if cfg.llm_provider == "anthropic":
        return AnthropicProvider(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model,
        )
    # Default: OpenAI-compatible (DeepSeek, MiMo, OpenAI)
    return DeepSeekProvider(
        api_key=cfg.llm_api_key,
        base_url=cfg.llm_base_url,
        model=cfg.llm_model,
    )


class Gateway:
    """Facade that manages sessions and agent lifecycle."""

    def __init__(self):
        self.sessions: dict[str, Session] = {}
        self.checkpoints: dict[str, CheckpointManager] = {}
        self.emitter = EventBus()
        self.workspace_manager = WorkspaceManager()

        # Create LLM provider from module-level config (may be overridden later)
        self._llm_provider: LLMProvider | None = None
        self._cfg: ConfigSchema | None = None

        # Create compute client for Rust node
        self.compute_client = ComputeClient(base_url=config.compute_node_url)

        # Tool registry and executor
        self.tool_registry = ToolRegistry()
        self._register_tools()
        self.tool_executor = ToolExecutor(self.tool_registry)

        # MCP manager for external tool connections
        self.mcp = MCPManager(self.tool_registry)

        # Background task manager
        self.tasks = TaskManager()

        # Content router for compression
        self.content_router = create_default_router()

        # Composer for cache-optimized prompt building
        self.composer = Composer(
            system_prompt=(
                "You are Rubbish, an AI agent with file editing, shell execution, "
                "and code analysis capabilities. You can read and edit files, run "
                "commands, and delegate tasks to sub-agents. Always think step by step."
            )
        )
        self.composer.add_tools(self.tool_registry.to_openai_schemas())

    def _register_tools(self):
        """Register all built-in tools with checkpoint support."""
        # File operations — schema only; checkpoint wired per-run
        FileEditTool().register(self.tool_registry)

        # Shell command execution
        ShellTool().register(self.tool_registry)

        # Sub-agent delegation
        AgentTool(agent_factory=self._create_sub_agent).register(self.tool_registry)

    def _get_checkpoint(self, session_id: str) -> CheckpointManager:
        """Get or create a checkpoint manager for the given session."""
        if session_id not in self.checkpoints:
            self.checkpoints[session_id] = CheckpointManager(
                session_id=session_id,
                ckpt_dir=f".sessions/{session_id}.ckpt",
            )
        return self.checkpoints[session_id]

    def _get_llm_provider(self) -> LLMProvider:
        """Get or create the LLM provider from the current runtime config."""
        cfg = self._cfg or config
        return create_llm_provider(cfg)

    def set_config(self, cfg: ConfigSchema):
        """Update the runtime config (called when Config API updates)."""
        self._cfg = cfg
        self._llm_provider = None  # force re-create on next use

    def _create_sub_agent(self, session_id: str) -> Agent:
        """Factory for sub-agents."""
        session = self.sessions.get(session_id)
        if not session:
            session = Session(session_id)
            self.sessions[session_id] = session
        return Agent(
            session=session,
            llm_provider=self._get_llm_provider(),
            tool_executor=self.tool_executor,
            emitter=self.emitter,
            composer=self.composer,
            content_router=self.content_router,
            agent_name=f"sub-{session_id[:8]}",
        )

    async def run(self, session_id: str, prompt: str) -> str:
        """Start an agent run in the given session."""
        session = self.sessions.get(session_id)
        if not session:
            session = Session(session_id)
            self.sessions[session_id] = session

        # Wire session-specific checkpoint into file edit tool
        ckpt = self._get_checkpoint(session_id)
        file_tool = FileEditTool(checkpoint_manager=ckpt)
        # Re-register with checkpoint support (replace handlers in-place)
        for name in ("read", "edit"):
            existing = self.tool_registry.get(name)
            if existing:
                self.tool_registry.register(
                    Tool(
                        name=name,
                        description=existing.description,
                        handler=getattr(file_tool, name),
                        schema=existing.schema,
                    )
                )

        agent = Agent(
            session=session,
            llm_provider=self._get_llm_provider(),
            tool_executor=self.tool_executor,
            emitter=self.emitter,
            composer=self.composer,
            content_router=self.content_router,
            compute_client=self.compute_client,
            agent_name="main",
        )

        # Track as background task
        task = self.tasks.start(session_id)
        try:
            await self.emitter.emit("background_start", {
                "task_id": task.id,
                "session_id": session_id,
            })
            await agent.run(prompt)
            self.tasks.complete(task.id)
            await self.emitter.emit("background_end", {
                "task_id": task.id,
                "session_id": session_id,
            })
        except Exception as e:
            self.tasks.complete(task.id, error=str(e))
            # Emit error + agent_end so the SSE stream closes and
            # the frontend stops its "Thinking..." state
            await self.emitter.emit("error", {
                "task_id": task.id,
                "session_id": session_id,
                "message": str(e),
            }, session_id=session_id)
            await self.emitter.emit("agent_end", {
                "turns": 0,
                "error": str(e),
            }, session_id=session_id)
        return session_id

    async def stop(self, session_id: str):
        """Stop an active agent run."""
        for task in self.tasks.list_active():
            if task.session_id == session_id:
                self.tasks.cancel(task.id)
                break

    async def shutdown(self):
        """Cleanup resources."""
        await self.llm_provider.client.aclose()
        await self.compute_client.close()
