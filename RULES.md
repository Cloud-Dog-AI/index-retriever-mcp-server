# index-retriever-mcp-server — RULES.md

## Common Rules

This project follows the [Cloud-Dog AI Platform Common Rules](../cloud-dog-ai-platform-standards/RULES.md) v2.7+.
Common rules are NOT restated here; consult central for: integrity (§1), environment+config (§2),
server+process management (§3), code+change management (§4), testing (§5), documentation (§6),
repo structure (§7), operational controls (§8), security boundaries (§9), infrastructure
protection (§10), Vault path verification (§11), implementation truthfulness (§12),
sandbox dispatch preconditions (§13 once landed), mandatory reading (§14 once renumbered).

The zero-tolerance prohibition on `os.environ.get()` fallback chains in service code is the
central rule at [RULES.md §1.4.1](../cloud-dog-ai-platform-standards/RULES.md) (landing in
W28A-882 Phase F; until then see also central §1.4 and incident records at central §1).

## Project-Specific Rules

### Verified port assignments

Verified against [`defaults.yaml`](/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server/defaults.yaml):

- API server: `8074`
- Web server: `8075`
- MCP server: `8076`
- A2A server: `8077`

### Vault sections used by this project

Load `env-vault` per central §2 before any operation. Vault sections this project depends on:

- `dev.databases` — PostgreSQL connection for profiles/jobs/audit metadata
- `dev.models` — Embedding model definitions (Ollama, OpenRouter, OpenAI-compat)
- `dev.vdbs` — Vector database connections (Chroma, Qdrant, OpenSearch, Weaviate, PGVector)
- `dev.storage` — Object storage for uploaded binaries (optional S3)
- `dev.redis` — Redis/Valkey connection (optional job queue multiplier)
- `dev.repository` — PyPI/NPM registry credentials

### Test env files

Standard committed non-secret env files (endpoints, ports, feature flags only):

- `tests/env-UT` — unit test config
- `tests/env-ST` — system test config
- `tests/env-IT` — integration test config (VDB endpoints, embedding endpoints, filesystem roots)
- `tests/env-AT` — application test config
- `tests/env-QT` — quality/security test config

`private/` is NOT required by default. If all credentials are in Vault (`dev.vdbs`, `dev.models`),
tests only need `tests/env-<TIER>` + sourcing `env-vault`. Per-backend secret files (e.g.
`private/env-<name>-secrets`) only if credentials are not yet in Vault.

Embedding-provider keys and VDB credentials always come from Vault (`dev.models`, `dev.vdbs`);
`cloud_dog_logging` redaction enforces no raw credentials in logs.

### Platform packages — MUST use (no bespoke alternatives)

| Concern | Package | Bespoke alternative forbidden |
|---------|---------|------------------------------|
| Config loading | `cloud_dog_config` | No custom env/YAML loaders |
| Logging | `cloud_dog_logging` | No custom structlog setup |
| API factory | `cloud_dog_api_kit` | No raw FastAPI() instantiation |
| Auth/RBAC | `cloud_dog_idam` | No custom JWT/API key/RBAC code |
| Job queue | `cloud_dog_jobs` | No custom job runners or schedulers |
| Embeddings | `cloud_dog_llm` | No direct OpenAI/Ollama client calls |
| VDB operations | `cloud_dog_vdb` | No direct chromadb/qdrant/opensearch client calls |

Installation:

```bash
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

### Library / server separation

- `index_tools/` MUST NOT import FastAPI, uvicorn, or MCP transport code.
- `index_retriever_server/` MUST NOT contain pipeline/embedding/VDB logic beyond dispatch and auth.
- All domain logic MUST be testable without starting a server.

### Connector safety

- Filesystem connectors MUST enforce configured scope roots.
- Path traversal (`../`) MUST be blocked.
- URI-based connectors MUST validate schemes and hosts against allowlists.
- Uploaded files MUST be stored in a sandboxed temporary directory.
- Connector registry + profile-based access controls govern which connectors a profile may invoke.
- Metadata-uplift and legacy-ingest pathways MUST flow through the canonical DiscoveryIndexService
  + metadata pipeline; bespoke ingest shortcuts are prohibited.

### Embedding provider usage

- All embedding calls MUST go through `cloud_dog_llm` adapters.
- NEVER hardcode model names, base URLs, or API keys.
- Model configuration comes from Vault `dev.models` section.
- Batch sizing, retries, and rate limits managed by `cloud_dog_llm`.
- Chunking and batch-size policy are owned by `cloud_dog_llm`; this service does not implement
  its own chunker.

### Vector backend usage

- All VDB operations MUST go through `cloud_dog_vdb` adapters.
- NEVER import `chromadb`, `qdrant_client`, etc. directly in project code.
- Backend configuration comes from Vault `dev.vdbs` section.
- Each backend MUST pass the same contract test suite.
- Spreadsheet VDB (`cloud_dog_vdb/spreadsheet`) is part of the supported backend set — see
  W28E-604 incident below.

### LlamaIndex / LangChain integration

- LlamaIndex is the primary framework wrapper.
- LangChain support is optional and enabled per profile.
- Framework code MUST be isolated in `index_tools/` and MUST NOT leak into server layer.
- Framework dependencies MUST be declared as optional extras in `pyproject.toml`.

### Prebuilt UI bundle vendoring (PS-77)

- The web server (`8075`) ships with the prebuilt UI bundle vendored from the monorepo.
- The vendored bundle is the unit of release — do not edit `dist/` directly; rebuild from the
  shared `@cloud-dog/ui` source and re-vendor.
- PS-77 compliance is verified on every deploy.

### Testing — project-specific extensions

Platform testing rules (central §5) apply in full. This section adds index-retriever specifics:

- Backend contract tests MUST run against all enabled VDB backends.
- Integration tests require real VDB, embedding provider, and running API server.
- NEVER mock VDB or embedding providers in ST/IT/AT tests.
- See [TESTS.md](./TESTS.md) for the complete test plan.

### Integrity enforcement (project-specific gates)

The central integrity rules apply (RULES.md §1). The following project-specific gates were
added after a documented integrity failure in this service (2026-02-20) and remain in force:

**Claim Gate (no proof, no claim).** Never claim `complete`, `100%`, `compliant`, or `verified`
without command evidence in the same update. Every claim must include the exact command run,
observed pass/fail/skip counts, and whether Vault was sourced. If any gate fails, state
`NOT COMPLIANT` explicitly.

**Live Backend Proof Gate.** Never claim live backend validation without running both a CRU
operation through `cloud_dog_vdb` (or project runtime) and an external verification against the
written artefact. Required proof per backend:

- `chroma` — HTTP check via `curl` against collection/object state.
- `qdrant` — HTTP check via `curl` against collection point.
- `weaviate` — HTTP check via `curl` against object endpoint.
- `opensearch` — HTTP check via `curl` against `_doc` endpoint.
- `pgvector` — protocol-correct SQL verification (`psql`), not HTTP.

**Test Integrity Gate.** Required execution order before any completion claim:

1. `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
2. `python3 -m pytest tests/integration --env tests/env-IT -q -rs` (without Vault; must fail
   explicitly, not skip).
3. Full tier run with Vault and exact counts.
4. Coverage run and reported percentage.

If coverage is below target or unknown, do not claim full compliance.

**Prohibited behaviour.** Do not reinterpret failing or partial results as acceptable. Do not
compress nuanced failures into "green" summaries. Do not present intermediate states as final
completion. Do not omit skip counts.

**Mandatory remediation behaviour.** If integrity is breached: record it in `CONTEXT-SUMMARY.md`
with exact file/command evidence, list rule IDs violated, list corrective actions completed,
list remaining non-compliance. Until all listed items are closed, completion claims are
prohibited.

---

## Incident Records

### 2026-02-20 — Local integrity-enforcement addendum

Documented integrity failure in this service led to the project-specific gates above (Claim
Gate / Live Backend Proof Gate / Test Integrity Gate / Prohibited behaviour / Mandatory
remediation behaviour). All gates remain in force; they extend central §1 with the
service-specific live-backend proof obligations.

### W28E-603 — IR doc-structure end-to-end

DONE 2026-06-05 (validator PASS, 15/15 YES, failures=0); deployed to preprod (`indexretriever0`).
Proven end-to-end LIVE against db-mcp. Key lessons captured here for re-use:

- Build from the LANE worktree, not the shared checkout — concurrent agents on `main` had been
  hijacking shared-checkout branches (e.g. W28D-323 api-kit 0.13.1 was foreign; ours was 0.13.0).
- `working/` is gitignored; closeout evidence under `working/evidence/<LANE>/` must be
  force-added (`git add -f`) and proven from the remote `-final-*` tag via tag-replay, not just
  from the worktree.
- "SENDBACK" is a validator contradiction token — treat it as a structural failure, not a
  retryable warning.
- Deploy chain: build from lane worktree → push registry → terraform apply targeted from the
  service-management workspace → verify live digest matches the pinned tag.

### W28E-604 — Excel / spreadsheet indexing

DONE across three phases (validator PASS); pushed to GitLab. Preprod deploy was gated.

- Added `cloud_dog_vdb/spreadsheet` backend and the index-retriever §14 control-plane wiring
  for it.
- Chroma `local_mode=in-memory` matrix in test runs.
- Source-stable object identity for spreadsheet rows.
- New `excel` source type added to connector + ingest pipeline.
- Closeout evidence required `git add -f` for the migration artefacts (the gitignored-log
  rule from the W28E-603 lessons applies here too).

### Platform incident relevance (cross-reference only — content owned by central)

The following platform incidents recorded in central RULES.md §1 are directly relevant to work
in this repository:

- Central §1.1 — Falsification incident: relevant to ingestion/search evidence, retention /
  reindex claims, and any report claim against this service.
- Central §1.3 — Fabrication incident: relevant to embedding model names, VDB backend names,
  connector allowlists, and port assignments in this service.
- Central §1.5 — Production firewall incident: relevant to any Docker/Terraform deployment or
  remote validation involving this service.

---

*Last updated: 2026-06-08 (trimmed to W28A-881 §5 model under W28A-882 Phase D).*
