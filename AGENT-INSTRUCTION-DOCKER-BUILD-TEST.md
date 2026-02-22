# Agent Instruction — Docker Build, Test & Run (index-retriever-mcp-server)

**Project:** `index-retriever-mcp-server`
**Version:** 1.0
**Date:** 2026-02-20
**Standard:** PS-91 (Docker Containerization)
**Ports:** API=8686, MCP=8687 (PORT-REGISTRY block 8686–8689)

---

## RULES COMPLIANCE — NON-NEGOTIABLE

This instruction is governed by PS-91 Docker Containerization Standards and PORT-REGISTRY.md.
You have standing approval to execute all steps without per-step approval. GET ON WITH IT.

**CRITICAL PORT CHANGE:** The API port was changed from `8080` to `8686` in `defaults.yaml` to resolve a conflict with sql-agent-mcp-server's web UI (port 8080). This change is already applied.

---

## 1. Prerequisites

Before starting, confirm:

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server

# 1. All local tests pass
pytest tests/unit/ --env tests/env-UT -x -q
pytest tests/system/ --env tests/env-ST -x -q
pytest tests/integration/ --env tests/env-IT -x -q
pytest tests/application/ --env tests/env-AT -x -q
pytest tests/security/ --env tests/env-QT -x -q

# 2. Quality gates
ruff check src/ tests/
ruff format --check src/ tests/

# 3. Port change confirmed
grep "port:" defaults.yaml | head -1
# EXPECTED: port: 8686 (NOT 8080)

# 4. Docker files exist (all 8)
for f in Dockerfile docker-build.sh docker-entrypoint.sh healthcheck.sh \
         docker-compose.yml .dockerignore docker-env.example server_control.sh; do
  test -f "$f" && echo "OK: $f" || echo "MISSING: $f"
done
```

**If any prerequisite fails, STOP. Fix it first.**

---

## 2. Docker Files Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `Dockerfile` | 72 | Multi-stage, proxy/CA, **BuildKit secret for private PyPI**, non-root (appuser UID 10001) |
| `docker-build.sh` | 96 | Build + Vault PyPI creds → pip.conf secret + registry tag + CA cert + log |
| `docker-entrypoint.sh` | 71 | Modes: all/api/mcp/status/test/shell + SIGTERM trap |
| `healthcheck.sh` | 4 | Checks `/health` on API port 8686 |
| `docker-compose.yml` | 59 | Individual (api, mcp) + all-in-one profile |
| `.dockerignore` | 18 | Excludes tests, secrets, caches, `.pip.conf.build` |
| `docker-env.example` | 44 | All CLOUD_DOG__INDEX__ vars + VDB + embedding + LLM |
| `server_control.sh` | 110 | PID-managed start/stop for api + mcp |

---

## 3. Build the Docker Image

### 3.1 Private PyPI Authentication

The `cloud_dog_*` platform packages are hosted on `pypi.cloud-dog.net` which requires **Basic auth** (HTTP 401 without credentials). The build script handles this automatically:

1. `docker-build.sh` sources credentials from `PYPI_USERNAME`/`PYPI_PASSWORD` env vars, or **auto-resolves from Vault** (`vault.dev.repository.pypi.username` / `.password`).
2. It generates a temporary `.pip.conf.build` file with the authenticated `extra-index-url`.
3. The Dockerfile uses `RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf` — credentials are available during `pip install` but **never baked into any image layer**.
4. The temp `.pip.conf.build` is deleted after the build completes.

**Security:** `docker history` will NOT reveal any PyPI credentials because BuildKit secret mounts are excluded from image layers.

### 3.2 Run the Build

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server

chmod +x docker-build.sh

# Option A: Auto-resolve credentials from Vault (recommended)
./docker-build.sh

# Option B: Explicit credentials
PYPI_USERNAME=admin PYPI_PASSWORD=<from-vault> ./docker-build.sh

# Verify image exists
docker images | grep index-retriever-mcp-server

# Verify no secrets baked in
docker history cloud-dog/index-retriever-mcp-server:latest --no-trunc | grep -i "api_key\|password\|token\|secret\|pypi"
# EXPECTED: NO OUTPUT
```

### 3.3 If the Build Fails

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ERROR: PYPI_USERNAME and PYPI_PASSWORD required` | Vault unreachable or env-vault missing | Set `PYPI_USERNAME`/`PYPI_PASSWORD` env vars manually |
| `401 Unauthorized` during pip install | Secret mount not working | Ensure `DOCKER_BUILDKIT=1` and Docker ≥ 18.09 |
| `Could not find a version that satisfies cloud_dog_config` | Private index not reachable | Check `--network=host` is being used, proxy is set |
| SSL/cert error on pypi.cloud-dog.net | CA cert not installed | Verify `CUSTOM_CA_CERT` path, check `--trusted-host` |
| General pip timeout | Proxy not configured | Export `HTTP_PROXY` / `HTTPS_PROXY` before build |

---

## 4. Create docker-env.local

Generate the local Docker environment file from Vault:

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server

# Source Vault credentials
source /opt/iac/Development/cloud-dog-ai/env-vault

# Query Vault for all required credentials
VAULT_JSON=$(vault kv get -mount=cloud_dog_ai -format=json config 2>/dev/null || echo "{}")

API_KEY=$(echo "$VAULT_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data',{}).get('data',{}).get('dev',{})
print(d.get('keys',{}).get('api_key',''))
" 2>/dev/null || echo "")

# VDB backends
QDRANT_HOST=$(echo "$VAULT_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data',{}).get('data',{}).get('dev',{})
print(d.get('vdbs',{}).get('qdrant',{}).get('host',''))
" 2>/dev/null || echo "")

QDRANT_PORT=$(echo "$VAULT_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data',{}).get('data',{}).get('dev',{})
print(d.get('vdbs',{}).get('qdrant',{}).get('port','6333'))
" 2>/dev/null || echo "6333")

CHROMA_URL=$(echo "$VAULT_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data',{}).get('data',{}).get('dev',{})
print(d.get('vdbs',{}).get('chroma',{}).get('base_url',''))
" 2>/dev/null || echo "")

# Embedding model
EMBED_URL=$(echo "$VAULT_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data',{}).get('data',{}).get('dev',{})
m=d.get('models',{}).get('ollama_nomic_embed_text_llm1',{})
print(m.get('base_url','http://localhost:11434'))
" 2>/dev/null || echo "http://localhost:11434")

cat > docker-env.local << EOF
# index-retriever-mcp-server — Local Docker Environment
# AUTO-GENERATED from Vault — do NOT commit

CLOUD_DOG__INDEX__API_SERVER__PORT=8686
CLOUD_DOG__INDEX__API_SERVER__HOST=0.0.0.0
CLOUD_DOG__INDEX__MCP_SERVER__PORT=8687
CLOUD_DOG__INDEX__MCP_SERVER__HOST=0.0.0.0

CLOUD_DOG__INDEX__API_KEY=${API_KEY}

# VDB — Qdrant
CLOUD_DOG__INDEX__VDB__PROVIDER=qdrant
CLOUD_DOG__INDEX__VDB__HOST=${QDRANT_HOST}
CLOUD_DOG__INDEX__VDB__PORT=${QDRANT_PORT}

# VDB — Chroma (alternative)
CLOUD_DOG__INDEX__VDB__CHROMA_URL=${CHROMA_URL}

# Embedding
CLOUD_DOG__INDEX__EMBEDDING__PROVIDER=ollama
CLOUD_DOG__INDEX__EMBEDDING__MODEL=nomic-embed-text
CLOUD_DOG__INDEX__EMBEDDING__BASE_URL=${EMBED_URL}
CLOUD_DOG__INDEX__EMBEDDING__DIMENSIONS=768

# LLM
CLOUD_DOG__INDEX__LLM__PROVIDER=ollama
CLOUD_DOG__INDEX__LLM__MODEL=qwen3:14b
CLOUD_DOG__INDEX__LLM__BASE_URL=${EMBED_URL}

# Vault
VAULT_ADDR=https://vault0.cloud-dog.net
VAULT_TOKEN=${VAULT_TOKEN}
CLOUD_DOG__VAULT__MOUNT_POINT=cloud_dog_ai
CLOUD_DOG__VAULT__CONFIG_PATH=config

# Logging
CLOUD_DOG__INDEX__LOG__LEVEL=INFO
CLOUD_DOG__INDEX__AUDIT__ENABLED=true
EOF

echo "docker-env.local created."
echo "  API_KEY=${API_KEY:+SET}${API_KEY:-EMPTY}"
echo "  QDRANT_HOST=${QDRANT_HOST:-EMPTY}"
echo "  CHROMA_URL=${CHROMA_URL:-EMPTY}"
echo "  EMBED_URL=${EMBED_URL}"
```

**IMPORTANT — BUILD vs RUNTIME FAILURE DISTINCTION:**

> **If the Docker image builds and the container starts with `/health` returning 200, the BUILD and CONTAINERIZATION are SUCCESSFUL.** Any subsequent failures reaching VDB, embedding, or LLM backends are **runtime environment failures**, not build failures. Do NOT conflate these.

index-retriever-mcp-server depends on **three external backends** at runtime:

| Backend | Endpoint | Status (as of 2026-02-20) | Required For |
|---------|----------|--------------------------|--------------|
| **VDB — Chroma** | `https://chroma.cloud-dog.net/api/v2/tenants/default_tenant/databases/default_database/collections` | ✅ 200 | Collection CRUD, ingest, search |
| **VDB — Qdrant** | `http://vdb1.app.vpc0.cloud-dog.net:6333/collections` | ⚠️ 401 (needs auth) | Collection CRUD, ingest, search |
| **Embedding — Ollama** | `http://llm1.app.vpc0.cloud-dog.net:11434/api/embeddings` | ✅ 200 | Vector generation |
| **LLM — Ollama** | `http://llm1.app.vpc0.cloud-dog.net:11434/api/chat` | ✅ 200 | Query rewriting |

**Note:** `vault.dev.vdbs` is currently **empty** — VDB endpoints come from `.env` / `docker-env.local`, not Vault.

Without these backends, `/health` will respond but tool operations will fail. **This is expected for a basic Docker smoke test and is NOT a build/containerization failure.**

To verify backend reachability before running tool tests:
```bash
# Chroma (primary VDB)
curl -skS -o /dev/null -w "%{http_code}" https://chroma.cloud-dog.net/api/v2/tenants/default_tenant/databases/default_database/collections
# EXPECTED: 200

# Qdrant (alternative VDB — may require auth)
curl -skS -o /dev/null -w "%{http_code}" http://vdb1.app.vpc0.cloud-dog.net:6333/collections
# EXPECTED: 200 (or 401 if auth required)

# Ollama (llm1 — primary)
curl -skS -o /dev/null -w "%{http_code}" http://llm1.app.vpc0.cloud-dog.net:11434/api/tags
# EXPECTED: 200
```

**If any backend returns non-200, skip §6.4/§6.5/§9 tool tests.** Report it as a runtime environment issue, not a build failure.

### Known Blocker (as of 2026-02-20)

> **Chroma returns HTTP 500 during integration test IT1_9.** This is an external Chroma server-side error at `https://chroma.cloud-dog.net/api/v2/tenants/default_tenant/databases/default_database/collections`, NOT a local build/containerization failure. The Docker image builds and runs correctly — this blocker is in the runtime environment only.
>
> **Action:** Skip IT1_9 (and any other tests that hit Chroma collection operations) until the Chroma backend is fixed. All other tests (UT, QT, and non-Chroma ST/IT/AT) should pass.

---

## 5. Run Docker Container (Local, --network host)

### 5.1 Start All Servers

```bash
docker run -d \
  --name index-retriever-test \
  --network host \
  --env-file docker-env.local \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/data:/app/data" \
  cloud-dog/index-retriever-mcp-server:latest all
```

### 5.2 Wait for Health

```bash
echo "Waiting for index-retriever-mcp-server..."
timeout 30 bash -c 'until curl -fs http://localhost:8686/health >/dev/null 2>&1; do sleep 1; done' \
  && echo "API healthy" || echo "TIMEOUT — check: docker logs index-retriever-test"

timeout 10 bash -c 'until curl -fs http://localhost:8687/health >/dev/null 2>&1; do sleep 1; done' \
  && echo "MCP healthy" || echo "MCP not ready (may be expected)"
```

### 5.3 Verify Container State

```bash
docker exec index-retriever-test whoami
# EXPECTED: appuser

docker exec index-retriever-test ps aux
docker logs index-retriever-test --tail 20
```

---

## 6. Docker Smoke Tests

### 6.1 Health Check

```bash
curl -s http://localhost:8686/health | python3 -m json.tool
# EXPECTED: {"status": "ok", ...}
```

### 6.2 Tool Catalogue

```bash
API_KEY="<from docker-env.local>"

curl -s http://localhost:8686/api/v1/tools \
  -H "x-api-key: ${API_KEY}" | python3 -m json.tool | head -40
# EXPECTED: list of index-retriever tools (search, ingest_*, profiles_*, collections_*, etc.)
```

### 6.3 List Profiles

```bash
curl -s -X POST http://localhost:8686/api/v1/tools/profiles_list \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
# EXPECTED: list of profiles (at least "default")
```

### 6.4 List Collections

```bash
curl -s -X POST http://localhost:8686/api/v1/tools/collections_list \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"profile": "default"}' | python3 -m json.tool
# EXPECTED: list of collections (may be empty if fresh)
```

### 6.5 Backend Health Check (requires live VDB)

```bash
curl -s -X POST http://localhost:8686/api/v1/tools/backend_health_check \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
# EXPECTED: VDB health status (success if Qdrant/Chroma reachable, error if not)
```

### 6.6 Authentication Rejection

```bash
curl -s -w "\n%{http_code}\n" http://localhost:8686/api/v1/tools \
  -H "x-api-key: invalid-key"
# EXPECTED: 401 or 403
```

---

## 7. Run Existing Test Suites (Bare Metal — Regression Check)

**NOTE:** index-retriever-mcp-server tests use `LiveIndexRuntime` (in-process, Vault-backed) and `IndexService` (in-memory). They do NOT start HTTP servers or bind ports. Tests are fully compatible with the Docker container running simultaneously on 8686.

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server

# UT — in-memory, no backends needed
pytest tests/unit/ --env tests/env-UT -x -q
# EXPECTED: 30 passed

# ST — may need Ollama/VDB for live backend tests
pytest tests/system/ --env tests/env-ST -x -q
# EXPECTED: 12 passed

# IT — uses LiveIndexRuntime, needs Vault + backends
pytest tests/integration/ --env tests/env-IT -x -v
# EXPECTED: 12 passed

# AT — uses LiveIndexRuntime, needs Vault + backends
pytest tests/application/ --env tests/env-AT -x -v
# EXPECTED: 5 passed

# QT — security checks
pytest tests/security/ --env tests/env-QT -x -q
# EXPECTED: 5 passed

# CT — contract tests
pytest tests/contract/ --env tests/env-UT -x -q
# EXPECTED: 3 passed
```

**Total: 67 tests expected.**

**NOTE on ST/IT/AT:** These tests use `LiveIndexRuntime` which connects to real Vault, Qdrant, Chroma, and Ollama. If any backend is unreachable, those tests will fail or skip. UT and QT always pass.

---

## 8. Docker Compose Testing

### 8.1 Individual Containers

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server

cp docker-env.local .env

docker compose up -d api mcp

docker compose ps
curl -s http://localhost:8686/health
curl -s http://localhost:8687/health

docker compose down
```

### 8.2 All-in-One Container

```bash
docker compose --profile all-in-one up -d all-in-one

curl -s http://localhost:8686/health
curl -s http://localhost:8687/health

docker compose --profile all-in-one down
```

---

## 9. Full End-to-End Docker Test (requires live backends)

If Ollama + Qdrant/Chroma are reachable, run the full ingest→search flow:

```bash
API_KEY="<from docker-env.local>"

# 1. Create a collection
curl -s -X POST http://localhost:8686/api/v1/tools/admin_collection_create \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"profile": "default", "collection": "docker-test"}' | python3 -m json.tool

# 2. Ingest a document
curl -s -X POST http://localhost:8686/api/v1/tools/ingest_text \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "default",
    "collection": "docker-test",
    "text": "Cloud-Dog AI platform provides standardised MCP servers for enterprise use.",
    "source": "docker-smoke-test",
    "actor": "docker-test"
  }' | python3 -m json.tool

# 3. Search for the document
curl -s -X POST http://localhost:8686/api/v1/tools/search \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "default",
    "collection": "docker-test",
    "query": "MCP servers enterprise",
    "top_k": 5
  }' | python3 -m json.tool
# EXPECTED: at least 1 result matching the ingested document
```

---

## 10. Stop and Clean Up

```bash
docker stop index-retriever-test 2>/dev/null; docker rm index-retriever-test 2>/dev/null
```

---

## 11. Quality Gates — All Must Pass

| # | Gate | Command | Expected |
|---|------|---------|----------|
| 1 | Image builds | `./docker-build.sh` | exit 0 |
| 2 | Image exists | `docker images \| grep index-retriever` | 1 row |
| 3 | No secrets in image | `docker history ... \| grep secret` | no output |
| 4 | Container starts | `docker run --network host ...` | running |
| 5 | Non-root user | `docker exec ... whoami` | appuser |
| 6 | Health check passes | `curl http://localhost:8686/health` | 200 |
| 7 | Tool catalogue returns | `curl .../api/v1/tools` | 200 + tools |
| 8 | Auth rejection works | `curl ... -H "x-api-key: bad"` | 401/403 |
| 9 | Port is 8686 not 8080 | `grep port defaults.yaml` | 8686 |
| 10 | UT regression | `pytest tests/unit/ --env UT` | 30 passed |
| 11 | All tiers pass | UT+ST+IT+AT+QT+CT | 67 passed |
| 12 | Compose individual | `docker compose up api mcp` | both healthy |

---

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Build fails with proxy error | `HTTP_PROXY` not set | `export HTTP_PROXY=...` before build |
| Health check timeout | Server not starting | `docker logs index-retriever-test` |
| Tool ops fail with VDB error | Qdrant/Chroma unreachable | Check backend connectivity |
| Embedding fails | Ollama unreachable | Verify Ollama on llm1/llm2 |
| Port 8686 already in use | Another service | `lsof -ti :8686` and kill |
| ST/IT tests fail | Live backends needed | UT/QT always pass without backends |

---

## 13. Absolute Prohibitions

1. DO NOT bake secrets into the Docker image.
2. DO NOT change the port from 8686/8687 in defaults.yaml (use PORT-REGISTRY.md).
3. DO NOT revert the port back to 8080 — it clashes with sql-agent web UI.
4. DO NOT import chromadb, qdrant_client, or openai directly — use platform packages.
5. DO NOT run the container as root in production.
6. DO NOT log to /tmp/ — log to /app/logs/.
7. DO NOT use `docker build` without `--network=host` (proxy required).
