#!/usr/bin/env bash
# PreToolUse hook for Bash: residual static guard after the iter57 moat
# handover. The PRIMARY moat for the stable control-plane (hooks/ scripts/
# templates/ CLAUDE.md .claude/{rules,skills,commands,agents}) is the OS lock
# (hooks/lib/cp-lock.sh — syscall-enforced, form-independent). This hook keeps
# ONLY what the lock cannot cover:
#   (1) runtime-state writes — docs/STATUS.md and the non-locked parts of
#       .claude/ (settings*.json, .gate-snapshot, evidence-log …) must stay
#       writable for the harness/framework, so Bash writes are gated
#       statically. Allowlist = hooks/lib/scripts-manifest.tsv class allow|ask
#       (single owner, iter55). manifest unreadable = deny (fail-closed).
#   (2) unlock forms — chmod/chflags/chattr aimed at the locked CP would turn
#       an EACCES "self-repair" into an uncaught accident (rev.2 撤回理由②).
#       Denied with a policy message that names the correct path.
#   (3) broad recursive chmod (-R on . / .. / / / *) — carries no CP token but
#       unlocks the whole tree including the CP (grill 致命4). ASK, not deny:
#       a user project may legitimately bulk-chmod its own tree.
# Everything else that lived in the retired check-control-plane.sh
# (obfuscation token analysis, glob/quote-split/interpreter resolution) is
# gone by design: those forms hit EACCES at the syscall regardless of shape.
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
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
STATUS_FILE="${ROOT}/docs/STATUS.md"

aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"

INPUT=$(cat)

# Byte-safety (iter76 SF-018): CMD below is arbitrary tool_input; under a
# UTF-8 locale one invalid byte crashes `tr` ("Illegal byte sequence") and
# `set -e` exits rc=1 with NO decision emitted = fail-open on the ONLY
# non-framework runtime-state guard. C locale processes byte-wise; every
# pattern in this hook is ASCII so matching is unchanged, and the python3
# extraction keeps UTF-8 fidelity under C (PEP 540). Mirrors
# check-destructive.sh / check-secrets.sh (iter73) — locale sweep complete.
export LC_ALL=C LC_CTYPE=C LANG=C

# No STATUS.md = no framework context: nothing to guard.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Case folding (iter54 C-1): on a case-insensitive FS, DOCS/STATUS.MD is the
# same inode as docs/STATUS.md — deny-side greps must fold there (and only
# there; folding allow-side carve-outs would WIDEN allow, the wrong way).
CASE_FOLD=0
if aegis_fs_case_insensitive "$ROOT"; then
  CASE_FOLD=1
fi
CASE_I=()
if [ "$CASE_FOLD" = "1" ]; then
  CASE_I=(-i)
fi

# Guard targets. RUNTIME_STATE is deliberately NARROWER than the retired
# CONTROL_PLANE regex: a user project's own foo/STATUS.md is not our
# runtime-state (the aegis STATUS lives at docs/STATUS.md; the bare form
# catches cwd-shifted mentions like `cd docs && sed -i … STATUS.md`).
RUNTIME_STATE='docs/STATUS\.md|(^|[^A-Za-z0-9_./-])STATUS\.md|\.claude/|\.claude([^A-Za-z0-9_/]|$)'
# Stable-CP tokens, used ONLY for the unlock-form check (the lock itself is
# the moat for these paths; boundary keeps a project's own src/hooks/ out).
# iter57 review 🟡: the .claude/ subdirs also accept no-trailing-slash and
# space/EOL boundaries so `chmod +w .claude/skills` routes to the OS-lock
# unlock message (task_type=framework), not the misleading runtime-state one.
LOCKED_CP='(^|[^A-Za-z0-9_./-])(\./)*(hooks|scripts|templates)(/|[[:space:]]|$)|(^|[^A-Za-z0-9_./-])CLAUDE\.md|\.claude/(rules|skills|commands|agents)(/|[[:space:]]|$)'
UNLOCK_TOOLS='(^|[^A-Za-z0-9_])(chmod|chflags|chattr)([[:space:]]|$)'

# Mask the CONTENT of every '...' / "..." quoted span with 'x', preserving the
# quotes and everything outside them (ported verbatim from the retired
# check-control-plane.sh — OBS-006). Single quotes take no escapes; inside
# double quotes a backslash escapes the next char. Prints the masked string;
# returns 1 on an UNBALANCED quote so the caller fails closed. Only safe when the
# command has NO $(...)/backtick (an active sub inside "" would be hidden).
mask_quoted() {
  local s="$1"
  local out="" i=0 ch state=none
  while [ "$i" -lt "${#s}" ]; do
    ch="${s:$i:1}"
    case "$state" in
      none)
        case "$ch" in
          "'") state=sq; out="${out}'" ;;
          '"') state=dq; out="${out}\"" ;;
          *)   out="${out}${ch}" ;;
        esac ;;
      sq)
        if [ "$ch" = "'" ]; then state=none; out="${out}'"; else out="${out}x"; fi ;;
      *)  # dq
        if [ "$ch" = '\' ]; then out="${out}xx"; i=$((i + 1))
        elif [ "$ch" = '"' ]; then state=none; out="${out}\""
        else out="${out}x"; fi ;;
    esac
    i=$((i + 1))
  done
  [ "$state" = none ] || return 1
  printf '%s' "$out"
}

# Command extraction (same contract as the retired hook): python3-first; the
# bash fast-path would truncate at the first embedded escaped quote and could
# hide a mention placed after it — treat that as extraction failure.
CMD=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
if [ -z "$CMD" ] && ! printf '%s' "$INPUT" | grep -q '\\"'; then
  CMD=$(extract_command "$INPUT")
fi
# Embedded newlines/CR are command separators (framework convention): a later
# line must not ride behind a benign first line in the line-oriented greps.
if [ -n "$CMD" ]; then
  CMD=$(printf '%s' "$CMD" | tr '\n\r' ';;')
fi

# True when the command WRITES to (not merely mentions) runtime-state. OBS-006:
# a runtime-state path inside a quoted literal that is not a write target
# (`git commit -m "...STATUS.md..."`, `echo "see docs/STATUS.md"`) is NOT a write
# and must be allowed. Strategy (ported from the retired hook's
# cmd_mentions_control_plane, keyed on RUNTIME_STATE):
#   - $(...) / backtick present → masking is unsafe → raw fail-closed grep.
#   - else mask quoted literals; (a) an unquoted runtime-state path anywhere, or
#     (b) a redirect target (quote-stripped from the RAW command) that is
#     runtime-state → write-eligible. A path surviving ONLY inside quotes → not.
_writes_runtime_state() {
  local cmd="$1" masked redir target
  if printf '%s' "$cmd" | grep -qE '\$\(|`'; then
    printf '%s' "$cmd" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE"
    return $?
  fi
  masked=$(mask_quoted "$cmd") || return 0   # unbalanced quotes → fail closed
  # (a) unquoted runtime-state path anywhere in the masked command.
  if printf '%s' "$masked" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE"; then
    return 0
  fi
  # (b) a redirect target (quote-stripped) that is runtime-state — even when the
  # path sat inside the quotes of the target token (`> "docs/STATUS.md"`).
  while IFS= read -r redir || [ -n "$redir" ]; do
    target=$(printf '%s' "$redir" | sed -E 's/^[[:space:]]*>>?[[:space:]]*//')
    case "$target" in
      \"*\") target="${target#\"}"; target="${target%\"}" ;;
      \'*\') target="${target#\'}"; target="${target%\'}" ;;
    esac
    [ -n "$target" ] || continue
    if printf '%s' "$target" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE"; then
      return 0
    fi
  done < <(printf '%s' "$cmd" | grep -oE ">>?[[:space:]]*(\"[^\"]*\"|'[^']*'|[^[:space:]|&;<>]+)")
  # (c) runtime-state survives ONLY inside a quoted literal (a/b cleared the
  # unquoted forms and redirect targets). A quoted token can still be a WRITE
  # DESTINATION for many commands (`python3 -c 'open("docs/STATUS.md","w")'`,
  # cp/mv/tee/sed -i/perl -i/…), so relax via an ALLOWLIST of no-write "message"
  # commands — NEVER a blocklist of writers (a writer not on the list leaks).
  # echo/printf/`git commit` cannot write FILE CONTENT to a path argument (their
  # only working-tree write is a redirect, already cleared in (b)); a chain
  # operator that could introduce a writer is fail-closed.
  if printf '%s' "$cmd" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE"; then
    if printf '%s' "$cmd" | grep -qE '[;&|]'; then
      return 0
    fi
    if ! printf '%s' "$cmd" | grep -qE '^[[:space:]]*(echo|printf|git[[:space:]]+commit)([[:space:]]|$)'; then
      return 0
    fi
  fi
  return 1
}
_unlock_form_on_cp() {
  printf '%s' "$1" | grep -qE "$UNLOCK_TOOLS" || return 1
  printf '%s' "$1" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$LOCKED_CP|\.claude/(rules|skills|commands|agents)/"
}
# grill 致命4: the most natural EACCES "self-repair" (`chmod -R u+w .`)
# carries no CP token, but recursion unlocks the CP with it.
_recursive_chmod_broad() {
  printf '%s' "$1" | grep -qE '(^|[^A-Za-z0-9_])chmod[[:space:]][^;|&]*-R' || return 1
  printf '%s' "$1" | grep -qE '[[:space:]](\.{1,2}/?|/|\*)([[:space:]]|$)'
}
# iter57 security 2nd-opinion (Major): the plain-text LOCKED_CP grep in
# _unlock_form_on_cp misses SHELL-OBFUSCATED unlock forms the retired hook's
# tokenizer caught — `chmod u+w hoo\ks/…`, `chmod +w hooks""/…`,
# `chmod +w "ho""oks"/…`, `chmod +w $(echo hooks)/…`. A full tokenizer is what
# the moat handover deliberately retired, so instead: an unlock tool whose
# quote/backslash-stripped form reveals a stable-CP token (or that builds the
# path via command substitution) is ASKed — the same fail-visible treatment as
# broad recursive chmod. This turns a SILENT allow (旧 deny からの後退) into a
# visible confirm without re-introducing a parser. Deep $()-built paths stay
# out of the accident threat model (recorded in docs/security-followups.md).
_obfuscated_unlock_on_cp() {
  local cmd="$1" norm
  printf '%s' "$cmd" | grep -qE "$UNLOCK_TOOLS" || return 1
  # Strip backslashes and both quote types via param expansion (no parser).
  norm="${cmd//\\/}"
  norm="${norm//\"/}"
  norm="${norm//\'/}"
  # Only meaningful when obfuscation was actually present: stripping CHANGED the
  # command (a quote/backslash existed), or a command substitution builds the
  # path. A plain `chmod +w hooks/…` (norm == cmd, no $()) is already DENIED by
  # _unlock_form_on_cp — do not downgrade it to ASK here.
  if [ "$norm" = "$cmd" ] && ! printf '%s' "$cmd" | grep -qE '\$\(|`'; then
    return 1
  fi
  # Left boundary keeps `webhooks`/`myscripts` out; right boundary accepts any
  # non-word char (/, space, ), backtick, EOL) so a cmdsub form `$(echo hooks)/`
  # — where the CP token is followed by `)` — is still revealed.
  printf '%s' "$norm" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE \
    '(^|[^[:alnum:]_./-])(hooks|scripts|templates)([^[:alnum:]_.]|$)|CLAUDE\.md|\.claude/(rules|skills|commands|agents)'
}

if [ -n "$CMD" ]; then
  if ! _writes_runtime_state "$CMD" && ! _unlock_form_on_cp "$CMD" \
     && ! _recursive_chmod_broad "$CMD" && ! _obfuscated_unlock_on_cp "$CMD"; then
    emit_allow
    exit 0
  fi
else
  # Extraction failed — fall back to the raw input (fail-closed). Real hook
  # input always carries transcript_path under ~/.claude/projects/, which the
  # `.claude/` alternation matches, so unextractable real input stays on the
  # deny path by construction (same property as the retired hook).
  if ! printf '%s' "$INPUT" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE|$LOCKED_CP"; then
    emit_allow
    exit 0
  fi
fi

# framework task: the CP is legitimately unlocked and STATUS/settings writes
# are the framework's own work — allow everything (retired-hook parity).
TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
if [ "$TASK_TYPE" = "framework" ]; then
  emit_allow
  exit 0
fi

if [ -n "$CMD" ] && _unlock_form_on_cp "$CMD"; then
  emit_deny "[integrity] chmod/chflags/chattr で control-plane（hooks/ scripts/ templates/ CLAUDE.md .claude/rules 等）の書込み保護を変更しようとしています。これは aegis の OS-lock（主 moat）です。EACCES が出た場合も解錠せず、framework の変更が正当な作業なら scripts/update-task.sh --type framework で task_type を切り替えてください。"
  exit 0
fi

if [ -n "$CMD" ] && _recursive_chmod_broad "$CMD"; then
  emit_ask "[integrity] 再帰 chmod（-R）がリポジトリ全体（. / .. / / / * 等）に及びます。control-plane の OS-lock（主 moat）も解錠されるため確認してください。EACCES への対処なら chmod ではなく task_type=framework への切替（scripts/update-task.sh）が正です。"
  exit 0
fi

if [ -n "$CMD" ] && _obfuscated_unlock_on_cp "$CMD"; then
  emit_ask "[integrity] chmod/chflags/chattr が難読化された形（バックスラッシュ・連結クォート・コマンド置換）で control-plane（hooks/ scripts/ templates/ CLAUDE.md .claude/*）を解錠しようとしている可能性があります。OS-lock（主 moat）の解錠は行わず、framework の変更が正当なら scripts/update-task.sh --type framework で task_type を切り替えてください。"
  exit 0
fi

# ---------------------------------------------------------------------------
# Allow-side carve-outs, ported VERBATIM from the retired check-control-plane.sh
# (iter55 contracts: manifest single-owner, safe-stderr strip, read-only forms,
# bare git stage). Deny detection above ran on the RAW $CMD; stripping only
# feeds the allow side (never widens what was already matched for deny).
# ---------------------------------------------------------------------------
SCRIPTS_MANIFEST="${SCRIPT_DIR}/lib/scripts-manifest.tsv"

# Chain/redirect operators that indicate compound or write commands. If present,
# the command is never eligible for allowlist or read-only pass-through.
CHAIN_OPS='[;&|>]|\$\(|`'

# SAFE stderr redirects only: `2>/dev/null` / `2>&1` cannot write a file but
# their > / & hit CHAIN_OPS and knocked read-only forms out of the carve-out
# (iter55 gate-battle 1). 2>>, 2>file, fd1 >/dev/null are NOT stripped.
strip_safe_stderr_redirects() {
  printf '%s' "$1" | sed -E \
    -e 's,(^|[[:space:]])2>[[:space:]]?/dev/null([[:space:]]|$),\1\2,g' \
    -e 's,(^|[[:space:]])2>&1([[:space:]]|$),\1\2,g'
}
CMD_SAFE=$(strip_safe_stderr_redirects "$CMD")

# Execution-form prefix match against the manifest (class allow|ask only).
# Substring matching would mistake a WRITE TO an allowlisted script for an
# execution (iter55 grill-code 🔴). manifest unreadable => rc 1 => fail-closed.
manifest_script_in() {
  local cmd="$1" entry cls
  [ -r "$SCRIPTS_MANIFEST" ] || return 1
  while IFS=$'\t' read -r entry cls || [ -n "$entry" ]; do
    case "$entry" in ''|\#*) continue ;; esac
    case "$cls" in allow|ask) ;; *) continue ;; esac
    case "$cmd" in
      "$entry"|"$entry "*|"./$entry"|"./$entry "*|\
      "python3 $entry"|"python3 $entry "*|"python $entry"|"python $entry "*|\
      "bash $entry"|"bash $entry "*|"sh $entry"|"sh $entry "*)
        return 0 ;;
    esac
  done < "$SCRIPTS_MANIFEST"
  return 1
}

is_allowlisted() {
  local cmd="$1"
  # Reject if command contains chain operators.
  if printf '%s' "$cmd" | grep -qE "$CHAIN_OPS"; then
    return 1
  fi
  manifest_script_in "$cmd"
}

if [ -n "$CMD_SAFE" ] && is_allowlisted "$CMD_SAFE"; then
  emit_allow
  exit 0
fi

# --- Read-only command checks (reading runtime-state is not mutation) ---
CHECK_CMD="$CMD_SAFE"
READ_ONLY_STARTS='^(cat|head|tail|less|more|grep|egrep|fgrep|rg|find|ls|wc|diff|file|stat|md5sum|sha256sum) '
WRITE_INDICATORS='(^|[^A-Za-z0-9_])sed\s+-i|>\s*[^&]|>>\s|(^|[^A-Za-z0-9_])(tee|cp|mv|chmod|rm|mkdir|touch|install|ln)\s|write_text|write_bytes|open\(.*[wax]|\.write\(|Path\(.*\.write|(unlink|remove|rename|truncate)[[:space:]]*\(|(^|[^A-Za-z0-9_])-(exec|execdir|ok|okdir|delete|fprint0?|fprintf|fls)($|[^A-Za-z0-9_])'

# (a) single read-only command: no chain/redirect operators at all.
if [ -n "$CHECK_CMD" ] && ! printf '%s' "$CHECK_CMD" | grep -qE "$CHAIN_OPS"; then
  if printf '%s' "$CHECK_CMD" | grep -qE "$READ_ONLY_STARTS" && \
     ! printf '%s' "$CHECK_CMD" | grep -qE "$WRITE_INDICATORS"; then
    emit_allow
    exit 0
  fi
fi

# (b) read-only PIPELINE: a `|`-only pipe whose EVERY segment is independently
# read-only. Only `|` is tolerated — ; & < > $() ` keep disqualifying.
if [ -n "$CHECK_CMD" ] && printf '%s' "$CHECK_CMD" | grep -q '|' \
   && ! printf '%s' "$CHECK_CMD" | grep -qE '[;&<>]|\$\(|`|\|\|'; then
  READ_ONLY_SEG='^[[:space:]]*(cat|head|tail|less|more|grep|egrep|fgrep|rg|find|ls|wc|diff|file|stat|md5sum|sha256sum)([[:space:]]|$)'
  pipe_all_ro=yes
  # `|| [ -n "$_seg" ]` processes the FINAL segment too (tr leaves no trailing
  # newline there — dropping it would fail OPEN on `| tee` / `| sh`).
  while IFS= read -r _seg || [ -n "$_seg" ]; do
    if ! printf '%s' "$_seg" | grep -qE "$READ_ONLY_SEG" \
       || printf '%s' "$_seg" | grep -qE "$WRITE_INDICATORS"; then
      pipe_all_ro=no
      break
    fi
  done < <(printf '%s' "$CHECK_CMD" | tr '|' '\n')
  if [ "$pipe_all_ro" = "yes" ]; then
    emit_allow
    exit 0
  fi
fi

# --- Bare `git add <paths>` staging carve-out (OBS-017 catch-22) ---
# Staging only records paths; it does not modify file CONTENT. ASK, not DENY.
# Broad/forced flags (-A/--all/-f/--force) and any chain/redirect keep denying.
is_bare_git_stage() {
  local cmd="$1"
  # Must be a git add/stage invocation (optionally `git -C <dir> add`).
  printf '%s' "$cmd" | grep -qE \
    '(^|[^A-Za-z0-9_])git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?(add|stage)([[:space:]]|$)' \
    || return 1
  # Reject any chain/redirect operator (same guard the allowlist uses).
  if printf '%s' "$cmd" | grep -qE "$CHAIN_OPS"; then
    return 1
  fi
  # Reject broad/forced staging flags. The short-cluster alt catches -A, -f and
  # combinations (-Af, -vfA); the long forms are matched explicitly.
  if printf '%s' "$cmd" | grep -qE \
       '(^|[[:space:]])(--all|--force|-[A-Za-z]*[Af][A-Za-z]*)([[:space:]]|$)'; then
    return 1
  fi
  return 0
}

if [ -n "$CMD_SAFE" ] && is_bare_git_stage "$CMD_SAFE"; then
  emit_ask "[integrity] git add で runtime-state（docs/STATUS.md・.claude/ 設定類）を staging しようとしています。ファイル内容は変更しません（baseline コミット等の正当な操作の可能性）。意図を確認してください。なおファイル名を含まない形（例: git add docs/）ならこの確認は出ません。"
  exit 0
fi

# Allowlisted script disqualified only by chaining — dedicated guidance
# (iter55 gate-battle 6: prevents the "hook is flaky" misread).
if [ -n "$CMD_SAFE" ] && manifest_script_in "$CMD_SAFE"; then
  emit_deny "[integrity] このコマンドは許可済みスクリプト（scripts-manifest）を含みますが、チェーン/リダイレクト演算子（; && || | > \$() \`）付きの複合コマンドでは実行できません。パイプ等を外し、スクリプトを単体コマンドとして実行してください。"
  exit 0
fi

# Default: deny. runtime-state referenced, not an authorized path.
emit_deny "[integrity] runtime-state（docs/STATUS.md・.claude/ 設定類）へ書込みうる Bash コマンドは project work（task_type=${TASK_TYPE}）中はブロックされます。ゲート値は scripts/update-gate.sh、task_type/task_size は scripts/update-task.sh を単体で実行してください。読取りは cat/grep 等の単体コマンドなら許可されます。"
exit 0
