# index-retriever-mcp-server — UT1.10
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests S3 connector URI parsing.

from index_tools.connectors.s3 import resolve


def test_connector_s3_resolve() -> None:
    plan = resolve("s3://bucket/path/file.txt")
    assert plan.source_type == "s3"
    assert plan.metadata["bucket"] == "bucket"
    assert plan.metadata["key"] == "path/file.txt"
