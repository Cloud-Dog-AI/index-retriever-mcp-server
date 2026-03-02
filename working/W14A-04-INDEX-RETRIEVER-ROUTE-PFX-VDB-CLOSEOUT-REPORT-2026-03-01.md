# W14A-04 Index-Retriever Route-Prefix + VDB Closeout Report (2026-03-01)

Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14A-04-INDEX-RETRIEVER-ROUTE-PFX-VDB-CLOSEOUT-STRICT.md`

## Final Verdict

`COMPLETE VERIFIED`

## Scope Closure

- `ROUTE-PFX-03`: closed with canonical route-prefix env contract and runtime route probes.
- `IDX-VDB-041`: already complete from W13B, re-validated in this closeout.
- Residual index `TEST-INTEGRITY` row: closed with current strict evidence.

## Hard-stop Prechecks (exact commands)

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
bash local-docker-server.sh --env tests/env-local-docker-server ensure | tee /tmp/w14a04_index_runtime_ensure.log
curl -fsS http://127.0.0.1:8686/health >/tmp/w14a04_index_health_pre.json
curl -fsS http://127.0.0.1:8687/mcp/tools >/tmp/w14a04_index_tools_pre.json
python3 - <<'PY' | tee /tmp/w14a04_index_vdb_version.log
import cloud_dog_vdb
print(cloud_dog_vdb.__version__)
PY
```

Precheck results:
- runtime ensure: `ALREADY RUNNING with matching env`
- API pre-health: HTTP 200
- MCP tools precheck: HTTP 200 (`ok=true`)
- VDB version: `0.4.1`

## Route-prefix Contract Adoption

Applied in active env files (`tests/env-*`):
- `TEST_API_BASE_PATH=/app/v1`
- `TEST_MCP_BASE_PATH=/mcp`
- `TEST_WEB_BASE_PATH=/`
- `TEST_A2A_BASE_PATH=/a2a`

Updated test path derivation:
- new helper: `tests/http_paths.py`
- integration/application/security tests now build tool endpoints from env contract keys.

Runtime API routes:
- canonical: `/app/v1/tools`, `/app/v1/tools/{tool_name}`, `/app/v1/health`
- compatibility alias retained: `/api/v1/tools`, `/api/v1/tools/{tool_name}`

MCP catalogue:
- canonical: `/mcp/tools`
- optional legacy alias retained as compatibility-only: `/tools`

## Strict Verification (exact commands)

Executed with Vault sourced for live-tier requirements:

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
python3 -m pytest tests/unit/ --env tests/env-UT-local-docker -q | tee /tmp/w14a04_index_ut.log
python3 -m pytest tests/system/ --env tests/env-ST-local-docker -q | tee /tmp/w14a04_index_st.log
python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q | tee /tmp/w14a04_index_it.log
python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q | tee /tmp/w14a04_index_at.log
curl -fsS http://127.0.0.1:8686/app/v1/health | tee /tmp/w14a04_index_health_canonical.json
curl -fsS http://127.0.0.1:8687/mcp/tools | tee /tmp/w14a04_index_tools_canonical.json
curl -fsS http://127.0.0.1:8687/tools | tee /tmp/w14a04_index_tools_legacy_alias.json
```

Exact summary lines:
- UT: `71 passed, 2 warnings in 1.58s`
- ST: `12 passed in 11.19s`
- IT: `17 passed in 9.12s`
- AT: `8 passed in 8.90s`

Route probe outputs:
- canonical API health (`/app/v1/health`):
  - `{"status":"ok","correlation_id":"...","checks":{"vdb":{"status":"ok","backend":"in-memory","provider":"chroma"},"embedding":{"status":"ok","dimensions":8}}}`
- canonical MCP catalogue (`/mcp/tools`):
  - `ok=true`, `tools=37`
- legacy alias (`/tools`):
  - `tools=37` (compatibility-only)

## WebUI Validation (exact commands)

```bash
cd /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
npm run lint -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14a04_index_ui_lint.log
npm run typecheck -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14a04_index_ui_typecheck.log
npm run e2e -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14a04_index_ui_e2e.log
npm run a11y -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14a04_index_ui_a11y.log
```

Exact summary lines:
- lint: `Tasks: 8 successful, 8 total`
- typecheck: `Tasks: 8 successful, 8 total`
- e2e: `12 passed (25.8s)`
- a11y: `2 passed (13.4s)`

## First Failing Assertion Per Failure (during execution)

Initial strict run failed before final pass due stale runtime image serving old API routes.

1. IT1.17 first failure
- `AssertionError: HTTP 404 for http://127.0.0.1:8686/app/v1/tools/parsers_list: {"detail":"Not Found"}`

2. IT1.7 first failure
- `AssertionError: HTTP 404 for http://127.0.0.1:8686/app/v1/tools/admin_collection_create: {"detail":"Not Found"}`

Root cause and fix:
- compose build was performed under a non-matching project name, producing image `index-retriever-mcp-server-all-in-one` while runtime used `index-retriever-local-docker-all-in-one`.
- fixed by no-cache rebuild with explicit local-docker project name and restart:
  - image updated to `sha256:0648af633a50f7f59b1e7e6329e90e02836c97307e16adec4c94c20b63cb569c`
  - rerun strict sequence passed fully.

## VDB 0.4.1 Evidence

- package version check: `/tmp/w14a04_index_vdb_version.log` -> `0.4.1`
- dependency wiring remained aligned with W13B:
  - `pyproject.toml` uses `cloud_dog_vdb>=0.4.1`
  - Docker installs `vendor/wheels/cloud_dog_vdb-0.4.1-py3-none-any.whl`

## Test-Integrity Evidence (residual row closure)

Command:

```bash
bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh . | tee /tmp/w14a04_index_verify_test_integrity.log
```

Result summary:
- `PASS: 10`
- `FAIL: 0`
- `WARN: 5` (decoration warnings on `env-local-docker-server` control keys only)

## Requirements / Architecture / Tests Traceability Delta

1. Requirements delta
- `REQUIREMENTS.md`:
  - added FR-01A canonical route-prefix contract (`/app/v1`, `/mcp`, `/`, `/a2a`)
  - explicit `TEST_*_BASE_PATH` env contract keys
  - canonical usage requirement with `/api/v1` compatibility-only clause

2. Architecture delta
- `ARCHITECTURE.md`:
  - added route-prefix contract section with canonical and compatibility paths

3. Test traceability delta
- `TESTS.md`:
  - added `Latest W14A-04 Status (2026-03-01)` section
  - added strict command evidence and route probe outputs
  - updated historical MCP probe examples from `/tools` to canonical `/mcp/tools`
  - documented route-prefix env keys in environment requirements

## Runtime Identity (final strict pass)

- Container: `index-retriever-all`
- Image: `index-retriever-local-docker-all-in-one:latest`
- Image ID: `sha256:0648af633a50f7f59b1e7e6329e90e02836c97307e16adec4c94c20b63cb569c`
