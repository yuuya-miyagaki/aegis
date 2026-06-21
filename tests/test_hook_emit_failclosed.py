#!/usr/bin/env python3
"""iteration 34 A1: emit.sh を source する PreToolUse 判定 hook（hooks/check-*.sh）は
全て AEGIS_SAFETY_FALLBACK ブロックを持ち、lib 欠損時に fail-closed（明示 deny）で
あることを *不変条件* として固定する。

背景（外部レビュー E2 ＋ 検証で 3→6 hook に拡張）:
check-deploy-gate / check-deploy-mcp-gate / check-skill-gate / check-cron-gate /
check-client-info / check-tdd は emit.sh を直 source していたため、emit.sh 欠損時に
`set -euo pipefail` 下で空 stdout + rc!=0 ＝ Claude Code 仕様で fail-OPEN（ツール続行）
に落ちていた。deploy 2 hook は deny hook なので最重大（外部レビューは deploy-mcp のみ
指摘し、CLI 版 check-deploy-gate を取りこぼしていた）。

本テストは「emit.sh を使う check-*.sh は必ず fallback を持つ」を *動的に* 検査するので、
将来 emit.sh を使う新 hook を足しても fallback 漏れを自動で捕まえる（個別列挙に依存しない）。
"""
from __future__ import annotations

import pathlib
import unittest

from test_safety_lib_missing import _run_hook, _scratch_install

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
BEGIN_MARK = "# AEGIS_SAFETY_FALLBACK_BEGIN"

# A1 で新たに fallback を付与する対象（検証で確定・全て PreToolUse・mirror 無し）。
NEW_FALLBACK_HOOKS = [
    "check-deploy-gate.sh",
    "check-deploy-mcp-gate.sh",
    "check-skill-gate.sh",
    "check-cron-gate.sh",
    "check-client-info.sh",
    "check-tdd.sh",
]


def _emit_sourcing_check_hooks() -> list[pathlib.Path]:
    out = []
    for p in sorted(HOOKS.glob("check-*.sh")):
        if "lib/emit.sh" in p.read_text(encoding="utf-8"):
            out.append(p)
    return out


class TestEmitHookFailClosed(unittest.TestCase):

    def test_every_emit_sourcing_check_hook_has_fallback(self):
        """emit.sh を使う PreToolUse 判定 hook は AEGIS_SAFETY_FALLBACK 必須。"""
        offenders = [
            p.name
            for p in _emit_sourcing_check_hooks()
            if BEGIN_MARK not in p.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            offenders, [],
            f"emit.sh を source する check-*.sh は fallback 必須だが欠落: {offenders} "
            f"（emit.sh 欠損時に空 stdout+rc!=0 で fail-OPEN する）",
        )

    def test_known_targets_are_emit_sourcing(self):
        """glob 退行で対象が空になっても気付けるよう、既知の対象集合を固定確認。"""
        names = {p.name for p in _emit_sourcing_check_hooks()}
        for h in ["check-gate.sh"] + NEW_FALLBACK_HOOKS:
            self.assertIn(h, names, f"{h} は emit.sh を source しているはず")

    def test_new_gate_hooks_fail_closed_when_emit_missing(self):
        """emit.sh を消した install で、対象 6 hook が明示 deny + rc=0 を出す。"""
        payload = (
            '{"tool_name": "Bash", "tool_input": {"command": "ls"}}'
        )
        with _scratch_install() as tmp:
            root = pathlib.Path(tmp)
            (root / "hooks/lib/emit.sh").unlink()
            for hook in NEW_FALLBACK_HOOKS:
                with self.subTest(hook=hook):
                    rc, out, err = _run_hook(root, hook, payload)
                    self.assertEqual(
                        rc, 0,
                        f"{hook}: emit.sh 欠損で rc=0 の明示 deny が必要 "
                        f"(rc={rc}, stderr={err[:200]!r})",
                    )
                    self.assertIn(
                        '"permissionDecision":"deny"', out,
                        f"{hook}: 明示 deny を emit すべき, got {out[:200]!r}",
                    )


if __name__ == "__main__":
    unittest.main()
