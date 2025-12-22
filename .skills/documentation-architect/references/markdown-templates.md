# Markdown Templates

## Table of Contents

1. README Template
2. AGENTS.md Template
3. Architecture Doc Template
4. Runbook Template
5. API Doc Template

## 1. README Template

````markdown
# Project Name

One-sentence purpose. Include primary audience.

## Quick Start

```bash
# from repo root
make install
make dev
```
````

## Key Concepts

- Concept 1: short definition
- Concept 2: short definition

## Architecture (Short)

- Layer 1: purpose
- Layer 2: purpose

## Configuration

- `ENV_VAR`: purpose
- `config/file.yaml`: purpose

## Testing

```bash
# from repo root
make test
```

## Troubleshooting

- Symptom: fix

````

## 2. AGENTS.md Template

```markdown
# Working Agreements

## Tooling
- Shell: zsh
- Python: uv
- Frontend: npm

## Setup
- `make install`
- copy `.env.example` to `.env`

## Run
- `make dev`
- `make backend`

## Tests
- `make test`
- `make lint`
- `make type-check`

## Architecture
- brief layer list

## Agent Workflows
- agent roles and where they live
- workflow phases
- config files
````

## 3. Architecture Doc Template

```markdown
# Architecture Overview

## System Context

- external actors
- integrations

## Components

- component A: responsibility
- component B: responsibility

## Data Flow

- request -> processing -> storage

## Key Configs

- config locations

## Extension Points

- plugins, tools, agents
```

## 4. Runbook Template

```markdown
# Runbook: <Incident or Task>

## Symptoms

- list

## Immediate Actions

1. step
2. step

## Diagnostics

- command
- log location

## Resolution

- fix steps

## Verification

- commands to confirm
```

## 5. API Doc Template

```markdown
# API Reference

## Base URL

- `http://localhost:8000`

## Authentication

- method

## Endpoints

### GET /health

- purpose
- response

### POST /v1/resource

- request body
- response body
```
