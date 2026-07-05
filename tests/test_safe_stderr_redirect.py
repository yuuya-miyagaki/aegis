#!/usr/bin/env python3
"""iter55 P3d（iter57 で check-runtime-state に移管）: 安全な stderr リダイレクト
（2>/dev/null・2>&1）の正規化。

ゲート戦闘1の正体: 素の runtime-state 読取（`cat docs/STATUS.md`）は read-only
carve-out で ALLOW だが、慣用的に付く `2>/dev/null` / `2>&1` の > / & が CHAIN_OPS に
該当し read-only・allowlist 両 carve-out から脱落して DENY。ファイル書込みが発生し得ない
2 形のみ除去し、それ以外（2>>, 2>file, 2>/dev/nullish, fd1 の >/dev/null, 除去後も残る >）
は fail-closed のまま。

iter57: この strip ロジックは check-control-plane から check-runtime-state.sh に verbatim
移植された。runtime-state を参照するコマンドでのみ発火するため、テストは STATUS.md を
対象にする（安定 CP への write 遮断は OS-lock の担当＝別テスト test_cp_lock_sf_catalog）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = "check-runtime-state.sh"


def _scratch_root() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / HOOK, hooks_dir / HOOK)
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    (lib_dir / "scripts-manifest.tsv").symlink_to(
        ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / HOOK)],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


class TestSafeStderrRedirectAllowed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_cat_status_devnull_allowed(self):
        out = _hook(self.root, "cat docs/STATUS.md 2>/dev/null")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_grep_status_devnull_with_space_allowed(self):
        out = _hook(self.root, "grep -n phase docs/STATUS.md 2> /dev/null")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_cat_status_stderr_merge_allowed(self):
        out = _hook(self.root, "cat docs/STATUS.md 2>&1")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_allowlisted_script_on_status_with_stderr_merge_allowed(self):
        out = _hook(self.root,
                    "python3 scripts/status_doctor.py docs/STATUS.md 2>&1")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_readonly_pipe_after_strip_allowed(self):
        out = _hook(self.root, "grep -n phase docs/STATUS.md 2>/dev/null | head -5")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")


class TestUnsafeRedirectsStayDenied(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_append_to_devnull_style_denied(self):
        out = _hook(self.root, "cat docs/STATUS.md 2>>/dev/null")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_stderr_to_file_denied(self):
        out = _hook(self.root, "cat docs/STATUS.md 2>err.log")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_devnullish_suffix_denied(self):
        out = _hook(self.root, "cat docs/STATUS.md 2>/dev/nullish")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_fd1_devnull_not_tolerated(self):
        out = _hook(self.root, "cat docs/STATUS.md >/dev/null")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_merge_then_real_redirect_denied(self):
        out = _hook(self.root, "cat docs/STATUS.md 2>&1 > out.txt")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_script_merge_then_chain_denied(self):
        out = _hook(self.root,
                    "python3 scripts/status_doctor.py docs/STATUS.md 2>&1 && rm x")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
