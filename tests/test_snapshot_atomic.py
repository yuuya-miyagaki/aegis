#!/usr/bin/env python3
"""K-7 (v1.6.2): snapshot 書込みの atomic 化契約。

第6回 Phase A F-03: post-status-audit.sh / session-start.sh / update-gate.sh
は snapshot を `> ; >> ; >>` の 3 段書込みで作る。中断（SIGKILL / OOM /
電源断）で部分書込みが残ると、`phase:` / `mode:` が欠落した snapshot に
なり、次セッションでタンパー検出が `[ -n "$OLD_PHASE" ]` ガードで素通り。

K-7 対策: tmp に組み立てて mv で原子的に置換。

grill YAGNI: 100 iter → 20 iter（確率的に十分検出可能、CI 時間短縮）。
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _setup_scratch() -> tempfile.TemporaryDirectory:
    """post-status-audit を動かせる最小 scaffold."""
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
    # 大きめの STATUS.md（中断で部分書込みになりやすくする）
    status = (
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
        "  spec: null\n"
        "blockers: []\n"
        "failure_tracking: null\n"
        "last_updated: \"2026-06-13T00:00:00Z\"\n"
        "---\n"
    )
    (p / "docs" / "STATUS.md").write_text(status, encoding="utf-8")
    (p / ".claude").mkdir()
    return tmp


class TestSnapshotAtomic(unittest.TestCase):
    """SIGKILL 中断で snapshot ファイルが部分書込みにならない。
    20 回の SIGKILL 介入で、snapshot ファイルが存在する状態では必ず
    phase: / mode: の両方が含まれていることを契約。"""

    def test_snapshot_is_atomic_under_sigkill(self):
        with _setup_scratch() as tmp:
            p = Path(tmp)
            snapshot = p / ".claude" / ".gate-snapshot"
            payload = (
                '{"hook_event_name":"PostToolUse","tool_name":"Edit",'
                '"tool_input":{"file_path":"' + str(p / "docs" / "STATUS.md") + '"}}'
            )
            for i in range(20):
                # Remove previous snapshot for a clean start
                if snapshot.exists():
                    snapshot.unlink()
                proc = subprocess.Popen(
                    ["bash", str(p / "hooks" / "post-status-audit.sh")],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, "CLAUDE_PROJECT_DIR": str(p)},
                )
                proc.stdin.write(payload.encode())
                proc.stdin.close()
                # Random small wait then kill
                time.sleep(0.001 * (i % 5))
                try:
                    proc.send_signal(signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
                # If snapshot was created at all, it MUST have both fields
                if snapshot.exists():
                    content = snapshot.read_text(encoding="utf-8")
                    if content.strip():
                        # The .tmp file MUST NOT be the visible snapshot
                        # (i.e. atomic mv happened).
                        # If we see content, both phase and mode must be there.
                        self.assertIn(
                            "phase:", content,
                            f"iter {i}: partial snapshot (no phase): "
                            f"{content!r}"
                        )
                        self.assertIn(
                            "mode:", content,
                            f"iter {i}: partial snapshot (no mode): "
                            f"{content!r}"
                        )

    def test_snapshot_tmp_file_does_not_linger(self):
        """成功した書込み後、.tmp.<pid> が残らない"""
        with _setup_scratch() as tmp:
            p = Path(tmp)
            snap_dir = p / ".claude"
            payload = (
                '{"hook_event_name":"PostToolUse","tool_name":"Edit",'
                '"tool_input":{"file_path":"' + str(p / "docs" / "STATUS.md") + '"}}'
            )
            subprocess.run(
                ["bash", str(p / "hooks" / "post-status-audit.sh")],
                input=payload, capture_output=True, text=True,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(p)},
            )
            stragglers = list(snap_dir.glob(".gate-snapshot.tmp.*"))
            self.assertEqual(
                stragglers, [],
                f"tmp files lingered after successful write: {stragglers}"
            )


if __name__ == "__main__":
    unittest.main()
