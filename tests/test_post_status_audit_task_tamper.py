#!/usr/bin/env python3
"""iter43 Task 4: post-status-audit.sh が task_type/task_size の改竄を
tamper-evidence する契約（I3 / SF-006）。

- raw Edit による task_size:L→S は block（必須 gate skip 防止）
- raw Edit による task_type:locked→framework は block（moat 解錠防止）
- update-task.sh 経由の正当変更は後続編集で block されない
- 旧形式 snapshot（task 行なし）は移行猶予で block しない
- 改竄 task_type 編集は cp_apply 到達前に block＝当該セッションで moat 維持
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


def _status(task_type: str = "framework", task_size: str = "L") -> str:
    return (
        f"---\nframework: aegis\nmode: Dev\nphase: implement\n"
        f"iteration: 43\ntask_type: {task_type}\ntask_size: {task_size}\n"
        "gate_approvals:\n"
        "  client_ready_for_dev: n/a\n"
        "  brainstorm: approved\n"
        "  plan: approved\n"
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


def _snapshot(task_type: str | None = "framework", task_size: str | None = "L") -> str:
    lines = [
        "gate_approvals:",
        "  client_ready_for_dev: n/a",
        "  brainstorm: approved",
        "  plan: approved",
        "  review: pending",
        "  qa: pending",
        "  security: pending",
        "  deploy: pending",
        "  dev_ready_for_client: pending",
        "phase: implement",
        "mode: Dev",
    ]
    if task_type is not None:
        lines.append(f"task_type: {task_type}")
    if task_size is not None:
        lines.append(f"task_size: {task_size}")
    return "\n".join(lines) + "\n"


def _scratch(status: str, snapshot: str | None) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=p, check=True,
                   capture_output=True)
    shutil.copytree(ROOT / "hooks", p / "hooks")
    shutil.copytree(ROOT / "scripts", p / "scripts")
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(status, encoding="utf-8")
    (p / ".claude").mkdir()
    if snapshot is not None:
        (p / ".claude" / ".gate-snapshot").write_text(snapshot, encoding="utf-8")
    return tmp


def _audit(p: Path) -> tuple[int, str]:
    payload = json.dumps({
        "hook_event_name": "PostToolUse", "tool_name": "Edit",
        "tool_input": {"file_path": str(p / "docs" / "STATUS.md")},
    })
    r = subprocess.run(
        ["bash", str(p / "hooks" / "post-status-audit.sh")],
        input=payload, capture_output=True, text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(p)},
    )
    return r.returncode, r.stdout


def _is_block(out: str) -> bool:
    return '"decision":"block"' in out.replace(" ", "")


def _unlock_tree(p: Path) -> None:
    subprocess.run(["chmod", "-R", "u+w", str(p)], capture_output=True)


class TestTaskTamper(unittest.TestCase):

    def test_size_downgrade_is_blocked(self):
        # snapshot says L; STATUS now says S (tampered)
        with _scratch(_status(task_size="S"), _snapshot(task_size="L")) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out), f"size L→S must block: {out!r}")
                self.assertIn("task-tamper", out)
            finally:
                _unlock_tree(p)

    def test_type_change_is_blocked(self):
        with _scratch(_status(task_type="bugfix"), _snapshot(task_type="framework")) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out), f"type change must block: {out!r}")
                self.assertIn("task-tamper", out)
            finally:
                _unlock_tree(p)

    def test_matching_task_fields_not_blocked(self):
        with _scratch(_status(), _snapshot()) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertFalse(_is_block(out), f"unchanged must not block: {out!r}")
            finally:
                _unlock_tree(p)

    def test_old_format_snapshot_migration_grace(self):
        # snapshot has NO task fields (old install); STATUS has them → grace.
        with _scratch(_status(), _snapshot(task_type=None, task_size=None)) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertFalse(_is_block(out), f"old snapshot must grace: {out!r}")
            finally:
                _unlock_tree(p)

    def test_authorized_update_task_then_edit_not_blocked(self):
        """review Major: update-task.sh で task_type を変えた後、その値に一致する
        STATUS への後続編集は false-block されない（snapshot 同期の end-to-end 契約）。"""
        with _scratch(_status(task_type="framework"), _snapshot(task_type="framework")) as tmp:
            p = Path(tmp)
            try:
                # authorized change framework→bugfix via update-task.sh
                r = subprocess.run(
                    ["bash", str(p / "scripts" / "update-task.sh"), "--type", "bugfix"],
                    capture_output=True, text=True,
                )
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                snap = (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")
                self.assertIn("task_type: bugfix", snap, f"snapshot not synced: {snap!r}")
                # a subsequent benign raw edit (STATUS already bugfix == snapshot) must NOT block
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertFalse(
                    _is_block(out),
                    f"authorized change must leave subsequent edits unblocked: {out!r}",
                )
            finally:
                _unlock_tree(p)

    def test_sf010_empty_baseline_size_injection_blocked(self):
        # SF-010: snapshot は現行フォーマット（task_type あり）だが task_size 行なし
        # → STATUS への raw-Edit task_size 追加は block（現行は grace で素通り＝RED）
        with _scratch(_status(task_size="S"),
                      _snapshot(task_type="framework", task_size=None)) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out),
                                f"empty-baseline size injection must block: {out!r}")
                self.assertIn("task-tamper", out)
            finally:
                _unlock_tree(p)

    def test_task_type_removal_blocked_self_defense(self):
        # grace を開ける前段（task_type 行の除去）自体が block される
        status_no_type = _status().replace("task_type: framework\n", "")
        with _scratch(status_no_type, _snapshot()) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out),
                                f"task_type removal must block: {out!r}")
            finally:
                _unlock_tree(p)

    def test_gate_line_missing_in_snapshot_injection_blocked(self):
        # SF-010 (iii) empty-baseline class: snapshot の gate ブロックに deploy 行が
        # 欠落 → STATUS raw-Edit で deploy: approved は block（現行は grace＝RED）
        status = _status().replace("  deploy: pending\n", "  deploy: approved\n")
        snapshot = _snapshot().replace("  deploy: pending\n", "")
        with _scratch(status, snapshot) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out),
                                f"gate empty-baseline injection must block: {out!r}")
                self.assertIn("gate-tamper", out)
            finally:
                _unlock_tree(p)

    def test_unlock_tamper_keeps_moat_locked_in_session(self):
        """bugfix(locked)→framework の改竄編集は cp_apply 到達前に block＝
        当該セッションで hooks/ は解錠されない。"""
        with _scratch(_status(task_type="framework"), _snapshot(task_type="bugfix")) as tmp:
            p = Path(tmp)
            try:
                # Pre-lock the CP (simulate a bugfix session's locked moat).
                subprocess.run(
                    ["bash", "-c",
                     f'source "{p}/hooks/lib/cp-lock.sh"; aegis_cp_lock "{p}"'],
                    capture_output=True,
                )
                self.assertFalse(os.access(p / "hooks", os.W_OK),
                                 "precondition: hooks/ should be locked")
                rc, out = _audit(p)
                self.assertTrue(_is_block(out), f"unlock tamper must block: {out!r}")
                # cp_apply must NOT have run (it's after the tamper check) → still locked
                self.assertFalse(
                    os.access(p / "hooks", os.W_OK),
                    "moat must stay locked: cp_apply ran before the tamper block",
                )
            finally:
                _unlock_tree(p)


if __name__ == "__main__":
    unittest.main()
