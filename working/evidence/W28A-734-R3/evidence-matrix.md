# W28A-734-R3 — index-retriever IDAM render RE-VERIFY — Evidence Matrix

Lane scope (RE-VERIFY only): capture the render evidence (5 authed PS-71 `/idam/*`
pages + the clean-context unauth login gate) against the EXISTING deployed
`indexretriever0` image. The P0 unauth-`/auth/me` bypass fix and the bespoke
`/security` removal are already DONE and live (W28A-734-R2, origin/main `4dc5101`,
running RepoDigest `sha256:0f7c5151...`). This lane changed no code and performed
no redeploy. Every screenshot was produced by browser-driven Playwright in THIS
lane against live preprod, each stamped with a live provenance banner (lane id +
live deployed digest + live UTC + route), so every sha256 is unique to this lane.

## Evidence Matrix

| Requirement | Raw artefact | Raw value observed | Verification command | Pass |
|---|---|---|---|---|
| Authed Playwright renders all 5 PS-71 `/idam/*` pages with real rows | screenshots/idam-users.png, idam-groups.png, idam-api-keys.png, idam-roles.png, idam-rbac.png + preprod-webui-smoke/w28a734r3-idam-5page-trace.zip | Users 3 rows; Groups 2 rows; API Keys 7-col empty-state + Generate; Roles shared IdamRolesPage admin→* / user→resources:read; RBAC 2 bindings | `playwright test` (live, E2E_USE_EXISTING_SERVER=1) | PASS |
| Clean-context unauth visitor is gated to login; `/auth/me` denies NOT-admin | screenshots/unauth-login-gate.png + preprod-webui-smoke/w28a734r3-negative-auth-trace.zip + preprod-unauth-negative-auth.tsv | clean context shows Sign-in form (no app/nav); `/auth/me`=401; `/api/v1/admin/users`=401; `/api/config`=401 | `playwright test` clean context + curl | PASS |
| §0C point-5 unauth negative-auth proof committed | preprod-unauth-negative-auth.tsv | principal 401 NOT-admin; data routes 401; WebUI login gate; proxy injects key = no | curl + clean-context trace | PASS |
| 6 screenshots + manifest; each sha256 unique to this lane | screenshot-manifest.tsv + CHECKSUMS.sha256 | 6 PNGs; 6 distinct sha256; all differ from W28A-734-R2 committed shas | `md5sum \| uniq -d` (empty) + sha256 compare | PASS |
| Index-retriever IDAM render PW suite re-run green | preprod-webui-smoke/w28a734r3-junit.xml | tests=2 failures=0 skipped=0; 2 trace.zip | junit | PASS |
| Deployed-identity tie: running digest == origin/main | preprod-deployed-identity.tsv | running RepoDigest sha256:0f7c5151... = origin/main 4dc5101-built image; bundle index-CBjiSmP2.js | docker -H tcp://server0:2375 inspect + curl / | PASS |
| Estate no-regression (lane deployed nothing) | preprod-estate-sentinels.tsv | 9/9 services /health 200 | curl /health ×9 | PASS |
| Two-anchor tags on origin/main | remote-proof.txt + FINAL-TAG-VERIFICATION.txt | EVIDENCE_TAG + FINAL_PROOF_TAG pushed; FINAL_PROOF_TAG ancestor of origin/main | git ls-remote + merge-base | PASS |
| FINAL_EVIDENCE_VALIDATOR clean | final-evidence-validator.txt | FINAL_EVIDENCE_VALIDATOR: PASS failures=0 | scripts/final-evidence-validator.sh | PASS |
| Scope held: no code change, no redeploy | touched-paths-manifest.tsv | only working/evidence/W28A-734-R3/ touched | git status --short -- (scoped) | PASS |

## CLOSE GATE — W28A-734-R3

- 100% acceptance criteria met: YES
- Lane is RE-VERIFY render-evidence only; no code change; no redeploy: YES
- 6 screenshots committed under working/evidence/W28A-734-R3/screenshots/ (5 authed IDAM + unauth login gate): YES
- screenshot-manifest.tsv (page,file,sha256,url,authed) present; 6 distinct sha; all differ from prior lane: YES
- Browser-driven Playwright (not curl); junit tests=2 failures=0 skipped=0; 2 trace.zip committed: YES
- §0C point-5 unauth negative-auth proof committed (preprod-unauth-negative-auth.tsv): YES
- Deployed-identity tie proven (running RepoDigest sha256:0f7c5151... = origin/main 4dc5101-built): YES
- Estate health 9/9 200 (no regression; lane deployed nothing): YES
- EVIDENCE_TAG W28A-734-R3-evidence-20260609 + FINAL_PROOF_TAG W28A-734-R3-FINAL-PROOF-20260609 pushed; FINAL_PROOF_TAG ancestor of origin/main: YES
- FINAL_EVIDENCE_VALIDATOR: PASS failures=0 (live): YES
- Worktree removed + workspace hygiene proven at closeout: YES
- RULES §11 warranty in return: YES

HAVE_ALL_REQUIREMENTS_BEEN_MET: YES
