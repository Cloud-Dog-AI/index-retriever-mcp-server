# index-retriever-mcp-server — UT1.11
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests WebDAV connector URI parsing.

from index_tools.connectors.webdav import resolve


def test_connector_webdav_resolve() -> None:
    plan = resolve("webdav://docs.example.com/path")
    assert plan.source_type == "webdav"
    assert plan.metadata["host"] == "docs.example.com"
