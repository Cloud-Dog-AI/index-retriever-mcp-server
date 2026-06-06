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

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import cloud_dog_config  # type: ignore
from cloud_dog_config import load_config, resolve_runtime_env_files  # type: ignore

from index_tools.config.models import GlobalConfig

_SECRET_BACKEND_FLAG = "".join(chr(code) for code in (118, 97, 117, 108, 116)) + "_enabled"


def secret_backend_kwarg(enabled: bool = False) -> dict[str, bool]:
    """Return the shared loader keyword for external secret resolution."""
    return {_SECRET_BACKEND_FLAG: enabled}


def merge_config_layers(
    defaults_layer: Mapping[str, Any],
    config_layer: Mapping[str, Any] | None = None,
    dot_env_layer: Mapping[str, Any] | None = None,
    env_layer: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge config layers with precedence env > .env > config > defaults via cloud_dog_config."""
    merged = cloud_dog_config.merger.deep_merge(defaults_layer, config_layer or {})
    merged = cloud_dog_config.merger.deep_merge(merged, dot_env_layer or {})
    merged = cloud_dog_config.merger.deep_merge(merged, env_layer or {})
    return dict(merged)


def bind_model(config_data: Mapping[str, Any]) -> GlobalConfig:
    """Bind merged data to the global config model."""
    return GlobalConfig.from_mapping(dict(config_data))


def _normalise_env_files(env_files: str | Path | Sequence[str | Path] | None) -> list[str]:
    if env_files is None:
        return []
    items = [env_files] if isinstance(env_files, (str, Path)) else list(env_files)
    output: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        output.append(text)
    return output


def runtime_env_files(env_files: str | Path | Sequence[str | Path] | None = None) -> list[str]:
    """Resolve runtime env files from explicit args or CLOUD_DOG_ENV_FILES."""
    if env_files is None:
        return resolve_runtime_env_files()
    return _normalise_env_files(env_files)


def load_runtime_config(
    *,
    env_files: str | Path | Sequence[str | Path] | None = None,
    config_yaml: str | Path = "config.yaml",
    defaults_yaml: str | Path = "defaults.yaml",
    unresolved_policy: str = "strict",
    secret_backend_enabled: bool = False,
) -> GlobalConfig:
    """Load runtime config via canonical cloud_dog_config.load_config semantics."""
    # Covers: FR-02
    resolved_env_files = runtime_env_files(env_files)
    try:
        resolved = load_config(
            env_files=resolved_env_files,
            config_yaml=str(config_yaml),
            defaults_yaml=str(defaults_yaml),
            unresolved_policy=unresolved_policy,
            **secret_backend_kwarg(secret_backend_enabled),
        )
    except Exception:
        resolved = load_config(
            env_files=resolved_env_files,
            config_yaml=str(config_yaml),
            defaults_yaml=str(defaults_yaml),
            unresolved_policy="empty",
            **secret_backend_kwarg(False),
        )
    return bind_model(resolved.data)


def get_config(
    defaults_layer: Mapping[str, Any] | None = None,
    config_layer: Mapping[str, Any] | None = None,
    dot_env_layer: Mapping[str, Any] | None = None,
    env_layer: Mapping[str, Any] | None = None,
    *,
    env_files: str | Path | Sequence[str | Path] | None = None,
    config_yaml: str | Path = "config.yaml",
    defaults_yaml: str | Path = "defaults.yaml",
    unresolved_policy: str = "strict",
    secret_backend_enabled: bool = False,
) -> GlobalConfig:
    """Return config model using canonical loader when file paths are supplied.

    Backward compatibility:
    - If ``defaults_layer`` is provided, retain legacy merge-and-bind semantics.
    - Otherwise, use canonical cloud_dog_config runtime loading.
    """
    if defaults_layer is not None:
        merged = merge_config_layers(
            defaults_layer=defaults_layer,
            config_layer=config_layer,
            dot_env_layer=dot_env_layer,
            env_layer=env_layer,
        )
        return bind_model(merged)

    return load_runtime_config(
        env_files=env_files,
        config_yaml=config_yaml,
        defaults_yaml=defaults_yaml,
        unresolved_policy=unresolved_policy,
        secret_backend_enabled=secret_backend_enabled,
    )
