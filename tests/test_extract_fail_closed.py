#!/usr/bin/env python3
"""R3: truncated/unparseable stdin must fail-closed (ask) when the raw payload
still matches a destructive/secret pattern, instead of silently allowing.

CC emits well-formed JSON, so this is a defense-in-depth fallback for the rare
case where command extraction fails on truncated/oversized stdin.

Run: python3 -m unittest tests.test_extract_fail_closed -v
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_hook(hook: str, payload: str) -> str:
    r = subprocess.run(["bash", str(ROOT / "hooks" / hook)],
                       input=payload, capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    return r.stdout.strip()


class TestExtractFailClosed(unittest.TestCase):
    def test_truncated_destructive_asks(self):
        # command 値が閉じ引用符なしで切断 → extract_command が空
        out = run_hook("check-destructive.sh",
                       '{"tool_name":"Bash","tool_input":{"command":"git push --force origin main')
        self.assertIn('"permissionDecision":"ask"', out)

    def test_truncated_benign_allows(self):
        out = run_hook("check-destructive.sh",
                       '{"tool_name":"Bash","tool_input":{"command":"echo hello world')
        self.assertEqual(json.loads(out), {})

    def test_truncated_secret_asks(self):
        out = run_hook("check-secrets.sh",
                       '{"tool_name":"Bash","tool_input":{"command":"git add .env')
        self.assertIn('"permissionDecision":"ask"', out)

    # --- 正常系回帰: フォールバックが通常経路に干渉しない ---
    def test_normal_recursive_delete_still_asks(self):
        out = run_hook("check-destructive.sh",
                       '{"tool_name":"Bash","tool_input":{"command":"rm -rf /important/data"}}')
        self.assertIn('"permissionDecision":"ask"', out)

    def test_normal_benign_allows(self):
        out = run_hook("check-destructive.sh",
                       '{"tool_name":"Bash","tool_input":{"command":"echo hi"}}')
        self.assertEqual(json.loads(out), {})

    def test_well_formed_safe_env_variant_allows(self):
        # .env.example は秘密でない（正常 JSON・抽出成功経路）
        out = run_hook("check-secrets.sh",
                       '{"tool_name":"Bash","tool_input":{"command":"git add .env.example"}}')
        self.assertEqual(json.loads(out), {})


if __name__ == "__main__":
    unittest.main()
