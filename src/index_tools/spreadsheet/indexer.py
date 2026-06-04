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

"""Spreadsheet indexing orchestration for index-retriever-mcp-server.

Bridges the pure ``cloud_dog_vdb.spreadsheet`` extraction (retrieval plane) and
the ``cloud_dog_db`` control plane: it extracts a workbook, persists the §14
control-plane rows, computes object-aware refresh decisions, and drives backend
upsert/delete via caller-supplied callbacks (so it is backend-neutral and reuses
the service's existing ``cloud_dog_vdb`` client). Stage 1/7/8/9 of the pipeline
(§10) — this layer never re-implements vector adapters or DB plumbing (§1.4).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cloud_dog_vdb.domain.models import Record
from cloud_dog_vdb.spreadsheet import extract_workbook, searchable_records_to_records
from cloud_dog_vdb.spreadsheet.config import SpreadsheetConfig
from cloud_dog_vdb.spreadsheet.manifest import diff_manifests
from cloud_dog_vdb.spreadsheet.model import ObjectManifestEntry

from index_tools.spreadsheet.repository import SpreadsheetMetadataRepository

#: Workbook formats routed to spreadsheet indexing in this phase (§5.1 / §21 Phase 1).
SUPPORTED_SPREADSHEET_EXTENSIONS = ("xlsx", "xlsm", "ods")

UpsertFn = Callable[[list[Record]], None]
DeleteFn = Callable[[list[str]], None]


def is_spreadsheet(file_name: str) -> bool:
    """Return ``True`` if ``file_name`` is a supported spreadsheet workbook."""
    if "." not in file_name:
        return False
    return file_name.rsplit(".", 1)[-1].lower() in SUPPORTED_SPREADSHEET_EXTENSIONS


@dataclass
class SpreadsheetIndexResult:
    """Outcome of a spreadsheet indexing run."""

    status: str
    object_counts: dict[str, int] = field(default_factory=dict)
    upserted: int = 0
    deleted: int = 0
    deleted_keys: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    job_id: int | None = None
    source_id: int | None = None
    version_id: int | None = None


class SpreadsheetIndexer:
    """Extract a workbook, persist §14 control plane, and drive backend sync."""

    def __init__(
        self,
        *,
        session_manager: Any | None = None,
        parser_version: str = "openpyxl/odf-v1",
        batch_size: int = 64,
    ) -> None:
        self._session_manager = session_manager
        self._parser_version = parser_version
        self._batch_size = max(1, batch_size)

    def index(
        self,
        data: bytes,
        *,
        file_name: str,
        source_uri: str,
        upsert: UpsertFn,
        delete: DeleteFn | None = None,
        backend_name: str = "",
        tenant_id: str = "default",
        config: SpreadsheetConfig | None = None,
        base_metadata: dict[str, Any] | None = None,
    ) -> SpreadsheetIndexResult:
        """Index one workbook. ``upsert``/``delete`` apply to the vector backend."""
        extraction = extract_workbook(
            data, file_name=file_name, source_uri=source_uri, config=config, permissions=[]
        )
        records = searchable_records_to_records(extraction.searchable_records, extra_metadata=base_metadata)

        if self._session_manager is None:
            self._upsert_batches(upsert, records)
            return SpreadsheetIndexResult(
                status=extraction.workbook.parse_status,
                object_counts=extraction.object_count_by_type(),
                upserted=len(records),
                warnings=list(extraction.workbook.warnings),
            )

        return self._index_with_control_plane(
            extraction=extraction,
            records=records,
            source_uri=source_uri,
            tenant_id=tenant_id,
            backend_name=backend_name,
            upsert=upsert,
            delete=delete,
        )

    def _index_with_control_plane(
        self,
        *,
        extraction,
        records: list[Record],
        source_uri: str,
        tenant_id: str,
        backend_name: str,
        upsert: UpsertFn,
        delete: DeleteFn | None,
    ) -> SpreadsheetIndexResult:
        workbook = extraction.workbook
        with self._session_manager.session() as session:
            repo = SpreadsheetMetadataRepository(session)
            source = repo.get_or_create_source(source_uri, workbook.file_format or "excel", tenant_id)
            job = repo.start_job(source, "index")

            if workbook.parse_status == "failed":
                repo.record_error(
                    job,
                    severity="error",
                    stage="parse",
                    object_key="",
                    message="; ".join(workbook.warnings) or "parse failed",
                    details={},
                )
                repo.finish_job(
                    job,
                    status="failed",
                    stats=extraction.stats,
                    warning_count=len(workbook.warnings),
                    error_summary="parse failed",
                )
                return SpreadsheetIndexResult(
                    status="failed", warnings=list(workbook.warnings), job_id=job.id, source_id=source.id
                )

            previous_version = repo.latest_previous_version(source)
            version = repo.add_version(
                source,
                file_hash=workbook.file_hash,
                version_hash=workbook.version_hash,
                size_bytes=workbook.size_bytes,
                parser_version=self._parser_version,
            )

            object_rows = {}
            for entry in extraction.manifest:
                object_rows[entry.object_key] = repo.record_object(version, entry)
            for rec in extraction.searchable_records:
                obj = object_rows.get(rec.delete_key)
                if obj is None:
                    continue
                repo.record_chunk(
                    obj,
                    chunk_key=rec.record_id,
                    backend_name=backend_name,
                    backend_record_id=rec.record_id,
                    text_hash=rec.source_hash,
                    embedding_profile=rec.embedding_input_profile,
                    metadata={"object_type": rec.object_type},
                )

            deleted_keys: list[str] = []
            # On the first version every record is upserted; on later versions only
            # new/changed records are (section 5.14 incremental re-index optimisation).
            upsert_keys: set[str] | None = None
            if previous_version is not None:
                previous_entries = [
                    ObjectManifestEntry(
                        object_key=o.object_key, object_type=o.object_type, object_hash=o.object_hash
                    )
                    for o in repo.objects_for_version(previous_version.id)
                ]
                decisions = diff_manifests(previous_entries, extraction.manifest)
                for decision in decisions:
                    repo.record_refresh(source, previous_version.id, version.id, decision)
                deleted_keys = [d.object_key for d in decisions if d.refresh_action == "delete"]
                upsert_keys = {d.object_key for d in decisions if d.refresh_action == "upsert"}

            records_to_upsert = (
                records if upsert_keys is None else [r for r in records if r.record_id in upsert_keys]
            )
            if delete is not None and deleted_keys:
                delete(deleted_keys)
            self._upsert_batches(upsert, records_to_upsert)

            repo.record_sync_state(
                version, backend_name=backend_name, upserted=len(records_to_upsert), deleted=len(deleted_keys)
            )
            repo.update_source_hash(source, workbook.file_hash)
            repo.finish_job(
                job, status="complete", stats=extraction.stats, warning_count=len(workbook.warnings)
            )

            return SpreadsheetIndexResult(
                status="complete",
                object_counts=extraction.object_count_by_type(),
                upserted=len(records_to_upsert),
                deleted=len(deleted_keys),
                deleted_keys=deleted_keys,
                warnings=list(workbook.warnings),
                job_id=job.id,
                source_id=source.id,
                version_id=version.id,
            )

    def _upsert_batches(self, upsert: UpsertFn, records: list[Record]) -> None:
        for start in range(0, len(records), self._batch_size):
            upsert(records[start : start + self._batch_size])
