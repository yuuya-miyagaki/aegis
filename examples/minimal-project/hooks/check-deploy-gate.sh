#!/usr/bin/env bash
# PreToolUse hook for Bash: blocks deploy commands when required gates are not approved.
# Thin wrapper — delegates all gate logic to check_status.py --check-deploy-ready.
# Covers major CLI deploy commands (vercel, firebase, netlify, npm/pnpm deploy).
# MCP-based deploys are covered by check-deploy-mcp-gate.sh (separate matcher).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
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
# Avoids false positives on read-only commands like: rg deploy, cat DEPLOY-CHECKLIST.template.md
# Patterns: vercel deploy [flags], bare vercel (default=deploy), firebase deploy,
#           netlify deploy, npm/pnpm/yarn/bun [run] deploy, flyctl/railway/gcloud deploy.
DEPLOY_RE='(^|[;&|] *)(vercel +deploy|vercel *$|firebase +deploy|netlify +deploy|(npm|pnpm|yarn|bun) +(run +)?deploy|flyctl +deploy|railway +deploy|gcloud +app +deploy)'
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
