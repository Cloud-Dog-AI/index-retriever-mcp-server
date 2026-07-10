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

"""Index-retriever VDB change-watch adapter (PS-102 §4.5 / CSTREAM-IR-001/002).

Thin per-service adapter over the common ``cloud_dog_api_kit.change_stream``
foundation. This package owns ONLY the domain glue (criteria over VDB metadata,
translating VDB mutations to the canonical envelope); the journal, cursor, queue,
broadcaster, and error model are all consumed from the foundation (RULES §1.4).
"""

from __future__ import annotations

from index_tools.change_stream.criteria import (
    ChangeCandidate,
    match,
    validate_criteria,
)
from index_tools.change_stream.service import SERVICE_ID, WatchService, make_audit_sink

__all__ = [
    "WatchService",
    "SERVICE_ID",
    "make_audit_sink",
    "ChangeCandidate",
    "match",
    "validate_criteria",
]
