---
template-id: T-SCM
template-version: 1.0
applies-to: tests/SCOPE-MAP.md
project: index-retriever-mcp-server
doc-last-updated: 2026-06-23T00:00:00Z
doc-git-branch: coordinator/20260622-agent-converge/index-retriever-main-merge
doc-age-policy: 30d
doc-conformance-stamp: 2026-06-23T00:00:00Z
---

# index-retriever-mcp-server - Test scope map

## Mapping

| Source glob | Test IDs |
|---|---|
| `src/index_server/api_server.py` | `T-UT-UT1-31`, `T-UT-UT1-35`, `T-IT-IT1-1`, `T-IT-IT1-18`, `T-AT-AT-WEBUI-SECURITYADMIN` |
| `src/index_server/mcp_server.py` | `T-UT-UT1-29`, `T-UT-UT1-31`, `T-UT-UT1-37`, `T-UT-UT1-40`, `T-SMOKE-TOOLS` |
| `src/index_server/a2a*.py` | `T-UT-UT1-38`, `T-IT-IT1-18`, `T-IT-IT-W28E603-PHASE25` |
| `src/index_server/auth/**` | `T-UT-UT1-5`, `T-UT-UT1-31`, `T-IT-IT1-21`, `T-QT-QT-COMPLIANCE` |
| `src/index_tools/tools/**` | `T-UT-UT1-33`, `T-UT-UT1-34`, `T-UT-UT1-36`, `T-UT-UT1-37`, `T-IT-IT1-17`, `T-IT-IT1-20` |
| `src/index_tools/pipeline/**` | `T-UT-UT1-15`, `T-UT-UT1-17`, `T-UT-UT1-18`, `T-UT-UT1-30`, `T-ST-ST1-15` |
| `src/index_tools/connectors/**` | `T-UT-UT1-9`, `T-UT-UT1-10`, `T-UT-UT1-11`, `T-UT-UT1-41`, `T-UT-UT1-42` |
| `src/index_tools/convert/**` | `T-UT-UT1-12`, `T-UT-UT1-13`, `T-UT-UT1-14`, `T-IT-IT2-7`, `T-IT-IT2-12` |
| `src/index_tools/embeddings/**` | `T-UT-UT1-23`, `T-UT-UT1-43`, `T-AT-AT2-4` |
| `src/index_tools/vdb/**` | `T-UT-UT1-24`, `T-CT-CT1-1`, `T-CT-CT1-3`, `T-IT-IT2-1`, `T-IT-IT2-6`, `T-AT-AT2-1` |
| `src/index_tools/db/**` | `T-UT-UT1-40`, `T-UT-UT1-45`, `T-ST-ST1-14`, `T-AT-AT2-6-DATABASEE2E` |
| `src/index_tools/sources/**` | `T-UT-UT-W28D440E5`, `T-IT-IT-W28D440E5` |
| `docs/**/*.md` | `T-QT-QT-TRACEABILITY`, `T-QT-QT-RULES-COMPLIANCE` |
| `tests/**/*.py` | `T-QT-QT-TRACEABILITY`, `T-QT-QT-MIGRATION-COMPLETENESS`, `T-QT-QT-RULES-COMPLIANCE` |
| `ui/dist/**` | `T-AT-AT-WEBUI-AUTHDASHBOARD`, `T-AT-AT-WEBUI-COLLECTIONCRUD`, `T-AT-AT-WEBUI-SECURITYADMIN` |

## Cross-references

- Requirements catalogue: `docs/REQUIREMENTS.md`
- Use-case catalogue: `docs/ROLES-AND-USECASES.md`
- Test catalogue: `docs/TESTS.md`
- Coverage matrix: `docs/REQ-COVERAGE.md`
