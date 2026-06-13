#!/usr/bin/env bash
# TaskCreated event hook (v0.13.0 Phase 0b).
#
# Per Claude Code Hooks spec, TaskCreated does not accept a matcher and fires
# unconditionally whenever the TaskCreate tool runs. We normalize the payload
# at the top of the script and apply gate logic, then return either:
#   - empty {} on allow (pass-through)
#   - JSON {"continue": false, "stopReason": "..."} on hard stop
#
# Use case (v0.13.0 採用方針 — see docs/plans/v0130-modernization-plan.md Rev.5
# Round 4-C):
#   TaskCreated = safety-boundary violation = hard stop (continue:false).
#   Example: plan gate is `pending` and phase is `implement` → block creating
#   any new implementation Task until plan is approved.
#
# raw_input fail-safe: if the payload cannot be parsed, dump to
# .claude/.task-event-debug.log (gitignored) and pass through, so the
# unparseable event does not silently break the session.
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
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Allow ROOT override via env (test fixtures use this to isolate from real aegis state).
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"
STATUS_FILE="${ROOT}/docs/STATUS.md"
DUMP_LOG="${ROOT}/.claude/.task-event-debug.log"

INPUT=$(cat)

# Normalize the payload: extract the task subject via python3 JSON probing.
# Per Claude Code Hooks reference, TaskCreated input uses `task_subject` and
# `task_description` (v0.13.0 Phase 0b NO-GO fix). Aegis previously probed
# only legacy / defensive keys; this revision probes the official keys first
# and falls back to the legacy keys for forward compat.
# Capture the interpreter exit code so a missing/broken python3 does NOT fail open.
# The hard-stop decision below depends only on STATUS.md (grep/sed, no python3),
# so the subject is needed only for the human-readable reason.
set +e
SUBJECT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
    # Top-level keys: official first (task_subject / task_description), then legacy.
    for key in ("task_subject", "task_description", "subject", "title", "description", "task"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            print(v)
            sys.exit(0)
    # Nested under common parent keys (defensive for wrapped payload shapes).
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
  # python3 unavailable/broken: do NOT fail open. The plan-gate check below is
  # python3-free, so fall through with a placeholder subject and evaluate it.
  SUBJECT="(subject unavailable: python3)"
elif [ -z "$SUBJECT" ]; then
  # python3 ran but found no recognizable subject = unrecognized payload shape.
  # Deliberate fail-safe: dump the raw payload and pass through (do not hard-stop
  # an event we could not understand).
  mkdir -p "$(dirname "$DUMP_LOG")"
  {
    printf '%s\n' "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] check-task-created: unparseable payload"
    printf '%s\n---\n' "$INPUT"
  } >> "$DUMP_LOG" 2>/dev/null || true
  emit_allow
  exit 0
fi

# If STATUS.md doesn't exist (e.g. test scaffold), pass through.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Extract plan gate and current phase.
PLAN_GATE=$(frontmatter_section "$STATUS_FILE" gate_approvals | grep -m1 "plan:" | sed "s/.*plan:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
PHASE=$(grep -m1 "^phase:" "$STATUS_FILE" | sed "s/^phase:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

# Hard-stop condition: phase=implement AND plan gate is not approved/n/a.
# Other phases (brainstorm, plan, review, qa, security, deploy, ship, docs) allow
# task management even before plan approval — TaskCreate is legitimate sub-task
# planning in those contexts.
if [ "$PHASE" = "implement" ] && [ "$PLAN_GATE" != "approved" ] && [ "$PLAN_GATE" != "n/a" ]; then
  # Build reason. Sanitize the external subject to a single printable line:
  # collapse ALL control chars (0x00-0x1F + DEL) to space, so emit.sh — which
  # only escapes structural JSON chars — never receives a raw control byte that
  # would make the hard-stop JSON malformed (Round 3 P1: malformed JSON on a
  # safety-boundary hard stop = fail-open).
  SUBJECT_PREVIEW=$(printf '%s' "$SUBJECT" | head -c 80 | tr '\000-\037\177' ' ')
  REASON=$(printf '[task-created] phase=implement で plan gate=%s。TaskCreate (subject: %s) を hard stop。先に /gate approve plan を実行してください。' "$PLAN_GATE" "$SUBJECT_PREVIEW")
  # TaskCreated uses {"continue": false, "stopReason": "..."} per v0.13.0 採用方針 (Round 4-C).
  emit_continue_false "$REASON"
  exit 0
fi

# Pass-through.
emit_allow
exit 0
