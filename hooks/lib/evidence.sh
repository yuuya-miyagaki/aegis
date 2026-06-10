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

AEGIS_EVIDENCE_MAX_BYTES="${AEGIS_EVIDENCE_MAX_BYTES:-1048576}"

evidence_log_path() { printf '%s/.claude/evidence-log.jsonl' "${1:-.}"; }

# append_evidence <root> <ok|fail> <raw-hook-input-json>  — always returns 0.
append_evidence() {
  local root="$1" status="$2" input="$3"
  local log cmd payload_sha fp ts
  log="$(evidence_log_path "$root")"
  mkdir -p "$(dirname "$log")" 2>/dev/null || return 0
  cmd="$(extract_command "$input" 2>/dev/null)" || cmd=""
  cmd="${cmd:0:500}"
  payload_sha="$(printf '%s' "${input:0:65536}" | _fp_sha256 2>/dev/null)" || payload_sha=""
  fp="$(fingerprint_worktree "$root" 2>/dev/null)" || fp="error"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts=""
  printf '{"v":1,"ts":"%s","src":"observed","cmd":"%s","status":"%s","payload_sha":"%s","fp":"%s"}\n' \
    "$ts" "$(_aegis_json_escape "$cmd")" "$status" "$payload_sha" "$fp" \
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
