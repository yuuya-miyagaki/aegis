#!/usr/bin/env bash
# Task update script — the ONLY authorized way to change task_type / task_size.
# iter43 (I3): task_type and task_size control which gates are required and the
# layer-2 moat lock. They are tamper-evidenced via .gate-snapshot +
# post-status-audit.sh. Because this script runs via Bash (not Edit/Write) it
# naturally bypasses the PostToolUse audit, then updates STATUS.md + snapshot
# atomically — mirroring scripts/update-gate.sh.
#
# Usage: bash scripts/update-task.sh [--type <type>] [--size <size>]
#   at least one of --type / --size is required.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"
SNAPSHOT_DIR="${ROOT}/.claude"

source "${ROOT}/hooks/lib/frontmatter.sh"
# snapshot single-source (iter43). Required: without it we cannot keep the
# snapshot in sync, so refuse rather than leave a stale tamper baseline.
if ! source "${ROOT}/hooks/lib/snapshot.sh" 2>/dev/null; then
  echo "ERROR: hooks/lib/snapshot.sh not available — cannot update snapshot"
  exit 1
fi
# layer-2 CP lock lib (optional — absent in minimal scaffolds). Used to re-apply
# the moat when task_type changes.
if [ -f "${ROOT}/hooks/lib/cp-lock.sh" ]; then
  source "${ROOT}/hooks/lib/cp-lock.sh" 2>/dev/null || true
fi

# Valid enums. MUST mirror check_status.py ALLOWED_TASK_TYPES / ALLOWED_TASK_SIZES.
VALID_TASK_TYPES="feature refactor bugfix hotfix framework"
VALID_TASK_SIZES="S M L"

# --- Argument parsing ---
NEW_TYPE=""
NEW_SIZE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --type)
      NEW_TYPE="${2:-}"
      shift 2 || { echo "ERROR: --type requires a value"; exit 1; }
      ;;
    --size)
      NEW_SIZE="${2:-}"
      shift 2 || { echo "ERROR: --size requires a value"; exit 1; }
      ;;
    *)
      echo "ERROR: unknown argument '$1'"
      echo "Usage: bash scripts/update-task.sh [--type <type>] [--size <size>]"
      exit 1
      ;;
  esac
done

if [ -z "$NEW_TYPE" ] && [ -z "$NEW_SIZE" ]; then
  echo "Usage: bash scripts/update-task.sh [--type <type>] [--size <size>]"
  echo ""
  echo "Valid types: $VALID_TASK_TYPES"
  echo "Valid sizes: $VALID_TASK_SIZES"
  echo "At least one of --type / --size is required."
  exit 1
fi

# --- Enum validation ---
if [ -n "$NEW_TYPE" ]; then
  _ok=false
  for t in $VALID_TASK_TYPES; do [ "$t" = "$NEW_TYPE" ] && _ok=true && break; done
  if [ "$_ok" != "true" ]; then
    echo "ERROR: invalid task_type '$NEW_TYPE'"
    echo "Valid types: $VALID_TASK_TYPES"
    exit 1
  fi
fi
if [ -n "$NEW_SIZE" ]; then
  _ok=false
  for s in $VALID_TASK_SIZES; do [ "$s" = "$NEW_SIZE" ] && _ok=true && break; done
  if [ "$_ok" != "true" ]; then
    echo "ERROR: invalid task_size '$NEW_SIZE'"
    echo "Valid sizes: $VALID_TASK_SIZES"
    exit 1
  fi
fi

if [ ! -f "$STATUS_FILE" ]; then
  echo "ERROR: docs/STATUS.md not found"
  exit 1
fi

# --- Exclusive lock (shared with update-gate.sh) ---
# Both scripts write STATUS.md + snapshot; sharing one lock dir serializes all
# STATUS writes. The full orphan-reclaim protocol lives in update-gate.sh — here
# a bounded mkdir-retry is enough: a lingering lock makes this run fail-closed
# (retry once the other writer finishes), the same UX as update-gate.sh.
mkdir -p "$SNAPSHOT_DIR"
LOCK_DIR="${SNAPSHOT_DIR}/.gate-update.lock.d"
LOCK_OK=false
for _ in {1..50}; do
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_OK=true
    trap 'rm -f "$LOCK_DIR/pid" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
    printf '%s' "$$" > "$LOCK_DIR/pid" 2>/dev/null || true
    break
  fi
  sleep 0.2
done
if [ "$LOCK_OK" != "true" ]; then
  echo "ERROR: a gate/task update lock blocks this run (${LOCK_DIR})."
  echo "Retry shortly. If no other session is running, remove the stale directory."
  exit 1
fi

# --- Read current task_type (to decide whether the moat must be re-applied) ---
OLD_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type" || true)

# --- Update STATUS.md atomically ---
# Anchored ^task_type: / ^task_size: (cannot match task_size_rationale: — the
# char after task_size is '_'). Replace if the line exists; insert if absent
# (task_size is an optional field that the STATUS template omits, so the FIRST
# size set — brainstorm Step D on a fresh project — must be able to add it).
# task_type is schema-required: if absent, error rather than silently no-op.
# _set_field <key> <value>: print STATUS_FILE to stdout with <key> set to <value>
# (replace if the line exists; insert after task_type if absent). Reads the
# script-global STATUS_FILE (each call runs after the previous mv, so it sees the
# latest content). rc 2 if task_type itself is absent (schema violation).
_set_field() {
  local key="$1" val="$2"
  if grep -q "^${key}:" "$STATUS_FILE"; then
    sed "s|^\(${key}:\).*|\1 ${val}|" "$STATUS_FILE"
  elif [ "$key" = "task_type" ]; then
    echo "ERROR: docs/STATUS.md has no '${key}:' line (schema violation)" >&2
    return 2
  else
    # Insert after the task_type: line (always present) so the new field lands
    # in the frontmatter scalar block, not inside a nested section.
    awk -v line="${key}: ${val}" '{print} /^task_type:/{print line}' "$STATUS_FILE"
  fi
}

TMP="${STATUS_FILE}.tmp.$$"
if [ -n "$NEW_TYPE" ]; then
  _set_field task_type "$NEW_TYPE" > "$TMP" || { rm -f "$TMP"; exit 1; }
  mv "$TMP" "$STATUS_FILE"
  echo "[task-update] task_type → ${NEW_TYPE}"
fi
if [ -n "$NEW_SIZE" ]; then
  _set_field task_size "$NEW_SIZE" > "$TMP" || { rm -f "$TMP"; exit 1; }
  mv "$TMP" "$STATUS_FILE"
  echo "[task-update] task_size → ${NEW_SIZE}"
fi

# --- Update snapshot (after STATUS write) ---
aegis_write_snapshot "$ROOT" || true

# --- Re-apply moat if task_type changed (last: lock side-effect) ---
if [ -n "$NEW_TYPE" ] && [ "$NEW_TYPE" != "$OLD_TYPE" ]; then
  if command -v aegis_cp_apply >/dev/null 2>&1; then
    aegis_cp_apply "$ROOT" "$NEW_TYPE" || \
      echo "[task-update] WARNING: control-plane re-lock partial (layer-1 static moat still active)"
  fi
fi

echo "[task-update] STATUS.md and .gate-snapshot updated."
