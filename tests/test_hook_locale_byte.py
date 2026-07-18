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

    Returns (returncode, permission_decision, reason). The invalid byte is
    carried as a lone chr(0xFF) in the Python str, serialized with
    ensure_ascii=False, then UTF-8-encoded. Because chr(0xFF) UTF-8-encodes to
    the two bytes 0xC3 0xBF, we collapse that sequence back to a single raw 0xFF
    so a genuinely invalid UTF-8 byte lands on stdin (while valid multibyte text
    — Japanese etc. — stays intact as proper UTF-8). NOTE: callers must pass the
    invalid byte only as chr(0xFF); a legitimate U+00FF (ÿ) in a command string
    would also be collapsed — no current test uses ÿ.

    If stdout is empty or not JSON, the decision is the literal string "CRASH"
    (distinguishes a fail-open crash from a legitimate allow). `reason` is the
    permissionDecisionReason (empty string when absent) — used to prove WHICH
    code path fired (the main byte-wise path emits a specific pattern message,
    the [ -z "$CMD" ] raw fallback emits a generic "解析に失敗" message).
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
        return proc.returncode, "CRASH", ""
    try:
        obj = json.loads(out)
    except (ValueError, json.JSONDecodeError):
        return proc.returncode, "CRASH", ""
    hso = obj.get("hookSpecificOutput", {})
    decision = hso.get("permissionDecision")  # None == allow ({} empty object)
    reason = hso.get("permissionDecisionReason", "")
    return proc.returncode, decision, reason


# --- check-destructive.sh: destructive commands must ASK ---

# The check-destructive fallback ([ -z "$CMD" ]) emits this generic reason when
# extraction is blanked; the byte-wise MAIN path emits a specific pattern message
# ("再帰削除"). Asserting the main-path message pins that extraction SUCCEEDED
# byte-wise — this is what fails if `export LC_ALL=C` is moved back to AFTER
# extraction (mutation B: extraction drops -> fallback -> generic message), which
# a bare `decision == "ask"` assertion could NOT catch (both paths yield "ask").
_FALLBACK_MSG = "コマンドの解析に失敗しました"
_MAIN_RECURSIVE_MSG = "再帰削除"


def test_destructive_byte_in_comment_still_asks():
    # RED before fix: 0xFF in a trailing comment crashes `tr` -> rc=1, CRASH.
    # After fix: byte-wise extraction succeeds -> MAIN path -> recursive-delete msg.
    rc, decision, reason = run(DESTRUCTIVE, "rm -rf /realdir #" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"
    assert _MAIN_RECURSIVE_MSG in reason and _FALLBACK_MSG not in reason, (
        f"expected MAIN-path recursive-delete warning (proves byte-wise extraction), "
        f"got fallback/other reason: {reason!r}")


def test_destructive_trailing_byte_still_asks():
    # RED before fix. After fix: MAIN path (not the extraction-drop fallback).
    rc, decision, reason = run(DESTRUCTIVE, "rm -rf /realdir" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"
    assert _MAIN_RECURSIVE_MSG in reason and _FALLBACK_MSG not in reason, (
        f"expected MAIN-path recursive-delete warning (proves byte-wise extraction), "
        f"got fallback/other reason: {reason!r}")


def test_destructive_valid_multibyte_still_asks():
    # i18n non-regression (already PASS): valid UTF-8 multibyte must not crash.
    rc, decision, _ = run(DESTRUCTIVE, "rm -rf ~/プロジェクト")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"


def test_destructive_ascii_baseline_asks():
    # Non-regression baseline (already PASS).
    rc, decision, _ = run(DESTRUCTIVE, "rm -rf /realdir")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "ask", f"expected ask, got {decision!r}"


# --- check-secrets.sh: staging secrets must DENY ---

def test_secrets_real_env_with_trailing_byte_still_denies():
    # PRIMARY pin. RED before fix: staging the REAL .env with a stray byte
    # elsewhere on the line must still deny — but extraction drops (grep) and/or
    # `tr` crashes -> fallback ASKs / crash. This pin is mutation-sensitive: it
    # goes RED both if the export is deleted AND if it is moved to after
    # extraction (deny->ask downgrade), unlike the destructive pins.
    rc, decision, _ = run(SECRETS, "git add .env realfile" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"


def test_secrets_byte_after_env_still_denies():
    # Auxiliary (non-crash intent, but crashes/downgrades before fix).
    rc, decision, _ = run(SECRETS, "git add .env" + chr(0xFF))
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"


def test_secrets_valid_multibyte_still_denies():
    # i18n non-regression (already PASS): valid UTF-8 multibyte must not crash.
    rc, decision, _ = run(SECRETS, "git add テスト/.env")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"


def test_secrets_ascii_baseline_denies():
    # Non-regression baseline (already PASS).
    rc, decision, _ = run(SECRETS, "git add .env")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision == "deny", f"expected deny, got {decision!r}"


# --- Accepted residual (SF-016): C locale narrows [[:space:]]/\s to ASCII, so a
# NON-ASCII whitespace SEPARATOR (NBSP U+00A0, ideographic space U+3000) between
# command tokens no longer matches the moat pattern. This is NOT a real bypass:
# bash word-splits only on ASCII IFS whitespace, so `rm<NBSP>-rf` / `git<NBSP>add`
# is a SINGLE non-existent token ("command not found") — it never deletes or
# stages anything. Re-widening would spuriously match non-runnable non-commands
# and fight C-locale determinism, so we ACCEPT and PIN the residual here (blind
# 2nd review divergence, iter73). If a future change re-widens to match Unicode
# whitespace, these two tests flip to warn/deny and must be revisited. ---
NBSP = " "


def test_destructive_unicode_ws_separator_is_accepted_residual_allow():
    # `rm<NBSP>-rf /x` is a single non-existent token, not a runnable `rm -rf`.
    # Under C locale the [[:space:]] separator does not match → allow. Pinned.
    rc, decision, _ = run(DESTRUCTIVE, "rm" + NBSP + "-rf /realdir")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision is None, (
        f"accepted residual: NBSP-separated non-command should allow, got {decision!r}. "
        f"If this changed to 'ask', the whitespace class was re-widened — revisit SF-016.")


def test_secrets_unicode_ws_separator_is_accepted_residual_allow():
    # `git<NBSP>add .env`: `git<NBSP>add` is a single non-existent token, not a
    # runnable `git add`. Under C locale the git[[:space:]]+add pattern does not
    # match → allow. Pinned as accepted residual.
    rc, decision, _ = run(SECRETS, "git" + NBSP + "add .env")
    assert rc == 0, f"hook crashed (rc={rc})"
    assert decision is None, (
        f"accepted residual: NBSP-separated non-command should allow, got {decision!r}. "
        f"If this changed to 'deny', the whitespace class was re-widened — revisit SF-016.")
