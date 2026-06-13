#!/usr/bin/env python3
"""K-7 (v1.6.2) grill 要検討 4: snapshot 部分破損の consumer 側ポリシー。

post-status-audit.sh は snapshot を消費して phase/mode タンパー検出に使う。
v1.6.1 までは `[ -n "$OLD_PHASE" ]` のガードで空文字を素通りさせていたため、
snapshot 破損 → タンパー検出 bypass の経路が存在した。

K-7 policy:
  - snapshot ファイル不在 → 初回 Edit とみなし allow + audit-skip.log に記録
  - snapshot ファイル存在 + phase 欠落 → fail-closed（明示 deny）
  - snapshot ファイル存在 + mode 欠落 → fail-closed
  - audit-skip.log が 3 行以上 → 次セッション SessionStart で warning
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


def _scratch_with_status() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=p, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=p, check=True,
                   capture_output=True)
    shutil.copytree(ROOT / "hooks", p / "hooks")
    shutil.copytree(ROOT / "scripts", p / "scripts")
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "iteration: 1\ntask_type: feature\n"
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
        "last_updated: \"2026-06-13T00:00:00Z\"\n"
        "---\n",
        encoding="utf-8",
    )
    (p / ".claude").mkdir()
    return tmp


def _run_audit(root: Path) -> tuple[int, str, str]:
    payload = json.dumps({
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(root / "docs" / "STATUS.md")},
    })
    r = subprocess.run(
        ["bash", str(root / "hooks" / "post-status-audit.sh")],
        input=payload, capture_output=True, text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)},
    )
    return r.returncode, r.stdout, r.stderr


class TestSnapshotConsumerPolicy(unittest.TestCase):

    def test_missing_snapshot_is_first_edit_allowance(self):
        """snapshot ファイル不在 → allow + audit-skip.log に記録"""
        with _scratch_with_status() as tmp:
            p = Path(tmp)
            snap = p / ".claude" / ".gate-snapshot"
            self.assertFalse(snap.exists())
            rc, out, _ = _run_audit(p)
            self.assertEqual(rc, 0)
            # Must NOT be a deny (audit-block) — first-edit is allowed
            self.assertNotIn(
                '"decision":"block"', out.replace(" ", ""),
                f"first edit (no snapshot) must not block: {out!r}"
            )
            # audit-skip.log は記録される
            log = p / ".claude" / ".audit-skip.log"
            self.assertTrue(
                log.exists(),
                "first-edit allowance must log to .claude/.audit-skip.log"
            )

    def test_empty_phase_in_snapshot_is_fail_closed(self):
        """snapshot 存在 + phase 行が空文字 → 明示 deny（block）"""
        with _scratch_with_status() as tmp:
            p = Path(tmp)
            snap = p / ".claude" / ".gate-snapshot"
            snap.parent.mkdir(parents=True, exist_ok=True)
            snap.write_text(
                "gate_approvals:\n  brainstorm: pending\nmode: Dev\nphase:\n",
                encoding="utf-8"
            )
            rc, out, _ = _run_audit(p)
            self.assertEqual(rc, 0)
            self.assertIn(
                '"decision":"block"', out.replace(" ", ""),
                f"empty phase in snapshot must fail-closed: {out!r}"
            )

    def test_empty_mode_in_snapshot_is_fail_closed(self):
        """snapshot 存在 + mode 行が空文字 → 明示 deny"""
        with _scratch_with_status() as tmp:
            p = Path(tmp)
            snap = p / ".claude" / ".gate-snapshot"
            snap.parent.mkdir(parents=True, exist_ok=True)
            snap.write_text(
                "gate_approvals:\n  brainstorm: pending\nmode:\nphase: implement\n",
                encoding="utf-8"
            )
            rc, out, _ = _run_audit(p)
            self.assertEqual(rc, 0)
            self.assertIn(
                '"decision":"block"', out.replace(" ", ""),
                f"empty mode in snapshot must fail-closed: {out!r}"
            )


if __name__ == "__main__":
    unittest.main()
