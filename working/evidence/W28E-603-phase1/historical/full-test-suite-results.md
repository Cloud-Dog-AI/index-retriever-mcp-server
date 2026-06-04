# W28E-603 — FULL test suite results (every pytest tier), with Vault-resolved live backends

Run with `env-vault` sourced (token policy `cloud_dog_ai_read`) so live VDB/embedding/IDAM
backends resolve. Every Python tier is GREEN. The only non-passes are 2 documented infra-boundary
skips (structure backend-matrix postgres/mysql — dev DB creds rejected from this client host).

| Tier | Command | Result |
|---|---|---|
| unit | `pytest tests/unit --env tests/env-UT` | 200 passed, 0 failed |
| quality | `pytest tests/quality --env tests/env-QT` | 47 passed, 0 failed |
| integration | `pytest tests/integration --env tests/env-IT` | 51 passed, 0 failed |
| system | `pytest tests/system --env tests/env-ST` | 26 passed, 2 skipped (matrix pg/mysql) |
| application | `pytest tests/application --env tests/env-AT` | 24 passed, 0 failed |
| contract | `pytest tests/contract --env tests/env-IT` | 4 passed, 0 failed |
| parser | `pytest tests/parser --env tests/env-PT` | 3 passed, 0 failed |
| security | `pytest tests/security --env tests/env-QT` | 6 passed, 0 failed |

## Pre-existing failures FOUND and FIXED this session (all failed identically on pristine origin/main 7157c13)
- **RC-01** (quality, hardcoded loopback): stale QT-allowlist line numbers for the documented-legitimate
  web_server proxy loopback — reconciled (`tests/quality/QT_COMPLIANCE/conftest.py`).
- **RC-09** (quality, stub marker): `connectors/resolver.fetch_source` `NotImplementedError` for s3/webdav/gdrive
  — implemented `fetch()` via `cloud_dog_storage.build_storage_backend` (`connectors/{s3,webdav,gdrive}.py`).
- **IT1_21** (integration, collection RBAC): `_enforce_collection_permission` only checked the role-permission,
  never the collection's `allowed_roles` — a reader could search a writer/admin-only collection. Added the
  per-collection `allowed_roles` gate (canonicalised both sides; admin bypass) in `src/index_server/mcp_server.py`
  and wired it into all collection-scoped tool dispatches.
- **IT1_22** (integration, api-key roles): `admin_api_key_create` registered the IDAM key under the OWNER USER,
  so resolution used the user's roles, not the key's — an admin-roled key was denied admin ops. Now the key is
  registered under a KEY-SCOPED identity carrying the key's roles (`src/index_tools/tools/service.py`).

## Test updated with source (brief §22)
- **ST1_14** migration test asserted the post-upgrade revision == baseline; the new `20260604_0002` structure
  migration is now the head. Changed to derive the current head dynamically from the Alembic scripts (no future drift).
