# index-retriever-mcp-server

`index-retriever-mcp-server` is the Cloud-Dog AI platform retrieval service for ingesting, indexing, and searching enterprise content across multiple vector database backends and parser providers, exposed through REST, MCP, and A2A-compatible interfaces.

## Quick Start

### Prerequisites
- Python `3.11+`
- Access to `https://pypi.cloud-dog.net/simple/`
- Vault bootstrap env file: `<workspace>/env-vault`

### Install
```bash
set -a; source <workspace>/env-vault; set +a
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

### Run
```bash
./server_control.sh --env tests/env-IT start all
./server_control.sh --env tests/env-IT status all
```

### Test
```bash
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q
```

## Architecture Overview

The repository separates transport/runtime concerns from indexing/search domain logic:
- `src/index_server/` for REST/MCP process bootstrap and auth middleware
- `src/index_tools/` for connectors, parsing orchestration, embeddings, VDB, queue, and service facade

Detailed architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## API Interfaces

| Interface | Base Path | Transport | Reference |
|---|---|---|---|
| REST API | `/api/v1` | HTTP/JSON | [docs/API-REFERENCE.md#rest-api](docs/API-REFERENCE.md#rest-api) |
| MCP API | `/mcp` | Streamable HTTP MCP | [docs/API-REFERENCE.md#mcp-tools](docs/API-REFERENCE.md#mcp-tools) |
| A2A | `/a2a` | HTTP/JSON (auth-gated) | [docs/API-REFERENCE.md#a2a-endpoints](docs/API-REFERENCE.md#a2a-endpoints) |

## Configuration

Configuration precedence and variable catalogue: [docs/ENV-REFERENCE.md](docs/ENV-REFERENCE.md)  
Deployment profiles and Vault wiring: [docs/DEPLOY.md](docs/DEPLOY.md)

## Platform Packages

| Package | Version Constraint | Role |
|---|---|---|
| `cloud_dog_config` | `>=0.3.1` | layered config and Vault resolution |
| `cloud_dog_logging` | `>=0.3.3` | structured logs and audit trail |
| `cloud_dog_api_kit` | `>=0.4.1` | API and MCP app factory |
| `cloud_dog_idam` | `>=0.2.0` | auth and RBAC enforcement |
| `cloud_dog_jobs` | `>=0.3.0` | job queue abstraction |
| `cloud_dog_db` | `>=0.1.0` | DB runtime helper |
| `cloud_dog_llm` | `>=0.2.1` | embedding/provider integration |
| `cloud_dog_vdb` | `>=0.5.2` | VDB + parser/OCR abstraction |
| `cloud_dog_storage` | `>=0.1.1` | storage backends and path utilities |

## Standards Alignment

| Standard | Status |
|---|---|
| PS-00 | ✅ |
| PS-10 | ✅ |
| PS-20 | ✅ |
| PS-30 | ✅ |
| PS-40 | ✅ |
| PS-50 | ✅ |
| PS-60 | ✅ |
| PS-70 | ✅ |
| PS-75 | ✅ |
| PS-80 | ✅ |
| PS-90 | ✅ |
| PS-95 | ✅ |

## Documentation Links

| Document | Path |
|---|---|
| Build Guide | [docs/BUILD.md](docs/BUILD.md) |
| Deploy Guide | [docs/DEPLOY.md](docs/DEPLOY.md) |
| API Reference | [docs/API-REFERENCE.md](docs/API-REFERENCE.md) |
| Environment Reference | [docs/ENV-REFERENCE.md](docs/ENV-REFERENCE.md) |
| Requirements | [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) |
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Tests | [docs/TESTS.md](docs/TESTS.md) |
| Rules | [RULES.md](RULES.md) |
| Context Handoff | [CONTEXT-SUMMARY.md](CONTEXT-SUMMARY.md) |

---

## Licence

Apache-2.0 — Copyright (c) 2026 Cloud-Dog, Viewdeck Engineering Limited
