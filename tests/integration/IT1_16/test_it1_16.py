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


def test_delegation_boundary_via_cloud_dog_vdb_pipeline(live_service: LiveIndexRuntime) -> None:
    preview = live_service.ingest_preview(
        text="column_a|column_b\n1|2\n3|4",
        source_uri="file://integration/table-doc.txt",
        parser_chain=["internal"],
        ocr_mode="auto",
        table_policy="table_as_json",
    )
    assert preview["parser_provider"] == "internal"
    assert preview["table_policy"] == "table_as_json"
    assert preview["chunk_count"] >= 1
    assert any(step["stage"] == "parse" for step in preview["checkpoints"])

    extract = live_service.extract_only(
        text="Delegated extract payload for parser boundary verification",
        source_uri="file://integration/extract-doc.txt",
        parser_chain=["internal"],
    )
    assert extract["parser_provider"] == "internal"
    assert extract["chunk_count"] >= 1

    tables = live_service.table_extract(
        text="col1|col2\nleft|right",
        source_uri="file://integration/table-only.txt",
        parser_chain=["internal"],
        table_policy="table_as_json",
    )
    assert tables["parser_provider"] == "internal"
    assert tables["table_count"] >= 1
