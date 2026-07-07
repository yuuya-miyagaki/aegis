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

    # -- iter61 (full-review 2026-07-06 R1): session-start must not launder a
    # gate revert into the snapshot — the snapshot is the recovery anchor that
    # made the iter60 incident recoverable, and an unconditional regeneration
    # at the next session boundary would destroy it.

    def test_session_start_preserves_snapshot_on_gate_regression(self):
        with _scratch() as tmp:
            p = Path(tmp)
            r = subprocess.run(
                ["bash", str(p / "scripts" / "update-gate.sh"),
                 "brainstorm", "approve"],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("brainstorm: approved", self._snap(p))
            # simulate the incident: STATUS reverted behind the writers' back
            status = p / "docs" / "STATUS.md"
            status.write_text(
                status.read_text(encoding="utf-8").replace(
                    "  brainstorm: approved", "  brainstorm: pending"
                ),
                encoding="utf-8",
            )
            r2 = subprocess.run(
                ["bash", str(p / "hooks" / "session-start.sh")],
                input="", capture_output=True, text=True,
            )
            snap = self._snap(p)
            self.assertIn("brainstorm: approved", snap,
                          "regression must preserve the earned snapshot: " + snap)
            self.assertIn("復旧アンカーとして温存", r2.stdout, r2.stdout + r2.stderr)

    def test_session_start_rewrites_snapshot_when_no_regression(self):
        with _scratch() as tmp:
            p = Path(tmp)
            r = subprocess.run(
                ["bash", str(p / "scripts" / "update-gate.sh"),
                 "brainstorm", "approve"],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            # non-gate STATUS change: snapshot must be refreshed, no warning
            status = p / "docs" / "STATUS.md"
            status.write_text(
                status.read_text(encoding="utf-8").replace(
                    "task_size: L", "task_size: M"
                ),
                encoding="utf-8",
            )
            r2 = subprocess.run(
                ["bash", str(p / "hooks" / "session-start.sh")],
                input="", capture_output=True, text=True,
            )
            snap = self._snap(p)
            self.assertIn("task_size: M", snap, snap)
            self.assertIn("brainstorm: approved", snap, snap)
            self.assertNotIn("復旧アンカーとして温存", r2.stdout, r2.stdout)

    def test_session_start_no_warning_after_authorized_reset(self):
        """正規の update-gate reset は snapshot を同時更新する＝直後の
        session-start は退行を検知せず無警告で再生成する（誤検知ゼロの生命線・
        盲検2次 m-3 の pin）。"""
        with _scratch() as tmp:
            p = Path(tmp)
            for action in ("approve", "reset"):
                r = subprocess.run(
                    ["bash", str(p / "scripts" / "update-gate.sh"),
                     "brainstorm", action],
                    capture_output=True, text=True,
                )
                self.assertEqual(r.returncode, 0, action + ": " + r.stdout + r.stderr)
            r2 = subprocess.run(
                ["bash", str(p / "hooks" / "session-start.sh")],
                input="", capture_output=True, text=True,
            )
            self.assertIn("brainstorm: pending", self._snap(p))
            self.assertNotIn("復旧アンカーとして温存", r2.stdout, r2.stdout)

    def test_regression_guard_fail_open_without_snapshot(self):
        """snapshot 不在 → 現行動作（生成）。ガードが session を brick しない。"""
        with _scratch() as tmp:
            p = Path(tmp)
            r = subprocess.run(
                ["bash", str(p / "hooks" / "session-start.sh")],
                input="", capture_output=True, text=True,
            )
            self.assertTrue((p / ".claude" / ".gate-snapshot").is_file(),
                            r.stdout + r.stderr)
            self.assertNotIn("復旧アンカーとして温存", r.stdout, r.stdout)

    def test_regression_guard_bounded_on_bloated_snapshot(self):
        """巨大 snapshot でも定数回の fork で完了する（2nd-review security
        Major-2: 行ごとの sed fork は session-start を数分ハングさせた）。
        50k 行を秒オーダで処理できること＝行ごと fork していないことの回帰。"""
        import time
        with _scratch() as tmp:
            p = Path(tmp)
            snap = p / ".claude" / ".gate-snapshot"
            snap.write_text(
                "gate_approvals:\n"
                + "  brainstorm: approved\n" * 50000
                + "phase: implement\nmode: Dev\n",
                encoding="utf-8",
            )
            # source the lib and call the guard directly (bounds the unit under test)
            script = (
                'source "%s"; aegis_snapshot_gate_regression "%s"; echo "rc=$?"'
                % (p / "hooks" / "lib" / "snapshot.sh", p)
            )
            start = time.monotonic()
            r = subprocess.run(["bash", "-c", script],
                               capture_output=True, text=True, timeout=30)
            elapsed = time.monotonic() - start
            # STATUS has brainstorm: pending (scaffold default) vs snapshot approved
            # => regression detected (rc0). The point is it returns quickly.
            self.assertIn("rc=0", r.stdout, r.stdout + r.stderr)
            self.assertLess(elapsed, 15.0,
                            f"guard took {elapsed:.1f}s on 50k lines (per-line fork?)")


if __name__ == "__main__":
    unittest.main()
