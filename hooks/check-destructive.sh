#!/usr/bin/env bash
# PreToolUse hook for Bash: warns on destructive commands.
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

# Load shared input extraction (fail-closed via safety lib on source failure).
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/patterns.sh"

# Read stdin.
INPUT=$(cat)

# Extract command.
CMD=$(extract_command "$INPUT")

# If no command extracted, allow — UNLESS the raw payload still matches a
# destructive pattern. Extraction can fail on truncated/oversized JSON; CC emits
# well-formed JSON, so this is a defense-in-depth fail-closed fallback (mirrors
# check-control-plane.sh's raw-target scan).
if [ -z "$CMD" ]; then
  RAW_LOWER=$(printf '%s' "$INPUT" | tr '[:upper:]' '[:lower:]')
  _raw_hit=""
  for i in "${!AEGIS_DESTRUCTIVE_LOWER_REGEX[@]}"; do
    if printf '%s' "$RAW_LOWER" | grep -qE "${AEGIS_DESTRUCTIVE_LOWER_REGEX[$i]}" 2>/dev/null; then _raw_hit=1; break; fi
  done
  if [ -z "$_raw_hit" ]; then
    for i in "${!AEGIS_DESTRUCTIVE_CMD_REGEX[@]}"; do
      if printf '%s' "$INPUT" | grep -qE "${AEGIS_DESTRUCTIVE_CMD_REGEX[$i]}" 2>/dev/null; then _raw_hit=1; break; fi
    done
  fi
  if [ -n "$_raw_hit" ] || printf '%s' "$INPUT" | grep -qE 'rm[[:space:]]+(-[a-zA-Z]*[rR]|--recursive)' 2>/dev/null; then
    emit_ask "[careful] コマンドの解析に失敗しましたが、入力が破壊的コマンドのパターンに一致します。意図を確認してください。"
  else
    emit_allow
  fi
  exit 0
fi

CMD_LOWER=$(printf '%s' "$CMD" | tr '[:upper:]' '[:lower:]')

# Safe exceptions for build artifacts.
# Strip the rm command and its flags, then check if all remaining args are safe.
SAFE_TARGETS=$(printf '%s' "$CMD" | sed -E 's/^[[:space:]]*rm[[:space:]]+(-[a-zA-Z]+[[:space:]]+)*//;s/--recursive[[:space:]]*//;s/--force[[:space:]]*//')
if [ -n "$SAFE_TARGETS" ]; then
  SAFE_ONLY=true
  # S-glob-1 (iter54): word-split WITHOUT pathname expansion. The unquoted
  # $SAFE_TARGETS previously glob-expanded against the hook CWD, so in a
  # build/dist-only directory `rm -rf *` turned `*` into "build dist" and the
  # safe-artifact exception swallowed the warning (fail-open). noglob is
  # save/restored so later patterns are untouched.
  case $- in *f*) _had_noglob=1 ;; *) _had_noglob=0 ;; esac
  set -f
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
  [ "$_had_noglob" = "1" ] || set +f
  if [ "$SAFE_ONLY" = true ]; then
    emit_allow
    exit 0
  fi
fi

# Destructive pattern checks.
WARN=""

# rm -r recursive: special-cased (the safe-targets exception above already
# returned for build-artifact-only deletes, so this is a real recursive delete).
# [rR] covers both -r (GNU) and -R (BSD/macOS) recursive flags (R4).
if printf '%s' "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*[rR]|--recursive)' 2>/dev/null; then
  WARN="破壊的: 再帰削除 (rm -r/-R)。ファイルを完全に削除します（復元できません）。"
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
