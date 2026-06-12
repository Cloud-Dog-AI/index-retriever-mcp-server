# Data Model — index-retriever-mcp-server

Canonical entity reference: the identity family, the domain family, and the IDAM cascade edge. Built by
W28A-749 (IDAM Thread-b) from the live models (file:line cited). Companion: `ROLES-AND-USECASES.md` (roles +
matrix), `ARCHITECTURE.md` (design), `API.md` (surfaces).

## 1. Identity family
In-memory `IndexService` records, synced to the `cloud_dog_idam` user/group/key services; re-seeded per process
from the bootstrap seed. Roles attach to BOTH users and groups (effective role = `User.roles ∪ ⋃ Group[g].roles`).

| Entity | Store | Key fields | file:line |
|---|---|---|---|
| **User** (`UserRecord`) | `IndexService.users` | `user_id`, `display_name`, `roles:set[str]`, `groups:set[str]`, `enabled:bool` | `tools/service.py:552-559` |
| **Group** (`GroupRecord`) | `IndexService.groups` | `group_id`, `roles:set[str]`, `members:set[str]`, `description` | `tools/service.py:563-569` |
| **GroupMember** | derived from `GroupRecord.members` | `(group_id, member_user_id)` | `tools/service.py:568` |
| **ApiKey** (`ApiKeyRecord`) | `IndexService.api_keys` | `key_id`, `token_hash`, `token_prefix`, `label`, `roles:set`, `capabilities:set`, `user_id`, `revoked` | `tools/service.py:573-584` |
| **Role** | `cloud_dog_idam` `SqlAlchemyRoleStore` (`roles`/`permissions`/`role_permissions`) | `name`, `permissions:list[str]` | `db/runtime.py:239-252` |

Runtime roles: `admin` `{"*"}` / `user` `{collection.read, collection.write, source.configure}` / `viewer`
`{collection.read}` (`auth/middleware.py:48-66`); see `ROLES-AND-USECASES.md §1`.

## 2. Domain family
| Entity | Backing | Key fields | file:line | Identity FK |
|---|---|---|---|---|
| **Profile** | `IndexService.profiles` | `name`, `enabled`, `backend`, `roles(allowed)` | `tools/service.py:749-774` | none |
| **Collection** (`CollectionRecord`) | `IndexService.collections` (`"{profile}:{collection}"`) | `profile`, `collection`, `description`, `dimensions`, `distance_metric`, `metadata`, `allowed_roles:set` | `tools/service.py:601-610` | none (`allowed_roles` is role-vocabulary) |
| **Document/Chunk** (`DocumentRecord`) | `IndexService.documents` + VDB | `doc_id`, `profile`, `collection`, `source`, `text`, `metadata`, `record_id` | `tools/service.py:525-535` | none |
| **SourceConfig** (`SourceConfigRecord`) | `IndexService.source_configs` | `source_id`, `source_type`, `uri`, `schedule`, `profile`, `collection`, `enabled` | `tools/service.py:614-624` | none |
| **Job** (`JobRecord`) | `cloud_dog_jobs` DB `jobs` | `job_id`, `profile`, `collection`, `job_type`, `status`, `payload`, `user_id?`, `attempt`, `max_attempts` | `queue/models.py:50-81` | weak `user_id?` (initiator) |
| **AuditEvent** | `cloud_dog_logging` JSONL | `event_type`, `actor`, `action`, `outcome`, `target`, `correlation_id` | `audit/logger.py:132-288` | actor=label |
| **Structure{Corpus,Pattern,Template}** | DB tables | `*_id`, `profile_id`, `collection_id`, … | `db/corpus_models.py:30-71` | none |

## 3. Identity↔Domain: DISJOINT today; the cascade edge (W28A-749)
**No domain row carries a `group_id`/`owner_user_id` FK** (e.g. `CollectionRecord` has `allowed_roles` only).
The cascade ("group-admin adds user to G → member reads G's collection") has no resource-scoped data path in
0.4.x. Per IDAM-B2 §2 the edge is the `cloud_dog_idam` **`RBACBinding`** row (no bespoke FK, no domain schema
change), enforced by the 0.5.0 resolver/guard:

| field | value for the index-retriever cascade |
|---|---|
| `subject_type` | `group` (or `user`) |
| `subject_id` | the group_id `G` |
| `project` | `index-retriever` |
| `resource_type` | `collection` (or `index_profile`) |
| `resource_id` | `"{profile}:{collection}"` (e.g. `default:kb`), `"{profile}"`, or `"*"` |
| `permission` | `collection.read` / `collection.write` |
| `granted_by` | the admin / group-admin actor |

Composition: `U ∈ G (GroupRecord.members) ∘ RBACBinding(group:G → collection:C = collection.read)`. The
resolver (`cloud_dog_idam.rbac.grants.effective_grants/authorise/allowed_resource_ids`) composes role-perms
with binding rows on the user AND the user's groups; LIST queries filter by `allowed_resource_ids`; point
checks pass `resource_id`. Revocation is automatic (the grant lives on the GROUP). Stored in the
`rbac_bindings` table (created capability-gated when `cloud_dog_idam>=0.5.0` is present). **Activated only when
the built image carries `cloud_dog_idam==0.5.0`** (W28A-749 keystone gate).
