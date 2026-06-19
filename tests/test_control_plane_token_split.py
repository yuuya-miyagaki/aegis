#!/usr/bin/env python3
"""SF-001: control-plane フックの quote/escape/bare-dir トークン分割バイパス。

変更前(8f8eb2d 系)は task_type=feature でこれらが allow になっていた(Critical)。
シェルのクォート除去/隣接連結/backslash/trailing-slash 無し bare-dir operand で
再構成される control-plane 書込み先を、フックは literal `hooks/`|... 一致のみで
判定していたため取りこぼしていた。Augment はこれらを deny 化しつつ既存 allow を
後退させない。

ハーネスは tests/test_control_plane_allowlist.py と同一。
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


class TestQuoteSplitBypass(unittest.TestCase):
    """クォート除去＋隣接連結／backslash で再構成される CP 書込み先。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_empty_quote_split_denied(self):
        out = _hook(self.root, 'cp safe.txt hooks""/lib/emit.sh')
        self.assertTrue(_denied(out), f"empty-quote split must deny: {out[:200]!r}")

    def test_adjacent_quote_concat_denied(self):
        out = _hook(self.root, 'cp safe.txt "ho""oks/lib/emit.sh"')
        self.assertTrue(_denied(out), f"adjacent-quote concat must deny: {out[:200]!r}")

    def test_single_quote_split_denied(self):
        out = _hook(self.root, "cp safe.txt 'hoo'ks/lib/emit.sh")
        self.assertTrue(_denied(out), f"single-quote split must deny: {out[:200]!r}")

    def test_slash_split_denied(self):
        out = _hook(self.root, 'cp safe.txt hooks"/"lib/emit.sh')
        self.assertTrue(_denied(out), f"slash split must deny: {out[:200]!r}")

    def test_backslash_escape_denied(self):
        out = _hook(self.root, 'cp safe.txt hooks\\/lib/emit.sh')
        self.assertTrue(_denied(out), f"backslash escape must deny: {out[:200]!r}")

    def test_redirect_split_target_denied(self):
        out = _hook(self.root, 'echo evil > "hoo""ks/lib/emit.sh"')
        self.assertTrue(_denied(out), f"split redirect target must deny: {out[:200]!r}")

    def test_status_md_split_denied(self):
        out = _hook(self.root, 'cp evil "STAT"US.md')
        self.assertTrue(_denied(out), f"split STATUS.md must deny: {out[:200]!r}")

    def test_xargs_split_denied(self):
        out = _hook(self.root, 'echo x | xargs -I{} cp {} "hoo"ks/lib/emit.sh')
        self.assertTrue(_denied(out), f"xargs split target must deny: {out[:200]!r}")

    def test_find_exec_split_denied(self):
        out = _hook(self.root, 'find . -name x -exec cp {} "hoo"ks/lib/emit.sh \\;')
        self.assertTrue(_denied(out), f"find -exec split target must deny: {out[:200]!r}")


class TestBareDirBypass(unittest.TestCase):
    """trailing-slash 無し bare ディレクトリ operand（CP 正規表現は `hooks/` を要求）。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_find_bare_dir_exec_rm_denied(self):
        out = _hook(self.root, "find hooks -type f -exec rm {} +")
        self.assertTrue(_denied(out), f"bare find -exec rm must deny: {out[:200]!r}")

    def test_rm_rf_bare_dir_denied(self):
        out = _hook(self.root, "rm -rf hooks")
        self.assertTrue(_denied(out), f"rm -rf bare hooks must deny: {out[:200]!r}")

    def test_cp_to_bare_dir_denied(self):
        out = _hook(self.root, "cp evil hooks")
        self.assertTrue(_denied(out), f"cp to bare hooks must deny: {out[:200]!r}")

    def test_rm_rf_bare_scripts_denied(self):
        out = _hook(self.root, "rm -rf scripts")
        self.assertTrue(_denied(out), f"rm -rf bare scripts must deny: {out[:200]!r}")

    def test_rm_rf_bare_templates_denied(self):
        out = _hook(self.root, "rm -rf templates")
        self.assertTrue(_denied(out), f"rm -rf bare templates must deny: {out[:200]!r}")


class TestNoRegressionAllows(unittest.TestCase):
    """既存 allow を後退させない（偽陽性ゼロの確認）。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_commit_message_status_allowed(self):
        out = _hook(self.root, 'git commit -m "update STATUS.md handling"')
        self.assertTrue(_allowed(out), f"CP in commit message must allow: {out[:200]!r}")

    def test_echo_quoted_cp_redirect_noncp_allowed(self):
        out = _hook(self.root, "echo 'see hooks/ for details' >> notes.txt")
        self.assertTrue(_allowed(out), f"CP in echo arg, non-CP target must allow: {out[:200]!r}")

    def test_ls_bare_dir_allowed(self):
        out = _hook(self.root, "ls hooks")
        self.assertTrue(_allowed(out), f"read of bare hooks must allow: {out[:200]!r}")

    def test_find_bare_dir_read_allowed(self):
        out = _hook(self.root, "find hooks -type f")
        self.assertTrue(_allowed(out), f"read find of bare hooks must allow: {out[:200]!r}")

    def test_subdir_named_hooks_allowed(self):
        # 上位 src/hooks は CP ではない（語境界で除外）。
        out = _hook(self.root, "rm -rf src/hooks")
        self.assertTrue(_allowed(out), f"project src/hooks is not CP: {out[:200]!r}")


class TestPython3Absent(unittest.TestCase):
    """degraded mode（python3 が壊れている/不在）: bare-dir は Sub-check 1(pure-bash)
    で deny、read は許可、フックはクラッシュしない。quote分割は既存挙動に fallback。"""

    @classmethod
    def setUpClass(cls):
        import os
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)
        binr = cls.root / "nopybin"
        binr.mkdir()
        shim = binr / "python3"
        shim.write_text("#!/bin/sh\nexit 127\n")
        shim.chmod(0o755)
        cls._env = dict(os.environ, PATH=f"{binr}:{os.environ.get('PATH', '')}")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _hook_nopy(self, cmd: str) -> str:
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
        r = subprocess.run(
            ["bash", str(self.root / "hooks" / "check-control-plane.sh")],
            input=payload, capture_output=True, text=True,
            cwd=str(self.root), env=self._env)
        return r.stdout

    def test_bare_dir_denied_without_python(self):
        out = self._hook_nopy("rm -rf hooks")
        self.assertTrue(_denied(out), f"bare-dir must deny without python3: {out[:200]!r}")

    def test_read_allowed_without_python(self):
        out = self._hook_nopy("ls hooks")
        self.assertTrue(_allowed(out), f"read must allow without python3: {out[:200]!r}")

    def test_no_crash_without_python(self):
        out = self._hook_nopy("rm -rf hooks")
        self.assertTrue(out.strip() != "", f"hook must emit a decision, not crash: {out[:200]!r}")


class TestAbsPathBareDir(unittest.TestCase):
    """F-1（iter32 1次レビュー break-attempt）: trailing-slash 無しの絶対 root パス
    bare-dir operand。`rm -rf {ROOT}/hooks/` は deny だが `{ROOT}/hooks`（末尾スラッシュ
    無し）が allow になっていた。設計 unit C が abs 形を約束していた未配線箇所。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_abs_rm_rf_hooks_denied(self):
        out = _hook(self.root, f"rm -rf {self.root}/hooks")
        self.assertTrue(_denied(out), f"abs bare hooks rm must deny: {out[:200]!r}")

    def test_abs_cp_to_scripts_denied(self):
        out = _hook(self.root, f"cp evil {self.root}/scripts")
        self.assertTrue(_denied(out), f"abs bare scripts cp must deny: {out[:200]!r}")

    def test_abs_mv_hooks_denied(self):
        out = _hook(self.root, f"mv {self.root}/hooks /tmp/x")
        self.assertTrue(_denied(out), f"abs bare hooks mv must deny: {out[:200]!r}")

    def test_abs_trailing_slash_still_denied(self):
        # 既存挙動（trailing slash 形）が後退しないことの確認。
        out = _hook(self.root, f"rm -rf {self.root}/hooks/")
        self.assertTrue(_denied(out), f"abs hooks/ must deny: {out[:200]!r}")


class TestAnsiCQuoting(unittest.TestCase):
    """F-2（iter32 1次レビュー break-attempt）: $'...' ANSI-C クォートで再構成される CP。
    shlex(posix) は $'...' を展開しないため取りこぼしていた。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_ansic_hex_rm_denied(self):
        out = _hook(self.root, "rm -rf $'hook\\x73'")
        self.assertTrue(_denied(out), f"$'hook\\x73' must deny: {out[:200]!r}")

    def test_ansic_full_hex_cp_denied(self):
        out = _hook(self.root, "cp evil $'\\x68\\x6f\\x6f\\x6b\\x73'")
        self.assertTrue(_denied(out), f"$'\\x68..' must deny: {out[:200]!r}")

    def test_ansic_plain_rm_denied(self):
        out = _hook(self.root, "rm -rf $'hooks'")
        self.assertTrue(_denied(out), f"$'hooks' must deny: {out[:200]!r}")

    def test_ansic_redirect_denied(self):
        out = _hook(self.root, "echo evil > $'hoo\\x6bs/lib/emit.sh'")
        self.assertTrue(_denied(out), f"$'..' redirect target must deny: {out[:200]!r}")

    def test_ansic_printf_noncp_allowed(self):
        out = _hook(self.root, "printf $'%s\\n' x")
        self.assertTrue(_allowed(out), f"$'%s\\n' non-CP must allow: {out[:200]!r}")

    def test_ansic_echo_tab_noncp_allowed(self):
        out = _hook(self.root, "echo $'a\\tb'")
        self.assertTrue(_allowed(out), f"$'a\\tb' non-CP must allow: {out[:200]!r}")


class TestPathNormalization(unittest.TestCase):
    """F-3（iter32 review round2 break-attempt）: パス正規化（.//・/./・連続スラッシュ）
    と $PWD 変数で再構成される CP。リテラル正規表現の左境界 `/` 除外と単一 `./` 想定で
    取りこぼしていた。ROOT 相対 normpath ＋ $PWD→ROOT 展開で塞ぐ。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_double_slash_redirect_denied(self):
        out = _hook(self.root, "echo evil > .//hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f".//hooks redirect must deny: {out[:200]!r}")

    def test_double_slash_rm_denied(self):
        out = _hook(self.root, "rm -rf .//hooks")
        self.assertTrue(_denied(out), f"rm .//hooks must deny: {out[:200]!r}")

    def test_dot_slash_dot_rm_denied(self):
        out = _hook(self.root, "rm -rf ././hooks")
        self.assertTrue(_denied(out), f"rm ././hooks must deny: {out[:200]!r}")

    def test_pwd_var_rm_denied(self):
        out = _hook(self.root, "rm -rf $PWD/hooks")
        self.assertTrue(_denied(out), f"rm $PWD/hooks must deny: {out[:200]!r}")

    def test_pwd_var_redirect_denied(self):
        out = _hook(self.root, "echo evil > $PWD/hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"$PWD redirect must deny: {out[:200]!r}")

    def test_abs_dot_rm_denied(self):
        out = _hook(self.root, f"rm -rf {self.root}/./hooks")
        self.assertTrue(_denied(out), f"abs /./hooks must deny: {out[:200]!r}")

    def test_abs_double_slash_rm_denied(self):
        out = _hook(self.root, f"rm -rf {self.root}//hooks")
        self.assertTrue(_denied(out), f"abs //hooks must deny: {out[:200]!r}")

    def test_cp_double_slash_scripts_denied(self):
        out = _hook(self.root, "cp evil .//scripts")
        self.assertTrue(_denied(out), f"cp .//scripts must deny: {out[:200]!r}")

    # ---- regression: sibling/parent dirs that are NOT the framework CP ----
    def test_sibling_src_hooks_allowed(self):
        out = _hook(self.root, "rm -rf src/hooks")
        self.assertTrue(_allowed(out), f"src/hooks (not CP) must allow: {out[:200]!r}")

    def test_node_modules_allowed(self):
        out = _hook(self.root, "rm -rf node_modules")
        self.assertTrue(_allowed(out), f"node_modules must allow: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
