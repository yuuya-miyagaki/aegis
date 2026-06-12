#!/usr/bin/env bash
# Evidence log writer — append-only observation of Bash executions (E1).
#
# Policy (docs/hook-failure-policy.md): recording is fail-open BY DESIGN —
# the observer must never break the session. A missing record fail-closes at
# the DECISION point instead (judge card reports 🟡 unverified), so a dead
# observer can degrade but never silently certify.
#
# Schema (one JSON line per execution):
#   {"v":1,"ts":"<utc>","src":"observed","cmd":"<first 500 chars>",
#    "status":"ok|fail","payload_sha":"<sha256 of first 64KB of raw hook
#    stdin>","fp":"<fingerprint.sh token>"}
# record-test-result.py appends the same schema with src:"manual".
#
# Source: source "$(dirname "$0")/lib/evidence.sh"

_EV_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_EV_LIB_DIR}/extract-input.sh"
source "${_EV_LIB_DIR}/emit.sh"
source "${_EV_LIB_DIR}/fingerprint.sh"
# C-2 (v1.6.1): the marker-verify check needs AEGIS_TEST_PASS_MARKER_REGEX.
source "${_EV_LIB_DIR}/patterns.sh"

AEGIS_EVIDENCE_MAX_BYTES="${AEGIS_EVIDENCE_MAX_BYTES:-1048576}"

evidence_log_path() { printf '%s/.claude/evidence-log.jsonl' "${1:-.}"; }

# _check_test_marker <raw-hook-input-json> — print "true" / "false".
# Decides whether the recorded tool_response demonstrates an ACTUAL test
# execution (not just a runner-named command that echoed forged text).
#
# Three-stage gate (all stages must pass for "true"):
#   (1) No-run flag check — if the command itself contains a no-run flag
#       like `--version`, `--collect-only`, `-h`, `--dry-run`, no test ran
#       regardless of output → "false". (Closes the
#       `echo "===== 1 passed in 0.01s =====" && pytest --collect-only`
#       grill-code A-Crit-2 / B-Critical forge.)
#   (2) Strong markers (AEGIS_TEST_PASS_MARKER_REGEX) — single-line
#       sufficient for verification. pytest === summary, jest "Tests:",
#       go "ok pkg X.Xs", etc. Any hit → "true".
#   (3) Weak markers (AEGIS_TEST_PASS_MARKER_PAIRS) — each entry is
#       "ANCHOR|||COMPANION"; BOTH halves must hit the output. unittest
#       and cargo: `Ran N tests in` + `OK`/`FAILED`, `running N tests`
#       + `test result: ok./FAILED.`. Single-line forge (e.g. echo OK
#       alone) does not satisfy.
#
# Stage 1 also requires the COMMAND text; we extract it via python3.
# If python3 is unavailable the output cannot be safely parsed → "false"
# (fail-closed).
_check_test_marker() {
  local input="$1" out cmd pat split anchor companion
  # Extract output (tail 4 KiB) and command via a single python3 pass.
  local extracted
  extracted=$(printf '%s' "$input" | python3 -c '
import sys, json
try:
    d = json.loads(sys.stdin.read())
    tr = d.get("tool_response") or {}
    o = tr.get("output", "") or ""
    if isinstance(o, list):
        o = "".join(str(x) for x in o)
    elif not isinstance(o, str):
        o = str(o)
    c = (d.get("tool_input") or {}).get("command", "") or ""
    if not isinstance(c, str):
        c = str(c)
    # Separator unlikely to appear in either field.
    sys.stdout.write(c[:4096] + "\x1eAEGISSEP\x1e" + o[-4096:])
except Exception:
    pass
' 2>/dev/null) || extracted=""
  if [ -z "$extracted" ]; then
    printf 'false'
    return 0
  fi
  cmd="${extracted%%$'\x1e'AEGISSEP$'\x1e'*}"
  out="${extracted##*$'\x1e'AEGISSEP$'\x1e'}"
  if [ -z "$out" ]; then
    printf 'false'
    return 0
  fi
  # Stage 1: no-run flag in the command disqualifies regardless of output.
  if [ -n "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] && \
     printf '%s' "$cmd" | grep -qE "$AEGIS_TEST_NO_RUN_FLAG_REGEX"; then
    printf 'false'
    return 0
  fi
  # Stage 2: strong markers — any single hit verifies.
  if [ "${#AEGIS_TEST_PASS_MARKER_REGEX[@]}" -gt 0 ]; then
    for pat in "${AEGIS_TEST_PASS_MARKER_REGEX[@]}"; do
      if printf '%s' "$out" | grep -qE "$pat"; then
        printf 'true'
        return 0
      fi
    done
  fi
  # Stage 3: weak pairs — BOTH halves must hit.
  if [ "${#AEGIS_TEST_PASS_MARKER_PAIRS[@]}" -gt 0 ]; then
    for split in "${AEGIS_TEST_PASS_MARKER_PAIRS[@]}"; do
      anchor="${split%%\|\|\|*}"
      companion="${split##*\|\|\|}"
      if [ -z "$anchor" ] || [ -z "$companion" ] || [ "$anchor" = "$split" ]; then
        continue
      fi
      if printf '%s' "$out" | grep -qE "$anchor" && \
         printf '%s' "$out" | grep -qE "$companion"; then
        printf 'true'
        return 0
      fi
    done
  fi
  printf 'false'
}

# append_evidence <root> <ok|fail> <raw-hook-input-json>  — always returns 0.
append_evidence() {
  local root="$1" status="$2" input="$3"
  local log cmd payload_sha fp ts marker_verified
  log="$(evidence_log_path "$root")"
  mkdir -p "$(dirname "$log")" 2>/dev/null || return 0
  cmd="$(extract_command "$input" 2>/dev/null)" || cmd=""
  cmd="${cmd:0:500}"
  payload_sha="$(printf '%s' "${input:0:65536}" | _fp_sha256 2>/dev/null)" || payload_sha=""
  fp="$(fingerprint_worktree "$root" 2>/dev/null)" || fp="error"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts=""
  marker_verified="$(_check_test_marker "$input" 2>/dev/null)" || marker_verified="false"
  printf '{"v":1,"ts":"%s","src":"observed","cmd":"%s","status":"%s","payload_sha":"%s","fp":"%s","marker_verified":%s}\n' \
    "$ts" "$(_aegis_json_escape "$cmd")" "$status" "$payload_sha" "$fp" "$marker_verified" \
    >> "$log" 2>/dev/null || true
  return 0
}

# rotate_evidence_log <root> — size-capped rotation + liveness touch.
# The touched (possibly empty) file is the "observer layer alive" signal
# consumed by check-task-completed.sh; rotation keeps one .1 generation,
# which read_test_result also scans.
rotate_evidence_log() {
  local root="$1" log size
  log="$(evidence_log_path "$root")"
  mkdir -p "$(dirname "$log")" 2>/dev/null || return 0
  if [ -f "$log" ]; then
    size=$(wc -c < "$log" 2>/dev/null | tr -d '[:space:]') || size=0
    if [ "${size:-0}" -gt "$AEGIS_EVIDENCE_MAX_BYTES" ]; then
      mv -f "$log" "${log}.1" 2>/dev/null || true
    fi
  fi
  : >> "$log" 2>/dev/null || true
  return 0
}
