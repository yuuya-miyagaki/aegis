#!/usr/bin/env python3
"""update-gate.sh の排他ロック（P3-3）。

並行セッションが同時に gate を更新すると lost update が起きる。
mkdir ロック（POSIX でアトミック・macOS に flock(1) が無い）で直列化し、
ロック保持中は STATUS.md 無書込のまま明示エラーで終了する。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_CONTENT = """---
framework: aegis
framework_version: "0.12.0"
project_name: test
mode: Dev
phase: brainstorm
task_type: feature
task_size: L
last_updated: "2026-01-01"
gate_approvals:
  client_ready_for_dev: approved
  brainstorm: pending
  plan: pending
  review: pending
  qa: pending
  security: approved
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: null
  plan: null
  spec: null
  review: null
  qa: null
  security: docs/qa-reports/security.md
  deploy: null
  translation: null
---
"""


class TestUpdateGateLock(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        docs = d / "docs"
        docs.mkdir()
        (docs / "STATUS.md").write_text(STATUS_CONTENT, encoding="utf-8")
        scripts = d / "scripts"
        scripts.mkdir()
        # Copy update-gate.sh so its ROOT resolves to the temp dir.
        shutil.copy2(ROOT / "scripts" / "update-gate.sh", scripts / "update-gate.sh")
        (scripts / "check_status.py").symlink_to(ROOT / "scripts" / "check_status.py")
        lib = d / "hooks" / "lib"
        lib.mkdir(parents=True)
        (lib / "frontmatter.sh").symlink_to(ROOT / "hooks" / "lib" / "frontmatter.sh")
        return d

    def _run(self, root: Path, gate: str, action: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(root / "scripts" / "update-gate.sh"), gate, action],
            capture_output=True, text=True, check=False, timeout=30,
        )

    def test_lock_held_fails_explicitly_without_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            before = (root / "docs" / "STATUS.md").read_text()
            r = self._run(root, "security", "reset")
            self.assertNotEqual(r.returncode, 0, "lock held → must fail")
            self.assertIn("lock", (r.stdout + r.stderr).lower(),
                          f"error must mention the lock: {r.stdout}{r.stderr}")
            self.assertEqual(before, (root / "docs" / "STATUS.md").read_text(),
                             "STATUS.md must not be written while locked")

    def test_lock_released_then_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r = self._run(root, "brainstorm", "approve")
            self.assertEqual(r.returncode, 0, f"unlocked approve must succeed: {r.stdout}{r.stderr}")
            status = (root / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: approved", status)
            self.assertFalse((root / ".claude" / ".gate-update.lock.d").exists(),
                             "lock dir must be released after a successful run")

    def test_reset_still_nulls_ref_single_pass(self):
        """1 パス書き込み化後も reset の ref null 化が維持される。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r = self._run(root, "security", "reset")
            self.assertEqual(r.returncode, 0, f"reset must succeed: {r.stdout}{r.stderr}")
            status = (root / "docs" / "STATUS.md").read_text()
            self.assertIn("security: pending", status)
            self.assertNotIn("docs/qa-reports/security.md", status,
                             "reset must null current_refs.security")

    def test_lock_acquired_before_current_read_structure(self):
        """構造固定（T3 v1.5.1）: ロック取得（mkdir）が CURRENT 読込より前。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertLess(
            text.index('mkdir "$LOCK_DIR"'), text.index("CURRENT=$("),
            "lock must be acquired before reading CURRENT (TOCTOU)")

    def test_lock_held_blocks_noop_approve(self):
        """ロック保持中は already-approved の no-op 承認も読込前に失敗する
        （旧実装は CURRENT を先に読んで exit 0 していた）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            (root / ".claude" / ".gate-update.lock.d").mkdir(parents=True)
            r = self._run(root, "security", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "lock held → must fail before CURRENT read")
            self.assertIn("lock", (r.stdout + r.stderr).lower())


if __name__ == "__main__":
    unittest.main()
