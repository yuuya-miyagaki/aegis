#!/usr/bin/env bash
# PreToolUse hook for Edit/Write: warns when editing production code without test changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

# Read stdin (JSON with tool_input).
INPUT=$(cat)

# Local escape hatch: AEGIS_TDD_MODE=off disables the TDD backstop for this session (full profile).
# Lowercase "off" only; any other value (unset/strict/invalid) keeps the strict default (fail-safe).
if [ "${AEGIS_TDD_MODE:-}" = "off" ]; then
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

# Skip non-production files: docs, templates, scripts, hooks, configs, framework control.
case "$TARGET_FILE" in
  */docs/*|*/templates/*|*/scripts/*|*/hooks/*|*/.claude/*|\
  *CLAUDE.md|*STATUS.md|*LEARNINGS.md|*README.md|\
  *.gitkeep|*.gitignore|*.json|*.yaml|*.yml|*.toml|*.ini|*.cfg|\
  *.md|*.txt|*.lock)
    emit_allow
    exit 0
    ;;
esac

# Skip test files themselves (they ARE the tests being written).
# Use boundary-aware patterns to avoid matching latest.ts, specification.ts, etc.
case "$TARGET_FILE" in
  */__tests__/*|__tests__/*|*/test/*|test/*|*/tests/*|tests/*|\
  *.test.*|*.spec.*|*_test.*|*_spec.*)
    emit_allow
    exit 0
    ;;
esac

# At this point, the target looks like production code.
# Check if there are test file changes in the current git diff (staged + unstaged).
HAS_TEST_CHANGES=false

if command -v git >/dev/null 2>&1; then
  # Check both staged and unstaged changes for test files.
  # Pattern matches actual code test files, not docs about testing.
  TEST_PATTERN='\.(test|spec)\.[a-zA-Z]+$|_(test|spec)\.[a-zA-Z]+$|(^|/)__tests__/|(^|/)tests?/'
  TEST_DIFF=$(git diff --name-only HEAD 2>/dev/null | grep -E "$TEST_PATTERN" || true)
  TEST_STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E "$TEST_PATTERN" || true)
  TEST_UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E "$TEST_PATTERN" || true)

  if [ -n "$TEST_DIFF" ] || [ -n "$TEST_STAGED" ] || [ -n "$TEST_UNTRACKED" ]; then
    HAS_TEST_CHANGES=true
  fi
fi

if [ "$HAS_TEST_CHANGES" = false ]; then
  emit_ask "[TDD] テストファイルの変更が検出されません。TDDルール: テストを先に書き、失敗を確認してから実装してください。"
else
  emit_allow
fi
exit 0
