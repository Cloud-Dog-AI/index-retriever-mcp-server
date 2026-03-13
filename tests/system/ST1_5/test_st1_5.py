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

# index-retriever-mcp-server — ST1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live reference-style ingest pipeline.

from pathlib import Path

from tests.live_runtime import LiveIndexRuntime


def test_ingest_reference_pipeline(live_service: LiveIndexRuntime, tmp_path: Path) -> None:
    path = tmp_path / "reference-doc.txt"
    path.write_text("reference material body", encoding="utf-8")
    rec = live_service.ingest_reference(
        profile="default",
        collection="st_ref",
        path=str(path),
        actor="system",
    )
    rows = live_service.search("default", "st_ref", "reference")
    assert rows
    assert rows[0]["id"] == rec.record_id
