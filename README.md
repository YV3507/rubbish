# Rubbish

> **Agent-driven code intelligence engine** — Python orchestrator + Rust compute + React WebUI.

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
