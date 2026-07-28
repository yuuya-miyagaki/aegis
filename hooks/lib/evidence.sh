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
#   For NON-test-runner commands (M4) fp is the literal "skipped" and
#   marker_verified is false — the reader ignores those entries, so the heavy
#   fingerprint/marker computation is skipped on the hot path.
# record-test-result.py appends the same schema with src:"manual". A manual
# green may additionally carry an optional "marker": true (iter71 SF-014
# audit field; not consumed by the judge).
# attest-test-run.py (iter78) appends src:"attested" entries with additive
# "counts" (structured event tallies) and "exit" fields — the ONLY src that
# can certify a pytest-family green in the judge.
#
# Source: source "$(dirname "$0")/lib/evidence.sh"

_EV_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_EV_LIB_DIR}/extract-input.sh"
source "${_EV_LIB_DIR}/emit.sh"
source "${_EV_LIB_DIR}/fingerprint.sh"
# C-2 (v1.6.1): the marker-verify check needs AEGIS_TEST_PASS_MARKER_REGEX.
# patterns.sh stays sourced here for is_test_runner_cmd (AEGIS_TEST_RUNNER_REGEX).
source "${_EV_LIB_DIR}/patterns.sh"
# iter71 (SF-014): the 4-stage marker core now lives in marker.sh (single
# implementation shared with record/drill). Its internal re-source of
# patterns.sh is idempotent variable assignment — harmless duplicate load.
# Guarded like the other optional libs: a bare `source missing.sh || true` is
# fatal under a caller's `set -e` (session-start.sh), so gate on -f. A missing
# marker.sh leaves aegis_marker_verdict undefined -> _check_test_marker's
# delegation fails -> verdict "false" (fail-closed on a gutted install).
if [ -f "${_EV_LIB_DIR}/marker.sh" ]; then
  source "${_EV_LIB_DIR}/marker.sh"
fi

AEGIS_EVIDENCE_MAX_BYTES="${AEGIS_EVIDENCE_MAX_BYTES:-1048576}"

evidence_log_path() { printf '%s/.claude/evidence-log.jsonl' "${1:-.}"; }

# _check_test_marker <raw-hook-input-json> — print "true" / "false".
# Decides whether the recorded tool_response demonstrates an ACTUAL test
# execution (not just a runner-named command that echoed forged text).
#
# iter71 (SF-014): the 4-stage verdict (NO_RUN flag → STRONG marker → WEAK
# pair → zero-run gate) now has a SINGLE implementation in marker.sh
# (aegis_marker_verdict), shared with record-test-result.py and the B1 drill.
# This wrapper does only what is hook-specific: (a) extract cmd/output/exitCode
# from the raw hook JSON via python3, (b) build a head+tail 4 KiB output window
# so a verbose run keeps both the pytest prologue and the summary line, and
# (c) delegate the verdict to aegis_marker_verdict.
#
# The COMMAND text is required by Stage 1; we extract it via python3. If python3
# is unavailable the output cannot be safely parsed → "false" (fail-closed).
_check_test_marker() {
  local input="$1" out cmd exit_code
  # Extract command (head 4 KiB), output (tail 4 KiB), and exitCode via a
  # single python3 pass. Claude Code uses camelCase `exitCode` in
  # tool_response; we accept either spelling for forward-compat.
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
    ec = tr.get("exitCode")
    if ec is None:
        ec = tr.get("exit_code")
    if isinstance(ec, bool) or not isinstance(ec, int):
        ec = ""
    else:
        ec = str(ec)
    # K-1 axis 3 keeps a pytest prologue regex (`platform / rootdir /
    # collected`); a verbose run with >4 KiB of progress lines would
    # truncate the prologue out of a tail-only window and force every
    # real test run to false. Take both ends (~4 KiB each) so prologue
    # and summary survive. grill-code Critical 2.
    HEAD_MAX = 4096
    TAIL_MAX = 4096
    if len(o) <= HEAD_MAX + TAIL_MAX:
        o_window = o
    else:
        o_window = o[:HEAD_MAX] + "\n...[aegis-truncated]...\n" + o[-TAIL_MAX:]
    # Separator unlikely to appear in any field.
    sys.stdout.write(
        c[:4096] + "\x1eAEGISSEP\x1e" + o_window + "\x1eAEGISSEP\x1e" + ec
    )
except Exception:
    pass
' 2>/dev/null) || extracted=""
  if [ -z "$extracted" ]; then
    printf 'false'
    return 0
  fi
  # Split on the separator. extracted = cmd ⌷ out ⌷ exit_code
  local _SEP=$'\x1e'AEGISSEP$'\x1e'
  cmd="${extracted%%${_SEP}*}"
  local _rest="${extracted#*${_SEP}}"
  out="${_rest%%${_SEP}*}"
  exit_code="${_rest#*${_SEP}}"
  # When extraction missed a separator, exit_code may equal _rest itself.
  if [ "$exit_code" = "$_rest" ]; then
    exit_code=""
  fi
  if [ -z "$out" ]; then
    printf 'false'
    return 0
  fi
  # Stages 1-4 moved to marker.sh (iter71 SF-014 shared positive-proof core).
  # Any non-"true" outcome — including rc3 evaluation-impossible — maps to
  # "false": identical on all normal paths, fail-closed on a gutted install
  # (a HALF-loaded patterns.sh that previously skipped Stage 1 now yields
  # rc3 -> false instead of a possible true).
  local verdict
  verdict="$(printf '%s' "$out" | aegis_marker_verdict "$exit_code" "$cmd" 2>/dev/null)" || verdict="false"
  if [ "$verdict" = "true" ]; then
    printf 'true'
  else
    printf 'false'
  fi
}

# is_test_runner_cmd <cmd> — print "true" if <cmd> is a test-runner invocation,
# else "false". Single-source classifier shared by the evidence recorder
# (append_evidence), the ReAct hint (post-bash.sh), and — by construction of the
# same normalization + patterns — the gate-time reader (build-judge-card.
# read_test_result). Normalization mirrors the reader: newlines -> ';', quoted
# spans masked to the inert token Q (DQ then SQ, T1 v1.5.2), then
# AEGIS_TEST_RUNNER_REGEX. Any drift can only fail-closed: a missed runner
# records fp="skipped" -> the reader reports 🟡 unverified, never silent-green.
#
# Hot-path cost: ONE sed (two -e scripts, DQ then SQ — identical to two piped
# seds for s///g) + ONE grep (all patterns as -e args = OR, same as the reader's
# any()). The `[@]:-` default and the _ge-count guard keep it safe under
# `set -u` on bash 3.2 (macOS) when the array is somehow empty.
is_test_runner_cmd() {
  local cmd="$1" norm _re
  norm=$(printf '%s' "$cmd" | tr '\n' ';' \
    | sed -E -e "s/${AEGIS_TR_STRIP_DQ}/Q/g" -e "s/${AEGIS_TR_STRIP_SQ}/Q/g")
  local _ge=()
  for _re in "${AEGIS_TEST_RUNNER_REGEX[@]:-}"; do
    [ -n "$_re" ] && _ge+=(-e "$_re")
  done
  if [ "${#_ge[@]}" -gt 0 ] && printf '%s' "$norm" | grep -Eq "${_ge[@]}"; then
    printf 'true'
    return 0
  fi
  printf 'false'
  return 0
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
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts=""
  # M4 hot-path cost control: the fingerprint (git subprocesses + file reads)
  # and the marker check (python3 + greps) are ONLY consumed for test-runner
  # entries — build-judge-card.read_test_result ignores every other entry.
  # Compute them only when the command is a test runner (classified on the
  # truncated, to-be-stored cmd so the decision matches the reader's input
  # exactly); otherwise record a cheap entry with a non-hex fp sentinel that
  # can never certify green. A misclassification only fails closed (sentinel
  # fp != current fp -> 🟡 unverified), never silent-green.
  if [ "$(is_test_runner_cmd "$cmd")" = "true" ]; then
    fp="$(fingerprint_worktree "$root" 2>/dev/null)" || fp="error"
    marker_verified="$(_check_test_marker "$input" 2>/dev/null)" || marker_verified="false"
  else
    fp="skipped"
    marker_verified="false"
  fi
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
