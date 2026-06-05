#!/usr/bin/env bash
# PreToolUse hook for Bash: denies commands that reference control plane paths
# during non-framework tasks.
#
# Strategy: ALLOWLIST, not blacklist.
# If the raw hook input mentions any control plane path, the command is denied
# UNLESS it matches the allowlist or task_type is "framework".
#
# Allowlist rules:
# - The command must be SOLELY an allowlisted script invocation (no chaining).
# - Commands containing ;, &&, ||, |, $(), `` are never allowlisted
#   (prevents "validator && malicious" bypass).
# - Known read-only simple commands (cat, grep, ls) are allowed only when
#   they contain no chaining operators and no write indicators.
#
# Control plane paths: STATUS.md, CLAUDE.md, .claude/, hooks/, scripts/
# Allowlist: update-gate.sh, check_status.py, check_framework_contract.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

# Read stdin (raw hook input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow (no framework context).
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Control plane path patterns.
CONTROL_PLANE='STATUS\.md|CLAUDE\.md|\.claude/|\.claude[^A-Za-z0-9_/]|hooks/|scripts/|templates/'

# Check the RAW input for control plane paths. This avoids extract_command
# truncation on commands with internal quotes (e.g. python3 -c "...STATUS.md...").
if ! printf '%s' "$INPUT" | grep -qE "$CONTROL_PLANE"; then
  # No control plane path in entire input — allow.
  emit_allow
  exit 0
fi

# Input references a control plane path. Extract the command for further checks.
CMD=$(extract_command "$INPUT")

# Chain/redirect operators that indicate compound or write commands. If present,
# the command is never eligible for allowlist or read-only pass-through.
# Includes > and >> to block "allowlisted_script > file" write bypass.
CHAIN_OPS='[;&|>]|\$\(|`'

# --- Allowlist check ---
# Only if the command has NO chaining operators, check if it is solely an
# allowlisted script invocation.
is_allowlisted() {
  local cmd="$1"
  # Reject if command contains chain operators.
  if printf '%s' "$cmd" | grep -qE "$CHAIN_OPS"; then
    return 1
  fi
  # Match: the command is exactly an allowlisted script call (with args).
  case "$cmd" in
    *scripts/check_framework_contract.py*|*scripts/check_status.py*|*scripts/update-gate.sh*)
      return 0
      ;;
  esac
  return 1
}

# Check extracted command.
if [ -n "$CMD" ] && is_allowlisted "$CMD"; then
  emit_allow
  exit 0
fi

# Fallback: check raw input for allowlist (extract_command may have truncated).
# Extract command via python3 for full fidelity.
FULL_CMD=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
if [ -n "$FULL_CMD" ] && is_allowlisted "$FULL_CMD"; then
  emit_allow
  exit 0
fi

# Check task_type: allow all if framework task.
TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
if [ "$TASK_TYPE" = "framework" ]; then
  emit_allow
  exit 0
fi

# --- Read-only simple command check ---
# Allow purely read-only commands with no chaining and no write indicators.
# Use FULL_CMD for accuracy (falls back to CMD if python3 extraction failed).
CHECK_CMD="${FULL_CMD:-$CMD}"
if [ -n "$CHECK_CMD" ]; then
  # Must not contain chain operators.
  if ! printf '%s' "$CHECK_CMD" | grep -qE "$CHAIN_OPS"; then
    READ_ONLY_STARTS='^(cat|head|tail|less|more|grep|egrep|fgrep|rg|find|ls|wc|diff|file|stat|md5sum|sha256sum) '
    WRITE_INDICATORS='sed\s+-i|>\s*[^&]|>>\s|tee\s|cp\s|mv\s|chmod\s|rm\s|mkdir\s|touch\s|install\s|ln\s|write_text|write_bytes|open\(.*[wax]|\.write\(|truncate|Path\(.*\.write|unlink|remove|rename'
    if printf '%s' "$CHECK_CMD" | grep -qE "$READ_ONLY_STARTS" && \
       ! printf '%s' "$CHECK_CMD" | grep -qE "$WRITE_INDICATORS"; then
      emit_allow
      exit 0
    fi
  fi
fi

# Default: deny. Control plane path present, not allowlisted, not read-only.
REASON=$(printf '[integrity] Bash command referencing control plane path blocked during project work (task_type=%s). Use Edit/Write tools for auditable changes, or set task_type=framework.' "$TASK_TYPE")
emit_deny "$REASON"
exit 0
