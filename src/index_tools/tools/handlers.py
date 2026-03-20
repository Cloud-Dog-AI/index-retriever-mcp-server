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

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from index_tools.tools.definitions import IngestOutput, SearchInput, SearchOutput, SearchResult


def handle_search(input_data: SearchInput, search_fn: Callable[..., list[dict[str, Any]]]) -> SearchOutput:
    """Execute handle search."""
    rows = search_fn(
        collection=input_data.collection,
        query=input_data.query,
        top_k=input_data.top_k,
        filters=input_data.filters,
    )
    results = [SearchResult.model_validate(row) for row in rows]
    return SearchOutput(results=results)


def handle_ingest_text() -> IngestOutput:
    """Execute handle ingest text."""
    return IngestOutput(job_id=str(uuid.uuid4()), status="queued")
