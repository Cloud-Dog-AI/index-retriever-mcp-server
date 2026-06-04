# W28E-603 — Quality-tier compliance: RC-01 + RC-09 FIXED (not excused)

An earlier pass disclosed RC-01 and RC-09 as "pre-existing" and moved on. That was wrong — they
are index-retriever failures in the target repo and they are now **fixed**. `pytest tests/quality
--env tests/env-QT` → **47 passed, 0 failed**. `pytest tests/unit --env tests/env-UT` → **200 passed, 0 failed**.

## RC-09 — stub/placeholder markers (FIXED: implemented via cloud_dog_storage)
- **Root cause:** `src/index_tools/connectors/resolver.py:fetch_source` raised
  `NotImplementedError("... requires backend credentials")` for `s3`/`webdav`/`gdrive` — a real stub.
  `fetch_source` is on the live `ingest_reference` path (`service.py:2429-2431`), so s3/webdav/gdrive
  references genuinely failed.
- **Fix (RULES §1.4):** implemented `fetch()` in `connectors/s3.py`, `connectors/webdav.py`,
  `connectors/gdrive.py`, each delegating to the **platform** `cloud_dog_storage.build_storage_backend`
  (S3 / WebDAV / Google Drive backends) with credentials resolved via `cloud_dog_config.get_config`
  (env/Vault). `resolver.fetch_source` now delegates to them. When a backend is unconfigured the
  platform raises `ConfigurationError` — a real "needs configuration" error, not a stub.
- **Tests:** `tests/unit/UT1_46` updated — the s3/webdav/gdrive legs now assert `ConfigurationError`
  (was `NotImplementedError`), plus a new positive test
  `test_w28c427r5_s3_fetch_delegates_to_cloud_dog_storage` proves fetch delegates to the storage
  backend and returns its bytes. Connector resolve tests (UT1_10/UT1_11/UT1_42) still pass.

## RC-01 — hardcoded URL/loopback (FIXED: reconciled drifted allowlist)
- **Root cause:** the QT allowlist pinned `web_server.py` loopback to lines `84/85/94/149/150`, but the
  (documented-legitimate) `_normalise_api_host` loopback + the three config-resolved base-URL builders
  had drifted to `86/87/96/151/152` (+2). The loopback is the internal reverse-proxy bridge target and
  was always sanctioned by the allowlist; the line pins were stale (this is why RC-01 had been red).
- **Fix:** updated `tests/quality/QT_COMPLIANCE/conftest.py` allowlist line numbers to the current
  positions. The web_server.py code is correct (config-resolved host:port; wildcard→loopback) and is
  identical across sibling services where this passes.

## Backend matrix vs REAL postgres/mysql — attempted, infra-bounded (honest)
To avoid a hollow skip, I attempted the postgres/mysql legs against the real dev databases:
- Sourced the sanctioned `env-vault` (token policy `cloud_dog_ai_read`), resolved
  `dev.databases.indexretrievermcp_dev_{postgresql,mysql}` from Vault, built sync URLs, installed
  `psycopg`+`PyMySQL` into the test venv.
- **Result:** the connection path works end-to-end — reaches `db2.app.vpc0.cloud-dog.net:5432`
  (postgres) and `db1.app.vpc0.cloud-dog.net:3306` (mysql) — but the servers reject the dev
  credentials from this host:
  - postgres: `FATAL: password authentication failed for user "indexretrievermcp_dev"`
  - mysql: `Access denied for user 'indexretrievermcp_dev'@'10.26.2.1' (using password: YES)`
- **Conclusion:** an infrastructure/credential boundary (dev DB grant/password does not admit this
  client host), NOT a code defect. cloud_dog_db builds the engine and connects correctly. The matrix
  therefore runs the **sqlite** leg locally (PASS) and skips postgres/mysql with an explicit reason;
  the persistence layer is dialect-agnostic (SQLAlchemy/Alembic + generic JSON) and the connection
  mechanism is proven to reach the live servers. I did not attempt to bypass DB auth.

## Net
- New quality failures introduced by this work: **0**.
- Long-standing IR quality failures fixed: **RC-01, RC-09**.
- Test venv change (additive, disclosed): `psycopg[binary]` + `PyMySQL` installed so the matrix can run
  against real postgres/mysql from a host whose grant admits it.
