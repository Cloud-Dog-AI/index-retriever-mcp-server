# W13B Index-Retriever VDB 0.4.1 Adoption Report (2026-03-01)

Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W13B-INDEX-RETRIEVER-VDB-0.4.1-ADOPTION-STRICT.md`

## Final Verdict

`COMPLETE VERIFIED`

## Runtime Identity

- Runtime controller env: `tests/env-local-docker-server`
- Runtime env: `tests/env-IT-local-docker`
- Container: `index-retriever-all`
- Image: `index-retriever-local-docker-all-in-one`
- Image ID: `sha256:4dabd651208252abd5dc0bd743687dd3ace7b74bb85f6f29f09b835dbe2e2766`
- Code revision: `ae460a1`
- Local-docker endpoints:
  - API: `http://127.0.0.1:8686`
  - MCP: `http://127.0.0.1:8687`

## Preconditions / Capability Gate

Commands executed:

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
ls -l /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-vdb/dist/cloud_dog_vdb-0.4.1-py3-none-any.whl
ls -l /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-vdb/dist/cloud_dog_vdb-0.4.1.tar.gz
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
python3 - <<'PY'
import socket
for host, port in [("127.0.0.1", 8686), ("127.0.0.1", 8687), ("llm1.cloud-dog.net", 443)]:
    s = socket.create_connection((host, port), timeout=3)
    s.close()
    print(f"CONNECT_OK {host}:{port}")
PY
```

Observed results:
- wheel + sdist present (`cloud_dog_vdb-0.4.1`)
- `CONNECT_OK 127.0.0.1:8686`
- `CONNECT_OK 127.0.0.1:8687`
- `CONNECT_OK llm1.cloud-dog.net:443`

## Guidance Assimilation

Guidance mapping report:
- `working/W13B-INDEX-RETRIEVER-GUIDANCE-MAPPING-2026-03-01.md`

Disposition counts:
- `ADOPTED`: 9
- `DEFERRED`: 1
- `REJECTED`: 1

## Implementation Summary

1. Dependency/build upgrade to `cloud_dog_vdb>=0.4.1`:
- `pyproject.toml`
- `Dockerfile`
- `vendor/wheels/cloud_dog_vdb-0.4.1-py3-none-any.whl`

2. Runtime capability adoption:
- metadata round-trip fields added and normalized
- capability-aware search planning and filter guard
- provider diagnostic envelope with redaction
- Infinity conditional runtime support

3. Responsibility boundary and tool-catalogue uplift:
- delegated wrapper tool surfaces implemented (`parsers_list`, `parser_test`, `ingest_preview`, `extract_only`, `ocr_run`, `table_extract`)
- MCP role map and dispatch added for new tools

4. Tests and coverage:
- Added IT/CT/AT/QT coverage for W13B behaviours
- Added UT closure tests for all new service/MCP branches
- Full suite coverage reached `100%`

## Canonical Doc/Traceability Updates

Updated canonical docs:
- `REQUIREMENTS.md` (W13B FR-13A + tool-catalogue additions)
- `ARCHITECTURE.md` (delegated parser boundary + capability/diagnostic/infinity architecture notes)
- `TESTS.md` (W13B strict evidence, commands, env files, test ID mapping)

## Strict Command Set (exact) and Outcomes

Executed backend strict sequence:

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
bash local-docker-server.sh --env tests/env-local-docker-server restart | tee /tmp/w13b_idx_runtime_restart.log
curl -fsS http://127.0.0.1:8686/health | tee /tmp/w13b_idx_health_api.json
curl -fsS http://127.0.0.1:8687/mcp/tools | tee /tmp/w13b_idx_mcp_tools.json
python3 -m pytest tests/unit/ --env tests/env-UT-local-docker -q | tee /tmp/w13b_idx_ut.log
python3 -m pytest tests/system/ --env tests/env-ST-local-docker -q | tee /tmp/w13b_idx_st.log
python3 -m pytest tests/contract/ --env tests/env-IT-local-docker -q | tee /tmp/w13b_idx_ct.log
python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q | tee /tmp/w13b_idx_it.log
python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q | tee /tmp/w13b_idx_at.log
python3 -m pytest tests/security/ --env tests/env-QT-local-docker -q | tee /tmp/w13b_idx_qt.log
```

Exact summary lines:
- UT: `71 passed, 2 warnings in 1.39s`
- ST: `12 passed in 10.21s`
- CT: `4 passed in 4.22s`
- IT: `17 passed in 9.34s`
- AT: `8 passed in 9.33s`
- QT: `6 passed in 2.30s`

Executed WebUI strict sequence:

```bash
cd /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
npm run lint -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w13b_idx_ui_lint.log
npm run typecheck -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w13b_idx_ui_typecheck.log
npm run e2e -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w13b_idx_ui_e2e.log
npm run a11y -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w13b_idx_ui_a11y.log
```

Exact summary lines:
- lint: `Tasks: 8 successful, 8 total`
- typecheck: `Tasks: 8 successful, 8 total`
- e2e: `12 passed (25.8s)`
- a11y: `2 passed (13.4s)`

## RULES/Test-Integrity Evidence

- `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
  - Result: `PASS 10, FAIL 0, WARN 5`
- Vault-less failure proof:
  - `env -u VAULT_TOKEN -u VAULT_ADDR -u VAULT_NAMESPACE -u CLOUD_DOG__VAULT__TOKEN python3 -m pytest tests/integration --env tests/env-IT -q -rs || true`
  - Result: `17 errors` with explicit `missing VAULT_TOKEN`; no skip masking
- Full coverage command:
  - `python3 -m pytest tests/ --env tests/env-UT-local-docker --env tests/env-ST-local-docker --env tests/env-IT-local-docker --env tests/env-AT-local-docker --env tests/env-QT-local-docker -q -rs --cov=src --cov-report=term-missing | tee /tmp/w13b_idx_cov.log`
  - Result: `118 passed, 2 warnings`; `TOTAL 1383 0 100%`

## First Failing Assertion(s) Observed During W13B Execution

During immediate post-restart health checks (startup race):
- `curl: (7) Failed to connect to 127.0.0.1 port 8686: Connection refused`
- `curl: (7) Failed to connect to 127.0.0.1 port 8687: Connection refused`

Resolution/evidence:
- Re-ran health/tool checks after container reached healthy state.
- Final artifacts:
  - `/tmp/w13b_idx_health_api.json` (HTTP 200 health payload)
  - `/tmp/w13b_idx_mcp_tools.json` (HTTP 200 MCP catalogue payload)

## File Diff Summary (W13B)

Core runtime/tooling:
- `pyproject.toml`
- `Dockerfile`
- `src/index_tools/pipeline/metadata.py`
- `src/index_tools/tools/service.py`
- `src/index_tools/tools/definitions.py`
- `src/index_tools/tools/registry.py`
- `src/index_server/mcp_server.py`
- `tests/live_runtime.py`

W13B tests:
- `tests/integration/IT1_13/test_it1_13.py`
- `tests/integration/IT1_14/test_it1_14.py`
- `tests/integration/IT1_15/test_it1_15.py`
- `tests/integration/IT1_16/test_it1_16.py`
- `tests/integration/IT1_17/test_it1_17.py`
- `tests/contract/CT1_4/test_ct1_4_infinity_contract.py`
- `tests/application/AT1_7/test_at1_7.py`
- `tests/security/QT1_6/test_qt1_6.py`
- `tests/unit/UT1_36/test_ut1_36_service_vdb041_branches.py`
- `tests/unit/UT1_37/test_ut1_37_mcp_vdb041_dispatch.py`

Traceability docs and tracker updates:
- `REQUIREMENTS.md`
- `ARCHITECTURE.md`
- `TESTS.md`
- `working/W13B-INDEX-RETRIEVER-GUIDANCE-MAPPING-2026-03-01.md`
- `cloud-dog-ai-platform-standards/migration/MIGRATION_PLAN.md`
- `cloud-dog-ai-platform-standards/CONTEXT-SUMMARY.md`
