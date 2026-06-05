# W28E-603 — COORDINATOR DECISION (CORRECTED): Criterion #13 — DELEGATION REVERSED

Supersedes the earlier same-file decision that scoped #13's residual to a delegated db-mcp lane. That earlier
decision is **WITHDRAWN** by the coordinator: it moved functionality to the right (a gate-to-the-right), which
is rejected. This is functional pushback — W28E-603 owes real work, not a presentation edit.

## Corrected decision (2026-06-05)
1. **§25 #13 is NOT met** until db-mcp read-only-RBAC-through-the-live-stack **and** audit-source attribution
   are **implemented and proven end-to-end through the live stack, inside W28E-603**. No "owned by another
   lane." No gate-to-the-right. The cross-service read-proof already captured (`db-mcp-read-proof.txt`) is the
   read-path half only; it does **not** satisfy #13.
2. That path runs through db-mcp, so **W28A-871 (DB-MCP UAT WebUI recovery & deploy smoke gate) is a HARD
   PREREQUISITE.** W28A-871 is currently RUNNING (dispatched 2026-06-05), not yet accepted. Once W28A-871 lands
   (db-mcp recovered + live + smoke green), W28E-603 implements and proves #13 end-to-end against the live db-mcp
   stack — including the read-only structure profile, read-only-RBAC enforcement (analyst data.read PASS /
   data.create 403) and audit-source attribution (access identifiable as db-mcp-service vs IndexRetriever).
3. **W28E-603 stays HELD / RUNNING at 14/15.** It may assert `HAVE_ALL_REQUIREMENTS_BEEN_MET: YES` /
   `FINAL_EVIDENCE_VALIDATOR: PASS failures=0` **only** when all 15 §25 criteria are genuinely met.
4. W28E-603 does **not** ride the W28E-618 deploy.

## Current honest state
14/15 §25 met. #13: read/present proven cross-service (partial); full end-to-end live read-only-RBAC + audit-
source owed in-lane, blocked on W28A-871. In-lane completion plan: `db-mcp-13-inlane-plan.md`.
