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
# Allowlist: update-gate.sh, check_status.py, check_framework_contract.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

# Load shared input extraction.
source "${SCRIPT_DIR}/lib/extract-input.sh"
source "${SCRIPT_DIR}/lib/emit.sh"

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

# True when the command references this project's control plane, including
# literal absolute paths under the project root (logical and physical forms —
# the boundary regex intentionally skips /-preceded names, so absolute paths
# need the fixed-string pass).
cmd_mentions_control_plane() {
  local cmd="$1" base
  if printf '%s' "$cmd" | grep -qE "$CONTROL_PLANE"; then
    return 0
  fi
  for base in "$ROOT" "$ROOT_REAL"; do
    if printf '%s' "$cmd" | grep -qF \
        -e "${base}/hooks/" -e "${base}/scripts/" -e "${base}/templates/"; then
      return 0
    fi
  done
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
  case "$cmd" in
    *scripts/check_framework_contract.py*|*scripts/check_status.py*|*scripts/update-gate.sh*)
      return 0
      ;;
  esac
  return 1
}

# Check extracted command (already full fidelity).
if [ -n "$CMD" ] && is_allowlisted "$CMD"; then
  emit_allow
  exit 0
fi

# Check task_type: allow all if framework task.
TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
if [ "$TASK_TYPE" = "framework" ]; then
  emit_allow
  exit 0
fi

# --- Read-only simple command check ---
# Allow purely read-only commands with no chaining and no write indicators.
CHECK_CMD="$CMD"
if [ -n "$CHECK_CMD" ]; then
  # Must not contain chain operators.
  if ! printf '%s' "$CHECK_CMD" | grep -qE "$CHAIN_OPS"; then
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
    if printf '%s' "$CHECK_CMD" | grep -qE "$READ_ONLY_STARTS" && \
       ! printf '%s' "$CHECK_CMD" | grep -qE "$WRITE_INDICATORS"; then
      emit_allow
      exit 0
    fi
  fi
fi

# Default: deny. Control plane path present, not allowlisted, not read-only.
REASON=$(printf '[integrity] Bash command referencing control plane path blocked during project work (task_type=%s). Use Edit/Write tools for auditable changes, or set task_type=framework.' "$TASK_TYPE")
emit_deny "$REASON"
exit 0
