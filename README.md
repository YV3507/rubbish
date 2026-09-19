# Rubbish

[![CI](https://github.com/YV3507/rubbish/actions/workflows/ci.yml/badge.svg)](https://github.com/YV3507/rubbish/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/rust-stable-orange.svg)](https://www.rust-lang.org/)
[![Node 20+](https://img.shields.io/badge/node-20%2B-brightgreen.svg)](https://nodejs.org/)

> **Agent-driven code intelligence engine** — Python orchestrator + Rust compute + React WebUI.

> [!NOTE]
> **Project status: early-stage, work in progress.** The architecture, HTTP API,
> code-graph index and context-compression pipeline are implemented and covered by
> tests, but several subsystems (tool-calling against a live LLM, MCP, permissions,
> session compaction) are still incomplete. See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
> for the current state before building on it.

---

## Features

- **Agent orchestration** — FastAPI agent loop with streaming SSE events and per-session history.
- **Code graph** — Rust/Axum service indexing a project into SQLite with FTS5/BM25 symbol search.
- **Context compression** — content-aware routing plus `SmartCrusher` JSON/text compression to cut token spend.
- **Loop protection** — `StormBreaker` guards against repeated failing tool calls.
- **Workspaces** — open, switch and revisit project directories from the WebUI.
- **Live configuration** — tune agent, LLM and tool parameters at runtime without a restart.
- **Bilingual docs** — full documentation in English and [中文](docs/zh-CN/README.md).

---

## Documentation

| Language | Link |
| :--- | :--- |
| English | [docs/README.md](docs/README.md) |
| 中文 | [docs/zh-CN/README.md](docs/zh-CN/README.md) |

### Quick Links

- [Architecture](docs/ARCHITECTURE.md) / [架构](docs/zh-CN/ARCHITECTURE.md)
- [API Reference](docs/API.md) / [API 参考](docs/zh-CN/API.md)
- [Configuration](docs/CONFIG.md) / [配置](docs/zh-CN/CONFIG.md)
- [Deployment](docs/DEPLOYMENT.md) / [部署](docs/zh-CN/DEPLOYMENT.md)
- [Development Guide](docs/DEVELOPMENT.md) / [开发指南](docs/zh-CN/DEVELOPMENT.md)

---

## Quick Start

```bash
# Full stack via Docker
cp .env.docker .env        # configure LLM_API_KEY
docker compose up --build -d
open http://localhost:3000

# Or individual services (Windows)
.\run.ps1 all
.\run.ps1 stop
```

---

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md). To report a vulnerability, follow
[SECURITY.md](.github/SECURITY.md).

---

## License

[MIT](LICENSE) © 2026 YV3507

