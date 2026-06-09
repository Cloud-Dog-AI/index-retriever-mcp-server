# W28A-734-R2 — Evidence Matrix & Close Gate

Lane: W28A-734-R2 — index-retriever IDAM WebUI: P0 /auth/me bypass fix + 5-page PS-71 + merge-to-main + preprod live proof.

| Requirement | Raw artefact | Raw value observed | Verification command | Pass |
|---|---|---|---|---|
| fdbe063 ⊆ origin/main | remote-proof.txt / canonical-main-ancestry.tsv | git merge-base --is-ancestor fdbe063 origin/main = 0 | git merge-base --is-ancestor | PASS |
| Live unauth /auth/me NOT admin | preprod-unauth-negative-auth.tsv + negative-auth trace.zip | 401 {"detail":"Authentication failed"} (was 200 configured:admin) | curl -k https://indexretriever0.cloud-dog.net/auth/me | PASS |
| Clean-context login gate | preprod-webui-smoke/...negative-aut...trace.zip + w28a734r2-login-gate.png | anon visitor sees Sign in form only, no admin nav | playwright clean-context | PASS |
| 5/5 /idam/* authed render | preprod-webui-smoke/*.png + idam-5page trace.zip + w28a734r2-junit.xml | 5 pages render (Users/Groups/API-Keys/Roles/RBAC), junit failures=0 | playwright w28a734r2-idam-5page.spec.ts | PASS |
| RBAC denial (reader 403) | preprod-functional-smoke.tsv | reader key /api/v1/admin/users = 403 | curl -H x-api-key:READER | PASS |
| Deployed digest == pushed | preprod-deployed-identity.tsv | live a014fc0f0c09 = sha256:ee88af46... | docker ps + docker images --digests | PASS |
| Unit negative-auth test | (service repo) tests/unit/UT1_31 | 211 UT passed incl test_web_runtime_config + predicate guard | pytest tests/unit | PASS |
| §0B estate no-regression | preprod-estate-sentinels.tsv | 4 sentinels health 200; index-retriever no new breakage | curl health | PASS |

## CLOSE GATE
- 100% acceptance criteria met: YES
- §1.4.1 bespoke os.environ grep (carve-out only): ZERO non-carve-out matches
- Full UT: 211 passed / 0 failed; QT: 47 passed
- Local docker unauth gate: 401 (proven in built image a014fc0)
- Live preprod unauth /auth/me: 401 NOT admin
- Service repo on origin/main (2d3b1ab); fdbe063 ⊆ origin/main
- EVIDENCE_TAG: W28A-734-R2-evidence-20260609   FINAL_PROOF_TAG: W28A-734-R2-FINAL-PROOF-20260609

HAVE_ALL_REQUIREMENTS_BEEN_MET: YES
