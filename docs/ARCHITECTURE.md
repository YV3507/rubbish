# Architecture

## Physical Deployment (3 Processes)

```mermaid
graph LR
    subgraph "Docker Compose"
        BE["Backend:8000<br/>Python/FastAPI"]
        CN["Compute:8080<br/>Rust/Axum"]
        FE["Frontend:3000<br/>React/Vite"]
    end

    USER["Browser"] -->|HTTP + SSE + WS| FE
    FE -->|"/api/*" proxy| BE
    BE -->|"/graph/* /compress/*"| CN
    BE -->|"aiosqlite"| SQLITE[("SQLite<br/>sessions.db")]
    CN -->|"rusqlite + FTS5"| DB[("SQLite<br/>codegraph.db")]

    style BE fill:#3572A5,color:#fff
    style CN fill:#DEA584,color:#fff
    style FE fill:#61DAFB,color:#000
```

## End-to-End Data Flow

```mermaid
sequenceDiagram
    participant User
    participant ReactUI
    participant FastAPI
    participant Agent
    participant Compute(Rust)
    participant LLM

    User->>ReactUI: Type prompt
    ReactUI->>FastAPI: POST /api/v1/agent/run
    FastAPI->>Agent: Create asyncio Task
    Agent->>Agent: AutoPlan detection (heuristic/LLM)
    Agent->>Agent: Compose user input (cache-aligned)
    Agent->>Compute(Rust): GET /graph/explore?symbol=login
    Compute(Rust)-->>Agent: Return callers/callees
    Agent->>Agent: Inject CodeGraph context
    Agent->>LLM: Stream request
    LLM-->>Agent: text_delta (thinking)
    Agent-->>FastAPI: SSE push text_delta
    FastAPI-->>ReactUI: EventSource render Markdown
    LLM-->>Agent: tool_call: edit_file
    Agent->>Agent: Generate diff preview
    Agent-->>FastAPI: WS push permission_request
    FastAPI-->>ReactUI: Modal "Allow edit?"
    User->>ReactUI: Click "Allow"
    ReactUI->>FastAPI: WS send {action: "allow"}
    FastAPI->>Agent: Resume await
    Agent->>Agent: Execute edit (checkpoint first)
    Agent->>Agent: Content Router (detect diff→compress)
    Agent->>Compute(Rust): POST /compress/crush (if needed)
    Compute(Rust)-->>Agent: Compressed result
    Agent->>Agent: StormBreaker.record(results)
    Agent->>Agent: MicroCompact (TTL check)
    Agent->>LLM: Next turn
    LLM-->>Agent: "Done"
    Agent-->>FastAPI: SSE push agent_end
    FastAPI-->>ReactUI: Close SSE, show completion
```

## Component Responsibilities

### Backend (Python)

```mermaid
classDiagram
    class Agent {
        +run(user_input)
        +storm_breaker: StormBreaker
        +micro_compact: MicroCompact
        +composer: Composer
        +content_router: ContentRouter
        -max_turns: int
        -water_level: float
    }
    class Gateway {
        +run(session_id, prompt)
        +stop(session_id)
        -sessions: dict
        +workspace_manager: WorkspaceManager
        +emitter: EventBus
    }
    class EventBus {
        +subscribe(session_id, kind)
        +emit(type, data, source)
        -queues: dict
    }
    class WorkspaceManager {
        +open(path): WorkspaceInfo
        +close()
        +switch_to(path)
        +current: WorkspaceInfo
        +recent: list[WorkspaceInfo]
        -persist_to_disk()
    }
    class AgentEmitter {
        +emit(type, data)
        -agent_name: string
        -auto_inject_source()
    }
    class StormBreaker {
        +record(results)
        +tripped: bool
        -counts: dict[(tool,error)]
        -per_tool_reset()
    }
    class MicroCompact {
        +compact(session)
        -ttl: timedelta
        -keep_recent: int
        -ttl_aligned_with_cache()
    }
    class Composer {
        +build(user_input, history)
        +compose_user(input, plan_mode)
        +is_cache_hit: bool
        -static_blocks: list
        -fingerprint: string
    }
    class ContentRouter {
        +compress(content)
        -strategies: list[Strategy]
        -detect_chain()
    }
    class AutoPlanDetector {
        +needs_plan(input)
        -heuristic_score(input)
        -llm_classifier()
    }
    class SubAgentGate {
        +check(tool_name)
        -allowed: set[string]
    }
    class ConfigSchema {
        +agent_max_turns: int
        +stormbreaker_max_consecutive_errors: int
        +microcompact_ttl_seconds: int
        +autoplan_heuristic_threshold: int
        +tool_max_concurrent_reads: int
    }
    class ToolExecutor {
        +execute_parallel(calls)
        -read_sem: Semaphore(8)
        -write_lock: Lock
    }
    class Session {
        +append(role, content)
        +build_messages()
        +headroom: float
    }
    class CheckpointManager {
        +save(file_path, content)
        +rollback(file_path)
        -turn_n_files()
        -path_escape_protect()
    }

    Gateway --> Agent : creates
    Gateway --> EventBus : owns
    Agent --> AgentEmitter : wraps EventBus
    Agent --> StormBreaker : records tool results
    Agent --> MicroCompact : time-based compaction
    Agent --> Composer : cache-optimized prompts
    Agent --> ContentRouter : tool result compression
    Agent --> AutoPlanDetector : pre-execution planning
    Agent --> Session : manages conversation
    Agent --> ToolExecutor : invokes tools
    Agent --> ConfigSchema : reads params
    ToolExecutor --> ToolRegistry : resolves
    Session --> CheckpointManager : file snapshots
    Session --> MicroCompact : compression
    SubAgentGate --> ToolExecutor : runtime gate
```

### Compute Node (Rust)

```mermaid
classDiagram
    class CodeGraph {
        +new(db_path)
        +add_node(id, name, kind)
        +get_callers(node_id)
    }
    class SmartCrusher {
        +crush_json(content, query)
        -statistical_sampling()
    }
    class CompressionPipeline {
        +run(content, query)
        -5_stage_pipeline()
    }
    class Searcher {
        +search(query, limit)
        -FTS5_BM25()
    }
    class ImpactAnalyzer {
        +compute_rwr(node_id, alpha)
        -PageRank()
    }

    CompressionPipeline --> SmartCrusher : delegates
    CodeGraph --> Searcher : uses
    CodeGraph --> ImpactAnalyzer : uses
```

## Config System

```mermaid
flowchart LR
    FE["Frontend Config Panel"] -->|GET /api/v1/config| API["Config API"]
    API -->|reads| STORE["ConfigStore<br/>JSON on disk"]
    STORE -->|loads| SCHEMA["ConfigSchema<br/>Default values"]
    SCHEMA -->|merged| RUNTIME["Runtime Config"]
    RUNTIME -->|injected into| AGENT["Agent"]
    RUNTIME -->|injected into| TOOLS["ToolExecutor"]
    RUNTIME -->|injected into| SB["StormBreaker"]
    RUNTIME -->|injected into| SESSION["Session"]
    RUNTIME -->|injected into| MC["MicroCompact"]
    RUNTIME -->|injected into| AP["AutoPlan"]

    FE -->|PUT /api/v1/config| API
    FE -->|POST /api/v1/config/reset| API
```

## Key Design Patterns

| Pattern | Module | Description |
| :--- | :--- | :--- |
| **MicroCompact** | `session/microcompact.py` | Time-aware compression aligned with Anthropic's 5-min prompt cache TTL |
| **Compose** | `llm/composer.py` | Cache-optimized prompt: system prompt stays static, variable content decorates user message tail |
| **StormBreaker** | `core/stormbreaker.py` | Per-tool `(name, error)` key tracking; success resets only its own tool's counter |
| **Content Router** | `headroom/router.py` | Detector chain (Diff→Code→Log→Search→Command→Text) routes content to optimal compressor |
| **AutoPlan** | `autoplan/detector.py` | Two-stage: cheap heuristic scoring (0-4), LLM classifier only for borderline cases (3s timeout) |
| **Workspace** | `workspace/__init__.py` | Tracks current & recent workspace directories; persists to disk; API-first |
| **Shutdown** | `main.py` + `run.ps1` | Dual-path: backend `/api/v1/shutdown` endpoint + `.\run.ps1 stop` with PID file tracking |
| **AgentEmitter** | `core/emitter.py` | Auto-injects `source` field into events; `subscribe(kind)` for kind-based filtering |
| **SubAgentGate** | `agentdef/loader.py` | Runtime tool access gate — doesn't alter tool list, denies at execution time to preserve cache |
| **Checkpoint** | `session/checkpoint.py` | Per-turn independent JSON files (`turn-N.json`), path-escape protection, idempotent restore |
