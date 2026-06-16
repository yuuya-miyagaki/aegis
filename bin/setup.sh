#!/usr/bin/env bash
# Aegis — Modular installer
# Usage: bin/setup.sh --profile=minimal|standard|full --target=<dir> [--force]
set -euo pipefail

# K-10 (v1.6.2 / DIST-03): prereq checks. Without these, a missing python3
# silently produces zero files because the process-substitution loop
# `while ... < <(parse_json_array ...)` does not propagate pipefail —
# setup ends with "Setup complete." and EXIT=0 / 0 files installed.
_aegis_require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd" >&2
    echo "       Install $cmd and re-run bin/setup.sh." >&2
    exit 1
  fi
  # Detect a stub that exists in PATH but exits non-zero (test fixture for
  # DIST-03 uses an `exit 127` stub to simulate a broken python3).
  if [[ "$cmd" == "python3" ]]; then
    if ! "$cmd" -c 'print("ok")' >/dev/null 2>&1; then
      echo "ERROR: python3 is on PATH but not functional (interpreter test failed)" >&2
      exit 1
    fi
  fi
}
_aegis_require_cmd bash
_aegis_require_cmd python3

# bash 4+ is the modern baseline (associative arrays, ${var,,}, etc.). aegis
# itself uses bash 3.2-safe constructs (macOS default), so we WARN rather
# than abort, but the warning still surfaces in setup output.
if (( BASH_VERSINFO[0] < 4 )); then
  echo "WARNING: bash 4+ recommended (current: ${BASH_VERSION}). aegis works on bash 3.2 but features depending on associative arrays may degrade." >&2
fi

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

# DIST-12 前倒し (v1.6.2): framework_root 自身への install を禁止する。
# `--target=<framework_root>` のうっかり指定は --force と組み合わさると
# framework の設定を上書きしうるため、入口で abort。
TARGET_REAL="$(cd "$TARGET" && pwd -P)"
FRAMEWORK_ROOT_REAL="$(cd "$FRAMEWORK_ROOT" && pwd -P)"
if [[ "$TARGET_REAL" == "$FRAMEWORK_ROOT_REAL" ]]; then
  echo "ERROR: cannot install into the framework repo itself ($FRAMEWORK_ROOT_REAL)" >&2
  echo "       Use --target=<your-project-dir>" >&2
  exit 1
fi

# K-11 (v1.6.2): framework_version stamp source.
# Read FRAMEWORK_VERSION from scripts/check_framework_contract.py (single
# source of truth — also referenced by status_doctor.py / drift checker).
FRAMEWORK_VERSION="$(python3 - <<'PY' 2>/dev/null || echo unknown
import re, pathlib
src = pathlib.Path("$FRAMEWORK_ROOT/scripts/check_framework_contract.py").read_text()
m = re.search(r'FRAMEWORK_VERSION\s*=\s*"([^"]+)"', src)
print(m.group(1) if m else "unknown")
PY
)"
# Python heredoc cannot interpolate the $FRAMEWORK_ROOT — fall back to a
# bash-level grep when the heredoc returns "unknown".
if [[ "$FRAMEWORK_VERSION" == "unknown" ]] || [[ -z "$FRAMEWORK_VERSION" ]]; then
  FRAMEWORK_VERSION="$(grep -E '^FRAMEWORK_VERSION\s*=' "$FRAMEWORK_ROOT/scripts/check_framework_contract.py" | sed -E 's/.*"([^"]+)".*/\1/' | head -1)"
fi
[[ -z "$FRAMEWORK_VERSION" ]] && FRAMEWORK_VERSION="unknown"

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

# K-9 (v1.6.2): force-overwrite for framework-owned files (e.g. hooks/lib/*).
# Loss of an old lib is the F6 / DIST-02 fail-open path — `SKIP (exists)`
# is wrong for these files because the upgrade target legitimately needs
# them replaced even when present. Always overwrite, never SKIP.
copy_file_force() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "  SKIP (source not found): $dst"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
  echo "  COPY (force): $dst"
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
  local target_settings="$target_dir/.claude/settings.local.json"

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

  # K-8 (v1.6.2): backup the existing settings before overwriting. The
  # backup is the user-visible signal of the behavioral change announced
  # in CHANGELOG (settings.local.json は再 install 時に .bak.<ts> で退避).
  if [[ -f "$target_settings" ]]; then
    cp "$target_settings" "${target_settings}.bak.$(date +%s)" 2>/dev/null || true
  fi

  # K-8 (v1.6.2) + grill 致命 4: generate filtered settings AND merge in
  # all top-level keys from the existing file EXCEPT `hooks` (which is
  # framework-owned and always overwritten). permissions / env / future
  # Claude Code keys are preserved.
  python3 -c "
import json, sys, os

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
            parts = cmd.split('/')
            if len(parts) >= 2:
                all_hooks.add(parts[-1].strip('\"'))

if include >= all_hooks:
    out = dict(template)  # full profile: use template as base
else:
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
    out = filtered

# K-8: merge in user keys (everything except 'hooks') from any existing file
target = '$target_settings'
if os.path.exists(target):
    try:
        with open(target) as f:
            existing = json.load(f)
    except Exception:
        existing = {}
    for k, v in existing.items():
        if k == 'hooks':
            continue  # framework-owned, never preserve user mutations
        out[k] = v   # preserve permissions / env / future keys

# P2-a (v1.7.0): minimal/standard default the phase-HINT nudge OFF via settings
# env (settings env propagates to hook process env). full leaves it unset = on.
# Key-level setdefault: only ADD the default when absent — a user's explicit
# env.AEGIS_NUDGE (on or off) survives re-install (K-8 preserve-user-keys).
profile_name = profile.get('name', '')
if profile_name in ('minimal', 'standard'):
    out.setdefault('env', {}).setdefault('AEGIS_NUDGE', 'off')

with open(target, 'w') as f:
    json.dump(out, f, indent=2)
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
  # K-9 (v1.6.2): hooks/lib/*.sh are framework-owned. Always force-overwrite,
  # never SKIP, to prevent old libs from lingering across upgrades and
  # silently breaking new hooks (DIST-02 / F6 同型).
  for lib in "$FRAMEWORK_ROOT"/hooks/lib/*.sh; do
    [[ -e "$lib" ]] || continue
    copy_file_force "$lib" "$target_dir/hooks/lib/$(basename "$lib")"
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

# --- Create a one-time framework baseline commit (OBS-017) ---
# Without an initial commit, the first dogfood review gate treats the freshly
# installed framework files as new uncommitted code and emits a framework-origin
# stub 🔴. Best-effort: every git failure degrades to a skip (never aborts the
# install). Acts ONLY on a repo with zero commits (fresh dir or empty repo); a
# repo that already has history is left untouched. Staging is scoped to the
# installed framework paths — never `git add -A`/`-f` — so unrelated files in
# the target stay unstaged.
create_framework_baseline() {
  local target="$1"

  if ! command -v git >/dev/null 2>&1; then
    echo "  (skipped: git not found)"
    return 0
  fi

  # Initialise a repo only when the target is not already under git.
  if ! git -C "$target" rev-parse --git-dir >/dev/null 2>&1; then
    if ! git -C "$target" init -q >/dev/null 2>&1; then
      echo "  (skipped: git init failed)"
      return 0
    fi
  fi

  # No-op when the repo already has any commit (existing project history).
  if git -C "$target" rev-parse --verify -q HEAD >/dev/null 2>&1; then
    echo "  (skipped: repo already has commits)"
    return 0
  fi

  # Stage ONLY the framework artifacts that were actually installed. `git add`
  # (without -f) honours the .gitignore written above, so runtime artifacts
  # (.gate-snapshot, evidence-log) are excluded automatically.
  local candidate
  local present=()
  for candidate in hooks scripts templates .claude CLAUDE.md docs; do
    [ -e "$target/$candidate" ] && present+=("$candidate")
  done
  if [ ${#present[@]} -eq 0 ]; then
    echo "  (skipped: no framework files to commit)"
    return 0
  fi
  if ! git -C "$target" add -- "${present[@]}" >/dev/null 2>&1; then
    echo "  (skipped: git add failed)"
    return 0
  fi

  # Use the user's configured identity when present; otherwise fall back to an
  # aegis identity so a fresh repo without any git config still commits.
  local ident=()
  if ! git -C "$target" config user.email >/dev/null 2>&1 \
     || ! git -C "$target" config user.name >/dev/null 2>&1; then
    ident=(-c user.name="Aegis Setup" -c user.email="setup@aegis.local")
  fi
  if git -C "$target" ${ident[@]+"${ident[@]}"} commit -q \
       -m "chore: Aegis framework baseline (installed by setup.sh)" \
       >/dev/null 2>&1; then
    echo "  Created baseline commit."
  else
    echo "  (skipped: git commit failed)"
  fi
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

# K-11 (v1.6.2): write the framework version stamp so status_doctor /
# check_framework_contract can detect installs that drift behind the
# framework. The stamp is updated every successful run (forward-only:
# user may downgrade by re-running with an older setup.sh).
mkdir -p "$TARGET/.claude"
printf '%s\n' "$FRAMEWORK_VERSION" > "$TARGET/.claude/.aegis-install-version"

# 5. Create a one-time framework baseline commit (OBS-017)
echo ""
echo "--- Framework baseline commit ---"
create_framework_baseline "$TARGET"

echo ""
echo "Setup complete."
