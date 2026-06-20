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
# Pipeline:
#   (1) No-run flag check — if the command itself contains a no-run flag
#       like `--version`, `--collect-only`, `-h`, `--dry-run`, no test ran
#       regardless of output → "false". (Closes the
#       `echo "===== 1 passed in 0.01s =====" && pytest --collect-only`
#       grill-code A-Crit-2 / B-Critical forge.)
#   (2) Strong markers (AEGIS_TEST_PASS_MARKER_REGEX) — single-line
#       sufficient candidate. pytest === summary, jest "Tests:",
#       go "ok pkg X.Xs", etc. Any hit → proceed to zero-run gate.
#   (3) Weak markers (AEGIS_TEST_PASS_MARKER_PAIRS) — each entry is
#       "ANCHOR|||COMPANION"; BOTH halves must hit the output. unittest
#       and cargo: `Ran N tests in` + `OK`/`FAILED`, `running N tests`
#       + `test result: ok./FAILED.`. Any hit → proceed to zero-run gate.
#   (4) K-1 (v1.6.2) Zero-run gate — after a marker candidate, run three
#       independent axes:
#         Axis 1 (universal): output contains a zero-run regex
#         (`collected 0 items`, `no tests ran`, `Ran 0 tests`,
#         `test result: ok. 0 passed`, etc.) → "false".
#         Axis 2 (pytest only): exitCode == 5 (no tests collected) → "false".
#         Axis 3 (pytest only): strong marker hit but ZERO prologue lines
#         (platform/rootdir/collected/cachedir/plugins) → "false".
#       Axis 2 and 3 require the command to match
#       AEGIS_TEST_IS_PYTEST_REGEX. The gate ensures REDTEAM-01 and its
#       grill-derived variants (output filter / stderr suppression /
#       prologue-less forge) all fail-closed.
#
# Stage 1 also requires the COMMAND text; we extract it via python3.
# If python3 is unavailable the output cannot be safely parsed → "false"
# (fail-closed).
_check_test_marker() {
  local input="$1" out cmd pat split anchor companion exit_code
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
  # Stage 1: no-run flag in the command disqualifies regardless of output.
  if [ -n "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] && \
     printf '%s' "$cmd" | grep -qE "$AEGIS_TEST_NO_RUN_FLAG_REGEX"; then
    printf 'false'
    return 0
  fi
  # Stage 2 / 3: did any marker hit?
  local marker_hit=0
  if [ "${#AEGIS_TEST_PASS_MARKER_REGEX[@]}" -gt 0 ]; then
    for pat in "${AEGIS_TEST_PASS_MARKER_REGEX[@]}"; do
      if printf '%s' "$out" | grep -qE "$pat"; then
        marker_hit=1
        break
      fi
    done
  fi
  if [ $marker_hit -eq 0 ] && [ "${#AEGIS_TEST_PASS_MARKER_PAIRS[@]}" -gt 0 ]; then
    for split in "${AEGIS_TEST_PASS_MARKER_PAIRS[@]}"; do
      anchor="${split%%\|\|\|*}"
      companion="${split##*\|\|\|}"
      if [ -z "$anchor" ] || [ -z "$companion" ] || [ "$anchor" = "$split" ]; then
        continue
      fi
      if printf '%s' "$out" | grep -qE "$anchor" && \
         printf '%s' "$out" | grep -qE "$companion"; then
        marker_hit=1
        break
      fi
    done
  fi
  if [ $marker_hit -eq 0 ]; then
    printf 'false'
    return 0
  fi
  # Stage 4: zero-run gate (K-1 v1.6.2). The marker hit is necessary but
  # not sufficient — any axis below downgrades to false.
  # Axis 1: universal output zero-run regex.
  if [ "${#AEGIS_TEST_ZERO_RUN_REGEX[@]}" -gt 0 ]; then
    for pat in "${AEGIS_TEST_ZERO_RUN_REGEX[@]}"; do
      if printf '%s' "$out" | grep -qE "$pat"; then
        printf 'false'
        return 0
      fi
    done
  fi
  # Axes 2 & 3: only apply when the command is in the pytest family.
  local is_pytest=0
  if [ -n "${AEGIS_TEST_IS_PYTEST_REGEX:-}" ] && \
     printf '%s' "$cmd" | grep -qE "$AEGIS_TEST_IS_PYTEST_REGEX"; then
    is_pytest=1
  fi
  if [ $is_pytest -eq 1 ]; then
    # Axis 2: pytest exit 5 = no tests collected.
    if [ -n "$exit_code" ] && \
       [ "$exit_code" = "${AEGIS_TEST_ZERO_RUN_EXIT_PYTEST:-5}" ]; then
      printf 'false'
      return 0
    fi
    # Axis 3: strong marker hit but ZERO prologue lines.
    if [ "${#AEGIS_TEST_PROLOGUE_REGEX[@]}" -gt 0 ]; then
      local prologue_hit=0 ppat
      for ppat in "${AEGIS_TEST_PROLOGUE_REGEX[@]}"; do
        if printf '%s' "$out" | grep -qE "$ppat"; then
          prologue_hit=1
          break
        fi
      done
      if [ $prologue_hit -eq 0 ]; then
        printf 'false'
        return 0
      fi
    fi
  fi
  printf 'true'
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
