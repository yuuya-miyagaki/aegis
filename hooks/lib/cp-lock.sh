#!/usr/bin/env bash
# hooks/lib/cp-lock.sh — layer-2 OS/FS write-lock for the stable control-plane.
# Sourced by session-start.sh. pure-bash, bash 3.2 safe, idempotent.
#   lock   = chmod -R a-w  (removes write for all; read+exec preserved)
#   unlock = chmod -R u+w  (restores owner write)
# Failure is NON-fatal: the caller warns and continues (OS lock is a defense
# layer, not a fail-closed gate — layer-1 static moat is always present).
# Owner of the stable CP path set (single source of truth for the chmod target).
# NOTE: this is the FS-path enumeration for layer-2; it is intentionally NOT
# unified with check-control-plane.sh's CONTROL_PLANE regex (different domain:
# command-token matching vs filesystem paths).

# aegis_cp_paths <root> — print existing lock-target paths, one per line.
aegis_cp_paths() {
  local root="$1" p
  # NOTE: .claude/settings*.json は意図的に対象外（Claude Code ハーネスが
  # permission grant / config を settings へ書くため lock すると破損する。
  # settings は layer-1 で保護済）。
  for p in \
    "hooks" \
    "scripts" \
    "templates" \
    "CLAUDE.md" \
    ".claude/rules" \
    ".claude/skills" \
    ".claude/commands" \
    ".claude/agents"; do
    [ -e "${root}/${p}" ] && printf '%s\n' "${root}/${p}"
  done
}

# aegis_cp_lock <root> — make the stable CP read-only. rc 0 all-ok, 1 on any failure.
aegis_cp_lock() {
  local root="$1" rc=0 p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    chmod -R a-w "$p" 2>/dev/null || rc=1
  done < <(aegis_cp_paths "$root")
  return "$rc"
}

# aegis_cp_unlock <root> — restore owner write on the stable CP. rc 0/1 as above.
aegis_cp_unlock() {
  local root="$1" rc=0 p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    chmod -R u+w "$p" 2>/dev/null || rc=1
  done < <(aegis_cp_paths "$root")
  return "$rc"
}
