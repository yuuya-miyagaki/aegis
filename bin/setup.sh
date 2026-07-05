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

# C2: accept both --flag=val and --flag val forms (CLAUDE.md prose uses the
# space form). The bare --flag arms consume the next token via an explicit
# `[ $# -ge 2 ]` guard — NOT shift's exit code, which is not a portable
# value-presence signal — so the "requires a value" error is deterministic
# across bash 3.2/4/5. Do not collapse back to =-only — the space arms are
# intentional, not dead code.
while [ $# -gt 0 ]; do
  case "$1" in
    --profile=*) PROFILE="${1#*=}"; shift ;;
    --profile)
      [ $# -ge 2 ] || { echo "ERROR: --profile requires a value" >&2; exit 1; }
      PROFILE="$2"; shift 2 ;;
    --target=*)  TARGET="${1#*=}"; shift ;;
    --target)
      [ $# -ge 2 ] || { echo "ERROR: --target requires a value" >&2; exit 1; }
      TARGET="$2"; shift 2 ;;
    --force)     FORCE=true; shift ;;
    -h|--help)
      echo "Usage: bin/setup.sh --profile=minimal|standard|full --target=<dir> [--force]"
      echo "       (--profile/--target also accept the space form: --profile full)"
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
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

# C-2 (iter54): validate the profile JSON up front, fail-closed. A broken
# profile previously made every parse_json_array call fail inside process
# substitutions / `|| return 0` guards, all of which swallow the error —
# ending with "Setup complete." rc 0 and ZERO files installed (a fail-open
# install = no moat at all). The path goes via argv (quoted heredoc body is
# not shell-expanded), so a framework path containing `'` cannot break it.
if ! python3 - "$PROFILE_JSON" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        json.load(f)
except Exception as exc:
    sys.stderr.write("ERROR: profile JSON is not valid: %s\n       parse error: %s\n"
                     % (sys.argv[1], exc))
    sys.exit(1)
PY
then
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
# C3: pass the path via argv so the quoted heredoc (injection-safe — body is not
# shell-expanded) still receives the real $FRAMEWORK_ROOT. This is the primary
# resolver; the grep below is a fallback, not the only working path.
FRAMEWORK_VERSION="$(python3 - "$FRAMEWORK_ROOT/scripts/check_framework_contract.py" <<'PY' 2>/dev/null || echo unknown
import re, pathlib, sys
src = pathlib.Path(sys.argv[1]).read_text()
m = re.search(r'FRAMEWORK_VERSION\s*=\s*"([^"]+)"', src)
print(m.group(1) if m else "unknown")
PY
)"
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
      echo "$FRAMEWORK_ROOT/templates/commands/validate.md"; return ;;
    ".claude/commands/retro.md")
      # Scaffold-safe variant: degrades gracefully when retro_report.py is absent.
      echo "$FRAMEWORK_ROOT/templates/commands/retro.md"; return ;;
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
  # C-3 (iter54): this branch is reachable with an existing $dst only under
  # --force, and copy_file handles USER-OWNED files (docs/STATUS.md, CLAUDE.md
  # — live operational state). Overwriting them with no recovery copy is data
  # loss, so apply the D3 diff-gated .bak here too: back up only when content
  # differs (identical re-install stays churn-free). Unlike copy_file_force's
  # best-effort `|| true`, a failed backup ABORTS — for user files the backup
  # is the whole point of the operation.
  if [[ -f "$dst" ]] && ! cmp -s "$src" "$dst"; then
    if ! cp "$dst" "${dst}.bak.$(date +%s)"; then
      echo "ERROR: could not back up existing $dst — aborting to avoid data loss" >&2
      exit 1
    fi
    echo "  OVERWRITE (user file, backed up): $dst"
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  INSTALLED_PATHS+=("$dst")
  echo "  COPY: $dst"
}

# K-9 (v1.6.2): force-overwrite for framework-owned files (e.g. hooks/lib/*).
# Loss of an old lib is the F6 / DIST-02 fail-open path — `SKIP (exists)`
# is wrong for these files because the upgrade target legitimately needs
# them replaced even when present. Always overwrite, never SKIP.
# D3 (iter41): diff-gated .bak. A same-version re-install where the file is
# identical is a no-op (no churn, no spurious .bak); a differing existing copy
# (stale framework file OR a user customization) is backed up before overwrite
# so it is recoverable. This is how security fixes in framework-owned assets
# reach existing installs across an upgrade.
copy_file_force() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "  SKIP (source not found): $dst"
    return
  fi
  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then
    return  # identical — nothing to do
  fi
  if [[ -f "$dst" ]]; then
    cp "$dst" "${dst}.bak.$(date +%s)" 2>/dev/null || true
  fi
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
  INSTALLED_PATHS+=("$dst")
  echo "  COPY (force): $dst"
}

# D3 (iter41): framework-owned paths are overwritten on upgrade (security fixes
# must reach existing installs); user-owned paths keep skip-if-exists so a
# user's STATUS / LEARNINGS / CLAUDE.md / settings / client docs are never
# clobbered. Classification is by TARGET rel-path (independent of template
# substitution in resolve_source).
is_framework_owned() {
  case "$1" in
    # bin/ is the installer itself; no profile ships it today, but it is
    # unambiguously framework-owned (listed so the classifier stays complete if
    # a future profile adds a bin/ entry).
    hooks/*|scripts/*|templates/*|bin/*) return 0 ;;
    .claude/skills/*|.claude/agents/*|.claude/commands/*|.claude/rules/*) return 0 ;;
    *) return 1 ;;
  esac
}

# Route a file to force-overwrite (framework-owned) or skip-if-exists (user).
copy_file_routed() {
  local rel="$1"
  local src="$2"
  local dst="$3"
  if is_framework_owned "$rel"; then
    copy_file_force "$src" "$dst"
  else
    copy_file "$src" "$dst"
  fi
}

# --- Parse JSON arrays (lightweight, no jq dependency) ---
# C-2 (iter54): file/key travel via argv into a quoted heredoc (the body is
# never shell-expanded), mirroring the FRAMEWORK_VERSION resolver above. The
# previous inline-interpolation form (`open('$json_file')`) broke into a
# python SyntaxError whenever the framework path contained a single quote —
# and every caller swallowed that failure (fail-open install).
parse_json_array() {
  local json_file="$1"
  local key="$2"
  # Extract array content for key, one entry per line
  python3 - "$json_file" "$key" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for item in data.get(sys.argv[2], []):
    print(item)
PY
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

  # Get hooks_include list. C-2 (iter54): argv-based parse + explicit rc split —
  # an EMPTY list (key absent) is the normal "profile ships no hooks" skip,
  # while a python FAILURE is a broken install step and must abort (the old
  # `2>/dev/null || return 0` folded both into a silent success).
  local hooks_include
  hooks_include=$(parse_json_array "$profile_json" "hooks_include") || {
    echo "ERROR: failed to read 'hooks_include' from profile: $profile_json" >&2
    exit 1
  }

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
  # C-2 (iter54): all three paths travel via argv into a quoted heredoc — the
  # old inline interpolation broke on a `'` in the TARGET path (python
  # SyntaxError) and aborted the install midway.
  python3 - "$hooks_template" "$profile_json" "$target_settings" <<'PY'
import json, sys, os

with open(sys.argv[1]) as f:
    template = json.load(f)

include = set()
with open(sys.argv[2]) as f:
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

# iter51: ship framework permissions.allow (the curated safe-command allow set)
# for ALL profiles. full uses out=dict(template) so it already carries it, but
# the filtered (minimal/standard) branch above keeps only 'hooks' and would drop
# permissions. Re-assert the template's allow here so every profile ships it.
if 'permissions' in template:
    # Carry the framework allow set into out for ALL profiles. Build a fresh dict
    # so we (1) never mutate the loaded template (full profile's out=dict(template)
    # is a shallow copy that shares template['permissions']), and (2) preserve any
    # other template-level permission keys (e.g. a future deny/ask) instead of
    # silently dropping them.
    perms = dict(out.get('permissions', {}))
    perms['allow'] = list(template['permissions'].get('allow', []))
    out['permissions'] = perms

# K-8: merge in user keys (everything except 'hooks') from any existing file
target = sys.argv[3]
if os.path.exists(target):
    try:
        with open(target) as f:
            existing = json.load(f)
    except Exception as e:
        # D4: do NOT silently drop the user's permissions/env when their
        # existing settings cannot be parsed (a // comment etc.). Warn loudly
        # and point at the .bak created above so they can recover.
        sys.stderr.write(
            'WARNING: existing %s could not be parsed as JSON (%s).\n'
            '         Its permissions/env were NOT carried over. A backup was '
            'saved alongside it (.bak.*); restore values manually if needed.\n'
            % (target, e)
        )
        existing = {}
    for k, v in existing.items():
        if k == 'hooks':
            continue  # framework-owned, never preserve user mutations
        if k == 'permissions' and isinstance(v, dict):
            # iter51: framework allow entries are authoritative (always present);
            # union them with the user's own allow additions (dedup, framework
            # first = stable & idempotent across re-installs). The user's deny /
            # ask / any other permission keys are preserved. To opt OUT of an
            # allowed command, the user adds it to ask/deny (a settings rule
            # overrides allow), rather than deleting the framework entry.
            merged = dict(v)  # keep user's deny / ask / other permission keys
            fw_allow = out.get('permissions', {}).get('allow', [])
            seen, union = set(), []
            for a in list(fw_allow) + list(v.get('allow', [])):
                if a not in seen:
                    seen.add(a)
                    union.append(a)
            if union:
                merged['allow'] = union
            out['permissions'] = merged
        else:
            out[k] = v   # preserve env / future keys

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
PY
  INSTALLED_PATHS+=("$target_settings")
  echo "  GENERATE: .claude/settings.local.json"
}

# --- Copy hook files based on hooks_include ---
copy_hooks() {
  local profile_json="$1"
  local target_dir="$2"

  # C-2 (iter54): rc split — empty (key absent) = normal skip; python failure
  # = abort (was `2>/dev/null || return 0`, which silently skipped ALL hooks
  # on any parse failure → installed target had no moat).
  local hooks_include
  hooks_include=$(parse_json_array "$profile_json" "hooks_include") || {
    echo "ERROR: failed to read 'hooks_include' from profile: $profile_json" >&2
    exit 1
  }

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
  # K-9 (v1.6.2): hooks/lib/*.sh / *.tsv are framework-owned. Always force-
  # overwrite, never SKIP, to prevent old libs from lingering across upgrades
  # and silently breaking new hooks (DIST-02 / F6 同型). iter55: the *.tsv glob
  # ships scripts-manifest.tsv — without it the installed allowlist is
  # fail-closed and denies every framework script. This calls copy_file_force
  # directly (rather than copy_file_routed) because the whole lib/ glob is
  # unconditionally framework-owned — is_framework_owned("hooks/lib/...") would
  # return the same routing anyway.
  for lib in "$FRAMEWORK_ROOT"/hooks/lib/*.sh "$FRAMEWORK_ROOT"/hooks/lib/*.tsv; do
    [[ -e "$lib" ]] || continue
    copy_file_force "$lib" "$target_dir/hooks/lib/$(basename "$lib")"
  done

  while IFS= read -r script; do
    copy_file_routed "hooks/$script" "$FRAMEWORK_ROOT/hooks/$script" "$target_dir/hooks/$script"
  done <<< "$hooks_include"

  # iter57: retired hooks — remove stale copies on upgrade. copy_hooks only
  # overwrites files it ships, never prunes what a profile dropped; without
  # this an old install keeps a wired-out check-control-plane.sh around (the
  # template no longer registers it, so it is dead weight, but its presence
  # misleads anyone auditing the installed moat).
  rm -f "$target_dir/hooks/check-control-plane.sh"
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
  [ -f "$target/.gitignore" ] && INSTALLED_PATHS+=("$target/.gitignore")
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

  # Stage ONLY the paths setup.sh actually wrote (recorded in INSTALLED_PATHS),
  # never whole directories — so a pre-existing user file inside a framework dir
  # (e.g. docs/user-note.md) is NOT swept into the baseline (C1 / E1). `git add`
  # (without -f) still honours the .gitignore written above, so runtime
  # artifacts (.gate-snapshot, evidence-log) are excluded automatically.
  local p rel
  local present=()
  if [ "${#INSTALLED_PATHS[@]}" -gt 0 ]; then
    for p in "${INSTALLED_PATHS[@]}"; do
      rel="${p#"$target/"}"
      [ "$rel" = "$p" ] && continue          # not under target (defensive)
      [ -e "$target/$rel" ] || continue
      # Skip paths git would ignore (e.g. a globally-ignored
      # .claude/settings.local.json). The old `git add <dir>` silently skipped
      # ignored files; an explicit add of an ignored path errors (rc 1) and would
      # lose the whole baseline, so replicate the silent-skip here.
      if git -C "$target" check-ignore -q -- "$rel" 2>/dev/null; then
        continue
      fi
      present+=("$rel")
    done
  fi
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

# Paths setup.sh actually wrote (copied or generated). The baseline commit
# stages exactly these — never whole directories — so pre-existing user files
# inside a framework dir (e.g. docs/user-note.md) are not swept in (C1 / E1).
INSTALLED_PATHS=()

# --- Main ---
echo "Aegis Setup"
echo "  Profile: $PROFILE"
echo "  Target:  $TARGET"
echo ""

# 1. Copy required files
# C-2 (iter54): capture-with-rc-check, not `< <(parse_json_array ...)` — a
# process substitution swallows the parser's exit code (K-10 already noted
# this), so a failing parse used to yield ZERO required files and still print
# "Setup complete." with rc 0. Now any parse failure aborts, fail-closed.
echo "--- Required files ---"
required=$(parse_json_array "$PROFILE_JSON" "required") || {
  echo "ERROR: failed to read 'required' from profile: $PROFILE_JSON" >&2
  exit 1
}
if [[ -n "$required" ]]; then
  while IFS= read -r rel_path; do
    src=$(resolve_source "$rel_path")
    copy_file_routed "$rel_path" "$src" "$TARGET/$rel_path"
  done <<< "$required"
else
  echo "  (none)"
fi

# 2. Copy recommended files
echo ""
echo "--- Recommended files ---"
recommended=$(parse_json_array "$PROFILE_JSON" "recommended") || {
  echo "ERROR: failed to read 'recommended' from profile: $PROFILE_JSON" >&2
  exit 1
}
if [[ -n "$recommended" ]]; then
  while IFS= read -r rel_path; do
    src=$(resolve_source "$rel_path")
    copy_file_routed "$rel_path" "$src" "$TARGET/$rel_path"
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
INSTALLED_PATHS+=("$TARGET/.claude/.aegis-install-version")

# 5. Create a one-time framework baseline commit (OBS-017)
echo ""
echo "--- Framework baseline commit ---"
create_framework_baseline "$TARGET"

echo ""
echo "Setup complete."
