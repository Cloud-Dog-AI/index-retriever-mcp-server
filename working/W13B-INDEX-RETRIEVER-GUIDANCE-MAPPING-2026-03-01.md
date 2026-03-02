# W13B Guidance Mapping — Index-Retriever (2026-03-01)

Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W13B-INDEX-RETRIEVER-VDB-0.4.1-ADOPTION-STRICT.md`  
Guidance inputs reviewed:
- `working/index_retriever_REQUIREMENTS.md`
- `working/index_retriever_ARCHITECTURE.md`

## Disposition Summary

- `ADOPTED`: 9
- `DEFERRED`: 1
- `REJECTED`: 1

## Proposal Mapping

| Guidance proposal | Disposition | Rationale | Resulting canonical references |
|---|---|---|---|
| Keep index-retriever control-plane focused (profile/collection CRUD, RBAC, jobs, audit) | ADOPTED | Matches project standards and existing architecture direction | `REQUIREMENTS.md` (FR-13A), `ARCHITECTURE.md` (3.4, 3.7A), `src/index_tools/tools/service.py` |
| Remove local parser/OCR/table internals and delegate to `cloud_dog_vdb` | ADOPTED | Required by W13B responsibility boundary and implemented via thin wrappers | `REQUIREMENTS.md` (FR-13A), `ARCHITECTURE.md` (3.4, 5.4), `src/index_tools/tools/service.py` |
| Add MCP/API thin-wrapper tools: `parsers_list`, `parser_test`, `ingest_preview`, `extract_only`, `ocr_run`, `table_extract` | ADOPTED | Implemented in service/definitions/registry/MCP dispatch with RBAC mapping | `REQUIREMENTS.md` (7.6), `src/index_tools/tools/definitions.py`, `src/index_tools/tools/registry.py`, `src/index_server/mcp_server.py`, `tests/integration/IT1_17/test_it1_17.py` |
| Preserve metadata round-trip (`source_uri`, `filename`, `mime_type`) across ingest and retrieval/search | ADOPTED | Implemented in ingest metadata path and validated in IT/AT | `REQUIREMENTS.md` (FR-13A), `src/index_tools/pipeline/metadata.py`, `src/index_tools/tools/service.py`, `tests/integration/IT1_13/test_it1_13.py`, `tests/application/AT1_7/test_at1_7.py` |
| Capability-aware backend planning with explicit negative path for unsupported filters | ADOPTED | Implemented in `search_plan` and live runtime capability planner; tested in IT/UT | `REQUIREMENTS.md` (FR-13A), `ARCHITECTURE.md` (3.7A), `src/index_tools/tools/service.py`, `tests/integration/IT1_14/test_it1_14.py`, `tests/unit/UT1_36/test_ut1_36_service_vdb041_branches.py` |
| Provider diagnostic propagation with secret-safe envelope | ADOPTED | Implemented with redacted diagnostic envelope objects in service/runtime and tested in QT/UT | `REQUIREMENTS.md` (FR-13A), `ARCHITECTURE.md` (3.7A), `src/index_tools/tools/service.py`, `tests/security/QT1_6/test_qt1_6.py`, `tests/unit/UT1_36/test_ut1_36_service_vdb041_branches.py` |
| Add Infinity backend adoption path when env-configured | ADOPTED | Implemented in live runtime config/registration and contract/integration tests | `REQUIREMENTS.md` (FR-13A), `ARCHITECTURE.md` (3.7A), `tests/live_runtime.py`, `tests/contract/CT1_4/test_ct1_4_infinity_contract.py`, `tests/integration/IT1_15/test_it1_15.py` |
| Expand strict test coverage for metadata/capability/delegation/wrapper/diagnostic paths | ADOPTED | Added IT/CT/AT/QT and UT closure tests; strict tiers pass with real runtime | `TESTS.md` (Latest W13B Status), `tests/integration/IT1_13..IT1_17`, `tests/contract/CT1_4`, `tests/application/AT1_7`, `tests/security/QT1_6`, `tests/unit/UT1_36`, `tests/unit/UT1_37` |
| Update canonical docs (`REQUIREMENTS.md`, `ARCHITECTURE.md`, `TESTS.md`) for W13B traceability | ADOPTED | Required by instruction and completed | `REQUIREMENTS.md`, `ARCHITECTURE.md`, `TESTS.md` |
| Persist parser policy blocks per profile/collection CRUD with full runtime storage semantics | DEFERRED | Current W13B scope delivered parser wrappers and execution path; persistent parser policy schema/storage contract needs dedicated profile model/API migration | Deferred to follow-on closeout wave (`W14A-04`) |
| Adopt proposed sample repository layout verbatim from guidance (`index_retriever_server/`, `orchestration/vdb_facade.py` etc.) | REJECTED | Guidance input is non-authoritative and conflicts with existing repository/module structure; no functional requirement mandates a structural rename | Existing canonical module layout retained in `src/index_server` and `src/index_tools` |
