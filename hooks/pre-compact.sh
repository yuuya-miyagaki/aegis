#!/usr/bin/env bash
# PreCompact hook: blocks compaction when STATUS.md appears stale,
# allows when state is current.
#
# Block condition: STATUS.md was not modified within the last 5 minutes
# AND next_action or phase is non-empty (active work session).
# This catches cases where compaction would discard context before
# the agent has persisted its working state to STATUS.md.
#
# Block / Allow contract (v0.12.2):
#   Both paths use exit 0. Block is signaled by stdout JSON
#   `{"decision":"block","reason":"..."}` (top-level).
#   Allow is signaled by stdout JSON
#   `{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"..."}}`.
#   IMPORTANT: do NOT use exit 2 here. Claude Code Hooks spec accepts either
#   exit 2 OR JSON `decision:block` for blocking PreCompact, but they are mutually
#   exclusive: exit 2 makes the runtime ignore stdout JSON and treat output as
#   stderr feedback only. aegis v0.12.2 採用方針は JSON block + exit 0。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

source "${SCRIPT_DIR}/lib/emit.sh"
source "${SCRIPT_DIR}/lib/frontmatter.sh"

# If STATUS.md doesn't exist, allow silently.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

MODE=$(frontmatter_value "$STATUS_FILE" "mode")
PHASE=$(frontmatter_value "$STATUS_FILE" "phase")
NEXT_ACTION=$(frontmatter_value "$STATUS_FILE" "next_action")

# Staleness check: block compaction if STATUS.md was not recently updated.
# Default: 5 minutes (300 seconds). Override with AEGIS_PRECOMPACT_INTERVAL
# (legacy ULTRA_PRECOMPACT_INTERVAL is honored as fallback for one release).
STALE_THRESHOLD="${AEGIS_PRECOMPACT_INTERVAL:-${ULTRA_PRECOMPACT_INTERVAL:-300}}"
# Validate: fall back to default if non-numeric, zero, or negative.
case "$STALE_THRESHOLD" in
  ''|*[!0-9]*|0) STALE_THRESHOLD=300 ;;
esac
NOW=$(date +%s)
FILE_MTIME=$(stat -f %m "$STATUS_FILE" 2>/dev/null || stat -c %Y "$STATUS_FILE" 2>/dev/null || echo "$NOW")
ELAPSED=$(( NOW - FILE_MTIME ))

if [ "$ELAPSED" -gt "$STALE_THRESHOLD" ] && [ -n "$PHASE" ] && [ "$PHASE" != "null" ]; then
  # STATUS.md is stale and there is an active phase — block compaction.
  # Per Claude Code Hooks spec, PreCompact uses top-level decision/reason.
  # IMPORTANT: must exit 0 — exit 2 causes Claude Code to ignore stdout JSON
  # and treat output as stderr feedback only. v0.12.2 採用方針は JSON block。
  MSG="[PreCompact BLOCKED] STATUS.md was last updated ${ELAPSED}s ago (threshold: ${STALE_THRESHOLD}s). mode=${MODE} phase=${PHASE} | Update STATUS.md before compaction to preserve working state."
  emit_block "$MSG"
  exit 0
fi

# STATUS.md is current or no active phase — allow compaction with context.
# Per Claude Code Hooks spec, PreCompact context uses hookSpecificOutput.additionalContext + hookEventName.
MSG="[PreCompact] mode=${MODE} phase=${PHASE} | next: ${NEXT_ACTION} | STATUS.md is current. Compaction allowed."

emit_context PreCompact "$MSG"
exit 0
