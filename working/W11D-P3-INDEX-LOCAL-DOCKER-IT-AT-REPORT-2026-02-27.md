# W11D-P3 Index-Retriever Local-Docker IT/AT Strict Report (2026-02-27)

## Scope
- Project: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`
- Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W11D-03-INDEX-RETRIEVER-LOCAL-DOCKER-IT-AT-STRICT.md`
- Goal: strict local-docker IT/AT run with Vault-backed live provider gating.

## Exact Commands Executed
```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server

set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a

bash local-docker-server.sh --env tests/env-local-docker-server ensure
curl -fsS http://127.0.0.1:8686/health >/tmp/w11d_index_health_api.json
curl -fsS http://127.0.0.1:8687/tools >/tmp/w11d_index_tools.json

a=0
python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q || a=$?
python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q || a=$?
python3 -m pytest tests/application/AT1_1 --env tests/env-AT-local-docker -q || a=$?
exit $a
```

## Hard-Stop Capability Checks
Socket checks were executed before required tests and after runtime ensure.

- Pre-run live dependencies:
  - `CONNECT_OK vault vault0.cloud-dog.net:8200`
  - `CONNECT_OK embed llm1.cloud-dog.net:443`
  - `CONNECT_OK chroma chroma.cloud-dog.net:443`
  - `CONNECT_OK qdrant vdb1.app.vpc0.cloud-dog.net:6333`
- Post-ensure local endpoints:
  - `CONNECT_OK api 127.0.0.1:8686`
  - `CONNECT_OK mcp 127.0.0.1:8687`

No permission-capability restriction occurred (`PermissionError` / `errno=1` not encountered). No `BLOCKED` condition triggered.

## Runtime Ensure + Precheck Output
- `bash local-docker-server.sh --env tests/env-local-docker-server ensure`
  - Result: `ALREADY RUNNING with matching env`
  - Service row: `index-retriever-all ... Up ... (healthy)`

Captured precheck files:
- `/tmp/w11d_index_health_api.json`
  - Body: `{\"status\":\"ok\",\"application\":\"index-retriever-mcp-server\",\"version\":\"0.1.0\",\"env_file\":null}`
  - SHA256: `6d743e7ccfa94a025e1e81d6f1490593a9b10d7456de81d10238d1e1d93cf636`
- `/tmp/w11d_index_tools.json`
  - Body: tool catalogue payload from `GET /tools` (JSON)
  - SHA256: `d8a8d749e815fbccf74da3cdc8b9853243041cfa1bc12b29240626697b7b1aee`

## Image / Hash Evidence
- Container: `631d636d7963`
- Image: `index-retriever-local-docker-all-in-one`
- Image ID: `sha256:937a3d17d6be3e253a03c1d74a517cd087a0587700ae07abea20c547cdc86f3f`
- Runtime env file: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server/tests/env-IT-local-docker`
- Runtime env hash: `2b5377ab75dd1510bed7c08f1ecc6d052b5243283dbffa0ac500a4dd5fa1fd0b`
- Code revision: `ae460a1`

## Test Results
- `python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q`
  - `12 passed in 7.98s`
- `python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q`
  - `7 passed in 7.22s`
- `python3 -m pytest tests/application/AT1_1 --env tests/env-AT-local-docker -q`
  - `1 passed in 1.67s`

Final exit accumulator: `W11D_EXIT_CODE=0`.

## Blocker Detail
- None. Required local-docker endpoint checks and live preflight conditions passed.
