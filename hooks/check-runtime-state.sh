#!/usr/bin/env bash
# PreToolUse hook for Bash: residual static guard after the iter57 moat
# handover. The PRIMARY moat for the stable control-plane (hooks/ scripts/
# templates/ CLAUDE.md .claude/{rules,skills,commands,agents}) is the OS lock
# (hooks/lib/cp-lock.sh — syscall-enforced, form-independent). This hook keeps
# ONLY what the lock cannot cover:
#   (1) runtime-state writes — docs/STATUS.md and the non-locked parts of
#       .claude/ (settings*.json, .gate-snapshot, evidence-log …) must stay
#       writable for the harness/framework, so Bash writes are gated
#       statically. Allowlist = hooks/lib/scripts-manifest.tsv class allow|ask
#       (single owner, iter55). manifest unreadable = deny (fail-closed).
#   (2) unlock forms — chmod/chflags/chattr aimed at the locked CP would turn
#       an EACCES "self-repair" into an uncaught accident (rev.2 撤回理由②).
#       Denied with a policy message that names the correct path.
#   (3) broad recursive chmod (-R on . / .. / / / *) — carries no CP token but
#       unlocks the whole tree including the CP (grill 致命4). ASK, not deny:
#       a user project may legitimately bulk-chmod its own tree.
# Everything else that lived in the retired check-control-plane.sh
# (obfuscation token analysis, glob/quote-split/interpreter resolution) is
# gone by design: those forms hit EACCES at the syscall regardless of shape.
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
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
STATUS_FILE="${ROOT}/docs/STATUS.md"

aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"

INPUT=$(cat)

# No STATUS.md = no framework context: nothing to guard.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Case folding (iter54 C-1): on a case-insensitive FS, DOCS/STATUS.MD is the
# same inode as docs/STATUS.md — deny-side greps must fold there (and only
# there; folding allow-side carve-outs would WIDEN allow, the wrong way).
CASE_FOLD=0
if aegis_fs_case_insensitive "$ROOT"; then
  CASE_FOLD=1
fi
CASE_I=()
if [ "$CASE_FOLD" = "1" ]; then
  CASE_I=(-i)
fi

# Guard targets. RUNTIME_STATE is deliberately NARROWER than the retired
# CONTROL_PLANE regex: a user project's own foo/STATUS.md is not our
# runtime-state (the aegis STATUS lives at docs/STATUS.md; the bare form
# catches cwd-shifted mentions like `cd docs && sed -i … STATUS.md`).
RUNTIME_STATE='docs/STATUS\.md|(^|[^A-Za-z0-9_./-])STATUS\.md|\.claude/|\.claude([^A-Za-z0-9_/]|$)'
# Stable-CP tokens, used ONLY for the unlock-form check (the lock itself is
# the moat for these paths; boundary keeps a project's own src/hooks/ out).
LOCKED_CP='(^|[^A-Za-z0-9_./-])(\./)*(hooks|scripts|templates)(/|[[:space:]]|$)|(^|[^A-Za-z0-9_./-])CLAUDE\.md'
UNLOCK_TOOLS='(^|[^A-Za-z0-9_])(chmod|chflags|chattr)([[:space:]]|$)'

# Command extraction (same contract as the retired hook): python3-first; the
# bash fast-path would truncate at the first embedded escaped quote and could
# hide a mention placed after it — treat that as extraction failure.
CMD=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
if [ -z "$CMD" ] && ! printf '%s' "$INPUT" | grep -q '\\"'; then
  CMD=$(extract_command "$INPUT")
fi
# Embedded newlines/CR are command separators (framework convention): a later
# line must not ride behind a benign first line in the line-oriented greps.
if [ -n "$CMD" ]; then
  CMD=$(printf '%s' "$CMD" | tr '\n\r' ';;')
fi

_mentions_runtime_state() {
  printf '%s' "$1" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE"
}
_unlock_form_on_cp() {
  printf '%s' "$1" | grep -qE "$UNLOCK_TOOLS" || return 1
  printf '%s' "$1" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$LOCKED_CP|\.claude/(rules|skills|commands|agents)/"
}
# grill 致命4: the most natural EACCES "self-repair" (`chmod -R u+w .`)
# carries no CP token, but recursion unlocks the CP with it.
_recursive_chmod_broad() {
  printf '%s' "$1" | grep -qE '(^|[^A-Za-z0-9_])chmod[[:space:]][^;|&]*-R' || return 1
  printf '%s' "$1" | grep -qE '[[:space:]](\.{1,2}/?|/|\*)([[:space:]]|$)'
}

if [ -n "$CMD" ]; then
  if ! _mentions_runtime_state "$CMD" && ! _unlock_form_on_cp "$CMD" \
     && ! _recursive_chmod_broad "$CMD"; then
    emit_allow
    exit 0
  fi
else
  # Extraction failed — fall back to the raw input (fail-closed). Real hook
  # input always carries transcript_path under ~/.claude/projects/, which the
  # `.claude/` alternation matches, so unextractable real input stays on the
  # deny path by construction (same property as the retired hook).
  if ! printf '%s' "$INPUT" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE|$LOCKED_CP"; then
    emit_allow
    exit 0
  fi
fi

# framework task: the CP is legitimately unlocked and STATUS/settings writes
# are the framework's own work — allow everything (retired-hook parity).
TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
if [ "$TASK_TYPE" = "framework" ]; then
  emit_allow
  exit 0
fi

if [ -n "$CMD" ] && _unlock_form_on_cp "$CMD"; then
  emit_deny "[integrity] chmod/chflags/chattr で control-plane（hooks/ scripts/ templates/ CLAUDE.md .claude/rules 等）の書込み保護を変更しようとしています。これは aegis の OS-lock（主 moat）です。EACCES が出た場合も解錠せず、framework の変更が正当な作業なら scripts/update-task.sh --type framework で task_type を切り替えてください。"
  exit 0
fi

if [ -n "$CMD" ] && _recursive_chmod_broad "$CMD"; then
  emit_ask "[integrity] 再帰 chmod（-R）がリポジトリ全体（. / .. / / / * 等）に及びます。control-plane の OS-lock（主 moat）も解錠されるため確認してください。EACCES への対処なら chmod ではなく task_type=framework への切替（scripts/update-task.sh）が正です。"
  exit 0
fi

# Default: deny. runtime-state referenced, not an authorized path.
emit_deny "[integrity] runtime-state（docs/STATUS.md・.claude/ 設定類）へ書込みうる Bash コマンドは project work（task_type=${TASK_TYPE}）中はブロックされます。ゲート値は scripts/update-gate.sh、task_type/task_size は scripts/update-task.sh を単体で実行してください。読取りは cat/grep 等の単体コマンドなら許可されます。"
exit 0
