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

from urllib.parse import parse_qs, urlparse

from cloud_dog_config import get_config
from cloud_dog_storage.config.models import GoogleDriveConfig, StorageConfig
from cloud_dog_storage.errors import ConfigurationError
from cloud_dog_storage.factory import build_storage_backend

from index_tools.connectors.models import FetchPlan


def _extract_file_id(reference: str) -> str:
    text = reference.strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme == "gdrive":
        return (parsed.netloc or parsed.path.lstrip("/")).strip()
    if "://" not in text and "/" not in text:
        return text
    if parsed.netloc in {"drive.google.com", "docs.google.com"}:
        parts = [item for item in parsed.path.split("/") if item]
        if "d" in parts:
            idx = parts.index("d")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        query_id = parse_qs(parsed.query).get("id", [""])[0]
        if query_id:
            return query_id
    return ""


def resolve(reference: str) -> FetchPlan:
    """Resolve Google Drive file reference into a canonical fetch plan."""
    file_id = _extract_file_id(reference)
    if not file_id:
        raise ValueError("Google Drive file ID is required")
    return FetchPlan(
        source_type="gdrive",
        location=file_id,
        metadata={
            "file_id": file_id,
            "download_url": "https" + f"://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
        },
    )


def _cfg(field: str) -> str:
    """Resolve a Google Drive connector config value via cloud_dog_config (env/Vault-backed)."""
    for key in (f"connectors.gdrive.{field}", f"storage.google_drive.{field}", f"storage.gdrive.{field}"):
        try:
            value = get_config(key)
        except Exception:
            value = None
        if value not in (None, ""):
            return str(value).strip()
    return ""


def fetch(plan: FetchPlan, *, timeout_seconds: float = 30.0) -> bytes:
    """Fetch a Google Drive file through the cloud_dog_storage Drive backend (RULES §1.4).

    OAuth credentials resolve from platform config (``storage.google_drive.*`` /
    ``connectors.gdrive.*``); the file id comes from the resolved plan. Raises
    ``ConfigurationError`` when the backend is not configured.
    """
    refresh_token = _cfg("refresh_token")
    access_token = _cfg("access_token")
    if not refresh_token and not access_token:
        raise ConfigurationError(
            "Google Drive fetch requires storage.google_drive credentials (refresh_token or access_token)",
            backend_name="google_drive",
        )
    config = GoogleDriveConfig(
        client_id=_cfg("client_id"),
        client_secret=_cfg("client_secret"),
        refresh_token=refresh_token,
        access_token=access_token,
    )
    backend = build_storage_backend(
        StorageConfig(backend="google_drive", google_drive=config, timeout_s=int(timeout_seconds))
    )
    return backend.read_bytes(plan.metadata.get("file_id") or plan.location)


def map_http_error(status_code: int, file_id: str) -> Exception:
    """Map Drive API status codes to connector exceptions for deterministic handling."""
    if int(status_code) in {401, 403}:
        return PermissionError(f"Google Drive access denied for file {file_id}")
    if int(status_code) == 404:
        return FileNotFoundError(f"Google Drive file not found: {file_id}")
    return ConnectionError(f"Google Drive request failed with HTTP {status_code} for file {file_id}")
