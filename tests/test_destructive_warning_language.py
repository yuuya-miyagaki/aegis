#!/usr/bin/env python3
"""iter53: destructive-command permission prompts must speak Japanese.

The hooks that gate destructive commands (rm -r, DROP TABLE, git push --force,
dd, mkfs, ...) emit their `permissionDecisionReason` to the user's confirmation
UI. Every other Aegis prompt is Japanese, but these danger warnings were
English — the highest-stakes prompt in the wrong language for the target
operator. This pins the warnings to Japanese and guards against future English
regressions.

Three layers:
  1. drift guard — every WARN array element in patterns.sh contains Japanese
  2. inline rm -r warning fires in Japanese (behavioral)
  3. truncated-payload fallbacks (destructive + secrets) fire in Japanese

Run: python3 -m unittest tests.test_destructive_warning_language -v
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "hooks" / "lib" / "patterns.sh"
HOOK_DESTRUCTIVE = ROOT / "hooks" / "check-destructive.sh"
HOOK_SECRETS = ROOT / "hooks" / "check-secrets.sh"

# LANG is stripped (env={"PATH":...}) to match the existing hook tests; decode
# stdout explicitly as UTF-8 so Japanese bytes survive on ASCII-locale hosts.
_ENV = {"PATH": "/usr/bin:/bin"}


def _has_japanese(s: str) -> bool:
    # >=1 Japanese char is enough: this catches a fully-English regression (the
    # actual failure mode) without false-positiving on legit ASCII command
    # tokens (rm -r, git push --force). A half-translated string still passes —
    # accepted, since the guard's job is "no English-only warnings", not prose QA.
    return any(
        "぀" <= c <= "ゟ"  # Hiragana
        or "゠" <= c <= "ヿ"  # Katakana
        or "一" <= c <= "鿿"  # CJK Unified Ideographs
        for c in s
    )


def _bash_array(name: str) -> list[str]:
    script = f'source "{PATTERNS}"; printf "%s\\n" "${{{name}[@]}}"'
    r = subprocess.run(["bash", "-c", script], capture_output=True,
                       encoding="utf-8", env=_ENV)
    assert r.returncode == 0, f"sourcing {name} failed: {r.stderr!r}"
    return [ln for ln in r.stdout.split("\n") if ln != ""]


def _run(hook: Path, payload: str) -> dict:
    r = subprocess.run(["bash", str(hook)], input=payload, capture_output=True,
                       encoding="utf-8", env=_ENV)
    return json.loads(r.stdout.strip())


def _reason(out: dict) -> str:
    return out["hookSpecificOutput"]["permissionDecisionReason"]


def _decision(out: dict) -> str:
    return out["hookSpecificOutput"]["permissionDecision"]


class TestWarnArraysAreJapanese(unittest.TestCase):
    """Layer 1: drift guard — future English additions fail here."""

    def test_lower_warn_all_japanese(self):
        warns = _bash_array("AEGIS_DESTRUCTIVE_LOWER_WARN")
        self.assertEqual(len(warns), 2, "expected 2 LOWER warnings")
        for w in warns:
            with self.subTest(warn=w):
                self.assertTrue(_has_japanese(w), f"English destructive WARN: {w!r}")

    def test_cmd_warn_all_japanese(self):
        warns = _bash_array("AEGIS_DESTRUCTIVE_CMD_WARN")
        self.assertEqual(len(warns), 16, "expected 16 CMD warnings")
        for w in warns:
            with self.subTest(warn=w):
                self.assertTrue(_has_japanese(w), f"English destructive WARN: {w!r}")

    def test_warn_regex_parity(self):
        # Every gated pattern MUST have a parallel warning: check-destructive.sh
        # indexes WARN by the REGEX index. A new REGEX without a matching WARN
        # would fire "[careful] " with no danger text — and neither the JP guard
        # nor a hardcoded count catches it. Pin parity to the real invariant.
        self.assertEqual(len(_bash_array("AEGIS_DESTRUCTIVE_LOWER_WARN")),
                         len(_bash_array("AEGIS_DESTRUCTIVE_LOWER_REGEX")),
                         "LOWER WARN/REGEX count mismatch")
        self.assertEqual(len(_bash_array("AEGIS_DESTRUCTIVE_CMD_WARN")),
                         len(_bash_array("AEGIS_DESTRUCTIVE_CMD_REGEX")),
                         "CMD WARN/REGEX count mismatch")


class TestInlineRecursiveDeleteJapanese(unittest.TestCase):
    """Layer 2: the inline rm -r/-R warning fires in Japanese."""

    def test_recursive_delete_reason_japanese(self):
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": "rm -rf /important"}})
        out = _run(HOOK_DESTRUCTIVE, payload)
        self.assertEqual(_decision(out), "ask")
        self.assertTrue(_has_japanese(_reason(out)),
                        f"English inline rm -r WARN: {_reason(out)!r}")
        # Distinctive token pins this to the inline recursive-delete warning,
        # not some other ask path firing by accident (false GREEN).
        self.assertIn("再帰削除", _reason(out))


class TestTruncatedFallbacksJapanese(unittest.TestCase):
    """Layer 3: extraction-failure fallbacks fire in Japanese (behavioral)."""

    def test_destructive_fallback_japanese(self):
        # Truncated JSON: extraction fails, raw payload still matches rm -R.
        out = _run(HOOK_DESTRUCTIVE,
                   '{"tool_name":"Bash","tool_input":{"command":"rm -Rf /important')
        self.assertEqual(_decision(out), "ask")
        self.assertTrue(_has_japanese(_reason(out)),
                        f"English destructive fallback: {_reason(out)!r}")
        self.assertIn("破壊的コマンド", _reason(out))

    def test_secrets_fallback_japanese(self):
        # Truncated JSON: extraction fails, raw payload still references .env.
        out = _run(HOOK_SECRETS,
                   '{"tool_name":"Bash","tool_input":{"command":"cat .env')
        self.assertEqual(_decision(out), "ask")
        self.assertTrue(_has_japanese(_reason(out)),
                        f"English secrets fallback: {_reason(out)!r}")
        self.assertIn("秘密情報", _reason(out))


if __name__ == "__main__":
    unittest.main()
