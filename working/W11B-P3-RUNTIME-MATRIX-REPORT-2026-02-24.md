# W11B-P3 Runtime Matrix Report (2026-02-24)

## Directive Compliance
- Followed `RULES.md` and W11B-03 instruction file exactly for runtime matrix scope.
- No stubs/mocks were introduced in ST/IT/AT paths.
- Real live backends were used for ST/IT/AT (`Vault`, `LLM`, `Chroma`, `Qdrant`).
- Hard-stop rule implemented and applied: capability checks run before each live-tier command; any `PermissionError`/`errno=1` would terminate as `BLOCKED`.

## Runtime Mode Contract Added
- `INDEX_RETRIEVER_RUNTIME_MODE` (strict values):
  - `local-server`
  - `local-docker`
  - `remote-runtime`
- External endpoint contract for non-local-server modes:
  - `INDEX_RETRIEVER_API_BASE_URL`
  - `INDEX_RETRIEVER_MCP_BASE_URL`

## Files Added/Updated
- Updated: `tests/conftest.py`
  - added runtime mode validation fixtures
  - added external endpoint preflight and capability checks for non-local-server modes
- Updated: `tests/integration/IT1_6/test_it1_6.py`
  - `local-docker`/`remote-runtime` now call real `GET /mcp/tools`
- Updated: `tests/integration/IT1_7/test_it1_7.py`
  - `local-docker`/`remote-runtime` now call real `POST /api/v1/tools/{tool}`
- Added: `tests/application/AT1_6/test_at1_6.py`
  - runtime-matrix transport flow through API + MCP endpoints
- Added env matrix (committed):
  - `tests/env-UT-local-server`
  - `tests/env-ST-local-server`
  - `tests/env-IT-local-server`
  - `tests/env-AT-local-server`
  - `tests/env-UT-local-docker`
  - `tests/env-ST-local-docker`
  - `tests/env-IT-local-docker`
  - `tests/env-AT-local-docker`
- Added env matrix (private/gitignored):
  - `private/env-UT-remote-runtime`
  - `private/env-ST-remote-runtime`
  - `private/env-IT-remote-runtime`
  - `private/env-AT-remote-runtime`

## Endpoint Runtime Setup Used
- Server control (rules-compliant):
  - `./server_control.sh --env /opt/iac/Development/cloud-dog-ai/env-vault stop all`
  - `./server_control.sh --env /opt/iac/Development/cloud-dog-ai/env-vault start api`
  - `./server_control.sh --env /opt/iac/Development/cloud-dog-ai/env-vault start mcp`
- Health checks:
  - `http://127.0.0.1:8686/health` -> `200`
  - `http://127.0.0.1:8687/health` -> `200`

## Capability Statement (Hard-Stop)
Before each live-tier run (ST/IT/AT), checks returned `CONNECT_OK` for:
- `vault0.cloud-dog.net:8200`
- `llm1.cloud-dog.net:443`
- `chroma.cloud-dog.net:443`
- `vdb1.app.vpc0.cloud-dog.net:6333`
- plus non-local-server modes:
  - `127.0.0.1:8686` (API)
  - `127.0.0.1:8687` (MCP)

No permission capability restriction occurred (`PermissionError`/`errno=1` not seen). No `BLOCKED` condition triggered.

## Required Commands and Results
`pytest` was not on PATH; equivalent commands were executed using `.venv/bin/pytest`.

### local-server
1. `.venv/bin/pytest tests/unit/ --env tests/env-UT-local-server -q` -> `61 passed`
2. `.venv/bin/pytest tests/system/ --env tests/env-ST-local-server -q` -> `12 passed`
3. `.venv/bin/pytest tests/integration/ --env tests/env-IT-local-server -q` -> `12 passed`
4. `.venv/bin/pytest tests/application/ --env tests/env-AT-local-server -q` -> `7 passed`

### local-docker
1. `.venv/bin/pytest tests/unit/ --env tests/env-UT-local-docker -q` -> `61 passed`
2. `.venv/bin/pytest tests/system/ --env tests/env-ST-local-docker -q` -> `12 passed`
3. `.venv/bin/pytest tests/integration/ --env tests/env-IT-local-docker -q` -> `12 passed`
4. `.venv/bin/pytest tests/application/ --env tests/env-AT-local-docker -q` -> `7 passed`

### remote-runtime
1. `.venv/bin/pytest tests/unit/ --env private/env-UT-remote-runtime -q` -> `61 passed`
2. `.venv/bin/pytest tests/system/ --env private/env-ST-remote-runtime -q` -> `12 passed`
3. `.venv/bin/pytest tests/integration/ --env private/env-IT-remote-runtime -q` -> `12 passed`
4. `.venv/bin/pytest tests/application/ --env private/env-AT-remote-runtime -q` -> `7 passed`

## Evidence Logs
Per-command logs:
- `working/w11b-rmx-logs/UT-local-server.log`
- `working/w11b-rmx-logs/ST-local-server.log`
- `working/w11b-rmx-logs/IT-local-server.log`
- `working/w11b-rmx-logs/AT-local-server.log`
- `working/w11b-rmx-logs/UT-local-docker.log`
- `working/w11b-rmx-logs/ST-local-docker.log`
- `working/w11b-rmx-logs/IT-local-docker.log`
- `working/w11b-rmx-logs/AT-local-docker.log`
- `working/w11b-rmx-logs/UT-remote-runtime.log`
- `working/w11b-rmx-logs/ST-remote-runtime.log`
- `working/w11b-rmx-logs/IT-remote-runtime.log`
- `working/w11b-rmx-logs/AT-remote-runtime.log`

## Final Status
- Runtime matrix Step 0 completed.
- No blocked capability condition.
- All 12 required matrix test commands passed.
