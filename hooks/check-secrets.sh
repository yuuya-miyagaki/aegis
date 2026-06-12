#!/usr/bin/env bash
# PreToolUse hook for Bash: prevents .env files from being staged or committed.
# Also warns when creating/editing .env without .gitignore protection.
#
# High-risk credential file patterns (PEM / SSH keys / credentials*.json /
# service-account*.json) live in hooks/lib/secrets-patterns.sh as the single
# source of truth (C-9). New credential types are added there, not here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load shared libraries.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"
source "${SCRIPT_DIR}/lib/secrets-patterns.sh"

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

# --- Check 0: Deny staging high-risk credential files (Form 1: command-text regex) ---
if printf '%s' "$CMD" | grep -qE "git\s+add\s+.*(${AEGIS_HIGH_RISK_RE})" 2>/dev/null; then
  emit_deny "[secrets] 高リスク認証ファイル (PEM鍵/SSH鍵/credentials.json/service-account.json 等) を git に追加しないでください。鍵が漏洩します。"
  exit 0
fi

# --- Check 1: Deny staging .env files ---
# Exclude safe variants: .env.example, .env.template, .env.sample

# Strip safe variants from command text, then check for remaining .env refs.
STRIPPED=$(printf '%s' "$CMD" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")

# Direct .env staging: git add .env, git add .env.local, git add path/.env.
# Case-insensitive: on a case-insensitive FS (macOS/Windows default) `git add .ENV`
# stages the real `.env` secret.
if printf '%s' "$STRIPPED" | grep -qiE 'git\s+add\s+.*\.env' 2>/dev/null; then
  emit_deny "[secrets] .env ファイルを git に追加しないでください。認証情報がリポジトリに漏洩します。"
  exit 0
fi

# Broad staging that would include .env or high-risk credentials: git add -A, git add .
if printf '%s' "$CMD" | grep -qE 'git\s+add\s+(-A|--all|\.)' 2>/dev/null; then
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

if printf '%s' "$CMD" | grep -qE 'git\s+commit' 2>/dev/null; then
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
