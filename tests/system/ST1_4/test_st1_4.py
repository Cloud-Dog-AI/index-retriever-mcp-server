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

# index-retriever-mcp-server — ST1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live text ingest pipeline to Chroma.

from tests.live_runtime import LiveIndexRuntime


def test_ingest_text_pipeline(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text("default", "st_text", "alpha beta gamma", "api://inline", actor="system")
    found = live_service.retrieve("default", "st_text", rec.record_id)
    assert found is not None
