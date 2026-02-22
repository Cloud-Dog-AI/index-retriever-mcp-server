# index-retriever-mcp-server — UT1.12
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests converter registry backend selection.

from index_tools.convert.registry import ConverterRegistry


def test_convert_registry_selection() -> None:
    reg = ConverterRegistry()
    reg.register(".txt", lambda b: b.decode("utf-8"))
    selected = reg.select(".txt")
    assert selected(b"hello") == "hello"
