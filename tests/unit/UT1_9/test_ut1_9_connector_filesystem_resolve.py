# index-retriever-mcp-server — UT1.9
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests filesystem connector resolution.

from pathlib import Path

from index_tools.connectors.filesystem import resolve


def test_connector_filesystem_resolve(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    target.write_text("hello", encoding="utf-8")
    plan = resolve([str(tmp_path)], str(target))
    assert plan.source_type == "filesystem"
    assert plan.location.endswith("doc.txt")
