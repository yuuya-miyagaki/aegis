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
# AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN
# I1 (iter41): PostToolUse fail-closed. If safety.sh is unreadable / unsourceable
# the libs below cannot load and the audit (gate/mode tamper detection) would die
# under set -e with empty stdout = allow = fail-open. Emit a PostToolUse block
# instead. Distinct from the PreToolUse byte-identity fallback (different schema).
if [ ! -r "${SCRIPT_DIR}/lib/safety.sh" ]; then
  printf '[aegis-safety] fail-closed: safety.sh not readable\n' >&2
  printf '%s\n' '{"decision":"block","reason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}'
  exit 0
fi
set +e
source "${SCRIPT_DIR}/lib/safety.sh" 2>/dev/null
_aegis_safety_rc=$?
set -e
if [ "$_aegis_safety_rc" -ne 0 ]; then
  printf '[aegis-safety] fail-closed: safety.sh source failed\n' >&2
  printf '%s\n' '{"decision":"block","reason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}'
  exit 0
fi
# AEGIS_SAFETY_FALLBACK_POSTTOOL_END
# Resolve framework root (allow CLAUDE_PROJECT_DIR override for test fixtures
# that source hooks from a copy laid out outside the framework repo).
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
STATUS_FILE="${ROOT}/docs/STATUS.md"
SNAPSHOT_FILE="${ROOT}/.claude/.gate-snapshot"
AUDIT_SKIP_LOG="${ROOT}/.claude/.audit-skip.log"

# Load shared libs fail-closed (PostToolUse block on absence/source failure).
# gate/mode tamper detection is bash-only (frontmatter.sh), so it must not be
# skipped just because a lib is missing.
aegis_require_lib_block "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib_block "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib_block "${SCRIPT_DIR}/lib/frontmatter.sh"
aegis_require_lib_block "${SCRIPT_DIR}/lib/phase-skills.sh"
# iter43 (I3): snapshot single-source. Required (fail-closed): the snapshot is
# the tamper-evidence baseline; a broken install missing it must fail loud like
# every other core lib (F6 life-support doctrine), not silently stop regen.
aegis_require_lib_block "${SCRIPT_DIR}/lib/snapshot.sh"
# layer-2 cp-lock lib (optional — absent in minimal scaffolds).
[ -r "${SCRIPT_DIR}/lib/cp-lock.sh" ] && source "${SCRIPT_DIR}/lib/cp-lock.sh" 2>/dev/null || true

# iter43 (I3): layer-2 re-lock from the CURRENT STATUS task_type. Called only on
# paths that are NOT a tamper block — see the two call sites. chmod side-effect
# only; never emits and never alters the audit decision.
_aegis_relock_from_status() {
  if command -v aegis_cp_apply >/dev/null 2>&1; then
    local _tt
    _tt=$(frontmatter_value "$STATUS_FILE" "task_type" || true)
    aegis_cp_apply "$ROOT" "$_tt" || true
  fi
}

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

# K-7 (v1.6.2) consumer policy: snapshot lifecycle.
#   - STATUS.md missing → can't compare, skip audit (no allowance log).
#   - snapshot missing → first-edit allowance: allow but log to
#     .audit-skip.log so the next SessionStart can warn on accumulation.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi
# iter43 (I3): the layer-2 re-lock (aegis_cp_apply) MOVED from the top of this
# hook to (a) this first-edit branch and (b) the clean path after the tamper
# checks. It must NOT run on a tamper BLOCK: a raw Edit of
# task_type:<locked>→framework would, if cp_apply ran first, UNLOCK the moat
# before the task-tamper check could block — handing the edit the very write
# access the block denies. The first-edit branch has no snapshot baseline (so no
# tamper is even possible), so re-locking from STATUS there is safe and preserves
# the iter37 backstop (a STATUS edit re-asserts the correct moat state).
if [ ! -f "$SNAPSHOT_FILE" ]; then
  mkdir -p "$(dirname "$AUDIT_SKIP_LOG")" 2>/dev/null || true
  printf '%s first-edit allowance (snapshot missing)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)" \
    >> "$AUDIT_SKIP_LOG" 2>/dev/null || true
  _aegis_relock_from_status
  emit_allow
  exit 0
fi

# K-7 (v1.6.2) consumer policy: snapshot integrity check.
# snapshot exists but a required field (phase or mode) is empty / missing
# → snapshot was partially written or tampered. Fail-closed (emit_block)
# so the tamper detector below isn't trivially bypassed by editing the
# snapshot to a blank field.
_AEGIS_SNAP_PHASE_CHECK=$(frontmatter_value "$SNAPSHOT_FILE" "phase")
_AEGIS_SNAP_MODE_CHECK=$(frontmatter_value "$SNAPSHOT_FILE" "mode")
if [ -z "$_AEGIS_SNAP_PHASE_CHECK" ] || [ -z "$_AEGIS_SNAP_MODE_CHECK" ]; then
  emit_block "[integrity] snapshot ファイル (.claude/.gate-snapshot) に必須フィールド (phase / mode) が欠落しています。手動編集や中断書き込みの可能性 — ファイルを確認するか /recover を実行してください。"
  exit 0
fi

# Check ALL gates for unauthorized value changes.
# Detect ANY change (not just →approved) to prevent bypass via direct edit.
# Authorized changes go through update-gate.sh which updates the snapshot atomically.
for gate in client_ready_for_dev brainstorm plan review qa security deploy dev_ready_for_client; do
  OLD=$(gate_value "$SNAPSHOT_FILE" "$gate")
  NEW=$(gate_value "$STATUS_FILE" "$gate")

  if [ "$OLD" != "$NEW" ] && [ -n "$OLD" ]; then
    REASON=$(printf '[gate-tamper] %s gate changed %s→%s without authorization. Use the /gate command to change gate values.' "$gate" "$OLD" "$NEW")
    emit_block "$REASON"
    exit 0
  fi
done

# --- Phase transition validation ---
OLD_PHASE=$(frontmatter_value "$SNAPSHOT_FILE" "phase")
NEW_PHASE=$(frontmatter_value "$STATUS_FILE" "phase")

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
OLD_MODE=$(frontmatter_value "$SNAPSHOT_FILE" "mode")
NEW_MODE=$(frontmatter_value "$STATUS_FILE" "mode")

if [ -n "$OLD_MODE" ] && [ -n "$NEW_MODE" ] && [ "$OLD_MODE" != "$NEW_MODE" ]; then
  # Mode changed — verify boundary gate.
  if [ "$OLD_MODE" = "Client" ] && [ "$NEW_MODE" = "Dev" ]; then
    BOUNDARY_GATE=$(gate_value "$STATUS_FILE" "client_ready_for_dev")
    if [ "$BOUNDARY_GATE" != "approved" ]; then
      REASON=$(printf "[mode-tamper] Mode changed Client→Dev but client_ready_for_dev is '%s' (must be approved). Use /gate approve client_ready_for_dev first." "$BOUNDARY_GATE")
      emit_block "$REASON"
      exit 0
    fi
  elif [ "$OLD_MODE" = "Dev" ] && [ "$NEW_MODE" = "Client" ]; then
    BOUNDARY_GATE=$(gate_value "$STATUS_FILE" "dev_ready_for_client")
    if [ "$BOUNDARY_GATE" != "approved" ]; then
      REASON=$(printf "[mode-tamper] Mode changed Dev→Client but dev_ready_for_client is '%s' (must be approved). Use /gate approve dev_ready_for_client first." "$BOUNDARY_GATE")
      emit_block "$REASON"
      exit 0
    fi
  fi
fi

# --- Task field tamper validation (iter43 / I3) ---
# task_type controls gate requirements (STRICT_GATE_TASK_TYPES) AND the layer-2
# moat lock; task_size controls which gates apply. Authorized changes go through
# scripts/update-task.sh (which updates the snapshot atomically). A raw Edit that
# changes either field is tamper — block (mirrors the gate loop). The `[ -n "$OLD" ]`
# guard is a migration grace: an older snapshot without task fields is upgraded by
# the regen below rather than blocking a legitimate edit.
# NOTE: this MUST run before aegis_cp_apply below — see the moved-cp_apply note above.
for tf in task_type task_size; do
  OLD_TF=$(frontmatter_value "$SNAPSHOT_FILE" "$tf")
  NEW_TF=$(frontmatter_value "$STATUS_FILE" "$tf")
  if [ "$OLD_TF" != "$NEW_TF" ] && [ -n "$OLD_TF" ]; then
    REASON=$(printf '[task-tamper] %s changed %s→%s without authorization. Use scripts/update-task.sh to change task_type/task_size.' "$tf" "$OLD_TF" "$NEW_TF")
    emit_block "$REASON"
    exit 0
  fi
done

# iter43 (I3): layer-2 re-lock, MOVED here from the top. Only the clean path
# (all tamper checks passed) reaches this, so a blocked tamper edit can never
# unlock the moat. On a clean edit task_type == snapshot (untampered), so this is
# an idempotent re-assert of the correct lock state (backstop; the primary
# re-lock on a legitimate task_type change happens in update-task.sh).
_aegis_relock_from_status

# iter43: snapshot regen via single-source aegis_write_snapshot (atomic tmp→mv;
# K-7 rationale preserved in hooks/lib/snapshot.sh). Captures gate/phase/mode +
# task_type/task_size so the next edit's tamper check has a baseline for the
# task fields too.
aegis_write_snapshot "$ROOT" || true

# Phase-skill injection (P1-A): a legitimate phase transition is the moment the
# next phase's skills must be loaded — SessionStart injection cannot reach a
# mid-session transition (2026-06-12 behavioral review). additionalContext is
# advisory: clients that ignore it lose only the hint, never the audit (fail-safe).
if [ -n "$OLD_PHASE" ] && [ -n "$NEW_PHASE" ] && [ "$OLD_PHASE" != "$NEW_PHASE" ]; then
  TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
  SKILL_PATHS=$(aegis_phase_skill_paths "$ROOT" "$NEW_PHASE" "$TASK_TYPE" | tr '\n' ' ')
  SKILL_PATHS="${SKILL_PATHS% }"
  if [ -n "$SKILL_PATHS" ]; then
    emit_context PostToolUse "[phase-skills] phase=${NEW_PHASE}: 必読skill(Readで読み込んで従う): ${SKILL_PATHS}"
    exit 0
  fi
fi

emit_allow
exit 0
