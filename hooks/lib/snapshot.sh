#!/usr/bin/env bash
# hooks/lib/snapshot.sh — single source for writing .claude/.gate-snapshot.
# iter43 (I3): the snapshot is the tamper-evidence baseline compared by
# post-status-audit.sh. It captures the gate_approvals block + phase + mode +
# task_type + task_size. task_type/task_size were added in iter43 so that
# raw Edits to them (which silently change gate requirements and the layer-2
# moat lock) become tamper-evident, mirroring how gates already work.
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
  mkdir -p "$snapshot_dir" 2>/dev/null || return 1
  local tmp="${snapshot_file}.tmp.$$"
  {
    sed -n '/^gate_approvals:/,/^[a-z]/{ /^gate_approvals:/p; /^  /p; }' "$status_file" 2>/dev/null
    grep -m1 "^phase:" "$status_file" 2>/dev/null
    grep -m1 "^mode:" "$status_file" 2>/dev/null
    grep -m1 "^task_type:" "$status_file" 2>/dev/null
    grep -m1 "^task_size:" "$status_file" 2>/dev/null
  } > "$tmp" 2>/dev/null && mv "$tmp" "$snapshot_file" 2>/dev/null || {
    rm -f "$tmp" 2>/dev/null || true
    return 1
  }
  return 0
}
