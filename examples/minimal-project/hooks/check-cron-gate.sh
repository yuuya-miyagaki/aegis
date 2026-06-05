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
source "${SCRIPT_DIR}/lib/emit.sh"

# Read stdin (JSON with tool_input containing the cron prompt).
INPUT=$(cat)

# Extract prompt from tool_input via python3.
# CronCreate's tool_input shape isn't strictly documented; we probe common keys.
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
' 2>/dev/null || true)

# If no prompt extractable, allow (defensive: payload shape may differ).
if [ -z "$PROMPT" ]; then
  emit_allow
  exit 0
fi

# Deploy + destructive patterns. Aligned with check-deploy-gate.sh and
# check-destructive.sh, but evaluated against the scheduled prompt text.
DANGER_RE='vercel +deploy|vercel *$|firebase +deploy|netlify +deploy|gcloud +app +deploy|(npm|pnpm|yarn|bun) +(run +)?deploy|flyctl +deploy|railway +deploy|rm\s+-[a-zA-Z]*r|drop\s+(table|database)|git\s+push\s+.*(-f\b|--force)|git\s+reset\s+--hard|git\s+filter-branch|git\s+update-ref\s+-d|git\s+reflog\s+expire.*--expire=now|npx\s+rimraf|find\s+.*-delete'

if printf '%s' "$PROMPT" | grep -qEi "$DANGER_RE"; then
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
