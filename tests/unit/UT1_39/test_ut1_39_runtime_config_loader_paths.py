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
    # Covers: FR-02
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
        secret_backend_enabled=False,
    )

    assert result is expected
    # The public param is `secret_backend_enabled` (W28A-861 zero-Vault-dependency
    # rename); the loader maps it to the canonical load_config `vault_enabled` kwarg
    # via secret_backend_kwarg(), so load_config still receives `vault_enabled`.
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
        secret_backend_enabled=False,
    )

    assert result is expected
    # get_config forwards the public `secret_backend_enabled` param verbatim to
    # load_runtime_config (the rename mapping to `vault_enabled` happens one layer
    # deeper, inside load_runtime_config -> load_config).
    assert captured == {
        "env_files": "tests/env-UT-local-docker",
        "config_yaml": "config.runtime.yaml",
        "defaults_yaml": "defaults.runtime.yaml",
        "unresolved_policy": "strict",
        "secret_backend_enabled": False,
    }
