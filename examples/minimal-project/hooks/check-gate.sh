#!/usr/bin/env bash
# PreToolUse hook for Edit/Write: blocks code edits when plan gate is not approved.
# Also protects framework control files (hooks, scripts, .claude, CLAUDE.md)
# from edits during non-framework project work.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

# Read stdin (JSON with tool_input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Extract file_path from tool_input.
TARGET_FILE=$(extract_file_path "$INPUT")

# If we can't determine target, allow.
if [ -z "$TARGET_FILE" ]; then
  emit_allow
  exit 0
fi

# --- Allowlist: project work files (always allowed) ---
case "$TARGET_FILE" in
  */docs/*|docs/*|*.gitkeep)
    emit_allow
    exit 0
    ;;
esac

# --- Templates: framework-controlled files ---
case "$TARGET_FILE" in
  */templates/*|templates/*)
    TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
    if [ "$TASK_TYPE" = "framework" ]; then
      emit_allow
      exit 0
    fi
    REASON=$(printf '[integrity] Template edit blocked during project work (task_type=%s). Templates are framework-controlled files.' "$TASK_TYPE")
    emit_deny "$REASON"
    exit 0
    ;;
esac

# --- Framework control files: protected during project work ---
case "$TARGET_FILE" in
  */hooks/*|hooks/*|*/scripts/*|scripts/*|*/.claude/*|.claude/*|*CLAUDE.md)
    # Allow only when task_type is "framework".
    TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
    if [ "$TASK_TYPE" = "framework" ]; then
      emit_allow
      exit 0
    fi
    REASON=$(printf '[integrity] Framework control file edit blocked during project work (task_type=%s). Only framework tasks may edit hooks/scripts/.claude/CLAUDE.md.' "$TASK_TYPE")
    emit_deny "$REASON"
    exit 0
    ;;
esac

# Extract mode and plan gate from STATUS.md frontmatter.
MODE=$(grep -m1 "^mode:" "$STATUS_FILE" | sed "s/^mode:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
PLAN_GATE=$(grep -A20 "^gate_approvals:" "$STATUS_FILE" | grep -m1 "plan:" | sed "s/.*plan:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

# Block code edits in Client mode.
if [ "$MODE" = "Client" ]; then
  emit_deny "[gate] Client mode: code edits are blocked. Complete Client phases and get client_ready_for_dev approval first."
  exit 0
fi

# Block code edits when plan gate is not approved.
if [ "$PLAN_GATE" != "approved" ] && [ "$PLAN_GATE" != "n/a" ]; then
  REASON=$(printf '[gate] Plan gate is %s. Complete brainstorm and plan phases before editing code.' "$PLAN_GATE")
  emit_deny "$REASON"
  exit 0
fi

emit_allow
exit 0
