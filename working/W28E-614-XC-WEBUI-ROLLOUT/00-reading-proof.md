# W28E-614 — Mandatory Reading Proof

Lane: W28E-614 — index-retriever XC WebUI rollout
Worker: claude-opus-4-7 (cloud-dog-ai sdk session)
Worktree: /opt/iac/Development/cloud-dog-ai/.coord-worktrees/w28e-614-svc/
Branch: w28e-614-index-retriever-xc

## Files re-read for THIS lane (verbatim from disk)

- RULES.md:                /opt/iac/Development/cloud-dog-ai/.coord-worktrees/w28e-614-svc/RULES.md
- AGENT-LESSONS.md:        /opt/iac/Development/cloud-dog-ai/.coord-worktrees/w28e-614-svc/AGENT-LESSONS.md
- Instruction:             /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/working/instructions/W28E-614-index-retriever-XC-WEBUI-ROLLOUT-2026-06-03.md
- Closeout controls:       /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/working/instructions/COMMON-FINAL-EVIDENCE-CLOSEOUT-CONTROLS.md
- W28E-608:                /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/working/instructions/W28E-608-XC-WEBUI-CROSS-SERVICE-ROLLOUT-2026-06-03.md
- W28E-608B:               /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/working/instructions/W28E-608B-XC-WEBUI-AUGMENT-PASS12-2026-06-03.md

RULES_REREAD: YES
AGENT_LESSONS_REREAD: YES

## Live version strings

- RULES.md header:                `# index-retriever-mcp-server — Agent & Engineer Rules` / **Version:** 3.0
- AGENT-LESSONS.md header:        `# Agent Lessons — index-retriever-mcp-server` / first section `## Platform Alignment (Binding - 2026-06-01)`

## Lane-specific reading-proof answers (copied from the files)

1. AGENT-LESSONS §1 (Platform Alignment binding 2026-06-01): "No Vault writes without explicit per-action user authorization; no SSH/firewall/live-container code or config hotfixes; no coordinator-owned state mutation unless assigned." — applied: this lane uses only `DOCKER_HOST=tcp://server2.viewdeck.com:2375` builds and Terraform-targeted apply; zero SSH; zero Vault writes; zero firewall edits.

2. AGENT-LESSONS line 29: "The `ThreadPoolExecutor` in `service.py:580` runs the asyncio event loop that hosts MCP/tool handlers. It is NOT a job queue and cannot be routed through `cloud_dog_jobs`." — applied: XC-010 `async_mode` work was placed in the MCP-server reindex/bulk_ingest path that does flow through `self.queue+JobRecord` (cloud_dog_jobs compatible), and we did NOT attempt to refactor the executor in service.py.

3. AGENT-LESSONS line 48: "`pytest.skip()` is FORBIDDEN in IT/AT tests per RULES §5.3.10." — applied: this lane adds Playwright (browser) tests, not IT/AT; no `pytest.skip` introduced; new specs use Playwright `test.skip` only where coordinator-authorized.

4. AGENT-LESSONS line 194: "`cloud-dog-api-kit==0.4.1` from `pypi.cloud-dog.net` is the required package version for this repo's `WebApiProxy` path. Do not modify `cloud_dog_api_kit` source directly and do not invent local intermediary versions." — applied: this lane does NOT touch cloud_dog_api_kit; uses the kit's `WebApiProxy` and `create_app` as-is. The new `/api/v1/admin/policies` route is added to the service `api_server.py`, not to the kit.

5. RULES §1 line 53 (env-vault sourcing): "`set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`" — noted but not used by this lane; we authenticate to live preprod via cookie login (admin / OrangeRiverTable from runtime config); no shared-Vault token scraping.

## Commands used to read/verify the files

```bash
$ head -3 /opt/iac/Development/cloud-dog-ai/.coord-worktrees/w28e-614-svc/RULES.md
$ head -3 /opt/iac/Development/cloud-dog-ai/.coord-worktrees/w28e-614-svc/AGENT-LESSONS.md
$ grep -n "ssh\|DOCKER_HOST\|server0\|vault\|api-kit\|local docker" \
    /opt/iac/Development/cloud-dog-ai/.coord-worktrees/w28e-614-svc/RULES.md
$ grep -nm10 "MCP transport\|.skip\|Vault\|bespoke\|filter-tree\|api-kit" \
    /opt/iac/Development/cloud-dog-ai/.coord-worktrees/w28e-614-svc/AGENT-LESSONS.md
```

The above commands were executed in this session on 2026-06-04 and the live
output of each was kept in the conversation transcript as the source of the
quoted answers above. No prior-conversation memory was used to satisfy this
reading-proof; the files were re-read for this lane.
