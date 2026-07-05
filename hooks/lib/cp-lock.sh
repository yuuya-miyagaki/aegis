#!/usr/bin/env bash
# hooks/lib/cp-lock.sh — layer-2 OS/FS write-lock for the stable control-plane.
# Sourced by session-start.sh. pure-bash, bash 3.2 safe, idempotent.
#   lock   = find <p> -exec chmod a-w  (removes write for all; read+exec preserved)
#   unlock = find <p> -exec chmod u+w  (restores owner write)
# Recursion uses `find -exec chmod {} +`, NOT `chmod -R`: this lib is also sourced
# by post-status-audit on a mid-session task_type change, which runs under the
# Claude Code hook sandbox where `chmod -R <dir>` affects ONLY the top-level CP
# directory and does NOT descend to nested files (e.g. hooks/lib/emit.sh) —
# leaving a desynced state the dir sentinel ([ -w <root>/hooks ]) then misreads as
# fully-applied, so the moat sticks half-locked. `find -exec chmod` walks every
# path explicitly and recurses correctly in that environment (iteration 40,
# reproduced + verified). Do NOT revert to `chmod -R`.
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
  # Guard: an empty root would make aegis_cp_paths emit absolute /hooks /scripts …
  # ([ -e ] would skip them on a normal system, but fail loud rather than silently).
  [ -n "$root" ] || return 1
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    # find -exec, not chmod -R (recurses under the hook sandbox; see header).
    # ! -type l (iter57): chmod FOLLOWS symlinks — locking through a link
    # would chmod a REAL file OUTSIDE the CP (iter55 symlink-pierce lesson).
    # A symlink entry itself has no meaningful mode; skip it entirely.
    find "$p" ! -type l -exec chmod a-w {} + 2>/dev/null || rc=1
  done < <(aegis_cp_paths "$root")
  return "$rc"
}

# aegis_cp_unlock <root> — restore owner write on the stable CP. rc 0/1 as above.
aegis_cp_unlock() {
  local root="$1" rc=0 p
  [ -n "$root" ] || return 1
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    # find -exec, not chmod -R (recurses under the hook sandbox; see header).
    # ! -type l: same symlink-pierce guard as aegis_cp_lock.
    find "$p" ! -type l -exec chmod u+w {} + 2>/dev/null || rc=1
  done < <(aegis_cp_paths "$root")
  return "$rc"
}

# aegis_cp_apply <root> <task_type> — re-establish the correct CP lock state for the
# CURRENT task_type. framework => unlock; anything else (incl. empty/unknown =>
# default-lock) => lock. Idempotent: a cheap sentinel probe ([ -w <root>/hooks ])
# decides whether a flip is needed so a no-op call avoids a redundant recursive chmod.
# rc mirrors the underlying lock/unlock (0 ok / 1 chmod failure); a no-op returns 0.
aegis_cp_apply() {
  local root="$1" task_type="$2" sentinel
  [ -n "$root" ] || return 1
  # INVARIANT: the sentinel MUST stay a member of aegis_cp_paths (it represents
  # whole-CP lock state). If "hooks" is ever removed from aegis_cp_paths, update
  # this sentinel too — otherwise the probe mis-detects state and skips chmod.
  sentinel="${root}/hooks"
  if [ "$task_type" = "framework" ]; then
    # desired = unlock. Already writable (unlocked) => no-op.
    if [ -e "$sentinel" ] && [ -w "$sentinel" ]; then
      return 0
    fi
    aegis_cp_unlock "$root"
  else
    # desired = lock (default-lock). Already non-writable (locked) => no-op.
    if [ -e "$sentinel" ] && [ ! -w "$sentinel" ]; then
      return 0
    fi
    aegis_cp_lock "$root"
  fi
}

# aegis_cp_verify <root> <task_type> — full-enumeration check that the ACTUAL
# FS state matches the EXPECTED lock state for task_type. Prints each
# mismatching path (one per line) to stdout; rc 0 = consistent, 1 = mismatch
# (or bad args). iter57 (moat promotion): the sentinel probe in aegis_cp_apply
# is a cheap 1-point read used only to SKIP a redundant chmod; verify is the
# promoted moat's fail-visible net — it walks every path. `-perm -u+w` is
# POSIX (works on BSD/macOS and GNU find alike); GNU-only `-writable` is NOT
# used. `! -type l`: a symlink's mode always reads 0777, so links would be
# permanent false positives under lock; they are also never chmod'd (above).
aegis_cp_verify() {
  local root="$1" task_type="$2" p bad rc=0
  [ -n "$root" ] || return 1
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ "$task_type" = "framework" ]; then
      bad=$(find "$p" ! -type l ! -perm -u+w 2>/dev/null)
    else
      bad=$(find "$p" ! -type l -perm -u+w 2>/dev/null)
    fi
    if [ -n "$bad" ]; then
      printf '%s\n' "$bad"
      rc=1
    fi
  done < <(aegis_cp_paths "$root")
  return "$rc"
}
