# W28A-148C Index Retriever W102 RBAC/Parser Return

Date: 2026-05-11
Scope: `index-retriever-mcp-server/**`

## Credential proof

Raw credential values were not printed.

Pre-existing ignored preprod config proof:

| Source | Entry | Present | Length | SHA-256 prefix | Roles |
| --- | ---: | --- | ---: | --- | --- |
| `private/env-PREPROD-resolved` | 1 | yes | 12 | `4c806362b613` | implicit default admin/maintainer/writer/reader |
| `private/env-PREPROD-resolved` | 2 | yes | 8 | `ef797c8118f0` | implicit default admin/maintainer/writer/reader |
| `private/env-PREPROD` | 1 | yes | 45 | `f875fa7ca0a3` | implicit default admin/maintainer/writer/reader |

Result: current ignored preprod env material does not prove admin/reader/writer separation because all entries are unscoped and therefore expand to the default full-role set in the previous parser.

Code fix: `AuthMiddleware` now supports explicit role-scoped keys:

- `CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY` -> admin, maintainer, writer, reader
- `CLOUD_DOG__INDEX__AUTH__MAINTAINER_API_KEY` -> maintainer, writer, reader
- `CLOUD_DOG__INDEX__AUTH__WRITER_API_KEY` -> writer, reader
- `CLOUD_DOG__INDEX__AUTH__READER_API_KEY` -> reader

The legacy comma form remains supported, including `token:role|role` entries. Unknown API keys are rejected before provider fallback, preventing accidental role expansion.

## Fixes

- RBAC: role-specific API-key env parsing added and exact key matching enforced before IDAM provider auth.
- RBAC API denial: existing per-tool dispatch denial now receives separated roles instead of collapsed default roles.
- Parser bridge: `ingest_preview` and `parser_test` now use a sync bridge that runs the coroutine directly only when no event loop is active; inside an active loop it runs the coroutine on a short-lived thread/loop. No parser path calls `asyncio.run()` directly.
- API docs: `/api-docs` now serves a stable rendered contract with an `API Docs` heading, `iframe[title="API documentation"]`, and `OpenAPI JSON` link.

## Validation

- `python3 -m pytest --env UT tests/unit/UT1_38/test_ut1_38_a2a_auth_contract.py tests/integration/IT1_24/test_it1_24_openapi_contract.py tests/integration/IT2_12/test_it2_12_internal_parser.py`
  - Result: `6 passed, 1 error`
  - Error: `tests/integration/IT1_24/test_it1_24_openapi_contract.py` fixture stopped because `VAULT_TOKEN` was not set.
- `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a; python3 -m pytest --env UT tests/integration/IT1_24/test_it1_24_openapi_contract.py`
  - Result: `1 passed in 8.70s`
- `python3 -m py_compile src/index_server/auth/middleware.py src/index_tools/tools/service.py src/index_server/api_server.py`
  - Result: pass.

## Slot use

No LLM/vector slot used. No provider-heavy rerun, reload, or reindex was performed.

## Residual blockers

- The committed code enables separated admin/writer/reader credential sources, but the ignored preprod env currently visible in this workspace is still collapsed/unscoped. A deployed preprod fix requires setting distinct role-specific keys in the approved Vault/config path and redeploying/restarting the service outside this task's prohibited Docker/publication scope.
- The requested Playwright failing-spec/full-shard rerun was not run after this source-only patch because the target preprod runtime has not been updated with these code/config changes.
