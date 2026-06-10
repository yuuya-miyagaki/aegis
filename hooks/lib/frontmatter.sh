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
