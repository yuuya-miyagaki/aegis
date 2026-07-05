#!/usr/bin/env bash
# v1.6.2 Red-team PoC rerun harness.
#
# Re-runs the original attack PoCs from full-review-2026-06-13.md against
# the v1.6.2 hooks and asserts they all fail-closed.
#
# Usage:
#   bash tests/poc/v162-redteam-rerun.sh             # all PoCs
#   bash tests/poc/v162-redteam-rerun.sh REDTEAM-01  # single PoC
#
# Exit codes:
#   0 — all PoCs intercepted (ASK / DENY)
#   1 — at least one PoC slipped through (allow)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0
FAIL=0
TOTAL=0

_assert_blocked() {
  local label="$1" hook="$2" cmd="$3"
  local payload out
  payload=$(printf '{"tool_name":"Bash","tool_input":{"command":%s}}' \
            "$(python3 -c 'import sys,json; print(json.dumps(sys.argv[1]))' "$cmd")")
  out=$(printf '%s' "$payload" | bash "$ROOT/hooks/$hook" 2>&1)
  TOTAL=$((TOTAL+1))
  if printf '%s' "$out" | grep -q '"permissionDecision":"\(deny\|ask\)"'; then
    printf '  ✓ %s blocked\n' "$label"
    PASS=$((PASS+1))
  else
    printf '  ✗ %s SLIPPED THROUGH: %s\n' "$label" "${out:0:200}"
    FAIL=$((FAIL+1))
  fi
}

# iter57: the stable-CP moat moved from the static check-control-plane.sh
# (retired) to the OS lock (hooks/lib/cp-lock.sh). The obfuscated write forms
# the old regex chased (cmdsub / backtick / printf -v / read / eval) are now
# blocked form-independently at the syscall: under lock the redirect target is
# read-only, so the write fails (EACCES) and the file stays INTACT. Assert on
# the FILE (unchanged), not a permissionDecision marker — the lock is not a
# hook that emits one. Mirrors tests/test_cp_lock_sf_catalog.py in this harness.
_assert_oslock_intact() {
  local label="$1" cmd="$2"
  if [ "$(id -u)" = "0" ]; then
    printf '  ⚠ %s skipped (root ignores a-w)\n' "$label"
    return 0
  fi
  local tmp before after
  tmp=$(mktemp -d)
  mkdir -p "$tmp/hooks/lib"
  printf 'SENTINEL\n' > "$tmp/hooks/lib/emit.sh"
  before=$(cat "$tmp/hooks/lib/emit.sh")
  ( source "$ROOT/hooks/lib/cp-lock.sh" && aegis_cp_lock "$tmp" ) >/dev/null 2>&1
  ( cd "$tmp" && eval "$cmd" ) >/dev/null 2>&1 || true
  after=$(cat "$tmp/hooks/lib/emit.sh" 2>/dev/null || printf '__UNREADABLE__')
  ( source "$ROOT/hooks/lib/cp-lock.sh" && aegis_cp_unlock "$tmp" ) >/dev/null 2>&1
  TOTAL=$((TOTAL+1))
  if [ "$after" = "$before" ]; then
    printf '  ✓ %s blocked by OS-lock (file INTACT)\n' "$label"
    PASS=$((PASS+1))
  else
    printf '  ✗ %s MODIFIED LOCKED FILE → %s\n' "$label" "${after:0:80}"
    FAIL=$((FAIL+1))
  fi
  rm -rf "$tmp" 2>/dev/null || { chmod -R u+w "$tmp" 2>/dev/null; rm -rf "$tmp"; }
}

_check_marker() {
  local label="$1" input="$2" expected="$3"
  local out
  out=$(printf '%s' "$input" | bash -c "source '$ROOT/hooks/lib/evidence.sh'; _check_test_marker \"\$(cat)\"")
  TOTAL=$((TOTAL+1))
  if [ "$out" = "$expected" ]; then
    printf '  ✓ %s → marker_verified=%s\n' "$label" "$out"
    PASS=$((PASS+1))
  else
    printf '  ✗ %s — expected %s, got %s\n' "$label" "$expected" "$out"
    FAIL=$((FAIL+1))
  fi
}

run_REDTEAM_01() {
  printf 'REDTEAM-01 (test-marker forge):\n'
  _check_marker "pytest -k __NEVER__ + echo forge" \
    '{"tool_name":"Bash","tool_input":{"command":"echo \"===== 3 passed in 0.42s =====\"; pytest -k __NEVER__"},"tool_response":{"output":"===== 3 passed in 0.42s =====\ncollected 0 items\n","exitCode":5}}' \
    "false"
}

run_REDTEAM_01b() {
  # grill-code Critical 2 (v1.6.2): >4 KiB verbose pytest output truncated to
  # tail-only window drops the prologue and downgrades real test runs to
  # false. Verify head+tail extraction keeps a real run verified.
  printf 'REDTEAM-01b (large-output prologue preservation, grill-code Critical 2):\n'
  local prologue middle summary output input
  prologue='platform darwin -- Python 3.11.5, pytest-7.4.3\nrootdir: /tmp/proj\ncollected 200 items\n\n'
  # Build a 200-line middle ~ 8 KB
  middle=$(python3 -c "print('\\n'.join(f'tests/test_module_{i:03d}.py::test_{i:03d} PASSED [{i//2:2d}%]' for i in range(200)))")
  middle="${middle}\n"
  summary='\n===== 200 passed in 12.34s =====\n'
  # Compose JSON via python so escapes are correct
  input=$(python3 -c "
import json, sys
prologue = sys.argv[1].replace('\\\\n','\n')
middle   = sys.argv[2].replace('\\\\n','\n')
summary  = sys.argv[3].replace('\\\\n','\n')
print(json.dumps({'tool_name':'Bash','tool_input':{'command':'pytest -v'},'tool_response':{'output':prologue+middle+summary,'exitCode':0}}))
" "$prologue" "$middle" "$summary")
  _check_marker "verbose pytest (200 tests, >8 KiB output)" "$input" "true"
}

run_REDTEAM_02() {
  # iter57: control-plane cmdsub bypass — the moat moved from the retired static
  # check-control-plane.sh to the OS lock. These obfuscated forms are now
  # blocked form-independently at the syscall (EACCES), so we assert the locked
  # file stays INTACT rather than expecting a permissionDecision marker.
  printf 'REDTEAM-02 (control-plane cmdsub bypass → OS-lock, iter57):\n'
  _assert_oslock_intact "cmdsub-quoted"   '> "$(echo hooks)/lib/emit.sh"'
  _assert_oslock_intact "cmdsub-unquoted" '> $(echo hooks)/lib/emit.sh'
  _assert_oslock_intact "backtick"        '> `echo hooks`/lib/emit.sh'
  _assert_oslock_intact "printf -v"       'printf -v D %s hooks; > $D/lib/emit.sh'
  _assert_oslock_intact "read"            'read D <<<hooks; > $D/lib/emit.sh'
  _assert_oslock_intact "eval"            'eval "D=hooks"; > $D/lib/emit.sh'
}

run_REDTEAM_02b() {
  # grill-code Critical 1 (v1.6.2) originally: a harmless first redirect hid an
  # evil second-or-later one. iter57: likewise now the OS lock's job — a benign
  # redirect to an unlocked sink cannot smuggle a later write into the locked CP.
  printf 'REDTEAM-02b (multi-redirect bypass → OS-lock, iter57):\n'
  _assert_oslock_intact "2nd-redirect-cmdsub"  'echo a > sink; > $(echo hooks)/lib/emit.sh'
  _assert_oslock_intact "2nd-append-cmdsub"    'echo a > sink && echo b >> $(echo hooks)/lib/emit.sh'
  _assert_oslock_intact "3rd-redirect-backtick" 'a > sink1; b > sink2; c > `echo hooks`/lib/emit.sh'
}

run_REDTEAM_03() {
  printf 'REDTEAM-03 (secrets quoted var):\n'
  _assert_blocked "double-quote \${F}" check-secrets.sh 'F=.env; git add "${F}"'
  _assert_blocked "double-quote \$F"   check-secrets.sh 'F=.env; git add "$F"'
  _assert_blocked "single-quote"       check-secrets.sh "F=.env; git add '\${F}'"
}

run_REDTEAM_04() {
  printf 'REDTEAM-04 (secrets cmdsub-built git):\n'
  _assert_blocked "cmdsub git add .env" check-secrets.sh '$(echo git) add .env'
  _assert_blocked "backtick git add"    check-secrets.sh '`echo git` add .env'
  _assert_blocked "cmdsub + .pem"       check-secrets.sh '$(echo git) add server.pem'
}

run_F_01_safety_lib_missing() {
  printf 'F-01 (lib missing fail-closed):\n'
  local tmp
  tmp=$(mktemp -d)
  cp -r "$ROOT/hooks" "$tmp/hooks"
  rm "$tmp/hooks/lib/emit.sh"
  mkdir -p "$tmp/docs"
  printf -- '---\nframework: aegis\nmode: Dev\nphase: implement\ntask_type: feature\n---\n' \
    > "$tmp/docs/STATUS.md"
  local payload out
  payload='{"tool_name":"Bash","tool_input":{"command":"ls"}}'
  out=$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$tmp" bash "$tmp/hooks/check-runtime-state.sh")
  TOTAL=$((TOTAL+1))
  if printf '%s' "$out" | grep -q '"permissionDecision":"deny"'; then
    printf '  ✓ emit.sh missing → explicit deny\n'
    PASS=$((PASS+1))
  else
    printf '  ✗ FAIL-OPEN — emit.sh missing did not deny: %s\n' "${out:0:200}"
    FAIL=$((FAIL+1))
  fi
  rm -rf "$tmp"
}

# Run requested PoC or all.
if [ "${1:-all}" = "all" ]; then
  run_REDTEAM_01
  run_REDTEAM_01b
  run_REDTEAM_02
  run_REDTEAM_02b
  run_REDTEAM_03
  run_REDTEAM_04
  run_F_01_safety_lib_missing
else
  case "$1" in
    REDTEAM-01)  run_REDTEAM_01 ;;
    REDTEAM-01b) run_REDTEAM_01b ;;
    REDTEAM-02)  run_REDTEAM_02 ;;
    REDTEAM-02b) run_REDTEAM_02b ;;
    REDTEAM-03)  run_REDTEAM_03 ;;
    REDTEAM-04)  run_REDTEAM_04 ;;
    F-01)        run_F_01_safety_lib_missing ;;
    *) printf 'Unknown PoC: %s\n' "$1" >&2; exit 2 ;;
  esac
fi

printf '\nSummary: %d/%d passed (%d failed)\n' "$PASS" "$TOTAL" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
