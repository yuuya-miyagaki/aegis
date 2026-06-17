#!/usr/bin/env bash
# PreToolUse hook for Bash: denies commands that reference control plane paths
# during non-framework tasks.
#
# Strategy: ALLOWLIST, not blacklist.
# If the extracted command mentions any control plane path, it is denied
# UNLESS it matches the allowlist or task_type is "framework". The raw hook
# input is only consulted when command extraction fails (fail-closed), because
# it always carries transcript_path under ~/.claude/projects/.
#
# Allowlist rules:
# - The command must be SOLELY an allowlisted script invocation (no chaining).
# - Commands containing ;, &&, ||, |, $(), `` are never allowlisted
#   (prevents "validator && malicious" bypass).
# - Known read-only simple commands (cat, grep, ls) are allowed only when
#   they contain no chaining operators and no write indicators.
#
# Control plane paths: STATUS.md, CLAUDE.md, .claude/, hooks/, scripts/
# Allowlist: update-gate.sh, check_status.py, check_framework_contract.py,
#            record-test-result.py, run-test-strength-drill.py (evidence scripts)
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
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction (fail-closed via safety lib on source failure).
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
# frontmatter.sh provides frontmatter_value (task_type read). Required (fail-closed)
# for consistency with the libs above; the whole lib/ ships in every install.
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"

# Read stdin (raw hook input).
INPUT=$(cat)

# If STATUS.md doesn't exist, allow (no framework context).
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Control plane path patterns. Directory names are boundary-anchored so a
# project's own src/hooks/ etc. does not match, but non-canonical re-entry
# forms (../hooks/, foo/../hooks/, /./hooks/) and unresolvable dynamic forms
# ($(pwd)/hooks/, $VAR/hooks/, ")/hooks/") stay deny-eligible (fail-closed:
# we cannot statically resolve them, so we treat them as control plane).
ROOT_REAL="$(cd "$ROOT" && pwd -P)"
CP_DIRS='hooks|scripts|templates'
CONTROL_PLANE='STATUS\.md|CLAUDE\.md|\.claude/|\.claude[^A-Za-z0-9_/]'
CONTROL_PLANE="${CONTROL_PLANE}|(^|[^A-Za-z0-9_./-])(\\./)*(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|(\\.\\./)+(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|/\\./(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|[)\`'\"]/(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|\\\$[A-Za-z_{][A-Za-z0-9_}]*/(${CP_DIRS})/"
# C-1 (v1.6.1): parameter-expansion DEFAULT literal — `${VAR:-hooks}/`.
# The boundary `[^A-Za-z0-9_./-]` excluded `:-` so `${HOOKS_DIR:-hooks}/lib/`
# slipped through. Cover :-, :=, :+ literals leading into a CP dir. The `}?`
# allows the form `${VAR:-hooks}/lib/` (close-brace between hooks and /) as
# well as `${VAR:-hooks/lib/...}` (path inside the braces).
CONTROL_PLANE="${CONTROL_PLANE}|:[-=+](${CP_DIRS})}?/"

# True when TEXT references this project's control plane (regex form + literal
# absolute paths under the project root — the boundary regex intentionally skips
# /-preceded names, so absolute paths need the fixed-string pass). Shared by the
# raw (fail-closed) and the masked (precise) passes of the mention check.
_text_mentions_cp() {
  local text="$1" base
  if printf '%s' "$text" | grep -qE "$CONTROL_PLANE"; then
    return 0
  fi
  for base in "$ROOT" "$ROOT_REAL"; do
    if printf '%s' "$text" | grep -qF \
        -e "${base}/hooks/" -e "${base}/scripts/" -e "${base}/templates/"; then
      return 0
    fi
  done
  return 1
}

# Mask the CONTENT of every '...' / "..." quoted span with 'x', preserving the
# quote characters and everything outside quotes. Single quotes take no escapes;
# inside double quotes a backslash escapes the next char (so \" does not end the
# span). Prints the masked string; returns 1 on an UNBALANCED quote so the
# caller fails closed. Only safe to call when the command has NO $(...)/backtick:
# a command substitution inside double quotes is still executed, so masking it
# would hide a real write (e.g. `echo "$(rm hooks/x)"`).
mask_quoted() {
  local s="$1"
  # NB: ${#s} is taken in the while-condition, not a sibling `local n=${#s}` on
  # the same line as `s="$1"` — a single `local` expands ${#s} against the OUTER
  # s (still empty), yielding 0 and an empty mask (a silent fail).
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

# True when the command WRITES to (not merely mentions) this project's control
# plane. OBS-006: a CP path inside a quoted literal that is not a write target
# (`git commit -m "...STATUS.md..."`, `echo 'see hooks/' >> notes.txt`) is NOT a
# write and must be allowed. Strategy:
#   - $(...) / backtick present → masking is unsafe (active spans inside double
#     quotes) → fall back to the raw fail-closed mention check.
#   - else mask quoted literals; an unquoted CP path anywhere → deny-eligible;
#     a redirect target (quote-stripped, taken from the RAW command so a quoted
#     `> "hooks/x"` and a `bash -c "... > hooks/x"` both count) that is CP →
#     deny-eligible.
#   - a CP path that survives only inside a quoted literal is relaxed ONLY for an
#     ALLOWLIST of no-write commands (echo/printf/git commit) — never a blocklist
#     of write utilities, which leaks (a writer not on the list bypasses).
# Variable-built write targets that are not literally CP fall through and are
# caught downstream by cmd_var_built_write (ask, fail-closed).
cmd_mentions_control_plane() {
  local cmd="$1" masked redir target
  # Command substitution present → cannot safely mask → raw fail-closed check.
  if printf '%s' "$cmd" | grep -qE '\$\(|`'; then
    _text_mentions_cp "$cmd"
    return $?
  fi
  # Mask quoted literals; unbalanced quotes → fail closed (treat as mention).
  masked=$(mask_quoted "$cmd") || return 0
  # (a) Unquoted CP path anywhere in the masked command.
  if _text_mentions_cp "$masked"; then
    return 0
  fi
  # (b) A redirect target (quote-stripped) that is control plane — even when the
  # CP path sat inside the quotes of the target token.
  while IFS= read -r redir || [ -n "$redir" ]; do
    target=$(printf '%s' "$redir" | sed -E 's/^[[:space:]]*>>?[[:space:]]*//')
    case "$target" in
      \"*\") target="${target#\"}"; target="${target%\"}" ;;
      \'*\') target="${target#\'}"; target="${target%\'}" ;;
    esac
    [ -n "$target" ] || continue
    if _text_mentions_cp "$target"; then
      return 0
    fi
  done < <(printf '%s' "$cmd" | grep -oE ">>?[[:space:]]*(\"[^\"]*\"|'[^']*'|[^[:space:]|&;<>]+)")
  # (c) The only remaining CP is inside a quoted literal (a/b already cleared the
  # unquoted forms and redirect targets). A quoted token can still be a WRITE
  # DESTINATION for many commands (cp/mv/tee/sed -i/perl -i/patch/awk/ed/...), so
  # the relaxation is an ALLOWLIST of known no-write "message" commands — NEVER a
  # blocklist of write utilities, which always leaks (a writer not on the list
  # would bypass). echo/printf/`git commit` cannot write FILE CONTENT to a path
  # argument (git commit mutates the repo index/objects, not a working-tree file);
  # their only working-tree write path is a redirect, already checked in (b).
  # Anything else, or any command separator (;, &, |; newline already normalized
  # to ; at extraction) that could introduce a writer, is fail-closed.
  if _text_mentions_cp "$cmd"; then
    if printf '%s' "$cmd" | grep -qE '[;&|]'; then
      return 0
    fi
    if ! printf '%s' "$cmd" \
         | grep -qE '^[[:space:]]*(echo|printf|git[[:space:]]+commit)([[:space:]]|$)'; then
      return 0
    fi
  fi
  return 1
}

# C-1 (v1.6.1): variable-built write target. Static expansion is undecidable,
# so when a command satisfies ALL three conditions we route to `ask`:
#   (1) at least one variable ASSIGNMENT at command position (X=val)
#   (2) at least one variable USE elsewhere ($X or ${X})
#   (3) a write operation present (redirect / write utility / -c script)
# The bypass `D=h; D=${D}ooks; > $D/lib/emit.sh` matches all three; legitimate
# `MY_VAR=safe make build` (no write to a var-built path) does not. The legit
# `OUT=/tmp/x; echo y > $OUT` triggers `ask` (mild friction) — user confirms.
# Receive list & rationale: docs/qa-reports/v161-security.md.
cmd_var_built_write() {
  local cmd="$1"
  # K-2 (v1.6.2): three independent paths cover REDTEAM-02 bypasses.
  #
  # Path A (v1.6.1 baseline): ASSIGNMENT + VARIABLE USE + WRITE OP.
  # Path B (v1.6.2 NEW): "first write redirect's target" contains $(...)
  #   or backtick. Static expansion is impossible — fail-closed by ASK.
  #   The target is sliced as everything between '>' and the next chain
  #   separator (|, &, ;) to avoid over-flagging an unrelated cmdsub in a
  #   later command (grill 要検討 1).
  # Path C (v1.6.2 NEW): alternative ASSIGNMENT forms (printf -v, read,
  #   eval, declare, local) co-occurring with any WRITE OP. The literal
  #   identifier= regex in Path A's gate (1) misses these.

  # --- Path B: cmdsub / backtick in ANY write target ---
  # Extract EVERY redirect target token (everything from a `>` / `>>` up
  # to the next chain separator). If any of them contains `$(` or
  # backtick, ASK. grill-code Critical 1 fix: the prior `sed -nE
  # 's/^[^>]*>>?...'` anchored to the FIRST `>` only and let attackers
  # bypass via `echo a > /tmp/safe; > $(echo hooks)/lib/emit.sh`. `grep
  # -oE` walks every redirect, including ones after `;`, `&&`, `||`.
  # Each match still slices target tokens at `|&;` so unrelated cmdsubs
  # in a later, separate command stay out (grill 要検討 1 preserved).
  if printf '%s' "$cmd" | grep -oE '>>?[[:space:]]*[^|&;]*' \
       | grep -qE '\$\(|`'; then
    return 0
  fi

  # --- Path C: alternative assignment forms + write op ---
  # printf -v VAR ... / read VAR / eval "VAR=..." / declare VAR=... /
  # local VAR=... can build a control-plane path that Path A's IDENT=
  # regex never sees. Pair with a write op (same regex as gate 3 below)
  # to avoid over-flagging plain `read x` etc.
  if printf '%s' "$cmd" | grep -qE \
       '(^|;|&|\|)[[:space:]]*(printf[[:space:]]+-v[[:space:]]+[A-Za-z_]|read[[:space:]]+[A-Za-z_]|eval[[:space:]]+["'\'']|declare[[:space:]]+[A-Za-z_]|local[[:space:]]+[A-Za-z_])' && \
     printf '%s' "$cmd" | grep -qE \
       '>>?[[:space:]]*[^&]|(^|[^A-Za-z0-9_])(tee|cp|mv|install|dd|truncate|ln|rm|chmod|chown|mkdir|curl|wget|rsync|tar)([[:space:]]|$)|sed[[:space:]]+-i|python3?[[:space:]]+-c|bash[[:space:]]+-c|git[[:space:]]+(apply|add|mv|rm|stage|update-index)|find[[:space:]]+.*-(exec|delete|fprint|fprintf)'; then
    return 0
  fi

  # --- Path A: v1.6.1 baseline (ASSIGNMENT + VAR USE + WRITE OP) ---
  # (1) ASSIGNMENT at command position: token start followed by IDENT=
  printf '%s' "$cmd" | grep -qE \
    '(^|;|&|\|)[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=|[[:space:]][A-Za-z_][A-Za-z0-9_]*=' \
    || return 1
  # (2) VARIABLE REFERENCE anywhere — $X, ${X}, ${X:-...}, etc.
  printf '%s' "$cmd" | grep -qE '\$\{?[A-Za-z_][A-Za-z0-9_]*' || return 1
  # (3) WRITE OPERATION: redirect or write/modify/delete utility or `-c`
  # interpreter script. Coverage extended from v1.6.1 initial (grill-code
  # A-Crit-1): ln/curl/wget/rsync/chmod/chown/rm/mkdir/git apply/find write
  # actions all can produce or zero-out a control-plane file via a var-built
  # path and equally collapse the moat (a missing or non-readable lib
  # silently fails the source — fail-open). Each utility is anchored on
  # non-alphanumeric boundary so substring matches in identifiers (e.g. a
  # filename containing `ln`) do not trigger.
  printf '%s' "$cmd" | grep -qE \
    '>>?[[:space:]]*[^&]|(^|[^A-Za-z0-9_])(tee|cp|mv|install|dd|truncate|ln|rm|chmod|chown|mkdir|curl|wget|rsync|tar)([[:space:]]|$)|sed[[:space:]]+-i|python3?[[:space:]]+-c|bash[[:space:]]+-c|git[[:space:]]+(apply|add|mv|rm|stage|update-index)|find[[:space:]]+.*-(exec|delete|fprint|fprintf)' \
    || return 1
  return 0
}

# Extract the command with full fidelity: python3 first, bash fast-path next.
# When the input carries embedded escaped quotes and python3 is unavailable,
# the bash fast-path would truncate at the first inner quote and could hide a
# control plane mention placed after it — treat that as extraction failure.
CMD=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
if [ -z "$CMD" ] && ! printf '%s' "$INPUT" | grep -q '\\"'; then
  CMD=$(extract_command "$INPUT")
fi
# Treat embedded newlines/CR as command separators: a multi-line command is
# multiple commands. This matches the framework convention (post-bash hook and
# build-judge-card.py normalize \n -> ;). Without it, the line-oriented greps
# below (read-only pipeline check, the quoted-mention allowlist) would let a
# writer on a LATER line ride along behind a benign first line — e.g.
# `echo ok⏎cp x "hooks/y"` would mask the quoted target and the `^echo` allowlist
# would match line 1, returning allow. Normalizing once, here, covers every
# downstream check on $CMD.
if [ -n "$CMD" ]; then
  CMD=$(printf '%s' "$CMD" | tr '\n\r' ';;')
fi

# Match control plane against the extracted command, NOT the raw input: real
# hook input always carries transcript_path under ~/.claude/projects/, so a
# raw-input match made this early-allow unreachable and denied nearly every
# Bash command at install targets (P1-1, evolution review 2026-06-10).
if [ -n "$CMD" ]; then
  if ! cmd_mentions_control_plane "$CMD"; then
    # C-1: cannot statically prove the write target stays out of control plane
    # when the command builds it via variable expansion. Ask rather than allow.
    if cmd_var_built_write "$CMD"; then
      emit_ask "[integrity] このコマンドは変数で書込み先 path を組み立てています (例: \$D/lib/...) — 制御プレーン (hooks/scripts/.claude) を意図せず上書きする可能性があるため確認してください。"
      exit 0
    fi
    emit_allow
    exit 0
  fi
else
  # Extraction failed — fall back to the raw input. A control plane mention
  # anywhere then keeps the deny path active (fail-closed).
  if ! printf '%s' "$INPUT" | grep -qE "$CONTROL_PLANE"; then
    emit_allow
    exit 0
  fi
fi

# Chain/redirect operators that indicate compound or write commands. If present,
# the command is never eligible for allowlist or read-only pass-through.
# Includes > and >> to block "allowlisted_script > file" write bypass.
CHAIN_OPS='[;&|>]|\$\(|`'

# --- Allowlist check ---
# Only if the command has NO chaining operators, check if it is solely an
# allowlisted script invocation.
is_allowlisted() {
  local cmd="$1"
  # Reject if command contains chain operators.
  if printf '%s' "$cmd" | grep -qE "$CHAIN_OPS"; then
    return 1
  fi
  # Match: the command is exactly an allowlisted script call (with args).
  # record-test-result.py / run-test-strength-drill.py are evidence-recording
  # scripts the agent runs during normal project work (OBS-018). They only
  # append to the evidence log / write a drill report through their own logic,
  # never via a shell write the user cannot audit — and the no-chain guard above
  # still denies `record-test-result.py && evil` or a `> hooks/...` redirect.
  case "$cmd" in
    *scripts/check_framework_contract.py*|*scripts/check_status.py*|*scripts/update-gate.sh*|*scripts/record-test-result.py*|*scripts/run-test-strength-drill.py*)
      return 0
      ;;
  esac
  return 1
}

# OBS-017 catch-22: a fresh non-framework project must stage the installed
# framework files for its baseline commit, but `git add hooks scripts templates
# .claude CLAUDE.md docs` was denied outright. `git add` only STAGES — it does
# not modify control-plane file CONTENT (Edit/Write are still required, and a
# write redirect / chained mutation is excluded below) — so a plain staging
# command is routed to ASK (user confirms) rather than DENY. Excluded, so they
# keep denying (fail-closed):
#   - broad/forced staging: -A/--all/-f/--force (can stage tree-wide deletions
#     or force-add ignored secrets);
#   - any chain/redirect operator (a later mutation rides along);
#   - content-writing subcommands: only `add`/`stage` qualify, never `apply`.
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

# Check extracted command (already full fidelity).
if [ -n "$CMD" ] && is_allowlisted "$CMD"; then
  emit_allow
  exit 0
fi

# Check task_type: allow all if framework task.
TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
if [ "$TASK_TYPE" = "framework" ]; then
  emit_allow
  exit 0
fi

# --- Read-only command checks ---
# Allow read-only inspection of control plane (reading is not mutation). Two
# forms: (a) a single read-only command, (b) a `|`-only pipeline whose every
# segment is read-only. Both share the WRITE_INDICATORS source below.
CHECK_CMD="$CMD"
READ_ONLY_STARTS='^(cat|head|tail|less|more|grep|egrep|fgrep|rg|find|ls|wc|diff|file|stat|md5sum|sha256sum) '
# unlink/remove/rename/truncate require a call form `(` — bare substrings
# false-positived on read-only greps like `grep -r "remove" hooks/` (P3-4).
# Word-form indicators carry a left boundary (T5a v1.5.1): without it,
# `grep "confirm " hooks/x.sh` matched rm\s inside "confirm ". find's
# write-capable action flags are listed with the same boundary (T5b):
# `find hooks/ -exec dd of={} +` passed READ_ONLY_STARTS and (no `;`)
# CHAIN_OPS — a real write bypass. The boundary also keeps filename
# mentions (pre-exec.log) allowed, and concatenating after `|` avoids a
# leading `-` pattern, which BSD grep would parse as an option (rc=2 →
# the `!` negation would turn that crash into fail-open).
WRITE_INDICATORS='(^|[^A-Za-z0-9_])sed\s+-i|>\s*[^&]|>>\s|(^|[^A-Za-z0-9_])(tee|cp|mv|chmod|rm|mkdir|touch|install|ln)\s|write_text|write_bytes|open\(.*[wax]|\.write\(|Path\(.*\.write|(unlink|remove|rename|truncate)[[:space:]]*\(|(^|[^A-Za-z0-9_])-(exec|execdir|ok|okdir|delete|fprint0?|fprintf|fls)($|[^A-Za-z0-9_])'

# (a) single read-only command: no chain/redirect operators at all.
if [ -n "$CHECK_CMD" ] && ! printf '%s' "$CHECK_CMD" | grep -qE "$CHAIN_OPS"; then
  if printf '%s' "$CHECK_CMD" | grep -qE "$READ_ONLY_STARTS" && \
     ! printf '%s' "$CHECK_CMD" | grep -qE "$WRITE_INDICATORS"; then
    emit_allow
    exit 0
  fi
fi

# (b) read-only PIPELINE (OBS-003): a `|`-only pipe whose EVERY segment is an
# independently read-only command (read-only starter + no write indicator) is
# safe against control plane. Only `|` is tolerated — `;`, `&` (so `&&`), `||`,
# `<`, `>`, `$()`, `` ` `` all keep disqualifying (fail-closed), so a write
# segment (`... -exec rm`, `| tee`) or any redirect/cmdsub still denies.
if [ -n "$CHECK_CMD" ] && printf '%s' "$CHECK_CMD" | grep -q '|' \
   && ! printf '%s' "$CHECK_CMD" | grep -qE '[;&<>]|\$\(|`|\|\|'; then
  READ_ONLY_SEG='^[[:space:]]*(cat|head|tail|less|more|grep|egrep|fgrep|rg|find|ls|wc|diff|file|stat|md5sum|sha256sum)([[:space:]]|$)'
  pipe_all_ro=yes
  # `|| [ -n "$_seg" ]` processes the FINAL segment too: tr leaves the last
  # segment without a trailing newline, and a bare `read` returns non-zero
  # there and would SKIP it — which is exactly the dangerous tail of a pipe
  # (`| tee`, `| sh`). Dropping it would fail OPEN.
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
# Staging the framework files for a baseline commit is legitimate and is not a
# content write to control plane, so ASK rather than DENY.
if [ -n "$CMD" ] && is_bare_git_stage "$CMD"; then
  emit_ask "[integrity] git add で制御プレーン (hooks/scripts/.claude 等) を staging しようとしています。ファイル内容は変更しません（baseline コミット等の正当な操作の可能性）。意図を確認してください。"
  exit 0
fi

# Default: deny. Control plane path present, not allowlisted, not read-only.
REASON=$(printf '[integrity] Bash command referencing control plane path blocked during project work (task_type=%s). Use Edit/Write tools for auditable changes, or set task_type=framework.' "$TASK_TYPE")
emit_deny "$REASON"
exit 0
