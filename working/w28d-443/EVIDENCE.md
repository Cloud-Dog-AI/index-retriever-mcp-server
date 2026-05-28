# W28D-443 Evidence: Index-Retriever Named Profile Durability

Date: 2026-05-28T08:42Z

## Decision

**Option 1: Restore durable named Index-Retriever profiles.**

The four Transparent Borders profiles are added to `defaults.yaml` as YAML-defined profiles, following the same pattern as `multilang`. YAML-defined profiles are loaded on every `IndexService.__init__()` call, making them durable across container restarts and Terraform redeployments.

## Source Change

File: `index-retriever-mcp-server/defaults.yaml` (lines 119-246 after edit)

Four profiles added:
- `demo27-transparent-borders`
- `transparent-borders-report-generation-country-reports`
- `transparent-borders-report-generation-knowledge`
- `transparent-borders-report-generation-web-support`

Each uses the same settings as `default`: `chroma` backend, `nomic-embed-text` model, `llm1.cloud-dog.net` embedding endpoint.

Test file added: `tests/unit/test_w28d443_tb_profile_durability.py` (4 tests)

## Mechanism

Profile loading path: `IndexService.__init__()` -> `_load_runtime_tree()` -> `cloud_dog_config.load_config()` -> parse `profiles.*` from `defaults.yaml` -> register in `self.profiles` dict (service.py:731-745). Profiles defined in YAML reload on every startup.

Previously, named profiles were created via `admin_profile_create()` at runtime and stored only in the in-memory `self.profiles` dict. These were lost on restart. By defining them in `defaults.yaml`, they follow the same durable path as `multilang`.

## Unit Test Results

```
187 passed in 60.82s
```

New tests:
- `test_tb_profiles_registered` - PASSED
- `test_tb_profiles_have_embeddings_config` - PASSED
- `test_tb_profiles_survive_reinit` - PASSED
- `test_tb_profiles_coexist_with_defaults` - PASSED

## Docker Build

```
Build OK: cloud-dog/index-retriever-mcp-server:latest
Tagged: registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest
Digest: sha256:8d4bdcc56ad1b0ec1d9b158676b575405ad1b6e21616d6294340be2115a22be0
```

## Terraform Deploy

```
Apply complete! Resources: 2 added, 0 changed, 2 destroyed.
```

TF targets: `docker_image.indexretriever`, `docker_container.indexretriever0`

## Live MCP Proof (Pre-Restart)

### profiles_list

Request: `{"method":"tools/call","params":{"name":"profiles_list","arguments":{}}}`

Response profiles: `["default", "demo27-transparent-borders", "multilang", "transparent-borders-report-generation-country-reports", "transparent-borders-report-generation-knowledge", "transparent-borders-report-generation-web-support"]`

All 6 profiles present.

### ingest_text + job_wait + search (all four TB profiles)

| Profile | ingest_text | job_id | job_wait status | search result |
|---|---|---|---|---|
| demo27-transparent-borders | queued | e28d6bda-b67c-4d44-973e-ed147a2517e8 | succeeded | score 0.895, text matched |
| transparent-borders-report-generation-country-reports | queued | 0ffbab56-42bf-4835-8826-7927caf4d9dd | succeeded | score matched |
| transparent-borders-report-generation-knowledge | queued | 7a908c31-8c36-4341-9828-23aece374fcc | succeeded | score matched |
| transparent-borders-report-generation-web-support | queued | 7a5164f2-4864-4a53-afb2-a22bba8ec303 | succeeded | score matched |

All four: ingest_text accepted (no 422), job_wait reached `succeeded`, search returned the ingested marker text.

## Post-Restart Durability Proof

Container restarted: `docker -H tcp://server0.viewdeck.com:2375 restart indexretriever0.app.vpc0.cloud-dog.net`

Health after restart: HTTP 200

### profiles_list (post-restart)

Response profiles: `["default", "demo27-transparent-borders", "multilang", "transparent-borders-report-generation-country-reports", "transparent-borders-report-generation-knowledge", "transparent-borders-report-generation-web-support"]`

All 6 profiles survive restart.

### ingest_text + job_wait + search (post-restart)

Profile: `demo27-transparent-borders`, collection: `w28d-443-post-restart`

- ingest_text: queued, job_id `1ae6a8b0-57e1-4aba-b076-06fec6b507f4`
- job_wait: `succeeded` at 100%
- search: returned marker text "W28D-443 post-restart durability marker 20260528" with score 0.922

Full ingest pipeline works after restart. Named profiles are durable.

## Raw Captures

- `working/w28d-443/pre-restart-mcp-captures.txt` (redacted admin tokens)

## Secret Scan

- Admin API key tokens redacted from captures
- `api-key:33282924bde4` is an internal audit fingerprint, not a secret
- No `cd_admin_*`, `VAULT_TOKEN`, or password values in tracked files
