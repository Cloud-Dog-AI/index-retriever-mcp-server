# index-retriever-mcp-server — UT1.20
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests dedupe skip policy.

from index_tools.pipeline.dedupe import DedupeIndex, DedupeRecord


def test_dedupe_policy_skip() -> None:
    dedupe = DedupeIndex()
    existing = DedupeRecord(doc_id="doc1", size=1, mtime=1, fingerprint="x")
    assert dedupe.apply_policy(existing, "skip") == "skip"
