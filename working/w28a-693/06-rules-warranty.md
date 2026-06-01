# W28A-693 RULES Warranty

HAVE_ALL_REQUIREMENTS_BEEN_MET: YES

Basis: raw local-code and Docker Playwright artefacts under `working/w28a-693/` prove Sections A-G using the corrected source-backed path. No SQLite job-status mutation is present in the spec or source path.

## Source-backed lifecycle proof

- Local Section A: `working/w28a-693/local-code/section-a-seed-proof.json`
- Docker Section A: `working/w28a-693/docker/section-a-seed-proof.json`
- Tool path: `IndexService.create_w28a_693_lifecycle_evidence_job`
- `source_backed`: true in both raw Section A files
- `post_hoc_database_mutation`: false in both raw Section A files
- `sqlite_update_used`: false in both raw Section A files

## Test proof

- Local-code JUnit: {'tests': '1', 'failures': '0', 'errors': '0', 'skipped': '0', 'time': '235.32685'}
- Docker JUnit: {'tests': '1', 'failures': '0', 'errors': '0', 'skipped': '0', 'time': '42.295545'}
- Local Playwright log: `working/w28a-693/local-code/playwright.log` => `1 passed (3.9m)`
- Docker Playwright log: `working/w28a-693/docker/playwright.log` => `1 passed (42.3s)`
- Trace proof: `working/w28a-693/playwright-trace-proof.log`
- Evidence matrix: `working/w28a-693/evidence-matrix-summary.log`

## Grep proof

- No SQLite/manual job status mutation: `working/w28a-693/no-sqlite-status-mutation-grep.txt` => `NO_MATCHES`
- PC17 no `.or(`: `working/w28a-693/pc17-no-or-grep.txt` => `NO_MATCHES`
- §1.4 bespoke job class grep: `working/w28a-693/bespoke-job-class-grep.txt`

## Local Docker proof

- Build log: `working/w28a-693/docker-build-script-sendback.log`
- Image proof: `working/w28a-693/docker-image-proof.log`
- Readiness proof: `working/w28a-693/docker-final-ready.log` => `ready: true`
- Cleanup proof: `working/w28a-693/docker-no-leftover-containers.log` => `NO_W28A_693_CONTAINERS`

## Git proof snapshot at warranty generation

Server repo path: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`

Command: `git log -1 --oneline`

```text
9d3106c fix: add W28A-693 source-backed lifecycle jobs
```

Command: `git status --short`

```text
M working/w28a-693/bespoke-job-class-grep.txt
 M working/w28a-693/close-gate.md
 M working/w28a-693/docker-build-script-sendback.log
 M working/w28a-693/docker-final-ready.log
 M working/w28a-693/docker-image-proof.log
 M working/w28a-693/docker-no-leftover-containers.log
 M working/w28a-693/docker-run-container-id.log
 M working/w28a-693/docker-stop-after-pass.log
 D working/w28a-693/docker/html-report/data/4da1f8a56828f9901725ebbfa890567c1cfbcfab.zip
 M working/w28a-693/docker/html-report/index.html
 M working/w28a-693/docker/junit.xml
 M working/w28a-693/docker/playwright.log
 M working/w28a-693/docker/section-a-seed-proof.json
 M working/w28a-693/docker/section-c-badge-proof.json
 M working/w28a-693/docker/section-d-detail-proof.json
 M working/w28a-693/docker/section-e-rbac-proof.json
 M working/w28a-693/docker/section-f-filter-bulk-proof.json
 M working/w28a-693/docker/section-g-cross-page-proof.json
 M working/w28a-693/evidence-matrix-summary.log
 D working/w28a-693/local-code/html-report/data/91e3ce8a02d58eadeeb48b991a601c3c3d29ed9b.zip
 M working/w28a-693/local-code/html-report/index.html
 M working/w28a-693/local-code/junit.xml
 M working/w28a-693/local-code/playwright.log
 M working/w28a-693/local-code/section-a-seed-proof.json
 M working/w28a-693/local-code/section-c-badge-proof.json
 M working/w28a-693/local-code/section-d-detail-proof.json
 M working/w28a-693/local-code/section-e-rbac-proof.json
 M working/w28a-693/local-code/section-f-filter-bulk-proof.json
 M working/w28a-693/local-code/section-g-cross-page-proof.json
 M working/w28a-693/pc17-no-or-grep.txt
 M working/w28a-693/playwright-trace-proof.log
 M working/w28a-693/preprod-touch-audit.md
 M working/w28a-693/py-compile.log
 M working/w28a-693/ui-typecheck.log
```

Command: `git ls-remote --heads origin main`

```text
66669906dc997d0500ea9da706f426de743017af	refs/heads/main
```

UI repo path: `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo`

Command: `git log -1 --oneline`

```text
16da675 fix(index-retriever): source-backed W28A-693 conformance evidence
```

Command: `git status --short -- apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text

```

Command: `git ls-remote --heads origin main`

```text
16da675d6aa9e05cb334d5d92ac674abf715f6b3	refs/heads/main
```

## Warranty

I verified every required W28A-693 Section A-G row against tracked raw artefacts. I did not use SQLite UPDATE/manual DB mutation to manufacture lifecycle states. The return is ready only after final server evidence commit and push update the git proof.
