#!/usr/bin/env bash
# Frontmatter readers — single source replacing fragile `grep -A20` YAML
# section reads (P3-5, evolution review 2026-06-10). Pure bash + awk.
#
# read_frontmatter <file>
#   stdout: every line between the leading `---` pair (delimiters excluded).
#   RC 1 + empty stdout when the file is missing, has no frontmatter, or the
#   frontmatter is unterminated (output is buffered so failure never emits
#   partial lines).
#
# frontmatter_section <file> <key>
#   stdout: the top-level `<key>:` line plus its indented block — the shape
#   previously produced by `grep -A20 "^<key>:"`, without the 20-line cap.
#   RC 1 when the key is absent.

read_frontmatter() {
  local file="$1"
  [ -f "$file" ] || return 1
  awk 'NR==1 { if ($0 != "---") exit 1; next }
       /^---[[:space:]]*$/ { found=1; exit }
       { buf = buf $0 ORS }
       END { if (found) printf "%s", buf; exit found ? 0 : 1 }' "$file"
}

frontmatter_section() {
  local file="$1" key="$2" out
  out=$(read_frontmatter "$file" | awk -v key="$key" '
    !f && index($0, key ":") == 1 { f=1; print; next }
    f && /^[^[:space:]]/ { exit }
    f { print }')
  [ -n "$out" ] || return 1
  printf '%s\n' "$out"
}
