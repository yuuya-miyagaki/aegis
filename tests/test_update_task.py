#!/usr/bin/env python3
"""iter43 Task 3: scripts/update-task.sh — task_type/task_size の
authorized write-path 契約。

raw Edit による task_type/task_size 改竄を block するのに対応する「正当な
変更経路」。Bash 経由実行で post-status-audit を自然バイパスし、STATUS と
snapshot をアトミックに一致更新する。task_type 変更時は moat を再適用する。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update-task.sh"

STATUS = (
    "---\nframework: aegis\nmode: Dev\nphase: brainstorm\n"
    "task_type: framework\ntask_size: L\n"
    'task_size_rationale: "do not clobber me"\n'
    "iteration: 43\n"
    "gate_approvals:\n"
    "  client_ready_for_dev: n/a\n"
    "  brainstorm: pending\n"
    "  plan: pending\n"
    "  review: pending\n"
    "  qa: pending\n"
    "  security: pending\n"
    "  deploy: pending\n"
    "  dev_ready_for_client: pending\n"
    "current_refs:\n"
    "  requirements: null\n"
    "blockers: []\n"
    "failure_tracking: null\n"
    'last_updated: "2026-06-24T00:00:00Z"\n'
    "---\n"
)


def _scratch(status: str = STATUS) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    shutil.copytree(ROOT / "hooks", p / "hooks")
    shutil.copytree(ROOT / "scripts", p / "scripts")
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(status, encoding="utf-8")
    (p / ".claude").mkdir()
    return tmp


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(root / "scripts" / "update-task.sh"), *args],
        capture_output=True, text=True,
    )


def _status(p: Path) -> str:
    return (p / "docs" / "STATUS.md").read_text(encoding="utf-8")


def _snap(p: Path) -> str:
    f = p / ".claude" / ".gate-snapshot"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def _unlock_tree(p: Path) -> None:
    """Re-grant write so TemporaryDirectory cleanup doesn't fail on a locked CP."""
    subprocess.run(["chmod", "-R", "u+w", str(p)], capture_output=True)


class TestUpdateTask(unittest.TestCase):

    def test_change_size_updates_status_and_snapshot(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                r = _run(p, "--size", "M")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("task_size: M", _status(p))
                self.assertIn("task_size: M", _snap(p))
            finally:
                _unlock_tree(p)

    def test_change_type_updates_status_and_snapshot(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                r = _run(p, "--type", "bugfix")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("task_type: bugfix", _status(p))
                self.assertIn("task_type: bugfix", _snap(p))
            finally:
                _unlock_tree(p)

    def test_change_both_in_one_call(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                r = _run(p, "--type", "refactor", "--size", "S")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                s = _status(p)
                self.assertIn("task_type: refactor", s)
                self.assertIn("task_size: S", s)
            finally:
                _unlock_tree(p)

    def test_reject_invalid_size(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                r = _run(p, "--size", "XL")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("task_size: L", _status(p))  # unchanged
            finally:
                _unlock_tree(p)

    def test_reject_invalid_type(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                r = _run(p, "--type", "wibble")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("task_type: framework", _status(p))  # unchanged
            finally:
                _unlock_tree(p)

    def test_no_args_is_usage_error(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                r = _run(p)
                self.assertNotEqual(r.returncode, 0)
            finally:
                _unlock_tree(p)

    def test_rationale_not_clobbered_on_size_change(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                _run(p, "--size", "M")
                self.assertIn('task_size_rationale: "do not clobber me"', _status(p))
            finally:
                _unlock_tree(p)

    def test_type_change_to_nonframework_locks_moat(self):
        """framework→bugfix で aegis_cp_apply が CP を施錠する（hooks 不可書）。"""
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                # framework start → hooks writable. Switch to bugfix → lock.
                r = _run(p, "--type", "bugfix")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertFalse(
                    os.access(p / "hooks", os.W_OK),
                    "hooks/ should be locked (non-writable) after switching to bugfix",
                )
            finally:
                _unlock_tree(p)

    def test_size_added_when_line_absent(self):
        """grill-code Critical: task_size 行が無い STATUS（新規プロジェクト）に
        --size で行を新規付与できる（黙って no-op しない）。"""
        status = STATUS.replace("task_size: L\n", "")  # remove the task_size line
        with _scratch(status) as tmp:
            p = Path(tmp)
            try:
                self.assertNotIn("task_size:", _status(p))  # precondition
                r = _run(p, "--size", "M")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("task_size: M", _status(p))
                self.assertIn("task_size: M", _snap(p))
            finally:
                _unlock_tree(p)

    def test_type_absent_errors_not_silent(self):
        """task_type 行が無いのに --type を指定したら黙らずエラー（schema 違反）。"""
        status = STATUS.replace("task_type: framework\n", "")
        with _scratch(status) as tmp:
            p = Path(tmp)
            try:
                r = _run(p, "--type", "bugfix")
                self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
            finally:
                _unlock_tree(p)

    def test_sequential_calls_release_lock(self):
        with _scratch() as tmp:
            p = Path(tmp)
            try:
                r1 = _run(p, "--size", "M")
                r2 = _run(p, "--size", "S")
                self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
                self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
                self.assertIn("task_size: S", _status(p))
            finally:
                _unlock_tree(p)


class TestEnumParity(unittest.TestCase):
    """review Minor: update-task.sh のハードコード enum が check_status.py の
    正本 (ALLOWED_TASK_TYPES / ALLOWED_TASK_SIZES) と一致することを契約。
    片方だけ更新すると update-task.sh が正当な値を黙って拒否する drift を防ぐ。"""

    def _bash_set(self, var: str) -> set:
        import re
        text = (ROOT / "scripts" / "update-task.sh").read_text(encoding="utf-8")
        m = re.search(rf'^{var}="([^"]*)"', text, re.M)
        assert m, f"{var} not found in update-task.sh"
        return set(m.group(1).split())

    def _py_set(self, name: str) -> set:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_status  # noqa: E402
        return set(getattr(check_status, name))

    def test_task_types_match(self):
        self.assertEqual(self._bash_set("VALID_TASK_TYPES"),
                         self._py_set("ALLOWED_TASK_TYPES"))

    def test_task_sizes_match(self):
        self.assertEqual(self._bash_set("VALID_TASK_SIZES"),
                         self._py_set("ALLOWED_TASK_SIZES"))


if __name__ == "__main__":
    unittest.main()
