# index-retriever-mcp-server — Deduplication
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Deduplication strategies and policy handling.

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module
from typing import Any

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
        return sha256(content).hexdigest()

    def check_duplicate(self, candidate: DedupeRecord, mode: str) -> DedupeRecord | None:
        """Execute check duplicate."""
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
