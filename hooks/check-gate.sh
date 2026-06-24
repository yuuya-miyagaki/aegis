#!/usr/bin/env bash
# PreToolUse hook for Edit/Write: blocks code edits when plan gate is not approved.
# Also protects framework control files (hooks, scripts, .claude, CLAUDE.md)
# from edits during non-framework project work.
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
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction (fail-closed via safety lib on source failure).
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"

# Read stdin (JSON with tool_input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Extract file_path from tool_input.
TARGET_FILE=$(extract_file_path "$INPUT")

# If we can't determine target, allow.
if [ -z "$TARGET_FILE" ]; then
  emit_allow
  exit 0
fi

# Physical form of the project root (macOS: /tmp vs /private/tmp; symlinked
# workdirs). Absolute targets may arrive in either form.
ROOT_REAL="$(cd "$ROOT" && pwd -P)"

# Lexically resolve ./ and ../ segments so non-canonical forms (././hooks/,
# foo/../hooks/, $ROOT/./hooks/) cannot dodge the root-anchored patterns.
# No filesystem access; unresolvable leading ..s are preserved.
normalize_target() {
  local p="$1" out="" seg abs=""
  case "$p" in /*) abs="/" ;; esac
  local IFS='/'
  for seg in $p; do
    case "$seg" in
      ""|".") ;;
      "..")
        case "$out" in
          ""|..|*/..) [ -z "$abs" ] && out="${out:+$out/}.." ;;
          */*) out="${out%/*}" ;;
          *) out="" ;;
        esac
        ;;
      *) out="${out:+$out/}$seg" ;;
    esac
  done
  printf '%s%s' "$abs" "$out"
}

TARGET_FILE="$(normalize_target "$TARGET_FILE")"

# --- Allowlist: project work files (always allowed) ---
case "$TARGET_FILE" in
  */docs/*|docs/*|*.gitkeep)
    emit_allow
    exit 0
    ;;
esac

# Framework-controlled paths are anchored to the project root ($ROOT or its
# physical form for absolute paths, bare prefix for relative ones): the
# framework delivers hooks/ scripts/ templates/ .claude/ CLAUDE.md at the
# root, while paths like src/hooks/ or a nested CLAUDE.md belong to the
# project (P1-2, evolution review 2026-06-10). Relative paths that still
# escape the root (../) may resolve into the root when the session cwd is a
# subdirectory — classification is unknowable here, so they stay protected
# (conservative deny).
is_protected_dir() {
  local path="$1" name="$2"
  case "$path" in
    "$ROOT"/$name/*|"$ROOT_REAL"/$name/*|$name/*|../$name/*|../*/$name/*)
      return 0 ;;
  esac
  return 1
}

# --- Templates: framework-controlled files ---
if is_protected_dir "$TARGET_FILE" templates; then
  TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
  if [ "$TASK_TYPE" = "framework" ]; then
    emit_allow
    exit 0
  fi
  REASON=$(printf '[integrity] Template edit blocked during project work (task_type=%s). Templates are framework-controlled files.' "$TASK_TYPE")
  emit_deny "$REASON"
  exit 0
fi

# --- Framework control files: protected during project work ---
is_control_file() {
  local path="$1"
  if is_protected_dir "$path" hooks || is_protected_dir "$path" scripts || \
     is_protected_dir "$path" .claude; then
    return 0
  fi
  case "$path" in
    "$ROOT"/CLAUDE.md|"$ROOT_REAL"/CLAUDE.md|CLAUDE.md|../CLAUDE.md|../*/CLAUDE.md)
      return 0 ;;
  esac
  return 1
}

if is_control_file "$TARGET_FILE"; then
  # Allow only when task_type is "framework".
  TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
  if [ "$TASK_TYPE" = "framework" ]; then
    emit_allow
    exit 0
  fi
  REASON=$(printf '[integrity] Framework control file edit blocked during project work (task_type=%s). Only framework tasks may edit hooks/scripts/.claude/CLAUDE.md.' "$TASK_TYPE")
  emit_deny "$REASON"
  exit 0
fi

# --- ROOT-external absolute targets: not this project's code (C5, iter44) ---
# Control files / templates / docs are handled above. The Client-mode lock and
# the plan gate below both exist to stop edits to THIS project's code; a clearly
# ROOT-external absolute path (e.g. global auto-memory at ~/.claude/.../memory/)
# is not project code, so neither applies — short-circuit to allow. This is
# intentional for both gates: auto-memory is mode-independent. Relative targets
# stay gated (cwd unknown; Edit/Write always supply absolute paths anyway).
# Fail-safe: if $ROOT_REAL were ever empty its pattern collapses to /*, which
# matches every absolute path into the first (keep-gating) arm — i.e. it errs
# toward gating, never toward allowing.
case "$TARGET_FILE" in
  # The literal '/' after $ROOT is load-bearing: it anchors the boundary so a
  # sibling like /path/aegis-backup does NOT match ROOT /path/aegis (no false
  # "internal"); only true children /path/aegis/... do.
  "$ROOT"/*|"$ROOT_REAL"/*) ;;   # inside the project root → keep gating
  /*)
    emit_allow
    exit 0
    ;;
esac

# Extract mode and plan gate from STATUS.md frontmatter.
MODE=$(frontmatter_value "$STATUS_FILE" "mode")
PLAN_GATE=$(gate_value "$STATUS_FILE" "plan")

# Block code edits in Client mode.
if [ "$MODE" = "Client" ]; then
  emit_deny "[gate] Client mode: code edits are blocked. Complete Client phases and get client_ready_for_dev approval first."
  exit 0
fi

# Block code edits when plan gate is not approved.
if [ "$PLAN_GATE" != "approved" ] && [ "$PLAN_GATE" != "n/a" ]; then
  REASON=$(printf '[gate] Plan gate is %s. Complete brainstorm and plan phases before editing code.' "$PLAN_GATE")
  emit_deny "$REASON"
  exit 0
fi

emit_allow
exit 0
