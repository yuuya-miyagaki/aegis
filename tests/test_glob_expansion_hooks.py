#!/usr/bin/env python3
"""iter54 S-glob-1/2: hook 内の unquoted 変数ループが glob 展開で誤判定する穴。

S-glob-1 (check-destructive.sh): `for target in $SAFE_TARGETS` が glob 展開され、
cwd に build/dist 等しか無いと `rm -rf *` の `*` が safe-artifact 名に化けて
「安全成果物のみ」判定＝警告ゼロ（fail-open）。
S-glob-2 (check-gate.sh): normalize_target の `for seg in $p`（IFS=/）が
glob 展開され、cwd の単字ファイルに `[id]` がマッチして Next.js の
`app/[id]/page.tsx` を `app/d/page.tsx` 等へ歪める（誤判定リスク）。

修正 = 両ループを noglob（set -f）で囲む挙動保存リファクタ。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch(hook_name: str, libs: tuple[str, ...]) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\ngate_approvals:\n  plan: approved\n---\n",
        encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / hook_name, hooks_dir / hook_name)
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in libs:
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _run_hook(root: Path, hook_name: str, payload: dict, cwd: Path) -> str:
    r = subprocess.run(
        ["bash", str(root / "hooks" / hook_name)],
        input=json.dumps(payload), capture_output=True, text=True, cwd=str(cwd))
    return r.stdout


class TestDestructiveGlobExpansion(unittest.TestCase):
    """S-glob-1: build/dist しか無い cwd でも `rm -rf *` は警告される。"""

    LIBS = ("extract-input.sh", "emit.sh", "safety.sh", "patterns.sh")

    def test_rm_rf_star_in_artifact_only_cwd_asks(self):
        with _scratch("check-destructive.sh", self.LIBS) as name:
            root = Path(name)
            work = root / "work"
            work.mkdir()
            (work / "build").mkdir()
            (work / "dist").mkdir()
            out = _run_hook(root, "check-destructive.sh",
                            {"tool_name": "Bash",
                             "tool_input": {"command": "rm -rf *"}}, cwd=work)
            self.assertIn('"permissionDecision":"ask"', out,
                          f"rm -rf * must warn even in artifact-only cwd: {out[:200]!r}")

    def test_rm_rf_star_in_mixed_cwd_asks(self):
        with _scratch("check-destructive.sh", self.LIBS) as name:
            root = Path(name)
            work = root / "work"
            work.mkdir()
            (work / "src.py").write_text("x\n")
            out = _run_hook(root, "check-destructive.sh",
                            {"tool_name": "Bash",
                             "tool_input": {"command": "rm -rf *"}}, cwd=work)
            self.assertIn('"permissionDecision":"ask"', out)

    def test_literal_safe_targets_still_allowed(self):
        """挙動保存: リテラル safe-artifact 指定の rm は従来どおり allow。"""
        with _scratch("check-destructive.sh", self.LIBS) as name:
            root = Path(name)
            out = _run_hook(root, "check-destructive.sh",
                            {"tool_name": "Bash",
                             "tool_input": {"command": "rm -rf node_modules dist"}},
                            cwd=root)
            self.assertEqual(out.strip(), "{}",
                             f"literal safe targets must stay allowed: {out[:200]!r}")


class TestGateGlobExpansion(unittest.TestCase):
    """S-glob-2: normalize_target のセグメントが cwd の実ファイルへ glob 展開されない。"""

    LIBS = ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh")

    def test_bracket_segment_expanding_to_control_dir_not_denied(self):
        """RED の本丸: リテラル `[h]ooks/...`（Edit はパスをリテラル扱い＝CP ではない）が、
        cwd の実在 dir hooks/ に glob 展開されて誤 deny になっていた。"""
        with _scratch("check-gate.sh", self.LIBS) as name:
            root = Path(name)  # scratch root には hooks/ が実在＝glob 餌
            out = _run_hook(root, "check-gate.sh",
                            {"tool_name": "Edit",
                             "tool_input": {"file_path": "[h]ooks/lib/emit.sh"}},
                            cwd=root)
            self.assertEqual(out.strip(), "{}",
                             f"literal [h]ooks path must not be glob-expanded "
                             f"into a control-plane deny: {out[:200]!r}")

    def test_nextjs_bracket_route_allowed_with_bait(self):
        """挙動保存: `app/[id]/page.tsx` は cwd に単字ファイルの glob 餌があっても allow。"""
        with _scratch("check-gate.sh", self.LIBS) as name:
            root = Path(name)
            (root / "d").write_text("bait\n")
            (root / "i").write_text("bait\n")
            out = _run_hook(root, "check-gate.sh",
                            {"tool_name": "Edit",
                             "tool_input": {"file_path": "app/[id]/page.tsx"}},
                            cwd=root)
            self.assertEqual(out.strip(), "{}",
                             f"[id] route edit must be allowed: {out[:200]!r}")

    def test_real_control_path_still_denied(self):
        """挙動保存: glob 餌があっても hooks/ 配下の実パスは deny のまま。"""
        with _scratch("check-gate.sh", self.LIBS) as name:
            root = Path(name)
            (root / "d").write_text("bait\n")
            out = _run_hook(root, "check-gate.sh",
                            {"tool_name": "Edit",
                             "tool_input": {"file_path": "hooks/lib/emit.sh"}},
                            cwd=root)
            self.assertIn('"permissionDecision":"deny"', out)


if __name__ == "__main__":
    unittest.main()
