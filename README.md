# AgenticFleet

![AgenticFleet Architecture](assets/banner.png)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/agentic-fleet?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/agentic-fleet)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/qredence/agentic-fleet)

> **⚠️ Active Development Notice**
> This project is under active development. Features, APIs, and workflows may change. We recommend pinning to specific versions for production use.

---

## What is AgenticFleet?

AgenticFleet is a FastAPI + Vite/React stack for orchestrating multi‑agent workflows. It ships a YAML‑driven backend, a modern web UI, and a CLI for scripted flows.

- Orchestrated agent workflows with HITL approvals
- Web UI and interactive CLI
- YAML configuration and strong typing
- Streaming updates (SSE) and checkpoints
- Notebooks, tests, and docs included

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key (`OPENAI_API_KEY` in `.env`)

### Install & Run

```bash
# Clone
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# Configure env
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# Install backend deps
make install
# Install frontend deps
make frontend-install

# Launch backend (8000) + frontend (5173)
make dev

# CLI: smoke tests and scripted flows
uv run agentic-fleet --help
```

---

## Common Tasks

```bash
make check         # lint, format, type-check, tests
make test          # backend tests (pytest)
make test-config   # validate YAML + wiring
make validate-agents  # verify AGENTS docs invariants
```

---

## Read Next

- Backend: src/agentic_fleet/AGENTS.md
- Frontend: src/frontend/AGENTS.md
- Tests: tests/AGENTS.md
- Docs index: docs/README.md

---

## License

MIT — see LICENSE for details.
