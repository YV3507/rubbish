"""Agent main loop: orchestrates LLM calls, tool execution, and session management.

Integrates MicroCompact, Compose system, StormBreaker, AutoPlan, ContentRouter,
and ComputeClient for Rust node integration.
"""

from app.config import config
from app.core.emitter import AgentEmitter, EventBus
from app.core.stormbreaker import StormBreaker
from app.session.session import Session
from app.session.microcompact import MicroCompact
from app.llm.base import LLMProvider
from app.llm.composer import Composer
from app.tools.executor import ToolExecutor
from app.tools.compute_client import ComputeClient
from app.headroom.router import ContentRouter, create_default_router


class Agent:
    """Main agent loop — async generator for streaming control."""

    def __init__(
        self,
        session: Session,
        llm_provider: LLMProvider,
        tool_executor: ToolExecutor,
        emitter: EventBus,
        composer: Composer | None = None,
        content_router: ContentRouter | None = None,
        compute_client: ComputeClient | None = None,
        agent_name: str = "main",
    ):
        self.session = session
        self.llm = llm_provider
        self.tools = tool_executor
        self.emitter = AgentEmitter(emitter, agent_name=agent_name)
        self.storm_breaker = StormBreaker(
            max_consecutive_errors=config.stormbreaker_max_consecutive_errors,
        )
        self.micro_compact = MicroCompact(
            ttl_seconds=config.microcompact_ttl_seconds,
            keep_recent=config.microcompact_keep_recent,
        )
        self.composer = composer or Composer()
        self.content_router = content_router or create_default_router()
        self.compute_client = compute_client
        self.max_turns = config.agent_max_turns
        self.offload_threshold = config.agent_offload_threshold_bytes
        self.water_level_threshold = config.agent_water_level_threshold

    async def run(self, user_input: str, **compose_kwargs):
        """Execute the agent loop for the given user input."""
        self.emitter.bind_session(self.session.id)

        # Build messages through Composer for cache-optimized prompt
        history = await self.session.build_messages()
        messages = self.composer.build(user_input, history=history, **compose_kwargs)
        self.composer.mark_cached()

        await self.session.append("user", user_input)
        await self.emitter.emit("agent_start", {"input": user_input})

        turn = 0
        try:
            for turn in range(self.max_turns):
                await self.emitter.emit("status", {"turn": turn + 1})

                # Water level check → trigger compaction
                if self.session.headroom > self.water_level_threshold:
                    await self.emitter.emit("compact_start", {})
                    await self.session.compact()
                    await self.emitter.emit("compact_end", {})

                # Time-based micro-compaction (cache-aligned)
                compacted = await self.micro_compact.compact(self.session)
                if compacted:
                    await self.emitter.emit(
                        "micro_compact", {"compacted": compacted}
                    )

                # Stream LLM response
                has_tool_calls = False
                async for chunk in self.llm.stream(messages):
                    await self.emitter.emit("text_delta", chunk.__dict__)

                    if chunk.tool_calls:
                        has_tool_calls = True
                        await self.emitter.emit(
                            "tool_exec_start",
                            {"tool_calls": len(chunk.tool_calls)},
                        )

                        results = await self.tools.execute_parallel(chunk.tool_calls)

                        # Route each tool result through content-aware compression
                        for res in results:
                            raw = str(res.content)
                            compressed, strategy, ratio = self.content_router.compress(raw)
                            if ratio > 0.1:
                                res.content = compressed
                                await self.emitter.emit(
                                    "usage",
                                    {"saved_ratio": ratio, "strategy": strategy},
                                )

                            # Try Rust SmartCrusher for extra compression (fallback-safe)
                            if self.compute_client and len(str(res.content)) > 500:
                                try:
                                    crushed = await self.compute_client.crush_json(
                                        str(res.content)
                                    )
                                    if crushed and crushed["saved_ratio"] > ratio:
                                        res.content = crushed["compressed"]
                                        await self.emitter.emit(
                                            "usage",
                                            {
                                                "saved_ratio": crushed["saved_ratio"],
                                                "strategy": "smart_crusher",
                                            },
                                        )
                                except Exception:
                                    # Rust node unavailable — continue with Python compression
                                    pass

                            # Offload large results
                            if len(str(res.content)) > self.offload_threshold:
                                res.content = f"[offloaded: {len(str(res.content))} bytes]"

                        self.storm_breaker.record(results)
                        if self.storm_breaker.tripped:
                            await self.emitter.emit(
                                "error",
                                {"message": self.storm_breaker.message},
                            )
                            await self.session.append(
                                "system", self.storm_breaker.message
                            )
                            break

                        await self.emitter.emit(
                            "tool_exec_end",
                            {"results": len(results)},
                        )
                        await self.session.append("tool", results)

                if not has_tool_calls:
                    # No tool calls → conversation turn complete
                    break
        except Exception as e:
            await self.emitter.emit("error", {"message": str(e)})
        finally:
            await self.emitter.emit("agent_end", {"turns": turn + 1})
