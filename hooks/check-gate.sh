#!/usr/bin/env bash
# PreToolUse hook for Edit/Write: blocks code edits until the implement-gating
# approval is in place. The gate is size-aware: task_size=S has no plan phase
# (impl->review->ship->docs), so its pre-implement approval is the brainstorm
# gate; every other size (M/L/unset/invalid) keeps the conservative plan-gate
# check.
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

# C-1 (iter54): conditional case-fold. On a case-insensitive FS an Edit to
# HOOKS/lib/emit.sh or CLAUDE.MD lands on the real control file, so the
# protection `case` matches below run under nocasematch — but only when the
# probe (hooks/lib/safety.sh) says the FS folds case; on a case-sensitive FS
# an uppercase HOOKS/ is a legitimately distinct user dir. The docs/* allowlist
# above stays case-sensitive: not folding it only OVER-gates (a DOCS/ edit
# falls through to the size-aware implement gate), never weakens protection.
CASE_FOLD=0
if aegis_fs_case_insensitive "$ROOT"; then
  CASE_FOLD=1
fi

# Lexically resolve ./ and ../ segments so non-canonical forms (././hooks/,
# foo/../hooks/, $ROOT/./hooks/) cannot dodge the root-anchored patterns.
# No filesystem access; unresolvable leading ..s are preserved.
normalize_target() {
  local p="$1" out="" seg abs="" had_noglob=0
  case "$p" in /*) abs="/" ;; esac
  # S-glob-2 (iter54): the unquoted $p word-split below must NOT
  # pathname-expand. A literal segment like [id] (Next.js route) or [h]ooks
  # otherwise matches real files in the hook CWD and rewrites the target —
  # e.g. Edit("[h]ooks/lib/emit.sh") glob-expanded to hooks/lib/emit.sh and
  # produced a spurious control-plane deny. noglob is save/restored (the
  # function runs in a $() subshell today, but do not rely on that).
  case $- in *f*) had_noglob=1 ;; esac
  set -f
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
  [ "$had_noglob" = "1" ] || set +f
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
  local path="$1" name="$2" rc=1
  # C-1: nocasematch is scoped to this case and restored immediately (bash
  # `case` honors the shopt). Guarded by if (not `&&`) so set -e survives
  # the CASE_FOLD=0 branch.
  if [ "$CASE_FOLD" = "1" ]; then shopt -s nocasematch; fi
  case "$path" in
    "$ROOT"/$name/*|"$ROOT_REAL"/$name/*|$name/*|../$name/*|../*/$name/*)
      rc=0 ;;
  esac
  if [ "$CASE_FOLD" = "1" ]; then shopt -u nocasematch; fi
  return $rc
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
  local path="$1" rc=1
  if is_protected_dir "$path" hooks || is_protected_dir "$path" scripts || \
     is_protected_dir "$path" .claude; then
    return 0
  fi
  # C-1: fold the CLAUDE.md name match too (CLAUDE.MD is the same file on a
  # case-insensitive FS).
  if [ "$CASE_FOLD" = "1" ]; then shopt -s nocasematch; fi
  case "$path" in
    "$ROOT"/CLAUDE.md|"$ROOT_REAL"/CLAUDE.md|CLAUDE.md|../CLAUDE.md|../*/CLAUDE.md)
      rc=0 ;;
  esac
  if [ "$CASE_FOLD" = "1" ]; then shopt -u nocasematch; fi
  return $rc
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
# the size-aware implement gate below both exist to stop edits to THIS project's
# code; a clearly
# ROOT-external absolute path (e.g. global auto-memory at ~/.claude/.../memory/)
# is not project code, so neither applies — short-circuit to allow. This is
# intentional for both gates: auto-memory is mode-independent. Relative targets
# stay gated (cwd unknown; Edit/Write always supply absolute paths anyway).
# Fail-safe: if $ROOT_REAL were ever empty its pattern collapses to /*, which
# matches every absolute path into the first (keep-gating) arm — i.e. it errs
# toward gating, never toward allowing.
# C-1 (iter54): the boundary test folds case with the FS — an uppercase
# spelling of a ROOT-internal path is the SAME project code on a
# case-insensitive FS and must NOT escape through the external-allow arm.
is_root_external_absolute() {
  local t="$1" rc=1
  if [ "$CASE_FOLD" = "1" ]; then shopt -s nocasematch; fi
  case "$t" in
    # The literal '/' after $ROOT is load-bearing: it anchors the boundary so a
    # sibling like /path/aegis-backup does NOT match ROOT /path/aegis (no false
    # "internal"); only true children /path/aegis/... do.
    "$ROOT"/*|"$ROOT_REAL"/*) ;;   # inside the project root → keep gating
    /*) rc=0 ;;                    # ROOT-external absolute → not project code
  esac
  if [ "$CASE_FOLD" = "1" ]; then shopt -u nocasematch; fi
  return $rc
}

if is_root_external_absolute "$TARGET_FILE"; then
  emit_allow
  exit 0
fi

# --- Repo-root prose (*.md): gates guard code, not prose (iter55) ---
# DOGFOOD-LOG.md / README.md など repo 直下のメタ文書は Client モード・plan 未承認
# でも編集可（ドッグフード ゲート戦闘2・4: 観測ログが書けずバッファ運用を強制された）。
# ここに到達する時点で CLAUDE.md・hooks/scripts/.claude/templates は上の control
# 検査で deny 済み、docs/* は先頭 allowlist で allow 済み。suffix は FS に合わせて
# case-fold（.MD 変種）。サブディレクトリの .md はコード木の可能性があるため対象外。
is_root_prose_md() {
  local t="$1" d rc=1
  # 盲検2次(security): symlink は解決しないため、repo 直下の `*.md` が制御ファイルへの
  # symlink だと prose 判定を通って allow され、iter55 前（plan-gate で deny）からの
  # 防御多層の後退になる。既存の symlink は fast-path に載せず gate に落とす（deny 復帰）。
  # 新規 prose ファイル（未作成）は `-L` 偽＝通る。Edit/Write は symlink を作れないため
  # これで LLM 由来経路は塞がり、事前設置 symlink も carve-out から除外される。
  if [ -L "$t" ]; then
    return 1
  fi
  d=$(dirname "$t")
  if [ "$CASE_FOLD" = "1" ]; then shopt -s nocasematch; fi
  case "$t" in
    *.md)
      case "$d" in
        "$ROOT"|"$ROOT_REAL"|.) rc=0 ;;
      esac ;;
  esac
  if [ "$CASE_FOLD" = "1" ]; then shopt -u nocasematch; fi
  return $rc
}

if is_root_prose_md "$TARGET_FILE"; then
  emit_allow
  exit 0
fi

# Extract mode from STATUS.md frontmatter.
MODE=$(frontmatter_value "$STATUS_FILE" "mode")

# Block code edits in Client mode (unchanged; runs before the gate check).
if [ "$MODE" = "Client" ]; then
  emit_deny "[gate] Client mode: code edits are blocked. Complete Client phases and get client_ready_for_dev approval first."
  exit 0
fi

# Size-aware implement gate. task_size=S has no plan phase in its flow
# (impl->review->ship->docs), so gating on plan would make S code edits
# structurally impossible (plan can never reach approved for S). For S the pre-implement
# approval is the brainstorm gate; every other size (M/L/unset/invalid) keeps
# the conservative plan-gate check — the gate is never loosened by an unknown
# or malformed task_size. Pure bash: only frontmatter_value / gate_value.
#
# task_size is read via frontmatter_value, which is frontmatter-scoped for
# ---delimited files since iter66 — a body `task_size: S` line can never spoof
# the gate into the S branch when the frontmatter omits the key (b9c95f7
# hardening now lives in the library, matching python extract_frontmatter).
TASK_SIZE=$(frontmatter_value "$STATUS_FILE" task_size)

if [ "$TASK_SIZE" = "S" ]; then
  BRAINSTORM_GATE=$(gate_value "$STATUS_FILE" "brainstorm")
  # Block code edits when the brainstorm gate is not approved (fail-closed: an
  # empty/missing value is not approved/n/a → deny).
  if [ "$BRAINSTORM_GATE" != "approved" ] && [ "$BRAINSTORM_GATE" != "n/a" ]; then
    REASON=$(printf '[gate] task_size=S skips the plan phase; the implement gate is brainstorm, which is %s. Complete the brainstorm phase before editing code.' "$BRAINSTORM_GATE")
    emit_deny "$REASON"
    exit 0
  fi
else
  PLAN_GATE=$(gate_value "$STATUS_FILE" "plan")
  # Block code edits when plan gate is not approved.
  if [ "$PLAN_GATE" != "approved" ] && [ "$PLAN_GATE" != "n/a" ]; then
    REASON=$(printf '[gate] Plan gate is %s. Complete brainstorm and plan phases before editing code.' "$PLAN_GATE")
    emit_deny "$REASON"
    exit 0
  fi
fi

emit_allow
exit 0
