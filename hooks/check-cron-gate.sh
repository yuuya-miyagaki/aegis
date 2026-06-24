#!/usr/bin/env bash
# PreToolUse hook for CronCreate: asks when the cron's payload prompt contains
# deploy or destructive command patterns.
#
# CronCreate schedules a Claude agent to run on a cron expression. If the
# scheduled prompt contains "vercel deploy", "rm -rf", "git push --force", etc.,
# it will execute without the same gate enforcement as an interactive session.
# We ask the user to confirm such payloads before the cron is registered.
#
# Output: hookSpecificOutput.permissionDecision: "ask" + permissionDecisionReason
# (PreToolUse spec, v0.12.2+).
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
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/patterns.sh"

# Read stdin (JSON with tool_input containing the cron prompt).
INPUT=$(cat)

# Extract prompt from tool_input via python3. Capture the interpreter exit code
# so a missing/broken python3 fails CLOSED, not open.
# CronCreate's tool_input shape isn't strictly documented; we probe common keys.
set +e
PROMPT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
    tool_input = data.get("tool_input", {})
    # Probe common keys; concatenate if multiple present (defensive).
    parts = []
    for key in ("prompt", "task", "instructions", "command"):
        v = tool_input.get(key)
        if isinstance(v, str):
            parts.append(v)
    print("\n".join(parts))
except Exception:
    print("")
' 2>/dev/null)
PY_RC=$?
set -e

# python3 unavailable/broken: cannot inspect the scheduled payload for
# deploy/destructive content. Fail CLOSED (ask).
if [ "$PY_RC" -ne 0 ]; then
  emit_ask '[cron-gate] スケジュール payload を解析できませんでした（python3 が利用不可）。デプロイ/破壊的コマンドを含まないか手動で確認してから承認してください。'
  exit 0
fi

# python3 succeeded with no extractable prompt → allow (defensive: shape differs).
if [ -z "$PROMPT" ]; then
  emit_allow
  exit 0
fi

# Deploy + destructive detection against the scheduled prompt text.
# G3 (iter42): single-sourced from hooks/lib/patterns.sh instead of an inline
# DANGER_RE, so new destructive patterns (e.g. dd/chmod -R from G1) and the full
# deploy regex propagate here automatically — no drift between the gates.
PROMPT_LOWER=$(printf '%s' "$PROMPT" | tr '[:upper:]' '[:lower:]')
_danger=""
# Deploy commands (shared regex).
printf '%s' "$PROMPT" | grep -qEi "$AEGIS_DEPLOY_REGEX" 2>/dev/null && _danger=1
# Destructive: SQL (matched against lower-cased prompt).
if [ -z "$_danger" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_LOWER_REGEX[@]}"; do
    if printf '%s' "$PROMPT_LOWER" | grep -qE "${AEGIS_DESTRUCTIVE_LOWER_REGEX[$i]}" 2>/dev/null; then _danger=1; break; fi
  done
fi
# Destructive: raw command patterns (git / dd / chmod -R / mkfs / shred / ...).
if [ -z "$_danger" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_CMD_REGEX[@]}"; do
    if printf '%s' "$PROMPT" | grep -qE "${AEGIS_DESTRUCTIVE_CMD_REGEX[$i]}" 2>/dev/null; then _danger=1; break; fi
  done
fi
# Recursive delete (rm -r/-R), special-cased like check-destructive.sh.
if [ -z "$_danger" ]; then
  printf '%s' "$PROMPT" | grep -qE 'rm\s+(-[a-zA-Z]*[rR]|--recursive)' 2>/dev/null && _danger=1
fi

if [ -n "$_danger" ]; then
  # Truncate the prompt preview to 200 chars and sanitize to a single printable
  # line: collapse ALL control chars (0x00-0x1F + DEL) to space so emit.sh never
  # receives a raw control byte that would make the ask JSON malformed (Round 3 P1).
  PREVIEW=$(printf '%s' "$PROMPT" | head -c 200 | tr '\000-\037\177' ' ')
  REASON=$(printf '[cron-gate] スケジュール対象 prompt にデプロイ/破壊的コマンドが含まれています。承認の前に内容を確認してください。preview: %s' "$PREVIEW")
  emit_ask "$REASON"
  exit 0
fi

# No dangerous pattern: allow.
emit_allow
exit 0
