#!/usr/bin/env bash
# PostToolUseFailure (Bash) ADVISORY: when a Bash command failed with an
# EACCES / "Permission denied" on a locked control-plane path, explain that
# this is the aegis OS-lock (the primary moat) BEFORE the agent reaches for
# `chmod +w` self-repair — which would turn a caught accident into an uncaught
# one (rev.2 撤回理由②の恒久対策).
#
# Fires only when BOTH signals hold:
#   (1) tool_response.stderr contains permission-denied / EACCES, AND
#   (2) tool_input.command mentions a LOCKED control-plane path.
# Requiring both avoids false positives from benign non-zero exits (a
# grep-no-match on hooks/, a failing test that prints a hooks/ path).
#
# Pure advisory: never blocks; every failure path fails OPEN (exit 0, no
# output). Unlike the deny hooks, python3 parsing is fine here — if python3 is
# absent the hook simply stays silent, which is the desired safe direction.
set -u

INPUT=$(cat 2>/dev/null || true)
[ -n "$INPUT" ] || exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || exit 0

# Do the AND-matching inside python3 (bash vars cannot hold NUL, so field-
# splitting stderr/command in the shell is fragile). Prints "FIRE" only when
# BOTH signals hold; empty otherwise. Any parse error => empty => silent.
#   (1) stderr matches permission-denied / EACCES / EPERM
#   (2) command mentions a LOCKED control-plane path — keyed off the command,
#       NOT the whole envelope (transcript_path always carries
#       ~/.claude/projects/, which would false-fire).
_verdict=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, re
try:
    d = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
stderr = (d.get("tool_response") or {}).get("stderr") or ""
cmd = (d.get("tool_input") or {}).get("command") or ""
deny = re.search(r"permission denied|operation not permitted|eacces|eperm", stderr, re.I)
cp = re.search(r"(^|[^A-Za-z0-9_./-])(\./)*(hooks|scripts|templates)/|(^|[^A-Za-z0-9_./-])CLAUDE\.md|\.claude/(rules|skills|commands|agents)/", cmd)
sys.stdout.write("FIRE" if (deny and cp) else "")
' 2>/dev/null) || exit 0

[ "$_verdict" = "FIRE" ] || exit 0

source "${SCRIPT_DIR}/lib/emit.sh" 2>/dev/null || exit 0
emit_context PostToolUseFailure "[oslock] 直前の Permission denied は aegis の OS-lock（主 moat）による control-plane 保護の可能性があります。chmod/chflags での解錠は行わないでください。framework ファイルの変更が正当な作業なら scripts/update-task.sh --type framework で task_type を切り替え、セッションを再開すると自動で unlock されます。"
exit 0
