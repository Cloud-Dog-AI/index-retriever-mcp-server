# W14B-03 — Index-Retriever A2A Enablement + Auth Contract Report (2026-03-01)

## Instruction
- `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14B-03-INDEX-RETRIEVER-A2A-ENABLE-AUTH-CONTRACT-STRICT.md`

## Scope Delivered
- Enabled API runtime A2A namespace:
  - `GET /a2a`
  - `GET /a2a/health`
- Removed `/a2a` 404 gap in local-docker runtime.
- Enforced A2A auth contract using shared API-key authority:
  - no auth => `401`
  - wrong key => `401`
  - `Authorization: Bearer 12345678` => `200`
- Added env contract keys for strict local-server/local-docker test env files:
  - `TEST_A2A_API_KEY=12345678`
  - `CLOUD_DOG__INDEX__AUTH__API_KEYS=test-api-key,12345678`
- Added tests:
  - Unit parity: `tests/unit/UT1_38/test_ut1_38_a2a_auth_contract.py`
  - Integration A2A auth matrix: `tests/integration/IT1_18/test_it1_18_a2a_health_auth_matrix.py`
  - Application A2A flow: `tests/application/AT1_8/test_at1_8_a2a_flow.py`

## Code and Docs Updated
- Runtime/auth:
  - `src/index_server/api_server.py`
  - `src/index_server/auth/middleware.py`
  - `tests/http_paths.py`
- Tests/env:
  - `tests/unit/UT1_31/test_ut1_31_server_runtime_paths.py`
  - `tests/unit/UT1_38/test_ut1_38_a2a_auth_contract.py`
  - `tests/integration/IT1_18/test_it1_18_a2a_health_auth_matrix.py`
  - `tests/application/AT1_8/test_at1_8_a2a_flow.py`
  - `tests/env-UT-local-docker`
  - `tests/env-ST-local-docker`
  - `tests/env-IT-local-docker`
  - `tests/env-AT-local-docker`
  - `tests/env-QT-local-docker`
  - `tests/env-UT-local-server`
  - `tests/env-ST-local-server`
  - `tests/env-IT-local-server`
  - `tests/env-AT-local-server`
- Traceability/docs:
  - `REQUIREMENTS.md`
  - `ARCHITECTURE.md`
  - `TESTS.md`
  - `CONTEXT-SUMMARY.md`
- Standards tracker/context:
  - `cloud-dog-ai-platform-standards/migration/MIGRATION_PLAN.md` (`A2A-AUTH-03`)
  - `cloud-dog-ai-platform-standards/CONTEXT-SUMMARY.md`

## Hard-Stop Prechecks (Exact Commands)
```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
bash local-docker-server.sh --env tests/env-local-docker-server ensure | tee /tmp/w14b03_index_ensure.log
curl -fsS http://127.0.0.1:8686/health >/tmp/w14b03_index_health.json
curl -fsS http://127.0.0.1:8687/mcp/tools >/tmp/w14b03_index_mcp_tools.json
curl -sS -o /tmp/w14b03_index_a2a_noauth.json -w '%{http_code}\n' http://127.0.0.1:8686/a2a/health | tee /tmp/w14b03_index_a2a_noauth.code
curl -sS -H 'Authorization: Bearer 12345678' -o /tmp/w14b03_index_a2a_auth.json -w '%{http_code}\n' http://127.0.0.1:8686/a2a/health | tee /tmp/w14b03_index_a2a_auth.code
```

### First Failing Assertions (Baseline Before Fix)
- Expected no-auth `401` but received `404` for `GET /a2a/health`.
- Expected auth `200` (`Authorization: Bearer 12345678`) but received `404` for `GET /a2a/health`.

### Post-Fix Hard-Stop Results
- `/tmp/w14b03_index_a2a_noauth.code` => `401`
- `/tmp/w14b03_index_a2a_auth.code` => `200`
- `/tmp/w14b03_index_a2a_noauth.json` => `{"detail":"Authentication failed"}`
- `/tmp/w14b03_index_a2a_auth.json` => `{"status":"ok", ...}`
- `/a2a` namespace probe:
  - `/tmp/w14b03_index_a2a_root_noauth.code` => `401`
  - `/tmp/w14b03_index_a2a_root_auth.code` => `200`
  - `/tmp/w14b03_index_a2a_root_auth.json` => `{"status":"ok","service":"index-retriever-a2a","base_path":"/a2a",...}`

## Strict Backend Verification (Exact Commands)
```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
python3 -m pytest tests/unit/ --env tests/env-UT-local-docker -q | tee /tmp/w14b03_index_ut.log
python3 -m pytest tests/system/ --env tests/env-ST-local-docker -q | tee /tmp/w14b03_index_st.log
python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q | tee /tmp/w14b03_index_it.log
python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q | tee /tmp/w14b03_index_at.log
```

### Strict Backend Summary Lines
- `74 passed, 2 warnings in 1.34s` (UT)
- `12 passed in 9.59s` (ST)
- `18 passed in 9.22s` (IT)
- `9 passed in 9.25s` (AT)

## WebUI Strict Block (Exact Commands)
```bash
cd /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
npm run lint -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14b03_index_ui_lint.log
npm run typecheck -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14b03_index_ui_typecheck.log
npm run e2e -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14b03_index_ui_e2e.log
npm run a11y -- --filter=@cloud-dog/app-index-retriever | tee /tmp/w14b03_index_ui_a11y.log
```

### First Failing Assertion in This Block and Resolution
- First run failed with environment issue: `/bin/bash: npm: command not found`.
- Resolved by sourcing nvm in shell (`source ~/.nvm/nvm.sh`) and rerunning exact command block.

### WebUI Summary Lines (Final)
- `Tasks: 8 successful, 8 total` (lint)
- `Tasks: 8 successful, 8 total` (typecheck)
- `12 passed (25.8s)` (e2e)
- `2 passed (13.4s)` (a11y)

## Additional Integrity Gate Evidence (RULES.md)
- `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
  - Result: `PASS: 10`, `FAIL: 0`, `WARN: 5` (`/tmp/w14b03_index_verify_test_integrity.log`)
- No-Vault IT fail-closed:
  - `env -u VAULT_TOKEN -u VAULT_ADDR -u VAULT_NAMESPACE -u CLOUD_DOG__VAULT__TOKEN python3 -m pytest tests/integration --env tests/env-IT-local-docker -q -rs`
  - Result: explicit `missing VAULT_TOKEN`, `18 errors` (`/tmp/w14b03_index_it_no_vault.log`)
- Full coverage with Vault-sourced run:
  - `python3 -m pytest tests/ --env tests/env-UT-local-docker --env tests/env-ST-local-docker --env tests/env-IT-local-docker --env tests/env-AT-local-docker --env tests/env-QT-local-docker -q -rs --cov=src --cov-report=term-missing`
  - Result: `TOTAL 1446 0 100%`, `123 passed, 2 warnings` (`/tmp/w14b03_index_cov.log`)

## Runtime Evidence
- Running container: `index-retriever-all`
- Runtime image id: `sha256:9cc4f10fc4802cc6bd387a0d058cb629180ed6c391718298385bdb618671bd29` (`/tmp/w14b03_index_runtime_image.log`)

## Final Verdict
`COMPLETE VERIFIED`
