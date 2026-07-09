#!/usr/bin/env bash
# Worktree fingerprint — SINGLE OWNER of the evidence-binding fingerprint.
# Binds an observed execution to the exact code it ran against (E1).
#
# Contract (consumed by evidence.sh and build-judge-card.py current_fingerprint):
#   stdout = one token: 64-hex sha256 | "oversize" | "nogit" | "error"; rc=0 on
#   all of these paths. Readers must require a 64-hex value before trusting
#   equality (token==token must never certify, e.g. nogit==nogit).
#
# Hash input = the committed non-docs/.claude tree-hash (sha256 of `git ls-tree
# -r HEAD` with docs/ and .claude/ paths removed; empty when no commits) +
# changed files vs HEAD + untracked files. The committed tree-hash is
# load-bearing and replaces the old `head:<sha>` line (R6 root 1): a code-change
# commit moves a blob sha so the fp moves — without it, two clean trees would
# share one fingerprint and a NEW untested commit would match an old recording
# (silent green). Unlike head:<sha> it does NOT move on a docs/.claude-only
# commit (those paths are excluded), so documentation and harness bookkeeping
# never invalidate a recording (mirrors build-judge-card NONCODE_PREFIXES). A
# failing git diff/ls-tree returns "error", never an empty list (an empty list
# would alias the clean-tree hash).
#
# Hardening (grill-code 2026-06-10): git runs with core.quotepath=off so
# non-ASCII names arrive raw (the quoted form made cat fail into a constant,
# leaving the fp blind to content changes — silent green). Names git still
# quotes (control chars / quotes / backslashes) and unreadable files fail
# closed to "error". Each file is framed as `f:<bytes>:<rel>\n<content>\n`
# (deleted: `d::<rel>\n`) so distinct trees can never concatenate into the
# same hash input.
#
# Source: source "$(dirname "$0")/lib/fingerprint.sh"
# Exec:   bash hooks/lib/fingerprint.sh <root>

AEGIS_FP_MAX_FILES="${AEGIS_FP_MAX_FILES:-200}"
AEGIS_FP_MAX_BYTES="${AEGIS_FP_MAX_BYTES:-10485760}"
AEGIS_FP_EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# sha256 via shasum (macOS) or sha256sum (Linux). stdin -> 64-hex on stdout.
_fp_sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
  else
    sha256sum | awk '{print $1}'
  fi
}

fingerprint_worktree() {
  local root="${1:-.}"
  if ! git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'nogit\n'
    return 0
  fi
  # Committed code state = sha256 of `git ls-tree -r HEAD` with docs/ and
  # .claude/ paths removed. `ref` (the diff baseline for working-tree changes)
  # stays HEAD, or the empty-tree constant when there are no commits.
  local ref="$AEGIS_FP_EMPTY_TREE" committed listing=""
  if git -C "$root" rev-parse --verify -q HEAD >/dev/null 2>&1; then
    ref="HEAD"
    listing=$(git -C "$root" -c core.quotepath=off ls-tree -r HEAD 2>/dev/null) \
      || { printf 'error\n'; return 0; }
  fi
  # Exclusion anchors on TAB+path-start (ls-tree line = `<mode> blob <sha>\t<path>`);
  # the trailing / means a root file literally named `docs` (no slash) is NOT
  # excluded. docs/ is a plain string (no regex metacharacter, so no escaping
  # needed); .claude/ uses the char-class [.] to force a LITERAL dot — $'\t\.claude/'
  # would let bash strip the backslash, leaving a bare dot (regex any-char) that
  # also excludes e.g. aclaude/ and hides its changes (silent green). Content is
  # never cat'd here, so a quoted path cannot mask a change: its blob sha still
  # moves the hash.
  local tab
  tab=$'\t'
  local filtered
  filtered=$(printf '%s\n' "$listing" \
               | grep -v -e "${tab}docs/" -e "${tab}[.]claude/" || true)
  committed=$(printf '%s' "$filtered" | _fp_sha256)
  local diff_files untracked_files
  diff_files=$(git -C "$root" -c core.quotepath=off diff --name-only "$ref" -- 2>/dev/null) \
    || { printf 'error\n'; return 0; }
  untracked_files=$(git -C "$root" -c core.quotepath=off ls-files --others --exclude-standard 2>/dev/null) \
    || { printf 'error\n'; return 0; }
  local files
  files=$(printf '%s\n%s\n' "$diff_files" "$untracked_files" \
           | LC_ALL=C sort -u | grep -v -e '^docs/' -e '^\.claude/' -e '^$' || true)
  local count=0 bytes=0 rel size
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    case "$rel" in
      '"'*)
        # Still quoted under quotepath=off (control chars / quotes /
        # backslashes): the on-disk path is unknowable here, so fail closed
        # instead of hashing a constant that masks content changes.
        printf 'error\n'; return 0 ;;
    esac
    count=$((count + 1))
    if [ -e "$root/$rel" ]; then
      if [ ! -f "$root/$rel" ] || [ ! -r "$root/$rel" ]; then
        printf 'error\n'; return 0
      fi
      size=$(wc -c < "$root/$rel" 2>/dev/null | tr -d '[:space:]') || size=0
      bytes=$((bytes + ${size:-0}))
    fi
  done <<EOF_COUNT
$files
EOF_COUNT
  if [ "$count" -gt "$AEGIS_FP_MAX_FILES" ] || [ "$bytes" -gt "$AEGIS_FP_MAX_BYTES" ]; then
    printf 'oversize\n'
    return 0
  fi
  {
    printf 'tree:%s\n' "$committed"
    while IFS= read -r rel; do
      [ -n "$rel" ] || continue
      if [ -f "$root/$rel" ]; then
        size=$(wc -c < "$root/$rel" 2>/dev/null | tr -d '[:space:]') || size=0
        printf 'f:%s:%s\n' "${size:-0}" "$rel"
        cat "$root/$rel" 2>/dev/null
        printf '\n'
      else
        printf 'd::%s\n' "$rel"
      fi
    done <<EOF_HASH
$files
EOF_HASH
  } | _fp_sha256
}

# Direct execution (python callers): bash fingerprint.sh <root>
if [ "${BASH_SOURCE[0]:-}" = "$0" ]; then
  fingerprint_worktree "${1:-.}"
fi
