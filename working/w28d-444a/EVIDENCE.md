# W28D-444A Evidence: NATO Doctrine Index-Retriever Named Profile Durability

Date: 2026-05-28T10:15Z

## Decision

Option 1: Restore durable named-profile by adding `nato-doctrine` to `defaults.yaml`.

## Source Change

File: `index-retriever-mcp-server/defaults.yaml`
- Added `nato-doctrine` profile with `type: "${CLOUD_DOG__INDEX__VDB__PROVIDER:chroma}"` (resolves to `qdrant` on preprod)
- Same embedding settings as `default`: `nomic-embed-text` on `llm1.cloud-dog.net`

## Live MCP Proof (Post-Deploy, Pre-Restart)

| Step | Tool | Result |
|---|---|---|
| 1 | profiles_list | 7 profiles including `nato-doctrine` |
| 2 | profile_get nato-doctrine | backend=qdrant, enabled=true |
| 3 | search nato-doctrine-library | 3 results (corpus accessible, scores 0.769) |
| 4 | ingest_text nato-doctrine-smoke | job_id `efc8a1f6-69df-4204-a8c3-9ff7e7136d11`, queued |
| 5 | job_wait | succeeded |
| 6 | search smoke marker | 3 results, top score 0.945 |

## Post-Restart Durability Proof

Container restarted: `docker -H tcp://server0.viewdeck.com:2375 restart indexretriever0.app.vpc0.cloud-dog.net`
Health after restart: HTTP 200

| Step | Tool | Result |
|---|---|---|
| 8 | profiles_list | 7 profiles including `nato-doctrine` (survived restart) |
| 9 | search pre-restart smoke marker | 3 results, top score 0.945 (pre-restart data accessible) |
| 10 | search nato-doctrine-library corpus | 3 results, scores 0.828/0.816/0.814 |
| 11 | ingest_text fresh post-restart | job `6a258c5a` succeeded |
| 12 | search fresh marker | 3 results, top score 0.918 |

## W28D-443 Cross-Reference

W28D-443 is closed by commit `4911fae` (same lane, same defaults.yaml fix pattern). The TB profiles are also durable. This fix extends the same pattern to `nato-doctrine`.

## Secret Scan

- No credentials in committed diff
- Qdrant API key in live `profile_get` response is redacted in evidence (appears as resolved env var in the container runtime only, not in source)
