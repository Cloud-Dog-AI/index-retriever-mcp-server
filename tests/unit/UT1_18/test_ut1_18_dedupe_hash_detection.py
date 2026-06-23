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

from index_tools.pipeline.dedupe import DedupeIndex, DedupeRecord
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-011") # W28E-1805A semantic binding


def test_dedupe_hash_detection() -> None:
    # Covers: FR-11
    dedupe = DedupeIndex()
    fingerprint = dedupe.fingerprint(b"hello")
    existing = DedupeRecord(doc_id="doc1", size=5, mtime=1, fingerprint=fingerprint)
    dedupe.upsert(existing)
    candidate = DedupeRecord(doc_id="doc2", size=5, mtime=2, fingerprint=fingerprint)
    assert dedupe.check_duplicate(candidate, mode="hash") == existing
