---
template-id: T-RUC
template-version: 1.1
applies-to: docs/ROLES-AND-USECASES.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards
extends-version: 1.0
extends-via: PS-REQ-TEST-TRACE v1.0

project: index-retriever-mcp-server
doc-last-updated: 2026-06-18
doc-git-commit: 16fd5b2c0000000000000000000000000000000000
doc-git-branch: main
doc-source-shas: []
doc-age-policy: indefinite
doc-conformance-stamp: 2026-06-18T00:00:00Z
req-trace-version: 1.0
---

# Roles & Use-Cases — index-retriever-mcp-server

Canonical IDAM reference for index-retriever: the role catalog, the use-cases (verbatim), the
requirement→role→surface→test traceability matrix, and the WebUI page→use-case→role map. Built by W28A-749
(IDAM Thread-b) from `docs/REQUIREMENTS.md`, the in-code roles (`src/index_server/auth/middleware.py`), the
tool registry (`src/index_tools/tools/registry.py`), and the live servers. Companion: `REQUIREMENTS.md`
(what), `ARCHITECTURE.md` (how), `DATA-MODEL.md` (entities), `API-REFERENCE.md` (surfaces), `TESTS.md` (T0–T3).

---

## 1. Roles

### 1.1 Runtime roles (authoritative — `src/index_server/auth/middleware.py:48-66`)
| Runtime role | Permissions | Legacy aliases (normalised to it) |
|---|---|---|
| `admin` | `{"*"}` (all) | `owner` |
| `user` | `{collection.read, collection.write, source.configure}` — **read-WRITE** | `maintainer`, `writer`, `read-write` |
| `viewer` | `{collection.read}` — **read-only** | `reader`, `read-only` |

Unresolved/blank role normalises to `viewer` (`_canonical_role`). Flat-login projection (727-R5 contract):
`admin→admin`, `user→read-write`, `viewer→read-only` (`flat_roles_for`). Effective role of a principal =
`User.roles ∪ ⋃ Group[g].roles` for the principal's groups. Permission strings: `collection.read`,
`collection.write`, `source.configure`, plus the per-tool category map in `mcp_server.py:194-275`.

> **Naming note (do not rename in this lane).** index-retriever's `user` is the read-WRITE principal and
> `viewer` is read-only — this is the live 0.4.x contract that the flat-login roles (`read-write`/`read-only`)
> depend on. It differs from the central PS-82/§83 catalog where `user` is the least-privilege baseline. The
> mapping (not a rename) is in §1.2.

### 1.2 Mapping to the central catalog (PS-82 §1/§7, `docs/standards/83-canonical-role-catalog.md`)
| Central role / grant | index-retriever runtime equivalent | Notes |
|---|---|---|
| `admin` (=`*`) | `admin` | full control |
| `user` (least-privilege baseline + in-scope read) | `viewer` | read-only domain access (`collection.read`) |
| `user` + `collection.write`/`source.configure` | `user` | the read-write principal |
| `group-admin` (manages owned groups' membership + resource bindings — **drives the cascade**) | *(central, via `cloud_dog_idam`)* | adds members + writes `RBACBinding group:G→collection:C` |
| `restricted` (no baseline; explicit grants only) | *(central; not in 0.4.x runtime)* | gap G3 |
| `job-control` (`jobs.read`+`jobs.control`) | maps onto `user`/`admin` for `job_*` tools today | gap G3 |
| `audit-log` (`logs.read`/`logs.read.all`) | maps onto `admin` for `/api/audit-log` today | gap G3 |
| `GROUPUSER` (sees only group G's data) | **collection-scoped** principal via the cascade (§4) | wired by W28A-749 against `cloud_dog_idam` 0.5.0 |
| `SERVICE` (machine; MCP/A2A only, no WebUI session) | api-key principal | FR-01B |

---

## 2. Use-cases (VERBATIM from `REQUIREMENTS.md` §4)

- **UC-01 — Upload file, index into profile collection, then query:** `profile_select(profile="default")` →
  `ingest_upload(profile="default", collection="kb", file=…, dedupe="hash") -> job_id` → `job_wait(job_id)` →
  `search(profile="default", collection="kb", query="…", top_k=10) -> results`.
- **UC-02 — Index remote reference (S3/WebDAV/Drive) by URI:** `ingest_reference(profile="p1",
  uri="s3://bucket/key", options={…}) -> job_id`; system fetches, converts, chunks, embeds, indexes;
  `job_get(job_id)` returns success + stats (chunks, tokens, time).
- **UC-03 — Stream chat messages and index in near-real-time:** client opens a stream endpoint (SSE/WS); sends
  message events with metadata (`thread_id`, `user_id`, tags); server streams acknowledgements; the
  chunk+embed+index pipeline runs asynchronously; retrieval can reference `thread_id`.
- **UC-04 — Duplicate detection on re-upload:** `ingest_upload(…, dedupe="hash+size+mtime")`; server computes
  fingerprints and checks index metadata; policy decides skip / replace / version-as-new with link to prior.
- **UC-05 — Admin creates a new profile and collection at runtime:** `admin_profile_create(…)` →
  `admin_collection_create(profile="p2", collection="finance")` → `admin_test_search(…)`; profile becomes
  available without restart (config is persisted).
- **UC-06 — Retention/cleanup job:** admin schedules `retention_run(profile="p1", rule="older_than:90d")`; job
  removes old data and updates metadata indexes; audit log includes removed document IDs and reason.

---

## 3. Traceability matrix (requirement → entity/action → use-case → role → surface → test-id)

See `working/w28a-749/B3-INDEX-RETRIEVER-MATRIX.md` §3 for the full 17-row matrix with verbatim FR text. Summary:

| Req | Action | Role | Surfaces | Test-IDs |
|---|---|---|---|---|
| UC-01 | ingest→search | user(write)/viewer(read) | MCP/API/A2A/WebUI | T0-IR-INGEST, T0-IR-SEARCH, T3-IR-UPLOAD-QUERY |
| UC-02/03/04 | ingest ref / stream / dedupe | user | MCP/API/A2A | T3-IR-REFERENCE/STREAM/DEDUPE |
| UC-05 | profile+collection CRUD runtime | admin | MCP/API/WebUI | T3-IR-PROFILE-CRUD, T3-IR-COLLECTION-CRUD, T9-IR-PROFILE-LIVE |
| UC-06 | retention | admin/maintainer | MCP/API/WebUI | T3-IR-RETENTION |
| FR-04 | AuthN gate | ANON→401 | all | T1-IR-AUTH-401 |
| FR-01B | A2A auth | ANON/service | A2A | T1-IR-A2A-401 |
| FR-05/16 | RBAC; admin-only admin tools | admin/user/viewer | all | T2-IR-ADMINONLY, T2-IR-COLLECTION-RBAC |
| FR-06 | audit coverage | system | all | T1-IR-AUDIT-COVERAGE |
| FR-07 | jobs CRUD | job-control/maintainer | MCP/API/WebUI | T2-IR-JOBS-RBAC |
| FR-14 | search/retrieve, stable IDs | viewer/user | all | T3-IR-SEARCH-SCOPE |
| FR-16A | tool inventory == runtime (92) | any | MCP | T0-IR-TOOLS-COUNT |
| RULES | connector scope/traversal | any | MCP/API | T0-IR-SCOPE-DENY, T3-IR-CONNECTOR-SCOPE |
| IDAM-B2 §3.3 | non-admin sees no secret | non-admin | all | T2-IR-NOSECRET |
| **CASCADE** | **group-admin adds U→G; U reads collection C only** | **group-admin / GROUPUSER** | **all** | **T3-IR-CASCADE** |

---

## 4. The cascade (group → collection), explicit resource model

**Resource type:** `collection` is the cascade resource (broad/profile-wide grants use `index_profile`).
**Binding (the edge, `cloud_dog_idam` `RBACBinding`, no bespoke FK):**

| subject_type | subject_id | project | resource_type | resource_id | permission |
|---|---|---|---|---|---|
| `group` | `G` (group_id) | `index-retriever` | `collection` | `"{profile}:{collection}"` (e.g. `default:kb`) — or `"*"` for all collections in scope | `collection.read` |
| `group` | `G` | `index-retriever` | `index_profile` | `"{profile}"` (e.g. `default`) — or `"*"` | `collection.read` (profile-wide) |

- **resource_id** is the collection key `"{profile}:{collection}"` (matches `CollectionRecord` key,
  `tools/service.py` `"{profile}:{collection}"`), or the profile name for `index_profile`. `"*"` = every
  resource of that type in the project (broad grant, e.g. group-admin/admin).
- **Filtering rules (default-DENY, IDAM-B2 §2.3):**
  - *List* (`collections_list`/`list_collections`/`search` over a profile): the route asks
    `allowed_resource_ids(user_id, resource_type="collection", permission="collection.read")`; if `"*"` →
    all collections; else the concrete set from the caller's user + group bindings. Server-side filter — the
    `GROUPUSER` provably sees only group G's collections, never client-side.
  - *Point* (`search`/`retrieve` on one collection, `collection_get`): `authorise(user_id,
    permission="collection.read", resource_type="collection", resource_id="{profile}:{collection}")`; 403 if no
    binding grants it. `ingest_*`/`delete_*`/`reindex` require `collection.write` — a `collection.read`-only
    binding → 403 (graded).
- **Membership edge:** the existing `GroupRecord.members` join (`groups_of(user_id)` adapter). Removing a member
  drops the path → revocation is automatic (the grant lives on the GROUP).

`T3-IR-CASCADE` proves this live: U∉G → read C 403 → group-admin adds U to G → U reads C 200 / lists only C /
can't write C / can't read D → group-admin removes U → 403, no restart. **Held until the built image carries
`cloud_dog_idam==0.5.0`** (resolver/guard); else `PACKAGE_RESOLUTION_BLOCKED` (W28A-749 §6 G9).

---

## 5. WebUI page → use-case → role (b-5; no orphan page; WebUI↔API parity)

Every SPA route (verified `cloud-dog-ai-ui-monorepo/apps/index-retriever/src/routes/App.tsx:327-357`) is a
strict API client (FR-17). Canonical entry `/dashboard`; `/`, `/login`, `*` → `/dashboard`.

| Route | Page | Use-case / requirement | Min role | Backing API |
|---|---|---|---|---|
| `/dashboard` | DashboardPage | service overview | viewer | `/api/status`, `/api/v1/health` |
| `/profiles` | ProfileCrudPage | UC-05, FR-03 profile CRUD | admin (write) / viewer (read) | `admin_profile_*`, `profiles_list` |
| `/collections` | CollectionCrudPage | UC-05, FR-16 collection CRUD | admin (write) / viewer (read) | `admin_collection_*`, `collections_list` |
| `/source-config` ("File Ingest") | SourceConfigPage | UC-02, FR-08 source config | user (`source.configure`) | `admin_source_config_*`, `source_configs_list` |
| `/ingest-search` ("Search Retrieve") | IngestSearchPage | UC-01/04, FR-14 ingest+search | user (ingest) / viewer (search) | `ingest_*`, `search`, `retrieve` |
| `/retention-delete` | RetentionDeletePage | UC-06, FR-16 retention/purge | admin/maintainer | `retention_run`, `delete_by_*`, `reindex_run` |
| `/jobs` | JobsPageView | FR-07 job control (PS-76) | job-control/maintainer | `job_list/get/cancel/retry`, `queue_status` |
| `/observability` | ObservabilityPage | FR-06 audit/logs | audit-log/admin | `/api/logs`, `/api/audit-log`, `/api/config-events` |
| `/mcp-console` | McpConsolePage | PS-72 MCP console | user | `/mcp`, `GET /mcp/tools` |
| `/a2a-console` | A2aConsolePage | PS-72 A2A console | user | `/a2a`, `/a2a/events` |
| `/api-docs` | ApiDocsPage | PS-74 API docs | viewer | `/api-docs`, `openapi.json` |
| `/settings` | SettingsPage | PS-73 settings (masked) | viewer (own) | `/api/config`, `/auth/me` |
| `/idam/users` (+`/admin/users`) | IdamUsersPage | CFG users CRUD | admin (all) / user (own row) | `users_list`, `admin_user_*` |
| `/idam/groups` (+`/admin/groups`) | IdamGroupsPage | CFG groups CRUD + membership (cascade source) | admin / group-admin | `groups_list`, `admin_group_*` |
| `/idam/api-keys` (+`/admin/api-keys`) | IdamApiKeysPage | CFG api-key CRUD | admin (all) / user (own) | `api_keys_list`, `admin_api_key_*` |
| `/idam/roles` (+`/admin/roles`) | IdamRolesPage | role catalog | admin | `SqlAlchemyRoleStore` via `/api/v1/admin/roles` |
| `/idam/rbac` (+`/admin/rbac`) | IdamRbacPage | RBAC bindings (the cascade write surface) | admin / group-admin | `rbac_bindings_list`, `admin_rbac_bind/unbind` |
| `/security` | →`/idam/users` | deprecated alias (W28A-734-R2) | — | redirect |
| `/admin` | →`/idam/users` | legacy gateway | — | redirect |

**No orphan page:** every route maps to a use-case/FR + role above. **Parity:** each page calls only the API
(FR-17); every admin action is reachable in MCP/API; destructive actions (`/retention-delete`) require explicit
confirmation (FR-17). The `/idam/*` pages are the shared `@cloud-dog/idam` components (PS-71, W28A-876).


<!-- W28C-1710b design-delta additions (2026-06-14T18:01:23Z) -->

## Cross-surface UC mappings (W28C-1710b)

Per T-RUC v1.1 + PS-REQ-TEST-TRACE §3.5, every UC-NNN maps to one OR MORE FR-NNN across surfaces.

This service's surface set: **api, mcp, a2a**.

Detailed UC-by-UC operator-review pass + per-FR cross-surface mapping deferred to W28C-1711. The cross-surface declarations are enabled here.

```yaml
# Schema for every UC-NNN (default; operator amends per UC):
surfaces: ['api', 'mcp', 'a2a']
roles: [admin, read-write, read-only, anon]
FR-mapping: []  # populated by W28C-1711
```
