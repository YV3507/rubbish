# 架构

## 物理部署（3 进程）

```mermaid
graph LR
    subgraph "Docker Compose"
        BE["Backend:8000<br/>Python/FastAPI"]
        CN["Compute:8080<br/>Rust/Axum"]
        FE["Frontend:3000<br/>React/Vite"]
    end

    USER["浏览器"] -->|HTTP + SSE + WS| FE
    FE -->|"/api/*" 代理| BE
    BE -->|"/graph/* /compress/*"| CN
    BE -->|"aiosqlite"| SQLITE[("SQLite<br/>sessions.db")]
    CN -->|"rusqlite + FTS5"| DB[("SQLite<br/>codegraph.db")]

    style BE fill:#3572A5,color:#fff
    style CN fill:#DEA584,color:#fff
    style FE fill:#61DAFB,color:#000
```

## 端到端数据流

```mermaid
sequenceDiagram
    participant User
    participant ReactUI
    participant FastAPI
    participant Agent
    participant Compute(Rust)
    participant LLM

    User->>ReactUI: 输入提示
    ReactUI->>FastAPI: POST /api/v1/agent/run
    FastAPI->>Agent: 创建 asyncio 任务
    Agent->>Agent: AutoPlan 检测（启发式/LLM）
    Agent->>Agent: 编排用户输入（缓存对齐）
    Agent->>Compute(Rust): GET /graph/explore?symbol=login
    Compute(Rust)-->>Agent: 返回调用者/被调用者
    Agent->>Agent: 注入 CodeGraph 上下文
    Agent->>LLM: 流式请求
    LLM-->>Agent: text_delta（思考）
    Agent-->>FastAPI: SSE 推送 text_delta
    FastAPI-->>ReactUI: EventSource 渲染 Markdown
    LLM-->>Agent: tool_call: edit_file
    Agent->>Agent: 生成差异预览
    Agent-->>FastAPI: WS 推送 permission_request
    FastAPI-->>ReactUI: 模态框"允许编辑？"
    User->>ReactUI: 点击"允许"
    ReactUI->>FastAPI: WS 发送 {action: "allow"}
    FastAPI->>Agent: 恢复等待
    Agent->>Agent: 执行编辑（先创建检查点）
    Agent->>Agent: 内容路由器（检测差异→压缩）
    Agent->>Compute(Rust): POST /compress/crush（如需要）
    Compute(Rust)-->>Agent: 压缩结果
    Agent->>Agent: StormBreaker.record(results)
    Agent->>Agent: MicroCompact（TTL 检查）
    Agent->>LLM: 下一轮
    LLM-->>Agent: "完成"
    Agent-->>FastAPI: SSE 推送 agent_end
    FastAPI-->>ReactUI: 关闭 SSE，显示完成
```

## 组件职责

### 后端（Python）

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

    Gateway --> Agent : 创建
    Gateway --> EventBus : 拥有
    Agent --> AgentEmitter : 包装 EventBus
    Agent --> StormBreaker : 记录工具结果
    Agent --> MicroCompact : 基于时间的压缩
    Agent --> Composer : 缓存优化提示
    Agent --> ContentRouter : 工具结果压缩
    Agent --> AutoPlanDetector : 执行前规划
    Agent --> Session : 管理对话
    Agent --> ToolExecutor : 调用工具
    Agent --> ConfigSchema : 读取参数
    ToolExecutor --> ToolRegistry : 解析
    Session --> CheckpointManager : 文件快照
    Session --> MicroCompact : 压缩
    SubAgentGate --> ToolExecutor : 运行时门控
```

### 计算节点（Rust）

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

    CompressionPipeline --> SmartCrusher : 委派
    CodeGraph --> Searcher : 使用
    CodeGraph --> ImpactAnalyzer : 使用
```

## 配置系统

```mermaid
flowchart LR
    FE["前端配置面板"] -->|GET /api/v1/config| API["配置 API"]
    API -->|读取| STORE["ConfigStore<br/>JSON on disk"]
    STORE -->|加载| SCHEMA["ConfigSchema<br/>默认值"]
    SCHEMA -->|合并| RUNTIME["运行时配置"]
    RUNTIME -->|注入| AGENT["Agent"]
    RUNTIME -->|注入| TOOLS["ToolExecutor"]
    RUNTIME -->|注入| SB["StormBreaker"]
    RUNTIME -->|注入| SESSION["Session"]
    RUNTIME -->|注入| MC["MicroCompact"]
    RUNTIME -->|注入| AP["AutoPlan"]

    FE -->|PUT /api/v1/config| API
    FE -->|POST /api/v1/config/reset| API
```

## 关键设计模式

| 模式 | 模块 | 描述 |
| :--- | :--- | :--- |
| **MicroCompact** | `session/microcompact.py` | 时间感知压缩，与 Anthropic 5 分钟提示缓存 TTL 对齐 |
| **Compose** | `llm/composer.py` | 缓存优化的提示：系统提示保持静态，可变内容装饰用户消息尾部 |
| **StormBreaker** | `core/stormbreaker.py` | 按工具的 `(名称, 错误)` 键追踪；成功仅重置自身计数器 |
| **Content Router** | `headroom/router.py` | 检测器链（Diff→Code→Log→Search→Command→Text）将内容路由到最优压缩器 |
| **AutoPlan** | `autoplan/detector.py` | 两阶段：低成本启发式评分（0-4），仅边界情况调用 LLM 分类器（3s 超时） |
| **Workspace** | `workspace/__init__.py` | 追踪当前和最近的工作区目录；持久化到磁盘；API 优先 |
| **Shutdown** | `main.py` + `run.ps1` | 双路径：后端 `/api/v1/shutdown` 端点 + `.\run.ps1 stop` 的 PID 文件追踪 |
| **AgentEmitter** | `core/emitter.py` | 自动向事件注入 `source` 字段；`subscribe(kind)` 支持按类型过滤 |
| **SubAgentGate** | `agentdef/loader.py` | 运行时工具访问门 — 不修改工具列表，在执行时拒绝以保持缓存 |
| **Checkpoint** | `session/checkpoint.py` | 每轮独立的 JSON 文件（`turn-N.json`），路径转义保护，幂等恢复 |
