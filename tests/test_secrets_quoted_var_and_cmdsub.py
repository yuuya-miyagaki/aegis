#!/usr/bin/env python3
"""K-3 / K-4 (v1.6.2): check-secrets.sh の bypass を塞ぐ。

第6回 Phase A:
  REDTEAM-03: F=.env; git add "${F}"            — クォート付き変数で素通り
  REDTEAM-04: $(echo git) add .env             — git 自体をコマンド置換で構築

加えて grill 要検討 2 で false-positive 抑止:
  - $(date +%s).env_var_name=foo               — .env はアイデンティファイア中
  - $(echo cat) .env.example                   — safe variant
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-secrets.sh"


def _scratch_project() -> tempfile.TemporaryDirectory:
    """git init + hooks/check-secrets.sh + lib をセットアップ。"""
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=p, check=True,
                   capture_output=True)
    # initial commit so git diff --cached works
    (p / "seed.txt").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=p, check=True,
                   capture_output=True)
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(HOOK, hooks_dir / "check-secrets.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "frontmatter.sh",
                "secrets-patterns.sh", "safety.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-secrets.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


_PERMISSION_DENY = '"permissionDecision":"deny"'
_PERMISSION_ASK = '"permissionDecision":"ask"'


def _is_blocked(out: str) -> bool:
    return _PERMISSION_DENY in out or _PERMISSION_ASK in out


class TestK3QuotedVar(unittest.TestCase):
    """REDTEAM-03: クォート付き変数 `"${F}"` で .env がステージできる。
    ASK に倒す（fail-closed）。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_project()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _assert_blocked(self, cmd: str):
        out = _hook(self.root, cmd)
        self.assertTrue(_is_blocked(out),
                        f"K-3 PoC must NOT pass: cmd={cmd!r}, out={out[:200]!r}")

    def test_quoted_double_brace_var_dotenv_blocked(self):
        """REDTEAM-03 主 PoC"""
        self._assert_blocked('F=.env; git add "${F}"')

    def test_quoted_single_brace_var_dotenv_blocked(self):
        self._assert_blocked('F=.env; git add "$F"')

    def test_quoted_var_stage_alias_blocked(self):
        self._assert_blocked('F=.env; git stage "${F}"')

    def test_quoted_var_with_git_C_blocked(self):
        self._assert_blocked('F=.env; git -C . add "${F}"')

    def test_single_quote_var_dotenv_blocked(self):
        """単一クォートは展開されないが、静的に区別する必然性は薄いので
        ASK 側に倒す（fail-closed）"""
        self._assert_blocked("F=.env; git add '${F}'")


class TestK4CmdsubBuiltGit(unittest.TestCase):
    """REDTEAM-04: `$(echo git) add .env` で git 検出 regex を完全迂回。
    `cmd` がコマンド置換 / backtick を含み、かつ word boundary 付き .env / 高
    リスク認証ファイルを含めば ASK。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_project()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _assert_blocked(self, cmd: str):
        out = _hook(self.root, cmd)
        self.assertTrue(_is_blocked(out),
                        f"K-4 PoC must NOT pass: cmd={cmd!r}, out={out[:200]!r}")

    def test_cmdsub_git_add_dotenv_blocked(self):
        """REDTEAM-04 主 PoC"""
        self._assert_blocked('$(echo git) add .env')

    def test_backtick_git_add_dotenv_blocked(self):
        self._assert_blocked('`echo git` add .env')

    def test_cmdsub_git_add_pem_blocked(self):
        self._assert_blocked('$(echo git) add server.pem')

    def test_cmdsub_git_add_id_rsa_blocked(self):
        self._assert_blocked('$(echo git) add ~/.ssh/id_rsa')

    def test_cmdsub_nested_blocked(self):
        """ネストした cmdsub も検出"""
        self._assert_blocked('$(echo $(echo git)) add .env')


class TestK4FalsePositiveAvoidance(unittest.TestCase):
    """grill 要検討 2: false-positive 抑止。
    .env が word-boundary を満たさない（mid-identifier）、または safe variant
    （.env.example / .env.template / .env.sample）は ASK にしてはいけない。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_project()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _assert_allowed(self, cmd: str):
        out = _hook(self.root, cmd)
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"false-positive deny: cmd={cmd!r}, out={out!r}")
        self.assertNotIn(_PERMISSION_ASK, out,
                         f"false-positive ask: cmd={cmd!r}, out={out!r}")

    def test_dotenv_inside_identifier_allowed(self):
        """`.env_var_name` のような中間文字列は word boundary 違反"""
        self._assert_allowed('$(date +%s).env_var_name=foo')

    def test_dotenv_example_allowed(self):
        """safe variant .env.example は許可"""
        self._assert_allowed('$(echo cat) .env.example')

    def test_dotenv_template_allowed(self):
        self._assert_allowed('$(echo cp) src/.env.template /tmp/foo')

    def test_dotenv_sample_allowed(self):
        self._assert_allowed('$(echo cat) src/.env.sample')

    def test_cmdsub_without_dotenv_allowed(self):
        """cmdsub あっても .env も認証ファイルも参照しないなら ASK しない"""
        self._assert_allowed('$(date +%s)')

    def test_cmdsub_unrelated_command_allowed(self):
        self._assert_allowed('echo $(date +%s) > /tmp/x.txt')


if __name__ == "__main__":
    unittest.main()
