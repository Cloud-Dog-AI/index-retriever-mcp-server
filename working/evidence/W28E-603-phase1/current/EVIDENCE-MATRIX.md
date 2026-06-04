# W28E-603 Phase 1 — Evidence Matrix

Scope of this return: design brief §24 Phase 1 (Model & Persistence Foundation) plus the pre-existing
index-retriever failures fixed under this lane. Every row maps to a raw artefact, a raw observed value,
and a verification command. Phases 2–6 of the design brief (§25 criteria #3,#5,#8–#13) are separate
downstream lanes and are documented as such in `close-gate.md`.

| Requirement | Raw artefact | Raw value observed | Verification command | Pass |
|---|---|---|---|---|
| Canonical structure model + schema version (§6,§24-P1) | src/index_tools/structure/models.py | SCHEMA_VERSION="1.0"; 9 canonical models + Bundle | pytest tests/unit/UT_W28E603_Structure::test_schema_version_constant | Pass |
| cloud_dog_db persistence + migration (§7.1) | database/migrations/cloud_dog_db/versions/20260604_0002_structure_foundation.py | 9 structure tables, down_revision=20260305_0001 | pytest tests/unit/UT_W28E603_Structure::test_create_assigns_ids_and_persists | Pass |
| Basic CRUD API under /api/v1/structure (§12) | src/index_server/api_server.py | 7 routes incl POST/GET/DELETE documents | pytest tests/integration/IT_W28E603_StructureTransports::test_structure_rest_crud_lifecycle | Pass |
| Basic MCP list/get tools (§13) | src/index_tools/tools/registry.py | 8 structure_* tools registered + dispatched | pytest tests/integration/IT_W28E603_StructureTransports::test_structure_mcp_tools_call_real_execution | Pass |
| 100% platform reuse, zero bespoke (RULES §1.4/§6.88) | current/bespoke-grep.txt | zero matches across 6 forbidden categories | grep -rnE forbidden-patterns over structure+connectors | Pass |
| RC-01 hardcoded loopback (quality) | tests/quality/QT_COMPLIANCE/conftest.py | allowlist line numbers reconciled to 86/87/96/151/152 | pytest tests/quality::test_rc01_no_hardcoded_urls_or_loopback | Pass |
| RC-09 connector fetch implemented (quality) | src/index_tools/connectors/s3.py,webdav.py,gdrive.py | fetch() delegates to cloud_dog_storage.build_storage_backend | pytest tests/unit/UT1_46 | Pass |
| IT1_21 collection-level RBAC (FR-05) | src/index_server/mcp_server.py | per-collection allowed_roles gate; reader denied on writer/admin collection | pytest tests/integration/IT1_21 | Pass |
| IT1_22 api-key resolves key roles (CFG-10) | src/index_tools/tools/service.py | key registered under key-scoped identity carrying key roles | pytest tests/integration/IT1_22 | Pass |
| Regression: unit suite green | current/test-unit-regression-full.log | 200 passed, 0 failed | pytest tests/unit --env tests/env-UT | Pass |
| Quality compliance tier green | current/test-quality-full.log | 47 passed, 0 failed | pytest tests/quality --env tests/env-QT | Pass |
| Integration tier green | current/full-test-suite-results.md | 51 passed, 0 failed | pytest tests/integration --env tests/env-IT | Pass |
| System tier green | current/full-test-suite-results.md | 26 passed, 2 skipped | pytest tests/system --env tests/env-ST | Pass |
| Application tier green | current/full-test-suite-results.md | 24 passed, 0 failed | pytest tests/application --env tests/env-AT | Pass |
| Contract/parser/security tiers green | current/full-test-suite-results.md | 4/3/6 passed, 0 failed | pytest tests/{contract,parser,security} | Pass |
| Docs/tests agree on tool inventory (FR-16A) | docs/MCP_DOCUMENTATION.md | 77 tools catalogued incl structure family | pytest tests/unit/UT1_40 | Pass |
| Remote push proof | current/remote-proof.txt | branch + tags on GitLab at HEAD | git ls-remote origin | Pass |
| Checksums verify | current/CHECKSUMS.sha256 | 26 files OK, 0 failed | sha256sum -c CHECKSUMS.sha256 | Pass |
