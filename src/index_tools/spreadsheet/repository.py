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

"""Persistence for the spreadsheet indexing control plane (Excel requirements §14).

A thin repository over the ``cloud_dog_db`` session; all SQL is expressed via the
ORM models in :mod:`index_tools.spreadsheet.sql_models`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cloud_dog_vdb.spreadsheet.manifest import RefreshDecision
from cloud_dog_vdb.spreadsheet.model import ObjectManifestEntry
from sqlalchemy import select
from sqlalchemy.orm import Session

from index_tools.spreadsheet.sql_models import (
    SpreadsheetBackendSyncState,
    SpreadsheetChunk,
    SpreadsheetIndexError,
    SpreadsheetIndexJob,
    SpreadsheetObject,
    SpreadsheetRefreshManifest,
    SpreadsheetSource,
    SpreadsheetSourceVersion,
)


def _now() -> datetime:
    return datetime.now(UTC)


class SpreadsheetMetadataRepository:
    """Read/write helper for the spreadsheet control-plane tables (§14)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_source(self, source_uri: str, source_type: str, tenant_id: str) -> SpreadsheetSource:
        stmt = select(SpreadsheetSource).where(
            SpreadsheetSource.source_uri == source_uri,
            SpreadsheetSource.tenant_id == tenant_id,
        )
        source = self.session.execute(stmt).scalar_one_or_none()
        if source is None:
            source = SpreadsheetSource(source_uri=source_uri, source_type=source_type, tenant_id=tenant_id)
            self.session.add(source)
            self.session.flush()
        return source

    def start_job(self, source: SpreadsheetSource, job_type: str = "index") -> SpreadsheetIndexJob:
        job = SpreadsheetIndexJob(
            source_id=source.id, job_type=job_type, status="running", started_at=_now(), stats_json={}
        )
        self.session.add(job)
        self.session.flush()
        return job

    def latest_previous_version(self, source: SpreadsheetSource) -> SpreadsheetSourceVersion | None:
        stmt = (
            select(SpreadsheetSourceVersion)
            .where(SpreadsheetSourceVersion.source_id == source.id)
            .order_by(SpreadsheetSourceVersion.id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def add_version(
        self,
        source: SpreadsheetSource,
        *,
        file_hash: str,
        version_hash: str,
        size_bytes: int,
        parser_version: str,
    ) -> SpreadsheetSourceVersion:
        version = SpreadsheetSourceVersion(
            source_id=source.id,
            file_hash=file_hash,
            version_hash=version_hash,
            size_bytes=size_bytes,
            parser_version=parser_version,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def objects_for_version(self, version_id: int) -> list[SpreadsheetObject]:
        stmt = select(SpreadsheetObject).where(SpreadsheetObject.source_version_id == version_id)
        return list(self.session.execute(stmt).scalars())

    def record_object(self, version: SpreadsheetSourceVersion, entry: ObjectManifestEntry) -> SpreadsheetObject:
        obj = SpreadsheetObject(
            source_version_id=version.id,
            object_type=entry.object_type,
            object_key=entry.object_key,
            parent_object_key=entry.parent_object_key,
            sheet_name=entry.sheet_name,
            table_name=entry.table_name,
            range_ref=entry.range_ref,
            object_hash=entry.object_hash,
            metadata_json={},
        )
        self.session.add(obj)
        self.session.flush()
        return obj

    def record_chunk(
        self,
        obj: SpreadsheetObject,
        *,
        chunk_key: str,
        backend_name: str,
        backend_record_id: str,
        text_hash: str,
        embedding_profile: str,
        metadata: dict[str, Any],
    ) -> SpreadsheetChunk:
        chunk = SpreadsheetChunk(
            object_id=obj.id,
            chunk_key=chunk_key,
            backend_name=backend_name,
            backend_record_id=backend_record_id,
            text_hash=text_hash,
            embedding_profile=embedding_profile,
            metadata_json=metadata,
        )
        self.session.add(chunk)
        return chunk

    def record_refresh(
        self,
        source: SpreadsheetSource,
        previous_version_id: int | None,
        current_version_id: int,
        decision: RefreshDecision,
    ) -> None:
        self.session.add(
            SpreadsheetRefreshManifest(
                source_id=source.id,
                previous_source_version_id=previous_version_id,
                current_source_version_id=current_version_id,
                object_key=decision.object_key,
                previous_object_hash=decision.previous_object_hash,
                current_object_hash=decision.current_object_hash,
                refresh_action=decision.refresh_action,
                reason=decision.reason,
            )
        )

    def record_sync_state(
        self,
        version: SpreadsheetSourceVersion,
        *,
        backend_name: str,
        upserted: int,
        deleted: int,
        status: str = "complete",
    ) -> None:
        self.session.add(
            SpreadsheetBackendSyncState(
                source_version_id=version.id,
                backend_name=backend_name,
                sync_status=status,
                last_synced_at=_now(),
                upserted_record_count=upserted,
                deleted_record_count=deleted,
            )
        )

    def record_error(
        self,
        job: SpreadsheetIndexJob,
        *,
        severity: str,
        stage: str,
        object_key: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        self.session.add(
            SpreadsheetIndexError(
                job_id=job.id,
                severity=severity,
                stage=stage,
                object_key=object_key,
                message=message,
                details_json=details,
            )
        )

    def update_source_hash(self, source: SpreadsheetSource, file_hash: str) -> None:
        source.last_seen_hash = file_hash
        self.session.add(source)

    def finish_job(
        self,
        job: SpreadsheetIndexJob,
        *,
        status: str,
        stats: dict[str, Any],
        warning_count: int,
        error_summary: str = "",
    ) -> None:
        job.status = status
        job.finished_at = _now()
        job.stats_json = dict(stats)
        job.warning_count = warning_count
        job.error_summary = error_summary
        self.session.add(job)
