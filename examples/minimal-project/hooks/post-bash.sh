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
source "${SCRIPT_DIR}/lib/emit.sh"

INPUT=$(cat)

# E1: record the failed execution into the evidence log (success path is
# recorded by post-bash-observe.sh). Observation is fail-open.
source "${SCRIPT_DIR}/lib/evidence.sh"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"
append_evidence "$ROOT" fail "$INPUT" || true

# Extract command from hook input.
CMD=$(extract_command "$INPUT")

# Only act on test runner commands (single source: patterns.sh).
source "${SCRIPT_DIR}/lib/patterns.sh"
IS_TEST=false
for _re in "${AEGIS_TEST_RUNNER_REGEX[@]}"; do
  if printf '%s' "$CMD" | grep -Eq "$_re"; then
    IS_TEST=true
    break
  fi
done

if [ "$IS_TEST" = true ]; then
  emit_context PostToolUseFailure "[ReAct] テスト失敗。Observe: エラー出力を読む → Think: 原因仮説1つ → Act: 最小変更1つ。複数変更を同時にしない。"
else
  emit_allow
fi
exit 0
