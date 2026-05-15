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

# Read stdin (JSON with tool_input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow.
if [ ! -f "$STATUS_FILE" ]; then
  echo '{}'
  exit 0
fi

# Extract file_path from tool_input.
TARGET_FILE=$(extract_file_path "$INPUT")

# If we can't determine target, allow.
if [ -z "$TARGET_FILE" ]; then
  echo '{}'
  exit 0
fi

# --- Allowlist: project work files (always allowed) ---
case "$TARGET_FILE" in
  */docs/*|docs/*|*.gitkeep)
    echo '{}'
    exit 0
    ;;
esac

# --- Templates: framework-controlled files ---
case "$TARGET_FILE" in
  */templates/*|templates/*)
    TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
    if [ "$TASK_TYPE" = "framework" ]; then
      echo '{}'
      exit 0
    fi
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] Template edit blocked during project work (task_type=%s). Templates are framework-controlled files."}}\n' "$TASK_TYPE"
    exit 0
    ;;
esac

# --- Framework control files: protected during project work ---
case "$TARGET_FILE" in
  */hooks/*|hooks/*|*/scripts/*|scripts/*|*/.claude/*|.claude/*|*CLAUDE.md)
    # Allow only when task_type is "framework".
    TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
    if [ "$TASK_TYPE" = "framework" ]; then
      echo '{}'
      exit 0
    fi
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] Framework control file edit blocked during project work (task_type=%s). Only framework tasks may edit hooks/scripts/.claude/CLAUDE.md."}}\n' "$TASK_TYPE"
    exit 0
    ;;
esac

# Extract mode and plan gate from STATUS.md frontmatter.
MODE=$(grep -m1 "^mode:" "$STATUS_FILE" | sed "s/^mode:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
PLAN_GATE=$(grep -A20 "^gate_approvals:" "$STATUS_FILE" | grep -m1 "plan:" | sed "s/.*plan:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

# Block code edits in Client mode.
if [ "$MODE" = "Client" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[gate] Client mode: code edits are blocked. Complete Client phases and get client_ready_for_dev approval first."}}\n'
  exit 0
fi

# Block code edits when plan gate is not approved.
if [ "$PLAN_GATE" != "approved" ] && [ "$PLAN_GATE" != "n/a" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[gate] Plan gate is %s. Complete brainstorm and plan phases before editing code."}}\n' "$PLAN_GATE"
  exit 0
fi

echo '{}'
exit 0
