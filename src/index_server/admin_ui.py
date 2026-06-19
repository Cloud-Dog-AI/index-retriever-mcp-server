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

"""Admin WebUI assets served by the API runtime.

Description:
- Provides the in-repo profile and security administration pages required by
  CFG-07 and CFG-11.
- The UI is a strict HTTP API client. All actions are executed from browser
  JavaScript through `/admin/*`, `/health`, and `/a2a/events`.

Related requirements:
- FR-01, FR-17
- CFG-07, CFG-11, CFG-13

Related tests:
- tests/application/AT1_10/test_at1_10_admin_webui_playwright.py
"""

from __future__ import annotations

import html
import json
from typing import Any


def admin_ui_styles() -> str:
    """Return the shared stylesheet for the admin pages."""
    return """
:root {
  --bg: #f3efe7;
  --panel: #fffaf1;
  --ink: #1d2b28;
  --muted: #6b746f;
  --accent: #155e63;
  --accent-2: #b8662b;
  --line: #d8cfbf;
  --ok: #245f45;
  --error: #9d2f1c;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(184, 102, 43, 0.18), transparent 28%),
    radial-gradient(circle at top right, rgba(21, 94, 99, 0.18), transparent 30%),
    linear-gradient(180deg, #f6f1e8 0%, #ece5d8 100%);
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}

a {
  color: inherit;
}

.shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.hero {
  display: grid;
  gap: 16px;
  padding: 24px;
  border: 1px solid rgba(29, 43, 40, 0.08);
  border-radius: 24px;
  background: rgba(255, 250, 241, 0.88);
  box-shadow: 0 20px 60px rgba(29, 43, 40, 0.08);
  backdrop-filter: blur(8px);
}

.hero h1 {
  margin: 0;
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
  font-size: clamp(2rem, 4vw, 3.6rem);
  line-height: 0.95;
}

.hero p {
  margin: 0;
  max-width: 70ch;
  color: var(--muted);
}

.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.nav a {
  padding: 10px 14px;
  border-radius: 999px;
  text-decoration: none;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.8);
}

.nav a[aria-current="page"] {
  background: var(--accent);
  color: #fdf8ee;
  border-color: var(--accent);
}

.grid {
  display: grid;
  gap: 18px;
  margin-top: 22px;
}

@media (min-width: 960px) {
  .grid {
    grid-template-columns: 1.2fr 0.8fr;
  }
}

.panel {
  padding: 18px;
  border-radius: 22px;
  background: var(--panel);
  border: 1px solid rgba(29, 43, 40, 0.09);
  box-shadow: 0 18px 45px rgba(29, 43, 40, 0.06);
}

.panel h2,
.panel h3 {
  margin-top: 0;
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
}

.stack {
  display: grid;
  gap: 12px;
}

.form-grid {
  display: grid;
  gap: 12px;
}

@media (min-width: 680px) {
  .form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

label {
  display: grid;
  gap: 6px;
  font-size: 0.92rem;
}

input,
select,
textarea,
button {
  font: inherit;
}

input,
select,
textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fffdf8;
  color: var(--ink);
}

textarea {
  min-height: 96px;
  resize: vertical;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

button {
  padding: 10px 14px;
  border: 0;
  border-radius: 999px;
  background: var(--accent);
  color: #fff8ef;
  cursor: pointer;
}

button.secondary {
  background: #f1e8d6;
  color: var(--ink);
}

button.warn {
  background: var(--accent-2);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result {
  padding: 12px;
  border-radius: 14px;
  background: #f7f3ea;
  border: 1px solid var(--line);
  min-height: 72px;
  overflow: auto;
  white-space: pre-wrap;
}

.result.ok {
  border-color: rgba(36, 95, 69, 0.25);
  color: var(--ok);
}

.result.error {
  border-color: rgba(157, 47, 28, 0.28);
  color: var(--error);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 10px 8px;
  border-bottom: 1px solid rgba(29, 43, 40, 0.08);
  vertical-align: top;
}

thead th {
  color: var(--muted);
  font-size: 0.85rem;
}

.muted {
  color: var(--muted);
}

.token {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.9rem;
}
""".strip()


def admin_ui_script() -> str:
    """Return the shared JavaScript runtime for the admin pages."""
    return """
const state = {
  authMode: window.localStorage.getItem("cd_idx_auth_mode") || "bearer",
  authToken: window.localStorage.getItem("cd_idx_auth_token") || "",
};

function el(testId) {
  return document.querySelector(`[data-testid="${testId}"]`);
}

function setResult(testId, payload, isError = false) {
  const node = el(testId);
  if (!node) {
    return;
  }
  node.classList.remove("ok", "error");
  node.classList.add(isError ? "error" : "ok");
  node.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function headers(extra = {}) {
  const out = { Accept: "application/json", ...extra };
  if (state.authMode === "api-key" && state.authToken) {
    out["X-API-Key"] = state.authToken;
  } else if (state.authToken) {
    out["Authorization"] = `Bearer ${state.authToken}`;
  }
  return out;
}

async function requestJson(method, path, body) {
  const options = { method, headers: headers() };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const text = await response.text();
  let parsed;
  try {
    parsed = text ? JSON.parse(text) : {};
  } catch (_error) {
    parsed = { raw: text };
  }
  if (!response.ok) {
    throw { status: response.status, body: parsed };
  }
  return parsed;
}

function csvToList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function saveAuth() {
  const mode = el("auth-mode").value;
  const token = el("auth-token").value.trim();
  state.authMode = mode;
  state.authToken = token;
  window.localStorage.setItem("cd_idx_auth_mode", mode);
  window.localStorage.setItem("cd_idx_auth_token", token);
  setResult("auth-result", { status: "saved", auth_mode: mode, token_present: token.length > 0 });
}

async function loadHealth() {
  try {
    const payload = await requestJson("GET", "/health");
    setResult("health-result", payload);
  } catch (error) {
    setResult("health-result", error, true);
  }
}

function renderRows(testId, rows, columns) {
  const tbody = el(testId);
  if (!tbody) {
    return;
  }
  tbody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const column of columns) {
      const td = document.createElement("td");
      const value = row[column];
      td.textContent = typeof value === "object" ? JSON.stringify(value) : String(value ?? "");
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function refreshProfiles() {
  try {
    const payload = await requestJson("GET", "/admin/profiles");
    renderRows("profiles-table-body", payload.profiles || [], ["profile", "enabled", "backend", "roles"]);
    setResult("profiles-result", payload);
  } catch (error) {
    setResult("profiles-result", error, true);
  }
}

async function refreshCollections() {
  const profileNode = el("collections-profile");
  const profile = profileNode ? profileNode.value.trim() || "default" : "default";
  try {
    const payload = await requestJson("GET", `/admin/collections?profile=${encodeURIComponent(profile)}`);
    renderRows("collections-table-body", payload.collections || [], [
      "profile",
      "collection",
      "description",
      "allowed_roles",
      "metadata"
    ]);
    setResult("collections-result", payload);
  } catch (error) {
    setResult("collections-result", error, true);
  }
}

async function createProfile() {
  const profile = el("profile-id").value.trim();
  const backend = el("profile-backend").value.trim();
  const roles = csvToList(el("profile-roles").value);
  try {
    const payload = await requestJson("POST", "/admin/profiles", {
      profile,
      config: { backend, roles, enabled: true },
    });
    await refreshProfiles();
    setResult("profiles-result", payload);
  } catch (error) {
    setResult("profiles-result", error, true);
  }
}

async function updateProfile() {
  const profile = el("profile-id").value.trim();
  const backend = el("profile-backend").value.trim();
  const roles = csvToList(el("profile-roles").value);
  try {
    const payload = await requestJson("PUT", `/admin/profiles/${encodeURIComponent(profile)}`, {
      config: { backend, roles, enabled: true },
    });
    await refreshProfiles();
    setResult("profiles-result", payload);
  } catch (error) {
    setResult("profiles-result", error, true);
  }
}

async function deleteProfile() {
  const profile = el("profile-id").value.trim();
  try {
    const payload = await requestJson("DELETE", `/admin/profiles/${encodeURIComponent(profile)}`);
    await refreshProfiles();
    setResult("profiles-result", payload);
  } catch (error) {
    setResult("profiles-result", error, true);
  }
}

async function refreshUsers() {
  try {
    const payload = await requestJson("GET", "/admin/users");
    renderRows("users-table-body", payload.users || [], ["user_id", "display_name", "roles", "groups", "enabled"]);
    setResult("users-result", payload);
  } catch (error) {
    setResult("users-result", error, true);
  }
}

async function createUser() {
  const userId = el("user-id").value.trim();
  const displayName = el("user-display-name").value.trim();
  const roles = csvToList(el("user-roles").value);
  try {
    const payload = await requestJson("POST", "/admin/users", {
      user_id: userId,
      display_name: displayName,
      roles,
    });
    await refreshUsers();
    setResult("users-result", payload);
  } catch (error) {
    setResult("users-result", error, true);
  }
}

async function updateUser() {
  const userId = el("user-id").value.trim();
  const displayName = el("user-display-name").value.trim();
  const roles = csvToList(el("user-roles").value);
  try {
    const payload = await requestJson("PUT", `/admin/users/${encodeURIComponent(userId)}`, {
      display_name: displayName,
      roles,
    });
    await refreshUsers();
    setResult("users-result", payload);
  } catch (error) {
    setResult("users-result", error, true);
  }
}

async function deleteUser() {
  const userId = el("user-id").value.trim();
  try {
    const payload = await requestJson("DELETE", `/admin/users/${encodeURIComponent(userId)}`);
    await refreshUsers();
    setResult("users-result", payload);
  } catch (error) {
    setResult("users-result", error, true);
  }
}

async function refreshGroups() {
  try {
    const payload = await requestJson("GET", "/admin/groups");
    renderRows("groups-table-body", payload.groups || [], ["group_id", "roles", "members"]);
    setResult("groups-result", payload);
  } catch (error) {
    setResult("groups-result", error, true);
  }
}

async function createGroup() {
  const groupId = el("group-id").value.trim();
  const roles = csvToList(el("group-roles").value);
  const members = csvToList(el("group-members").value);
  try {
    const payload = await requestJson("POST", "/admin/groups", {
      group_id: groupId,
      roles,
      members,
    });
    await refreshGroups();
    setResult("groups-result", payload);
  } catch (error) {
    setResult("groups-result", error, true);
  }
}

async function updateGroup() {
  const groupId = el("group-id").value.trim();
  const roles = csvToList(el("group-roles").value);
  const members = csvToList(el("group-members").value);
  try {
    const payload = await requestJson("PUT", `/admin/groups/${encodeURIComponent(groupId)}`, {
      roles,
      members,
    });
    await refreshGroups();
    setResult("groups-result", payload);
  } catch (error) {
    setResult("groups-result", error, true);
  }
}

async function deleteGroup() {
  const groupId = el("group-id").value.trim();
  try {
    const payload = await requestJson("DELETE", `/admin/groups/${encodeURIComponent(groupId)}`);
    await refreshGroups();
    setResult("groups-result", payload);
  } catch (error) {
    setResult("groups-result", error, true);
  }
}

async function refreshApiKeys() {
  try {
    const payload = await requestJson("GET", "/admin/api-keys");
    renderRows("api-keys-table-body", payload.api_keys || [], [
      "key_id",
      "label",
      "roles",
      "capabilities",
      "user_id",
      "revoked"
    ]);
    setResult("api-keys-result", payload);
  } catch (error) {
    setResult("api-keys-result", error, true);
  }
}

async function createApiKey() {
  const label = el("api-key-label").value.trim();
  const userId = el("api-key-user-id").value.trim();
  const roles = csvToList(el("api-key-roles").value);
  const capabilities = csvToList(el("api-key-capabilities").value);
  try {
    const payload = await requestJson("POST", "/admin/api-keys", {
      label,
      user_id: userId || null,
      roles,
      capabilities,
    });
    const tokenNode = el("api-key-token");
    if (tokenNode) {
      tokenNode.textContent = payload.api_key?.token || "";
    }
    await refreshApiKeys();
    setResult("api-keys-result", payload);
  } catch (error) {
    setResult("api-keys-result", error, true);
  }
}

async function revokeApiKey() {
  const keyId = el("api-key-id").value.trim();
  try {
    const payload = await requestJson("DELETE", `/admin/api-keys/${encodeURIComponent(keyId)}`);
    await refreshApiKeys();
    setResult("api-keys-result", payload);
  } catch (error) {
    setResult("api-keys-result", error, true);
  }
}

async function refreshEvents() {
  try {
    const payload = await requestJson("GET", "/a2a/events");
    setResult("events-result", payload);
  } catch (error) {
    setResult("events-result", error, true);
  }
}

// -- W28E-603 structure / corpus / template workflows --
async function structureExtract() {
  try {
    const out = await requestJson("POST", "/api/v1/structure/extract", {
      text: el("struct-extract-text").value,
      profile: el("struct-extract-profile").value.trim() || "default",
      collection: el("struct-extract-collection").value.trim() || "default",
    });
    setResult("struct-doc-result", out);
  } catch (error) { setResult("struct-doc-result", error, true); }
}
async function structureListDocs() {
  try {
    const profile = el("struct-extract-profile").value.trim() || "default";
    setResult("struct-doc-result", await requestJson("GET", `/api/v1/structure/documents?profile=${encodeURIComponent(profile)}`));
  } catch (error) { setResult("struct-doc-result", error, true); }
}
async function structureOutline() {
  try {
    const id = el("struct-doc-id").value.trim();
    setResult("struct-doc-result", await requestJson("GET", `/api/v1/structure/documents/${encodeURIComponent(id)}/outline`));
  } catch (error) { setResult("struct-doc-result", error, true); }
}
async function corpusCreate() {
  try {
    const out = await requestJson("POST", "/api/v1/structure/corpora", {
      name: el("corpus-name").value.trim(),
      profile_id: el("struct-extract-profile").value.trim() || "default",
      document_ids: csvToList(el("corpus-docs").value),
    });
    setResult("corpus-result", out);
  } catch (error) { setResult("corpus-result", error, true); }
}
async function corpusList() {
  try {
    const profile = el("struct-extract-profile").value.trim() || "default";
    setResult("corpus-result", await requestJson("GET", `/api/v1/structure/corpora?profile=${encodeURIComponent(profile)}`));
  } catch (error) { setResult("corpus-result", error, true); }
}
async function corpusAnalyse() {
  try {
    const id = el("corpus-id").value.trim();
    setResult("corpus-result", await requestJson("POST", `/api/v1/structure/corpora/${encodeURIComponent(id)}/analyse`));
  } catch (error) { setResult("corpus-result", error, true); }
}
async function corpusPatterns() {
  try {
    const id = el("corpus-id").value.trim();
    setResult("corpus-result", await requestJson("GET", `/api/v1/structure/corpora/${encodeURIComponent(id)}/patterns`));
  } catch (error) { setResult("corpus-result", error, true); }
}
async function templateGenerate() {
  try {
    const out = await requestJson("POST", "/api/v1/structure/templates", {
      corpus_id: el("template-corpus-id").value.trim(),
      name: el("template-name").value.trim() || undefined,
    });
    setResult("template-result", out);
  } catch (error) { setResult("template-result", error, true); }
}
async function templateExport() {
  try {
    const id = el("template-id").value.trim();
    const fmt = el("template-format").value.trim() || "markdown";
    setResult("template-result", await requestJson("GET", `/api/v1/structure/templates/${encodeURIComponent(id)}/export?format=${encodeURIComponent(fmt)}`));
  } catch (error) { setResult("template-result", error, true); }
}
async function templateDelete() {
  try {
    const id = el("template-id").value.trim();
    setResult("template-result", await requestJson("DELETE", `/api/v1/structure/templates/${encodeURIComponent(id)}`));
  } catch (error) { setResult("template-result", error, true); }
}
function bootstrapStructure() {
  wire("struct-extract-btn", structureExtract);
  wire("struct-docs-refresh", structureListDocs);
  wire("struct-outline-btn", structureOutline);
  wire("corpus-create-btn", corpusCreate);
  wire("corpus-list-btn", corpusList);
  wire("corpus-analyse-btn", corpusAnalyse);
  wire("corpus-patterns-btn", corpusPatterns);
  wire("template-generate-btn", templateGenerate);
  wire("template-export-btn", templateExport);
  wire("template-delete-btn", templateDelete);
}

function wire(testId, handler) {
  const node = el(testId);
  if (!node) {
    return;
  }
  node.addEventListener("click", (event) => {
    event.preventDefault();
    void handler();
  });
}

function bootstrapAuthForm() {
  const mode = el("auth-mode");
  const token = el("auth-token");
  if (mode) {
    mode.value = state.authMode;
  }
  if (token) {
    token.value = state.authToken;
  }
  wire("auth-save", saveAuth);
  wire("health-refresh", loadHealth);
}

function bootstrapProfiles() {
  wire("profiles-refresh", refreshProfiles);
  wire("profile-create", createProfile);
  wire("profile-update", updateProfile);
  wire("profile-delete", deleteProfile);
}

function bootstrapCollections() {
  wire("collections-refresh", refreshCollections);
}

function bootstrapSecurity() {
  wire("users-refresh", refreshUsers);
  wire("user-create", createUser);
  wire("user-update", updateUser);
  wire("user-delete", deleteUser);
  wire("groups-refresh", refreshGroups);
  wire("group-create", createGroup);
  wire("group-update", updateGroup);
  wire("group-delete", deleteGroup);
  wire("api-keys-refresh", refreshApiKeys);
  wire("api-key-create", createApiKey);
  wire("api-key-revoke", revokeApiKey);
  wire("events-refresh", refreshEvents);
}

window.addEventListener("DOMContentLoaded", () => {
  bootstrapAuthForm();
  bootstrapProfiles();
  bootstrapCollections();
  bootstrapSecurity();
  bootstrapStructure();
  if (el("profiles-table-body")) {
    void refreshProfiles();
  }
  if (el("collections-table-body")) {
    void refreshCollections();
  }
  if (el("users-table-body")) {
    void refreshUsers();
    void refreshGroups();
    void refreshApiKeys();
    void refreshEvents();
  }
  void loadHealth();
});
""".strip()


def _shell(title: str, description: str, current: str, body: str) -> str:
    """Render the shared page chrome around a route-specific body."""
    profiles_current = 'aria-current="page"' if current == "profiles" else ""
    collections_current = 'aria-current="page"' if current == "collections" else ""
    security_current = 'aria-current="page"' if current == "security" else ""
    structure_current = 'aria-current="page"' if current == "structure" else ""
    return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link rel="stylesheet" href="/admin/ui/styles.css">
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <div class="nav" aria-label="Admin navigation">
          <a href="/admin/ui/profiles" {profiles_current}>Profiles</a>
          <a href="/admin/ui/collections" {collections_current}>Collections</a>
          <a href="/admin/ui/security" {security_current}>Security</a>
          <a href="/admin/ui/structure" {structure_current}>Structure</a>
        </div>
        <div class="stack">
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </section>
      <section class="grid">
        <section class="panel stack">
          <h2>Session</h2>
          <p class="muted">Choose Bearer token or API key. The page uses the HTTP API only.</p>
          <div class="form-grid">
            <label>
              Auth mode
              <select data-testid="auth-mode">
                <option value="bearer">Bearer token</option>
                <option value="api-key">API key</option>
              </select>
            </label>
            <label>
              Token
              <input data-testid="auth-token" type="text" autocomplete="off" placeholder="valid-admin-token">
            </label>
          </div>
          <div class="actions">
            <button data-testid="auth-save" type="button">Save session</button>
            <button class="secondary" data-testid="health-refresh" type="button">Refresh health</button>
          </div>
          <div class="result" data-testid="auth-result" aria-live="polite"></div>
          <div class="result" data-testid="health-result" aria-live="polite"></div>
        </section>
        {body}
      </section>
    </main>
    <script src="/admin/ui/app.js"></script>
  </body>
</html>
""".strip()


def profiles_page() -> str:
    """Return the profile-management page."""
    body = """
<section class="panel stack">
  <h2>Profile management</h2>
  <div class="form-grid">
    <label>
      Profile ID
      <input data-testid="profile-id" type="text" autocomplete="off" placeholder="sample-search">
    </label>
    <label>
      Backend
      <input data-testid="profile-backend" type="text" autocomplete="off" placeholder="qdrant">
    </label>
    <label style="grid-column: 1 / -1;">
      Roles
      <input data-testid="profile-roles" type="text" autocomplete="off" value="reader,writer,maintainer">
    </label>
  </div>
  <div class="actions">
    <button data-testid="profile-create" type="button">Create profile</button>
    <button data-testid="profile-update" type="button">Update profile</button>
    <button class="warn" data-testid="profile-delete" type="button">Delete profile</button>
    <button class="secondary" data-testid="profiles-refresh" type="button">Refresh list</button>
  </div>
  <div class="result" data-testid="profiles-result" aria-live="polite"></div>
  <div class="stack">
    <h3>Profiles</h3>
    <table>
      <thead>
        <tr>
          <th>Profile</th>
          <th>Enabled</th>
          <th>Backend</th>
          <th>Roles</th>
        </tr>
      </thead>
      <tbody data-testid="profiles-table-body"></tbody>
    </table>
  </div>
</section>
""".strip()
    return _shell(
        title="Index profile control",
        description="Create, update, list, and delete runtime profiles through the admin HTTP API.",
        current="profiles",
        body=body,
    )


def _collection_rows(collections: list[dict[str, Any]] | None) -> str:
    """Render collection rows that are visible before JavaScript refresh."""
    rows = []
    for item in collections or []:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('profile') or ''))}</td>"
            f"<td>{html.escape(str(item.get('collection') or ''))}</td>"
            f"<td>{html.escape(str(item.get('description') or ''))}</td>"
            f"<td>{html.escape(json.dumps(item.get('allowed_roles') or [], sort_keys=True))}</td>"
            f"<td>{html.escape(json.dumps(item.get('metadata') or {}, sort_keys=True))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def collections_page(collections: list[dict[str, Any]] | None = None) -> str:
    """Return the collection inventory page."""
    initial_rows = _collection_rows(collections)
    body = f"""
<section class="panel stack">
  <h2>Collection inventory</h2>
  <p class="muted">Lists runtime collections from <span class="token">/admin/collections</span> using the saved session token. Server-rendered rows are included for demo warrant screenshots.</p>
  <div class="form-grid">
    <label>
      Profile
      <input data-testid="collections-profile" type="text" autocomplete="off" value="default">
    </label>
  </div>
  <div class="actions">
    <button class="secondary" data-testid="collections-refresh" type="button">Refresh collections</button>
  </div>
  <div class="result" data-testid="collections-result" aria-live="polite"></div>
  <div class="stack">
    <h3>Collections</h3>
    <table>
      <thead>
        <tr>
          <th>Profile</th>
          <th>Collection</th>
          <th>Description</th>
          <th>Allowed roles</th>
          <th>Metadata</th>
        </tr>
      </thead>
      <tbody data-testid="collections-table-body">{initial_rows}</tbody>
    </table>
  </div>
</section>
""".strip()
    return _shell(
        title="Index collection inventory",
        description="Inspect live retrieval collections through the admin HTTP API.",
        current="collections",
        body=body,
    )


def security_page() -> str:
    """Return the user, group, and API-key management page."""
    body = """
<section class="stack">
  <section class="panel stack">
    <h2>Users</h2>
    <div class="form-grid">
      <label>
        User ID
        <input data-testid="user-id" type="text" autocomplete="off" placeholder="ops-user">
      </label>
      <label>
        Display name
        <input data-testid="user-display-name" type="text" autocomplete="off" placeholder="Ops User">
      </label>
      <label style="grid-column: 1 / -1;">
        Roles
        <input data-testid="user-roles" type="text" autocomplete="off" value="admin">
      </label>
    </div>
    <div class="actions">
      <button data-testid="user-create" type="button">Create user</button>
      <button data-testid="user-update" type="button">Update user</button>
      <button class="warn" data-testid="user-delete" type="button">Delete user</button>
      <button class="secondary" data-testid="users-refresh" type="button">Refresh users</button>
    </div>
    <div class="result" data-testid="users-result" aria-live="polite"></div>
    <table>
      <thead>
        <tr>
          <th>User</th>
          <th>Display name</th>
          <th>Roles</th>
          <th>Groups</th>
          <th>Enabled</th>
        </tr>
      </thead>
      <tbody data-testid="users-table-body"></tbody>
    </table>
  </section>
  <section class="panel stack">
    <h2>Groups</h2>
    <div class="form-grid">
      <label>
        Group ID
        <input data-testid="group-id" type="text" autocomplete="off" placeholder="ops-team">
      </label>
      <label>
        Roles
        <input data-testid="group-roles" type="text" autocomplete="off" value="writer">
      </label>
      <label style="grid-column: 1 / -1;">
        Members
        <input data-testid="group-members" type="text" autocomplete="off" placeholder="ops-user">
      </label>
    </div>
    <div class="actions">
      <button data-testid="group-create" type="button">Create group</button>
      <button data-testid="group-update" type="button">Update group</button>
      <button class="warn" data-testid="group-delete" type="button">Delete group</button>
      <button class="secondary" data-testid="groups-refresh" type="button">Refresh groups</button>
    </div>
    <div class="result" data-testid="groups-result" aria-live="polite"></div>
    <table>
      <thead>
        <tr>
          <th>Group</th>
          <th>Roles</th>
          <th>Members</th>
        </tr>
      </thead>
      <tbody data-testid="groups-table-body"></tbody>
    </table>
  </section>
  <section class="panel stack">
    <h2>API keys</h2>
    <div class="form-grid">
      <label>
        Key label
        <input data-testid="api-key-label" type="text" autocomplete="off" placeholder="ui-admin-key">
      </label>
      <label>
        User ID
        <input data-testid="api-key-user-id" type="text" autocomplete="off" placeholder="ops-user">
      </label>
      <label>
        Roles
        <input data-testid="api-key-roles" type="text" autocomplete="off" value="admin">
      </label>
      <label>
        Capabilities
        <input data-testid="api-key-capabilities" type="text" autocomplete="off" value="admin,search,ingest">
      </label>
      <label style="grid-column: 1 / -1;">
        Key ID to revoke
        <input data-testid="api-key-id" type="text" autocomplete="off" placeholder="api-key-001">
      </label>
    </div>
    <div class="actions">
      <button data-testid="api-key-create" type="button">Create API key</button>
      <button class="warn" data-testid="api-key-revoke" type="button">Revoke API key</button>
      <button class="secondary" data-testid="api-keys-refresh" type="button">Refresh keys</button>
    </div>
    <div class="result" data-testid="api-keys-result" aria-live="polite"></div>
    <div class="stack">
      <strong>Latest issued token</strong>
      <div class="result token" data-testid="api-key-token"></div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Key ID</th>
          <th>Label</th>
          <th>Roles</th>
          <th>Capabilities</th>
          <th>User</th>
          <th>Revoked</th>
        </tr>
      </thead>
      <tbody data-testid="api-keys-table-body"></tbody>
    </table>
  </section>
  <section class="panel stack">
    <h2>A2A config events</h2>
    <div class="actions">
      <button class="secondary" data-testid="events-refresh" type="button">Refresh events</button>
    </div>
    <div class="result" data-testid="events-result" aria-live="polite"></div>
  </section>
</section>
""".strip()
    return _shell(
        title="Identity and key control",
        description="Manage users, groups, API keys, and inspect config events through the admin HTTP API.",
        current="security",
        body=body,
    )


def structure_page() -> str:
    """Return the document-structure inspection / corpus / template workflow page (W28E-603 §25 #11)."""
    body = """
<section class="panel stack" data-testid="structure-panel">
  <h2>Document structure</h2>
  <p class="muted">Extract, inspect, analyse corpora, and generate templates through the HTTP API.</p>
  <div class="form-grid">
    <label>Profile <input data-testid="struct-extract-profile" type="text" value="default"></label>
    <label>Collection <input data-testid="struct-extract-collection" type="text" value="default"></label>
    <label style="grid-column: 1 / -1;">Text to extract
      <textarea data-testid="struct-extract-text" rows="4" placeholder="# Introduction&#10;..."></textarea></label>
  </div>
  <div class="actions">
    <button data-testid="struct-extract-btn" type="button">Extract structure</button>
    <button class="secondary" data-testid="struct-docs-refresh" type="button">List documents</button>
  </div>
  <div class="form-grid">
    <label>Structure document id <input data-testid="struct-doc-id" type="text"></label>
  </div>
  <div class="actions">
    <button data-testid="struct-outline-btn" type="button">Get outline</button>
  </div>
  <div class="result" data-testid="struct-doc-result" aria-live="polite"></div>
</section>
<section class="panel stack" data-testid="corpus-panel">
  <h2>Corpus analysis</h2>
  <div class="form-grid">
    <label>Corpus name <input data-testid="corpus-name" type="text" placeholder="specs"></label>
    <label style="grid-column: 1 / -1;">Document ids (comma separated)
      <input data-testid="corpus-docs" type="text"></label>
    <label>Corpus id <input data-testid="corpus-id" type="text"></label>
  </div>
  <div class="actions">
    <button data-testid="corpus-create-btn" type="button">Create corpus</button>
    <button class="secondary" data-testid="corpus-list-btn" type="button">List corpora</button>
    <button data-testid="corpus-analyse-btn" type="button">Analyse corpus</button>
    <button class="secondary" data-testid="corpus-patterns-btn" type="button">Get patterns</button>
  </div>
  <div class="result" data-testid="corpus-result" aria-live="polite"></div>
</section>
<section class="panel stack" data-testid="template-panel">
  <h2>Template intelligence</h2>
  <div class="form-grid">
    <label>Corpus id <input data-testid="template-corpus-id" type="text"></label>
    <label>Template name <input data-testid="template-name" type="text"></label>
    <label>Template id <input data-testid="template-id" type="text"></label>
    <label>Export format
      <select data-testid="template-format"><option value="markdown">markdown</option><option value="json">json</option></select></label>
  </div>
  <div class="actions">
    <button data-testid="template-generate-btn" type="button">Generate template</button>
    <button class="secondary" data-testid="template-export-btn" type="button">Export template</button>
    <button class="danger" data-testid="template-delete-btn" type="button">Delete template</button>
  </div>
  <div class="result" data-testid="template-result" aria-live="polite"></div>
</section>
""".strip()
    return _shell(
        title="Document structure intelligence",
        description="Inspect document structure and run corpus + template workflows through the admin HTTP API.",
        current="structure",
        body=body,
    )
