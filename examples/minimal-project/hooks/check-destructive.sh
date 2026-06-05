#!/usr/bin/env bash
# PreToolUse hook for Bash: warns on destructive commands.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"
source "${SCRIPT_DIR}/lib/patterns.sh"

# Read stdin.
INPUT=$(cat)

# Extract command.
CMD=$(extract_command "$INPUT")

# If no command extracted, allow.
if [ -z "$CMD" ]; then
  emit_allow
  exit 0
fi

CMD_LOWER=$(printf '%s' "$CMD" | tr '[:upper:]' '[:lower:]')

# Safe exceptions for build artifacts.
# Strip the rm command and its flags, then check if all remaining args are safe.
SAFE_TARGETS=$(printf '%s' "$CMD" | sed -E 's/^[[:space:]]*rm[[:space:]]+(-[a-zA-Z]+[[:space:]]+)*//;s/--recursive[[:space:]]*//;s/--force[[:space:]]*//')
if [ -n "$SAFE_TARGETS" ]; then
  SAFE_ONLY=true
  for target in $SAFE_TARGETS; do
    case "$target" in
      */node_modules|node_modules|*/dist|dist|*/__pycache__|__pycache__|*/build|build|*/coverage|coverage|*/.next|.next|*/.turbo|.turbo|*/.cache|.cache)
        ;;
      -*)
        ;;
      *)
        SAFE_ONLY=false
        break
        ;;
    esac
  done
  if [ "$SAFE_ONLY" = true ]; then
    emit_allow
    exit 0
  fi
fi

# Destructive pattern checks.
WARN=""

# rm -r recursive: special-cased (the safe-targets exception above already
# returned for build-artifact-only deletes, so this is a real recursive delete).
if printf '%s' "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r|--recursive)' 2>/dev/null; then
  WARN="Destructive: recursive delete (rm -r). Permanently removes files."
fi

# LOWER-cased command patterns (SQL) from patterns.sh.
if [ -z "$WARN" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_LOWER_REGEX[@]}"; do
    if printf '%s' "$CMD_LOWER" | grep -qE "${AEGIS_DESTRUCTIVE_LOWER_REGEX[$i]}" 2>/dev/null; then
      WARN="${AEGIS_DESTRUCTIVE_LOWER_WARN[$i]}"
      break
    fi
  done
fi

# RAW command patterns (git / bulk-delete) from patterns.sh.
if [ -z "$WARN" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_CMD_REGEX[@]}"; do
    if printf '%s' "$CMD" | grep -qE "${AEGIS_DESTRUCTIVE_CMD_REGEX[$i]}" 2>/dev/null; then
      WARN="${AEGIS_DESTRUCTIVE_CMD_WARN[$i]}"
      break
    fi
  done
fi

if [ -n "$WARN" ]; then
  emit_ask "[careful] $WARN"
else
  emit_allow
fi
exit 0
