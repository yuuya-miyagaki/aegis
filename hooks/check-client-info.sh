#!/usr/bin/env bash
# PreToolUse hook for Edit/Write: blocks requirements edits when docs/client/context.md is missing.
# Ensures client onboarding is complete before requirements are written.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

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
MODE=$(grep -m1 "^mode:" "$STATUS_FILE" | sed "s/^mode:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
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
