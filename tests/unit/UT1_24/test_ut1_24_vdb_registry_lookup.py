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

from index_tools.vdb.adapters import InMemoryVdbAdapter
from index_tools.vdb.registry import VdbRegistry


def test_vdb_registry_lookup() -> None:
    # Covers: FR-13
    registry = VdbRegistry()
    registry.register("chroma", InMemoryVdbAdapter)
    adapter = registry.get("chroma")
    assert isinstance(adapter, InMemoryVdbAdapter)
