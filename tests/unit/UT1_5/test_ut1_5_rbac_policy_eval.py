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

from index_tools.security.rbac import RbacAuthoriser, Subject
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_rbac_policy_eval() -> None:
    authz = RbacAuthoriser({"user": ["collection.write"], "viewer": ["collection.read"]})
    subject = Subject(user_id="u1", roles={"user"})
    assert authz.is_allowed(subject, "collection.write") is True
    assert authz.is_allowed(subject, "admin") is False
