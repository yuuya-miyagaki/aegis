#!/usr/bin/env bash
# hooks/lib/snapshot.sh — single source for writing .claude/.gate-snapshot.
# iter43 (I3): the snapshot is the tamper-evidence baseline compared by
# post-status-audit.sh. It captures the gate_approvals block + phase + mode +
# task_type + task_size. task_type/task_size were added in iter43 so that
# raw Edits to them (which silently change gate requirements and the layer-2
# moat lock) become tamper-evident, mirroring how gates already work.

# snapshot.sh consumes read_frontmatter/_section_filter; source defensively
# so a caller that loads snapshot.sh alone still works (bash 3.2 safe).
if ! declare -F read_frontmatter >/dev/null 2>&1; then
  . "$(dirname "${BASH_SOURCE[0]}")/frontmatter.sh"
fi
#
# Single-function / multiple-fire-point design (iter37): session-start.sh,
# update-gate.sh, update-task.sh, and post-status-audit.sh all call this helper
# instead of duplicating the extraction inline (which had drifted to 3 copies).
#
# Atomic write (K-7, v1.6.2): stage in a per-PID tmp then rename. A crash before
# the mv leaves the previous snapshot intact — never a partially-written file
# with phase/mode missing (which the tamper detector's `[ -n "$OLD" ]` guard
# would bypass). Non-destructive: if STATUS.md is absent or the staging write
# fails, the existing snapshot is left untouched.

# aegis_write_snapshot <root> — regenerate <root>/.claude/.gate-snapshot from
# <root>/docs/STATUS.md. rc 0 on success; non-zero (without clobbering the
# existing snapshot) if STATUS.md is missing or staging fails.
aegis_write_snapshot() {
  local root="$1"
  [ -n "$root" ] || return 1
  local status_file="${root}/docs/STATUS.md"
  local snapshot_dir="${root}/.claude"
  local snapshot_file="${snapshot_dir}/.gate-snapshot"
  [ -f "$status_file" ] || return 1
  # Frontmatter-scoped source (iter66 Fix③): body lines can never poison the
  # tamper baseline. Malformed/unterminated frontmatter -> keep the existing
  # snapshot untouched (non-destructive, K-7) and report failure.
  local fm
  fm=$(read_frontmatter "$status_file") || return 1
  [ -n "$fm" ] || return 1
  mkdir -p "$snapshot_dir" 2>/dev/null || return 1
  local tmp="${snapshot_file}.tmp.$$"
  # `|| true` per key: an absent OPTIONAL key (task_size before brainstorm
  # Step D) must not abort the regen — the old whole-file version silently
  # failed here, leaving a stale snapshot (one enabler of the SF-010
  # empty-baseline window).
  {
    printf '%s\n' "$fm" | _section_filter gate_approvals
    printf '%s\n' "$fm" | grep -m1 "^phase:" || true
    printf '%s\n' "$fm" | grep -m1 "^mode:" || true
    printf '%s\n' "$fm" | grep -m1 "^task_type:" || true
    printf '%s\n' "$fm" | grep -m1 "^task_size:" || true
  } > "$tmp" 2>/dev/null && mv "$tmp" "$snapshot_file" 2>/dev/null || {
    rm -f "$tmp" 2>/dev/null || true
    return 1
  }
  return 0
}

# aegis_snapshot_gate_regression <root> — rc 0 when the EXISTING snapshot holds
# an earned gate value (approved / n/a) that current STATUS.md shows as pending.
# Consumed by session-start.sh so an accidental docs/ revert (full-review
# 2026-07-06 R1 / iter60 incident) cannot launder the recovery anchor away at
# the next session boundary. Fail-open toward CURRENT behaviour: missing or
# unreadable snapshot/STATUS -> rc 1 (caller regenerates as before). Authorized
# writers refresh the snapshot on every legitimate reset, so a normal rollover
# never trips this.
#
# The current STATUS gate_approvals block is read ONCE with a single `sed`
# (not one fork per snapshot line — that was O(lines) process spawns and hung
# session-start for minutes on a bloated/corrupt snapshot; 2nd-review security
# Major-2). No bash associative array: hooks target bash 3.2 (macOS default),
# which lacks `declare -A`. The block string is newline-prefixed and each
# earned gate is matched as a whole line via case. Gate names are restricted to
# [a-z_] as defense in depth so a tampered snapshot line cannot become a glob.
aegis_snapshot_gate_regression() {
  local root="$1"
  [ -n "$root" ] || return 1
  local status_file="${root}/docs/STATUS.md"
  local snapshot_file="${root}/.claude/.gate-snapshot"
  [ -f "$status_file" ] || return 1
  [ -f "$snapshot_file" ] || return 1
  local nl cur_block line gate
  nl=$'\n'
  cur_block=$(sed -n '/^gate_approvals:/,/^[a-z]/p' "$status_file" 2>/dev/null)
  cur_block="${nl}${cur_block}"   # newline-anchor the first line too
  while IFS= read -r line; do
    case "$line" in
      '  '*': approved'|'  '*': n/a') ;;
      *) continue ;;
    esac
    gate="${line%%:*}"; gate="${gate#  }"
    case "$gate" in ''|*[!a-z_]*) continue ;; esac
    # earned in the snapshot but pending now == a regression -> preserve anchor
    case "$cur_block" in
      *"${nl}  ${gate}: pending"*) return 0 ;;
    esac
  done < "$snapshot_file"
  return 1
}
