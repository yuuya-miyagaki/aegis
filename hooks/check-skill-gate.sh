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
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"

# Read stdin (JSON with tool_input.skill).
INPUT=$(cat)

# Extract skill name from tool_input via python3 for JSON fidelity. Capture the
# interpreter exit code so a missing/broken python3 fails CLOSED, not open.
set +e
SKILL_NAME=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
    tool_input = data.get("tool_input", {})
    # Skill tool spec: tool_input has a "skill" field
    print(tool_input.get("skill", ""))
except Exception:
    print("")
' 2>/dev/null)
PY_RC=$?
set -e

# python3 unavailable/broken: we cannot determine the skill, so we cannot clear
# it. Fail CLOSED (ask) rather than allow a possible control-plane skill.
if [ "$PY_RC" -ne 0 ]; then
  emit_ask '[skill-gate] スキル名を判定できませんでした（python3 が利用不可）。aegis 制御層 (.claude/settings.json / keybindings) を変更しないか手動で確認してから承認してください。'
  exit 0
fi

# python3 succeeded with an empty skill name = field genuinely absent → allow.
if [ -z "$SKILL_NAME" ]; then
  emit_allow
  exit 0
fi

# Control-plane skills: anything that can rewrite .claude/settings.json,
# permissions, or keybindings. These bypass Edit/Write hooks because the
# Skill tool runs the mutation internally.
case "$SKILL_NAME" in
  update-config|keybindings-help|fewer-permission-prompts)
    # Skill name is wrapped in backticks; parentheses are used for parenthetical text.
    REASON=$(printf '[skill-gate] Skill `%s` は aegis 制御層 (.claude/settings.json または keybindings) を変更する可能性があります。スキル本文と引数を確認してから承認してください。' "$SKILL_NAME")
    emit_ask "$REASON"
    exit 0
    ;;
esac

# Non-control-plane skill: allow.
emit_allow
exit 0
