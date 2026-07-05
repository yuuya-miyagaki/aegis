"""aegis_cp_verify: 期待 lock 状態と実 FS 状態の全数照合（iter57 主 moat 昇格）。

sentinel 1点プローブ（[ -w hooks ]）は「hooks/ dir 自体」しか見ないため、ネスト
深部の 1 ファイルだけ writable に戻る half-locked を誤読する。verify は
aegis_cp_paths の全対象を find -perm -u+w（POSIX・BSD/GNU 両対応）で歩き、
期待との不一致 path を stdout に列挙して rc1 を返す。

symlink（grill 致命2）: symlink の mode は常に 0777 に見えるため verify は
`! -type l` で除外する。lock/unlock 側も同フラグで symlink を chmod しない
（iter55「symlink 貫通」教訓 — 追従 chmod は CP 外の実ファイルを壊す）。

後始末は test_cp_lock_lib.py と同じ try/finally + chmod -R u+w イディオム
（assert 失敗時の read-only 残骸で pytest tmp GC が荒れるのを防ぐ）。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "cp-lock.sh"

WINDOWS = sys.platform.startswith("win")
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    WINDOWS or ROOTUSER,
    reason="chmod write-bit is a no-op on native Windows / bypassed by root")


def _make_scratch() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "hooks" / "lib").mkdir(parents=True)
    (p / "hooks" / "lib" / "emit.sh").write_text("echo lib\n")
    (p / "scripts").mkdir()
    (p / "scripts" / "a.py").write_text("print(1)\n")
    (p / "CLAUDE.md").write_text("# rules\n")
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text("---\n---\n")
    return tmp


def _bash(snippet: str, root: str):
    return subprocess.run(
        ["bash", "-c", f'source "{LIB}"; {snippet}'],
        capture_output=True, text=True, cwd=root,
    )


@NO_FS_LOCK
class TestCpVerify:
    def test_verify_ok_when_fully_locked(self):
        tmp = _make_scratch()
        try:
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            r = _bash('aegis_cp_verify "$PWD" feature', tmp.name)
            assert r.returncode == 0, r.stdout + r.stderr
            assert r.stdout.strip() == ""
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_verify_detects_half_locked_nested_file(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            # 事故シミュレーション: ネスト深部 1 ファイルだけ writable に戻る。
            # dir sentinel（hooks/ 自体）は locked のままなので旧プローブでは不可視。
            (p / "hooks" / "lib" / "emit.sh").chmod(0o644)
            r = _bash('aegis_cp_verify "$PWD" feature', tmp.name)
            assert r.returncode == 1
            assert "hooks/lib/emit.sh" in r.stdout
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_verify_detects_locked_remnant_in_framework_mode(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            _bash('aegis_cp_lock "$PWD"', tmp.name)
            _bash('aegis_cp_unlock "$PWD"', tmp.name)
            # unlock 期待なのに 1 本だけ read-only が残った（chmod 部分失敗の形）
            (p / "scripts" / "a.py").chmod(0o444)
            r = _bash('aegis_cp_verify "$PWD" framework', tmp.name)
            assert r.returncode == 1
            assert "scripts/a.py" in r.stdout
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_verify_empty_root_fails_loud(self):
        tmp = _make_scratch()
        try:
            r = _bash('aegis_cp_verify "" feature', tmp.name)
            assert r.returncode == 1
        finally:
            tmp.cleanup()

    def test_verify_ignores_symlinks(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            outside = p / "outside.txt"
            outside.write_text("external\n")
            (p / "hooks" / "link-out.sh").symlink_to(outside)
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            # symlink 自体は mode 0777 に見えるが違反として報告しない
            r = _bash('aegis_cp_verify "$PWD" feature', tmp.name)
            assert r.returncode == 0, r.stdout + r.stderr
            assert "link-out.sh" not in r.stdout
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_lock_does_not_chmod_symlink_target(self):
        """iter55「symlink 貫通」教訓: lock が symlink を追従して CP 外の
        実ファイルを read-only 化してはならない。"""
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            outside = p / "outside.txt"
            outside.write_text("external\n")
            (p / "hooks" / "link-out.sh").symlink_to(outside)
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            assert os.access(outside, os.W_OK), \
                "lock が symlink を貫通して外部ターゲットを chmod した"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()
