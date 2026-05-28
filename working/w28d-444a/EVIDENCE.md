# W28D-444A R2 Evidence: NATO Doctrine Index-Retriever Named Profile Durability

Date: 2026-05-28T14:30Z

## Decision

Option 1: Restore durable named-profile by adding `nato-doctrine` to `defaults.yaml`.

## Source Change

File: `index-retriever-mcp-server/defaults.yaml` (commit `4fc70c7`)
- Added `nato-doctrine` profile with `type: "${CLOUD_DOG__INDEX__VDB__PROVIDER:chroma}"` (resolves to `qdrant` on preprod)
- Embedding: `nomic-embed-text` on `${EMBED_BASE_URL}`

## Raw MCP JSON Artefacts

All raw JSON responses are tracked at `working/w28d-444a/raw/`. Secrets redacted.

### Post-Restart-1 Proof

| File | MCP Tool | Key Result |
|---|---|---|
| `raw/00-restart.log` | docker restart | Health: 200 |
| `raw/01-profiles-list.json` | profiles_list | 7 profiles incl. `nato-doctrine` |
| `raw/02-profile-get-nato-doctrine.json` | profile_get | backend=qdrant, enabled=true |
| `raw/03-search-corpus.json` | search nato-doctrine-library | 3 results, scores 0.769 |
| `raw/04-ingest-text.json` | ingest_text nato-doctrine-smoke | job `7ca607c5`, queued |
| `raw/05-job-wait.json` | job_wait | succeeded |
| `raw/06-search-smoke.json` | search smoke marker | 3 results, top score 0.944 |

### Post-Restart-2 Durability Proof

| File | MCP Tool | Key Result |
|---|---|---|
| `raw/07-restart-2.log` | docker restart | Health: 200 |
| `raw/08-profiles-list-post-restart2.json` | profiles_list | 7 profiles incl. `nato-doctrine` (survived 2nd restart) |
| `raw/09-search-smoke-post-restart2.json` | search pre-restart marker | 3 results, top score 0.944 |
| `raw/10-search-corpus-post-restart2.json` | search nato-doctrine-library | 3 results (full corpus accessible) |
| `raw/11-ingest-post-restart2.json` | ingest_text fresh marker | job `adf33567`, queued |
| `raw/12-job-wait-post-restart2.json` | job_wait | succeeded |
| `raw/13-search-fresh-post-restart2.json` | search fresh marker | 3 results, top score 0.938 |

### Terraform State

| File | Content |
|---|---|
| `raw/terraform-state-image.json` | `docker_image.indexretriever` state |
| `raw/terraform-state-container.txt` | `docker_container.indexretriever0` state (first 30 lines) |

## Terraform Deploy (from R1)

- Image digest: `sha256:aaa34d67545ed899c55950d9e7a56389d5641f51c8b6e8b7ec18293c3b6d14ed`
- `Apply complete! Resources: 2 added, 0 changed, 2 destroyed.`
- TF targets: `docker_image.indexretriever`, `docker_container.indexretriever0`
- TF plan file: `w28d-444a.tfplan`

## Success Criteria (all PASS)

| Criterion | Raw evidence file | Result |
|---|---|---|
| profiles_list includes nato-doctrine post-restart-1 | `01-profiles-list.json` | PASS |
| profile_get shows backend=qdrant | `02-profile-get-nato-doctrine.json` | PASS |
| NATO corpus searchable in nato-doctrine-library | `03-search-corpus.json` | PASS (3 results) |
| ingest_text into nato-doctrine-smoke | `04-ingest-text.json` | PASS (queued) |
| job_wait reaches succeeded | `05-job-wait.json` | PASS |
| search returns smoke marker | `06-search-smoke.json` | PASS (score 0.944) |
| profiles_list post-restart-2 includes nato-doctrine | `08-profiles-list-post-restart2.json` | PASS (survived) |
| Pre-restart marker searchable post-restart-2 | `09-search-smoke-post-restart2.json` | PASS (score 0.944) |
| NATO corpus searchable post-restart-2 | `10-search-corpus-post-restart2.json` | PASS (3 results) |
| Fresh post-restart-2 ingest succeeds | `11-ingest-post-restart2.json` + `12-job-wait-post-restart2.json` | PASS (succeeded) |
| Fresh marker searchable post-restart-2 | `13-search-fresh-post-restart2.json` | PASS (score 0.938) |

## W28D-443 Cross-Reference

W28D-443 closed by commit `4911fae` (same `defaults.yaml` pattern). Both NATO and TB named profiles are durable.

## Commits + Remote Ancestry

| Repo | Commit | Remote |
|---|---|---|
| index-retriever-mcp-server | `4fc70c7` (source) | origin/main = `4fc70c7` |
| cloud-dog-ai-platform-standards | `82e3a89` (R1 evidence) | origin/main matched at time of push |

R2 evidence commit will update both repos.

## git diff --check

Clean (no whitespace errors).

## Secret Scan

- Admin tokens: redacted from all raw files, verified absent
- Qdrant API keys: redacted from all raw files, verified absent
- VAULT_TOKEN / passwords: absent
- Source diff contains no credentials

## PREPROD_TOUCH_AUDIT

- Docker push: `registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest`
- Terraform apply: 2 added, 2 destroyed
- Container restart x2: `docker -H tcp://server0.viewdeck.com:2375 restart`
- No SSH, no Vault writes, no firewall changes
