# index-retriever-mcp-server — Config Loader
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Config loading and model binding via cloud_dog_config integration.

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import cloud_dog_config  # type: ignore

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


def get_config(
    defaults_layer: Mapping[str, Any],
    config_layer: Mapping[str, Any] | None = None,
    dot_env_layer: Mapping[str, Any] | None = None,
    env_layer: Mapping[str, Any] | None = None,
) -> GlobalConfig:
    """Get merged configuration using cloud_dog_config."""
    merged = merge_config_layers(
        defaults_layer=defaults_layer,
        config_layer=config_layer,
        dot_env_layer=dot_env_layer,
        env_layer=env_layer,
    )
    return bind_model(merged)
