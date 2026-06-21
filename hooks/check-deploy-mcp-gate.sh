#!/usr/bin/env bash
# PreToolUse hook for MCP tools: blocks MCP deploy tools when required gates
# are not approved.
# Thin wrapper — delegates all gate logic to check_status.py --check-deploy-ready.
# Companion to check-deploy-gate.sh (covers CLI deploys via Bash matcher).
# Matcher (registered in settings.json / hooks.template.json): the literal
# mcp__claude_ai_Vercel__deploy_to_vercel. v0.13.0 Phase 0b で broad regex
# mcp__.*__deploy.* から narrowing 済み。Firebase 等の他 MCP deploy は未対応
# （将来、対応 MCP を増やす際に明示 matcher として追加）。
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

aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"

# Read stdin (JSON with tool_name and tool_input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# The matcher regex already filtered to deploy MCP tools.
# No further tool_input inspection needed — the tool_name match is sufficient.

# Delegate gate check to check_status.py (sole source of truth).
# RC contract (P2-3): 0=allow / 2+leading "ASK:"=ask (size-skip deploy needs
# human confirm) / anything else=deny. RC=2 WITHOUT the ASK: marker falls
# through to deny so interpreter failures are never mistaken for ask.
# set +e: python returning non-zero is expected (deny/ask) — must not abort before emitting JSON.
set +e
RESULT=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-deploy-ready 2>&1)
RC=$?
set -e
if [ $RC -eq 2 ] && printf '%s' "$RESULT" | grep -q '^ASK:'; then
  MSG=$(printf '%s' "$RESULT" | sed 's/^ASK:[[:space:]]*//' | tr '\n' ' ')
  emit_ask "[deploy-gate-mcp] $MSG"
  exit 0
fi
if [ $RC -ne 0 ]; then
  MSG=$(printf '%s' "$RESULT" | tr '\n' ' ')
  REASON=$(printf '[deploy-gate-mcp] %s' "$MSG")
  emit_deny "$REASON"
  exit 0
fi

emit_allow
exit 0
