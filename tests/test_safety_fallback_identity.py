#!/usr/bin/env python3
"""K-5 (v1.6.2) ＋ iteration 34 A1: emit.sh を使う 12 個の PreToolUse 判定 hook の
safety.sh fallback ブロックが byte-identical であることを契約化する（grill 致命 5）。

safety.sh が source できないという最悪ケースで明示 DENY を出すための
inline fallback は、全 12 hook で SHA256 一致が義務。drift が起きると JSON
スキーマや reason 文字列が分岐し、将来の Claude Code 仕様変更（例:
hookEventName → hook_event_name）で 12 箇所同期漏れが起きる。

各 hook は AEGIS_SAFETY_FALLBACK_BEGIN / END マーカーで囲んだ厳密
ブロックを持ち、本テストがその SHA256 一致を強制する。
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

FALLBACK_HOOKS = [
    # iter57: check-control-plane.sh 退役 → 残余静的ガード check-runtime-state.sh
    # が同一の deny-side fallback ブロックを継承（corruption 時 deny に倒す）。
    "check-runtime-state.sh",
    "check-secrets.sh",
    "check-destructive.sh",
    "check-gate.sh",
    "check-task-completed.sh",
    "check-task-created.sh",
    # iteration 34 A1: emit.sh を使う残りの PreToolUse 判定 hook（corruption 時 deny に倒す）
    "check-deploy-gate.sh",
    "check-deploy-mcp-gate.sh",
    "check-skill-gate.sh",
    "check-cron-gate.sh",
    "check-client-info.sh",
    "check-tdd.sh",
]

BEGIN_MARK = "# AEGIS_SAFETY_FALLBACK_BEGIN"
END_MARK = "# AEGIS_SAFETY_FALLBACK_END"


def _extract_fallback(path: pathlib.Path) -> str:
    text = path.read_text(encoding="utf-8")
    pattern = (
        re.escape(BEGIN_MARK)
        + r"[ \t]*\n(.*?)\n[ \t]*"
        + re.escape(END_MARK)
    )
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        raise AssertionError(
            f"fallback markers missing in {path.name}: looking for "
            f"{BEGIN_MARK!r} and {END_MARK!r}"
        )
    return m.group(1)


class TestSafetyFallbackIdentity(unittest.TestCase):

    def test_all_deny_hooks_have_identical_fallback(self):
        hooks_dir = ROOT / "hooks"
        blocks = []
        for h in FALLBACK_HOOKS:
            blocks.append(_extract_fallback(hooks_dir / h))
        digests = {hashlib.sha256(b.encode("utf-8")).hexdigest() for b in blocks}
        self.assertEqual(
            len(digests), 1,
            f"safety fallback block drift across {FALLBACK_HOOKS}: {digests}"
        )

    def test_fallback_has_no_dynamic_substitution(self):
        """fallback は静的固定文字列。JSON injection 防止のため、JSON
        ペイロード本体に %s や $VAR / ${VAR} 等の動的置換を含めてはいけない。"""
        block = _extract_fallback(ROOT / "hooks" / FALLBACK_HOOKS[0])
        # JSON ペイロードを抽出: 最初の '{' で始まる単一クォート文字列
        # （printf format string '%s\n' は { を含まないので素通り）
        m = re.search(r"'(\{[^']*\})'", block)
        self.assertIsNotNone(
            m, f"fallback must contain a single-quoted JSON literal: {block!r}"
        )
        payload = m.group(1)
        # ペイロード本体には %s も $ も含めない
        self.assertNotIn(
            "%s", payload,
            f"JSON payload must not contain %s: {payload!r}"
        )
        self.assertNotIn(
            "$", payload,
            f"JSON payload must not contain $ substitution: {payload!r}"
        )

    def test_fallback_emits_deny_decision(self):
        """fallback JSON が確実に deny を吐く形であること。"""
        block = _extract_fallback(ROOT / "hooks" / FALLBACK_HOOKS[0])
        self.assertIn(
            '"permissionDecision":"deny"', block,
            f"fallback must emit permissionDecision deny: {block!r}",
        )

    def test_fallback_exits_zero(self):
        """fallback は exit 0（明示 deny。crash で fail-open しない）。"""
        block = _extract_fallback(ROOT / "hooks" / FALLBACK_HOOKS[0])
        self.assertIn(
            "exit 0", block,
            f"fallback must exit 0 (not crash): {block!r}",
        )


if __name__ == "__main__":
    unittest.main()
