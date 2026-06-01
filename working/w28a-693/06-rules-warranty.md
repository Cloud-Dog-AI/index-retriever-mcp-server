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

## Final Proof Anchor

The previous R4 blocker was a self-referential hash loop: a proof commit recorded
the prior commit, then the proof commit became the final returned HEAD. This
warranty now avoids that false claim.

Final git proof is anchored after the final proof-anchor commit is pushed in
annotated tag `W28A-693-R4-FINAL-PROOF`. The tag message records the immutable
post-push raw outputs for:

- `git rev-parse HEAD`
- `git ls-remote origin refs/heads/main`
- `git status --short`
- `git ls-files working/w28a-693/ | wc -l`
- local-code and Docker JUnit summaries
- local-code and Docker `.last-run.json` statuses
- trace zip counts
- UI `git ls-remote origin refs/heads/main`
- UI scoped `git status --short -- apps/index-retriever`

## Warranty

I verified every required W28A-693 Section A-G row against tracked raw artefacts. I did not use SQLite UPDATE/manual DB mutation to manufacture lifecycle states. The committed proof files name the final proof anchor without asserting a stale hash; the immutable post-push raw git proof is the annotated tag `W28A-693-R4-FINAL-PROOF`.
