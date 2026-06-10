#!/usr/bin/env bash
# PreToolUse hook for Bash: blocks deploy commands when required gates are not approved.
# Thin wrapper — delegates all gate logic to check_status.py --check-deploy-ready.
# Covers major CLI deploy commands (vercel, firebase, netlify, npm/pnpm deploy).
# MCP-based deploys are covered by check-deploy-mcp-gate.sh (separate matcher).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Allow ROOT override via env (test fixtures use this to isolate from real aegis
# state; same convention as check-task-created.sh). Unset in production.
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

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
DEPLOY_RE='(^|[[:space:];&|])(vercel +deploy|vercel( +--[A-Za-z][A-Za-z0-9-]*(=[^[:space:];&|]*)?)*[[:space:]]*($|[;&|>])|firebase +deploy|netlify +deploy|(npm|pnpm|yarn|bun) +(run +)?deploy|flyctl +deploy|railway +deploy|gcloud +app +deploy|wrangler +(deploy|publish))'
if ! printf '%s' "$CMD" | grep -qEi "$DEPLOY_RE"; then
  emit_allow
  exit 0
fi

# Delegate gate check to check_status.py (sole source of truth).
# set +e: python returning non-zero is expected (deny) — must not abort before emitting JSON.
set +e
RESULT=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-deploy-ready 2>&1)
RC=$?
set -e
if [ $RC -ne 0 ]; then
  MSG=$(printf '%s' "$RESULT" | tr '\n' ' ')
  REASON=$(printf '[deploy-gate] %s' "$MSG")
  emit_deny "$REASON"
  exit 0
fi

emit_allow
exit 0
