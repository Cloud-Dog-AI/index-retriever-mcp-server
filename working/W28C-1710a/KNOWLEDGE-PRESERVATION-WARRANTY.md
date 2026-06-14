---
lane: W28C-1710a
service: index-retriever-mcp-server
date: 2026-06-14T17:37:15Z
---

# index-retriever-mcp-server — Knowledge Preservation Warranty (W28C-1710a)

## Programme summary for this service

| Metric | Value |
|---|---:|
| Archived docs merged | 1 |
| Total archived-lines carried forward | 52 |
| Topics preserved (PRESENT) | 10 |
| Topics lost (residual) | 0 |
| Successor docs updated | 1 |
| Lines added to successor docs | +61 |
| Lines removed from successor docs | -0 |
| **residual-loss-lines** | **0** |

## Per-doc SHA256 chain (successor pre/post)

| Successor canonical | pre-sha256(12) | post-sha256(12) | pre-lines | post-lines | +lines | -lines | residual-loss-lines |
|---|---|---|---:|---:|---:|---:|---:|
| `docs/API-REFERENCE.md` | `088e9d589738` | `128206411afa` | 52 | 113 | +61 | -0 | 0 |

## Per-archived-doc topic preservation

| Archived | archived-lines | archived-sha256(12) | Successor | topics-recorded | topics-present | residual-loss-topics |
|---|---:|---|---|---:|---:|---:|
| `archive/2026-06-12/API.md` | 52 | `e5e1750394d0` | `docs/API-REFERENCE.md` | 10 | 10 | 0 |

## Attestation

I warrant that:

1. Every archived doc under `index-retriever-mcp-server/archive/2026-06-12/` has been merged verbatim into the named successor canonical doc(s) — full content preserved as a marked `## Recovered domain content` section.
2. Archive contents have NOT been modified during this lane (sha256 of every archived file matches the pre-merge fingerprint).
3. No successor doc had any line removed during this lane (delta-lines-removed = 0 per row).
4. residual-loss-lines = 0 for this service.
5. No `tests/` file modified; no CI-critical file modified.
6. Per-doc topic checklists at `cloud-dog-ai-platform-standards/working/evidence/W28C-1710a/per-doc/index-retriever-mcp-server/<archived-name>.topics.tsv` — every row marked PRESENT.

**HAVE_ALL_REQUIREMENTS_BEEN_MET_FOR_INDEX_RETRIEVER_MCP_SERVER_RECOVERY**: YES

---
Operator countersignature: ___________________________ Date: __________
