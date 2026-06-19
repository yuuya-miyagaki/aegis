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


class TestCmdsubAndVar(unittest.TestCase):
    """F-4（iter32 review round3 break-attempt）: cmdsub/変数で再構成される CP。
    pwd/$PWD は cwd=ROOT に解決して deny、未知 cmdsub/$VAR が前置され CP ディレクトリ名が
    残る形は ASK、CP 名が不透明な cmdsub に消える形（$(echo hooks)/lib）のみ accepted 残余。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _asked(self, out):
        return '"permissionDecision":"ask"' in out

    # ---- pwd cmdsub → resolvable → DENY ----
    def test_pwd_cmdsub_rm_denied(self):
        out = _hook(self.root, "rm -rf $(pwd)/hooks")
        self.assertTrue(_denied(out), f"$(pwd)/hooks must deny: {out[:200]!r}")

    def test_pwd_backtick_rm_denied(self):
        out = _hook(self.root, "rm -rf `pwd`/hooks")
        self.assertTrue(_denied(out), f"`pwd`/hooks must deny: {out[:200]!r}")

    def test_pwd_cmdsub_quoted_rm_denied(self):
        out = _hook(self.root, 'rm -rf "$(pwd)"/scripts')
        self.assertTrue(_denied(out), f'"$(pwd)"/scripts must deny: {out[:200]!r}')

    def test_pwd_cmdsub_redirect_denied(self):
        out = _hook(self.root, "echo evil > $(pwd)/hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"$(pwd) redirect must deny: {out[:200]!r}")

    # ---- unknown cmdsub/$VAR prefix + CP component → ASK ----
    def test_unknown_cmdsub_prefix_ask(self):
        out = _hook(self.root, "rm -rf $(date)/hooks")
        self.assertTrue(self._asked(out), f"$(date)/hooks must ask: {out[:200]!r}")

    def test_external_var_prefix_ask(self):
        out = _hook(self.root, "rm -rf $DIR/hooks")
        self.assertTrue(self._asked(out), f"$DIR/hooks must ask: {out[:200]!r}")

    # ---- accepted residual: CP name consumed into an opaque cmdsub → allow ----
    def test_cp_name_inside_cmdsub_residual_allowed(self):
        out = _hook(self.root, "rm -rf $(echo hooks)/lib")
        self.assertTrue(_allowed(out), f"$(echo hooks)/lib residual allow: {out[:200]!r}")

    # ---- regression: cmdsub not touching CP → allow ----
    def test_cmdsub_noncp_allowed(self):
        out = _hook(self.root, "cp $(ls *.txt) dest/")
        self.assertTrue(_allowed(out), f"cmdsub source non-CP must allow: {out[:200]!r}")

    def test_cmdsub_echo_noncp_allowed(self):
        out = _hook(self.root, "echo $(date)")
        self.assertTrue(_allowed(out), f"echo $(date) must allow: {out[:200]!r}")


class TestParamDefaultAndBrace(unittest.TestCase):
    """F-5/F-6（iter32 review round4 break-attempt）: パラメータ展開デフォルト
    ${VAR:-hooks}（VAR 未設定時に静的リテラル hooks に展開）と brace 展開
    {hooks,build}。どちらも静的に見える CP 名を sentinel が潰していた。静的部を
    解決して deny する。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # ---- parameter-expansion default to a CP literal → DENY ----
    def test_param_default_dash_denied(self):
        out = _hook(self.root, "rm -rf ${X:-hooks}")
        self.assertTrue(_denied(out), f"${{X:-hooks}} must deny: {out[:200]!r}")

    def test_param_default_assign_denied(self):
        out = _hook(self.root, "rm -rf ${X:=scripts}")
        self.assertTrue(_denied(out), f"${{X:=scripts}} must deny: {out[:200]!r}")

    def test_param_default_plus_denied(self):
        out = _hook(self.root, "rm -rf ${X:+templates}")
        self.assertTrue(_denied(out), f"${{X:+templates}} must deny: {out[:200]!r}")

    def test_param_default_quoted_denied(self):
        out = _hook(self.root, 'rm -rf "${X:-hooks}"')
        self.assertTrue(_denied(out), f'"${{X:-hooks}}" must deny: {out[:200]!r}')

    def test_param_default_suffix_denied(self):
        out = _hook(self.root, "cp evil ${X:-hooks}/lib")
        self.assertTrue(_denied(out), f"${{X:-hooks}}/lib must deny: {out[:200]!r}")

    # ---- brace expansion including a CP dir → DENY ----
    def test_brace_hooks_denied(self):
        out = _hook(self.root, "rm -rf {hooks,build}")
        self.assertTrue(_denied(out), f"{{hooks,build}} must deny: {out[:200]!r}")

    def test_brace_scripts_denied(self):
        out = _hook(self.root, "rm -rf {dist,scripts}")
        self.assertTrue(_denied(out), f"{{dist,scripts}} must deny: {out[:200]!r}")

    # ---- regression: non-CP default / brace → ALLOW ----
    def test_param_default_noncp_allowed(self):
        out = _hook(self.root, "rm -rf ${X:-/tmp/safe}")
        self.assertTrue(_allowed(out), f"non-CP default must allow: {out[:200]!r}")

    def test_param_use_only_allowed(self):
        out = _hook(self.root, "echo ${PATH}")
        self.assertTrue(_allowed(out), f"plain ${{PATH}} must allow: {out[:200]!r}")

    def test_brace_noncp_allowed(self):
        out = _hook(self.root, "rm -rf {a,b}")
        self.assertTrue(_allowed(out), f"non-CP brace must allow: {out[:200]!r}")

    def test_brace_subdir_allowed(self):
        out = _hook(self.root, "cp x {src,dist}/file")
        self.assertTrue(_allowed(out), f"non-CP brace subdir must allow: {out[:200]!r}")


class TestTildeAndNestedParam(unittest.TestCase):
    """round5 盲検 break-attempt: `~+`(=PWD=ROOT) と入れ子 param-default
    ${X:-${Y:-hooks}}。どちらも静的に CP に解決するのに取りこぼしていた。
    `~+` は ROOT 展開して deny、入れ子 param-default は _PARAM/_PWD 置換を
    fixpoint ループ化して全層を解決。`~-`(=OLDPWD) は runtime 値依存のため
    $OLDPWD と同じく sentinel→ASK、`~`(=HOME) は CP でない。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _asked(self, out):
        return '"permissionDecision":"ask"' in out

    # ---- tilde-plus (~+ = PWD = ROOT) → DENY ----
    def test_tilde_plus_rm_denied(self):
        out = _hook(self.root, "rm -rf ~+/hooks")
        self.assertTrue(_denied(out), f"~+/hooks must deny: {out[:200]!r}")

    def test_tilde_plus_cp_scripts_denied(self):
        out = _hook(self.root, "cp evil ~+/scripts")
        self.assertTrue(_denied(out), f"~+/scripts must deny: {out[:200]!r}")

    def test_tilde_plus_redirect_denied(self):
        out = _hook(self.root, "echo evil > ~+/hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"~+ redirect must deny: {out[:200]!r}")

    def test_tilde_plus_noncp_allowed(self):
        out = _hook(self.root, "rm -rf ~+/build")
        self.assertTrue(_allowed(out), f"~+/build (non-CP) must allow: {out[:200]!r}")

    # ---- nested parameter-default → DENY (fixpoint resolution) ----
    def test_nested_param_default_denied(self):
        out = _hook(self.root, "rm -rf ${X:-${Y:-hooks}}")
        self.assertTrue(_denied(out), f"nested ${{X:-${{Y:-hooks}}}} must deny: {out[:200]!r}")

    def test_nested_param_default_suffix_denied(self):
        out = _hook(self.root, "cp evil ${X:-${Y:-hooks}}/lib")
        self.assertTrue(_denied(out), f"nested param suffix must deny: {out[:200]!r}")

    def test_nested_param_tilde_inside_denied(self):
        out = _hook(self.root, "rm -rf ${X:-~+}/hooks")
        self.assertTrue(_denied(out), f"${{X:-~+}}/hooks must deny: {out[:200]!r}")

    def test_nested_param_default_noncp_allowed(self):
        out = _hook(self.root, "rm -rf ${X:-${Y:-/tmp/safe}}")
        self.assertTrue(_allowed(out), f"nested non-CP default must allow: {out[:200]!r}")

    # ---- tilde-minus (~- = OLDPWD, runtime-unknown) → ASK ----
    def test_tilde_minus_oldpwd_ask(self):
        out = _hook(self.root, "rm -rf ~-/hooks")
        self.assertTrue(self._asked(out), f"~-/hooks (OLDPWD) must ask: {out[:200]!r}")

    # ---- tilde-home (~ = HOME, not the project CP) → ALLOW ----
    def test_tilde_home_noncp_allowed(self):
        out = _hook(self.root, "rm -rf ~/hooks")
        self.assertTrue(_allowed(out), f"~/hooks (HOME) is not project CP: {out[:200]!r}")


class TestExpansionSplitAndBareClaude(unittest.TestCase):
    """round6 盲検 break-attempt: augment GATE が「リテラル hooks|scripts|templates
    部分文字列」を要求するため、展開で CP 名を分割すると python リゾルバに到達せず
    即 ALLOW になっていた（systemic な GATE 弱点）。また `.claude` の境界正規表現が
    末尾（文字列末）を取りこぼし `rm -rf .claude` が allow だった。
    - 静的に解決する分割（h${X:-ooks} / {h,x}ooks）→ DENY
    - runtime 値依存の接着（ho${EMPTY}oks / ${X#zzz}hooks）→ ASK（fail-safe）
    - `.claude` 末尾 → DENY、read は ALLOW 維持。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _asked(self, out):
        return '"permissionDecision":"ask"' in out

    # ---- C-2: bare `.claude` at end-of-command → DENY ----
    def test_bare_claude_rm_denied(self):
        out = _hook(self.root, "rm -rf .claude")
        self.assertTrue(_denied(out), f"rm -rf .claude must deny: {out[:200]!r}")

    def test_bare_claude_cp_denied(self):
        out = _hook(self.root, "cp evil .claude")
        self.assertTrue(_denied(out), f"cp evil .claude must deny: {out[:200]!r}")

    def test_bare_claude_read_allowed(self):
        out = _hook(self.root, "ls .claude")
        self.assertTrue(_allowed(out), f"ls .claude (read) must allow: {out[:200]!r}")

    def test_claude_slash_still_denied(self):
        out = _hook(self.root, "rm -rf .claude/")
        self.assertTrue(_denied(out), f".claude/ regression must deny: {out[:200]!r}")

    # ---- C-3 static: expansion-split CP name resolves → DENY ----
    def test_param_split_prefix_denied(self):
        out = _hook(self.root, "rm -rf h${X:-ooks}")
        self.assertTrue(_denied(out), f"h${{X:-ooks}} must deny: {out[:200]!r}")

    def test_param_split_suffix_denied(self):
        out = _hook(self.root, "rm -rf hoo${X:-ks}")
        self.assertTrue(_denied(out), f"hoo${{X:-ks}} must deny: {out[:200]!r}")

    def test_brace_split_denied(self):
        out = _hook(self.root, "rm -rf {h,x}ooks")
        self.assertTrue(_denied(out), f"{{h,x}}ooks must deny: {out[:200]!r}")

    # ---- C-3 empty-glue: unknown expansion MIGHT be empty → ASK ----
    def test_empty_var_glue_ask(self):
        out = _hook(self.root, "rm -rf ho${EMPTY}oks")
        self.assertTrue(self._asked(out), f"ho${{EMPTY}}oks must ask: {out[:200]!r}")

    def test_empty_var_prefix_glue_ask(self):
        out = _hook(self.root, "rm -rf ${E}hooks")
        self.assertTrue(self._asked(out), f"${{E}}hooks must ask: {out[:200]!r}")

    def test_status_md_cmdsub_glue_ask(self):
        out = _hook(self.root, "cp evil STAT$(echo)US.md")
        self.assertTrue(self._asked(out), f"STAT$(echo)US.md must ask: {out[:200]!r}")

    # ---- C-4 strip/pattern-sub glued to literal → ASK (X may be unset) ----
    def test_strip_prefix_glue_ask(self):
        out = _hook(self.root, "rm -rf ${X#zzz}hooks")
        self.assertTrue(self._asked(out), f"${{X#zzz}}hooks must ask: {out[:200]!r}")

    def test_strip_suffix_glue_ask(self):
        out = _hook(self.root, "rm -rf ${X%zzz}hooks")
        self.assertTrue(self._asked(out), f"${{X%zzz}}hooks must ask: {out[:200]!r}")

    def test_patsub_glue_ask(self):
        out = _hook(self.root, "rm -rf ${X//y/z}hooks")
        self.assertTrue(self._asked(out), f"${{X//y/z}}hooks must ask: {out[:200]!r}")

    # ---- regression: non-CP expansion-split must ALLOW (no false positive) ----
    def test_noncp_param_split_allowed(self):
        out = _hook(self.root, "rm -rf h${X:-ome}/cache")
        self.assertTrue(_allowed(out), f"home/cache (non-CP) must allow: {out[:200]!r}")

    def test_noncp_brace_split_allowed(self):
        out = _hook(self.root, "rm -rf {a,b}ooks")
        self.assertTrue(_allowed(out), f"aooks/books (non-CP) must allow: {out[:200]!r}")

    def test_noncp_empty_glue_allowed(self):
        out = _hook(self.root, "rm -rf build${X}")
        self.assertTrue(_allowed(out), f"build (non-CP) must allow: {out[:200]!r}")

    def test_echo_var_allowed(self):
        out = _hook(self.root, "echo $HOME")
        self.assertTrue(_allowed(out), f"echo $HOME must allow: {out[:200]!r}")


class TestBareSpecialParams(unittest.TestCase):
    """round7 盲検 break-attempt: bare special-parameter（$0-$9 / $$ $? $# $! $- $* $@）が
    augment の _VAR（`\\$[A-Za-z_]…`）にマッチせず sentinel 化されないため、`$0/hooks` 等が
    ALLOW に漏れていた（波括弧版 `${0}/hooks` は `\\$\\{…\\}` が拾い正しく ASK）。実害ある
    書込み（ROOT/hooks への解決）は再現できないが、augment の fail-safe 設計 invariant
    『静的に解決できない展開が CP 隣接なら ASK』に対する fail-open かつ波括弧版との不整合。
    bare special-param も sentinel→ASK に揃え、未解決展開を一律 ASK に収束させる。
    standalone（CP 非隣接）は誤検知ゼロで ALLOW を維持。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _asked(self, out):
        return '"permissionDecision":"ask"' in out

    # ---- bare special-param adjacent to a CP dir → ASK (fail-safe) ----
    def test_dollar0_hooks_ask(self):
        out = _hook(self.root, "rm -rf $0/hooks")
        self.assertTrue(self._asked(out), f"$0/hooks must ask: {out[:200]!r}")

    def test_dollar_pid_hooks_ask(self):
        out = _hook(self.root, "rm -rf $$/hooks")
        self.assertTrue(self._asked(out), f"$$/hooks must ask: {out[:200]!r}")

    def test_dollar_q_scripts_ask(self):
        out = _hook(self.root, "cp evil $?/scripts/x")
        self.assertTrue(self._asked(out), f"$?/scripts must ask: {out[:200]!r}")

    def test_dollar_argc_hooks_ask(self):
        out = _hook(self.root, "rm -rf $#/hooks")
        self.assertTrue(self._asked(out), f"$#/hooks must ask: {out[:200]!r}")

    def test_dollar_bang_hooks_ask(self):
        out = _hook(self.root, "rm -rf $!/hooks")
        self.assertTrue(self._asked(out), f"$!/hooks must ask: {out[:200]!r}")

    def test_dollar_dash_hooks_ask(self):
        out = _hook(self.root, "rm -rf $-/hooks")
        self.assertTrue(self._asked(out), f"$-/hooks must ask: {out[:200]!r}")

    def test_dollar_star_hooks_ask(self):
        out = _hook(self.root, "rm -rf $*/hooks")
        self.assertTrue(self._asked(out), f"$*/hooks must ask: {out[:200]!r}")

    def test_dollar_at_hooks_ask(self):
        out = _hook(self.root, "rm -rf $@/hooks")
        self.assertTrue(self._asked(out), f"$@/hooks must ask: {out[:200]!r}")

    def test_dollar_digit_templates_ask(self):
        out = _hook(self.root, "rm -rf $1/templates")
        self.assertTrue(self._asked(out), f"$1/templates must ask: {out[:200]!r}")

    # ---- redirect target built from a special-param → ASK ----
    def test_special_redirect_target_ask(self):
        out = _hook(self.root, "echo evil > $0/hooks/lib/emit.sh")
        self.assertTrue(self._asked(out), f"$0 redirect target must ask: {out[:200]!r}")

    # ---- braced form regression: still ASK ----
    def test_braced_zero_hooks_ask(self):
        out = _hook(self.root, "rm -rf ${0}/hooks")
        self.assertTrue(self._asked(out), f"${{0}}/hooks must ask: {out[:200]!r}")

    # ---- no false positive: special-param NOT adjacent to CP → ALLOW ----
    def test_standalone_special_allowed(self):
        out = _hook(self.root, "echo $$")
        self.assertTrue(_allowed(out), f"echo $$ must allow: {out[:200]!r}")

    def test_special_noncp_path_allowed(self):
        out = _hook(self.root, "rm -rf $0/build")
        self.assertTrue(_allowed(out), f"$0/build (non-CP) must allow: {out[:200]!r}")

    def test_special_arg_allowed(self):
        out = _hook(self.root, "cp $1 /tmp/dest")
        self.assertTrue(_allowed(out), f"cp $1 /tmp/dest must allow: {out[:200]!r}")

    def test_awk_field_var_allowed(self):
        out = _hook(self.root, "awk '{print $2}' notes.txt")
        self.assertTrue(_allowed(out), f"awk field $2 must not false-positive: {out[:200]!r}")


class TestGlobAndCharClass(unittest.TestCase):
    """round8 盲検 break-attempt（security agent）: glob/wildcard/char-class が
    実行時(cwd=ROOT)に実 control-plane へ展開するのに、augment GATE が『リテラル
    CP 部分文字列』を要求するため resolver 未到達で ALLOW に漏れていた（Critical・
    当初 SF-001 と同等。`glob=SF-002 runtime fundamental limit` の誤記録を是正＝
    glob は fnmatch で既知 CP 名に静的照合でき closable）。
    GATE に `?`/`*`/`[` を追加し、resolver で各 path component を CP 絶対パスへ
    prefix-fnmatch 照合 → CP に解決しうる write=deny / read=read-only carve-out で
    allow / `build/*` 等の非CP配下=allow。quoted glob は shlex posix が quote を
    剥がすため deny 側に倒れる（リテラル `hook?` は存在しない無害 path＝fail-safe FP）。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # ---- `?` glob hitting a CP dir (write) → DENY ----
    def test_qmark_dir_rm_denied(self):
        out = _hook(self.root, "rm -rf hook?")
        self.assertTrue(_denied(out), f"rm -rf hook? must deny: {out[:200]!r}")

    def test_qmark_redirect_emit_denied(self):
        out = _hook(self.root, "echo evil > hook?/lib/emit.sh")
        self.assertTrue(_denied(out), f"> hook?/lib/emit.sh must deny: {out[:200]!r}")

    def test_qmark_append_safety_denied(self):
        out = _hook(self.root, "echo evil >> hook?/lib/safety.sh")
        self.assertTrue(_denied(out), f">> hook?/lib/safety.sh must deny: {out[:200]!r}")

    def test_qmark_cp_into_denied(self):
        out = _hook(self.root, "cp evil hook?/lib/emit.sh")
        self.assertTrue(_denied(out), f"cp into hook?/lib must deny: {out[:200]!r}")

    def test_qmark_tee_denied(self):
        out = _hook(self.root, "echo evil | tee hook?/lib/emit.sh")
        self.assertTrue(_denied(out), f"tee hook?/lib must deny: {out[:200]!r}")

    def test_qmark_mv_away_denied(self):
        out = _hook(self.root, "mv hook? /tmp/gone")
        self.assertTrue(_denied(out), f"mv hook? away must deny: {out[:200]!r}")

    def test_qmark_chmod_denied(self):
        out = _hook(self.root, "chmod 000 hook?")
        self.assertTrue(_denied(out), f"chmod 000 hook? must deny: {out[:200]!r}")

    def test_qmark_truncate_denied(self):
        out = _hook(self.root, "truncate -s0 hook?/lib/emit.sh")
        self.assertTrue(_denied(out), f"truncate hook? must deny: {out[:200]!r}")

    def test_qmark_find_delete_denied(self):
        out = _hook(self.root, "find hook? -name '*.sh' -delete")
        self.assertTrue(_denied(out), f"find hook? -delete must deny: {out[:200]!r}")

    # ---- `*` glob → DENY ----
    def test_star_dir_denied(self):
        out = _hook(self.root, "rm -rf hook*")
        self.assertTrue(_denied(out), f"rm -rf hook* must deny: {out[:200]!r}")

    def test_bare_star_denied(self):
        out = _hook(self.root, "rm -rf *")
        self.assertTrue(_denied(out), f"rm -rf * (matches hooks) must deny: {out[:200]!r}")

    def test_star_scripts_denied(self):
        out = _hook(self.root, "rm -rf script*")
        self.assertTrue(_denied(out), f"rm -rf script* must deny: {out[:200]!r}")

    def test_star_templates_denied(self):
        out = _hook(self.root, "rm -rf template*")
        self.assertTrue(_denied(out), f"rm -rf template* must deny: {out[:200]!r}")

    # ---- char-class spelling out a CP name → DENY ----
    def test_charclass_full_hooks_denied(self):
        out = _hook(self.root, "rm -rf [h][o][o][k][s]")
        self.assertTrue(_denied(out), f"[h][o][o][k][s] must deny: {out[:200]!r}")

    def test_charclass_partial_hooks_denied(self):
        out = _hook(self.root, "rm -rf [h]ooks")
        self.assertTrue(_denied(out), f"[h]ooks must deny: {out[:200]!r}")

    def test_charclass_scripts_denied(self):
        out = _hook(self.root, "rm -rf s[c]ripts")
        self.assertTrue(_denied(out), f"s[c]ripts must deny: {out[:200]!r}")

    def test_multi_qmark_hooks_denied(self):
        out = _hook(self.root, "rm -rf h??ks")
        self.assertTrue(_denied(out), f"h??ks must deny: {out[:200]!r}")

    # ---- file CPs (STATUS.md / CLAUDE.md) via glob → DENY ----
    def test_status_glob_redirect_denied(self):
        out = _hook(self.root, "echo evil > docs/STATUS.m?")
        self.assertTrue(_denied(out), f"docs/STATUS.m? must deny: {out[:200]!r}")

    def test_claude_md_glob_suffix_denied(self):
        out = _hook(self.root, "cp evil CLAUDE.m?")
        self.assertTrue(_denied(out), f"CLAUDE.m? must deny: {out[:200]!r}")

    def test_claude_md_glob_mid_denied(self):
        out = _hook(self.root, "cp evil CLAUD?.md")
        self.assertTrue(_denied(out), f"CLAUD?.md must deny: {out[:200]!r}")

    def test_claude_md_charclass_denied(self):
        out = _hook(self.root, "cp evil [C]LAUDE.md")
        self.assertTrue(_denied(out), f"[C]LAUDE.md must deny: {out[:200]!r}")

    # ---- .claude dir via glob → DENY ----
    def test_dotclaude_glob_file_denied(self):
        out = _hook(self.root, "cp evil .clau??/settings.json")
        self.assertTrue(_denied(out), f".clau??/settings.json must deny: {out[:200]!r}")

    def test_dotclaude_glob_dir_denied(self):
        out = _hook(self.root, "rm -rf .claud?")
        self.assertTrue(_denied(out), f"rm -rf .claud? must deny: {out[:200]!r}")

    # ---- quoted glob: shlex strips quotes → fail-safe DENY (documented) ----
    def test_quoted_glob_failsafe_denied(self):
        out = _hook(self.root, 'cp evil "hook?/lib/emit.sh"')
        self.assertTrue(_denied(out), f"quoted hook? is fail-safe deny: {out[:200]!r}")

    # ---- literal + glob: clear literal CP keeps DENY (no downgrade) ----
    def test_literal_and_glob_denied(self):
        out = _hook(self.root, "rm -rf hooks/ build?")
        self.assertTrue(_denied(out), f"literal hooks/ + glob must deny: {out[:200]!r}")

    # ---- reads of CP via glob → ALLOW (read-only carve-out) ----
    def test_glob_read_ls_allowed(self):
        out = _hook(self.root, "ls hook?")
        self.assertTrue(_allowed(out), f"ls hook? (read) must allow: {out[:200]!r}")

    def test_glob_read_cat_allowed(self):
        out = _hook(self.root, "cat hook?/lib/emit.sh")
        self.assertTrue(_allowed(out), f"cat hook?/... (read) must allow: {out[:200]!r}")

    # ---- negatives: glob NOT resolving to CP → ALLOW (no false positive) ----
    def test_neg_build_glob_allowed(self):
        out = _hook(self.root, "rm -rf buil?")
        self.assertTrue(_allowed(out), f"rm -rf buil? (non-CP) must allow: {out[:200]!r}")

    def test_neg_dist_star_allowed(self):
        out = _hook(self.root, "rm -rf dis*")
        self.assertTrue(_allowed(out), f"rm -rf dis* (non-CP) must allow: {out[:200]!r}")

    def test_neg_glob_under_noncp_allowed(self):
        out = _hook(self.root, "rm -rf build/*")
        self.assertTrue(_allowed(out), f"build/* (glob under non-CP) must allow: {out[:200]!r}")

    def test_neg_cp_into_noncp_glob_allowed(self):
        out = _hook(self.root, "cp foo.txt bar*")
        self.assertTrue(_allowed(out), f"cp foo.txt bar* (non-CP) must allow: {out[:200]!r}")

    def test_neg_star_suffix_allowed(self):
        out = _hook(self.root, "cat *.py")
        self.assertTrue(_allowed(out), f"cat *.py (non-CP read) must allow: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
