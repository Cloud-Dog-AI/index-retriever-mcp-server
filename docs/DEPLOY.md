# Deploy Guide — index-retriever-mcp-server

## 1. Docker Deployment

### Build
```bash
./docker-build.sh
```

### Run (single-host example)
```bash
docker run --rm \
  --name index-retriever \
  -p 8686:8686 -p 8687:8687 \
  --env-file tests/env-IT \
  registry.cloud-dog.net/cloud-dog-ai/index-retriever-mcp-server:latest
```

### Compose
```bash
docker compose up -d
```

## 2. Bare Metal Deployment

### Install
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

### Run under supervisor/systemd
- Use `server_control.sh --env <env-file> start all` for process management.
- Recommended split services:
  - API: `src/index_server/api_server.py`
  - MCP: `src/index_server/mcp_server.py`

## 3. Terraform Reference

Infrastructure deployments are managed in:
- `/opt/iac/Development/cloud-dog-repo/terraform/`

This repository does not apply Terraform directly.

## 4. Vault Integration

### Bootstrap
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
bash scripts/validate-vault.sh
```

### Vault paths used
- `dev.databases`
- `dev.models`
- `dev.vdbs`
- `dev.storage`
- `dev.redis`
- `dev.repository`

## 5. Database Options

| Mode | Dialect | Use | Key Variables |
|---|---|---|---|
| Local dev | SQLite | fast local iteration | `DB_URL=sqlite+aiosqlite:///...` |
| Preprod/prod | PostgreSQL | recommended persistent metadata | `CLOUD_DOG__INDEX__DB__URL` or `DB_URL` |
| Optional | MySQL | compatibility testing path | `CLOUD_DOG_DB__*` / `CLOUD_DOG__DB__*` |

Migration/initialisation is handled by runtime startup (`index_tools.db.initialise_database`).

## 6. VDB Options

Supported backends (via `cloud_dog_vdb`):
- Chroma
- Qdrant
- OpenSearch
- PGVector
- Weaviate
- Infinity

Primary configuration keys are documented in [ENV-REFERENCE.md](ENV-REFERENCE.md).

## 7. LLM/Embedding Configurations

Embedding route is provided through `cloud_dog_llm`.

Tested model matrix in this project test suite includes:
- `bge-m3:567m` (1024 dimensions)
- `nomic-embed-text` (768 dimensions)
- `granite-embedding:278m` (768 dimensions)

Typical endpoints:
- `https://llm1.cloud-dog.net`
- `https://llm2.cloud-dog.net`

## 8. Health Check

- API health: `GET /health`
- Canonical API health: `GET /app/v1/health`
- A2A health (auth required): `GET /a2a/health`
- MCP health: `GET /health` on MCP listener

Expected payload includes:
- top-level `status: "ok"`
- backend checks for DB, VDB, embedding on API health payload

## 9. Monitoring and Audit

- Runtime logs: `logs/`
- Audit logs:
  - API: `CLOUD_DOG__INDEX__API_AUDIT_PATH` (fallback `logs/index-retriever-audit-api.jsonl`)
  - MCP: `CLOUD_DOG__INDEX__MCP_AUDIT_PATH` (fallback `logs/index-retriever-audit-mcp.jsonl`)
- Test and agent evidence: `working/`
- Operational diagnostics: `server_control.sh --env <env-file> status all`

## Preprod Deployment Reference

### Terraform

- Terraform root: `/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/60 Cloud-Dog AI Containers`
- Public hostname: `https://indexretriever0.cloud-dog.net`
- Container name: `indexretriever0.app.vpc0.cloud-dog.net`

### Health Verification

```bash
curl -sk https://indexretriever0.cloud-dog.net/health
curl -sk https://indexretriever0.cloud-dog.net/login
```

### Rollback

1. Identify the last known good registry tag or digest.
2. Update the deployment target back to that tag or digest.
3. Re-apply Terraform or re-run the deployment workflow for this service.
4. Re-check `/health`, the public login route, and any project-specific API or MCP health endpoints.
