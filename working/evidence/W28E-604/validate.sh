#!/usr/bin/env bash
# W28E-604 final evidence validator. Re-runs the binding checks live and fails on
# any non-GATED requirement, §1.4 violation, dirty scope, checksum mismatch,
# secret hit, or test regression. Emits the exact gate line at the end.
set -u
EV="$(cd "$(dirname "$0")" && pwd)"
VDBWT=/opt/iac/Development/cloud-dog-ai/working/w28e604-vdb-wt
IRWT=/opt/iac/Development/cloud-dog-ai/working/w28e604-ir-wt
VDBP="$VDBWT/packages/backend/platform-vdb"
SRC1="$VDBP/cloud_dog_vdb/spreadsheet"
SRC2="$IRWT/src/index_tools/spreadsheet"
failures=0
note() { echo "[$1] $2"; }
fail() { failures=$((failures+1)); echo "[FAIL] $1"; }

# 1) RULES §1.4 bespoke-replacement grep == 0
n_env=$(grep -rn 'os.environ.get\|os.environ\[' "$SRC1" "$SRC2" 2>/dev/null | grep -vc __pycache__)
n_log=$(grep -rn '^import logging\|^from logging\|logging.getLogger\|logging.basicConfig' "$SRC1" "$SRC2" 2>/dev/null | grep -vc cloud_dog_logging)
n_cache=$(grep -rn 'functools.lru_cache\|functools.cache' "$SRC1" "$SRC2" 2>/dev/null | grep -vc __pycache__)
n_adapt=$(find "$SRC1" "$SRC2" -name '*_adapter.py' 2>/dev/null | wc -l)
if [ "$n_env" -eq 0 ] && [ "$n_log" -eq 0 ] && [ "$n_cache" -eq 0 ] && [ "$n_adapt" -eq 0 ]; then
  note OK "§1.4 grep zero (env=$n_env log=$n_log cache=$n_cache adapters=$n_adapt)"
else
  fail "§1.4 grep non-zero (env=$n_env log=$n_log cache=$n_cache adapters=$n_adapt)"
fi

# 2) scoped clean (gitignored filtered) both worktrees
d1=$(cd "$VDBWT" && git status --porcelain | grep -vcE '\.venv|__pycache__|/pyarrow')
d2=$(cd "$IRWT" && git status --porcelain | grep -vcE '\.venv|__pycache__|/data/')
[ "$d1" -eq 0 ] && note OK "platform-vdb scope clean" || fail "platform-vdb scope dirty ($d1)"
[ "$d2" -eq 0 ] && note OK "index-retriever scope clean" || fail "index-retriever scope dirty ($d2)"

# 3) requirements-map: no FAIL rows; GATED rows must cite a guard
nfail=$(grep -cP '\tFAIL$' "$EV/requirements-map.tsv")
[ "$nfail" -eq 0 ] && note OK "requirements-map has 0 FAIL rows" || fail "requirements-map has $nfail FAIL rows"
while IFS=$'\t' read -r _ _ _ observed _ status; do
  [ "$status" = "GATED" ] || continue
  echo "$observed" | grep -qiE 'LOCAL ONLY|confirm|§6.78|user' || fail "GATED row lacks guard citation: $observed"
done < "$EV/requirements-map.tsv"

# 4) secret scan over new src
nsec=$(grep -rEn "(password|secret|token|api[_-]?key)\s*[:=]\s*['\"][^'\"]{6,}" "$SRC1" "$SRC2" 2>/dev/null | grep -viE 'pattern|sensitivity|redact|exclude|_FUNCS|keyword|api_kit' | wc -l)
[ "$nsec" -eq 0 ] && note OK "secret scan clean" || fail "secret scan hits=$nsec"

# 5) checksums of static evidence
if (cd "$EV" && sha256sum -c CHECKSUMS.sha256 >/tmp/w28e604_cksum.txt 2>&1); then
  note OK "CHECKSUMS verified"
else
  fail "CHECKSUMS mismatch"; cat /tmp/w28e604_cksum.txt
fi

# 6) live test replay — platform-vdb UT
vdb_out=$(cd "$VDBP" && .venv/bin/python -m pytest tests/unit --env tests/env-UT -q -p no:cacheprovider 2>&1 | tail -1)
note INFO "platform-vdb UT: $vdb_out"
echo "$vdb_out" | grep -qE '239 passed' && note OK "platform-vdb UT 239 passed" || fail "platform-vdb UT not 239 passed"

# 7) live test replay — index-retriever UT
ir_out=$(cd "$IRWT" && .venv/bin/python -m pytest tests/unit --env tests/env-UT -q -p no:cacheprovider 2>&1 | tail -1)
note INFO "index-retriever UT: $ir_out"
echo "$ir_out" | grep -qE '198 passed' && note OK "index-retriever UT 198 passed" || fail "index-retriever UT not 198 passed"

echo "----------------------------------------------------------------"
echo "FINAL_EVIDENCE_VALIDATOR: $([ "$failures" -eq 0 ] && echo PASS || echo FAIL) failures=$failures"
