# index-retriever-mcp-server — UT1.21
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests dedupe replace policy.

from index_tools.pipeline.dedupe import DedupeIndex, DedupeRecord


def test_dedupe_policy_replace() -> None:
    dedupe = DedupeIndex()
    existing = DedupeRecord(doc_id="doc1", size=1, mtime=1, fingerprint="x")
    assert dedupe.apply_policy(existing, "replace") == "replace"
