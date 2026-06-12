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
# Extracts tool_response.output and checks if ANY pattern in
# AEGIS_TEST_PASS_MARKER_REGEX matches a real summary line in the output.
# If python3 is unavailable, the output cannot be extracted → "false"
# (fail-closed in the sense that the entry will not be honored as green).
_check_test_marker() {
  local input="$1" out pat
  out=$(printf '%s' "$input" | python3 -c '
import sys, json
try:
    d = json.loads(sys.stdin.read())
    tr = d.get("tool_response") or {}
    o = tr.get("output", "") or ""
    if isinstance(o, list):
        o = "".join(str(x) for x in o)
    elif not isinstance(o, str):
        o = str(o)
    sys.stdout.write(o[-4096:])
except Exception:
    pass
' 2>/dev/null) || out=""
  if [ -z "$out" ]; then
    printf 'false'
    return 0
  fi
  if [ "${#AEGIS_TEST_PASS_MARKER_REGEX[@]}" -eq 0 ]; then
    printf 'false'
    return 0
  fi
  for pat in "${AEGIS_TEST_PASS_MARKER_REGEX[@]}"; do
    if printf '%s' "$out" | grep -qE "$pat"; then
      printf 'true'
      return 0
    fi
  done
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
