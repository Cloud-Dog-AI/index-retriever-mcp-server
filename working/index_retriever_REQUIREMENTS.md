# Requirements — index-retriever-mcp-server

**Version:** 1.1  
**Date:** 2026-02-26  
**Standards:** PS-00, PS-10, PS-20, PS-40, PS-50, PS-60, PS-70, PS-75, PS-80, PS-90, PS-95  
**Platform packages:** `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_jobs`, `cloud_dog_llm`, `cloud_dog_vdb`

---

## 1. Purpose

`index-retriever-mcp-server` is an **API-first** service that exposes indexing and retrieval capabilities for agentic flows via:
- MCP-compatible **A2A tools**,
- an **HTTP API** (canonical interface),
- an **Admin WebUI**.

The service is a wrapper/orchestrator that manages profiles/collections, jobs, RBAC and audit, and delegates core ingestion (including parsing/OCR/tables/chunking) to `cloud_dog_vdb`. fileciteturn4file0

---

## 2. Responsibilities (refactor)

### 2.1 Responsibilities of index-retriever
- Profile/collection CRUD at runtime (control plane).
- RBAC enforcement (via `cloud_dog_idam`) for profiles/collections/tools.
- Job submission and monitoring (via `cloud_dog_jobs`).
- Audit and operational logging (via `cloud_dog_logging`).
- Presenting APIs/tools/WebUI for:
  - ingest, preview, extract-only,
  - search/retrieve,
  - maintenance (retention/reindex),
  - diagnostics (backend/provider health).

### 2.2 Responsibilities of `cloud_dog_vdb`
Index-retriever MUST NOT re-implement:
- parser chain selection (MinerU/DeepDoc/Docling/marker-mcp/Pandoc/internal readers),
- OCR subsystem and heuristics,
- table extraction policies and table chunk kinds,
- Document IR/provenance model,
- boundary-aware chunking extensions and quality gates,
- connector acquisition primitives in the ingestion pipeline.

---

## 3. Functional Requirements (delta)

### FR-09 Conversion and parsing (delegated)
- Index-retriever SHALL invoke `cloud_dog_vdb` ingestion pipeline to perform:
  - parsing/conversion via configured parser chains,
  - OCR where configured,
  - table handling as configured,
  - IR generation, quality gates, and chunking.
- Index-retriever SHALL surface parser controls and diagnostics through its own API and MCP tools.

### FR-16 Management operations (extend)
Admin/maintainer tools SHALL include:
- manage parser policies per profile/collection (as config blocks),
- run `ingest_preview` and `extract_only`,
- test parser endpoints and OCR providers (connectivity + sample run).

---

## 4. Tool Catalogue (additions)

Index-retriever SHALL expose (thin wrappers over `cloud_dog_vdb` pipeline components):
- `parsers_list`
- `parser_test`
- `ingest_preview`
- `extract_only`
- `ocr_run` (admin/maintainer by default)
- `table_extract` (admin/maintainer)

---

## 5. Acceptance Criteria (delta)

1. Parser/OCR/table capabilities are configurable per profile/collection and persist via runtime CRUD.
2. Preview mode returns chosen parser chain, OCR decision, and chunk plan deterministically.
3. Each ingest job audit record includes parser chain, OCR provider, table policy, chunker version.
4. Index-retriever codebase contains no bespoke parser implementation; it delegates to `cloud_dog_vdb`.
