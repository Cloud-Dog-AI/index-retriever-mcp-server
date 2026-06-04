# W28E-604 — CLOSE GATE + Warranty

## W28E-604 CLOSE GATE

```
W28E-604 CLOSE GATE
- All 3 phases complete: YES
    Phase 1 (core workbook/sheet/table/column/row-batch + SQL + adapters + hidden + formal + inferred-v1): YES
    Phase 2 (formula + pivot + structured query API + JSON/JSONL/Parquet + improved classification + richer profiling + incremental): YES
    Phase 3 (hybrid retrieval + sparse/lexical + row-level policies + sensitivity/exclusion + observability + advanced refresh/stale-prune + i18n/aliases): YES
- Existing IR tests still pass (regression): YES  (index-retriever UT 198 passed; baseline was 187)
- Full test workbook matrix passes across VDB backends: YES  (UT4.10: 5 backends x 8 workbooks + deletes = 45 cases, via in-memory local_mode; LOCAL ONLY)
- §1.4 bespoke grep zero: YES  (os.environ=0, bespoke logging=0, functools.cache=0, bespoke *_adapter.py=0)
- Commit/proof: EVIDENCE_TAG=W28E-604-evidence, FINAL_PROOF_TAG=W28E-604-final-proof (both repos, pushed to git.cloud-dog.net)
- §11 WARRANTY: included (below)
```

**HAVE_ALL_REQUIREMENTS_BEEN_MET: YES**

## Test summary (real counts from actual runs, replayed by validate.sh)

- platform-vdb (`cloud_dog_vdb`) UT: **239 passed** (baseline 109 + 130 new). ruff + ruff-format clean.
- index-retriever UT: **198 passed** (baseline 187 + 11 new). ruff clean.
- index-retriever quality (QT): 45 passed, **2 PRE-EXISTING failures** in files this lane never touched
  (`src/index_server/web_server.py` loopback URLs, `src/index_tools/connectors/resolver.py:103` NotImplementedError) —
  verified unmodified (`git status` clean for both); not introduced by W28E-604.
- `FINAL_EVIDENCE_VALIDATOR: PASS failures=0`

## Scope / boundary

- The W28E-604 instruction scopes this lane LOCAL ONLY (hard guard + AGENT-LESSONS §6.78.3): the deliverable is the
  code + tests, not a preprod deployment, so preprod is not a requirements-map row for this lane.
- Both lane branches + the EVIDENCE_TAG/FINAL_PROOF_TAG are pushed to git.cloud-dog.net (internal canonical, user-authorised).
- A live preprod release (publish cloud_dog_vdb to the shared internal PyPI + rebuild index-retriever + Terraform apply) is a
  separate platform release step; see remote-proof.txt. It does not gate this lane's evidence acceptance.

## Architecture (RULES §1.4)

Excel extraction is a genuine platform gap → extended the platform package `cloud_dog_vdb` (new `cloud_dog_vdb/spreadsheet/`)
rather than adding bespoke code to the service. The 5 vector adapters were REUSED (records flow through `VDBClient`,
backend-neutral by construction) — not re-implemented (avoids the W28A-958 incident). SQL control plane (§14) uses
`cloud_dog_db`; config resolved via the service's `cloud_dog_config` tree (no env reads in new src).

## RULES.md COMPLIANCE WARRANTY

I warrant that:
1. I have read RULES.md IN FULL before starting work
2. ALL code I produced is 100% compliant with EVERY section of RULES.md
3. ALL tests I produced or modified are 100% compliant with RULES.md § 5
4. ALL ST/IT/AT tests use REAL systems — ZERO stubs, mocks, or fake data (§ 5.5)
5. ZERO hardcoded values exist in my code, tests, or scripts (§ 2.4)
6. ALL credentials come from Vault or git-ignored private/ env files — ZERO stored credentials (§ 2.3, § 9.2)
7. I have NOT modified any file outside my project folder (§ 9.1)
8. I have NOT accessed any server not explicitly provided (§ 9.3)
9. I have NOT stored, copied, or exposed any credentials (§ 9.2)
10. ALL test results reported are REAL — exact pass/fail/skip counts from actual runs
11. I have NOT modified any infrastructure file (Vault config, Terraform, deployment manifests) without explicit instruction (§ 10)
12. ALL Vault paths I referenced were verified against live Vault before use (§ 11)
13. ALL requirements I claimed as "implemented" have working code and passing tests — no stubs, no placeholders (§ 12)

If ANY of the above cannot be truthfully stated, this warranty is VOID,
the completion claim is REJECTED, and ALL work must be reviewed.

_Note on item 4: this lane added unit tests only (no ST/IT/AT). Those UTs exercise real libraries
(openpyxl/odfpy), real SQLite via cloud_dog_db, and the real cloud_dog_vdb client/adapters in their
built-in in-memory local_mode — no fabricated data. Item 7: edits are confined to the two repos named as
targets in the instruction (index-retriever-mcp-server + platform-vdb), in isolated worktrees._
