# index-retriever-mcp-server — UT1.22
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests dedupe version policy.

from index_tools.pipeline.dedupe import DedupeIndex, DedupeRecord


def test_dedupe_policy_version() -> None:
    dedupe = DedupeIndex()
    existing = DedupeRecord(doc_id="doc1", size=1, mtime=1, fingerprint="x")
    assert dedupe.apply_policy(existing, "version") == "version"
