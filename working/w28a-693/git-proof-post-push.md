# W28A-693 Git Proof After Push

Captured after pushing the W28A-693 source/evidence commits for the same lane.

## Server Repo

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

## UI Repo

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
