#!/usr/bin/env bash
# PostToolUse hook for Edit/Write/NotebookEdit on STATUS.md: detects unauthorized
# gate advancement, phase skips, and mode tamper.
# Compares current gate_approvals against the session-start snapshot.
# If any gate / phase / mode advances without authorization, block via top-level
# `{"decision":"block","reason":"..."}` (PostToolUse spec, v0.12.2).
#
# Target filtering (v0.12.2): hooks.template.json no longer uses an `if` filter.
# The official Claude Code Hooks spec restricts `if` to a single permission rule
# with no `&&`/`||`/list, which silently neutered the previous
# `Edit(*STATUS.md) || Write(*STATUS.md) || NotebookEdit(*STATUS.md)` filter and
# missed Write / NotebookEdit edits. The matcher `Edit|Write|NotebookEdit` is
# registered, and this script's `case "$TARGET_FILE" in *STATUS.md` filter below
# covers all three tools.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"
SNAPSHOT_FILE="${ROOT}/.claude/.gate-snapshot"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

# Read stdin (JSON with tool_input/tool_result).
INPUT=$(cat)

# Primary target filter (v0.12.2+): hooks.template.json no longer uses an `if`
# field — the Claude Code Hooks spec restricts `if` to a single permission rule
# with no `||`, which silently neutered the previous Write/NotebookEdit coverage.
# The matcher is `Edit|Write|NotebookEdit`, and this `case "$TARGET_FILE" in
# *STATUS.md` is the authoritative filter covering all three tool variants.
TARGET_FILE=$(extract_file_path "$INPUT")
case "$TARGET_FILE" in
  *STATUS.md) ;; # proceed with audit
  *)
    emit_allow
    exit 0
    ;;
esac

# If snapshot or STATUS.md doesn't exist, skip audit.
if [ ! -f "$SNAPSHOT_FILE" ] || [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Extract gate value from a file.
extract_gate() {
  local file="$1"
  local gate="$2"
  grep -A20 "^gate_approvals:" "$file" | grep -m1 "${gate}:" | sed "s/.*${gate}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}

# Check ALL gates for unauthorized value changes.
# Detect ANY change (not just →approved) to prevent bypass via direct edit.
# Authorized changes go through update-gate.sh which updates the snapshot atomically.
for gate in client_ready_for_dev brainstorm plan review qa security deploy dev_ready_for_client; do
  OLD=$(extract_gate "$SNAPSHOT_FILE" "$gate")
  NEW=$(extract_gate "$STATUS_FILE" "$gate")

  if [ "$OLD" != "$NEW" ] && [ -n "$OLD" ]; then
    REASON=$(printf '[gate-tamper] %s gate changed %s→%s without authorization. Use the /gate command to change gate values.' "$gate" "$OLD" "$NEW")
    emit_block "$REASON"
    exit 0
  fi
done

# --- Phase transition validation ---
OLD_PHASE=$(grep -m1 "^phase:" "$SNAPSHOT_FILE" | sed "s/^phase:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
NEW_PHASE=$(grep -m1 "^phase:" "$STATUS_FILE" | sed "s/^phase:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

if [ -n "$OLD_PHASE" ] && [ -n "$NEW_PHASE" ] && [ "$OLD_PHASE" != "$NEW_PHASE" ]; then
  # set +e: python returning non-zero is expected (deny) — must not abort before emitting JSON.
  set +e
  TRANSITION_CHECK=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-phase-transition "$OLD_PHASE" "$NEW_PHASE" 2>&1)
  TRANSITION_RC=$?
  set -e
  if [ $TRANSITION_RC -ne 0 ]; then
    MSG=$(printf '%s' "$TRANSITION_CHECK" | tr '\n' ' ')
    REASON=$(printf '[phase-skip] %s' "$MSG")
    emit_block "$REASON"
    exit 0
  fi
fi

# --- Mode change validation ---
OLD_MODE=$(grep -m1 "^mode:" "$SNAPSHOT_FILE" | sed "s/^mode:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
NEW_MODE=$(grep -m1 "^mode:" "$STATUS_FILE" | sed "s/^mode:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

if [ -n "$OLD_MODE" ] && [ -n "$NEW_MODE" ] && [ "$OLD_MODE" != "$NEW_MODE" ]; then
  # Mode changed — verify boundary gate.
  extract_gate_from_status() {
    local gate="$1"
    grep -A20 "^gate_approvals:" "$STATUS_FILE" | grep -m1 "${gate}:" | sed "s/.*${gate}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
  }

  if [ "$OLD_MODE" = "Client" ] && [ "$NEW_MODE" = "Dev" ]; then
    BOUNDARY_GATE=$(extract_gate_from_status "client_ready_for_dev")
    if [ "$BOUNDARY_GATE" != "approved" ]; then
      REASON=$(printf "[mode-tamper] Mode changed Client→Dev but client_ready_for_dev is '%s' (must be approved). Use /gate approve client_ready_for_dev first." "$BOUNDARY_GATE")
      emit_block "$REASON"
      exit 0
    fi
  elif [ "$OLD_MODE" = "Dev" ] && [ "$NEW_MODE" = "Client" ]; then
    BOUNDARY_GATE=$(extract_gate_from_status "dev_ready_for_client")
    if [ "$BOUNDARY_GATE" != "approved" ]; then
      REASON=$(printf "[mode-tamper] Mode changed Dev→Client but dev_ready_for_client is '%s' (must be approved). Use /gate approve dev_ready_for_client first." "$BOUNDARY_GATE")
      emit_block "$REASON"
      exit 0
    fi
  fi
fi

# No tampering or invalid transition detected. Update snapshot to reflect legitimate changes.
# Extract gate_approvals section for next comparison.
sed -n '/^gate_approvals:/,/^[a-z]/{ /^gate_approvals:/p; /^  /p; }' "$STATUS_FILE" > "$SNAPSHOT_FILE" 2>/dev/null || true
# Preserve phase in snapshot.
grep -m1 "^phase:" "$STATUS_FILE" >> "$SNAPSHOT_FILE" 2>/dev/null || true
# Preserve mode in snapshot.
grep -m1 "^mode:" "$STATUS_FILE" >> "$SNAPSHOT_FILE" 2>/dev/null || true

emit_allow
exit 0
