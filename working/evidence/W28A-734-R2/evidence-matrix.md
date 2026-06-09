# W28A-734-R2 — Evidence Matrix & Close Gate (FINAL — P0 + /security residual)

| Requirement | Raw artefact | Raw value observed | Verification command | Pass |
|---|---|---|---|---|
| fdbe063 ⊆ origin/main | remote-proof.txt / canonical-main-ancestry.tsv | merge-base --is-ancestor = 0 | git merge-base --is-ancestor fdbe063 origin/main | PASS |
| Live unauth /auth/me NOT admin (post-redeploy) | preprod-unauth-negative-auth.tsv + negative-auth trace.zip | 401 (was 200 configured:admin) | curl -k /auth/me | PASS |
| Clean-context login gate | negative-auth trace.zip + w28a734r2-login-gate.png | anon sees Sign in only | playwright clean-context | PASS |
| 5/5 /idam/* authed render | preprod-webui-smoke/*.png + idam-5page trace.zip + junit | 5 pages render, junit failures=0 | playwright idam-5page | PASS |
| /security bespoke fork REMOVED | w28a734r2-security-fork-removed.png + idam-5page trace.zip | /security -> /idam/users; no Security Overview nav; no RBAC-binding-explorer | playwright idam-5page assertion | PASS |
| Bespoke fork code deleted | monorepo 74b47cb | SecurityAdminSections+SecurityPage+4 wrappers deleted (-1200 LOC) | git show 74b47cb | PASS |
| RBAC denial (reader 403) | preprod-functional-smoke.tsv | reader /api/v1/admin/users = 403 | curl -H x-api-key:READER | PASS |
| Redeployed digest == pushed | preprod-deployed-identity.tsv | live 86a0a563a284 = sha256:0f7c5151... | docker ps + images --digests | PASS |
| Unit negative-auth test | service tests/unit/UT1_31 | 211 UT passed incl predicate guard | pytest tests/unit | PASS |

## CLOSE GATE
- 100% acceptance criteria met (P0 + /security residual): YES
- P0 NOT regressed by /security removal: live unauth /auth/me = 401
- §1.4: bespoke /security SecurityAdminSectionView fork deleted (canonical /idam owns IDAM admin)
- Service origin/main 1d045b0 (ui/dist index-CBjiSmP2.js); monorepo origin/main 74b47cb; fdbe063 ⊆ origin/main
- EVIDENCE_TAG: W28A-734-R2-evidence-20260609-final   FINAL_PROOF_TAG: W28A-734-R2-FINAL-PROOF-20260609-final

HAVE_ALL_REQUIREMENTS_BEEN_MET: YES
