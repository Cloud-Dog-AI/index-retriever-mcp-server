# PREPROD Deployment - index-retriever-mcp-server

## 1. Container
- Image: `registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest`
- Hostname: `indexretriever0.cloud-dog.net`
- Public URL: `https://indexretriever0.cloud-dog.net`
- Network IP: `10.26.2.69`
- Terraform source: `/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/27 MLAgents/indexretriever_containers.tf.json`

## 2. Ports
| Interface | Internal port | Traefik entrypoint | Public path |
|---|---:|---|---|
| API | `8083` | `securestream` | `https://indexretriever0.cloud-dog.net/api` |
| MCP | `8081` | `mcpserver` | `https://indexretriever0.cloud-dog.net/mcp` |
| Health | `8083` | `websecure` | `https://indexretriever0.cloud-dog.net/health` |

## 3. Volume Mounts
| Container path | Host path | Purpose |
|---|---|---|
| `/app/logs` | `/opt/docker/indexretriever0/logs` | Logs |
| `/app/data` | `/opt/docker/indexretriever0/data` | SQLite DB and data |
| `/app/certs` | `/opt/docker/indexretriever0/certificates` | TLS trust bundle |

## 4. Environment (Delta from defaults.yaml)
### Runtime
- API server `0.0.0.0:8083`
- MCP server `0.0.0.0:8081`
- Vault direct integration enabled via `VAULT_ADDR`, `VAULT_MOUNT_POINT`, `VAULT_CONFIG_PATH`

### Data and embeddings
- Qdrant URL via `vault.dev.vdbs.qdrant.url`
- Embeddings via `vault.dev.models.ollama_nomic_embed_text_llm1.*`
- SQLite DB path: `sqlite+aiosqlite:///data/index-retriever-preprod.db`

### Auth
- API keys via `vault.dev.services.indexretriever0.api_key`

## 5. External Dependencies
| Dependency | Endpoint | Required |
|---|---|---|
| Qdrant | `http://vdb1.app.vpc0.cloud-dog.net:6333` | Y |
| Embeddings | `https://llm1.cloud-dog.net` | Y |
| Vault | `https://vault0.cloud-dog.net` | Y |

## 6. Health Check
`curl -fsS https://indexretriever0.cloud-dog.net/health` -> HTTP `200`

## 7. Deployment
Managed by Terraform. Do NOT deploy manually.

## 8. Verification
1. `curl -fsS https://indexretriever0.cloud-dog.net/health`
2. API auth check with index-retriever API key
3. MCP reachability check on `/mcp`
4. Confirm logs in `/opt/docker/indexretriever0/logs`

## Vault Gaps
- None for required preprod container settings.
