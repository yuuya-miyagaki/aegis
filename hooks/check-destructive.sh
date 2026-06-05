#!/usr/bin/env bash
# PreToolUse hook for Bash: warns on destructive commands.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

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

if printf '%s' "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r|--recursive)' 2>/dev/null; then
  WARN="Destructive: recursive delete (rm -r). Permanently removes files."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD_LOWER" | grep -qE 'drop\s+(table|database)' 2>/dev/null; then
  WARN="Destructive: SQL DROP detected."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD_LOWER" | grep -qE '\btruncate\b' 2>/dev/null; then
  WARN="Destructive: SQL TRUNCATE detected."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+push\s+.*(-f\b|--force)' 2>/dev/null; then
  WARN="Destructive: git force-push rewrites remote history."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+reset\s+--hard' 2>/dev/null; then
  WARN="Destructive: git reset --hard discards uncommitted changes."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+(checkout|restore)\s+\.' 2>/dev/null; then
  WARN="Destructive: discards all uncommitted working tree changes."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+branch\s+(-[a-zA-Z]*[dD]\b|--delete)' 2>/dev/null; then
  WARN="Destructive: branch deletion."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+(checkout|restore)\s+--\s+' 2>/dev/null; then
  WARN="Destructive: discards changes to specific files."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+clean\s+.*-f' 2>/dev/null; then
  WARN="Destructive: git clean removes untracked files."
fi

# v0.13.0 Phase 0b: high-risk patterns added.
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+filter-branch' 2>/dev/null; then
  WARN="Destructive: git filter-branch rewrites repository history (irreversible)."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+update-ref\s+-d' 2>/dev/null; then
  WARN="Destructive: git update-ref -d deletes a ref permanently."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+reflog\s+expire.*--expire=now' 2>/dev/null; then
  WARN="Destructive: git reflog expire --expire=now wipes reflog (no recovery)."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'npx\s+rimraf' 2>/dev/null; then
  WARN="Destructive: npx rimraf bulk-deletes files recursively."
fi

if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'find\s+.+\s+-delete' 2>/dev/null; then
  WARN="Destructive: find -delete bulk-deletes matching files."
fi

if [ -n "$WARN" ]; then
  emit_ask "[careful] $WARN"
else
  emit_allow
fi
exit 0
