# W28A-734 — 00 Reading Proof & Pre-Flight

READING PROOF
RULES_REREAD: YES (RULES.md Version 2.7, 2026-06-01)
AGENT_LESSONS_REREAD: YES (AGENT-LESSONS.md Version 3.16, 2026-06-06)

Lane: **W28A-734 IDAM WebUI Compliance — index-retriever** (child of W28A-726).
Generated/owned by: the Auditor, executing the lane per coordinator direction.
Date: 2026-06-07.

## Mandatory Reading (versions / proof)

| # | Document | Version / proof |
|---|----------|-----------------|
| 1 | `cloud-dog-ai-platform-standards/RULES.md` | **v2.7** (Last updated 2026-06-01); md5 `a0f74afb8dae24fdeb5638011bf9bc66` |
| 2 | `cloud-dog-ai-platform-standards/AGENT-LESSONS.md` | **v3.16 — 2026-06-06**; md5 `a908e4cb8743ec3d2956d33d86a5bbb3` |
| 3 | `AGENT-BOOTSTRAP-DIRECTIVE.md` | read (bootstrap directive) |
| 4 | `PLATFORM-TLS-PROXY-GUIDANCE.md` | read (TLS proxy guidance) |
| 5 | `docs/standards/30-ui.md` (PS-30 DataTable) | read — DataTable footer `Total Records: N • Page X of Y` |
| 6 | `docs/standards/71-idam-webui.md` (PS-71 v2) | read — IW1.1/IW2.1/IW3.1/IW3A.1/IW4.1 column tables; IW3.4 reveal modal; IW*.2 button text |
| 7 | `docs/standards/70-user-mgmt-idam.md` (PS-70) | read — roles/permissions/RBAC distinction |
| 8 | `docs/standards/40-logging-observability.md` (PS-40) | read — RBAC denial audit fields |
| 9 | `docs/standards/77-webui-comprehensive.md` (PS-77) | read |
| 10 | `working/instructions/W28A-706-IDAM-WEBUI-STANDARD-2026-05-29.md` | read |
| 11 | `working/instructions/W28A-716-IDAM-WEBUI-COMPLIANCE-2026-05-29.md` | read |
| 12 | `working/instructions/W28A-726-IDAM-WEBUI-COMPLIANCE-DISPATCHER-2026-05-29.md` | read — exact lowercase header mandate (`username` not `Username`, `last_login` not `Last Login`) lines 180-195 |
| 13 | `cloud-dog-ai-ui-monorepo/AGENT-LESSONS.md` | read |
| 14 | project `RULES`/`AGENT-LESSONS`/env templates/route maps | read (see 01-route-inventory.md) |
| 15 | `COMMON-FINAL-EVIDENCE-CLOSEOUT-CONTROLS.md` | read — §0A Non-Negotiable Final Evidence Gate |

## Exact validator pass string (target)

```
FINAL_EVIDENCE_VALIDATOR: PASS failures=0
```

## Boundaries

- **Source boundary:** Two repos, both on isolated lane worktrees on branch `w28a-734-idam-webui-index-retriever`:
  - Service: `/opt/iac/Development/cloud-dog-ai/.w28a734-svc` (off `main` @ `b164abd`).
  - UI monorepo: `/opt/iac/Development/cloud-dog-ai/.w28a734-ui-monorepo` (off W28A-872-R2 tip `2a4b7b9`, to inherit the landed shared-pattern migration and avoid an App.tsx merge conflict when 872-R2 merges). Will NOT modify `packages/ui` (shared) — only `apps/index-retriever`.
- **Credential boundary:** local docker-env only (`docker-env.local`, `docker-env.example`). No Vault writes; no invented Vault paths (RULES §11). No raw API-key values in screenshots/traces/DOM/logs/reports.
- **Docker boundary:** local docker only; never SSH (RULES §7). Build/test on **server2** (`DOCKER_HOST=tcp://server2.viewdeck.com:2375`) — default socket is preprod server0 and is OFF-LIMITS for build/test/lifecycle.

## PREPROD_TOUCH_AUDIT

- No `terraform apply`, no preprod deploy, no default-socket lifecycle (`docker rm/stop`) performed by this lane.
- Preprod host `indexretriever0` NOT touched. All bring-up is ephemeral local docker on server2.
- One-Agent-Per-Service: W28A-872-R2 finished `apps/index-retriever` at commit `7a7d73c` (10:32); its later commits (10:37–10:40) touch only `packages/ui` tests — no live collision on `apps/index-retriever`. This lane works on an isolated worktree off the 872-R2 tip and does not touch `packages/ui`.

## Delta summary (true scope — see 01-route-inventory.md)

index-retriever IDAM pages render via bespoke `apps/index-retriever/src/views/SecurityAdminSections.tsx` using platform `DataTable`/`EntityDialog` but with non-conformant columns/labels/buttons and a persistent token panel (not a reveal-once modal). Work:
1. Conform 4 page column sets to PS-71 v2 exact lowercase headers/order.
2. `+ Add User / + Add Group / + Generate API Key / + Add Binding`; bulk `Bulk Delete / Bulk Revoke / Bulk Remove`.
3. One-time API-key reveal modal (IW3.4) replacing the persistent "Latest issued token" panel.
4. Route conversion `/admin/*`→`/idam/*` (App.tsx nav+routes; service `web_server.py` `_SPA_ADMIN_PATHS` + SPA route registration), `/admin/*` retained as legacy alias redirect.
5. Backend: surface `granted_by` in `rbac_bindings_list` (config-event actor, else `system`).

**Roles page (IW3A) note:** the PS-71 standard canonical set is 5 pages (adds `/idam/roles`, IW3A). The W28A-734 instruction explicitly scopes 4 (`users`/`groups`/`api-keys`/`rbac`). This lane delivers the 4 named pages; the Roles page (IW3A) is flagged for a coordinator decision / separate lane and is not silently absorbed (concrete owner: coordinator).
