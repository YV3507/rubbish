# Contributing to Rubbish

Thanks for your interest in Rubbish — an agent-driven code intelligence engine
built from a Python orchestrator, a Rust compute node, and a React WebUI.

## Ways to contribute

- **Bug reports** — open an issue using the bug report template.
- **Feature requests** — open an issue using the feature request template.
- **Pull requests** — small, focused changes are easiest to review.
- **Documentation** — improvements to `docs/` (English and `docs/zh-CN/`) are very welcome.

If you are planning a large change, please open an issue first so we can agree
on the approach before you invest a lot of time.

## Repository layout

| Path | Component | Stack |
| :--- | :--- | :--- |
| `backend/` | Agent orchestration, HTTP/SSE API | Python 3.11+, FastAPI |
| `compute-node/` | Code graph + context compression | Rust, Axum, SQLite/FTS5 |
| `frontend/` | Web UI | React, Vite, TypeScript, Tailwind |
| `docs/` | Documentation (EN + zh-CN) | Markdown |

## Development setup

### Prerequisites

- Python 3.11+
- Rust (stable toolchain)
- Node.js 20+
- Optional: Docker + Docker Compose

### Run the full stack locally (Windows)

```powershell
.\run.ps1 all -Install     # start all three services in the background
.\run.ps1 stop             # gracefully stop them
```

### Run the full stack with Docker

```bash
cp .env.docker .env        # then set LLM_API_KEY
docker compose up --build -d
```

The Web UI is served at <http://localhost:3000>.

## Running tests

```powershell
.\runtests.ps1                      # all modules
.\runtests.ps1 -Module backend
.\runtests.ps1 -Module compute-node
.\runtests.ps1 -Module frontend
.\runtests.ps1 -Integration         # requires a built compute-node binary
```

Or per module:

```bash
cd backend      && python -m pytest tests/ -m "not integration"
cd compute-node && cargo test
cd frontend     && npm test
```

The integration suite starts the real Rust compute node as a subprocess, so it
requires `cargo build` to have produced `compute-node/target/debug/rubbish-compute`.

## Pull request checklist

- [ ] The change is scoped to one concern.
- [ ] All three test suites pass locally (`.\runtests.ps1`).
- [ ] New behaviour is covered by tests where practical.
- [ ] Documentation under `docs/` is updated if you changed public behaviour or config.
- [ ] No secrets (API keys, tokens) are committed — `.env` files must stay untracked.

## Commit messages

Short imperative summaries are preferred, e.g. `compute-node: fix FTS5 duplicate rows`.
Both English and Chinese commit messages are acceptable.

## Code style

- **Python** — 4-space indent, type hints on public functions.
- **Rust** — `cargo fmt` before committing; keep `cargo clippy` clean where possible.
- **TypeScript** — match the existing component structure; keep types explicit.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
