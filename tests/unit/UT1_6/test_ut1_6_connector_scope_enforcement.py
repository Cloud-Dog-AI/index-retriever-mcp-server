# index-retriever-mcp-server — UT1.6
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests connector filesystem scope enforcement.

from pathlib import Path

import pytest

from index_tools.security.scope import ScopeError, resolve_scoped_path


def test_scope_blocks_escape(tmp_path: Path) -> None:
    allowed = str(tmp_path)
    inside = tmp_path / "a.txt"
    inside.write_text("x", encoding="utf-8")
    assert resolve_scoped_path([allowed], str(inside)) == inside.resolve()

    with pytest.raises(ScopeError):
        resolve_scoped_path([allowed], "/etc/passwd")
