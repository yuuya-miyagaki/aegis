#!/usr/bin/env python3
"""K-8 / K-9 / K-11 (v1.6.2): setup.sh 配布パスの破壊抑止。

第6回 Phase A DIST-01〜04:
  K-8 (DIST-01): generate_settings が settings.local.json を無条件上書きし
    permissions.allow / env / 未知 key を消失させる。grill 致命 4 で
    『hooks 以外の全 key を保存』に拡張。
  K-9 (DIST-02): upgrade で旧 hooks/lib/*.sh が SKIP 残留→新 hook が
    function 不在で exit 127→Claude Code fail-open。F6 同型 2 例目。
  K-11 (DIST-04): framework_version stamp 不在で status_doctor /
    check_framework_contract が install 先の版差分を見ない。
  DIST-12 前倒し: --target=<framework_root> で framework 自身に install
    しようとしたら abort。
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SH = ROOT / "bin" / "setup.sh"
STATUS_DOCTOR = ROOT / "scripts" / "status_doctor.py"

# Read FRAMEWORK_VERSION from the contract module without importing.
def _framework_version() -> str:
    import re
    text = (ROOT / "scripts" / "check_framework_contract.py").read_text()
    m = re.search(r'FRAMEWORK_VERSION\s*=\s*"([^"]+)"', text)
    assert m, "FRAMEWORK_VERSION constant missing"
    return m.group(1)


FRAMEWORK_VERSION = _framework_version()


def _setup(profile: str, target: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(SETUP_SH), f"--profile={profile}", f"--target={target}"],
        capture_output=True, text=True,
    )


class TestK8PreserveUserSettings(unittest.TestCase):
    """K-8 / DIST-01 + grill 致命 4: 既存 settings.local.json のユーザ key 保存"""

    def test_existing_permissions_allow_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            project.mkdir()
            (project / ".claude").mkdir()
            existing = {
                "permissions": {"allow": ["Bash(npm:*)"]},
                "hooks": {},
            }
            (project / ".claude/settings.local.json").write_text(
                json.dumps(existing))
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0, f"setup failed: {r.stderr}")
            after = json.loads(
                (project / ".claude/settings.local.json").read_text())
            self.assertIn("Bash(npm:*)",
                          after.get("permissions", {}).get("allow", []),
                          f"user permission lost: {after}")

    def test_existing_env_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            project.mkdir()
            (project / ".claude").mkdir()
            existing = {"env": {"MY_VAR": "x"}, "hooks": {}}
            (project / ".claude/settings.local.json").write_text(
                json.dumps(existing))
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0, f"setup failed: {r.stderr}")
            after = json.loads(
                (project / ".claude/settings.local.json").read_text())
            self.assertEqual(after.get("env", {}).get("MY_VAR"), "x",
                             f"env lost: {after}")

    def test_unknown_top_level_key_preserved(self):
        """grill 致命 4: 将来 Claude Code が追加する未知 key も保存"""
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            project.mkdir()
            (project / ".claude").mkdir()
            existing = {"futureKey": {"x": 1}, "hooks": {}}
            (project / ".claude/settings.local.json").write_text(
                json.dumps(existing))
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0, f"setup failed: {r.stderr}")
            after = json.loads(
                (project / ".claude/settings.local.json").read_text())
            self.assertEqual(after.get("futureKey", {}).get("x"), 1,
                             f"unknown key lost: {after}")

    def test_hooks_section_overwritten(self):
        """hooks は framework 管理＝強制上書き"""
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            project.mkdir()
            (project / ".claude").mkdir()
            existing = {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "CustomMarker", "hooks": []}
                    ]
                }
            }
            (project / ".claude/settings.local.json").write_text(
                json.dumps(existing))
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0)
            after = json.loads(
                (project / ".claude/settings.local.json").read_text())
            matchers = [
                e.get("matcher", "")
                for e in after.get("hooks", {}).get("PreToolUse", [])
            ]
            self.assertNotIn("CustomMarker", matchers,
                             "user hooks section must be overwritten")

    def test_backup_created_on_overwrite(self):
        """既存ファイルがあれば .bak.<ts> が作られる"""
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            project.mkdir()
            (project / ".claude").mkdir()
            (project / ".claude/settings.local.json").write_text('{"hooks":{}}')
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0)
            baks = list((project / ".claude").glob("settings.local.json.bak.*"))
            self.assertGreaterEqual(
                len(baks), 1, f"no backup created: {list((project / '.claude').iterdir())}"
            )


class TestK9LibForceUpgrade(unittest.TestCase):
    """K-9 / DIST-02: upgrade で旧 lib が残留→新 hook 死亡を防ぐ"""

    def test_lib_force_overwritten_on_reinstall(self):
        """v1.4 風の古い emit.sh を残しておくと再 install で強制上書き"""
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0, f"first setup failed: {r.stderr}")
            # Truncate emit.sh to simulate old/broken version
            emit = project / "hooks/lib/emit.sh"
            emit.write_text("# old stub — no functions\n")
            # Re-run setup
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0, f"upgrade failed: {r.stderr}")
            content = emit.read_text()
            self.assertIn("emit_ask", content,
                          "lib not force-upgraded — F6 同型再発")


class TestK11VersionStamp(unittest.TestCase):
    """K-11 / DIST-04: install 時に framework_version stamp を書く"""

    def test_install_writes_version_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0, f"setup failed: {r.stderr}")
            stamp = project / ".claude" / ".aegis-install-version"
            self.assertTrue(
                stamp.exists(),
                f"version stamp file missing: {list((project / '.claude').iterdir())}"
            )
            self.assertEqual(stamp.read_text().strip(), FRAMEWORK_VERSION)

    def test_doctor_warns_on_version_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            r = _setup("standard", project)
            self.assertEqual(r.returncode, 0)
            # Simulate old install
            (project / ".claude" / ".aegis-install-version").write_text("1.4.0\n")
            r = subprocess.run(
                ["python3", str(STATUS_DOCTOR), "--root", str(project)],
                capture_output=True, text=True,
            )
            # status_doctor must mention version mismatch
            self.assertTrue(
                "version" in (r.stdout + r.stderr).lower()
                or r.returncode != 0,
                f"doctor missed version mismatch: rc={r.returncode} "
                f"stdout={r.stdout[:200]} stderr={r.stderr[:200]}"
            )


class TestDIST12FrameworkSelfInstallBlocked(unittest.TestCase):
    """DIST-12 前倒し: --target が framework_root と同一なら abort"""

    def test_target_equal_to_framework_root_is_rejected(self):
        r = subprocess.run(
            [str(SETUP_SH), "--profile=standard", f"--target={ROOT}"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(r.returncode, 0,
                            f"framework self-install should fail: {r.stdout}")
        self.assertIn(
            "framework",
            (r.stdout + r.stderr).lower(),
            f"error should mention framework: {r.stderr}"
        )


if __name__ == "__main__":
    unittest.main()
