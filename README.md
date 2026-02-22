# index-retriever-mcp-server

**Version:** 0.1.0 (pre-development)  
**Status:** Seed — documentation complete, ready for implementation  
**Repository:** `https://git.cloud-dog.net/cloud-dog-ai/index-retriever-mcp-server`

An **API-first MCP server** providing the full range of vector database indexing, searching, and retrieval capabilities for agentic flows. Wraps LlamaIndex (and optionally LangChain) with a consistent operational envelope: ingestion, conversion, embedding, pluggable vector backends, multi-profile multi-collection management, deduplication, job/queue management, audit logging, RBAC, and an admin WebUI.

---

## Architecture Overview

```
src/
  index_tools/                # Reusable library (no server/transport concerns)
    config/                   # cloud_dog_config integration
    security/                 # cloud_dog_idam RBAC + scope enforcement
    audit/                    # cloud_dog_logging audit trail
    queue/                    # cloud_dog_jobs integration
    connectors/               # Source fetchers (filesystem, S3, WebDAV, FTP, GDrive)
    convert/                  # Document conversion (Pandoc, PDF, Office)
    pipeline/                 # Ingest orchestration: fetch→convert→chunk→embed→upsert
    embeddings/               # cloud_dog_llm embedding provider adapters
    vdb/                      # cloud_dog_vdb vector backend adapters
    search/                   # Query, filters, hybrid, rerank
    tools/                    # Tool definitions and Pydantic schemas
  index_server/               # Transport + auth + routing
    api_server.py             # cloud_dog_api_kit FastAPI factory
    mcp_server.py             # MCP transport (stdio/HTTP)
    streaming.py              # SSE/WS ingestion + job updates
    auth/                     # cloud_dog_idam middleware
    admin/                    # Admin endpoints
    webui/                    # Admin UI (future, @cloud-dog/* packages)
    main.py                   # Entrypoint
```

---

## Platform Standards Alignment

| Standard | ID | Status | Notes |
|----------|-----|--------|-------|
| Engineering Principles | PS-00 | ✅ Designed | UK English, API-first, config-driven, testable |
| Architecture | PS-10 | ✅ Designed | Library/server separation |
| API Contracts | PS-20 | ✅ Designed | OpenAPI, correlation IDs, error taxonomy |
| UI Standards | PS-30 | 🔲 Planned | Admin WebUI via `@cloud-dog/*` |
| Logging & Observability | PS-40 | ✅ Designed | Structured JSON + JSONL audit |
| LLM Interfaces | PS-50 | ✅ Designed | Embedding via `cloud_dog_llm` |
| VDB Interfaces | PS-60 | ✅ Designed | Vector backends via `cloud_dog_vdb` |
| User Mgmt & IDAM | PS-70 | ✅ Designed | Auth/RBAC via `cloud_dog_idam` |
| Job Queue | PS-75 | ✅ Designed | Ingest/reindex/retention jobs via `cloud_dog_jobs` |
| Config Management | PS-80 | ✅ Designed | `cloud_dog_config` integration |
| Security | PS-90 | ✅ Designed | Secrets never logged, default-deny |
| Testing | PS-95 | ✅ Designed | Full test plan in TESTS.md |

---

## Platform Package Dependencies

| Package | PyPI | Purpose |
|---------|------|---------|
| `cloud_dog_config` | ✅ | Config loading: env → .env → YAML → defaults → Vault |
| `cloud_dog_logging` | ✅ | Structured JSON ops logs + JSONL audit |
| `cloud_dog_api_kit` | ✅ | FastAPI app factory, middleware, health, errors |
| `cloud_dog_idam` | ✅ | Auth middleware, RBAC, JWT/API key, OIDC/LDAP/SAML |
| `cloud_dog_jobs` | ✅ | Job queue for ingest, reindex, retention, compact |
| `cloud_dog_llm` | ✅ | Embedding provider adapters (OpenAI-compat, Ollama-compat) |
| `cloud_dog_vdb` | ✅ | Vector backend adapters (Chroma, Qdrant, OpenSearch, Weaviate, PGVector) |

---

## Quick Start (Development)

```bash
# 1. Load Vault credentials
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a

# 2. Install dependencies
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/

# 3. Copy and configure environment
cp .env.example private/.env
# Edit private/.env with your settings

# 4. Run
python -m index_server.main --env private/.env
```

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| [REQUIREMENTS.md](REQUIREMENTS.md) | Full functional and non-functional requirements |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module decomposition, data model, flows |
| [TESTS.md](TESTS.md) | Complete test plan (UT/ST/IT/AT/QT) |
| [RULES.md](RULES.md) | Project-specific agent/engineer rules |
| [CONTEXT-SUMMARY.md](CONTEXT-SUMMARY.md) | Living project state summary |

---

## Configuration Precedence

```
os.environ → .env → config.yaml → defaults.yaml → Vault
```

All configuration is managed via `cloud_dog_config`. See `defaults.yaml` for the full configuration schema.

---

## Security

- RBAC gates all operations (profiles, collections, tools) via `cloud_dog_idam`
- Audit log is append-only JSONL via `cloud_dog_logging`
- Connector scopes enforce filesystem/URI boundaries
- Secrets never logged; credentials encrypted at rest
- Default-deny posture
