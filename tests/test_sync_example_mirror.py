#!/usr/bin/env python3
"""scripts/sync_example_mirror.py の単体テスト（P3-A / M1）。

実マニフェスト（check_reference_drift の MIRROR_DIRS/MIRROR_FILES/
MIRROR_ALLOWLIST）を使い、fake root + example レイアウトに対して sync_mirror の
copy / allowlist skip / stale 除去（DIRS と FILES の両方）/ mode 保持 / 冪等 /
分岐ファイル不可侵を検証する。実 repo は変更しない。"""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_example_mirror import sync_mirror  # noqa: E402


def _write(p: Path, text: str, *, executable: bool = False) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if executable:
        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class TestSyncMirror(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        # root 側の制御ファイル（MIRROR_DIRS + MIRROR_FILES）
        _write(d / "hooks" / "foo.sh", "#!/bin/sh\necho NEW\n", executable=True)
        _write(d / ".claude" / "skills" / "x" / "SKILL.md", "---\nname: x\n---\n")
        _write(d / ".claude" / "commands" / "validate.md", "ROOT validate\n")
        _write(d / "scripts" / "check_status.py", "# root check_status\n")
        # example 側
        ex = d / "examples" / "minimal-project"
        _write(ex / "CLAUDE.md", "PROJECT-SPECIFIC\n")  # 分岐（MIRROR_DIRS 外）
        _write(ex / ".claude" / "commands" / "validate.md", "EXAMPLE validate\n")  # allowlist
        _write(ex / "hooks" / "stale.sh", "#!/bin/sh\necho OLD\n")  # DIRS stale
        _write(ex / "scripts" / "status_doctor.py", "# stale doctor\n")  # FILES stale
        return d

    def test_copies_mirror_file_byte_identical(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            src = (root / "hooks" / "foo.sh").read_bytes()
            dst = (root / "examples" / "minimal-project" / "hooks" / "foo.sh").read_bytes()
            self.assertEqual(src, dst)

    def test_copies_mirror_explicit_file(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            dst = root / "examples" / "minimal-project" / "scripts" / "check_status.py"
            self.assertEqual(dst.read_text(), "# root check_status\n")

    def test_preserves_executable_mode(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            dst = root / "examples" / "minimal-project" / "hooks" / "foo.sh"
            self.assertTrue(os.access(dst, os.X_OK), "executable bit must be preserved")

    def test_allowlist_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            v = (root / "examples" / "minimal-project" / ".claude"
                 / "commands" / "validate.md").read_text()
            self.assertEqual(v, "EXAMPLE validate\n", "allowlisted file must not be overwritten")

    def test_stale_dir_file_removed(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            stale = root / "examples" / "minimal-project" / "hooks" / "stale.sh"
            self.assertFalse(stale.exists(), "stale MIRROR_DIRS file (absent in root) must be removed")

    def test_stale_explicit_file_removed(self):
        # grill 要検討1: MIRROR_FILES の stale も対称に除去
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            stale = root / "examples" / "minimal-project" / "scripts" / "status_doctor.py"
            self.assertFalse(stale.exists(),
                             "stale MIRROR_FILES copy (absent in root) must be removed")

    def test_divergent_file_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            cm = (root / "examples" / "minimal-project" / "CLAUDE.md").read_text()
            self.assertEqual(cm, "PROJECT-SPECIFIC\n", "MIRROR_DIRS 外の分岐ファイルは不可侵")

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            ex = root / "examples"
            snap1 = {p.relative_to(root).as_posix(): p.read_bytes()
                     for p in ex.rglob("*") if p.is_file()}
            sync_mirror(root)
            snap2 = {p.relative_to(root).as_posix(): p.read_bytes()
                     for p in ex.rglob("*") if p.is_file()}
            self.assertEqual(snap1, snap2, "2回実行で同一内容・同一集合（冪等）")


if __name__ == "__main__":
    unittest.main()
