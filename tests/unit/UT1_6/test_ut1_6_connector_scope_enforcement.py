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
