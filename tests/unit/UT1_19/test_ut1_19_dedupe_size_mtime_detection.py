# index-retriever-mcp-server — UT1.19
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests dedupe size and mtime detection.

from index_tools.pipeline.dedupe import DedupeIndex, DedupeRecord


def test_dedupe_size_mtime_detection() -> None:
    dedupe = DedupeIndex()
    existing = DedupeRecord(doc_id="doc1", size=10, mtime=22, fingerprint="a")
    dedupe.upsert(existing)
    candidate = DedupeRecord(doc_id="doc2", size=10, mtime=22, fingerprint="b")
    assert dedupe.check_duplicate(candidate, mode="size+mtime") == existing
