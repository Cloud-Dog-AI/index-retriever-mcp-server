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

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from cloud_dog_vdb.metadata.identity import compute_content_hash

try:
    xxhash_module: Any = import_module("xxhash")
except ImportError:  # pragma: no cover
    xxhash_module = None


@dataclass(slots=True)
class DedupeRecord:
    """DedupeRecord definition."""

    doc_id: str
    size: int
    mtime: int
    fingerprint: str


class DedupeIndex:
    """In-memory dedupe index for policy decisions."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self._records: dict[str, DedupeRecord] = {}

    @staticmethod
    def fingerprint(content: bytes, method: str = "sha256") -> str:
        """Execute fingerprint."""
        if method == "xxhash" and xxhash_module is not None:
            return str(xxhash_module.xxh64(content).hexdigest())
        return compute_content_hash(content.decode("utf-8", errors="replace"))

    def check_duplicate(self, candidate: DedupeRecord, mode: str) -> DedupeRecord | None:
        """Execute check duplicate."""
        # Covers: FR-11
        if mode == "size+mtime":
            for existing in self._records.values():
                if existing.size == candidate.size and existing.mtime == candidate.mtime:
                    return existing
            return None
        for existing in self._records.values():
            if existing.fingerprint == candidate.fingerprint:
                return existing
        return None

    def apply_policy(self, existing: DedupeRecord | None, policy: str) -> str:
        """Execute apply policy."""
        if existing is None:
            return "ingest"
        if policy == "skip":
            return "skip"
        if policy == "replace":
            return "replace"
        if policy == "version":
            return "version"
        raise ValueError(f"Unsupported dedupe policy: {policy}")

    def upsert(self, record: DedupeRecord) -> None:
        """Execute upsert."""
        self._records[record.doc_id] = record
