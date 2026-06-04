# W28E-603 — pre-existing index-retriever failures fixed under this lane

Four failures present on pristine `origin/main` 7157c13 (proven failing there) were fixed. All four are
real index-retriever code, and the capability exists in sibling services.

## RC-01 — hardcoded loopback (quality tier)
The QT allowlist pinned `web_server.py`'s documented-legitimate internal-proxy loopback to stale line
numbers; the loopback had drifted +2. Reconciled the allowlist line numbers in
`tests/quality/QT_COMPLIANCE/conftest.py`. Raw: `pytest tests/quality::test_rc01_no_hardcoded_urls_or_loopback` PASS.

## RC-09 — connector fetch stub (quality tier)
`connectors/resolver.fetch_source` raised a stub error for s3/webdav/gdrive on the live ingest_reference path.
Implemented `fetch()` in `connectors/{s3,webdav,gdrive}.py` delegating to the platform
`cloud_dog_storage.build_storage_backend` with `cloud_dog_config`-resolved credentials. Raw:
`pytest tests/unit/UT1_46` PASS (3 tests, incl positive delegation test).

## IT1_21 — collection-level RBAC (integration tier)
`_enforce_collection_permission` checked only the role-permission, never the collection's `allowed_roles`,
so a reader could search a writer/admin-only collection. Added the per-collection `allowed_roles` gate
(canonicalised both sides; admin bypass) in `src/index_server/mcp_server.py`, wired into all 10
collection-scoped tool dispatches. Raw: `pytest tests/integration/IT1_21` PASS.

## IT1_22 — api-key role resolution (integration tier)
`admin_api_key_create` registered the IDAM key under the owner user, so api-key auth resolved the user's
roles, not the key's; an admin-roled key was denied admin operations. Now registered under a key-scoped
identity carrying the key's own roles in `src/index_tools/tools/service.py`. Raw:
`pytest tests/integration/IT1_22` PASS.

## ST1_14 — migration head (test updated with source, design brief §22)
The migration test asserted the post-upgrade revision equals the baseline; the new `20260604_0002`
structure migration is now the Alembic head. Updated to derive the head dynamically from the Alembic
scripts (`tests/system/ST1_14`). Raw: `pytest tests/system/ST1_14` PASS.

## Backend-matrix postgres/mysql legs (skipped — infrastructure boundary)
The structure backend-matrix attempts the postgresql/mysql legs against the real dev databases. With the
`env-vault` token, Vault resolves the dev credentials and the connection reaches `db2:5432` and `db1:3306`,
but the servers reject the dev credentials from this client host (raw: `password authentication failed` /
`Access denied ...@10.26.2.1`). This is an infrastructure credential boundary; the persistence layer is
dialect-agnostic and the sqlite leg passes. DB authentication was not bypassed.
