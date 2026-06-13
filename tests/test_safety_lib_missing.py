#!/usr/bin/env python3
"""K-5 (v1.6.2): lib 欠落で全 deny hook が明示 DENY を返す契約。

第6回 Phase A F-01: `set -euo pipefail` 下で hooks/lib/*.sh の source が
失敗すると exit 1 + 空 stdout になり、Claude Code 仕様で fail-open
（操作許可）に落ちる。これは moat の根本破綻。

K-5 対策: hooks/lib/safety.sh が source 失敗を捕捉して明示 DENY を吐く。
全 deny hook の冒頭に静的 fallback ブロックを置く。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DENY_HOOKS = [
    "check-control-plane.sh",
    "check-secrets.sh",
    "check-destructive.sh",
    "check-gate.sh",
    "check-task-completed.sh",
    "check-task-created.sh",
]

# どの lib を欠落させても fail-closed であるべき (各 hook が実際に require する lib のみ)
# safety.sh は全 hook 共通の fallback ブロックで処理される。
HOOK_LIB_DEPS = {
    "check-control-plane.sh": ["emit.sh", "extract-input.sh"],
    "check-secrets.sh":       ["emit.sh", "extract-input.sh", "secrets-patterns.sh"],
    "check-destructive.sh":   ["emit.sh", "extract-input.sh", "patterns.sh"],
    "check-gate.sh":          ["emit.sh", "extract-input.sh", "frontmatter.sh"],
    "check-task-completed.sh": ["emit.sh"],
    "check-task-created.sh":  ["emit.sh", "frontmatter.sh"],
}


def _scratch_install() -> tempfile.TemporaryDirectory:
    """フル install scaffold を /tmp に作って返す。"""
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=p, check=True,
                   capture_output=True)
    # Copy framework into tmp (not symlinks so we can delete libs).
    shutil.copytree(ROOT / "hooks", p / "hooks")
    shutil.copytree(ROOT / "templates", p / "templates")
    (p / "docs").mkdir(exist_ok=True)
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    return tmp


def _run_hook(root: Path, hook: str, payload: str) -> tuple[int, str, str]:
    r = subprocess.run(
        ["bash", str(root / "hooks" / hook)],
        input=payload, capture_output=True, text=True, cwd=str(root),
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)})
    return r.returncode, r.stdout, r.stderr


class TestLibMissingFailsClosed(unittest.TestCase):
    """各 lib を消した状態で deny hook が明示 DENY を出すこと"""

    def _assert_fail_closed(self, root: Path, hook: str):
        payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        rc, out, err = _run_hook(root, hook, payload)
        # rc must be 0 (fail-CLOSED via explicit deny, not crash)
        self.assertEqual(
            rc, 0,
            f"{hook}: must rc=0 with explicit deny, not crash "
            f"(rc={rc}, stderr={err[:200]})")
        # stdout must contain a deny decision
        self.assertIn(
            '"permissionDecision":"deny"', out,
            f"{hook}: must emit explicit deny, got {out[:200]!r}")
        # The deny reason should mention integrity / safety
        self.assertTrue(
            "integrity" in out.lower() or "safety" in out.lower(),
            f"{hook}: deny reason should reference integrity / safety, "
            f"got {out[:200]!r}")

    def test_emit_lib_missing(self):
        """全 deny hook が emit.sh を require しているので、欠落で fail-closed"""
        with _scratch_install() as tmp:
            root = Path(tmp)
            (root / "hooks/lib/emit.sh").unlink()
            for hook, libs in HOOK_LIB_DEPS.items():
                if "emit.sh" not in libs:
                    continue
                with self.subTest(hook=hook):
                    self._assert_fail_closed(root, hook)

    def test_extract_input_lib_missing(self):
        """extract-input.sh を require する hook のみ fail-closed の対象"""
        with _scratch_install() as tmp:
            root = Path(tmp)
            (root / "hooks/lib/extract-input.sh").unlink()
            for hook, libs in HOOK_LIB_DEPS.items():
                if "extract-input.sh" not in libs:
                    continue
                with self.subTest(hook=hook):
                    self._assert_fail_closed(root, hook)

    def test_safety_lib_missing(self):
        """safety.sh 自身が欠落しても fallback inline で fail-closed（全 hook 対象）"""
        with _scratch_install() as tmp:
            root = Path(tmp)
            (root / "hooks/lib/safety.sh").unlink()
            for hook in DENY_HOOKS:
                with self.subTest(hook=hook):
                    self._assert_fail_closed(root, hook)

    def test_secrets_patterns_lib_missing(self):
        with _scratch_install() as tmp:
            root = Path(tmp)
            (root / "hooks/lib/secrets-patterns.sh").unlink()
            for hook, libs in HOOK_LIB_DEPS.items():
                if "secrets-patterns.sh" not in libs:
                    continue
                with self.subTest(hook=hook):
                    self._assert_fail_closed(root, hook)

    def test_frontmatter_lib_missing(self):
        with _scratch_install() as tmp:
            root = Path(tmp)
            (root / "hooks/lib/frontmatter.sh").unlink()
            for hook, libs in HOOK_LIB_DEPS.items():
                if "frontmatter.sh" not in libs:
                    continue
                with self.subTest(hook=hook):
                    self._assert_fail_closed(root, hook)


if __name__ == "__main__":
    unittest.main()
