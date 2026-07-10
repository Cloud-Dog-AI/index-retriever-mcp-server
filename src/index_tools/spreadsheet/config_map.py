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

"""Map resolved service configuration to a ``SpreadsheetConfig`` (Excel §5.15).

The caller resolves values through ``cloud_dog_config`` and passes a plain
mapping; this module never reads the environment itself (RULES §1.4).
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from cloud_dog_vdb.spreadsheet.config import SpreadsheetConfig

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _coerce(default: Any, value: Any) -> Any:
    if isinstance(default, bool):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
        return bool(value)
    if isinstance(default, int) and not isinstance(default, bool):
        return int(value)
    if isinstance(default, float):
        return float(value)
    if isinstance(default, list):
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return list(value)
    return str(value)


def build_spreadsheet_config(overrides: dict[str, Any] | None = None) -> SpreadsheetConfig:
    """Build a validated :class:`SpreadsheetConfig` from optional overrides (§5.15)."""
    config = SpreadsheetConfig()
    known = {f.name: getattr(config, f.name) for f in fields(SpreadsheetConfig)}
    for key, value in (overrides or {}).items():
        if value is None or key not in known:
            continue
        setattr(config, key, _coerce(known[key], value))
    config.validate()
    return config
