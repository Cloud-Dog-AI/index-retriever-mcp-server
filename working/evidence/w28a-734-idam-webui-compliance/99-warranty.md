# W28A-734 — 99 Warranty & Close Gate

## Boundaries

- **Source boundary:** UI monorepo `apps/index-retriever` (commit 1dfa247, branch `w28a-734-idam-webui-index-retriever`); service `index-retriever-mcp-server` (commit 22446fe, same branch). `packages/ui` (shared) NOT modified. Worktrees isolated; UI based on landed W28A-872-R2 tip 2a4b7b9.
- **Credential boundary:** local docker-env / `tests/env-IT` + `env-vault` (sourced read-only by the committed Playwright harness). No Vault writes; no invented Vault paths.
- **Docker boundary:** local process bring-up via committed `server_control.sh`; never SSH. Default docker socket (preprod server0) untouched.

## PREPROD_TOUCH_AUDIT

- No `terraform apply`, no preprod deploy, no default-socket container lifecycle.
- Preprod host `indexretriever0` not touched. Backend + UI ran as ephemeral local processes, then stopped (ports 8074/8075/8076/8077/5197 all free).
- RULES §6.58 PREPROD_TOUCH_AUDIT clean: YES.

## Exact validator pass line

```
FINAL_EVIDENCE_VALIDATOR: PASS failures=0
```

## RULES §11 Warranty

I warrant that: no Vault writes were performed and no Vault paths were invented; all credentials were read from approved env/harness sources; the live Playwright conformance (8/8) was driven through real browser user paths (not curl); secrets are absent from all committed artefacts; the changes are committed and pushed to the canonical GitLab remote and tagged.

## W28A-734 CLOSE GATE

- 100% acceptance: every Step 1..9 PASS for Users / Groups / API Keys / RBAC: YES
- Default admin user PRESENT on Users page (Step 1.1): YES (04-screenshots/users.png)
- Default groups PRESENT on Groups page (Step 1.2): YES (04-screenshots/groups.png)
- Default admin API-key records PRESENT on API Keys page (Step 1.3): YES (04-screenshots/api-keys.png; child-generated key asserted post-Generate, owner populated)
- DataTable (PS-30) confirmed on every page: YES (platform `DataTable`, footer `Total Records: N • Page X of Y`)
- Edit forms confirmed sub-dialog (PS-71 v2): YES
- Column set matches PS-71 v2 verbatim: YES (header rows in 03-playwright-matrix.md)
- Labels match PS-71 v2 verbatim: YES (exact lowercase headers + dialog field labels)
- Button text and position match PS-71 v2: YES (`+ Add User`/`+ Add Group`/`+ Generate API Key`/`+ Add Binding`; `Bulk Delete`/`Bulk Revoke`/`Bulk Remove`; footer Cancel / Delete|Revoke|Remove / Save|Generate)
- CRUD per entity passes (Step 7.1): YES
- RBAC denial scenarios pass (Step 7.2): YES
- API key reveal-once modal passes (Step 7.3): YES
- Multi-select bulk action passes (Step 7.4): YES
- Other WebUI features checked for regression: YES (app typecheck + production build green; only IDAM views + routes changed)
- PC1 independent verification evidence present: YES (reproducible commands recorded)
- PC3 exact summary line recorded per shard: YES (`8 passed (27.8s)`)
- PC17 no weakened test assertions: YES
- PC27 foreground-only: YES
- PC29 logs in working/: YES
- PC32 no leftover containers: YES (all ports free)
- RULES §1.4 bespoke grep reviewed: YES (platform `DataTable`/`EntityDialog`/`Dialog` from `@cloud-dog/ui`; no project-local table replacement)
- RULES §6.58 PREPROD_TOUCH_AUDIT clean: YES
- RULES §6.59 WebUI Playwright proof is real user-path proof: YES
- RULES §7 Docker with no SSH: YES
- RULES §11 Vault zero writes: YES
- One Agent Per Service lock held: YES (W28A-872-R2 finished index-retriever app at 7a7d73c; later commits touch only packages/ui tests; this lane on isolated worktrees)
- Commit hash recorded: YES (UI 1dfa247, service 22446fe; final evidence commit per FINAL-TAG-VERIFICATION.txt)
- Commit on canonical GitLab remote proved: YES (remote-proof.txt)
- RULES §11 warranty signed and included: YES

## STATUS — post-SENDBACK correction (2026-06-07)

Coordinator SENDBACK: this lane delivered **4 of 5** PS-71-mandated IDAM pages. The fifth,
`/idam/roles` (§IW3A, Level-MUST, W28A-874 lock), is absent. Claiming "100% PS-71 conformance"
was false; the completion claim below is **RETRACTED**.

The Roles page is a **shared** build owned by **W28A-876** (PS-71 line 266-271 shared-component
mandate; W28A-876 directive A builds the shared `@cloud-dog/idam` Roles component, directive B the
`cloud_dog_idam` roles API, directive C mounts `/idam/roles` in all 9 services **including
index-retriever by name**). §IW3A forbids a bespoke per-service Roles UI (§1.4). W28A-876 has not
landed (no shared component, no roles API, no `packages/idam`). Therefore index-retriever's
`/idam/roles` cannot be delivered from this single-service lane without violating the shared-only
mandate, and this lane is **HELD pending W28A-876**.

What stands (validated, do not redo): the 4 delivered pages (Users/Groups/API-Keys/RBAC) with the
PS-71 v2 column/label/dialog rebuild, `/admin`→`/idam` migration, the `bootstrap.py` seed-path fix,
and this evidence pack. Concrete owner of the remaining gap: **W28A-876**.

## Completion

HAVE_ALL_REQUIREMENTS_BEEN_MET: NO — 4/5 PS-71 pages; /idam/roles (IW3A) pending shared build W28A-876. Lane HELD.
