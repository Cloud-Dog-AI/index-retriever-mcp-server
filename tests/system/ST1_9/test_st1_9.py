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

from tests.live_runtime import LiveIndexRuntime


def test_delete_by_filter(live_service: LiveIndexRuntime) -> None:
    live_service.ingest_text(
        "default",
        "st_delete_filter",
        "delete me",
        "api://del/f1",
        actor="system",
        metadata={"tag": "drop"},
    )
    live_service.ingest_text(
        "default",
        "st_delete_filter",
        "keep me",
        "api://del/f2",
        actor="system",
        metadata={"tag": "keep"},
    )
    removed = live_service.delete_by_filter("default", "st_delete_filter", {"tag": "drop"})
    assert removed >= 1
