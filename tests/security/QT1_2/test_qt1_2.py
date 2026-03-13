# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
