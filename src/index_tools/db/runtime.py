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

"""cloud_dog_db runtime integration for index-retriever-mcp-server."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from cloud_dog_storage import path_utils
from cloud_dog_db import (
    DatabaseSettings,
    MigrationRunner,
    SyncSessionManager,
    build_sync_engine,
    probe_database,
)
from cloud_dog_db.migrations.runner import MigrationConfig
from filelock import FileLock
from index_tools.config.loader import runtime_env_files, secret_backend_kwarg
from sqlalchemy import Engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError


@dataclass(slots=True)
class PlatformDatabaseRuntime:
    settings: DatabaseSettings
    engine: Engine
    session_manager: SyncSessionManager
    migration_runner: MigrationRunner


_RUNTIME_LOCK = Lock()
_RUNTIME: PlatformDatabaseRuntime | None = None


def _project_root() -> Path:
    current = path_utils.as_path(path_utils.resolve_path(__file__))
    for candidate in current.parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return current.parents[4]


def _default_sqlite_path() -> str:
    return "./data/index_retriever.db"


def _env_value(*names: str) -> str | None:
    import os

    process_env = dict(os.environ)
    for name in names:
        value = str(process_env.get(name, "")).strip()
        if value:
            return value
        converted = name.replace("__", ".").lower()
        value = str(process_env.get(converted, "")).strip()
        if value:
            return value

    try:
        from cloud_dog_config import get_config, load_config  # type: ignore
    except ImportError:
        return None

    for name in names:
        try:
            cfg_val = get_config(name)
        except Exception:
            cfg_val = None
        if cfg_val is not None:
            value = str(cfg_val).strip()
            if value:
                return value
        converted = name.replace("__", ".").lower()
        try:
            cfg_val = get_config(converted)
        except Exception:
            cfg_val = None
        if cfg_val is not None:
            value = str(cfg_val).strip()
            if value:
                return value
    try:
        compiled = load_config(
            env_files=runtime_env_files(),
            unresolved_policy="strict",
            **secret_backend_kwarg(False),
        )
    except Exception:
        compiled = None
    if compiled is None:
        return None
    for name in names:
        for candidate in (name, name.replace("__", ".").lower()):
            try:
                value = str(compiled.get(candidate) or "").strip()
            except Exception:
                value = ""
            if value:
                return value
    return None


_SEP = "://"
_URL_REWRITES: tuple[tuple[str, str], ...] = (
    (f"sqlite+aiosqlite{_SEP}", f"sqlite+pysqlite{_SEP}"),
    (f"postgresql+asyncpg{_SEP}", f"postgresql+psycopg{_SEP}"),
    (f"mysql+aiomysql{_SEP}", f"mysql+pymysql{_SEP}"),
)


def _normalise_sync_url(raw_url: str) -> str:
    url = raw_url.strip()
    for async_prefix, sync_prefix in _URL_REWRITES:
        if url.startswith(async_prefix):
            return sync_prefix + url[len(async_prefix):]
    return url


def _settings_from_env() -> DatabaseSettings:
    explicit_url = _env_value(
        "CLOUD_DOG__DB__URL",
        "CLOUD_DOG_DB__URL",
        "CLOUD_DOG__INDEX__DB__URL",
        "INDEX_RETRIEVER_DB_URL",
        "DB_URL",
    )
    if explicit_url:
        return DatabaseSettings(url=_normalise_sync_url(explicit_url))

    payload: dict[str, Any] = {}
    env_map = {
        "dialect": ("CLOUD_DOG_DB__DIALECT", "CLOUD_DOG__DB__DIALECT"),
        "driver": ("CLOUD_DOG_DB__DRIVER", "CLOUD_DOG__DB__DRIVER"),
        "host": ("CLOUD_DOG_DB__HOST", "CLOUD_DOG__DB__HOST"),
        "port": ("CLOUD_DOG_DB__PORT", "CLOUD_DOG__DB__PORT"),
        "username": ("CLOUD_DOG_DB__USERNAME", "CLOUD_DOG__DB__USERNAME"),
        "password": ("CLOUD_DOG_DB__PASSWORD", "CLOUD_DOG__DB__PASSWORD"),
        "database": ("CLOUD_DOG_DB__DATABASE", "CLOUD_DOG__DB__DATABASE"),
        "path": ("CLOUD_DOG_DB__PATH", "CLOUD_DOG__DB__PATH"),
        "schema_name": ("CLOUD_DOG_DB__SCHEMA", "CLOUD_DOG__DB__SCHEMA"),
    }
    for field, names in env_map.items():
        value = _env_value(*names)
        if value is not None:
            payload[field] = value
    if not payload:
        payload = {
            "dialect": "sqlite",
            "database": _default_sqlite_path(),
        }
    elif not str(payload.get("database") or "").strip() and not str(payload.get("url") or "").strip():
        payload["database"] = _default_sqlite_path()
    return DatabaseSettings.model_validate(payload)


def _sqlite_path(settings: DatabaseSettings) -> Path | None:
    url = make_url(settings.to_sync_url())
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database or url.database == ":memory:":
        return None
    path = path_utils.as_path(url.database)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _migration_script_location() -> str:
    return str((_project_root() / "database" / "migrations" / "cloud_dog_db").resolve())


def _is_existing_table_error(exc: OperationalError) -> bool:
    message = str(exc).lower()
    return "table" in message and "already exists" in message


def _run_migrations(runner: MigrationRunner, sqlite_path: Path | None) -> None:
    def upgrade_with_retry() -> None:
        try:
            runner.upgrade("head")
        except OperationalError as exc:
            if sqlite_path is None or not _is_existing_table_error(exc):
                raise
            runner.upgrade("head")

    if sqlite_path is None:
        upgrade_with_retry()
        return

    lock = FileLock(f"{sqlite_path}.migrate.lock")
    with lock:
        upgrade_with_retry()


def initialise_database(*, force_reinit: bool = False) -> PlatformDatabaseRuntime:
    """Initialise engine/session/migrations through cloud_dog_db."""
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is not None and not force_reinit:
            return _RUNTIME

        settings = _settings_from_env()
        sqlite_path = _sqlite_path(settings)
        if sqlite_path is not None:
            path_utils.mkdir(str(sqlite_path.parent))

        engine = build_sync_engine(settings)
        session_manager = SyncSessionManager(engine)
        runner = MigrationRunner(
            MigrationConfig(
                script_location=_migration_script_location(),
                sqlalchemy_url=settings.to_sync_url(),
            )
        )
        _run_migrations(runner, sqlite_path)

        # W28A-876 Gate 4b: ensure the canonical cloud_dog_idam role tables exist
        # so the PS-71 §IW3A Roles page (/api/v1/admin/roles) is backed by the
        # shared SqlAlchemyRoleStore. Only the role-related tables are created
        # here; other idam tables are not part of this service's schema.
        from cloud_dog_idam.storage.sqlalchemy.models import (  # type: ignore[import-not-found,import-untyped]
            PermissionORM as _PermissionORM,
            RoleORM as _RoleORM,
            RolePermissionORM as _RolePermissionORM,
        )
        _RoleORM.metadata.create_all(
            bind=engine,
            checkfirst=True,
            tables=[
                _RoleORM.__table__,
                _PermissionORM.__table__,
                _RolePermissionORM.__table__,
            ],
        )

        _RUNTIME = PlatformDatabaseRuntime(
            settings=settings,
            engine=engine,
            session_manager=session_manager,
            migration_runner=runner,
        )
        return _RUNTIME


def database_health(runtime: PlatformDatabaseRuntime | None = None) -> dict[str, Any]:
    """Return DB probe details for health handlers."""
    active = runtime or _RUNTIME
    if active is None:
        return {"ok": False, "status": "not_initialised"}
    try:
        probe = probe_database(active.engine)
        return {"ok": bool(probe.get("ok", False)), "probe": probe}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def shutdown_database() -> None:
    """Dispose database engine."""
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            return
        _RUNTIME.engine.dispose()
        _RUNTIME = None
