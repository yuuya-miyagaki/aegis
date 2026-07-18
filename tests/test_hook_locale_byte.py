"""iter73 locale/byte hardening — the two deny-side moat hooks must NOT crash
on invalid-UTF-8 stdin.

check-destructive.sh and check-secrets.sh run `tr '[:upper:]' '[:lower:]'` on
the Bash command under `set -euo pipefail`. When the command carries an invalid
UTF-8 byte (e.g. 0xFF) and the process locale is UTF-8, `tr` dies with
`Illegal byte sequence` -> the hook exits rc=1 with EMPTY stdout -> no decision
JSON -> the moat check is silently SKIPPED (fail-open).

This file pins the DESIRED post-fix behavior. The fix (Task 2/3, NOT this task)
adds `export LC_ALL=C LC_CTYPE=C LANG=C` right after command extraction so
`tr`/`grep` become byte-wise and never crash.

RED status: the crash-regression cases (1,2,5,6) FAIL now because the hook
crashes (rc=1, empty stdout -> decision "CRASH"); the i18n/ASCII non-regression
cases (3,4,7,8) already PASS. Every test runs under an explicit UTF-8 locale —
that is the whole point (the iter72 lesson: all-ASCII tests under any locale
missed this crash).
"""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
DESTRUCTIVE = ROOT / "hooks" / "check-destructive.sh"
SECRETS = ROOT / "hooks" / "check-secrets.sh"

# Explicit UTF-8 locale — under this locale `tr` crashes on invalid UTF-8 bytes.
_UTF8_ENV = dict(
    os.environ,
    LC_ALL="en_US.UTF-8",
    LC_CTYPE="en_US.UTF-8",
    LANG="en_US.UTF-8",
)


def run(hook, command_str):
    """Invoke a hook with a Bash command that may contain a lone 0xFF byte.

    Returns (returncode, permission_decision). The invalid byte is carried as a
    lone chr(0xFF) in the Python str, serialized with ensure_ascii=False, then
    UTF-8-encoded. Because chr(0xFF) UTF-8-encodes to the two bytes 0xC3 0xBF,
    we collapse that sequence back to a single raw 0xFF so a genuinely invalid
    UTF-8 byte lands on stdin (while valid multibyte text — Japanese etc. —
    stays intact as proper UTF-8). If stdout is empty or not JSON, the decision
    is the literal string "CRASH" (distinguishes a crash from allow).
    """
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": command_str}},
        ensure_ascii=False,
    ).encode("utf-8").replace(b"\xc3\xbf", b"\xff")
    proc = subprocess.run(
        ["bash", str(hook)],
        input=payload,
        capture_output=True,
        env=_UTF8_ENV,
    )
    out = proc.stdout.decode(errors="replace").strip()
    if not out:
        return proc.returncode, "CRASH"
    try:
        obj = json.loads(out)
    except (ValueError, json.JSONDecodeError):
        return proc.returncode, "CRASH"
    decision = obj.get("hookSpecificOutput", {}).get("permissionDecision")
    return proc.returncode, decision  # None == allow ({} empty object)


# --- check-destructive.sh: destructive commands must ASK ---

def test_destructive_byte_in_comment_still_asks():
    # RED now: 0xFF in a trailing comment crashes `tr` -> rc=1, decision CRASH.
    rc, decision = run(DESTRUCTIVE, "rm -rf /realdir #" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"


def test_destructive_trailing_byte_still_asks():
    # RED now.
    rc, decision = run(DESTRUCTIVE, "rm -rf /realdir" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"


def test_destructive_valid_multibyte_still_asks():
    # i18n non-regression (already PASS): valid UTF-8 multibyte must not crash.
    rc, decision = run(DESTRUCTIVE, "rm -rf ~/プロジェクト")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"


def test_destructive_ascii_baseline_asks():
    # Non-regression baseline (already PASS).
    rc, decision = run(DESTRUCTIVE, "rm -rf /realdir")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"


# --- check-secrets.sh: staging secrets must DENY ---

def test_secrets_real_env_with_trailing_byte_still_denies():
    # PRIMARY pin. RED now: staging the REAL .env with a stray byte elsewhere on
    # the line must still deny — but `tr` crashes -> fail-open.
    rc, decision = run(SECRETS, "git add .env realfile" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"


def test_secrets_byte_after_env_still_denies():
    # Auxiliary (non-crash intent, but crashes now). RED now.
    rc, decision = run(SECRETS, "git add .env" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"


def test_secrets_valid_multibyte_still_denies():
    # i18n non-regression (already PASS): valid UTF-8 multibyte must not crash.
    rc, decision = run(SECRETS, "git add テスト/.env")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"


def test_secrets_ascii_baseline_denies():
    # Non-regression baseline (already PASS).
    rc, decision = run(SECRETS, "git add .env")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"
