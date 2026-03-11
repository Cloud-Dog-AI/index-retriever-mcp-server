# index-retriever-mcp-server — UT1.39
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Coverage tests for canonical runtime config loader paths.

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from index_tools.config import loader


def test_normalise_env_files_handles_none_scalars_and_sequence() -> None:
    assert loader._normalise_env_files(None) == []
    assert loader._normalise_env_files(" tests/env-UT-local-docker ") == ["tests/env-UT-local-docker"]
    assert loader._normalise_env_files(Path("tests/env-ST-local-docker")) == ["tests/env-ST-local-docker"]
    assert loader._normalise_env_files(
        [
            " tests/env-IT-local-docker ",
            "",
            "   ",
            Path("tests/env-AT-local-docker"),
        ]
    ) == [
        "tests/env-IT-local-docker",
        "tests/env-AT-local-docker",
    ]


def test_load_runtime_config_delegates_to_canonical_loader(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}
    expected = object()

    def _fake_load_config(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(data={"runtime": "ok"})

    def _fake_bind_model(config_data: dict[str, str]) -> object:
        assert config_data == {"runtime": "ok"}
        return expected

    monkeypatch.setattr(loader, "load_config", _fake_load_config)
    monkeypatch.setattr(loader, "bind_model", _fake_bind_model)

    result = loader.load_runtime_config(
        env_files=[
            Path("tests/env-UT-local-docker"),
            " tests/env-ST-local-docker ",
        ],
        config_yaml=Path("config.custom.yaml"),
        defaults_yaml=Path("defaults.custom.yaml"),
        unresolved_policy="strict",
        vault_enabled=False,
    )

    assert result is expected
    assert captured == {
        "env_files": [
            "tests/env-UT-local-docker",
            "tests/env-ST-local-docker",
        ],
        "config_yaml": "config.custom.yaml",
        "defaults_yaml": "defaults.custom.yaml",
        "unresolved_policy": "strict",
        "vault_enabled": False,
    }


def test_get_config_uses_runtime_loader_when_defaults_layer_missing(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}
    expected = object()

    def _fake_load_runtime_config(**kwargs: Any) -> object:
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(loader, "load_runtime_config", _fake_load_runtime_config)

    result = loader.get_config(
        env_files="tests/env-UT-local-docker",
        config_yaml="config.runtime.yaml",
        defaults_yaml="defaults.runtime.yaml",
        unresolved_policy="strict",
        vault_enabled=False,
    )

    assert result is expected
    assert captured == {
        "env_files": "tests/env-UT-local-docker",
        "config_yaml": "config.runtime.yaml",
        "defaults_yaml": "defaults.runtime.yaml",
        "unresolved_policy": "strict",
        "vault_enabled": False,
    }
