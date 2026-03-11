# index-retriever-mcp-server — Config Loader
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Config loading and model binding via cloud_dog_config integration.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import cloud_dog_config  # type: ignore
from cloud_dog_config import load_config  # type: ignore

from index_tools.config.models import GlobalConfig


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


def load_runtime_config(
    *,
    env_files: str | Path | Sequence[str | Path] | None = None,
    config_yaml: str | Path = "config.yaml",
    defaults_yaml: str | Path = "defaults.yaml",
    unresolved_policy: str = "strict",
    vault_enabled: bool = True,
) -> GlobalConfig:
    """Load runtime config via canonical cloud_dog_config.load_config semantics."""
    resolved = load_config(
        env_files=_normalise_env_files(env_files),
        config_yaml=str(config_yaml),
        defaults_yaml=str(defaults_yaml),
        unresolved_policy=unresolved_policy,
        vault_enabled=vault_enabled,
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
    vault_enabled: bool = True,
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
        vault_enabled=vault_enabled,
    )
