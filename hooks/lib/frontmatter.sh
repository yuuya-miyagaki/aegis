#!/usr/bin/env bash
# Frontmatter readers — single source replacing the fragile 20-line-capped
# grep YAML section reads (P3-5, evolution review 2026-06-10). Pure bash + awk.
#
# read_frontmatter <file>
#   stdout: every line between the leading `---` pair (delimiters excluded).
#   RC 1 + empty stdout when the file is missing, has no frontmatter, or the
#   frontmatter is unterminated (output is buffered so failure never emits
#   partial lines).
#
# frontmatter_section <file> <key>
#   stdout: the top-level `<key>:` line plus its indented block — the shape
#   previously produced by the 20-line-capped grep, without the line cap.
#   RC 1 when the key is absent.
#
# raw_section <file> <key>
#   Same block extraction but scans the whole file without requiring `---`
#   delimiters. For bare frontmatter-shaped files like .claude/.gate-snapshot.
#   RC 1 when the file is missing or the key is absent.

read_frontmatter() {
  local file="$1"
  [ -f "$file" ] || return 1
  awk 'NR==1 { if ($0 != "---") exit 1; next }
       /^---[[:space:]]*$/ { found=1; exit }
       { buf = buf $0 ORS }
       END { if (found) printf "%s", buf; exit found ? 0 : 1 }' "$file"
}

_section_filter() {
  awk -v key="$1" '
    !f && index($0, key ":") == 1 { f=1; print; next }
    f && /^[^[:space:]]/ { exit }
    f { print }'
}

frontmatter_section() {
  local file="$1" key="$2" out
  out=$(read_frontmatter "$file" | _section_filter "$key")
  [ -n "$out" ] || return 1
  printf '%s\n' "$out"
}

raw_section() {
  local file="$1" key="$2" out
  [ -f "$file" ] || return 1
  out=$(_section_filter "$key" < "$file")
  [ -n "$out" ] || return 1
  printf '%s\n' "$out"
}

# frontmatter_value <file> <key>
#   stdout: top-level scalar value (surrounding double-quotes stripped).
#   Files starting with `---` are read WITHIN the frontmatter scope only
#   (first match; body lines are invisible — SF-010). `---` present but
#   unterminated -> empty (fail-closed). Bare frontmatter files
#   (.gate-snapshot, no ---) keep the whole-file read. Empty stdout + RC 0
#   when the file or key is absent (callers test -n/-z; unchanged contract).
frontmatter_value() {
  local file="$1" key="$2" src=""
  [ -f "$file" ] || return 0
  # Match read_frontmatter's terminator tolerance: a leading `--- ` (trailing
  # space) is a frontmatter-shaped file, not a bare one, so it takes the scoped
  # path and fails closed (read_frontmatter's NR==1 strict `---` mismatch -> rc1
  # -> empty) instead of leaking body lines via a whole-file read (iter66 Fix B).
  if head -n1 "$file" 2>/dev/null | grep -qE '^---[[:space:]]*$'; then
    src=$(read_frontmatter "$file") || src=""
  else
    src=$(cat "$file" 2>/dev/null) || src=""
  fi
  printf '%s\n' "$src" | grep -m1 "^${key}:" \
    | sed "s/^${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}

# gate_value <file> <gate>
#   stdout: the value of `<gate>:` under the gate_approvals section.
#   Files starting with `---`: frontmatter_section ONLY (no body fallback —
#   F-2: a body gate_approvals block must never drive gate decisions).
#   Bare files (.gate-snapshot, no ---): raw_section as before. 2-space
#   anchor prevents substring matches. Empty stdout + RC 0 when absent.
gate_value() {
  local file="$1" gate="$2" src=""
  [ -f "$file" ] || return 0
  # `--- ` (trailing space) -> scoped path (fail-closed), never the body
  # gate_approvals block via raw whole-file read (iter66 Fix B; F-2 aligned).
  if head -n1 "$file" 2>/dev/null | grep -qE '^---[[:space:]]*$'; then
    src=$(frontmatter_section "$file" gate_approvals 2>/dev/null) || src=""
  else
    src=$(raw_section "$file" gate_approvals 2>/dev/null) || src=""
  fi
  printf '%s\n' "$src" | grep -m1 "  ${gate}:" \
    | sed "s/.*${gate}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}
