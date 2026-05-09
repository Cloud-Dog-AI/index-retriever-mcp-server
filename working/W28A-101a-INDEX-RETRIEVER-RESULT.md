# W28A-101a Index Retriever Python 3.12 Rerun Result

Date: 2026-05-09
Repository: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`
Branch: `main`
Baseline commit: `e25cefc` (`W28A-95a-R1 fix VDB matrix hygiene`)
Instruction: `cloud-dog-ai-platform-standards/working/instructions/W28A-101a-index-retriever-PYTHON-312-RERUN-2026-05-08.md`

## Contract Readback

Scope was the formal Python 3.12.13 service-wave rerun after accepted W28A-95a-R1 VDB breadth. I did not invent local VDB/database services and did not weaken or replace the accepted W28A-95a-R1 breadth evidence. Runtime and tests used `.venv/bin/python` on Python 3.12.13, provided Vault/platform contracts, and repo-provided control/build scripts.

Accepted W28A-95a-R1 breadth evidence retained:

- `working/w28a-95a-r1-vault-resolution.log`: `env-VDB-{chroma,qdrant,opensearch,pgvector,weaviate,infinity}: resolved_vdb_values=pass`, `literal_vault_placeholders=pass`.
- `working/w28a-95a-r1-vdb-env-contract-summary.log`: all six VDB env files map to platform/Vault-backed endpoints.
- `working/w28a-95a-r1-env-VDB-{chroma,qdrant,opensearch,pgvector,weaviate,infinity}.log`: per-backend final matrix evidence from the accepted W28A-95a-R1 run.

## Python 3.12 Evidence

| Gate | Result | Log |
| --- | --- | --- |
| PS-100 runtime guard | PASS: Python 3.12.13, `runtime_guard=pass`, `asyncio_cross_thread=pass` | `working/w28a-101-ps100-python-runtime-guard.log` |
| Unit tests | PASS: 157 passed, 0 failed, 0 errors | `working/w28a-101-ut.log` |
| System tests | PASS: 25 passed, 0 failed, 0 errors | `working/w28a-101-st.log` |
| Integration tests | PASS: 46 passed, 0 failed, 0 errors | `working/w28a-101-it.log` |
| Application tests | PASS: 24 passed, 0 failed, 0 errors | `working/w28a-101-at.log` |
| Quality tests | PASS: 47 passed, 0 failed, 0 errors | `working/w28a-101-qt.log` |
| Package build | PASS: sdist and wheel built for `index_retriever_mcp_server-0.1.3rc1` | `working/w28a-101-build.log` |
| Docker build | PASS: `cloud-dog/index-retriever-mcp-server:w28a-101a-python312` and registry tag created | `working/w28a-101-docker-build.log` |
| server_control smoke | PASS: `api`, `web`, `mcp`, and `a2a` start/status/HTTP/stop through `server_control.sh --env tests/env-ST` | `working/w28a-101-server-smoke.log` |
| Initial diff check | PASS | `working/w28a-101-diff-check.log` |
| Final diff check | PASS | `working/w28a-101-diff-check-final.log` |
| Stale Python scan | PASS: no active runtime/package/build/test-runner Python 3.10/3.11 references after pruning venv/build/archive/working/vendor paths | `working/w28a-101-stale-python-scan-final.log` |
| Trusted-host scan | REVIEWED: trusted-host usage limited to `Dockerfile` and `docker-build.sh` package-install/build paths | `working/w28a-101-trusted-host-scan-final.log` |
| Skip/xfail grep | REVIEWED: no hidden runtime skips in completed IT/AT/QT results; static conditional backend/parser markers are visible in grep output | `working/w28a-101-skip-xfail-grep.log` |

Notes:

- Full IT and AT completed with zero skips reported in pytest summaries.
- Pytest emitted cleanup warnings for old `/tmp/pytest-of-gary/garbage-*` WebDAV snapshot directories after some runs; these were post-test cleanup warnings and did not affect pass/fail results.
- The `server_control` smoke verified process lifecycle and HTTP readiness. API/A2A health returned HTTP 200 with a degraded VDB check in the smoke context; real backend breadth remains covered by the accepted W28A-95a-R1 per-backend logs and the W28A-101 full IT/AT rerun.

## Coverage Classification

| Area | Rerun evidence |
| --- | --- |
| Runtime guard / dependency floor | PS-100 confirms Python 3.12.13 and async/runtime compatibility. |
| API/auth/admin/security/error paths | UT, IT, AT, and QT include API auth, A2A auth matrix, RBAC/admin, security headers, error mapping, audit/config paths, and rule compliance. |
| MCP/A2A | UT, IT, AT, and server smoke cover MCP tool registration/runtime paths, A2A health/auth/events, and process startup for MCP/A2A servers. |
| Storage/database variants | IT/AT include platform database startup/e2e coverage and live service flows; SQLite ST smoke remained repo-provided. |
| VDB breadth | W28A-101 IT includes live contract coverage for Chroma, Qdrant, OpenSearch, PGVector, Weaviate, and Infinity; W28A-95a-R1 accepted per-backend env matrix remains final breadth proof. |
| Ingest/search/retrieve/delete/reindex/retention | UT/ST/IT/AT exercise service CRUD, queueing, ingest, retrieval/search, delete/reindex/retention, source config, and web/API workflows. |
| Parsers/OCR/document handling | IT/AT include parser/provider contract coverage and application document workflows; QT verifies no weakened IT/AT skip policy. |
| Packaging/container/server lifecycle | Package build, Docker build, and `server_control.sh` smoke all passed under the Python 3.12 rerun. |

## Resubmission State

No product code fixes were required during this rerun. Evidence logs and this result report are the intended commit contents.

Required completion state:

- Full IT: 46 passed, 0 failed, 0 errors.
- Full AT: 24 passed, 0 failed, 0 errors.
- QT: 47 passed, 0 failed, 0 errors.
- UT/ST: 157 and 25 passed respectively.
- Package and Docker builds: passed.
- `git diff --check`: passed.
- Services stopped after smoke.
