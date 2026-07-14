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

"""W28E-1870-A unit tests for the VDB change-watch criteria matcher (FR-019)."""

from __future__ import annotations

import pytest
from cloud_dog_api_kit.change_stream.errors import InvalidCriteria

from index_tools.change_stream.criteria import ChangeCandidate, match, validate_criteria

pytestmark = [pytest.mark.UT, pytest.mark.internal]


def _cand(**kw):
    base = dict(collection="docs", action="ingested", object_ref="d1")
    base.update(kw)
    return ChangeCandidate(**base)


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("FR-019")
def test_empty_criteria_matches_all():
    m = match({}, _cand())
    assert m == {"all": True}


@pytest.mark.req("FR-019")
def test_collection_criterion_exact_and_list():
    assert match({"collection": "docs"}, _cand(collection="docs")) is not None
    assert match({"collection": "docs"}, _cand(collection="other")) is None
    assert match({"collection": ["a", "docs"]}, _cand(collection="docs")) is not None


@pytest.mark.req("FR-019")
def test_action_criterion():
    assert match({"action": ["ingested", "deleted"]}, _cand(action="deleted")) is not None
    assert match({"action": "ingested"}, _cand(action="deleted")) is None


@pytest.mark.req("FR-019")
def test_source_uri_glob_and_regex():
    c = _cand(source_uri="https://a.example.com/reports/q1.pdf")
    assert match({"source_uri": "*://*.example.com/reports/*"}, c) is not None
    assert match({"source_uri": "re:reports/q[0-9]+\\.pdf$"}, c) is not None
    assert match({"source_uri": "*://other.net/*"}, c) is None


@pytest.mark.req("FR-019")
def test_source_domain_criterion():
    c = _cand(source_uri="https://user:pw@docs.example.com:8443/a")
    assert match({"source_domain": "docs.example.com"}, c) is not None
    assert match({"source_domain": ["x.net", "docs.example.com"]}, c) is not None
    assert match({"source_domain": "example.com"}, c) is None


@pytest.mark.req("FR-019")
def test_title_and_language_and_text():
    c = _cand(title="Quarterly Report", language="en", text="revenue grew 12% year over year")
    assert match({"title": "Quarterly*"}, c) is not None
    assert match({"language": "en"}, c) is not None
    assert match({"language": ["fr", "de"]}, c) is None
    assert match({"text": "re:grew [0-9]+%"}, c) is not None
    assert match({"text": "*missing phrase*"}, c) is None


@pytest.mark.req("FR-019")
def test_metadata_keys_and_values():
    c = _cand(metadata={"doc_id": "d1", "embedding_model": "nomic", "lifecycle_state": "active"})
    assert match({"metadata_keys": ["doc_id", "embedding_model"]}, c) is not None
    assert match({"metadata_keys": ["absent_key"]}, c) is None
    assert match({"metadata": {"lifecycle_state": "active"}}, c) is not None
    assert match({"metadata": {"lifecycle_state": "deleted"}}, c) is None
    assert match({"metadata": {"embedding_model": "re:^nomic"}}, c) is not None


@pytest.mark.req("FR-019")
def test_combined_criteria_all_must_match():
    c = _cand(collection="docs", action="ingested", language="en", title="Report")
    ok = match({"collection": "docs", "action": "ingested", "language": "en"}, c)
    assert ok is not None
    # one failing criterion fails the whole watch
    assert match({"collection": "docs", "language": "fr"}, c) is None


@pytest.mark.req("FR-019")
def test_criteria_match_provenance_is_recorded():
    c = _cand(collection="docs", action="ingested", source_uri="https://x.io/a")
    m = match({"collection": "docs", "action": "ingested", "source_domain": "x.io"}, c)
    assert m["collection"] == "docs"
    assert m["action"] == "ingested"
    assert m["source_domain"] == "x.io"


@pytest.mark.req("FR-019")
def test_validate_rejects_unknown_field():
    with pytest.raises(InvalidCriteria):
        validate_criteria({"bogus": 1})


@pytest.mark.req("FR-019")
def test_validate_rejects_unknown_action_verb():
    with pytest.raises(InvalidCriteria):
        validate_criteria({"action": "exploded"})


@pytest.mark.req("FR-019")
def test_validate_rejects_bad_regex():
    with pytest.raises(InvalidCriteria):
        validate_criteria({"title": "re:([unclosed"})
