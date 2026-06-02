# Publication smoke test (W28A-832)

External local-Docker smoke — starts the container from the external `env.example`
with **no Vault, no preprod, no internal services**, and checks the API / MCP / A2A
/ WebUI surfaces. LLM defaults to OpenRouter; pass `OPENROUTER_API_KEY` on the
command line only if you exercise live LLM features (not needed for the surface smoke).

Reusable harness: `cdci/scripts/publication-smoke.sh` (from the cdci repo).

```bash
docker run -d --name index-smoke --network host \
  -e CLOUD_DOG_ENV_FILE=/app/env.example -v "$PWD/env.example:/app/env.example:ro" \
  cloud-dog/index-retriever-mcp-server:<tag>
# probe API :8083/health  WebUI :8080/  MCP :8081/mcp  A2A :8082/health + /.well-known/agent.json
```

Expected: `RESULT: PASS` (3xx/4xx on auth-gated or login-redirected surfaces still
prove the surface is up). Never use SSH for a remote daemon — use
`DOCKER_HOST=tcp://host:port` (RULES.md §3.2).
