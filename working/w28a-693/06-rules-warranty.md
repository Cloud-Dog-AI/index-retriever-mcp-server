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

## Git proof snapshot after source/evidence push

Server repo path: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`

Command: `git log -1 --oneline`

```text
a579c0f evidence: W28A-693 source-backed jobs conformance
```

Command: `git rev-parse HEAD`

```text
a579c0fe4b10d4937259e14873838970f90c97d8
```

Command: `git status --short`

```text

```

Command: `git ls-remote --heads origin main`

```text
a579c0fe4b10d4937259e14873838970f90c97d8	refs/heads/main
```

UI repo path: `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo`

Command: `git log -1 --oneline`

```text
16da675 fix(index-retriever): source-backed W28A-693 conformance evidence
```

Command: `git rev-parse HEAD`

```text
16da675d6aa9e05cb334d5d92ac674abf715f6b3
```

Command: `git status --short -- apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text

```

Command: `git ls-remote --heads origin main`

```text
16da675d6aa9e05cb334d5d92ac674abf715f6b3	refs/heads/main
```

## Warranty

I verified every required W28A-693 Section A-G row against tracked raw artefacts. I did not use SQLite UPDATE/manual DB mutation to manufacture lifecycle states. The source/evidence commit is pushed and the post-push git proof is recorded in `working/w28a-693/git-proof-post-push.md`.
