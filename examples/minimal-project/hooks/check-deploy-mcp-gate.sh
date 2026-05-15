#!/usr/bin/env bash
# PreToolUse hook for MCP tools: blocks MCP deploy tools when required gates
# are not approved.
# Thin wrapper — delegates all gate logic to check_status.py --check-deploy-ready.
# Companion to check-deploy-gate.sh (covers CLI deploys via Bash matcher).
# Matcher: mcp__.*__deploy.* (Vercel deploy, Firebase deploy, etc.)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Read stdin (JSON with tool_name and tool_input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow.
if [ ! -f "$STATUS_FILE" ]; then
  echo '{}'
  exit 0
fi

# The matcher regex already filtered to deploy MCP tools.
# No further tool_input inspection needed — the tool_name match is sufficient.

# Delegate gate check to check_status.py (sole source of truth).
# set +e: python returning non-zero is expected (deny) — must not abort before emitting JSON.
set +e
RESULT=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-deploy-ready 2>&1)
RC=$?
set -e
if [ $RC -ne 0 ]; then
  MSG=$(printf '%s' "$RESULT" | tr '\n' ' ')
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[deploy-gate-mcp] %s"}}\n' "$MSG"
  exit 0
fi

echo '{}'
exit 0
