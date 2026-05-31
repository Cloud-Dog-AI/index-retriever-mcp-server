# W28A-693 Rules Warranty

HAVE_ALL_REQUIREMENTS_BEEN_MET: YES

I warrant that W28A-693 has been completed against the requested quality bar for Index Retriever local code and local Docker. Sections A-G were rerun against current local code and against the local Docker image, and the required raw evidence is under `working/w28a-693/`.

## Implementation Delivered

- Server job RBAC now enforces owner-only non-admin `job_list`, `job_get`, `job_wait`, `job_cancel`, and `job_retry`, while admin retains cross-actor access.
- Browser tool proxying forwards browser `Authorization` and `X-API-Key` headers instead of replacing them with the configured service key.
- Async job execution is controllable through config (`CLOUD_DOG__INDEX__QUEUE__ASYNC_JOB_EXECUTION` / `CLOUD_DOG__QUEUE__ASYNC_JOB_EXECUTION`) without adding direct env reads outside the config helper path.
- `ingest_text` forwards idempotency keys and metadata into the durable job service so current-run failed/dead-lettered and retry-wait states are reproducible.
- Index Retriever WebUI uses same-origin A2A proxy paths for Service Health, A2A Console, and API Docs, with local Vite preview proxying `/a2a` to the local A2A service.
- The W28A-693 Playwright spec executes the full sendback matrix: Sections A-G, current-run state coverage, PS-76 lifecycle badges, details controls/tabs/Escape close, all 8 RBAC rows, exact search, status/type/actor/date filters, every-column sort, page sizes 10/25/50/100, bulk cancel/retry/delete, and strict console/network capture.
- Docker build is reproducible from the server worktree with final UI bundle synced into `ui/dist`.

## Validation Results

- Python compile: PASS. Evidence: `working/w28a-693/py-compile.log`.
- Integration test `IT1_20` job management: PASS, `1 passed in 44.12s`. Evidence: `working/w28a-693/pytest-it1-20-job-management.log`.
- UI typecheck: PASS. Evidence: `working/w28a-693/ui-typecheck.log`.
- UI build: PASS. Evidence: `working/w28a-693/ui-build.log`.
- Local-code Playwright: PASS, `1 passed (5.6m)`. Evidence: `working/w28a-693/local-code/playwright.log`, `working/w28a-693/local-code/junit.xml`, `working/w28a-693/local-code/html-report/index.html`, and trace bundle under `working/w28a-693/local-code/html-report/data/`.
- Local-Docker Playwright: PASS, `1 passed (2.4m)`. Evidence: `working/w28a-693/docker/playwright.log`, `working/w28a-693/docker/junit.xml`, `working/w28a-693/docker/html-report/index.html`, and trace bundle under `working/w28a-693/docker/html-report/data/`.
- Docker image proof: `cloud-dog/index-retriever-mcp-server:w28a-693-sendback`, image id `sha256:e4e35c6e4090d87ebdf102fd37371b0fcd8638b537d4fa6ef7124abcebddaee8`, created `2026-06-01T00:23:06.505367254+01:00`. Evidence: `working/w28a-693/docker-image-proof.log`.
- Docker readiness proof: API, tools, auth, WebUI proxy, MCP, and A2A endpoints returned expected 200 responses. Evidence: `working/w28a-693/docker-final-ready.log`.
- Docker cleanup proof: `NO_W28A_693_CONTAINERS`. Evidence: `working/w28a-693/docker-no-leftover-containers.log`.
- Docker build hygiene proof: `NO_PIP_CONF_OR_CUSTOM_CA_LEFTOVER`. Evidence: `working/w28a-693/pip-conf-leftover-proof.txt`.

## Section Evidence

- Section A current-run coverage: local and Docker `section-a-seed-proof.json` contain `succeeded`, `dead_lettered`, `retry_wait`, `cancelled`, and `running`.
- Section B DataTable: local and Docker `section-b-table-proof.json` capture all 12 mandatory columns and total-record pagination text.
- Section C PS-76 lifecycle badge colours: local and Docker `section-c-badge-proof.json` capture green success, red failed/dead-lettered, yellow retry_wait, secondary running, and secondary strikethrough cancelled.
- Section D details: local and Docker `section-d-detail-proof.json` capture Copy Job ID, Retry, Cancel, Delete, all seven tabs, and Escape close.
- Section E RBAC: local and Docker `section-e-rbac-proof.json` capture all 8 RBAC rows with real admin, non-admin, and cross-actor outcomes.
- Section F filters/sorts/pagination/bulk actions: local and Docker `section-f-filter-bulk-proof.json` captures exact search, status/type/actor/date filters, every mandatory column sorted ascending/descending, page sizes 10/25/50/100 selected, and bulk cancel/retry/delete confirmation paths.
- Section G strict cross-page smoke: local and Docker `section-g-cross-page-proof.json` captures 12 routes with zero console errors and zero network failures after expected RBAC failures were excluded before Section G.
- Matrix summary: `working/w28a-693/evidence-matrix-summary.log`.
- Trace proof: `working/w28a-693/playwright-trace-proof.log` lists `test.trace`, `1-trace.trace`, and network traces inside both HTML report data bundles.

## Hard Guard Warranty

- Section 1.4 bespoke grep: clean. `working/w28a-693/bespoke-job-class-grep.txt` records `NO_MATCHES`.
- PC17: clean. `working/w28a-693/pc17-no-or-grep.txt` records `NO_MATCHES`.
- PC27: foreground-only. Docker and Playwright runs were executed in foreground terminal sessions; no detached background process remains.
- PC29: required artefacts are under `working/w28a-693/`.
- PC32: clean. `working/w28a-693/docker-no-leftover-containers.log` records `NO_W28A_693_CONTAINERS`.
- PREPROD_TOUCH_AUDIT: clean. See `working/w28a-693/preprod-touch-audit.md`.
- Vault writes: none.
- Secret leak: none observed in committed evidence; Docker build logs redact private PyPI credentials.
- Weakened assertions: none; no `.or()` fallback accepting failure states.

## Git Proof

### Server Repo

Path: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`

Command: `git log -1 --oneline`

```text
e08a6ba fix: complete W28A-693 jobs webui conformance
```

Command: `git status --short`

```text
```

Command: `git ls-remote --heads origin main`

```text
e08a6babab350f7b956ef59e171e4e47f7e4f598	refs/heads/main
```

Command: `git ls-files Dockerfile docker-build.sh src/index_server/mcp_server.py src/index_server/web_server.py src/index_tools/tools/service.py tests/integration/IT1_20/test_it1_20_job_management_tools.py ui/dist/index.html ui/dist/assets/index-DQOfiJ_O.js`

```text
Dockerfile
docker-build.sh
src/index_server/mcp_server.py
src/index_server/web_server.py
src/index_tools/tools/service.py
tests/integration/IT1_20/test_it1_20_job_management_tools.py
ui/dist/assets/index-DQOfiJ_O.js
ui/dist/index.html
```

Command: `git ls-files working/w28a-693`

```text
working/w28a-693/00-preflight.md
working/w28a-693/06-rules-warranty.md
working/w28a-693/bespoke-job-class-grep.txt
working/w28a-693/close-gate.md
working/w28a-693/docker-build-script-after-a2a-fix.log
working/w28a-693/docker-build-script-sendback.log
working/w28a-693/docker-final-ready.log
working/w28a-693/docker-image-proof.log
working/w28a-693/docker-no-leftover-containers.log
working/w28a-693/docker-run-container-id.log
working/w28a-693/docker-stop-after-pass.log
working/w28a-693/docker/html-report/data/4da1f8a56828f9901725ebbfa890567c1cfbcfab.zip
working/w28a-693/docker/html-report/index.html
working/w28a-693/docker/html-report/trace/assets/codeMirrorModule-a5XoALAZ.js
working/w28a-693/docker/html-report/trace/assets/defaultSettingsView-CJSZINFr.js
working/w28a-693/docker/html-report/trace/codeMirrorModule.DYBRYzYX.css
working/w28a-693/docker/html-report/trace/codicon.DCmgc-ay.ttf
working/w28a-693/docker/html-report/trace/defaultSettingsView.7ch9cixO.css
working/w28a-693/docker/html-report/trace/index.BDwrLSGN.js
working/w28a-693/docker/html-report/trace/index.BVu7tZDe.css
working/w28a-693/docker/html-report/trace/index.html
working/w28a-693/docker/html-report/trace/manifest.webmanifest
working/w28a-693/docker/html-report/trace/playwright-logo.svg
working/w28a-693/docker/html-report/trace/snapshot.html
working/w28a-693/docker/html-report/trace/sw.bundle.js
working/w28a-693/docker/html-report/trace/uiMode.Btcz36p_.css
working/w28a-693/docker/html-report/trace/uiMode.CQJ9SCIQ.js
working/w28a-693/docker/html-report/trace/uiMode.html
working/w28a-693/docker/html-report/trace/xtermModule.DYP7pi_n.css
working/w28a-693/docker/junit.xml
working/w28a-693/docker/playwright.log
working/w28a-693/docker/section-a-seed-proof.json
working/w28a-693/docker/section-b-table-proof.json
working/w28a-693/docker/section-c-badge-proof.json
working/w28a-693/docker/section-d-detail-proof.json
working/w28a-693/docker/section-e-rbac-proof.json
working/w28a-693/docker/section-f-filter-bulk-proof.json
working/w28a-693/docker/section-g-cross-page-proof.json
working/w28a-693/evidence-matrix-summary.log
working/w28a-693/git-proof-post-push.md
working/w28a-693/local-code/html-report/data/91e3ce8a02d58eadeeb48b991a601c3c3d29ed9b.zip
working/w28a-693/local-code/html-report/index.html
working/w28a-693/local-code/html-report/trace/assets/codeMirrorModule-a5XoALAZ.js
working/w28a-693/local-code/html-report/trace/assets/defaultSettingsView-CJSZINFr.js
working/w28a-693/local-code/html-report/trace/codeMirrorModule.DYBRYzYX.css
working/w28a-693/local-code/html-report/trace/codicon.DCmgc-ay.ttf
working/w28a-693/local-code/html-report/trace/defaultSettingsView.7ch9cixO.css
working/w28a-693/local-code/html-report/trace/index.BDwrLSGN.js
working/w28a-693/local-code/html-report/trace/index.BVu7tZDe.css
working/w28a-693/local-code/html-report/trace/index.html
working/w28a-693/local-code/html-report/trace/manifest.webmanifest
working/w28a-693/local-code/html-report/trace/playwright-logo.svg
working/w28a-693/local-code/html-report/trace/snapshot.html
working/w28a-693/local-code/html-report/trace/sw.bundle.js
working/w28a-693/local-code/html-report/trace/uiMode.Btcz36p_.css
working/w28a-693/local-code/html-report/trace/uiMode.CQJ9SCIQ.js
working/w28a-693/local-code/html-report/trace/uiMode.html
working/w28a-693/local-code/html-report/trace/xtermModule.DYP7pi_n.css
working/w28a-693/local-code/junit.xml
working/w28a-693/local-code/playwright.log
working/w28a-693/local-code/section-a-seed-proof.json
working/w28a-693/local-code/section-b-table-proof.json
working/w28a-693/local-code/section-c-badge-proof.json
working/w28a-693/local-code/section-d-detail-proof.json
working/w28a-693/local-code/section-e-rbac-proof.json
working/w28a-693/local-code/section-f-filter-bulk-proof.json
working/w28a-693/local-code/section-g-cross-page-proof.json
working/w28a-693/pc17-no-or-grep.txt
working/w28a-693/pip-conf-leftover-proof.txt
working/w28a-693/playwright-trace-proof.log
working/w28a-693/preprod-touch-audit.md
working/w28a-693/py-compile.log
working/w28a-693/pytest-it1-20-job-management.log
working/w28a-693/ui-build.log
working/w28a-693/ui-dist-sync-proof.log
working/w28a-693/ui-typecheck.log
```

### UI Repo

Path: `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo`

Command: `git log -1 --oneline`

```text
4ebff4c fix(index-retriever): complete W28A-693 jobs conformance
```

Command: `git status --short -- apps/index-retriever/playwright.config.ts apps/index-retriever/vite.config.ts apps/index-retriever/src/routes/App.tsx apps/index-retriever/src/views/A2aConsolePage.tsx apps/index-retriever/src/views/ApiDocsPage.tsx apps/index-retriever/src/views/JobsPageView.tsx apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text
```

Command: `git ls-remote --heads origin main`

```text
4ebff4c13fa6124c843a0be7eb3eef0d6223100b	refs/heads/main
```

Command: `git ls-files apps/index-retriever/playwright.config.ts apps/index-retriever/vite.config.ts apps/index-retriever/src/routes/App.tsx apps/index-retriever/src/views/A2aConsolePage.tsx apps/index-retriever/src/views/ApiDocsPage.tsx apps/index-retriever/src/views/JobsPageView.tsx apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text
apps/index-retriever/playwright.config.ts
apps/index-retriever/src/routes/App.tsx
apps/index-retriever/src/views/A2aConsolePage.tsx
apps/index-retriever/src/views/ApiDocsPage.tsx
apps/index-retriever/src/views/JobsPageView.tsx
apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts
apps/index-retriever/vite.config.ts
```
