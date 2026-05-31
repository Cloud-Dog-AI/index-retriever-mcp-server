# W28A-693 Pre-Flight

Instruction: `W28A-693-JOB-WEBUI-COMPLIANCE-INDEX_RETRIEVER-2026-05-29.md`

- RULES_REREAD: YES (version: 2.4)
- AGENT-LESSONS-REREAD: YES (platform version: 3.7; project AGENT-LESSONS read)
- BOOTSTRAP_REREAD: YES (version: 5.0)
- PS-76 v2 read: YES (version: 2.0)
- Project AGENT-LESSONS read: YES
- UI monorepo AGENT-LESSONS read: file not present; `cloud-dog-ai-ui-monorepo/AGENTS.md` read
- PREPROD_TOUCH_AUDIT: declared local-only/read-only
- NO_VAULT_WRITES: YES
- NO_SECRET_LEAK: YES
- Background processes: NO

## Reading Proof

1. PS-76 v2 JW2 mandatory columns: Job ID, Type, Status, Created, Started, Updated, Completed, Actor, Duration, Result link, Log link, Retry count.
2. PS-76 v2 JW3 succeeded badge: green success badge.
3. PS-76 v2 JW4 mandatory detail dialog tabs: Overview, Parameters, Input ref, Result/Output, Thinking, Lifecycle log, Raw.
4. PS-76 v2 JW5 bulk actions: Cancel Selected, Retry Selected, Delete Selected.
5. PS-76 v2 JW6 non-admin behaviour: non-admin users see only their own jobs, cannot use actor filtering, cannot see delete controls, and direct access to another actor's job returns inline 403.
6. W28A-620 pagination format: `Total Records: N` and `Page X of Y` with Prev/Next and 10/25/50/100 page-size options.
7. AGENT-LESSONS section 6.58 invalidation: missing preprod touch audit, SSH, live hotfixes, manual host edits, uncontrolled Terraform/live mutation, or unproven durable deployment invalidates the return.
8. AGENT-LESSONS section 6.59 100% acceptance: full instruction scope must be completed, audited, evidenced, and warranted with real user-path proof; health checks, route 200s, screenshots, discovery, or partial API success alone are not readiness evidence.

## Target And Evidence

- Target repo: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`
- UI source repo: `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo`
- Jobs source file used: `apps/index-retriever/src/views/JobsPageView.tsx`
- Evidence root: `working/w28a-693/`
- Local code evidence: `working/w28a-693/local-code/`
- Local Docker evidence: `working/w28a-693/docker/`
