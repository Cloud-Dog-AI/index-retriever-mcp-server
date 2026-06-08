# W28E-603 Phase 1 — Reading Proof

Lane: **W28E-603 — Index-Retriever Document Structure Intelligence**, Phase 1 (Model & Persistence Foundation)
plus the pre-existing index-retriever failures fixed under this lane.
Worktree: `/opt/iac/Development/cloud-dog-ai/.w28e603-ir-wt`, branch `w28e-603-phase1-structure` off `origin/main` 7157c13.
Date: 2026-06-04. Background processes: NO.

RULES-REREAD: YES
AGENT-LESSONS-REREAD: YES

## Mandatory files read

| # | File | Version / anchor |
|---|------|------------------|
| 1 | `cloud-dog-ai-platform-standards/RULES.md` | RULES.md version: v2.7 (2026-06-01) |
| 2 | `cloud-dog-ai-platform-standards/AGENT-LESSONS.md` | AGENT-LESSONS.md version: v3.13 (2026-06-04) |
| 3 | `cloud-dog-ai-platform-standards/AGENT-BOOTSTRAP-DIRECTIVE.md` | read |
| 4 | `index-retriever-mcp-server/AGENT-LESSONS.md` | IR deltas (W28A-602/878/882/884/908a/908b/964) |
| 5 | Design brief `working/INDEX-RETRIEVER-MCP-AGENT-DESIGN-BRIEF-2026-05-27.md` | 1330 lines, read |
| 6 | `index-retriever-mcp-server/docs/ARCHITECTURE.md` | read |

## PRE-FLIGHT reading proof

1. RULES.md §1.4 — three platform packages: `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_db`
   (full set also: `cloud_dog_cache`, `cloud_dog_storage`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_vdb`).
2. AGENT-LESSONS §6.78 — IR-enhancement rule: "New skeleton projects are planning-only; no runtime claims until code exists."
3. Design brief §3 — strategic decision: canonical structure persists through `cloud_dog_db`; the VDB is a derived retrieval layer, not the source of truth.
4. Design brief §22 — three guardrails: reuse platform packages; extend `cloud_dog_db` rather than bypass; keep canonical structure out of the VDB / route API+MCP+A2A+WebUI through one service layer.
5. RULES.md version: v2.7
6. AGENT-LESSONS.md version: v3.13

## Lane credential / source boundary

LOCAL ONLY for code; no Docker push, no SSH, no deploy. GitLab `origin` (`git.cloud-dog.net`) is the canonical
internal source — normal push. Live test backends (VDB/IDAM/embedding/postgres/mysql) resolved via the sanctioned
`env-vault` token (policy `cloud_dog_ai_read`); Vault was read only, never written.
