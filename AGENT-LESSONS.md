# Agent lessons — index-retriever-mcp-server

Last reviewed: 2026-07-15
Scope: durable project-specific knowledge only.

## Authority and use

The binding programme rules and cross-programme lessons are in
`../cloud-dog-ai-platform-standards/RULES.md` and
`../cloud-dog-ai-platform-standards/AGENT-LESSONS.md`. This file is an overlay:
central authority wins on conflict. Read current project source, canonical docs, the
exact instruction and SSOT before acting.

Mutable versions, ports, endpoints, credentials, counts and lane states are not
authority here; resolve them from current configuration, manifests and source.

## Current project knowledge

- **INDEX-CORE-001 — Lifecycle overlay.** Search results combine vector-store state with
  service-local lifecycle and compatibility overlays. Preserve
  ingest/delete/search/retrieve state shaping across Web, API and MCP.
- **INDEX-META-001 — Upload URI parsing.** For non-standard upload URIs, filenames may
  be in the parsed authority rather than path. Resolve both before inferring filename
  and MIME type.
- **INDEX-STORAGE-001 — Storage adoption.** Common-storage adoption includes
  audit/evidence sinks as well as document helpers. Do not swallow platform
  required-field errors into generic MCP success envelopes.
- **INDEX-CONFIG-001 — Runtime cache isolation.** Clear cached runtime configuration
  when tests mutate env/config and in fixture teardown; otherwise one acceptance case
  can poison later cases.
- **INDEX-PATH-001 — Compatibility paths.** Prove the configured API base, preserved
  legacy path and rejected stale path separately. Local code-path proof, image proof and
  live environment override are distinct.
- **INDEX-SOURCE-001 — Server-visible sources.** A source-config test runs in the
  selected service environment. Filesystem paths must exist there; a controller-local
  temporary path is not a valid preprod source.
- **INDEX-PROFILE-001 — Profile durability.** Prove each profile through list, ingest,
  job completion and same-profile search, then repeat after restart/redeploy. One-shot
  creation is not durability.
- **INDEX-UI-001 — Security admin surface.** Users, groups, API keys and RBAC share one
  security-admin page. Keep status/action shaping and accessible row controls consistent
  when changing any section.
- **INDEX-DOC-001 — Metadata contract.** Requirements and architecture define metadata
  ownership and field names. Update API reference and tests with a model change rather
  than inventing local names.
- **INDEX-TEST-001 — Full native gate.** Targeted tests diagnose; the repository's named
  full native suite exposes cross-layer runtime/WebUI contamination and remains the
  acceptance gate when required.

## Historical provenance

The complete pre-refresh document is preserved at commit `94f4e8cb3de1b12d390fb8e7d6b138f243d88afb`, path `AGENT-LESSONS.md`, SHA-256 `43f00b63cb9aca99b5785fb354dcb847c7f54d6f68eac2723feede432475837d`. Its 60 addressable units, including 26 historical, mutable, duplicate or heading-only units omitted from the active body, are mapped individually in the central `lesson-unit-migration.tsv` ledger.
