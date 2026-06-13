#!/usr/bin/env python3
"""R4: recursive delete must prompt regardless of -r / -R case.

The destructive hook previously matched only a trailing lowercase `r`
(`-[a-zA-Z]*r`), so capital-R recursive deletes (`rm -R`, `rm -Rf`; common on
BSD/macOS) bypassed the gate and ran without a confirmation prompt. This pins
case-insensitive coverage on both the main path and the truncated-stdin
fallback, without regressing the safe-build-artifact exception.

Run: python3 -m unittest tests.test_destructive_recursive -v
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-destructive.sh"


def run(cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(["bash", str(HOOK)], input=payload,
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    return r.stdout.strip()


def run_raw(payload: str) -> str:
    r = subprocess.run(["bash", str(HOOK)], input=payload,
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    return r.stdout.strip()


class TestRecursiveDeleteCaseInsensitive(unittest.TestCase):
    def test_recursive_variants_ask(self):
        for cmd in ("rm -r /important",
                    "rm -R /important",
                    "rm -rf /important",
                    "rm -Rf /important",
                    "rm -fR /important",
                    "rm --recursive /important"):
            with self.subTest(cmd=cmd):
                self.assertIn('"permissionDecision":"ask"', run(cmd),
                              f"recursive delete not gated: {cmd!r}")

    def test_safe_build_artifact_still_allows(self):
        # build-artifact recursive deletes are intentionally allowed
        for cmd in ("rm -Rf node_modules", "rm -rf dist", "rm -R .next"):
            with self.subTest(cmd=cmd):
                self.assertEqual(json.loads(run(cmd)), {},
                                 f"safe target should allow: {cmd!r}")

    def test_non_recursive_and_benign(self):
        self.assertEqual(json.loads(run("echo hi")), {})
        # plain non-recursive rm of a single file is not the recursive gate's job
        self.assertEqual(json.loads(run("rm file.txt")), {})

    def test_truncated_capital_r_fallback_asks(self):
        out = run_raw('{"tool_name":"Bash","tool_input":{"command":"rm -Rf /important')
        self.assertIn('"permissionDecision":"ask"', out)


if __name__ == "__main__":
    unittest.main()
