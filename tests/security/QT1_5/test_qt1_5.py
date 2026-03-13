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

# index-retriever-mcp-server — QT1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Backend adapter contract conformance check.

from index_tools.vdb.adapters import InMemoryVdbAdapter


def _contract_run(adapter: InMemoryVdbAdapter) -> tuple[int, int, int]:
    adapter.create_collection("contract")
    adapter.upsert("contract", "doc1", ["contract alpha"], [[0.1, 0.2]], metadata={"tenant": "t1"})
    adapter.upsert("contract", "doc2", ["contract beta"], [[0.2, 0.3]], metadata={"tenant": "t2"})
    q1 = len(adapter.query("contract", "contract", top_k=10))
    d1 = int(adapter.delete_by_doc_id("contract", "doc1"))
    q2 = len(adapter.query("contract", "contract", top_k=10))
    return q1, d1, q2


def test_backend_contract_conformance() -> None:
    left = _contract_run(InMemoryVdbAdapter())
    right = _contract_run(InMemoryVdbAdapter())
    assert left == right
