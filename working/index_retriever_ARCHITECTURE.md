# index-retriever-mcp-server Architecture

**Version:** 1.1  
**Date:** 2026-02-26  
**Standards:** PS-00, PS-10, PS-20, PS-40, PS-50, PS-60, PS-70, PS-75, PS-80, PS-90, PS-95  
**Platform packages:** `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_jobs`, `cloud_dog_llm`, `cloud_dog_vdb`

---

## 1. Overview

Index-retriever is an API-first service that orchestrates configuration, access control, and job scheduling around shared ingestion/search capabilities in `cloud_dog_vdb`. fileciteturn4file1

**Key refactor:** parser/OCR/table/chunking implementation lives in `cloud_dog_vdb`; index-retriever consumes it via stable APIs and config.

---

## 2. Updated Repository Layout

```
repo/
  REQUIREMENTS.md
  ARCHITECTURE.md
  defaults.yaml
  config.yaml
  src/
    index_tools/
      config/                       # cloud_dog_config + runtime persisted profile blocks
      admin/                        # profile/collection CRUD and diagnostics
      orchestration/
        jobs.py                     # cloud_dog_jobs integration
        vdb_facade.py               # calls cloud_dog_vdb runtime client + pipeline
      tools/                        # MCP tool wrappers
    index_retriever_server/
      api_server.py                 # FastAPI via cloud_dog_api_kit
      mcp_server.py                 # MCP transport
      streaming.py                  # SSE/WS for job status + stream ingestion sessions
      auth/                         # cloud_dog_idam
      webui/                        # admin UI
  tests/
    unit/
    integration/
    application/
    security/
```

---

## 3. Operational Flow

1. AuthN/AuthZ via `cloud_dog_idam`
2. Resolve profile/collection config (includes `cloud_dog_vdb` ingestion policy blocks)
3. Enqueue job via `cloud_dog_jobs`
4. Worker executes `cloud_dog_vdb` pipeline:
   - acquire → parse/OCR/tables → IR → chunk → embed → upsert
5. Audit via `cloud_dog_logging`
6. Results and diagnostics exposed via HTTP API + MCP tools
