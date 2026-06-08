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

from urllib.parse import urlparse

from cloud_dog_config import get_config
from cloud_dog_storage.backends.webdav import WebDavStorage
from cloud_dog_storage.config.models import StorageConfig, WebDavConfig
from cloud_dog_storage.errors import ConfigurationError
from cloud_dog_storage.factory import build_storage_backend

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    """Execute resolve."""
    parsed = urlparse(uri)
    if parsed.scheme not in {"webdav", "webdavs", "http", "https"}:
        raise ValueError("Invalid WebDAV URI")
    return FetchPlan(source_type="webdav", location=uri, metadata={"host": parsed.netloc})


def _cfg(field: str) -> str:
    """Resolve a WebDAV connector config value via cloud_dog_config (env/Vault-backed)."""
    for key in (f"connectors.webdav.{field}", f"storage.webdav.{field}"):
        try:
            value = get_config(key)
        except Exception:
            value = None
        if value not in (None, ""):
            return str(value).strip()
    return ""


def fetch(plan: FetchPlan, *, timeout_seconds: float = 30.0) -> bytes:
    """Fetch a WebDAV object through the cloud_dog_storage WebDAV backend (RULES §1.4).

    The server ``base_url`` and credentials resolve from platform config
    (``storage.webdav.*`` / ``connectors.webdav.*``); the object path comes from the
    resolved plan. Raises ``ConfigurationError`` when the backend is not configured.
    """
    base_url = _cfg("base_url")
    if not base_url:
        raise ConfigurationError("WebDAV fetch requires storage.webdav.base_url", backend_name="webdav")
    config = WebDavConfig(base_url=base_url, username=_cfg("username"), password=_cfg("password"))
    backend = build_storage_backend(StorageConfig(backend="webdav", webdav=config, timeout_s=int(timeout_seconds)))
    object_path = urlparse(plan.location).path or "/"
    return backend.read_bytes(object_path)


def build_storage(
    base_url: str,
    *,
    username: str = "",
    password: str = "",
) -> WebDavStorage:
    """Build a cloud_dog_storage WebDAV backend from connection parameters.

    This adapter allows callers to use the platform storage interface for
    WebDAV read/write operations instead of bespoke HTTP calls.
    """
    config = WebDavConfig(base_url=base_url, username=username, password=password)
    return WebDavStorage(config)
