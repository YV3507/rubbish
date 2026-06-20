# Deployment

## Docker Compose (Development)

```mermaid
graph TB
    subgraph "docker compose up"
        B["backend:8000<br/>Python FastAPI<br/>uvicorn app.main:app"]
        C["compute:8080<br/>Rust Axum<br/>rubbish-compute"]
        F["frontend:3000<br/>React + Vite<br/>nginx static serve"]
        V["Volume: rubbish_data<br/>/data"]
    end

    B -->|HTTP| C
    F -->|proxy /api/*| B
    B --> V

    style B fill:#3572A5,color:#fff
    style C fill:#DEA584,color:#fff
    style F fill:#61DAFB,color:#000
```

```bash
# Start all services
docker compose up -d --build

# Check logs
docker compose logs -f

# Stop
docker compose down
```

## Production Build

```bash
# Build images
docker compose build

# Tag and push
docker tag rubbish-backend:latest registry.example.com/rubbish-backend:latest
docker tag rubbish-compute:latest registry.example.com/rubbish-compute:latest
docker tag rubbish-webui:latest registry.example.com/rubbish-webui:latest
```

## Configuration

All runtime parameters are exposed via the config API at `/api/v1/config`.

```mermaid
flowchart LR
    ENV["Environment Variables"] -->|overrides| CFG["Configuration File<br/>config.json"]
    CFG -->|loaded at startup| RUNTIME["Runtime"]
    API["Config API"] -->|PUT| CFG
    WEBUI["WebUI Settings Panel"] -->|API call| API
```

### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/rubbish.db` | Backend database |
| `COMPUTE_NODE_URL` | `http://compute:8080` | Rust compute node address |
| `COMPUTE_DB_PATH` | `./data/codegraph.db` | Compute node SQLite database path (`:memory:` for testing) |
| `COMPUTE_PORT` | `8080` | Compute node HTTP listen port |
| `LOG_LEVEL` | `INFO` | Logging level |

## Data Persistence

```
/data/
├── rubbish.db            # Main SQLite (sessions, checkpoints)
├── config.json            # Config overrides
├── offload/               # Offloaded large results
│   ├── abc123.json
│   └── def456.json
└── compute/
    └── codegraph.db       # CodeGraph SQLite (nodes, edges, FTS5)
```

## System Requirements

| Component | CPU | RAM | Disk |
| :--- | :--- | :--- | :--- |
| Backend | 1 core | 1 GB | 1 GB |
| Compute | 2 cores | 2 GB | 5 GB |
| Frontend | 1 core | 512 MB | 500 MB |
