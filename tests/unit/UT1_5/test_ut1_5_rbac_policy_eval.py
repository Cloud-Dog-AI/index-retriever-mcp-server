# index-retriever-mcp-server — UT1.5
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests RBAC policy evaluation.

from index_tools.security.rbac import RbacAuthoriser, Subject


def test_rbac_policy_eval() -> None:
    authz = RbacAuthoriser({"writer": ["ingest_*"], "reader": ["search"]})
    subject = Subject(user_id="u1", roles={"writer"})
    assert authz.is_allowed(subject, "ingest_text") is True
    assert authz.is_allowed(subject, "admin_profile_create") is False
