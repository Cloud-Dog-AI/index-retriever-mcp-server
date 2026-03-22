# PREPROD Deployment — Index Retriever MCP Server

This document describes the pre-production operator/deployment overlay for this service. The Terraform container environment is the runtime source of truth, and `private/env-PREPROD` is the operator/test overlay used for local control commands and pytest runs against the deployed preprod service. Defaults and non-preprod settings remain documented in `docs/ENV-REFERENCE.md`, `docs/ARCHITECTURE.md`, and `defaults.yaml`.

## 1. Overview
- Service URL: `https://indexretriever0.cloud-dog.net`
- Container hostname: `indexretriever0.app.vpc0.cloud-dog.net`
- Health endpoint verified during W28A-241: `https://indexretriever0.cloud-dog.net/health`
- Docker image: `registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest`
- Active Terraform container definition: `/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/60 Cloud-Dog AI Containers/indexretriever_containers.tf.json`
- Legacy/parallel Terraform definition to cross-check when investigating drift: `/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/27 MLAgents/indexretriever_containers.tf.json`
- Operator overlay file: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server/private/env-PREPROD`

### Port allocation
| Surface | Internal port | External URL |
|---|---:|---|
| API | 8083 | `https://indexretriever0.cloud-dog.net` (health exposed at `/health`) |
| MCP | 8081 | `https://indexretriever0.cloud-dog.net/mcp` |
| A2A/Test auth | internal/test only | use API key from Vault |

## 2. Configuration
Section 2 documents the full preprod environment surface that differs from or materially specialises the defaults. Use it together with `defaults.yaml` and `docs/ENV-REFERENCE.md` when tracing a value through the precedence chain `os.environ -> --env file -> config.yaml -> defaults.yaml`.

### Server and auth settings
| Setting(s) | Default / baseline | Preprod source | Preprod change? | Notes |
|---|---|---|---|---|
| `CLOUD_DOG__INDEX__API_SERVER__HOST/PORT` | `0.0.0.0:8686` via defaults | Terraform + `private/env-PREPROD` | Yes | Preprod API binds to `8083` internally and is proxied externally. |
| `CLOUD_DOG__INDEX__MCP_SERVER__HOST/PORT` | `8687` in defaults | Terraform + `private/env-PREPROD` | Yes | MCP binds to `8081`. |
| `CLOUD_DOG__INDEX__AUTH__API_KEYS`, `TEST_A2A_API_KEY` | blank | Vault-backed Terraform + `private/env-PREPROD` | Yes | Required for API and A2A smoke checks. |
| CA/Vault variables (`REQUESTS_CA_BUNDLE`, `VAULT_*`, `CLOUD_DOG__VAULT__*`) | unset | Terraform + `private/env-PREPROD` | Yes | Needed for Vault expression resolution and TLS trust. |

### VDB, embeddings, and storage settings
| Setting(s) | Default / baseline | Preprod source | Preprod change? | Notes |
|---|---|---|---|---|
| `CLOUD_DOG__INDEX__VDB__PROVIDER`, `...QDRANT_URL`, `QDRANT_URL` | defaults favour local Chroma | Terraform + `private/env-PREPROD` | Yes | Preprod uses Qdrant for the shared retrieval backend. |
| `CLOUD_DOG__INDEX__EMBEDDING__PROVIDER/MODEL/BASE_URL`, `EMBED_BASE_URL` | defaults use OpenAI-compatible `nomic-embed-text` | Terraform + `private/env-PREPROD` | Yes | Preprod pins Ollama embedding service settings. |
| `DB_URL`, `INDEX_RETRIEVER_DB_URL`, `CLOUD_DOG__INDEX__DB__URL` | sqlite default under `./data` | Terraform + `private/env-PREPROD` | Yes | Container stores state under `/data/index-retriever-preprod.db`. |
| `CLOUD_DOG__INDEX__API_AUDIT_PATH`, `...MCP_AUDIT_PATH`, `...STORAGE__AUDIT__PATH` | defaults use repo-local logs | Terraform | Yes | Container log paths are explicitly set. |
| `INDEX_RETRIEVER_RUNTIME_MODE`, `TEST_ENV_TIER` | not set in defaults | Terraform | Yes | Preprod container runs as `local-docker`; operator tests layer `private/env-PREPROD` on top. |

## 3. Preprod-Specific Overrides
Only settings that differ materially from defaults or that must be supplied for preprod are listed here. The literal operator/test overlay is `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server/private/env-PREPROD`.

| Override | Why preprod differs | Source of truth |
|---|---|---|
| API/MCP ports 8083/8081 | Aligns with the all-in-one preprod container layout. | Terraform 60-container file |
| Qdrant backend instead of local Chroma | Shared preprod retrieval stack uses managed Qdrant. | Vault + Terraform |
| Ollama embedding endpoint/model | Preprod pins a shared embedding service, not the conceptual default. | Vault + Terraform |
| SQLite DB path under `/data` | Container persistence path differs from repo-local development. | Terraform 60-container file |
| Explicit audit log paths | Container log volume is under `/app/logs`. | Terraform 60-container file |

## 4. Vault Configuration
This service reads preprod secrets from the shared Vault config blob at `cloud_dog_ai/config`.

### Required Vault paths
- `dev.services.indexretriever0` for API keys
- `dev.vdbs.qdrant` for Qdrant URL/credentials if required
- `dev.models.ollama_nomic_embed_text_llm1` for embedding provider/model/base URL

### Operator setup
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
vault kv get -mount=cloud_dog_ai config
```

### Populate or refresh missing entries
Use a merged JSON payload rather than editing Terraform or the running container.

```bash
vault kv put -mount=cloud_dog_ai config   content=@/tmp/cloud-dog-ai-config.preprod.json
```

Example payload fragment:
```json
{
  "dev": {
    "services": {"indexretriever0": {"api_key": "<API_KEY>"}},
    "vdbs": {"qdrant": {"url": "<QDRANT_URL>"}}
  }
}
```

## 5. Deployment Steps
The project rules forbid ad-hoc `docker build`; use the repo entrypoint script.

1. Load Vault-backed build credentials.
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
```
2. Build the image.
```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server && bash docker-build.sh latest
```
3. Tag and push the image.
```bash
docker tag cloud-dog/index-retriever-mcp-server:latest registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest
docker push registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest
```
4. Plan and apply the Terraform update from the shared preprod workspace.
```bash
cd '/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/60 Cloud-Dog AI Containers'
terraform plan -out=tfplan.out
terraform apply tfplan.out
```
5. Verify the deployed service.
```bash
curl -fsS https://indexretriever0.cloud-dog.net/health
```

## 6. Testing Against Preprod
Use the committed tier env file plus `private/env-PREPROD` as the environment-specific overlay.

1. `pytest tests/system --env tests/env-ST --env private/env-PREPROD -q`
2. `pytest tests/integration --env tests/env-IT --env private/env-PREPROD -q`
3. Parser/provider-specific preprod tests can add extra overlays, but `private/env-PREPROD` is the required base preprod layer.

Known limitations:
- Long-running ingest jobs should be run one at a time on shared preprod.
- Parser-specific destructive corpus tests should avoid shared collections unless namespaced.

## 7. Troubleshooting
- `curl -fsS https://indexretriever0.cloud-dog.net/health` should return `status=ok`.
- `docker -H server0.viewdeck.com logs indexretriever0.app.vpc0.cloud-dog.net` for runtime logs.
- If vector backend health fails, verify the Qdrant URL in `private/env-PREPROD` and Vault before changing runtime code.
