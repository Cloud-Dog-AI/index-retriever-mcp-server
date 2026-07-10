# W28E-604 Evidence Matrix

Every requirement is proven from a committed raw artefact (replayable from the tag).

| Requirement | Raw artefact | Raw value observed | Verification command | Pass |
|---|---|---|---|---|
| P1 .xlsx/.xlsm/.ods ingestion (§5.1/§21) | raw/vdb-UT4.4-parse.log | 7 passed | grep "passed" raw/vdb-UT4.4-parse.log | PASS |
| P1 workbook/sheet/table/column/row-batch (§21) | raw/vdb-UT4.5-pipeline.log | 14 passed | grep "passed" raw/vdb-UT4.5-pipeline.log | PASS |
| P1 SQL metadata via cloud_dog_db (§14) | raw/ir-UT1_70-spreadsheet.log | 11 passed; 9 ss_* tables | grep "passed" raw/ir-UT1_70-spreadsheet.log | PASS |
| P1 Chroma/Qdrant/Weaviate/OpenSearch/pgvector adapters (§15) | raw/vdb-UT4.10-matrix.log | 45 passed | grep "passed" raw/vdb-UT4.10-matrix.log | PASS |
| P1 hidden sheet handling (§5.3) | raw/vdb-UT4.4-parse.log | hidden visibility captured | grep "hidden" raw/vdb-UT4.4-parse.log | PASS |
| P1 formal table extraction (§5.4) | raw/vdb-UT4.5-pipeline.log | tbl_sales formal A1:D4 | grep "object_counts" raw/vdb-UT4.5-pipeline.log | PASS |
| P1 inferred region detection v1 (§5.5/§12) | raw/vdb-UT4.3-detect.log | 5 passed | grep "passed" raw/vdb-UT4.3-detect.log | PASS |
| P2 formula extraction + kind (§5.8) | raw/vdb-UT4.8-phase2.log | formula tests passed | grep "formula" raw/vdb-UT4.8-phase2.log | PASS |
| P2 pivot extraction + summaries (§5.9) | raw/vdb-UT4.8-phase2.log | pivot tests passed | grep "pivot" raw/vdb-UT4.8-phase2.log | PASS |
| P2 structured query API (§5.17) | raw/vdb-UT4.8-phase2.log | query tests passed | grep "query" raw/vdb-UT4.8-phase2.log | PASS |
| P2 JSON/JSONL/Parquet/CSV (§5.16) | raw/vdb-UT4.8-phase2.log | formats+parquet passed | grep "formats" raw/vdb-UT4.8-phase2.log | PASS |
| P2 richer column profiling (§5.6) | raw/vdb-UT4.2-profile.log | 5 passed; numeric min/max/mean | grep "passed" raw/vdb-UT4.2-profile.log | PASS |
| P2 incremental re-index (§5.14) | raw/ir-UT1_70-spreadsheet.log | reindex_same upserted=0 | grep "reindex_same" raw/ir-UT1_70-spreadsheet.log | PASS |
| P3 hybrid/sparse retrieval (§16) | raw/vdb-UT4.9-phase3.log | retrieval tests passed | grep "retrieval" raw/vdb-UT4.9-phase3.log | PASS |
| P3 row-level policies (§5.7) | raw/vdb-UT4.9-phase3.log | row_policy tests passed | grep "row_policy" raw/vdb-UT4.9-phase3.log | PASS |
| P3 sensitivity + exclusion (§17.3) | raw/vdb-UT4.9-phase3.log | sensitivity tests passed | grep "sensitivity" raw/vdb-UT4.9-phase3.log | PASS |
| P3 advanced refresh + stale prune (§5.18) | raw/ir-UT1_70-spreadsheet.log | refresh_mode tests passed | grep "refresh_mode" raw/ir-UT1_70-spreadsheet.log | PASS |
| P3 multilingual/i18n (§5.19) | raw/vdb-UT4.9-phase3.log | i18n tests passed | grep "i18n" raw/vdb-UT4.9-phase3.log | PASS |
| Backend matrix §19.2 | raw/vdb-UT4.10-matrix.log | 45 passed | grep "45 passed" raw/vdb-UT4.10-matrix.log | PASS |
| SQL backend matrix §19.3 | raw/ir-UT1_70-spreadsheet.log | SQLite live; Maria/PG via cloud_dog_db | grep "migration" raw/ir-UT1_70-spreadsheet.log | PASS |
| No macro execution §17.1 | raw/vdb-UT4.4-parse.log | macro detection no-exec passed | grep "macro" raw/vdb-UT4.4-parse.log | PASS |
| RULES §1.4 zero bespoke | raw/gates-checks.log | 0 env / 0 logging / 0 cache / 0 adapters | grep "0 matches" raw/gates-checks.log | PASS |
| No regression — platform-vdb | raw/vdb-UT-full.log | 239 passed | grep "239 passed" raw/vdb-UT-full.log | PASS |
| No regression — index-retriever | raw/ir-UT-full.log | 198 passed | grep "198 passed" raw/ir-UT-full.log | PASS |
| CLOSE GATE all 3 phases complete | CLOSE-GATE.md | YES | grep "All 3 phases complete: YES" CLOSE-GATE.md | PASS |
| CLOSE GATE §1.4 grep zero | raw/gates-checks.log | 0 across all checks | grep "0 matches" raw/gates-checks.log | PASS |
| Remote push (branches + tags) | remote-proof.txt | pushed to git.cloud-dog.net | git ls-remote origin | PASS |
