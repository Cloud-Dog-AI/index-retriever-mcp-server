# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import pytest

from index_tools.connectors.resolver import fetch_source, resolve_source
from index_tools.tools.service import IndexService


def test_w28c427r5_connector_resolver_matrix(tmp_path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("connector matrix", encoding="utf-8")

    cases = [
        (str(sample), "filesystem"),
        ("https://example.com/source.txt", "http"),
        ("s3://bucket/key.txt", "s3"),
        ("webdav://dav.example.com/files/source.txt", "webdav"),
        ("ftp://ftp.example.com/files/source.txt", "ftp"),
        ("gdrive://1AbCdEfGhIjKlMnOpQrStUvWxYz", "gdrive"),
        ("https://drive.google.com/file/d/1ABCDEF/view?usp=sharing", "gdrive"),
    ]
    for uri, expected in cases:
        plan = resolve_source(uri, allowed_roots=[str(tmp_path)])
        assert plan.source_type == expected

    assert fetch_source(resolve_source(str(sample), allowed_roots=[str(tmp_path)])) == b"connector matrix"
    for uri in ("s3://bucket/key.txt", "webdav://dav.example.com/files/source.txt", "gdrive://1AbCdEfGhIjKlMnOpQrStUvWxYz"):
        with pytest.raises(NotImplementedError, match="requires backend credentials"):
            _ = fetch_source(resolve_source(uri, allowed_roots=[str(tmp_path)]))

    with pytest.raises(ValueError, match="Unsupported source scheme"):
        _ = resolve_source("ssh://example.com/source.txt", allowed_roots=[str(tmp_path)])


def test_w28c427r5_source_config_policy_gate_rejects_unsupported_before_fetch(service: IndexService) -> None:
    with pytest.raises(ValueError, match="Unsupported source type"):
        service.admin_source_config_create(
            source_id="bad-scheme",
            roles={"admin"},
            payload={
                "source_type": "ssh",
                "uri": "ssh://example.com/source.txt",
                "profile": "default",
                "collection": "default",
            },
        )
    with pytest.raises(ValueError, match="Google Drive file ID is required"):
        service.admin_source_config_create(
            source_id="bad-gdrive",
            roles={"admin"},
            payload={
                "source_type": "gdrive",
                "uri": "https://example.com/not-drive",
                "profile": "default",
                "collection": "default",
            },
        )
    created = service.admin_source_config_create(
        source_id="good-gdrive",
        roles={"admin"},
        payload={
            "source_type": "gdrive",
            "uri": "gdrive://1AbCdEfGhIjKlMnOpQrStUvWxYz",
            "profile": "default",
            "collection": "default",
        },
    )
    assert created["source_type"] == "gdrive"
