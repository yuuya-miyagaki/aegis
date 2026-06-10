#!/usr/bin/env bash
# Aegis — Modular installer
# Usage: bin/setup.sh --profile=minimal|standard|full --target=<dir> [--force]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRAMEWORK_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Argument parsing ---
PROFILE=""
TARGET="."
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --profile=*) PROFILE="${arg#*=}" ;;
    --target=*)  TARGET="${arg#*=}" ;;
    --force)     FORCE=true ;;
    -h|--help)
      echo "Usage: bin/setup.sh --profile=minimal|standard|full --target=<dir> [--force]"
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PROFILE" ]]; then
  echo "ERROR: --profile is required (minimal|standard|full)" >&2
  exit 1
fi

VALID_PROFILES="minimal standard full"
PROFILE_VALID=false
for p in $VALID_PROFILES; do
  [[ "$p" == "$PROFILE" ]] && PROFILE_VALID=true && break
done
if [[ "$PROFILE_VALID" == "false" ]]; then
  echo "ERROR: Invalid profile '$PROFILE'. Valid profiles: $VALID_PROFILES" >&2
  exit 1
fi

PROFILE_JSON="$FRAMEWORK_ROOT/templates/profiles/${PROFILE}.json"
if [[ ! -f "$PROFILE_JSON" ]]; then
  echo "ERROR: Profile file not found: $PROFILE_JSON" >&2
  exit 1
fi

if [[ ! -d "$TARGET" ]]; then
  mkdir -p "$TARGET"
fi
TARGET="$(cd "$TARGET" && pwd)"

# --- Template mapping ---
resolve_source() {
  local rel_path="$1"
  # Template overrides
  case "$rel_path" in
    "CLAUDE.md")         echo "$FRAMEWORK_ROOT/templates/CLAUDE.template.md"; return ;;
    "docs/STATUS.md")    echo "$FRAMEWORK_ROOT/templates/STATUS.template.md"; return ;;
    "docs/LEARNINGS.md") echo "$FRAMEWORK_ROOT/templates/LEARNINGS.template.md"; return ;;
    ".claude/commands/validate.md")
      echo "$FRAMEWORK_ROOT/examples/minimal-project/.claude/commands/validate.md"; return ;;
    ".claude/commands/retro.md")
      # Scaffold-safe variant: degrades gracefully when retro_report.py is absent
      # (no profile ships it). Both validate.md and retro.md are in drift's
      # MIRROR_ALLOWLIST and MUST be mapped here, or the install ships the
      # framework variant that hard-runs a missing script (audit F3, 2026-06-07).
      echo "$FRAMEWORK_ROOT/examples/minimal-project/.claude/commands/retro.md"; return ;;
    "docs/client/context.md")        echo "$FRAMEWORK_ROOT/templates/CLIENT-CONTEXT.template.md"; return ;;
    "docs/client/glossary.md")       echo "$FRAMEWORK_ROOT/templates/CLIENT-GLOSSARY.template.md"; return ;;
    "docs/client/open-questions.md") echo "$FRAMEWORK_ROOT/templates/CLIENT-OPEN-QUESTIONS.template.md"; return ;;
    "docs/translation/mapping.md")   echo "$FRAMEWORK_ROOT/templates/TRANSLATION-MAPPING.template.md"; return ;;
  esac
  # Default: copy from framework root
  echo "$FRAMEWORK_ROOT/$rel_path"
}

# --- Copy file with skip/force logic ---
copy_file() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "  SKIP (source not found): $dst"
    return
  fi
  if [[ -f "$dst" ]] && [[ "$FORCE" != "true" ]]; then
    echo "  SKIP (exists): $dst"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "  COPY: $dst"
}

# --- Parse JSON arrays (lightweight, no jq dependency) ---
parse_json_array() {
  local json_file="$1"
  local key="$2"
  # Extract array content for key, one entry per line
  python3 -c "
import json, sys
with open('$json_file') as f:
    data = json.load(f)
for item in data.get('$key', []):
    print(item)
"
}

# --- Generate settings.local.json from hooks_include ---
generate_settings() {
  local profile_json="$1"
  local target_dir="$2"
  local hooks_template="$FRAMEWORK_ROOT/templates/hooks.template.json"

  if [[ ! -f "$hooks_template" ]]; then
    echo "  SKIP: hooks.template.json not found"
    return
  fi

  # Get hooks_include list
  local hooks_include
  hooks_include=$(python3 -c "
import json, sys
with open('$profile_json') as f:
    data = json.load(f)
include = data.get('hooks_include', [])
if not include:
    sys.exit(1)
for h in include:
    print(h)
" 2>/dev/null) || return 0

  if [[ -z "$hooks_include" ]]; then
    return 0
  fi

  # Generate filtered settings.local.json
  python3 -c "
import json, sys

with open('$hooks_template') as f:
    template = json.load(f)

include = set()
with open('$profile_json') as f:
    profile = json.load(f)
include = set(profile.get('hooks_include', []))

# Check if all hooks are included (full profile)
all_hooks = set()
for event_name, entries in template.get('hooks', {}).items():
    for entry in entries:
        for hook in entry.get('hooks', []):
            cmd = hook.get('command', '')
            # Extract script name from 'bash \"\${CLAUDE_PROJECT_DIR:-.}\"/hooks/script-name.sh'
            # (strip('\"') tolerates a quote landing on the last segment).
            parts = cmd.split('/')
            if len(parts) >= 2:
                all_hooks.add(parts[-1].strip('\"'))

if include >= all_hooks:
    # Full profile: copy template as-is
    with open('$target_dir/.claude/settings.local.json', 'w') as f:
        json.dump(template, f, indent=2)
        f.write('\n')
    sys.exit(0)

# Filter: keep only hooks whose script is in hooks_include
filtered = {'hooks': {}}
for event_name, entries in template.get('hooks', {}).items():
    filtered_entries = []
    for entry in entries:
        filtered_hooks = []
        for hook in entry.get('hooks', []):
            cmd = hook.get('command', '')
            parts = cmd.split('/')
            if len(parts) >= 2:
                script = parts[-1].strip('\"')
                if script in include:
                    filtered_hooks.append(hook)
        if filtered_hooks:
            new_entry = dict(entry)
            new_entry['hooks'] = filtered_hooks
            filtered_entries.append(new_entry)
    if filtered_entries:
        filtered['hooks'][event_name] = filtered_entries

with open('$target_dir/.claude/settings.local.json', 'w') as f:
    json.dump(filtered, f, indent=2)
    f.write('\n')
"
  echo "  GENERATE: .claude/settings.local.json"
}

# --- Copy hook files based on hooks_include ---
copy_hooks() {
  local profile_json="$1"
  local target_dir="$2"

  local hooks_include
  hooks_include=$(parse_json_array "$profile_json" "hooks_include" 2>/dev/null) || return 0

  if [[ -z "$hooks_include" ]]; then
    return 0
  fi

  # Copy ALL shared hook libs when any hook is included. Every hook sources
  # lib/emit.sh (the single output source); check-destructive also sources
  # lib/patterns.sh. Copy the whole lib/ rather than selecting per-hook: the
  # libs are tiny shared helpers, and a future hook sourcing a new lib must not
  # silently ship without it. The glob's no-match case is harmless (copy_file
  # SKIPs a non-existent source). Without this, installed hooks die at
  # `source lib/emit.sh` and the moat fails open (audit F6, 2026-06-07).
  for lib in "$FRAMEWORK_ROOT"/hooks/lib/*.sh; do
    [[ -e "$lib" ]] || continue
    copy_file "$lib" "$target_dir/hooks/lib/$(basename "$lib")"
  done

  while IFS= read -r script; do
    copy_file "$FRAMEWORK_ROOT/hooks/$script" "$target_dir/hooks/$script"
  done <<< "$hooks_include"
}

# --- Ensure runtime artifacts are gitignored in the install target ---
# Idempotent: each entry is appended only when not already present verbatim.
ensure_target_gitignore() {
  local target="$1"
  local entries=".claude/evidence-log.jsonl
.claude/evidence-log.jsonl.1
.claude/.gate-snapshot
.claude/.task-event-debug.log"
  local entry
  while IFS= read -r entry; do
    [ -n "$entry" ] || continue
    if [ ! -f "$target/.gitignore" ] || ! grep -qxF "$entry" "$target/.gitignore"; then
      printf '%s\n' "$entry" >> "$target/.gitignore"
    fi
  done <<EOF_GI
$entries
EOF_GI
}

# --- Main ---
echo "Aegis Setup"
echo "  Profile: $PROFILE"
echo "  Target:  $TARGET"
echo ""

# 1. Copy required files
echo "--- Required files ---"
while IFS= read -r rel_path; do
  src=$(resolve_source "$rel_path")
  copy_file "$src" "$TARGET/$rel_path"
done < <(parse_json_array "$PROFILE_JSON" "required")

# 2. Copy recommended files
echo ""
echo "--- Recommended files ---"
recommended=$(parse_json_array "$PROFILE_JSON" "recommended" 2>/dev/null) || true
if [[ -n "$recommended" ]]; then
  while IFS= read -r rel_path; do
    src=$(resolve_source "$rel_path")
    copy_file "$src" "$TARGET/$rel_path"
  done <<< "$recommended"
else
  echo "  (none)"
fi

# 3. Copy hook files based on hooks_include
echo ""
echo "--- Hook files ---"
copy_hooks "$PROFILE_JSON" "$TARGET"
ensure_target_gitignore "$TARGET"

# 4. Generate settings.local.json
echo ""
echo "--- Settings generation ---"
mkdir -p "$TARGET/.claude"
mkdir -p "$TARGET/docs/decisions"
generate_settings "$PROFILE_JSON" "$TARGET"

echo ""
echo "Setup complete."
