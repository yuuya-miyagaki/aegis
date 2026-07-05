"""iter57 主 moat 交代: 残余ミニフック check-runtime-state.sh の契約 pin。

主 moat（OS-lock）が物理的に守れない領域だけを静的に守る:
  (1) runtime-state（docs/STATUS.md・.claude/ 非 lock 部＝settings*.json,
      .gate-snapshot 等）への Bash 書込み — manifest allowlist 連動・fail-closed
  (2) lock 対象 CP への unlock 形（chmod/chflags/chattr）— 明確なポリシー deny
  (3) 再帰 chmod × ルート/glob（grill 致命4: EACCES 後の最自然な自己修復
      `chmod -R u+w .` が唯一の moat を無効化する）— ASK

Harness は tests/test_scripts_manifest_hook.py と同型。
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


def _scratch_root(task_type: str = "feature",
                  include_manifest: bool = True) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        f"task_type: {task_type}\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / HOOK, hooks_dir / HOOK)
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    if include_manifest:
        (lib_dir / "scripts-manifest.tsv").symlink_to(
            ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
    return tmp


def _hook_raw(root: Path, payload: str, env: dict | None = None) -> str:
    import os
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(
        ["bash", str(root / "hooks" / HOOK)],
        input=payload, capture_output=True, text=True, cwd=str(root), env=e)
    return r.stdout


def _hook(root: Path, cmd: str, env: dict | None = None) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    return _hook_raw(root, payload, env)


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


def _asked(out: str) -> bool:
    return '"permissionDecision":"ask"' in out


def _manifest_entries() -> "tuple[list[str], list[str]]":
    """Read hooks/lib/scripts-manifest.tsv (single owner, iter55) and return
    (allow|ask paths, framework-only paths). iter57 review fix-forward: the
    retired test_scripts_manifest_hook.py::TestManifestRunnable enumerated
    EVERY entry; a representative subset would miss a per-script regression."""
    manifest = ROOT / "hooks" / "lib" / "scripts-manifest.tsv"
    allow_ask: list[str] = []
    framework_only: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        path, cls = parts[0].strip(), parts[1].strip()
        if cls in ("allow", "ask"):
            allow_ask.append(path)
        elif cls == "framework-only":
            framework_only.append(path)
    return allow_ask, framework_only


class TestRuntimeStateDeny(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_status_append_denied(self):
        out = _hook(self.root, "echo x >> docs/STATUS.md")
        self.assertTrue(_denied(out), out[:200])

    def test_status_sed_gate_tamper_denied(self):
        out = _hook(self.root, "sed -i 's/pending/approved/' docs/STATUS.md")
        self.assertTrue(_denied(out), out[:200])

    def test_bare_status_after_cd_denied(self):
        out = _hook(self.root, "cd docs && sed -i 's/x/y/' STATUS.md")
        self.assertTrue(_denied(out), out[:200])

    def test_settings_write_denied(self):
        out = _hook(self.root, "echo '{}' > .claude/settings.json")
        self.assertTrue(_denied(out), out[:200])

    def test_gate_snapshot_write_denied(self):
        out = _hook(self.root, "printf x > .claude/.gate-snapshot")
        self.assertTrue(_denied(out), out[:200])

    def test_unrelated_command_allowed(self):
        for cmd in ("echo hi", "ls src/", "npm test"):
            with self.subTest(cmd=cmd):
                self.assertTrue(_allowed(_hook(self.root, cmd)), cmd)

    def test_user_project_own_statusmd_allowed(self):
        """意図的な狭窄（grill 要検討1）: ユーザープロジェクト自身の
        foo/STATUS.md は runtime-state ではない（旧 hook は過剰 deny だった）。"""
        out = _hook(self.root, "echo note >> notes/STATUS.md")
        self.assertTrue(_allowed(out), out[:200])

    def test_deny_message_names_correct_tools(self):
        out = _hook(self.root, "echo x >> docs/STATUS.md")
        self.assertIn("update-gate.sh", out)
        self.assertIn("update-task.sh", out)

    # --- OBS-006 quoted-literal rescue (iter57 review 🔴 regression fix) ---

    def test_commit_message_mentioning_status_allowed(self):
        """`git commit -m "...docs/STATUS.md..."` は書込みでない引用リテラル → allow。"""
        for cmd in ('git commit -m "fix docs/STATUS.md rendering"',
                    "git commit -m 'update STATUS.md handling'",
                    'echo "see docs/STATUS.md for details"',
                    'printf "%s" ".claude/settings.json is here"'):
            with self.subTest(cmd=cmd):
                self.assertTrue(_allowed(_hook(self.root, cmd)), f"{cmd}: {_hook(self.root, cmd)[:200]}")

    def test_unquoted_status_write_still_denied(self):
        """未クォートの書込みターゲットは救済しない（deny 維持）。"""
        for cmd in ("sed -i 's/pending/approved/' docs/STATUS.md",
                    "echo x > docs/STATUS.md",
                    'echo x > "docs/STATUS.md"'):
            with self.subTest(cmd=cmd):
                self.assertTrue(_denied(_hook(self.root, cmd)), f"{cmd}: {_hook(self.root, cmd)[:200]}")

    def test_cmdsub_with_status_mention_fail_closed(self):
        """$(...) 併用は mask 不能 → raw fail-closed で deny 維持。"""
        out = _hook(self.root, 'echo "$(cat docs/STATUS.md)"')
        self.assertTrue(_denied(out), out[:200])

    def test_quoted_write_via_non_message_command_denied(self):
        """(c) 救済は echo/printf/git commit 限定。python3 -c で引用リテラル内の
        STATUS へ書くのは write＝deny（allowlist でない書き手を素通しにしない）。"""
        for cmd in ('python3 -c \'open("docs/STATUS.md","w").write("x")\'',
                    "perl -i -pe 's/a/b/' 'docs/STATUS.md'",
                    'echo x; cp evil "docs/STATUS.md"'):
            with self.subTest(cmd=cmd):
                self.assertTrue(_denied(_hook(self.root, cmd)),
                                f"{cmd}: {_hook(self.root, cmd)[:200]}")

    def test_unlock_claude_subdir_no_slash_uses_oslock_message(self):
        """🟡: chmod +w .claude/skills（末尾スラッシュ無し）は OS-lock 解錠 deny
        ＝task_type=framework 案内メッセージを出す（runtime-state 汎用文言でない）。"""
        out = _hook(self.root, "chmod +w .claude/skills")
        self.assertTrue(_denied(out), out[:200])
        self.assertIn("OS-lock", out)
        self.assertIn("task_type", out)


class TestUnlockFormDeny(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_chmod_unlock_on_cp_denied(self):
        for cmd in ("chmod +w hooks/", "chmod -R u+w scripts",
                    "chflags nouchg hooks/lib/emit.sh",
                    "chattr -i templates/x",
                    "chmod u+w CLAUDE.md",
                    "chmod +w .claude/skills/tdd/SKILL.md"):
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_denied(out), f"{cmd}: {out[:200]}")

    def test_deny_message_explains_oslock(self):
        out = _hook(self.root, "chmod +w hooks/")
        self.assertIn("OS-lock", out)
        self.assertIn("update-task.sh", out)

    def test_non_cp_chmod_allowed(self):
        for cmd in ("chmod 755 src/app.py", "chmod +x build/run.sh"):
            with self.subTest(cmd=cmd):
                self.assertTrue(_allowed(_hook(self.root, cmd)), cmd)

    def test_recursive_chmod_broad_asks(self):
        """grill 致命4: EACCES 後の最自然な自己修復は CP token を含まない。"""
        for cmd in ("chmod -R u+w .", "chmod -R 777 ./", "chmod u+w -R *"):
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_asked(out), f"{cmd}: {out[:200]}")

    def test_recursive_chmod_scoped_allowed(self):
        out = _hook(self.root, "chmod -R 755 src/")
        self.assertTrue(_allowed(out), out[:200])


class TestAllowlistReadOnlyStage(unittest.TestCase):
    """PORT-4〜7（旧 check-control-plane から移植）: manifest allowlist・
    read-only 迂回・safe-stderr strip・bare git stage ask の契約維持。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_manifest_script_with_status_arg_allowed(self):
        for cmd in ("python3 scripts/check_status.py docs/STATUS.md",
                    "./scripts/status_doctor.py docs/STATUS.md",
                    "bash scripts/update-gate.sh review approve"):
            with self.subTest(cmd=cmd):
                self.assertTrue(_allowed(_hook(self.root, cmd)), cmd)

    def test_manifest_script_chained_denied_with_guidance(self):
        out = _hook(self.root,
                    "python3 scripts/check_status.py docs/STATUS.md && rm -rf x")
        self.assertTrue(_denied(out), out[:200])
        self.assertIn("単体コマンド", out)

    def test_missing_manifest_fail_closed(self):
        with _scratch_root(include_manifest=False) as name:
            root = Path(name)
            out = _hook(root, "python3 scripts/check_status.py docs/STATUS.md")
            self.assertTrue(_denied(out), out[:200])

    def test_read_only_single_allowed(self):
        for cmd in ("cat docs/STATUS.md", "grep -n phase docs/STATUS.md",
                    "head -5 docs/STATUS.md", "wc -l docs/STATUS.md"):
            with self.subTest(cmd=cmd):
                self.assertTrue(_allowed(_hook(self.root, cmd)), cmd)

    def test_read_only_with_safe_stderr_allowed(self):
        for cmd in ("cat docs/STATUS.md 2>/dev/null",
                    "grep -n phase docs/STATUS.md 2>&1"):
            with self.subTest(cmd=cmd):
                self.assertTrue(_allowed(_hook(self.root, cmd)), cmd)

    def test_read_only_pipeline_allowed(self):
        out = _hook(self.root, "grep -n phase docs/STATUS.md | head -3")
        self.assertTrue(_allowed(out), out[:200])

    def test_read_with_redirect_denied(self):
        out = _hook(self.root, "cat docs/STATUS.md > /tmp/x")
        self.assertTrue(_denied(out), out[:200])

    def test_write_indicator_in_pipeline_denied(self):
        out = _hook(self.root, "cat docs/STATUS.md | tee /tmp/x")
        self.assertTrue(_denied(out), out[:200])

    def test_git_stage_status_asks(self):
        for cmd in ("git add docs/STATUS.md",
                    "git add .claude/settings.local.json"):
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_asked(out), f"{cmd}: {out[:200]}")

    def test_git_stage_forced_or_chained_denied(self):
        for cmd in ("git add -f docs/STATUS.md",
                    "git add docs/STATUS.md && git commit -m x"):
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_denied(out), f"{cmd}: {out[:200]}")

    def test_all_manifest_allow_ask_scripts_pass_in_runtime_context(self):
        """iter57 review fix-forward (retired TestManifestRunnable の全数列挙を継承):
        scripts-manifest.tsv の allow|ask 全エントリが runtime-state を伴う文脈でも
        ALLOW されることを pin。新 hook では scripts/ は RUNTIME_STATE 外＝素の実行は
        early-allow になるため、docs/STATUS.md を伴わせて manifest allowlist 経路を
        実際に通す（将来いずれか1本を誤 deny する回帰を代表3本サブセットは捕捉できない)."""
        allow_ask, _ = _manifest_entries()
        self.assertGreaterEqual(len(allow_ask), 12, "manifest allow|ask 全数")
        for path in allow_ask:
            runner = "python3" if path.endswith(".py") else "bash"
            cmd = f"{runner} {path} docs/STATUS.md"
            with self.subTest(script=path):
                out = _hook(self.root, cmd)
                self.assertTrue(_allowed(out), f"{cmd}: {out[:200]}")

    def test_all_framework_only_scripts_denied_in_runtime_context(self):
        """framework-only クラスは非 framework タスク中に runtime-state を触ると DENY
        （旧 TestManifestRunnable の framework-only DENY 回帰の受け皿）。"""
        _, framework_only = _manifest_entries()
        self.assertGreaterEqual(len(framework_only), 1, "manifest framework-only 全数")
        for path in framework_only:
            runner = "python3" if path.endswith(".py") else "bash"
            cmd = f"{runner} {path} docs/STATUS.md"
            with self.subTest(script=path):
                out = _hook(self.root, cmd)
                self.assertTrue(_denied(out), f"{cmd}: {out[:200]}")


class TestFrameworkAndFailClosed(unittest.TestCase):
    def test_framework_task_allows_everything(self):
        with _scratch_root(task_type="framework") as name:
            root = Path(name)
            for cmd in ("echo x >> docs/STATUS.md", "chmod -R u+w .",
                        "chmod +w hooks/"):
                with self.subTest(cmd=cmd):
                    self.assertTrue(_allowed(_hook(root, cmd)), cmd)

    def test_extraction_failure_with_mention_denies(self):
        """抽出不能入力（非 JSON）に runtime-state 言及 → fail-closed deny。"""
        with _scratch_root() as name:
            root = Path(name)
            out = _hook_raw(root, "not-json but mentions docs/STATUS.md here")
            self.assertTrue(_denied(out), out[:200])

    def test_extraction_failure_without_mention_allows(self):
        with _scratch_root() as name:
            root = Path(name)
            out = _hook_raw(root, "not-json and harmless")
            self.assertTrue(_allowed(out), out[:200])

    def test_case_fold_deny_when_forced(self):
        """case-insensitive FS では DOCS/STATUS.MD も同一実体（iter54 C-1 系）。"""
        with _scratch_root() as name:
            root = Path(name)
            out = _hook(root, "echo x >> DOCS/STATUS.MD",
                        env={"AEGIS_CASE_FOLD_FORCE": "1"})
            self.assertTrue(_denied(out), out[:200])

    def test_missing_status_allows(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "hooks").mkdir()
            shutil.copy2(ROOT / "hooks" / HOOK, root / "hooks" / HOOK)
            lib = root / "hooks" / "lib"
            lib.mkdir()
            for l in ("extract-input.sh", "emit.sh", "safety.sh",
                      "frontmatter.sh"):
                (lib / l).symlink_to(ROOT / "hooks" / "lib" / l)
            out = _hook(root, "echo x >> docs/STATUS.md")
            self.assertTrue(_allowed(out), out[:200])


if __name__ == "__main__":
    unittest.main()
