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

from index_tools.connectors.filesystem import resolve
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_connector_filesystem_resolve(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    target.write_text("hello", encoding="utf-8")
    plan = resolve([str(tmp_path)], str(target))
    assert plan.source_type == "filesystem"
    assert plan.location.endswith("doc.txt")
