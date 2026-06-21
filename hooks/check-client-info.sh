#!/usr/bin/env bash
# PreToolUse hook for Edit/Write: blocks requirements edits when docs/client/context.md is missing.
# Ensures client onboarding is complete before requirements are written.
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
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction.
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"

# Read stdin (JSON with tool_input).
INPUT=$(cat)

# Extract file_path from tool_input.
TARGET_FILE=$(extract_file_path "$INPUT")

# Only activate when the file_path contains docs/requirements/.
case "$TARGET_FILE" in
  *docs/requirements/*)
    ;;
  *)
    emit_allow
    exit 0
    ;;
esac

# If STATUS.md doesn't exist, allow.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Check MODE: skip if Dev.
MODE=$(frontmatter_value "$STATUS_FILE" "mode")
if [ "$MODE" = "Dev" ]; then
  emit_allow
  exit 0
fi

# Check if docs/client/context.md exists.
CLIENT_CONTEXT="${ROOT}/docs/client/context.md"
if [ -f "$CLIENT_CONTEXT" ]; then
  emit_allow
  exit 0
fi

# docs/client/context.md is missing: deny the edit.
emit_deny "docs/client/context.md が見つかりません。requirements 編集の前にクライアント情報を記録してください。→ client-workflow skill の onboard フェーズを実行"
exit 0
