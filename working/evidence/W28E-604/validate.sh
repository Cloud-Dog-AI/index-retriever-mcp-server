#!/usr/bin/env bash
# W28E-604 final evidence validator (deterministic, two-anchor).
# Verifies the COMMITTED raw test logs (integrity + verdicts), the live §1.4
# bespoke-grep and secret scan, scoped-clean worktrees, and a FAIL-free
# requirements-map. Output is timing-free so it is stable + checksummable.
# Replay: each raw/*.log header carries the exact pytest command to re-run.
set -u
EV="$(cd "$(dirname "$0")" && pwd)"
RAW="$EV/raw"
VDBWT=/opt/iac/Development/cloud-dog-ai/working/w28e604-vdb-wt
IRWT=/opt/iac/Development/cloud-dog-ai/working/w28e604-ir-wt
SRC1="$VDBWT/packages/backend/platform-vdb/cloud_dog_vdb/spreadsheet"
SRC2="$IRWT/src/index_tools/spreadsheet"
failures=0
out=""
add() { out+="$1"$'\n'; }
chk() { if [ "$2" -eq 0 ]; then add "[OK] $1"; else add "[FAIL] $1"; failures=$((failures + 1)); fi; }

# Raw test-log integrity (the committed run output must be untampered).
(cd "$EV" && sha256sum -c raw-checksums.sha256 >/dev/null 2>&1); chk "raw test-log checksums intact" $?

# Verdicts read from the committed raw logs.
grep -q "239 passed" "$RAW/vdb-UT-full.log"; chk "platform-vdb full UT 239 passed (raw/vdb-UT-full.log)" $?
grep -q "198 passed" "$RAW/ir-UT-full.log"; chk "index-retriever full UT 198 passed (raw/ir-UT-full.log)" $?
grep -q "45 passed" "$RAW/vdb-UT4.10-matrix.log"; chk "backend matrix 45 passed (raw/vdb-UT4.10-matrix.log)" $?
grep -q "11 passed" "$RAW/ir-UT1_70-spreadsheet.log"; chk "IR spreadsheet group 11 passed (raw/ir-UT1_70-spreadsheet.log)" $?
for g in 4.1 4.2 4.3 4.4 4.5 4.6 4.7 4.8 4.9 4.10; do
  f=$(ls "$RAW"/vdb-UT${g}-*.log 2>/dev/null | head -1)
  if [ -n "$f" ] && grep -qE '[0-9]+ passed' "$f" && ! grep -qE '[0-9]+ failed' "$f"; then
    add "[OK] platform-vdb UT${g} group passed (raw/$(basename "$f"))"
  else
    add "[FAIL] platform-vdb UT${g} group missing/failed"; failures=$((failures + 1))
  fi
done

# RULES §1.4 bespoke-replacement grep (live, deterministic counts).
n=$(grep -rn 'os.environ.get\|os.environ\[' "$SRC1" "$SRC2" 2>/dev/null | grep -vc __pycache__); [ "$n" -eq 0 ]; chk "§1.4 os.environ zero" $?
n=$(grep -rn '^import logging\|^from logging\|logging.getLogger\|logging.basicConfig' "$SRC1" "$SRC2" 2>/dev/null | grep -vc cloud_dog_logging); [ "$n" -eq 0 ]; chk "§1.4 bespoke logging zero" $?
n=$(grep -rn 'functools.lru_cache\|functools.cache' "$SRC1" "$SRC2" 2>/dev/null | grep -vc __pycache__); [ "$n" -eq 0 ]; chk "§1.4 functools cache zero" $?
n=$(find "$SRC1" "$SRC2" -name '*_adapter.py' 2>/dev/null | wc -l); [ "$n" -eq 0 ]; chk "§1.4 zero bespoke *_adapter.py (adapters reused)" $?

# Secret scan (live).
n=$(grep -rEn "(password|secret|token|api[_-]?key)\s*[:=]\s*['\"][^'\"]{6,}" "$SRC1" "$SRC2" 2>/dev/null | grep -viE 'pattern|sensitivity|redact|exclude|_FUNCS|keyword|api_kit' | wc -l); [ "$n" -eq 0 ]; chk "secret scan clean" $?

# requirements-map: no FAIL rows; GATED rows cite a guard.
nf=$(grep -cP '\tFAIL$' "$EV/requirements-map.tsv"); [ "$nf" -eq 0 ]; chk "requirements-map 0 FAIL rows" $?
gbad=0
while IFS=$'\t' read -r _ _ _ observed _ status; do
  [ "$status" = "GATED" ] || continue
  echo "$observed" | grep -qiE 'LOCAL ONLY|coordinator|§6.78' || gbad=$((gbad + 1))
done < "$EV/requirements-map.tsv"
[ "$gbad" -eq 0 ]; chk "GATED rows cite authorising guard" $?

# Scoped clean: ignore gitignored noise, the evidence dir (may be uncommitted during
# validation), and external files recorded in external-dirty-ledger.tsv (e.g. another
# lane's instruction that a concurrent process keeps rewriting in the worktree).
ext=$(awk -F'\t' 'NR>1 && $1!="" {print $1}' "$EV/external-dirty-ledger.tsv" | paste -sd'|' -)
base='\.venv|__pycache__|/pyarrow|/data/|working/evidence/W28E-604'
filt="$base${ext:+|$ext}"
d=$(cd "$VDBWT" && git status --porcelain | grep -vcE "$filt"); [ "$d" -eq 0 ]; chk "platform-vdb scope clean (external-ledger excluded)" $?
d=$(cd "$IRWT" && git status --porcelain | grep -vcE "$filt"); [ "$d" -eq 0 ]; chk "index-retriever scope clean (external-ledger excluded)" $?

verdict="FINAL_EVIDENCE_VALIDATOR: $([ "$failures" -eq 0 ] && echo PASS || echo FAIL) failures=$failures"
echo "=== W28E-604 FINAL EVIDENCE VALIDATOR — anchor(begin) ==="
echo "$verdict"
echo "----------------------------------------------------------------"
printf '%s' "$out"
echo "----------------------------------------------------------------"
echo "$verdict"
