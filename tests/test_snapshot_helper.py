#!/usr/bin/env python3
"""iter43 Task 1: hooks/lib/snapshot.sh の aegis_write_snapshot 契約。

snapshot 書込みを単一関数化し、gate_approvals/phase/mode に加えて
task_type/task_size を含める（I3: task_type/task_size tamper-evidence の土台）。
3 writer（session-start / update-gate / post-status-audit）が共有する。
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_LIB = ROOT / "hooks" / "lib" / "snapshot.sh"

STATUS = (
    "---\n"
    "framework: aegis\n"
    "mode: Dev\n"
    "phase: implement\n"
    "task_type: framework\n"
    "task_size: L\n"
    "iteration: 43\n"
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
    "---\n"
)


def _scratch(status: str = STATUS) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(status, encoding="utf-8")
    (p / ".claude").mkdir()
    return tmp


def _write_snapshot(root: Path) -> tuple[int, str]:
    """Source snapshot.sh and call aegis_write_snapshot <root>."""
    script = f'source "{SNAPSHOT_LIB}"; aegis_write_snapshot "{root}"'
    r = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True
    )
    return r.returncode, r.stderr


def test_snapshot_contains_gate_phase_mode():
    with _scratch() as tmp:
        p = Path(tmp)
        rc, err = _write_snapshot(p)
        assert rc == 0, f"helper failed: {err}"
        snap = (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")
        assert "gate_approvals:" in snap
        assert "brainstorm: approved" in snap
        assert "phase: implement" in snap
        assert "mode: Dev" in snap


def test_snapshot_contains_task_type_and_size():
    with _scratch() as tmp:
        p = Path(tmp)
        rc, err = _write_snapshot(p)
        assert rc == 0, f"helper failed: {err}"
        snap = (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")
        assert "task_type: framework" in snap, f"missing task_type: {snap!r}"
        assert "task_size: L" in snap, f"missing task_size: {snap!r}"


def test_snapshot_atomic_no_tmp_lingers():
    with _scratch() as tmp:
        p = Path(tmp)
        _write_snapshot(p)
        stragglers = list((p / ".claude").glob(".gate-snapshot.tmp.*"))
        assert stragglers == [], f"tmp lingered: {stragglers}"


def test_snapshot_survives_null_task_size():
    status = STATUS.replace("task_size: L\n", "task_size: null\n")
    with _scratch(status) as tmp:
        p = Path(tmp)
        rc, err = _write_snapshot(p)
        assert rc == 0, f"helper failed on null task_size: {err}"
        snap = (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")
        # still writes the line (value null) — migration-grace-compatible
        assert "task_size:" in snap
        assert "phase: implement" in snap


def test_snapshot_failure_preserves_existing():
    """STATUS 不在で書込みできなくても既存 snapshot を破壊しない（非破壊）。"""
    with _scratch() as tmp:
        p = Path(tmp)
        snap_file = p / ".claude" / ".gate-snapshot"
        snap_file.write_text("phase: old\nmode: Dev\n", encoding="utf-8")
        (p / "docs" / "STATUS.md").unlink()
        _write_snapshot(p)
        # existing snapshot must remain (not truncated to empty)
        assert snap_file.exists()
        assert "old" in snap_file.read_text(encoding="utf-8")
