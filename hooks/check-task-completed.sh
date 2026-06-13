#!/usr/bin/env bash
# TaskCompleted event hook (v0.13.0 Phase 0b).
#
# Per Claude Code Hooks spec, TaskCompleted does not accept a matcher and fires
# unconditionally whenever a task is marked complete. We normalize the payload
# at the top of the script and apply integrity checks.
#
# Use case (v0.13.0 採用方針 — see docs/plans/v0130-modernization-plan.md Rev.5
# Round 4-C):
#   TaskCompleted = minor inconsistency = 差し戻し (exit 2 + stderr).
#   Example: STATUS.md `next_action` is empty when a task completion is signaled
#   → push back via exit 2 so the model receives the feedback and can correct
#     the report, without halting the entire teammate session.
#
# raw_input fail-safe: dump unparseable payloads to .claude/.task-event-debug.log
# (gitignored) and pass through.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# AEGIS_SAFETY_FALLBACK_BEGIN
if [ ! -r "${SCRIPT_DIR}/lib/safety.sh" ]; then
  printf '[aegis-safety] fail-closed: safety.sh not readable\n' >&2
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}}'
  exit 0
fi
set +e
source "${SCRIPT_DIR}/lib/safety.sh" 2>/dev/null
_aegis_safety_rc=$?
set -e
if [ "$_aegis_safety_rc" -ne 0 ]; then
  printf '[aegis-safety] fail-closed: safety.sh source failed\n' >&2
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}}'
  exit 0
fi
# AEGIS_SAFETY_FALLBACK_END
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Allow ROOT override via env (test fixtures use this to isolate from real aegis state).
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"
STATUS_FILE="${ROOT}/docs/STATUS.md"
DUMP_LOG="${ROOT}/.claude/.task-event-debug.log"

INPUT=$(cat)

# Normalize payload via python3 JSON probing.
# Per Claude Code Hooks reference, TaskCompleted input uses `task_subject` and
# `task_description` (v0.13.0 Phase 0b NO-GO fix). Official keys probed first,
# legacy keys kept as forward-compat fallback.
# Capture the interpreter exit code so a missing/broken python3 does NOT fail
# open (P3-1, policy: moat → 差し戻し). Same shape as check-task-created.sh.
set +e
SUBJECT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
    for key in ("task_subject", "task_description", "subject", "title", "description", "task"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            print(v)
            sys.exit(0)
    for parent in ("tool_input", "task", "input"):
        sub = data.get(parent) or {}
        if isinstance(sub, dict):
            for key in ("task_subject", "task_description", "subject", "title", "description"):
                v = sub.get(key)
                if isinstance(v, str) and v.strip():
                    print(v)
                    sys.exit(0)
    print("")
except Exception:
    print("")
' 2>/dev/null)
PY_RC=$?
set -e

if [ "$PY_RC" -ne 0 ]; then
  # python3 unavailable/broken: do NOT fail open. The next_action check below
  # is python3-free; the evidence check failure path also closes (policy: moat).
  SUBJECT="(subject unavailable: python3)"
elif [ -z "$SUBJECT" ]; then
  # python3 ran but found no recognizable subject = unrecognized payload shape.
  # Deliberate fail-safe: dump and pass through (parse failure ≠ dependency loss).
  mkdir -p "$(dirname "$DUMP_LOG")"
  {
    printf '%s\n' "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] check-task-completed: unparseable payload"
    printf '%s\n---\n' "$INPUT"
  } >> "$DUMP_LOG" 2>/dev/null || true
  emit_allow
  exit 0
fi

if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Extract next_action from STATUS.md.
NEXT_ACTION=$(grep -m1 "^next_action:" "$STATUS_FILE" | sed "s/^next_action:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

# Strip whitespace.
NEXT_ACTION_STRIPPED=$(printf '%s' "$NEXT_ACTION" | tr -d '[:space:]')

# 差し戻し condition: next_action is empty or null.
# This catches cases where the model marks a task complete without updating
# STATUS.md to reflect what's next.
if [ -z "$NEXT_ACTION_STRIPPED" ] || [ "$NEXT_ACTION_STRIPPED" = "null" ]; then
  SUBJECT_PREVIEW=$(printf '%s' "$SUBJECT" | head -c 80 | tr '\n' ' ')
  # TaskCompleted uses exit 2 + stderr for 差し戻し per v0.13.0 採用方針 (Round 4-C).
  # The model receives the stderr text as feedback and can correct the report.
  printf '[task-completed] TaskCompleted (subject: %s) しましたが STATUS.md next_action が未更新です。完了前に next_action を更新してください。\n' "$SUBJECT_PREVIEW" >&2
  exit 2
fi

# E1: observer liveness. The evidence log file is created/touched by
# session-start (rotate_evidence_log) on EVERY session, so its absence means
# the hook layer never ran in this workspace (the silent fail-open class found
# in v1.4.0 grill: CLAUDE_PROJECT_DIR unset). An empty file passes — only
# total absence pushes back. Policy: moat → 差し戻し.
if [ ! -f "${ROOT}/.claude/evidence-log.jsonl" ]; then
  printf '[task-completed] evidence-log が存在しません（hook 観測系が未稼働の可能性）。hooks 配線と session-start の発火を確認してから完了してください。\n' >&2
  exit 2
fi

# Evidence integrity: reuse validate_status_file's gate/ref + existence checks
# at completion time. python3 absent -> 差し戻し (exit 2): completion evidence
# cannot be verified, so do not certify the completion (P3-1, policy: moat).
set +e
EVIDENCE=$(python3 "${DEFAULT_ROOT}/scripts/check_status.py" --root "$ROOT" --check-completion-evidence 2>/dev/null)
EV_RC=$?
set -e
if [ "$EV_RC" -ne 0 ] && [ -z "$EVIDENCE" ]; then
  printf '[task-completed] evidence 整合性を検証できません（python3 実行不能, rc=%s）。環境を復旧してから完了してください。\n' "$EV_RC" >&2
  exit 2
fi
if [ -n "$EVIDENCE" ]; then
  SUBJECT_PREVIEW=$(printf '%s' "$SUBJECT" | head -c 80 | tr '\n' ' ')
  printf '[task-completed] TaskCompleted (subject: %s) しましたが evidence 整合性に違反があります:\n%s\n完了前に STATUS.md を修正してください。\n' "$SUBJECT_PREVIEW" "$EVIDENCE" >&2
  exit 2
fi

# Pass-through.
emit_allow
exit 0
