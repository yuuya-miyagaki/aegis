#!/usr/bin/env python3
"""update-gate.sh の排他ロック（P3-3）。

並行セッションが同時に gate を更新すると lost update が起きる。
mkdir ロック（POSIX でアトミック・macOS に flock(1) が無い）で直列化し、
ロック保持中は STATUS.md 無書込のまま明示エラーで終了する。
"""
from __future__ import annotations

import os
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

    def _dead_pid(self) -> int:
        """確実に死んでいる PID を得る（直近終了の子プロセス）。"""
        p = subprocess.Popen(["true"])
        p.wait()
        return p.pid

    def test_stale_lock_with_dead_pid_is_reclaimed(self):
        """死んだ PID の pid ファイルを持つ stale lock は自動回収され、
        後続の承認が成功する（T4 v1.5.1）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text(str(self._dead_pid()), encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertEqual(r.returncode, 0,
                             f"dead-pid stale lock must be reclaimed: {r.stdout}{r.stderr}")
            self.assertIn("brainstorm: approved",
                          (root / "docs" / "STATUS.md").read_text())
            self.assertFalse(lock.exists(), "reclaimed lock must be released after run")

    def test_lock_with_live_pid_is_not_reclaimed(self):
        """生きた PID（テストランナー自身）を持つロックは回収されず、
        文言が pid を含む「並行実行中」系になる（🟡-4）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text(str(os.getpid()), encoding="utf-8")
            before = (root / "docs" / "STATUS.md").read_text()
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0, "live-pid lock must not be reclaimed")
            self.assertIn(str(os.getpid()), r.stdout + r.stderr,
                          "error must mention the live holder pid")
            self.assertTrue(lock.exists(), "live lock must be left intact")
            self.assertEqual(before, (root / "docs" / "STATUS.md").read_text())

    def test_lock_with_garbage_pid_is_not_reclaimed(self):
        """数字以外の pid 内容は判別不能 → 回収しない（fail-closed）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text("not-a-pid", encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0, "garbage pid must not be reclaimed")
            self.assertTrue(lock.exists())

    def test_orphan_claim_dead_claimer_restored_and_reclaimed(self):
        """claimer 死亡の孤児 claim は pid に復元され、既存 dead-pid 回収路に
        合流して後続承認が成功する（T4a v1.5.2、claim-mv クラッシュ窓の根治）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            claimer = self._dead_pid()
            holder = self._dead_pid()
            (lock / f"pid.claim.{claimer}").write_text(str(holder),
                                                       encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertEqual(r.returncode, 0,
                             f"orphan claim must be restored+reclaimed: "
                             f"{r.stdout}{r.stderr}")
            self.assertIn("brainstorm: approved",
                          (root / "docs" / "STATUS.md").read_text())
            self.assertFalse(lock.exists(),
                             "restored lock must be released after run")

    def test_orphan_claim_live_claimer_left_alone(self):
        """claimer 生存中の claim は復元しない（fail-closed・guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            claim = lock / f"pid.claim.{os.getpid()}"
            claim.write_text(str(self._dead_pid()), encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "live claimer must not be disturbed")
            self.assertTrue(claim.exists(), "live claim must be left intact")

    def _age(self, p: Path) -> None:
        """採用 age-gate（-mmin +1 ＝実効 2 分超）より古い mtime に偽装する。
        必ず dir へのエントリ追加が終わってから呼ぶこと（追加で mtime が戻る）。"""
        subprocess.run(["touch", "-t", "202601010000", str(p)], check=True)

    def test_pidless_old_lock_is_adopted(self):
        """pid なし・実効 2 分超のロックは O_EXCL 採用で引き取られ、
        承認が成功して通常解放される（T4b v1.5.2）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            self._age(lock)
            r = self._run(root, "brainstorm", "approve")
            self.assertEqual(r.returncode, 0,
                             f"aged pid-less lock must be adopted: "
                             f"{r.stdout}{r.stderr}")
            self.assertIn("brainstorm: approved",
                          (root / "docs" / "STATUS.md").read_text())
            self.assertFalse(lock.exists(),
                             "adopted lock must be released after run")

    def test_pidless_young_lock_is_not_adopted(self):
        """若い pid なし dir（mkdir〜pid 書込の正常な瞬間）は採用しない
        （guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "young pid-less dir must not be adopted")
            self.assertTrue(lock.exists())

    def test_old_lock_with_live_claim_is_not_adopted(self):
        """claim が存在する dir は採用対象外（T4a の管轄、guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            claim = lock / f"pid.claim.{os.getpid()}"
            claim.write_text("1", encoding="utf-8")
            self._age(lock)
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(claim.exists())

    def test_empty_pid_old_lock_stays_fail_closed(self):
        """空 pid ファイルは O_EXCL を構造的に失敗させ、採用されない＝
        従来どおり手動削除案内（fail-closed・guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text("", encoding="utf-8")
            self._age(lock)
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "empty pid must stay manual-removal")
            self.assertTrue(lock.exists())

    def _spawn(self, root: Path, gate: str, action: str) -> subprocess.Popen:
        return subprocess.Popen(
            ["bash", str(root / "scripts" / "update-gate.sh"), gate, action],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_wait_window_is_50_iterations(self):
        """構造固定（T5 v1.5.2）: 待機ループは 50 回 × 0.2s = 10s。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertIn("for _ in {1..50}; do", text)

    def test_live_contention_both_succeed(self):
        """高速パス（approve/reset）の実競合 2 contender: 敗者も勝者完了後に
        10s 窓内で自力取得し両方成功する（T5。v1.5.1 では敗者 rc=1 だった
        仕様の意図的変更）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            ops = [("brainstorm", "approve"), ("security", "reset")]
            procs = [self._spawn(root, g, a) for g, a in ops]
            outs = [p.communicate(timeout=30) for p in procs]
            self.assertEqual([p.returncode for p in procs], [0, 0],
                             f"both contenders must succeed: {outs}")
            status = (root / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: approved", status)
            self.assertIn("security: pending", status)
            self.assertFalse(
                (root / ".claude" / ".gate-update.lock.d").exists())

    def test_adoption_race_no_lost_update(self):
        """pid なし旧ロックへ 3 contender 同時（T4b×T5 合成ドリル）:
        O_EXCL の単一勝者はカーネル保証。観測契約は「全員逐次成功・
        lost update ゼロ・ロック残留ゼロ」。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            subprocess.run(["touch", "-t", "202601010000", str(lock)],
                           check=True)
            ops = [("brainstorm", "approve"), ("security", "reset"),
                   ("client_ready_for_dev", "reset")]
            procs = [self._spawn(root, g, a) for g, a in ops]
            outs = [p.communicate(timeout=30) for p in procs]
            self.assertEqual([p.returncode for p in procs], [0, 0, 0],
                             f"all contenders must succeed: {outs}")
            status = (root / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: approved", status)
            self.assertIn("security: pending", status)
            self.assertIn("client_ready_for_dev: pending", status)
            self.assertTrue(status.startswith("---"),
                            "frontmatter must not be torn")
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
