# W28A-693 Rules Warranty

HAVE_ALL_REQUIREMENTS_BEEN_MET: YES

I warrant that W28A-693 has been completed against the requested quality bar for index-retriever local code and local Docker. All sections A-G have real Playwright DOM evidence, traces, HTML report output, and JUnit XML. No screenshot-only or curl-only evidence is used as proof of completion.

## Implementation Delivered

- `JobsPageView.tsx` now implements PS-76 v2 job table behaviour: mandatory columns in order, status lifecycle badges, exact Job ID search, status/type/actor/date filters, sorting, pagination, column toggle, multi-select, bulk cancel/retry/delete, and sub-dialog detail view with all seven tabs.
- App state now carries authenticated `userId` and `displayName` so RBAC filtering can distinguish admin and non-admin user paths.
- `job_delete` is implemented in the service/registry/MCP server and is admin-only.
- `list_collections` alias is registered for MCP Console seeding.
- The deployed WebUI bundle in `ui/dist` was rebuilt from the monorepo source.
- A2A console/API docs agent-card loading now respects the configured A2A base URL, preventing cross-page smoke 404 regressions.

## Validation Results

- UI typecheck: PASS. Evidence: `working/w28a-693/ui-typecheck.log`.
- UI build: PASS. Evidence: `working/w28a-693/ui-build.log`.
- Python compile: PASS. Evidence: `working/w28a-693/py-compile.log` (command exited 0 with no compiler output).
- Integration test `IT1_20` job management: PASS, `1 passed in 25.72s`. Evidence: `working/w28a-693/pytest-it1-20-job-management.log`.
- Local-code Playwright: PASS, `1 passed (1.5m)`. Evidence: `working/w28a-693/local-code/junit.xml`, `working/w28a-693/local-code/html-report/index.html`, trace zip in `working/w28a-693/local-code/html-report/data/`.
- Local-Docker Playwright: PASS, `1 passed (56.7s)`. Evidence: `working/w28a-693/docker/junit.xml`, `working/w28a-693/docker/html-report/index.html`, trace zip in `working/w28a-693/docker/html-report/data/`.
- Docker image proof: `cloud-dog/index-retriever-mcp-server:w28a-693` image id `244b30fb59ad`. Evidence: `working/w28a-693/docker-image-proof.log`.
- Docker readiness proof: health, tools API, tools Web, auth, Web, and A2A agent card returned 200. Evidence: `working/w28a-693/docker-final-ready.log`.
- Docker cleanup proof: `NO_W28A_693_CONTAINERS`. Evidence: `working/w28a-693/docker-no-leftover-containers.log`.

## Section Evidence

- Section A seed jobs: local and Docker `section-a-seed-proof.json`; both contain real MCP Console tool calls and 10 seeded job IDs.
- Section A local observed statuses: `succeeded=709`, `dead_lettered=49`, `retry_wait=2`, `cancelled=61`, `running=2`.
- Section A Docker observed statuses: `succeeded=709`, `dead_lettered=49`, `retry_wait=2`, `cancelled=61`, `running=1`.
- Section B DataTable: `section-b-table-proof.json`; 12 mandatory columns and total records visible.
- Section C lifecycle badges: `section-c-badge-proof.json`; green success, red failed-family, secondary cancelled with strikethrough captured.
- Section D detail dialog: `section-d-detail-proof.json`; seven tabs and Escape close captured.
- Section E RBAC: `section-e-rbac-proof.json`; actor filter hidden for non-admin, delete hidden for non-admin, direct other-job 403 checked, and writer user path captured.
- Section F search/filter/sort/bulk/pagination: `section-f-filter-bulk-proof.json`; exact Job ID search, `Total Records / Page X of Y`, and three bulk actions captured.
- Section G cross-page smoke: `section-g-cross-page-proof.json`; 12 routes navigated with zero added console errors and zero added network failures.

## Hard Guard Warranty

- Section 1.4 bespoke grep: clean. Raw command output in `working/w28a-693/bespoke-job-class-grep.txt` has zero `class.*Job\b` matches under `src/`.
- PC17: clean. `working/w28a-693/pc17-no-or-grep.txt` has zero `.or(` matches in the W28A-693 page/spec.
- PC27: foreground-only. All test and Docker runs were executed in foreground terminal sessions; no detached background process is required for this return.
- PC29: all artefacts are under `working/w28a-693/`.
- PC32: clean. No `w28a-693` container remains after the pass.
- PREPROD_TOUCH_AUDIT: clean. See `working/w28a-693/preprod-touch-audit.md`.
- Vault writes: none.
- Secret leak: none observed in committed evidence; build logs redact private PyPI credentials.
- Weakened assertions: none; no `.or()` fallback accepting failure states.

## Git Proof

Captured after pushing the substantive W28A-693 commits.

### Server Repo

Command: `git log -1 --oneline`

```text
da38e59 fix: complete W28A-693 jobs webui conformance
```

Command: `git status --short`

```text

```

Command: `git ls-remote origin main`

```text
da38e59d210e03c3d006f29b22bd0e3c78353d0f	refs/heads/main
```

Command: `git ls-files src/index_server/mcp_server.py src/index_tools/queue/engine.py src/index_tools/tools/registry.py src/index_tools/tools/service.py tests/integration/IT1_20/test_it1_20_job_management_tools.py ui/dist/index.html ui/dist/assets/index-0txyp-vA.css ui/dist/assets/index-CWSGLkc_.js working/w28a-693/06-rules-warranty.md working/w28a-693/local-code/junit.xml working/w28a-693/docker/junit.xml working/w28a-693/local-code/html-report/data/22aec44bae41a499944d31cdf92982bfcdabb365.zip working/w28a-693/docker/html-report/data/7651387b9d2d8d6add80e473de0e6dd40d71c67f.zip`

```text
src/index_server/mcp_server.py
src/index_tools/queue/engine.py
src/index_tools/tools/registry.py
src/index_tools/tools/service.py
tests/integration/IT1_20/test_it1_20_job_management_tools.py
ui/dist/assets/index-0txyp-vA.css
ui/dist/assets/index-CWSGLkc_.js
ui/dist/index.html
working/w28a-693/06-rules-warranty.md
working/w28a-693/docker/html-report/data/7651387b9d2d8d6add80e473de0e6dd40d71c67f.zip
working/w28a-693/docker/junit.xml
working/w28a-693/local-code/html-report/data/22aec44bae41a499944d31cdf92982bfcdabb365.zip
working/w28a-693/local-code/junit.xml
```

### UI Repo

Command: `git log -1 --oneline`

```text
3f9cec3 fix(index-retriever): align jobs webui conformance
```

Command: `git status --short -- apps/index-retriever/src/state/AppState.tsx apps/index-retriever/src/views/A2aConsolePage.tsx apps/index-retriever/src/views/ApiDocsPage.tsx apps/index-retriever/src/views/JobsPageView.tsx apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text

```

Command: `git ls-remote origin main`

```text
3f9cec3b1829f6e1b124349f58a7b953aa2f9cfa	refs/heads/main
```

Command: `git ls-files apps/index-retriever/src/state/AppState.tsx apps/index-retriever/src/views/A2aConsolePage.tsx apps/index-retriever/src/views/ApiDocsPage.tsx apps/index-retriever/src/views/JobsPageView.tsx apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text
apps/index-retriever/src/state/AppState.tsx
apps/index-retriever/src/views/A2aConsolePage.tsx
apps/index-retriever/src/views/ApiDocsPage.tsx
apps/index-retriever/src/views/JobsPageView.tsx
apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts
```
