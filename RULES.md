# index-retriever-mcp-server — Agent & Engineer Rules

**Version:** 1.1  
**Date:** 2026-02-20  
**Parent:** `cloud-dog-ai-platform-standards/RULES.md` v1.2

This document extends the platform-wide rules. Read the parent RULES.md first.

---

## Section 1 — Platform Rules (Inherited)

All rules from `cloud-dog-ai-platform-standards/RULES.md` apply without exception:
- Integrity and honesty (non-negotiable)
- Configuration precedence: `os.environ → .env → config.yaml → defaults.yaml → Vault`
- Env file usage: `--env tests/env-<TIER>` for tests (UT/ST/IT/AT/QT); `private/env-<name>` only if credentials not yet in Vault
- Credential management: Vault primary; `private/` only for credentials not yet migrated to Vault
- Zero hardcoded values
- UK English throughout

---

## Section 2 — Vault Configuration

### Load before any operation
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
```

### Validate access
```bash
bash scripts/validate-vault.sh
```

### Vault sections used by this project
- `dev.databases` — PostgreSQL connection for profiles/jobs/audit metadata
- `dev.models` — Embedding model definitions (Ollama, OpenRouter, OpenAI-compat)
- `dev.vdbs` — Vector database connections (Chroma, Qdrant, OpenSearch, Weaviate, PGVector)
- `dev.storage` — Object storage for uploaded binaries (optional S3)
- `dev.redis` — Redis/Valkey connection (optional job queue multiplier)
- `dev.repository` — PyPI/NPM registry credentials

---

## Section 3 — Credential Management

### Standard test env files (committed, non-secret)
- `tests/env-UT` — unit test config
- `tests/env-ST` — system test config
- `tests/env-IT` — integration test config (VDB endpoints, embedding endpoints, filesystem roots)
- `tests/env-AT` — application test config
- `tests/env-QT` — quality/security test config

These contain non-secret configuration only (endpoints, ports, feature flags).

### Private env files (ONLY if credentials not yet in Vault)
- `private/env-<name>-secrets` — credentials (embedding API keys, VDB auth tokens, DB passwords)
- Per-backend secret files only if those credentials are not yet in Vault.

**NOTE:** `private/` is NOT required by default. If all credentials are in Vault (dev.vdbs, dev.models), tests only need `tests/env-<TIER>` + sourcing `env-vault`.

### Rules
- All credentials MUST be stored in Vault or `private/` (git-ignored) — never committed
- NEVER commit real API keys, embedding tokens, or database passwords
- NEVER log raw credentials (enforced by `cloud_dog_logging` redaction)
- Embedding provider keys from Vault (`dev.models` section)
- VDB credentials from Vault (`dev.vdbs` section)

---

## Section 4 — Platform Package Rules

### MUST use (no bespoke alternatives)
| Concern | Package | Bespoke alternative forbidden |
|---------|---------|------------------------------|
| Config loading | `cloud_dog_config` | No custom env/YAML loaders |
| Logging | `cloud_dog_logging` | No custom structlog setup |
| API factory | `cloud_dog_api_kit` | No raw FastAPI() instantiation |
| Auth/RBAC | `cloud_dog_idam` | No custom JWT/API key/RBAC code |
| Job queue | `cloud_dog_jobs` | No custom job runners or schedulers |
| Embeddings | `cloud_dog_llm` | No direct OpenAI/Ollama client calls |
| VDB operations | `cloud_dog_vdb` | No direct chromadb/qdrant/opensearch client calls |

### Installation
```bash
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

---

## Section 5 — Project-Specific Rules

### Library/server separation
- `index_tools/` MUST NOT import FastAPI, uvicorn, or MCP transport code
- `index_retriever_server/` MUST NOT contain pipeline/embedding/VDB logic beyond dispatch and auth
- All domain logic MUST be testable without starting a server

### Connector safety
- Filesystem connectors MUST enforce configured scope roots
- Path traversal (`../`) MUST be blocked
- URI-based connectors MUST validate schemes and hosts against allowlists
- Uploaded files MUST be stored in a sandboxed temporary directory

### Embedding provider usage
- All embedding calls MUST go through `cloud_dog_llm` adapters
- NEVER hardcode model names, base URLs, or API keys
- Model configuration comes from Vault `dev.models` section
- Batch sizing, retries, and rate limits managed by `cloud_dog_llm`

### Vector backend usage
- All VDB operations MUST go through `cloud_dog_vdb` adapters
- NEVER import chromadb, qdrant_client, etc. directly in project code
- Backend configuration comes from Vault `dev.vdbs` section
- Each backend MUST pass the same contract test suite

### LlamaIndex/LangChain integration
- LlamaIndex is the primary framework wrapper
- LangChain support is optional and enabled per profile
- Framework code MUST be isolated in `index_tools/` and MUST NOT leak into server layer
- Framework dependencies MUST be declared as optional extras in `pyproject.toml`

---

## Section 6 — Testing Rules

- Follow PS-95 test hierarchy: UT/ST/IT/AT/QT
- All tests use `--env tests/env-<TIER>` for configuration (e.g. `--env tests/env-UT`, `--env tests/env-IT`)
- Backend contract tests MUST run against all enabled VDB backends
- Integration tests require real VDB, embedding provider, and running API server
- NEVER mock VDB or embedding providers in ST/IT/AT tests
- See TESTS.md for complete test plan

---

## Section 7 — Integrity Enforcement Addendum (2026-02-20)

This section is mandatory and was added after a documented integrity failure in this project.

### 7.1 Claim Gate (No proof, no claim)

- NEVER claim `complete`, `100%`, `compliant`, or `verified` without command evidence in the same update.
- Every claim must include:
  - exact command run,
  - observed pass/fail/skip counts,
  - whether Vault was sourced.
- If any gate fails, state `NOT COMPLIANT` explicitly.

### 7.2 Live Backend Proof Gate

- NEVER claim live backend validation without running both:
  - CRU operation through `cloud_dog_vdb` or project runtime, and
  - external verification against the written artefact.
- Required proof per backend:
  - `chroma`: HTTP check via `curl` against collection/object state.
  - `qdrant`: HTTP check via `curl` against collection point.
  - `weaviate`: HTTP check via `curl` against object endpoint.
  - `opensearch`: HTTP check via `curl` against `_doc` endpoint.
  - `pgvector`: protocol-correct SQL verification (`psql`), not HTTP.

### 7.3 Test Integrity Gate

- Required execution order before any completion claim:
  1. `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
  2. `python3 -m pytest tests/integration --env tests/env-IT -q -rs` (without Vault; must fail explicitly, not skip)
  3. full tier run with Vault and exact counts
  4. coverage run and reported percentage
- If coverage is below target or unknown, do not claim full compliance.

### 7.4 Prohibited Behaviour

- Do not reinterpret failing or partial results as acceptable.
- Do not compress nuanced failures into “green” summaries.
- Do not present intermediate states as final completion.
- Do not omit skip counts.

### 7.5 Mandatory Remediation Behaviour

- If integrity is breached:
  - record it in `CONTEXT-SUMMARY.md` with exact file/command evidence,
  - list rule IDs violated,
  - list corrective actions completed,
  - list remaining non-compliance.
- Until all listed items are closed, completion claims are prohibited.
