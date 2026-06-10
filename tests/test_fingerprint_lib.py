#!/usr/bin/env python3
"""fingerprint.sh — worktree fingerprint 単一所有者の契約テスト。

トークン契約: stdout 1行 = 64-hex sha256 | "oversize" | "nogit" | "error"、
常に rc=0。判定対象: HEAD コミット sha（無ければ empty-tree 定数）＋
HEAD 比の変更ファイル＋未追跡ファイル。docs/ と .claude/ プレフィックスは
除外（build-judge-card NONCODE_PREFIXES と同義）。
HEAD sha をハッシュ入力に混入する理由: クリーンツリー同士の fp 一致で
未テストの新コミットが green 認証されるのを防ぐ（grill-plan 🔴1）。
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FP = ROOT / "hooks" / "lib" / "fingerprint.sh"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def run_fp(root: Path, env_extra: dict | None = None) -> str:
    import os
    env = os.environ.copy()
    env.update(env_extra or {})
    proc = subprocess.run(["bash", str(FP), str(root)],
                          capture_output=True, text=True, timeout=60, env=env)
    assert proc.returncode == 0, f"rc={proc.returncode} stderr={proc.stderr}"
    return proc.stdout.strip()


def make_repo(d: Path) -> None:
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "init"], check=True)


class TestFingerprint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nogit_token(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(run_fp(Path(d)), "nogit")

    def test_clean_tree_is_deterministic_hex(self):
        a = run_fp(self.root)
        b = run_fp(self.root)
        self.assertRegex(a, HEX64)
        self.assertEqual(a, b)

    def test_untracked_code_file_changes_fp(self):
        before = run_fp(self.root)
        (self.root / "app.py").write_text("print(1)\n")
        after = run_fp(self.root)
        self.assertNotEqual(before, after)
        self.assertRegex(after, HEX64)

    def test_content_change_changes_fp(self):
        (self.root / "app.py").write_text("print(1)\n")
        a = run_fp(self.root)
        (self.root / "app.py").write_text("print(2)\n")
        b = run_fp(self.root)
        self.assertNotEqual(a, b)

    def test_docs_and_claude_excluded(self):
        (self.root / "app.py").write_text("print(1)\n")
        base = run_fp(self.root)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "STATUS.md").write_text("x\n")
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "snap").write_text("y\n")
        self.assertEqual(run_fp(self.root), base)

    def test_oversize_by_file_count(self):
        (self.root / "a.py").write_text("1\n")
        (self.root / "b.py").write_text("2\n")
        self.assertEqual(
            run_fp(self.root, {"AEGIS_FP_MAX_FILES": "1"}), "oversize")

    def test_oversize_by_bytes(self):
        (self.root / "big.py").write_text("x" * 100)
        self.assertEqual(
            run_fp(self.root, {"AEGIS_FP_MAX_BYTES": "10"}), "oversize")

    def test_repo_without_head_uses_empty_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "-C", d, "init", "-q"], check=True)
            (root / "app.py").write_text("print(1)\n")
            self.assertRegex(run_fp(root), HEX64)

    def test_new_commit_changes_fp_even_when_tree_clean(self):
        # grill-plan 🔴1: クリーンツリー同士でも HEAD が進めば fp は変わる。
        # さもなくば「コミット→テスト→さらにコミット」で未テストコードが
        # 記録時 fp と一致し green 認証される。
        a = run_fp(self.root)
        (self.root / "app.py").write_text("print(1)\n")
        subprocess.run(["git", "-C", str(self.root), "add", "app.py"],
                       check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-q", "-m", "x"],
                       check=True)
        b = run_fp(self.root)  # ツリーは再びクリーン
        self.assertRegex(b, HEX64)
        self.assertNotEqual(a, b)


class TestFingerprintHardening(unittest.TestCase):
    """grill-code 所見: 非ASCII名・無区切り連結・読取不能の silent-green 封鎖。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nonascii_filename_content_change_changes_fp(self):
        # grill-code 🔴1: core.quotepath 既定 on だと git が非ASCII名を
        # octal-quote し cat が失敗、内容を変えても fp が不変（silent green）。
        (self.root / "テスト.py").write_text("print(1)\n", encoding="utf-8")
        a = run_fp(self.root)
        (self.root / "テスト.py").write_text("print(2)\n", encoding="utf-8")
        b = run_fp(self.root)
        self.assertRegex(a, HEX64)
        self.assertRegex(b, HEX64)
        self.assertNotEqual(a, b)

    def test_nonascii_docs_file_still_excluded(self):
        (self.root / "app.py").write_text("print(1)\n")
        base = run_fp(self.root)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "メモ.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(run_fp(self.root), base)

    def test_boundary_concat_collision_resistant(self):
        # grill-code 🟡1: rel＋content の無区切り連結だと {B:"bfoo"} と
        # {B:"b", f:"oo"} が同一ハッシュ入力になる（同一 HEAD 下で衝突）。
        (self.root / "B").write_text("bfoo")
        a = run_fp(self.root)
        (self.root / "B").write_text("b")
        (self.root / "f").write_text("oo")
        b = run_fp(self.root)
        self.assertNotEqual(a, b)

    def test_unreadable_file_yields_error_token(self):
        import os
        if os.geteuid() == 0:
            self.skipTest("root はパーミッションを無視する")
        p = self.root / "secret.py"
        p.write_text("x\n")
        p.chmod(0o000)
        try:
            self.assertEqual(run_fp(self.root), "error")
        finally:
            p.chmod(0o644)

    def test_quoted_filename_yields_error_token(self):
        # quotepath=off でも quote/制御文字入りの名前は git が quote する。
        # cat 失敗で定数を混ぜる（fp 不感）のではなく error に倒す（fail-closed）。
        (self.root / 'a"b.py').write_text("print(1)\n")
        self.assertEqual(run_fp(self.root), "error")

    def test_deleted_tracked_file_changes_fp(self):
        (self.root / "src.py").write_text("print(1)\n")
        subprocess.run(["git", "-C", str(self.root), "add", "src.py"],
                       check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-q", "-m", "x"],
                       check=True)
        clean = run_fp(self.root)
        (self.root / "src.py").unlink()
        deleted = run_fp(self.root)
        self.assertRegex(deleted, HEX64)
        self.assertNotEqual(clean, deleted)


if __name__ == "__main__":
    unittest.main()
