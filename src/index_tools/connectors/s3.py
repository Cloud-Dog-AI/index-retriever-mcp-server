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
from cloud_dog_storage.config.models import S3Config, StorageConfig
from cloud_dog_storage.factory import build_storage_backend

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    """Execute resolve."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError("Invalid S3 URI")
    key = parsed.path.lstrip("/")
    return FetchPlan(source_type="s3", location=uri, metadata={"bucket": parsed.netloc, "key": key})


def _cfg(field: str) -> str:
    """Resolve an S3 connector config value via cloud_dog_config (env/Vault-backed)."""
    for key in (f"connectors.s3.{field}", f"storage.s3.{field}"):
        try:
            value = get_config(key)
        except Exception:
            value = None
        if value not in (None, ""):
            return str(value).strip()
    return ""


def fetch(plan: FetchPlan, *, timeout_seconds: float = 30.0) -> bytes:
    """Fetch an S3 object through the cloud_dog_storage S3 backend (RULES §1.4).

    Endpoint/region/credentials resolve from platform config (``storage.s3.*`` /
    ``connectors.s3.*``); bucket/key come from the resolved plan. Raises
    cloud_dog_storage ``ConfigurationError`` when the backend is not configured.
    """
    s3_config = S3Config(
        endpoint=_cfg("endpoint"),
        bucket=plan.metadata.get("bucket", "") or _cfg("bucket"),
        region=_cfg("region") or "us-east-1",
        access_key=_cfg("access_key"),
        secret_key=_cfg("secret_key"),
    )
    backend = build_storage_backend(StorageConfig(backend="s3", s3=s3_config, timeout_s=int(timeout_seconds)))
    return backend.read_bytes(plan.metadata.get("key", ""))
