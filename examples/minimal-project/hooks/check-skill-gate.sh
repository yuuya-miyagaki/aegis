#!/usr/bin/env bash
# PreToolUse hook for Skill: asks for confirmation when invoking control-plane skills
# that can modify the Claude Code harness configuration (settings, keybindings, permissions).
#
# The aegis framework relies on .claude/settings.json and permission configurations
# being authoritative. Skills that mutate these files bypass aegis gate logic, so we
# surface them for explicit user approval rather than blanket-denying (some are
# legitimate ops, e.g. user explicitly running /update-config).
#
# Output: hookSpecificOutput.permissionDecision: "ask" + permissionDecisionReason
# (PreToolUse spec, v0.12.2+).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Read stdin (JSON with tool_input.skill).
INPUT=$(cat)

# Extract skill name from tool_input via python3 for JSON fidelity.
SKILL_NAME=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
    tool_input = data.get("tool_input", {})
    # Skill tool spec: tool_input has a "skill" field
    print(tool_input.get("skill", ""))
except Exception:
    print("")
' 2>/dev/null || true)

# If we cannot determine the skill name, allow (defensive default).
if [ -z "$SKILL_NAME" ]; then
  echo '{}'
  exit 0
fi

# Control-plane skills: anything that can rewrite .claude/settings.json,
# permissions, or keybindings. These bypass Edit/Write hooks because the
# Skill tool runs the mutation internally.
case "$SKILL_NAME" in
  update-config|keybindings-help|fewer-permission-prompts)
    # Avoid double-quotes inside the JSON string to keep stdout valid JSON.
    # Skill name is wrapped in backticks; parentheses are used for parenthetical text.
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"[skill-gate] Skill `%s` は aegis 制御層 (.claude/settings.json または keybindings) を変更する可能性があります。スキル本文と引数を確認してから承認してください。"}}\n' "$SKILL_NAME"
    exit 0
    ;;
esac

# Non-control-plane skill: allow.
echo '{}'
exit 0
