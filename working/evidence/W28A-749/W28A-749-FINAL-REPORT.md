# W28A-749 — index-retriever IDAM Thread-b — FINAL REPORT

The b-method (b-3/b-4/b-5/b-7) delivered for index-retriever, with the W28A-741 keystone cascade
(`cloud_dog_idam` 0.5.x resolver/guard) wired and **proven live on the deployed `indexretriever0`** across
the full G1–G8 chain. Source on `origin/main`; image built from it, deployed; live T3 cascade + 4-sentinel
browser smoke green.

## Prime directive readback
I will not lie, fudge, hack, or falsify; 100% real systems; proof for every claim. Every value below is from
a raw artefact in this evidence pack.

## What was delivered
- **b-3** `docs/ROLES-AND-USECASES.md` — 17-row matrix (use-cases verbatim, bolded T3-IR-CASCADE), entities
  DISJOINT finding, roles reconciled to the central catalog.
- **b-5** UI justification — 18/18 SPA routes mapped to use-case+role, 0 orphan, strict API client.
- **b-7** canonical 6-doc set (`REQUIREMENTS/ROLES-AND-USECASES/ARCHITECTURE/API/DATA-MODEL/TESTS`),
  tool-count reconciled to runtime **92**, 9 docs archived.
- **b-4 / cascade wiring** — resource-aware guard consuming `cloud_dog_idam.rbac.grants/membership/
  guard_registry/secret_masking`; `rbac_bindings` table; resource-scoped `admin_rbac_bind/unbind`; live grants
  invalidation. T0/T1/T2 smoke + T3-IR-CASCADE under `tests/smoke/`.
- **G1–G8** full chain — built image (idam 0.5.2), deployed to `indexretriever0`, live cascade proven.

## Platform package compliance
cloud_dog_config / cloud_dog_logging / cloud_dog_api_kit / cloud_dog_idam (0.5.2, cascade) / cloud_dog_db /
cloud_dog_jobs / cloud_dog_llm / cloud_dog_vdb / cloud_dog_storage — USED. §1.4.1 grep: 0 violations in `src/`.

## Evidence Matrix
| Requirement | Raw artefact (path) | Raw value observed | Verification command | Pass |
|---|---|---|---|---|
| GATE 0 reading warrant | `00-reading-proof.md` | 8 files SHA256(12) + 3 rule-ids each | `cat 00-reading-proof.md` | PASS |
| b-3 matrix (verbatim + cascade) | `docs/ROLES-AND-USECASES.md` | 17 rows, bolded T3-IR-CASCADE | `git show origin/main:docs/ROLES-AND-USECASES.md` | PASS |
| b-5 UI (no orphan, parity) | `B5-UI-JUSTIFICATION.md` | 18/18 mapped, 0 orphan | `git show origin/main:docs/ROLES-AND-USECASES.md` | PASS |
| b-7 canonical 6 + tool 92 | `docs/*.md` | 6-set present; FR-16A/§7.7 = 92 | `ls docs/; grep 92 docs/REQUIREMENTS.md` | PASS |
| tool inventory == 92 | `ut-regression.log` | UT1_40 asserts ==92 | `pytest tests/unit/UT1_40` | PASS |
| b-4 T0/T1/T2 live | `t0t3-st.log` | 9 passed (anon->401/A2A/RBAC) | `pytest tests/smoke/access_control_matrix_smoke.py` | PASS |
| §1.4.1 zero os.environ.get | scan | 0 in `src/` | `grep -rnE "os.environ.get\|os.environ\[\|os.getenv" src/` | PASS |
| G3 unit regression (0.5.x) | `ut-regression.log` | 212 passed 0 failed | `pytest tests/unit --env tests/env-UT` | PASS |
| G4 keystone resolves (normal index) | `g4-docker-build.log` | Build OK; idam>=0.5.1 resolved | `bash docker-build.sh w28a-749 --variant dev` | PASS |
| G5 in-image symbols | `g5-in-image-symbol-proof.log` | idam 0.5.2; all symbols; IN-IMAGE CASCADE PROOF PASS | `docker run --entrypoint python IMG -c report` | PASS |
| G6 source + image | `remote-proof.txt` | origin/main=5cba8eb; registry sha256:02c322e26c62 | `git ls-remote origin main; docker push` | PASS |
| G7 targeted deploy | `preprod-deployed-identity.txt` | 2 add 0 change 2 destroy; Up healthy; image 1179163c0480 | `terraform apply -target=docker_container.indexretriever0` | PASS |
| G8 health/api-docs/stability | `g8-estate-health.txt`,`g8-stability.log` | /health 200, /api-docs 200, 60s all 200 | `curl -sk https://indexretriever0.cloud-dog.net/health` | PASS |
| G8 LIVE T3-IR-CASCADE | `g8-live-cascade.txt` | 403->add->200/403/403->remove->403 | live cascade curl sequence | PASS |
| G8 browser smoke (target+4 sentinels) | `g8-browser-smoke.log` | PASS 5/5, SPA mounted, 0 pageerror | `node browser-smoke.js` | PASS |
| no estate regression | `g8-estate-health.txt` | 9/9 services /health 200 | `for h in ...; curl /health` | PASS |

## CONTRACT EVIDENCE SELF-REJECTION GATE
| Gate | Raw proof | PASS |
|---|---|---|
| Contract enumerated | requirements-map.tsv 16 rows -> raw artefacts | YES |
| Exact value proof | observed values match (digests, 200s, 403/200 cascade, 92, 212) | YES |
| Required path executed | API+MCP gate, terraform deploy, live curl, real browser | YES |
| Test command proof | foreground pytest counts + logs recorded | YES |
| Evidence Matrix present | above | YES |
| No conditional skip | cascade tests run (0.5.x present), not skipped | YES |
| No shortcut substitution | live cascade + real browser, not health-only | YES |
| No manual state mutation | cascade via admin API path; cleaned up | YES |
| Local/runtime proof | in-image proof + deployed-container proof | YES |
| Commit/evidence ordering | evidence after final source commit; tags after | YES |
| Secrets/redaction | admin key resolved into var, never printed; logs masked | YES |
| Scope/dirty tree | scoped-clean-proof.txt; touched-paths outside=0 | YES |

## CLOSE GATE
- 100% acceptance criteria met: YES
- Report at: working/evidence/W28A-749/W28A-749-FINAL-REPORT.md
- PC27 foreground-only: YES
- PC29 logs in project working/: YES
- PC32 no leftover containers/processes: YES (test entities cleaned; local images are build artefacts)
- §1.4.1 bespoke grep (zero): YES (0 in src/)
- §1.6 platform package compliance section in report: YES
- Source commit on origin/main: 5cba8eb (ancestor of HEAD)
- Deployed digest == registry == :latest (no @sha256 pin): YES (registry sha256:02c322e26c62; container Up healthy)

HAVE_ALL_REQUIREMENTS_BEEN_MET: YES

## RULES.md §11 WARRANTY
The full RULES.md §11 completion warranty (13 points) is stated verbatim in the lane return for this evidence pack; all 13 lines hold true.
