#!/usr/bin/env python3
"""Contract + fail-closed tests for hooks/lib/emit.sh (the single emitter).

Run: python3 -m unittest tests.test_emit_lib -v
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMIT = ROOT / "hooks" / "lib" / "emit.sh"


def emit(call: str) -> tuple[int, object]:
    """Source emit.sh and run one function call. Returns (rc, parsed_or_raw)."""
    script = f'source "{EMIT}"\n{call}\n'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    out = r.stdout.strip()
    try:
        parsed = json.loads(out) if out else {}
    except json.JSONDecodeError:
        return r.returncode, out
    return r.returncode, parsed


class TestEmitContract(unittest.TestCase):
    def test_emit_allow_is_empty_object(self):
        rc, out = emit("emit_allow")
        self.assertEqual(rc, 0)
        self.assertEqual(out, {})

    def test_emit_deny_shape(self):
        rc, out = emit("emit_deny 'no edits allowed'")
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertEqual(hso["permissionDecisionReason"], "no edits allowed")

    def test_emit_ask_shape(self):
        rc, out = emit("emit_ask 'confirm please'")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_emit_block_shape(self):
        rc, out = emit("emit_block 'gate tampered'")
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"], "gate tampered")
        self.assertNotIn("permissionDecision", out)

    def test_emit_context_shape(self):
        rc, out = emit("emit_context 'SessionStart' 'hello world'")
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "SessionStart")
        self.assertEqual(hso["additionalContext"], "hello world")

    def test_emit_continue_false_shape(self):
        rc, out = emit("emit_continue_false 'plan gate pending'")
        self.assertEqual(out["continue"], False)
        self.assertEqual(out["stopReason"], "plan gate pending")
        self.assertNotIn("decision", out)

    def test_escaping_quotes_newlines_backslash(self):
        """Quotes, newline, backslash must produce valid JSON that round-trips."""
        rc, out = emit('emit_deny \'a "q" \\ and\nnewline\'')
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecisionReason"],
            'a "q" \\ and\nnewline',
        )


class TestEmitFailClosed(unittest.TestCase):
    """Round 1 #3 / Round 2 P1: the deny/block output path must NOT depend on any
    external interpreter (python3/jq/node), so it can never fail open when one is
    absent."""

    def test_emit_sh_has_no_interpreter_dependency(self):
        # Check EXECUTABLE code only — full-line comments may legitimately
        # discuss the rationale (e.g. "no python3/jq"). Strip lines whose first
        # non-space char is '#'.
        code = "\n".join(
            line
            for line in EMIT.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        for forbidden in ("python3", "python ", "jq ", "node "):
            self.assertNotIn(
                forbidden, code,
                f"emit.sh code must not invoke an external interpreter (found '{forbidden.strip()}'); "
                "the deny/block path must not fail open if it is missing",
            )

    def test_deny_valid_json_with_only_coreutils_path(self):
        """Even with a minimal PATH (no python3), emit_deny must still emit valid blocking JSON."""
        script = f'source "{EMIT}"\nemit_deny "blocked"\n'
        r = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin"},
        )
        out = json.loads(r.stdout.strip())
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
