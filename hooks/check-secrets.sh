#!/usr/bin/env bash
# PreToolUse hook for Bash: prevents .env files from being staged or committed.
# Also warns when creating/editing .env without .gitignore protection.
#
# High-risk credential file patterns (PEM / SSH keys / credentials*.json /
# service-account*.json) live in hooks/lib/secrets-patterns.sh as the single
# source of truth (C-9). New credential types are added there, not here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# AEGIS_SAFETY_FALLBACK_BEGIN
if [ ! -r "${SCRIPT_DIR}/lib/safety.sh" ]; then
  printf '[aegis-safety] fail-closed: safety.sh not readable\n' >&2
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}}'
  exit 0
fi
set +e
source "${SCRIPT_DIR}/lib/safety.sh" 2>/dev/null
_aegis_safety_rc=$?
set -e
if [ "$_aegis_safety_rc" -ne 0 ]; then
  printf '[aegis-safety] fail-closed: safety.sh source failed\n' >&2
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}}'
  exit 0
fi
# AEGIS_SAFETY_FALLBACK_END

# Load shared libraries (fail-closed via safety lib on source failure).
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/secrets-patterns.sh"

# Read stdin.
INPUT=$(cat)

# Extract command.
CMD=$(extract_command "$INPUT")

# If no command extracted, allow.
if [ -z "$CMD" ]; then
  emit_allow
  exit 0
fi

# Safe .env variants that are NOT secrets (may be committed).
SAFE_ENV_SUFFIXES='\.env\.(example|template|sample)'

# S-3 (v1.6.1): extend the "git staging" detection to cover all command-line
# variants that the baseline `git\s+add\s+` regex missed:
#   - git --git-dir=.git --work-tree=. add .env     (--git-dir / --work-tree flags)
#   - git -C /tmp/repo add .env                     (-C path)
#   - git -c safe.directory=foo add .env            (-c key=value)
#   - git stage .env                                (add alias)
#   - git update-index --add .env                   (plumbing path)
# GIT_PRE_OPTS matches any series of git options (long/short with optional value).
# OUT OF SCOPE (v1.6.1 受容済み・v161-security.md): git stash push .env
# (legitimate use cases dominate), git apply --index, eval/alias forms.
GIT_PRE_OPTS='(-{1,2}[A-Za-z][-A-Za-z0-9]*(=[^[:space:]]+|[[:space:]]+[^[:space:]-][^[:space:]]*)?[[:space:]]+)*'
GIT_STAGE_VERB='(add|stage|update-index)'

# --- Check 0: Deny staging high-risk credential files (Form 1: command-text regex) ---
if printf '%s' "$CMD" | grep -qE "git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}([[:space:]]+(--[A-Za-z][-A-Za-z0-9]*[[:space:]]+)*)?.*(${AEGIS_HIGH_RISK_RE})" 2>/dev/null; then
  emit_deny "[secrets] 高リスク認証ファイル (PEM鍵/SSH鍵/credentials.json/service-account.json 等) を git に追加しないでください。鍵が漏洩します。"
  exit 0
fi

# --- Check 1: Deny staging .env files ---
# Exclude safe variants: .env.example, .env.template, .env.sample

# Strip safe variants from command text, then check for remaining .env refs.
STRIPPED=$(printf '%s' "$CMD" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")

# Direct .env staging across all variants. Case-insensitive: on case-insensitive
# FS (macOS/Windows default) `git add .ENV` stages the real `.env` secret.
if printf '%s' "$STRIPPED" | grep -qiE "git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}([[:space:]]+(--[A-Za-z][-A-Za-z0-9]*[[:space:]]+)*)?.*\.env" 2>/dev/null; then
  emit_deny "[secrets] .env ファイルを git に追加しないでください。認証情報がリポジトリに漏洩します。"
  exit 0
fi

# Broad staging that would include .env or high-risk credentials: git add -A, git add .
# Only `add` (not stage / update-index) has the -A/--all/. broad-stage spellings.
if printf '%s' "$CMD" | grep -qE "git[[:space:]]+${GIT_PRE_OPTS}add[[:space:]]+(-A|--all|\.)" 2>/dev/null; then
  ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

  # v0.13.0 Phase 0b NO-GO fix: broad staging must also catch high-risk credentials
  # (these have no "safe variant", so any presence in the repo is risky).
  # Form 3 (find -name globs) + Form 2 (basename case glob): broad capture by
  # find, then tight match by case.
  FIND_ARGS=()
  for _name in "${AEGIS_HIGH_RISK_FIND_NAMES[@]}"; do
    FIND_ARGS+=( -name "$_name" -o )
  done
  # Trim the trailing -o.
  unset 'FIND_ARGS[${#FIND_ARGS[@]}-1]'

  HAS_HIGH_RISK=false
  while IFS= read -r f; do
    BN=$(basename "$f")
    # Iterate AEGIS_HIGH_RISK_CASE_GLOB_ARR — `case "$x" in $JOINED)` does NOT
    # honor `|` as alternation after variable expansion (the whole expanded
    # string becomes ONE pattern). Per-entry [[ == glob ]] preserves the
    # narrow-match intent of the original literal case stanza.
    for _glob in "${AEGIS_HIGH_RISK_CASE_GLOB_ARR[@]}"; do
      # shellcheck disable=SC2053
      # Intentional unquoted RHS — _glob is a glob pattern.
      if [[ $BN == $_glob ]]; then
        HAS_HIGH_RISK=true; break 2
      fi
    done
  done < <(find "$ROOT" \
    \( "${FIND_ARGS[@]}" \) \
    -not -path '*/node_modules/*' \
    -not -path '*/.git/*' \
    -not -path '*/vendor/*' \
    -not -path '*/.venv/*' \
    2>/dev/null || true)
  if [ "$HAS_HIGH_RISK" = true ]; then
    emit_deny "[secrets] git add -A / git add . は repository 内の高リスク認証ファイル (PEM鍵/SSH鍵/credentials.json/service-account.json) を含む可能性があります。個別のファイル名を指定し、高リスクファイルは事前に削除/移動してください。"
    exit 0
  fi

  # Check if actual secret .env files exist anywhere in the repo (excluding safe variants).
  # Recursive search handles monorepo layouts (e.g., services/api/.env).
  HAS_SECRET_ENV=false
  while IFS= read -r f; do
    case "$(basename "$f")" in
      .env.example|.env.template|.env.sample) ;;
      *) HAS_SECRET_ENV=true; break ;;
    esac
  done < <(find "$ROOT" -name '.env*' \
    -not -path '*/node_modules/*' \
    -not -path '*/.git/*' \
    -not -path '*/vendor/*' \
    -not -path '*/.venv/*' \
    2>/dev/null || true)
  if [ "$HAS_SECRET_ENV" = true ]; then
    emit_deny "[secrets] git add -A / git add . は .env を含む可能性があります。個別のファイル名を指定して git add してください。"
    exit 0
  fi
fi

# --- Check 2: Deny commit when .env is staged ---

# grill-code A-S4 (v1.6.1): commit verb also accepts the same GIT_PRE_OPTS
# prefix as the staging verbs above. Without this, `git --git-dir=.git
# --work-tree=. commit` and `git -C dir commit` skipped the staged-diff check.
if printf '%s' "$CMD" | grep -qE "git[[:space:]]+${GIT_PRE_OPTS}commit" 2>/dev/null; then
  # v0.13.0 Phase 0b NO-GO fix: high-risk credential files in staged diff (Form 4).
  if git diff --cached --name-only 2>/dev/null | grep -E "${AEGIS_HIGH_RISK_STAGED_RE}" | grep -q . 2>/dev/null; then
    emit_deny "[secrets] 高リスク認証ファイル (PEM鍵/SSH鍵/credentials.json/service-account.json) がステージングされています。git reset HEAD でファイル名を指定して除外してからコミットしてください。"
    exit 0
  fi
  # Check if any secret .env file is in the staging area (exclude safe variants)
  if git diff --cached --name-only 2>/dev/null | grep -E '\.env' | grep -vE "${SAFE_ENV_SUFFIXES}$" | grep -q . 2>/dev/null; then
    emit_deny "[secrets] .env ファイルがステージングされています。git reset HEAD .env で除外してからコミットしてください。"
    exit 0
  fi
fi

# grill-code A-Crit-4 (v1.6.1) + K-3 (v1.6.2):
# `F=.env; git add $F`, `F=.env; git add "${F}"`, `F=.env; git add '${F}'`
# all build the filename via variable expansion, so the literal-`.env` regex
# above misses it. Mirror the C-1 var-built-write heuristic: if the command
# has BOTH a variable assignment AND uses `git <stage> [QUOTE]$VAR[QUOTE]`,
# ASK. Same logic applies to high-risk credentials staged via var-built names.
# K-3 extends the v1.6.1 regex to accept optional `"` / `'` immediately
# before `$` (REDTEAM-03: `git add "${F}"` had silently passed because the
# leading quote broke the [^.[:space:]]+ chain).
if printf '%s' "$CMD" | grep -qE '(^|[;&|][[:space:]]*|[[:space:]])[A-Za-z_][A-Za-z0-9_]*=' 2>/dev/null && \
   printf '%s' "$CMD" | grep -qE "git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}[[:space:]]+([\"'\\\\]?[^.[:space:]]+[[:space:]]+)*[\"'\\\\]?\\\$\\{?[A-Za-z_][A-Za-z0-9_]*" 2>/dev/null; then
  emit_ask "[secrets] git のステージング先パスが変数 (\$VAR) で組み立てられています — .env や認証ファイルを意図せず追加しないか確認してください。"
  exit 0
fi

# K-4 (v1.6.2): cmdsub / backtick で git や引数を組み立てる経路の bypass。
# REDTEAM-04: `$(echo git) add .env` / `` `echo git` add .env `` は
# git[[:space:]]+... 前提の全 regex を完全に迂回する。
# 静的に解決不能（コマンド置換の出力次第）なので、cmdsub/backtick が含まれ、
# かつ word-boundary 付きの `.env` か高リスク認証ファイル参照があれば ASK。
# safe variants (.env.example/.template/.sample) は事前 strip して
# false-positive を抑止（grill 要検討 2）。
K4_STRIPPED=$(printf '%s' "$CMD" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")
if printf '%s' "$CMD" | grep -qE '\$\(|`' 2>/dev/null && \
   { printf '%s' "$K4_STRIPPED" | grep -qE "(^|[^A-Za-z0-9_])\\.env([^A-Za-z0-9_]|$)" 2>/dev/null || \
     printf '%s' "$K4_STRIPPED" | grep -qE "${AEGIS_HIGH_RISK_RE}" 2>/dev/null; }; then
  emit_ask "[secrets] コマンドが \$(...) / \`...\` で構築されており、.env や認証ファイルを参照しています — 意図しないステージング/書込みでないか確認してください。"
  exit 0
fi

# --- Check 3: Warn when .gitignore lacks .env protection ---
# This triggers only for commands that create or write secret .env files via Bash
# (e.g., echo "KEY=val" > .env, cp template .env)
# Safe variants (.env.example, .env.template, .env.sample) are excluded.

STRIPPED_WRITE=$(printf '%s' "$CMD" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")
if printf '%s' "$STRIPPED_WRITE" | grep -qE '>\s*\.env|>\s*\S+/\.env|cp\s+.*\.env' 2>/dev/null; then
  ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  if [ -f "${ROOT}/.gitignore" ]; then
    if ! grep -qE '^\s*\.env' "${ROOT}/.gitignore" 2>/dev/null; then
      emit_ask "[secrets] .gitignore に .env が含まれていません。先に .gitignore に .env を追加することを推奨します。"
      exit 0
    fi
  else
    emit_ask "[secrets] .gitignore が見つかりません。.env をリポジトリに含めないよう .gitignore を先に作成してください。"
    exit 0
  fi
fi

# No issue found — allow.
emit_allow
exit 0
