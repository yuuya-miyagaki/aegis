#!/usr/bin/env python3
"""iter55 P3d: 安全な stderr リダイレクト（2>/dev/null・2>&1）の正規化。

ドッグフードのゲート戦闘1の正体（2026-07-03 実プローブで確定）: 素の `ls templates/` は
read-only carve-out で ALLOW だが、エージェントが慣用的に付ける `2>/dev/null` / `2>&1` の
> / & が CHAIN_OPS に該当し read-only・allowlist 両 carve-out から脱落して DENY。
ファイル書込みが発生し得ない 2 形のみ除去し、それ以外（2>>, 2>file, 2>/dev/nullish,
fd1 の >/dev/null, 除去後も残る >）は fail-closed のまま。
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


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
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

    def test_ls_devnull_allowed(self):
        out = _hook(self.root, "ls templates/ 2>/dev/null")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_ls_devnull_with_space_allowed(self):
        out = _hook(self.root, "ls -la templates/ docs/ 2> /dev/null")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_ls_stderr_merge_allowed(self):
        out = _hook(self.root, "ls templates/ docs/ 2>&1")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_allowlisted_script_with_stderr_merge_allowed(self):
        out = _hook(self.root, "bash scripts/update-gate.sh review approve 2>&1")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_readonly_pipe_after_strip_allowed(self):
        out = _hook(self.root, "grep -rn foo scripts/ 2>/dev/null | head -5")
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
        out = _hook(self.root, "ls hooks/ 2>>/dev/null")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_stderr_to_file_denied(self):
        out = _hook(self.root, "ls hooks/ 2>err.log")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_devnullish_suffix_denied(self):
        out = _hook(self.root, "ls hooks/ 2>/dev/nullish")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_fd1_devnull_not_tolerated(self):
        out = _hook(self.root, "ls hooks/ >/dev/null")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_merge_then_real_redirect_denied(self):
        out = _hook(self.root, "ls hooks/ 2>&1 > hooks/evil")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_script_merge_then_chain_denied(self):
        out = _hook(self.root,
                    "bash scripts/update-gate.sh review approve 2>&1 && rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
