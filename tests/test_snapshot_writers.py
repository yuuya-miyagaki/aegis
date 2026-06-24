#!/usr/bin/env python3
"""iter43 Task 2: 3 つの snapshot writer が共有 helper 経由で
task_type/task_size を snapshot に書くことの契約。

session-start.sh / update-gate.sh / post-status-audit.sh はいずれも
aegis_write_snapshot を呼び、snapshot に task_type/task_size が入る。
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

STATUS = (
    "---\nframework: aegis\nmode: Dev\nphase: implement\n"
    "iteration: 43\ntask_type: framework\ntask_size: L\n"
    'task_size_rationale: "guard against clobber"\n'
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


def _scratch() -> tempfile.TemporaryDirectory:
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
    (p / "docs" / "STATUS.md").write_text(STATUS, encoding="utf-8")
    (p / ".claude").mkdir()
    return tmp


class TestSnapshotWriters(unittest.TestCase):

    def _snap(self, p: Path) -> str:
        return (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")

    def test_session_start_writes_task_fields(self):
        with _scratch() as tmp:
            p = Path(tmp)
            subprocess.run(
                ["bash", str(p / "hooks" / "session-start.sh")],
                input="", capture_output=True, text=True,
            )
            snap = self._snap(p)
            self.assertIn("task_type: framework", snap, snap)
            self.assertIn("task_size: L", snap, snap)

    def test_post_status_audit_regen_writes_task_fields(self):
        with _scratch() as tmp:
            p = Path(tmp)
            # Pre-create a valid (phase/mode present) snapshot matching STATUS so
            # the audit reaches the end-of-run regen (not first-edit allowance).
            (p / ".claude" / ".gate-snapshot").write_text(
                "gate_approvals:\n  brainstorm: pending\nphase: implement\nmode: Dev\n",
                encoding="utf-8",
            )
            payload = json.dumps({
                "hook_event_name": "PostToolUse", "tool_name": "Edit",
                "tool_input": {"file_path": str(p / "docs" / "STATUS.md")},
            })
            subprocess.run(
                ["bash", str(p / "hooks" / "post-status-audit.sh")],
                input=payload, capture_output=True, text=True,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(p)},
            )
            snap = self._snap(p)
            self.assertIn("task_type: framework", snap, snap)
            self.assertIn("task_size: L", snap, snap)

    def test_update_gate_writes_task_fields(self):
        with _scratch() as tmp:
            p = Path(tmp)
            r = subprocess.run(
                ["bash", str(p / "scripts" / "update-gate.sh"), "brainstorm", "approve"],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            snap = self._snap(p)
            self.assertIn("task_type: framework", snap, snap)
            self.assertIn("task_size: L", snap, snap)

    def test_task_size_rationale_not_captured(self):
        """grep ^task_size: は task_size_rationale を巻き込まない。"""
        with _scratch() as tmp:
            p = Path(tmp)
            subprocess.run(
                ["bash", str(p / "hooks" / "session-start.sh")],
                input="", capture_output=True, text=True,
            )
            snap = self._snap(p)
            self.assertNotIn("rationale", snap, snap)


if __name__ == "__main__":
    unittest.main()
