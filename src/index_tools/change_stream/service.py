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

"""Index-retriever VDB change-watch adapter (PS-102 §4.5, CSTREAM-IR-001/002).

``WatchService`` is a *thin adapter* over the common change-stream foundation
published in ``cloud_dog_api_kit.change_stream`` (PS-102 §9 / RULES §1.4). It:

* builds a :class:`~cloud_dog_api_kit.change_stream.WatchCoordinator` whose
  per-watch journal is the durable :class:`SqlJournal` (backed by the service's
  ``cloud_dog_db`` engine) so a watch backlog survives restart (CSTREAM-007);
* wires the coordinator's ``on_emit`` hook to the service's existing
  ``cloud_dog_api_kit.a2a.events`` broadcaster via ``make_broadcast_hook`` for
  live SSE fan-out (PS-102 §5.2) — no bespoke broadcaster;
* wires the coordinator's ``audit_sink`` to ``cloud_dog_logging`` (CSTREAM-010);
* enforces RBAC/tenancy at the adapter boundary via ``cloud_dog_idam`` — a watch
  is scoped to a tenant + VDB profile; cross-tenant reads are a hard failure
  (CSTREAM-009);
* translates observed VDB mutations (ingest / lifecycle delete / supersede /
  collection create-delete) into the canonical :class:`ChangeEvent` envelope and
  emits them to every *live* watch whose criteria match (CSTREAM-IR-001/002).

This adapter re-implements NO journal, cursor, queue, broadcaster, RBAC, or error
model — all of that is consumed from the foundation.
"""

from __future__ import annotations

import contextlib
import threading
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from cloud_dog_api_kit.change_stream import (
    ACTIONS,
    ChangeEvent,
    WatchCoordinator,
    WatchSpec,
    make_broadcast_hook,
)
from cloud_dog_api_kit.change_stream.db_journal import SqlJournal
from cloud_dog_api_kit.change_stream.errors import (
    InvalidCriteria,
    WatchNotFound,
)
from cloud_dog_api_kit.change_stream.journal import InMemoryJournal, Journal

from index_tools.change_stream.criteria import (
    ChangeCandidate,
    validate_criteria,
)
from index_tools.change_stream.criteria import (
    match as criteria_match,
)

SERVICE_ID = "index-retriever"
_SOURCE_TYPE = "vdb_collection"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WatchService:
    """Per-service change-watch adapter binding the common coordinator to VDB ops.

    Args:
        service_id: stable service identifier for the envelope (``index-retriever``).
        engine: an optional SQLAlchemy ``Engine`` (from ``cloud_dog_db``). When
            supplied, watches journal durably via :class:`SqlJournal`; when
            ``None`` (unit tests / no DB), a bounded in-memory journal is used so
            the adapter still functions without a live database.
        broadcaster: an optional ``cloud_dog_api_kit.a2a.events`` broadcaster; when
            supplied, emitted events fan out live via ``make_broadcast_hook``.
        audit_sink: optional ``(kind, mapping)`` callable — the service wires
            ``cloud_dog_logging`` here.
        broadcast_scheduler: optional scheduler for the (async) broadcast publish
            so the sync emit path never blocks a worker (CSTREAM-002).
    """

    def __init__(
        self,
        *,
        service_id: str = SERVICE_ID,
        engine: Any | None = None,
        broadcaster: Any | None = None,
        audit_sink: Callable[[str, Mapping[str, Any]], None] | None = None,
        broadcast_scheduler: Callable[[Any], None] | None = None,
    ) -> None:
        self._service_id = service_id
        self._engine = engine
        self._lock = threading.RLock()
        # watch_id -> declarative spec view (tenant/profile/criteria) kept for
        # criteria evaluation + RBAC scoping. The coordinator owns state/journal.
        self._specs: dict[str, WatchSpec] = {}
        self._criteria: dict[str, Mapping[str, Any]] = {}

        on_emit = None
        if broadcaster is not None:
            on_emit = make_broadcast_hook(broadcaster, scheduler=broadcast_scheduler)

        # Ensure the durable journal table exists once (idempotent).
        if engine is not None:
            with contextlib.suppress(Exception):  # pragma: no cover - schema may already exist
                SqlJournal.create_schema(engine)

        self._coordinator = WatchCoordinator(
            journal_factory=self._journal_factory,
            on_emit=on_emit,
            audit_sink=audit_sink,
        )

    # ------------------------------------------------------------------
    # journal factory (durable SqlJournal, else bounded in-memory)
    # ------------------------------------------------------------------
    def _journal_factory(self, spec: WatchSpec) -> Journal:
        if self._engine is not None:
            return SqlJournal(
                self._engine,
                spec.watch_id,
                max_size=spec.journal_max,
                ttl_seconds=spec.journal_ttl_seconds,
            )
        return InMemoryJournal(max_size=spec.journal_max, ttl_seconds=spec.journal_ttl_seconds)

    @property
    def coordinator(self) -> WatchCoordinator:
        return self._coordinator

    # ------------------------------------------------------------------
    # RBAC / tenancy boundary (CSTREAM-009)
    # ------------------------------------------------------------------
    def _require_owner(self, watch_id: str, tenant_id: str) -> WatchSpec:
        """Return the spec if the caller's tenant owns the watch, else raise.

        Cross-tenant / cross-profile access is a hard failure — the watch is
        scoped to the tenant it was created under (PS-102 §7).
        """
        spec = self._specs.get(watch_id)
        if spec is None:
            raise WatchNotFound(f"no watch {watch_id!r}")
        if tenant_id is not None and spec.tenant_id != tenant_id:
            # Do not leak existence across tenants: report not-found.
            raise WatchNotFound(f"no watch {watch_id!r}")
        return spec

    # ------------------------------------------------------------------
    # lifecycle (create/list/status/pause/resume/delete) — PS-102 §5.1
    # ------------------------------------------------------------------
    def create_watch(
        self,
        *,
        profile_id: str,
        tenant_id: str,
        actor: str,
        criteria: Mapping[str, Any] | None = None,
        max_batch: int = 100,
        max_inflight: int = 4,
        journal_max: int = 1000,
        journal_ttl_seconds: float | None = None,
        watch_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_criteria = dict(criteria or {})
        validate_criteria(resolved_criteria)
        if max_batch < 1 or max_inflight < 1 or journal_max < 1:
            raise InvalidCriteria("max_batch, max_inflight and journal_max must be >= 1")
        wid = watch_id or f"irw-{uuid.uuid4().hex[:16]}"
        spec = WatchSpec(
            watch_id=wid,
            service_id=self._service_id,
            profile_id=profile_id,
            tenant_id=tenant_id,
            actor=actor,
            criteria=resolved_criteria,
            max_batch=max_batch,
            max_inflight=max_inflight,
            journal_max=journal_max,
            journal_ttl_seconds=journal_ttl_seconds,
        )
        with self._lock:
            status = self._coordinator.create_watch(spec)
            self._specs[wid] = spec
            self._criteria[wid] = resolved_criteria
        return self._watch_view(spec, status)

    def list_watches(self, *, tenant_id: str) -> list[dict[str, Any]]:
        with self._lock:
            out: list[dict[str, Any]] = []
            for wid, spec in self._specs.items():
                if spec.tenant_id != tenant_id:
                    continue
                out.append(self._watch_view(spec, self._coordinator.get_status(wid)))
            return out

    def get_watch(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        spec = self._require_owner(watch_id, tenant_id)
        return self._watch_view(spec, self._coordinator.get_status(watch_id))

    def get_status(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.get_status(watch_id))

    def pause(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.pause(watch_id))

    def resume(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.resume(watch_id))

    def delete(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        with self._lock:
            self._coordinator.delete(watch_id)
            self._specs.pop(watch_id, None)
            self._criteria.pop(watch_id, None)
        return {"watch_id": watch_id, "deleted": True}

    # ------------------------------------------------------------------
    # retrieval / ack / recover — PS-102 §5.2 (pull-batch base mode)
    # ------------------------------------------------------------------
    def get_batch(
        self,
        watch_id: str,
        *,
        tenant_id: str,
        since_cursor: str | None = None,
        max_batch: int | None = None,
    ) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        result = self._coordinator.get_batch(watch_id, since_cursor=since_cursor, max_batch=max_batch)
        return WatchCoordinator.batch_to_dict(result, redact=True)

    def ack(self, watch_id: str, *, tenant_id: str, ack_cursor: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.ack(watch_id, ack_cursor))

    def recover(
        self, watch_id: str, *, tenant_id: str, since_cursor: str | None = None
    ) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        cursor = self._coordinator.recover(watch_id, since_cursor=since_cursor)
        return {"watch_id": watch_id, "resume_cursor": cursor}

    def test_event(
        self,
        watch_id: str,
        *,
        tenant_id: str,
        action: str = "created",
        object_ref: str = "test",
        **meta: Any,
    ) -> dict[str, Any]:
        """Inject a deterministic synthetic event (PS-102 §5.8)."""
        self._require_owner(watch_id, tenant_id)
        if action not in ACTIONS:
            raise InvalidCriteria(f"unknown action verb {action!r}")
        seq = self._coordinator.test_event(watch_id, action=action, object_ref=object_ref, **meta)
        return {"watch_id": watch_id, "emitted_seq": seq, "action": action, "object_ref": object_ref}

    # ------------------------------------------------------------------
    # health (PS-102 §5.9) — aggregated for the service /health
    # ------------------------------------------------------------------
    def health(self) -> dict[str, int]:
        with self._lock:
            return self._coordinator.health()

    # ------------------------------------------------------------------
    # domain-event capture (CSTREAM-IR-001) — called by IndexService hooks
    # ------------------------------------------------------------------
    def observe_change(
        self,
        *,
        tenant_id: str,
        collection: str,
        action: str,
        object_ref: str,
        object_version: str = "",
        source_uri: str = "",
        title: str = "",
        language: str = "",
        doc_id: str = "",
        chunk_id: str = "",
        text: str = "",
        metadata: Mapping[str, Any] | None = None,
        actor: str | None = None,
        correlation_id: str | None = None,
        summary: str = "",
    ) -> list[str]:
        """Fan a single observed VDB change into every matching *live* watch.

        Returns the list of watch ids the change was emitted to (may be empty).
        This is the server-mediated capture path (PS-102 §6 native-first): the
        change is captured at the point index-retriever performs the mutation, so
        there is no polling/scan and no busy-wait.
        """
        if action not in ACTIONS:
            # Defensive: an unknown verb is a contract error, but capture must
            # never crash the mutating request path — skip silently.
            return []
        meta = dict(metadata or {})
        candidate = ChangeCandidate(
            collection=collection,
            action=action,
            object_ref=object_ref,
            object_version=object_version,
            source_uri=source_uri or str(meta.get("source_uri", "")),
            title=title or str(meta.get("title", "")),
            language=language or str(meta.get("language", "")),
            doc_id=doc_id or str(meta.get("doc_id", "")),
            chunk_id=chunk_id or str(meta.get("chunk_id", "")),
            text=text,
            metadata=meta,
        )
        emitted: list[str] = []
        # snapshot watch ids under lock; emit outside the lock is fine (coordinator
        # is single-process and its own emit is cheap + bounded).
        with self._lock:
            targets = [
                (wid, spec, self._criteria.get(wid, {}))
                for wid, spec in self._specs.items()
                if spec.tenant_id == tenant_id
            ]
        for wid, spec, crit in targets:
            # only emit to live watches; a paused watch retains its cursor and is
            # not fed new events (PS-102 §5.1).
            status = self._coordinator.get_status(wid)
            if status.state != "live":
                continue
            matched = criteria_match(crit, candidate)
            if matched is None:
                continue
            event = self._build_event(
                spec=spec,
                candidate=candidate,
                criteria_match=matched,
                actor=actor,
                correlation_id=correlation_id,
                summary=summary,
            )
            try:
                self._coordinator.emit(wid, event)
                emitted.append(wid)
            except Exception:  # pragma: no cover - a paused/removed watch races
                continue
        return emitted

    # ------------------------------------------------------------------
    # envelope + view builders
    # ------------------------------------------------------------------
    def _build_event(
        self,
        *,
        spec: WatchSpec,
        candidate: ChangeCandidate,
        criteria_match: Mapping[str, Any],
        actor: str | None,
        correlation_id: str | None,
        summary: str,
    ) -> ChangeEvent:
        # per-service typed metadata extension (PS-102 §4.1 index-retriever row)
        meta = candidate.metadata
        typed_metadata = {
            "collection": candidate.collection,
            "doc_id": candidate.doc_id or str(meta.get("doc_id", "")),
            "chunk_id": candidate.chunk_id or str(meta.get("chunk_id", "")),
            "source_uri": candidate.source_uri,
            "source_domain": _domain(candidate.source_uri),
            "title": candidate.title,
            "language": candidate.language or str(meta.get("language", "")),
            "embedding_model": str(meta.get("embedding_model", "")),
            "lifecycle_state": str(meta.get("lifecycle_state", "")),
        }
        return ChangeEvent(
            watch_id=spec.watch_id,
            service_id=self._service_id,
            profile_id=spec.profile_id,
            source_type=_SOURCE_TYPE,
            source_ref=f"{spec.profile_id}:{candidate.collection}",
            action=candidate.action,
            object_ref=candidate.object_ref,
            object_version=candidate.object_version or candidate.doc_id or candidate.object_ref,
            tenant_id=spec.tenant_id,
            event_time=_utc_now(),
            observed_time=_utc_now(),
            criteria_match=dict(criteria_match),
            summary=summary or _default_summary(candidate),
            metadata=typed_metadata,
            correlation_id=correlation_id,
            actor={"id": actor, "type": "user"} if actor else None,
            provenance={"capture": "server_mediated", "collection": candidate.collection},
        )

    def _watch_view(self, spec: WatchSpec, status: Any) -> dict[str, Any]:
        return {
            "watch_id": spec.watch_id,
            "service_id": spec.service_id,
            "profile_id": spec.profile_id,
            "tenant_id": spec.tenant_id,
            "actor": spec.actor,
            "criteria": dict(spec.criteria),
            "max_batch": spec.max_batch,
            "max_inflight": spec.max_inflight,
            "journal_max": spec.journal_max,
            "journal_ttl_seconds": spec.journal_ttl_seconds,
            "status": self._status_view(status),
        }

    @staticmethod
    def _status_view(status: Any) -> dict[str, Any]:
        return {
            "watch_id": status.watch_id,
            "tenant_id": status.tenant_id,
            "state": status.state,
            "journal_depth": status.depth,
            "earliest_seq": status.earliest_seq,
            "latest_seq": status.latest_seq,
            "ack_seq": status.ack_seq,
            "inflight": status.inflight,
            "throttled": status.throttled,
            "trimmed_total": status.trimmed_total,
        }


def make_audit_sink(audit_logger: Any) -> Callable[[str, Mapping[str, Any]], None]:
    """Build a coordinator ``audit_sink`` that writes to ``cloud_dog_logging``.

    The common :class:`WatchCoordinator` calls ``audit_sink(kind, row)`` for every
    lifecycle / emission / delivery / ack / recover / throttle event (CSTREAM-010).
    This adapter maps each to the service's :class:`AuditLogger.log_admin_action`
    so watch audit lands in the same privileged audit stream as the rest of the
    service — no bespoke audit writer (RULES §1.4).
    """

    def _sink(kind: str, row: Mapping[str, Any]) -> None:
        watch_id = str(row.get("watch_id", ""))
        actor = str(row.get("actor") or "system")
        details = {k: v for k, v in row.items() if k not in {"watch_id", "actor"}}
        with contextlib.suppress(Exception):  # pragma: no cover - audit must never break the flow
            audit_logger.log_admin_action(
                actor=actor,
                roles=set(),
                action=f"change_watch.{kind}",
                target_type="change_watch",
                target_id=watch_id or "-",
                new_value=details or None,
            )

    return _sink


def _domain(uri: str) -> str:
    from urllib.parse import urlparse

    if not uri:
        return ""
    parsed = urlparse(uri)
    if parsed.netloc:
        return parsed.netloc.rsplit("@", 1)[-1].split(":", 1)[0]
    return ""


def _default_summary(candidate: ChangeCandidate) -> str:
    label = candidate.title or candidate.source_uri or candidate.object_ref
    return f"{candidate.action} {candidate.collection}/{label}".strip()
