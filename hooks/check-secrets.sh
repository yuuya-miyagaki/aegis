#!/usr/bin/env bash
# PreToolUse hook for Bash: prevents .env files from being staged or committed.
# Also warns when creating/editing .env without .gitignore protection.
#
# High-risk credential file patterns (PEM / SSH keys / credentials*.json /
# service-account*.json) live in hooks/lib/secrets-patterns.sh as the single
# source of truth (C-9). New credential types are added there, not here.
#
# SCOPE (D2): this is a secret-FILE-NAME gate, not a content scanner. It blocks
# known credential *file names* (.env, id_*, *.pem, credentials*.json,
# service-account*.json) from being staged/committed. It does NOT inspect file
# CONTENT — a secret VALUE written into an arbitrarily-named file (e.g.
# `echo "AKIA..." > config.yaml`) is out of scope by design.
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
# iter75 SF-017: aegis_dequote_normalize（quote/backslash/${IFS} 畳み込み）を提供。
# OPTIONAL（fail-open）: 正規化 re-check は defense-in-depth ASK 補強であり、生形の
# deny は上流で確定済み。patterns.sh 欠落時はこの補強のみ無効化し、他の deny/allow
# 判定は不変（require_lib=fail-closed にすると欠落 install が全 deny に退行するため不採）。
if [ -r "${SCRIPT_DIR}/lib/patterns.sh" ]; then
  set +e; source "${SCRIPT_DIR}/lib/patterns.sh" 2>/dev/null; set -e
fi

# Read stdin.
INPUT=$(cat)

# iter73 (locale/byte hardening): force BYTE-WISE (C locale) matching for the
# ENTIRE hook — extract_command's grep/sed fast-path AND every tr/grep below
# (command text, and the git-staged-diff pipe). Under a UTF-8 locale, an invalid
# UTF-8 byte in the command makes grep silently emit NOTHING (extract_command
# then returns empty → the [ -z "$CMD" ] fallback only ASKs, downgrading a real
# DENY) and makes `tr` abort with "Illegal byte sequence" (set -euo pipefail then
# kills the hook rc=1, no decision — fail-open). Set C locale BEFORE extraction
# so the grep fast-path is byte-wise too. Byte-wise is correct for every runnable
# command: the patterns are ASCII literals plus `[[:space:]]` token separators
# (`git[[:space:]]+…add`), and under C those classes match ASCII whitespace only.
# Since bash word-splits ONLY on ASCII IFS whitespace, a real staging command
# always uses ASCII separators — so no runnable command is missed. (A non-ASCII
# separator, e.g. `git<NBSP>add .env`, makes `git<NBSP>add` a single non-existent
# token → "command not found"; not matching it loses nothing. Accepted residual,
# pinned in tests/test_hook_locale_byte.py; see docs/security-followups.md SF-016.)
# The C locale does NOT corrupt
# extract_command's python3 path: CPython auto-enables UTF-8 Mode under a C/POSIX
# locale (PEP 540), so stdin/stdout stay UTF-8 and valid multibyte text (Japanese
# paths etc.) is preserved byte-for-byte (verified: identical extraction bytes
# under C vs UTF-8). Mirrors hooks/lib/marker.sh (iter72 F-CRIT-1).
export LC_ALL=C LC_CTYPE=C LANG=C

# Extract command.
CMD=$(extract_command "$INPUT")

# If no command extracted, allow — UNLESS the raw payload still references a
# secret/credential file (defense-in-depth fail-closed fallback for truncated JSON).
# C-1 (iter54): credential-name matching is case-folded UNCONDITIONALLY (no FS
# probe): on a case-insensitive FS `key.PEM` IS the real key file, and on a
# case-sensitive FS an uppercase-named key is still a real key file — folding
# is a pure widening of the deny (never a correctness risk). Mechanism: the
# TEXT is lowercased (tr) and matched against the existing lowercase patterns,
# NOT `grep -i` — bracket expressions like [^.a-z] interact ambiguously with -i
# across grep implementations. The fold is applied SYMMETRICALLY: every folded
# positive pattern has its safe-variant exclusion / strip folded too, so
# `.ENV.EXAMPLE` does not become a false deny.
if [ -z "$CMD" ]; then
  RAW_LC=$(printf '%s' "$INPUT" | tr '[:upper:]' '[:lower:]')
  # Credential file patterns come from the lib (C-9 single owner); .env is local.
  if printf '%s' "$RAW_LC" | grep -qE "\.env([^.a-z]|\$)|${AEGIS_HIGH_RISK_RE}" 2>/dev/null \
     && ! printf '%s' "$RAW_LC" | grep -qE '\.env\.(example|template|sample)' 2>/dev/null; then
    emit_ask "[careful] コマンドの解析に失敗しましたが、入力が秘密情報/認証ファイルを参照しています。意図を確認してください。"
  else
    emit_allow
  fi
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

# G2 (iter42): honor `-C <path>` / `--git-dir=<path>` so `git -C repo commit`
# scans the TARGET repo's staged diff, not the hook CWD (which scanned nothing
# and let a staged .env through). git options precede the subcommand, so scope
# extraction to the pre-`commit` prefix — otherwise a `-C` inside the commit
# message (git -C r commit -m "fix -C") is grabbed by the greedy match.
_aegis_git_dir_args() {
  # Strip from the ` commit` SUBCOMMAND (space-delimited) onward — NOT a bare
  # "commit" substring, which could appear inside the -C path (e.g. a repo at
  # /home/u/my-commit-tool) and truncate the path mid-way.
  local cmd="${1%% commit*}"
  local flag="" path=""
  # --git-dir=PATH  and  --git-dir PATH  (GIT_PRE_OPTS already admits both forms).
  path=$(printf '%s' "$cmd" | sed -nE 's/.*--git-dir=([^[:space:]]+).*/\1/p' | head -1)
  [ -n "$path" ] && flag="--git-dir"
  if [ -z "$path" ]; then
    path=$(printf '%s' "$cmd" | sed -nE 's/.*--git-dir[[:space:]]+([^[:space:]]+).*/\1/p' | head -1)
    [ -n "$path" ] && flag="--git-dir"
  fi
  if [ -z "$path" ]; then
    path=$(printf '%s' "$cmd" | sed -nE 's/.*[[:space:]]-C[[:space:]]+([^[:space:]]+).*/\1/p' | head -1)
    [ -n "$path" ] && flag="-C"
  fi
  [ -z "$path" ] && return
  # Strip one layer of surrounding matched quotes: git -C "/repo" → /repo. A
  # quoted path CONTAINING spaces is not fully recovered (the unquoted capture
  # stops at the space) — accepted known limitation, identical to the pre-G2
  # CWD-scan baseline; rare and out of the accident-prevention sweet spot.
  case "$path" in
    \"*\") path="${path#\"}"; path="${path%\"}" ;;
    \'*\') path="${path#\'}"; path="${path%\'}" ;;
  esac
  printf -- '%s\n%s\n' "$flag" "$path"
}

# C-1 (iter54): lowercased command text for credential-NAME matching (see the
# fold rationale at the fallback above). The git verb/option regexes use
# [A-Za-z] classes, so they match unchanged on lowercased text.
CMD_LC=$(printf '%s' "$CMD" | tr '[:upper:]' '[:lower:]')

# iter75-ff (SF-017 F1): NORM / NORM_LC を前倒し計算（broad-stage :196 / commit :270
# の二経路トリガで使うため、それらより前で用意する）。aegis_dequote_normalize
# （quote/backslash/${IFS} 畳み込み）は OPTIONAL（patterns.sh 欠落時は未定義）ので
# ガードし、欠落時は NORM="" として NORM 経路を無効化（生の deny/allow は不変）。
# 末尾の明示 .env 正規化 re-check（:346-）は依然この NORM を使う。
NORM=""; NORM_LC=""
if command -v aegis_dequote_normalize >/dev/null 2>&1; then
  NORM=$(aegis_dequote_normalize "$CMD")
  NORM_LC=$(printf '%s' "$NORM" | tr '[:upper:]' '[:lower:]')
fi

# iter75 SF-017: staging 検出 regex を単一ソース化（raw deny と正規化 ask が同一検出器）。
_STAGE_HIGHRISK_RE="git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}([[:space:]]+(--[A-Za-z][-A-Za-z0-9]*[[:space:]]+)*)?.*(${AEGIS_HIGH_RISK_RE})"
_STAGE_ENV_RE="git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}([[:space:]]+(--[A-Za-z][-A-Za-z0-9]*[[:space:]]+)*)?.*\.env"
# iter75-ff (SF-017 F1): broad-stage / commit のトリガも単一ソース化。生 CMD の
# deny 経路と正規化 NORM の ask 経路が同一トリガを共有する（NORM でも broad/commit
# を再検出して難読化バイパスを塞ぐ・盲検2次 F1）。
# iter77 SF-021: verb を (add|stage) に拡張。`git stage` は `git add` の完全 alias で
# 同じ -A/--all/. broad-stage 綴りを取る（`git stage -A` == `git add -A`）。
# GIT_STAGE_VERB（:111・(add|stage|update-index)）は流用しない: update-index は
# -A/--all/. の broad 綴りを持たない別コマンド（plumbing）で、混ぜると broad regex が
# 意味を成さない綴りを許容してしまうため、broad 検出は add|stage のみを対象にする。
_STAGE_BROAD_RE="git[[:space:]]+${GIT_PRE_OPTS}(add|stage)[[:space:]]+(-a|--all|\.\.?/?($|[^[:alnum:]._/-])|\.[^[:space:]]*[*?[])"
_STAGE_COMMIT_RE="git[[:space:]]+${GIT_PRE_OPTS}commit"

# iter75-ff (SF-017 F1): broad-stage スキャンを関数抽出（挙動保存リファクタ）。
# repo に高リスク cred / secret .env が存在するかを走査し、検出種別を stdout に返す:
#   highrisk … 高リスク cred（PEM/SSH/credentials/service-account）検出
#   env      … secret .env 検出（safe variant 除外後）
#   （空）    … いずれも無し
# highrisk を env より優先（従来の raw 経路が high-risk を先に deny していた順序を保存）。
# ROOT 計算・find・safe-variant 除外の既存ロジックを完全保存。
_aegis_broad_secret_kind() {
  local ROOT; ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

  # v0.13.0 Phase 0b NO-GO fix: broad staging must also catch high-risk credentials
  # (these have no "safe variant", so any presence in the repo is risky).
  # Form 3 (find -name globs) + Form 2 (basename case glob): broad capture by
  # find, then tight match by case.
  # C-1 (iter54): -iname (was -name) — a KEY.PEM / ID_RSA in the repo is a real
  # credential file on ANY filesystem; the over-fetch step folds case.
  local FIND_ARGS=()
  local _name
  for _name in "${AEGIS_HIGH_RISK_FIND_NAMES[@]}"; do
    FIND_ARGS+=( -iname "$_name" -o )
  done
  # Trim the trailing -o.
  unset 'FIND_ARGS[${#FIND_ARGS[@]}-1]'

  local HAS_HIGH_RISK=false f BN _glob
  while IFS= read -r f; do
    # C-1: fold the basename before the tight gate — the form-2 globs are
    # lowercase and [[ == ]] is case-sensitive.
    BN=$(basename "$f" | tr '[:upper:]' '[:lower:]')
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
    printf 'highrisk\n'
    return
  fi

  # Check if actual secret .env files exist anywhere in the repo (excluding safe variants).
  # Recursive search handles monorepo layouts (e.g., services/api/.env).
  local HAS_SECRET_ENV=false
  while IFS= read -r f; do
    # C-1: -iname over-fetches case variants; the folded basename keeps the
    # safe-variant exemption symmetric (.ENV.EXAMPLE is exempt like .env.example).
    case "$(basename "$f" | tr '[:upper:]' '[:lower:]')" in
      .env.example|.env.template|.env.sample) ;;
      *) HAS_SECRET_ENV=true; break ;;
    esac
  done < <(find "$ROOT" -iname '.env*' \
    -not -path '*/node_modules/*' \
    -not -path '*/.git/*' \
    -not -path '*/vendor/*' \
    -not -path '*/.venv/*' \
    2>/dev/null || true)
  if [ "$HAS_SECRET_ENV" = true ]; then
    printf 'env\n'
    return
  fi
}

# iter75-ff (SF-017 F1): commit-time staged-diff スキャンを関数抽出（挙動保存）。
# 引数: GIT_DIR_ARGS 相当（-C/--git-dir 解決済みの git オプション列）。
# highrisk / env / （空）を stdout に返す。既存 raw 経路と同じ順序・除外規則。
_aegis_staged_secret_kind() {
  # v0.13.0 Phase 0b NO-GO fix: high-risk credential files in staged diff (Form 4).
  # C-1 (iter54): staged names are folded (tr) before matching, so KEY.PEM is
  # caught; the .env safe-variant -v exclusion runs on the SAME folded stream
  # (symmetric — a staged .ENV.EXAMPLE stays allowed).
  if git ${@+"$@"} diff --cached --name-only 2>/dev/null | tr '[:upper:]' '[:lower:]' | grep -E "${AEGIS_HIGH_RISK_STAGED_RE}" | grep -q . 2>/dev/null; then
    printf 'highrisk\n'
    return
  fi
  # Check if any secret .env file is in the staging area (exclude safe variants)
  if git ${@+"$@"} diff --cached --name-only 2>/dev/null | tr '[:upper:]' '[:lower:]' | grep -E '\.env' | grep -vE "${SAFE_ENV_SUFFIXES}$" | grep -q . 2>/dev/null; then
    printf 'env\n'
    return
  fi
}

# --- Check 0: Deny staging high-risk credential files (Form 1: command-text regex) ---
if printf '%s' "$CMD_LC" | grep -qE "$_STAGE_HIGHRISK_RE" 2>/dev/null; then
  emit_deny "[secrets] 高リスク認証ファイル (PEM鍵/SSH鍵/credentials.json/service-account.json 等) を git に追加しないでください。鍵が漏洩します。"
  exit 0
fi

# --- Check 1: Deny staging .env files ---
# Exclude safe variants: .env.example, .env.template, .env.sample

# Strip safe variants from command text, then check for remaining .env refs.
# C-1: strip runs on the LOWERCASED text so `.ENV.EXAMPLE` is stripped exactly
# like `.env.example` (symmetric fold — a case-variant safe file must not
# become a false deny).
STRIPPED=$(printf '%s' "$CMD_LC" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")

# Direct .env staging across all variants. Case-insensitive: on case-insensitive
# FS (macOS/Windows default) `git add .ENV` stages the real `.env` secret.
if printf '%s' "$STRIPPED" | grep -qE "$_STAGE_ENV_RE" 2>/dev/null; then
  # iter56 ①付随: .env.test 等は safe-list に入れない設計判断（中身無検査で
  # 「テスト用だから安全」は成立しない）。回避策の案内のみ文言で行う。
  emit_deny "[secrets] .env ファイルを git に追加しないでください。認証情報がリポジトリに漏洩します。プレースホルダのみのテンプレートは .env.example / .env.template / .env.sample 名なら追加できます。"
  exit 0
fi

# Broad staging that would include .env or high-risk credentials: git add -A, git add .
# iter77 SF-021 訂正（旧コメントは事実誤認だった）: `git stage` は `git add` の完全
# alias なので同じ -A/--all/. broad-stage 綴りを取る（stage も検出対象）。除外すべきは
# `update-index` のみ — これは -A/--all/. の broad 綴りを持たない別 plumbing コマンド。
# よって broad 検出の verb は (add|stage)（GIT_STAGE_VERB の update-index は含めない）。
# C-1: matched on CMD_LC so `GIT ADD -a` / `GIT STAGE -a` folds too; `-A` is spelled `-a` here.
# iter56 ①: a bare `\.` prefix-matched leading-dot FILENAMES (.env.example,
# .gitignore — 2 real denies in dogfood M2). Broad-dot means a token that
# stages a whole directory: . / .. / ./ / ../ followed by EOL or any
# NON-path character (negated class, not a delimiter enumeration — grill-code
# 🔴: listing ;&| missed `)` and `>`, letting `(cd x && git add .)` slip).
# The last branch `\.[^space]*[*?[]` catches a leading-dot GLOB (`.en*`, `.e?v`,
# `.*`) — a glob can expand to the real .env and bypassed BOTH this check and the
# literal-.env check above (blind security 2nd-opinion Major; the commit-time
# staged-diff scan still blocked the leak, but the add moat must not silently
# allow). Only the FIRST arg after `add` is inspected (regex anchored there), so
# a non-leading-dot glob like `foo.txt*` stays allowed.
# Known residual: dot-files whose 2nd char is outside [[:alnum:]._/-] (e.g.
# `.~x`, `.@foo`) still read as broad => deny. Deny-side = safe; use `--`.
# iter75-ff (SF-017 F1): 二経路トリガ。BROAD_RAW=生 CMD_LC が broad regex に一致
# （従来 deny・不変）。BROAD_NORM=難読化を畳んだ NORM_LC のみが一致（NORM!=CMD の
# とき）。どちらでもスキャン（_aegis_broad_secret_kind）し、種別が非空なら:
# RAW→emit_deny（従来メッセージ・種別で出し分け）／NORM のみ→emit_ask（難読化文言）。
BROAD_RAW=false; BROAD_NORM=false
printf '%s' "$CMD_LC" | grep -qE "$_STAGE_BROAD_RE" 2>/dev/null && BROAD_RAW=true
if [ "$BROAD_RAW" != true ] && [ -n "$NORM" ] && [ "$NORM" != "$CMD" ]; then
  printf '%s' "$NORM_LC" | grep -qE "$_STAGE_BROAD_RE" 2>/dev/null && BROAD_NORM=true
fi
if [ "$BROAD_RAW" = true ] || [ "$BROAD_NORM" = true ]; then
  BROAD_KIND=$(_aegis_broad_secret_kind)
  if [ -n "$BROAD_KIND" ]; then
    if [ "$BROAD_RAW" = true ]; then
      if [ "$BROAD_KIND" = highrisk ]; then
        emit_deny "[secrets] broad staging (git add -A / git stage -A / git add .) は repository 内の高リスク認証ファイル (PEM鍵/SSH鍵/credentials.json/service-account.json) を含む可能性があります。個別のファイル名を指定し、高リスクファイルは事前に削除/移動してください。"
      else
        emit_deny "[secrets] broad staging (git add -A / git stage -A / git add .) は .env を含む可能性があります。個別のファイル名を指定してステージングしてください。"
      fi
    else
      emit_ask "[secrets] 難読化された形（連結クォート/バックスラッシュ/\${IFS}）で repository 内の .env / 認証ファイルを broad staging（git add -A / git stage -A / git add .）しようとしている可能性があります。意図を確認してください。生の形（例: git add -A / git stage -A）は拒否されます。"
    fi
    exit 0
  fi
fi

# --- Check 2: Deny commit when .env is staged ---

# grill-code A-S4 (v1.6.1): commit verb also accepts the same GIT_PRE_OPTS
# prefix as the staging verbs above. Without this, `git --git-dir=.git
# --work-tree=. commit` and `git -C dir commit` skipped the staged-diff check.
# C-1 (iter54): the TRIGGER matches on CMD_LC (a `GIT COMMIT` resolves to
# /bin/git via the FS on a case-insensitive system); the -C/--git-dir path
# EXTRACTION below stays on the raw $CMD — folding it would corrupt the path.
# iter75-ff (SF-017 F1): commit も二経路トリガ。COMMIT_RAW=生 CMD_LC が commit regex に
# 一致（従来 deny・不変）。COMMIT_NORM=NORM_LC のみ一致（難読化 `git${IFS}commit` 等）。
# staged-diff スキャン（_aegis_staged_secret_kind）で .env/高リスクが staged なら:
# RAW→emit_deny（従来メッセージ・種別で出し分け）／NORM のみ→emit_ask（難読化文言）。
COMMIT_RAW=false; COMMIT_NORM=false
printf '%s' "$CMD_LC" | grep -qE "$_STAGE_COMMIT_RE" 2>/dev/null && COMMIT_RAW=true
if [ "$COMMIT_RAW" != true ] && [ -n "$NORM" ] && [ "$NORM" != "$CMD" ]; then
  printf '%s' "$NORM_LC" | grep -qE "$_STAGE_COMMIT_RE" 2>/dev/null && COMMIT_NORM=true
fi
if [ "$COMMIT_RAW" = true ] || [ "$COMMIT_NORM" = true ]; then
  # G2: resolve -C/--git-dir so the staged-diff scan targets the right repo.
  # Empty when absent → git runs in the hook CWD (current behavior, no regression).
  # 難読化 NORM-only 経路も生 $CMD から解決（obfuscated commit は通常 -C を持たず、
  # 持てば raw regex 側で既に一致するため CMD 基準で不変）。
  GIT_DIR_ARGS=()
  while IFS= read -r _a; do [ -n "$_a" ] && GIT_DIR_ARGS+=("$_a"); done < <(_aegis_git_dir_args "$CMD")
  COMMIT_KIND=$(_aegis_staged_secret_kind ${GIT_DIR_ARGS[@]+"${GIT_DIR_ARGS[@]}"})
  if [ -n "$COMMIT_KIND" ]; then
    if [ "$COMMIT_RAW" = true ]; then
      if [ "$COMMIT_KIND" = highrisk ]; then
        emit_deny "[secrets] 高リスク認証ファイル (PEM鍵/SSH鍵/credentials.json/service-account.json) がステージングされています。git reset HEAD でファイル名を指定して除外してからコミットしてください。"
      else
        emit_deny "[secrets] .env ファイルがステージングされています。git reset HEAD .env で除外してからコミットしてください。"
      fi
    else
      emit_ask "[secrets] 難読化された形（連結クォート/バックスラッシュ/\${IFS}）で .env / 認証ファイルが staged のまま commit しようとしている可能性があります。意図を確認してください。生の形（例: git commit）は拒否されます。"
    fi
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
# C-1 (iter54): lowercase-then-strip keeps the fold symmetric here too.
K4_STRIPPED=$(printf '%s' "$CMD_LC" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")
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

# C-1 (iter54): lowercase-then-strip (symmetric fold; `cp x .ENV` is a real
# secret .env on a case-insensitive FS).
STRIPPED_WRITE=$(printf '%s' "$CMD_LC" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")
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

# iter75 SF-017: 生 CMD で全 deny を通過したとき、quote/backslash/${IFS} 難読化を
# 正規化し、同じ staging 検出器（単一ソース）を再適用。難読化実在かつ一致 → ASK
# （DENY でなく: command 位置非解釈ゆえ commit -m 内 .env 言及と区別不能・
# _obfuscated_unlock_on_cp 一貫）。NORM/NORM_LC は CMD_LC 直後で前倒し計算済み
# （iter75-ff）。patterns.sh 欠落時は NORM="" ゆえこのブロックは自然に skip。
if [ -n "$NORM" ] && [ "$NORM" != "$CMD" ]; then
  NORM_STRIPPED=$(printf '%s' "$NORM_LC" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")
  if printf '%s' "$NORM_LC" | grep -qE "$_STAGE_HIGHRISK_RE" 2>/dev/null \
     || printf '%s' "$NORM_STRIPPED" | grep -qE "$_STAGE_ENV_RE" 2>/dev/null; then
    emit_ask "[secrets] 難読化された形（連結クォート/バックスラッシュ/\${IFS}）で認証ファイル (.env / 鍵 / credentials 等) を git に staging しようとしている可能性があります。意図を確認してください。生の形（例: git add .env）は拒否されます。"
    exit 0
  fi
fi

# No issue found — allow.
emit_allow
exit 0
