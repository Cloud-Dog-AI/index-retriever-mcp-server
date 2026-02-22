# index-retriever-mcp-server — QT1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Connector scope escape is blocked.

from pathlib import Path

import pytest

from index_tools.security.scope import ScopeError, resolve_scoped_path


def test_connector_scope_escape(tmp_path: Path) -> None:
    inside = tmp_path / "inside.txt"
    inside.write_text("ok", encoding="utf-8")
    assert resolve_scoped_path([str(tmp_path)], str(inside)) == inside.resolve()

    with pytest.raises(ScopeError):
        resolve_scoped_path([str(tmp_path)], "/etc/shadow")
