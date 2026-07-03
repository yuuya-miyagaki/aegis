#!/usr/bin/env python3
"""iter55 P3a-c: 初見殺し deny/ask メッセージの改善（ドッグフード ゲート戦闘5・6・docs 摩擦）。

- 許可済みスクリプト＋チェーン演算子 → 「単体で実行せよ」の専用文言
- 汎用 deny → update-gate.sh / update-task.sh の案内（「Edit/Write を使え」単独の矛盾解消）
- git add で CP ファイル名 mention → 「git add docs/ 形式なら確認なし」のヒント
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch_root() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    (lib_dir / "scripts-manifest.tsv").symlink_to(
        ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
    return tmp


def _out(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _reason(out: str) -> str:
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


class TestMessages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_chained_allowlisted_script_gets_standalone_hint(self):
        out = _out(self.root, "bash scripts/update-gate.sh review approve | tail -20")
        self.assertIn('"deny"', out)
        self.assertIn("単体", _reason(out))

    def test_generic_deny_names_canonical_scripts(self):
        out = _out(self.root, "touch hooks/newfile.sh")
        self.assertIn('"deny"', out)
        reason = _reason(out)
        self.assertIn("update-gate.sh", reason)
        self.assertIn("update-task.sh", reason)

    def test_git_add_status_mention_hint(self):
        out = _out(self.root, "git add docs/STATUS.md")
        self.assertIn('"ask"', out)
        self.assertIn("git add docs/", _reason(out))


if __name__ == "__main__":
    unittest.main()
