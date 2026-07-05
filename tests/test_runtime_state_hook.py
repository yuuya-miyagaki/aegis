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
