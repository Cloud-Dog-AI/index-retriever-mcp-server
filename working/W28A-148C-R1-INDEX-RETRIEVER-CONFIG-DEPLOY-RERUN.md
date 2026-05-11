# W28A-148C-R1 Index Retriever Config/Deploy/Rerun

Date: 2026-05-11
Scope: `index-retriever-mcp-server/**`, MLAgents `indexretriever0` deployment/config only.

## Source State

- `index-retriever-mcp-server` worktree was clean before this report.
- `HEAD`: `de76ca0`
- `origin/main`: `de76ca0`
- Source fix: `de76ca0 Fix index retriever RBAC parser docs`

## Role Config Proof

Raw credential values were not printed.

Approved MLAgents preprod config now supplies distinct scoped role variables to `indexretriever0`:

| Role | Terraform variable | Container env | Present | Length | SHA-256 prefix | Runtime mapping |
| --- | --- | --- | --- | ---: | --- | --- |
| admin | `indexretriever_admin_api_key` | `CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY` | yes | 57 | `33282924bde4` | admin, maintainer, writer, reader |
| maintainer | `indexretriever_maintainer_api_key` | `CLOUD_DOG__INDEX__AUTH__MAINTAINER_API_KEY` | yes | 62 | `a4c9409b4490` | maintainer, writer, reader |
| writer | `indexretriever_writer_api_key` | `CLOUD_DOG__INDEX__AUTH__WRITER_API_KEY` | yes | 58 | `27fd107a9c59` | writer, reader |
| reader | `indexretriever_reader_api_key` | `CLOUD_DOG__INDEX__AUTH__READER_API_KEY` | yes | 58 | `9a3ac2acf219` | reader |

Distinct proof: `true`.

Post-deploy Docker inspect proved all four scoped env names present with values redacted.

## Deploy Proof

- Build command: `./docker-build.sh`
- Local image ID: `sha256:500063c9fbe59dd099383e232f8d0485d2c43ee2a96d866b0853fe864ed32368`
- Registry push digest: `sha256:6a61ef41cc5b04adb7469d452129ba046053536e20627baf7823598e0e97d3f0`
- Terraform plan target: `docker_image.indexretriever`, `docker_container.indexretriever0`
- Terraform plan scope: `2 to add, 0 to change, 2 to destroy`; only `docker_image.indexretriever` and `docker_container.indexretriever0`
- Terraform apply: `2 added, 0 changed, 2 destroyed`
- New container ID: `2e53a09d6d4da8832c0142213a12d4ef1e15a107b6a7dea767570c62fd1521e8`
- New container image: `sha256:500063c9fbe59dd099383e232f8d0485d2c43ee2a96d866b0853fe864ed32368`
- Container health: `healthy`
- Container start: `2026-05-11T14:04:29Z`
- Python proof: `python=3.12.13`
- Source proof in container:
  - `middleware.py`: role env support present
  - `api_server.py`: API docs/parser bridge proof present

## Live Health

- `GET https://indexretriever0.cloud-dog.net/health`: 200, `status=ok`
- `GET https://indexretriever0.cloud-dog.net/api/health`: 200, `status=ok`
- `GET https://indexretriever0.cloud-dog.net/status`: 200, `status=ok`, host `indexretriever0.app.vpc0.cloud-dog.net`

## Test Results

First focused Playwright attempt was invalid as an app result because Chromium could not launch inside the sandbox:

- Result: `3 failed`
- Failure mode: `sandbox_host_linux.cc:41`, `Operation not permitted`
- Action: reran with approved escalation.

Focused failing specs against deployed preprod:

- `P7 API docs page loads`: initial escalated combined run failed once on missing heading after auth; immediate single rerun passed.
- `writer sees source config mutations blocked but sync remains available across connector types`: passed in escalated combined run.
- `W28A-908b MCP console parser, preview, OCR, table extraction, and RBAC checks`: passed in escalated combined run.
- `viewer sees collections read-only and collection create is denied`: passed in exact follow-up run; earlier grep missed this title.

Exact focused outputs:

- Combined focused rerun: `2 passed, 1 failed (P7)`.
- P7 single rerun: `1 passed (4.6s)`.
- Viewer collection-denial rerun: `1 passed (4.1s)`.

Full Index Retriever shard:

- Command: `npm run e2e -- --workers=1 --reporter=line`
- Result: `54 passed (4.2m)`

## Slot Use

- LLM1: not used.
- No reload/reindex was performed.
- No full W28A-102 estate rerun was performed.
- No public publication was performed.

## Residual Blockers

- None for the post-`de76ca0` Index Retriever W28A-102 blocker. Role-specific config is deployed and the full Index Retriever shard is green.
