# Agent Instruction — Fix index-retriever-mcp-server Test Integrity

**Package:** `index-retriever-mcp-server`
**Date:** 2026-02-20 (updated after 15:53 UTC audit)
**Status:** OPEN — **HIGH** severity — IT tests real but cleanup broken
**Audit Reference:** `cloud-dog-ai-platform-standards/AGENT-DISPATCH-TABLE.md` § FRAUD FINDINGS

---

## ⚠️ AUDIT FINDING (2026-02-20 15:53 UTC)

**IT tests ARE hitting real backends** (Chroma, Qdrant, Ollama — 53s runtime proves real network calls). This is the ONLY new service build with genuinely real IT tests. However:

### Problem: Hundreds of orphaned test collections in Chroma

The `LiveIndexRuntime.cleanup()` method is not reliably removing test collections. A `chromadb.HttpClient.list_collections()` call returns **200+ orphaned collections** with names like `ad0bc1ec_default_it_chroma`, `45c5a1df_default_it_chroma`, etc.

### MANDATORY FIX

1. **Fix `cleanup()` in `tests/live_runtime.py`** — ensure ALL collections created during a test session are deleted
2. **Add a cleanup verification** at end of IT session that lists remaining test collections and fails if any orphans exist
3. **Write a one-off cleanup script** to purge the existing 200+ orphaned collections from Chroma
4. **Document the real IT test results** — pass/fail/skip counts per tier with Vault sourced

---

## INTEGRITY WARRANTY — READ THIS FIRST

This section is copied verbatim from the platform-wide `RULES.md` Section 1. It is **NON-NEGOTIABLE**.

**I WILL NEVER:**
- **LIE** about test results, implementation status, or compliance
- **FUDGE** test data, configuration, or validation results
- **HACK** around problems instead of fixing root causes
- **FALSIFY** test outputs, logs, or status reports
- **STUB** functionality in IT/AT tests when real implementation is required
- **FAKE** success when there are errors, warnings, or failures
- **HIDE** failures, warnings, or non-compliance
- **PRETEND** tests pass when they fail
- **SKIP** validation steps to claim completion
- **BYPASS** rules or requirements for convenience

**IF I CANNOT GUARANTEE 100% COMPLIANCE, I WILL STOP AND SAY SO EXPLICITLY.**

**"ASK. DON'T GUESS. DON'T LIE. DON'T FUDGE."**

---

## MANDATORY READING BEFORE ANY WORK

1. `cloud-dog-ai-platform-standards/RULES.md` — Sections 1, 5 (especially § 5.3 items 9–13, § 5.5)
2. `cloud-dog-ai-platform-standards/migration/AGENT-BEHAVIOUR-RULES.md` — RULES 12 and 13
3. This instruction document — in full, before writing any code

---

## AUDIT FINDINGS

| ID | Severity | Finding |
|----|----------|---------|
| **IR-1** | CRITICAL | `conftest.py:166,175` uses `pytest.skip()` when `LiveIndexRuntime` fails or backends not ready. ALL 34 non-UT tests silently skip. This produces "30 passed, 0 failed, 34 skipped" which looks like success. |
| **IR-2** | HIGH | `tests/env-IT` provides `CHROMA_PATH=/tmp/index-retriever-it/chroma` but `LiveIndexRuntime` reads `CHROMA_URL` / `CLOUD_DOG__INDEX__VDB__CHROMA_URL`. The env file variable is **decoration** — never consumed by the test runtime. Same for `EMBED_BASE_URL` (consumed) vs. Qdrant (missing entirely). |
| **IR-3** | HIGH | `tests/env-IT` has NO `VAULT_ADDR` or `VAULT_TOKEN`. So the Vault fallback in `LiveIndexRuntime:191-225` also fails. Without `env-vault` sourced, no VDB URLs resolve → RuntimeError → `pytest.skip()`. |
| **IR-4** | HIGH | ST tests (ST1.1–ST1.12) ALL use `LiveIndexRuntime` which connects to real Chroma/Qdrant/Ollama/PostgreSQL. Per RULES.md § 5.1, ST tests use "Real systems only" — but they should be system-level functionality tests, not full backend integration. There are NO local/in-memory ST alternatives. |
| **IR-5** | MEDIUM | `live_runtime.py` has been partially fixed — it now reads `os.environ` first and falls back to Vault. But env-IT doesn't provide the critical VDB URLs, making the env-first path fail and forcing Vault fallback. |

---

## HARD CONSTRAINTS

- **DO NOT** delete any existing test.
- **DO NOT** weaken any assertion.
- **DO NOT** add `local_mode=True` to IT/AT/CT tests.
- **DO NOT** add credentials to env files in the repository.
- **DO NOT** claim completion without running the full verification chain AND reporting exact pass/fail/skip counts.
- **UK English only.**

---

## PHASE 1 — Fix silent skip → pytest.fail() for IT/AT/CT/QT (IR-1)

### Step 1.1 — Update `tests/conftest.py` `live_service_preflight` fixture

The fixture at line 160-175 currently uses `pytest.skip()`. Change to tier-aware behaviour:

```python
@pytest.fixture(scope="session")
def live_service_preflight(envs: list[str]) -> None:
    """Validate live backend readiness once per session before running live tests."""
    tier = envs[0] if envs else "UT"
    try:
        runtime = LiveIndexRuntime()
    except Exception as exc:
        if tier in ("IT", "AT", "CT", "QT"):
            pytest.fail(
                f"Live runtime environment is not configured for {tier} tier: {exc}. "
                f"Run: set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a"
            )
        pytest.skip(f"Live runtime environment is not configured: {exc}")
        return

    try:
        issues = runtime.preflight()
    finally:
        runtime.cleanup()

    if issues:
        if tier in ("IT", "AT", "CT", "QT"):
            pytest.fail(
                f"Live runtime dependencies not ready for {tier} tier: "
                + "; ".join(issues)
            )
        pytest.skip("Live runtime dependencies not ready: " + "; ".join(issues))
```

### Step 1.2 — Add `TEST_ENV_TIER` to all env files (if not already present)

Verify each `tests/env-*` file has `TEST_ENV_TIER=<tier>`. Current env files already have this — confirm.

---

## PHASE 2 — Fix env-IT to provide real VDB URLs (IR-2, IR-3)

### Step 2.1 — Add real VDB URLs to env-IT

The env-IT file must provide the actual URLs that `LiveIndexRuntime` reads. Add:

```
# Real backend URLs for IT — credentials come from env-vault
CLOUD_DOG__INDEX__VDB__CHROMA_URL=https://chroma.cloud-dog.net
CLOUD_DOG__INDEX__VDB__QDRANT_URL=https://qdrant1.app.vpc0.cloud-dog.net:6333
```

**DO NOT** add `CHROMA_AUTH_TOKEN`, `QDRANT_API_KEY`, or `VAULT_TOKEN` — those are credentials that come from `env-vault` at runtime.

### Step 2.2 — Add Vault non-secret variables to env-IT

```
VAULT_ADDR=https://vault0.cloud-dog.net
VAULT_MOUNT_POINT=cloud_dog_ai
VAULT_CONFIG_PATH=config
```

These are addresses, not credentials. `VAULT_TOKEN` comes from `env-vault`.

### Step 2.3 — Remove decoration variable `CHROMA_PATH` from env-IT

`CHROMA_PATH=/tmp/index-retriever-it/chroma` is not consumed by `LiveIndexRuntime`. Remove it. If any other code uses `CHROMA_PATH` for local-mode Chroma, that belongs in `env-UT` or `env-ST` only.

### Step 2.4 — Update env-AT and env-QT similarly

AT and QT tests also use `LiveIndexRuntime`. Apply the same changes.

### Step 2.5 — Verify env-UT and env-ST do NOT have real backend URLs

UT and ST must not require real backends. They should keep `CHROMA_PATH` for local mode and `EMBED_BASE_URL=http://127.0.0.1:11434/v1` for local Ollama or stubs.

---

## PHASE 3 — Fix ST test tier (IR-4)

### Step 3.1 — Decide: ST tests should use local backends

The current ST tests (ST1.1–ST1.12) all use `LiveIndexRuntime` which connects to real Chroma, Qdrant, Ollama, and PostgreSQL. This makes them IT-level tests.

**Two options (choose one):**

**Option A — Reclassify to IT:** Move ST1.1–ST1.12 to IT tier. Renumber as IT1.13–IT1.24. Write new ST tests that use local/in-memory backends.

**Option B — Create LocalIndexRuntime for ST:** Create a `tests/local_runtime.py` that uses `local_mode=True` for Chroma, in-memory SQLite for jobs, and either mocked or local Ollama for embeddings. Rewrite ST tests to use `LocalIndexRuntime`.

**Recommendation:** Option B — it provides genuine system-level testing without requiring external services.

### Step 3.2 — If Option B: Create `tests/local_runtime.py`

This should be a stripped-down `LiveIndexRuntime` that:
- Uses `local_mode=True` for Chroma
- Uses `sqlite:////tmp/...` for job queue
- Uses a local embedding stub (or small local Ollama if available)
- Does NOT connect to any external service
- Does NOT call Vault

### Step 3.3 — Update ST conftest fixture

```python
@pytest.fixture()
def local_service() -> LocalIndexRuntime:
    runtime = LocalIndexRuntime()
    try:
        yield runtime
    finally:
        runtime.cleanup()
```

### Step 3.4 — Update ST tests to use `local_service` instead of `live_service`

---

## PHASE 4 — Verify env file consumption

### Step 4.1 — For each variable in each env file, confirm it is consumed

Run through each env file and trace each variable to its consumer:

| Env File | Variable | Consumer | Status |
|----------|----------|----------|--------|
| env-IT | `TEST_ENV_TIER` | `conftest.py` → `envs` fixture | ✓ |
| env-IT | `INDEX_RETRIEVER_SERVICE_NAME` | ? | VERIFY |
| env-IT | `EMBED_BASE_URL` | `live_runtime.py:178` via `_env()` | ✓ |
| env-IT | `CHROMA_PATH` | **NOTHING** in LiveIndexRuntime | ✗ REMOVE |
| env-IT | `DB_URL` | `live_runtime.py:188` via `_env()` | ✓ |
| ... | ... | ... | ... |

**Every variable must have a verified consumer. Remove any that don't.**

---

## PHASE 5 — Verification

### Step 5.1 — Run UT (must pass with 0 skipped)

```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
.venv/bin/pytest tests/unit --env tests/env-UT -v 2>&1 | tail -5
```

**Expected:** All pass, 0 skipped.

### Step 5.2 — Run ST (must pass with 0 skipped, no external services)

```bash
.venv/bin/pytest tests/system --env tests/env-ST -v 2>&1 | tail -5
```

**Expected:** All pass, 0 skipped. No network calls to Chroma/Qdrant/Ollama.

### Step 5.3 — Run IT WITHOUT env-vault (must FAIL, not skip)

```bash
.venv/bin/pytest tests/integration --env tests/env-IT -v 2>&1 | tail -10
```

**Expected:** `FAILED` (not SKIPPED) with a clear message: "Live runtime environment is not configured for IT tier... Run: set -a; source .../env-vault; set +a"

### Step 5.4 — Run IT WITH env-vault (must pass against real backends)

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
.venv/bin/pytest tests/integration --env tests/env-IT -v 2>&1 | tail -10
```

**Expected:** All pass against real Chroma, Qdrant, Ollama. 0 skipped.

### Step 5.5 — Run AT, CT, QT similarly (with env-vault)

### Step 5.6 — Report honestly

State exact counts: `N passed, N failed, N skipped` for EACH tier. If any IT/AT/CT test skipped, explain WHY.

---

## COMPLETION GATE

This instruction is complete ONLY when:

1. `pytest.skip()` replaced with `pytest.fail()` for IT/AT/CT/QT tiers in conftest
2. env-IT provides real VDB URLs consumed by `LiveIndexRuntime`
3. Decoration variables removed from env files
4. ST tests work without external services (local runtime or reclassified)
5. UT + ST: 0 skipped
6. IT without env-vault: FAILS explicitly (not silently skips)
7. IT/AT/CT/QT with env-vault: all pass against real backends, 0 skipped
8. Full pass/fail/skip counts reported honestly for every tier

**DO NOT claim completion without evidence for ALL 8 gates.**
