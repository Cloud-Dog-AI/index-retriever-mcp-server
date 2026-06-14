---
lane: W28C-1711
service: index-retriever-mcp-server
date: 2026-06-14T19:26:47Z
---

# index-retriever-mcp-server — W28C-1711 Knowledge Preservation Delta

## Per-test SHA chain (additive marker swap only)

- Test files in `tests/`: 165
- Files with probe markers swapped to req(): 2
- Probes mechanically bound to req('FR/CS-NNN'): 20
- Probes retained for operator review (no confident FR match): 361

## Attestation

- No test logic mutation in this lane (marker-only change).
- No archive content modified.
- No CI-critical files modified.
- No fake tests authored (operator-review required for new tests per FR/CS with no existing coverage).
- W28C-1710a recovered topics still PRESENT in canonical docs (1710b precondition verified at lane start).

**lines-removed: 0** (probe → req() in-place swap is N-replace-with-M-character, not line-level removal)
**topics-lost: 0** · **W28C-1710a recovered topics: PRESENT YES**
