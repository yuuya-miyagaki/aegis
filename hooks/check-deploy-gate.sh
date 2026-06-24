#!/usr/bin/env bash
# PreToolUse hook for Bash: blocks deploy commands when required gates are not approved.
# Thin wrapper — delegates all gate logic to check_status.py --check-deploy-ready.
# Covers major CLI deploy commands (vercel, firebase, netlify, npm/pnpm deploy).
# MCP-based deploys are covered by check-deploy-mcp-gate.sh (separate matcher).
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
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Allow ROOT override via env (test fixtures use this to isolate from real aegis
# state; same convention as check-task-created.sh). Unset in production.
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction.
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/patterns.sh"

# Read stdin (JSON with tool_input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Extract command from tool_input.
CMD=$(extract_command "$INPUT")
if [ -z "$CMD" ]; then
  emit_allow
  exit 0
fi

# Deploy execution command trigger — match actual deploy commands only.
# The tool name is anchored at a word boundary (start, or preceded by whitespace
# / ; / & / |) so a benign prefix (npx, sudo, time, FOO=bar env-assignment) does
# NOT slip the gate — `npx vercel deploy` is a normal phrasing. This still avoids
# read-only false matches (rg deploy, cat DEPLOY-CHECKLIST.template.md) because
# they contain no tool-name+deploy bigram. A leading non-boundary char (e.g. the
# '-' in my-vercel) does not match.
# Patterns: vercel deploy [flags], vercel with ONLY flags (default=deploy, incl.
#           --prod; subcommands like `vercel env` do NOT match), firebase/netlify
#           deploy, npm/pnpm/yarn/bun [run] deploy, flyctl/railway/gcloud deploy,
#           wrangler deploy|publish.
# G3 (iter42): pattern moved to hooks/lib/patterns.sh (AEGIS_DEPLOY_REGEX) so
# check-cron-gate.sh shares the exact same deploy detection (no drift).
if ! printf '%s' "$CMD" | grep -qEi "$AEGIS_DEPLOY_REGEX"; then
  emit_allow
  exit 0
fi

# Delegate gate check to check_status.py (sole source of truth).
# RC contract (P2-3): 0=allow / 2+leading "ASK:"=ask (size-skip deploy needs
# human confirm) / anything else=deny. RC=2 WITHOUT the ASK: marker falls
# through to deny so interpreter failures are never mistaken for ask.
# set +e: python returning non-zero is expected (deny/ask) — must not abort before emitting JSON.
# stdout/stderr are separated (T2 v1.5.1): decision text comes from stdout
# only; stderr is merged into the deny reason ONLY when stdout is empty
# (interpreter-failure diagnostics). mktemp failure must not kill the hook
# under set -e — fall back to /dev/null (diagnostics lost, gate path intact).
ERR_FILE=$(mktemp 2>/dev/null) || ERR_FILE=/dev/null
set +e
RESULT=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-deploy-ready 2>"$ERR_FILE")
RC=$?
set -e
ERR_CONTENT=""
if [ "$ERR_FILE" != "/dev/null" ]; then
  ERR_CONTENT=$(cat "$ERR_FILE" 2>/dev/null || true)
  rm -f "$ERR_FILE" 2>/dev/null || true
fi
if [ $RC -eq 2 ] && printf '%s' "$RESULT" | grep -q '^ASK:'; then
  MSG=$(printf '%s' "$RESULT" | sed 's/^ASK:[[:space:]]*//' | tr '\n' ' ')
  emit_ask "[deploy-gate] $MSG"
  exit 0
fi
if [ $RC -ne 0 ]; then
  if [ -z "$RESULT" ] && [ -n "$ERR_CONTENT" ]; then
    RESULT="$ERR_CONTENT"
  fi
  MSG=$(printf '%s' "$RESULT" | tr '\n' ' ')
  REASON=$(printf '[deploy-gate] %s' "$MSG")
  emit_deny "$REASON"
  exit 0
fi

emit_allow
exit 0
