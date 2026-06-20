#!/usr/bin/env python3
"""K-6 (v1.6.2): 全 PreToolUse hook が `timeout` を宣言していることの契約。

第6回 Phase A F-02: hook の timeout 宣言が settings に皆無なため、
長時間 hook が native 既定（~60s）で打ち切られると exit 124/137 → 空 stdout
→ Claude Code が fail-open。timeout を明示宣言して非標準環境でも fail-safe。

timeout 値の根拠は docs/perf-baseline.md。
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

TEMPLATES = [
    ROOT / "templates" / "hooks.template.json",
]

# K-6: PreToolUse hooks must declare a timeout.
# Bounds (per docs/perf-baseline.md): lower 5s, upper 60s.
TIMEOUT_MIN_SEC = 5
TIMEOUT_MAX_SEC = 60


def _hooks_in_settings(path: pathlib.Path) -> list[dict]:
    """settings JSON から全 hook entry をフラットに展開して返す。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for event_name, entries in data.get("hooks", {}).items():
        for entry in entries:
            matcher = entry.get("matcher", "")
            for sub in entry.get("hooks", []):
                sub_with_meta = dict(sub)
                sub_with_meta["_event"] = event_name
                sub_with_meta["_matcher"] = matcher
                out.append(sub_with_meta)
    return out


class TestPreToolUseTimeouts(unittest.TestCase):

    def test_all_pretooluse_hooks_have_timeout(self):
        """PreToolUse 全 hook に timeout フィールドが宣言されている"""
        for path in TEMPLATES:
            with self.subTest(template=str(path)):
                for hook in _hooks_in_settings(path):
                    if hook["_event"] != "PreToolUse":
                        continue
                    self.assertIn(
                        "timeout", hook,
                        f"{path.name}: PreToolUse hook missing timeout: "
                        f"matcher={hook['_matcher']!r} cmd={hook.get('command', '')[:80]!r}"
                    )

    def test_timeout_is_int_in_bounds(self):
        """timeout が整数で 5〜60 秒の範囲内"""
        for path in TEMPLATES:
            with self.subTest(template=str(path)):
                for hook in _hooks_in_settings(path):
                    if "timeout" not in hook:
                        continue
                    t = hook["timeout"]
                    self.assertIsInstance(
                        t, int,
                        f"{path.name}: timeout must be int, got {type(t).__name__}"
                    )
                    self.assertGreaterEqual(
                        t, TIMEOUT_MIN_SEC,
                        f"{path.name}: timeout < {TIMEOUT_MIN_SEC}s: {t}"
                    )
                    self.assertLessEqual(
                        t, TIMEOUT_MAX_SEC,
                        f"{path.name}: timeout > {TIMEOUT_MAX_SEC}s: {t}"
                    )


if __name__ == "__main__":
    unittest.main()
