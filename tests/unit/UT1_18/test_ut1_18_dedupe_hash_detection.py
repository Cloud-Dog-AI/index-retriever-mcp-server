# index-retriever-mcp-server — UT1.18
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests dedupe hash detection.

from index_tools.pipeline.dedupe import DedupeIndex, DedupeRecord


def test_dedupe_hash_detection() -> None:
    dedupe = DedupeIndex()
    fingerprint = dedupe.fingerprint(b"hello")
    existing = DedupeRecord(doc_id="doc1", size=5, mtime=1, fingerprint=fingerprint)
    dedupe.upsert(existing)
    candidate = DedupeRecord(doc_id="doc2", size=5, mtime=2, fingerprint=fingerprint)
    assert dedupe.check_duplicate(candidate, mode="hash") == existing
