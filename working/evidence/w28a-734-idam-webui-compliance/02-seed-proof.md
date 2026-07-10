# W28A-734 — 02 Seed Proof

Seed source: `config/bootstrap-seed.yaml` (commit b164abd baseline; unchanged by this lane).
Seed loading defect fixed in this lane: `src/index_tools/bootstrap.py` `resolve_seed_path()` now
falls back to the repo-relative `config/bootstrap-seed.yaml` for local (non-container) runs
(PS-71 IW1.6 Admin Seed Guard — without it the Users/Groups/RBAC pages rendered empty).

## Live runtime proof (backend started from this lane's worktree, NO seed env set)

`resolve_seed_path()` resolved (fallback exercised, no env):
```
/opt/iac/Development/cloud-dog-ai/.w28a734-svc/config/bootstrap-seed.yaml
```

MCP tool `users_list` (POST /api/v1/tools/users_list, admin token):
```
users: ['admin', 'colin', 'gary']
```

MCP tool `groups_list`:
```
groups: ['administrators', 'ragflow']
```

- SEED_ADMIN_USER `admin`: PRESENT (Users page, screenshot 04-screenshots/users.png).
- SEED_GROUPS `administrators`, `ragflow`: PRESENT (Groups page, screenshot 04-screenshots/groups.png).
- SEED_API_KEYS: bootstrap-seed leaves `api_keys: []` (no inline tokens). The child-generated API-key
  record is asserted after the Generate flow on the API Keys page; the `owner` column is populated and
  raw secret values are absent from the DataTable (API Keys page, screenshot 04-screenshots/api-keys.png).
- RBAC default admin binding `user:admin` / `admin`: PRESENT (RBAC page, screenshot 04-screenshots/rbac.png).

## Secret handling

No raw API-key secret value appears in any screenshot, DOM capture, log, trace, or committed evidence.
The one-time reveal modal shows the generated secret once then clears it; the conformance test asserts
the secret is absent from the DOM after close. The reveal-modal Playwright trace (which would contain a
one-time token frame) was intentionally excluded from committed evidence; reveal-once is proven by the
passing conformance test and its assertions.
