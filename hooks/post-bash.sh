#!/usr/bin/env bash
# PostToolUseFailure hook for Bash: detects test runner failures and suggests ReAct approach.
#
# Migrated from PostToolUse (v0.12.2): this hook now fires only when a Bash
# command exits non-zero, so we no longer check the exit code ourselves.
# Output uses hookSpecificOutput.additionalContext per Claude Code Hooks spec
# (PostToolUseFailure is informational; it does not block).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"

INPUT=$(cat)

# Extract command from hook input.
CMD=$(extract_command "$INPUT")

# Only act on test runner commands.
IS_TEST=false
case "$CMD" in
  *vitest*|*jest*|*pytest*|*cargo\ test*|*go\ test*|*npm\ test*|*pnpm\ test*|*bun\ test*)
    IS_TEST=true
    ;;
esac

if [ "$IS_TEST" = true ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"[ReAct] テスト失敗。Observe: エラー出力を読む → Think: 原因仮説1つ → Act: 最小変更1つ。複数変更を同時にしない。"}}\n'
else
  echo '{}'
fi
exit 0
