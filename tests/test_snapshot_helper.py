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


# --- iter66 Task 3 (Fix ③): snapshot 生成を frontmatter スコープ化 -----------

def test_body_spoof_lines_excluded_from_snapshot():
    """本文の task_size/gate_approvals 行が snapshot に混入しない。"""
    status = (
        "---\nmode: Dev\nphase: plan\ntask_type: framework\n"
        "gate_approvals:\n  review: pending\n---\n"
        "body\ntask_size: S\ngate_approvals:\n  review: approved\n"
    )
    with _scratch(status) as tmp:
        p = Path(tmp)
        rc, err = _write_snapshot(p)
        assert rc == 0, f"helper failed: {err}"
        snap = (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")
        assert "task_size: S" not in snap, f"body task_size leaked: {snap!r}"
        assert "review: approved" not in snap, f"body gate leaked: {snap!r}"
        assert "task_type: framework" in snap, f"missing task_type: {snap!r}"


def test_absent_task_size_still_regenerates():
    """潜在バグ修復: task_size 行なしでも regen は成功し task_type は記録される。"""
    status = (
        "---\nmode: Dev\nphase: brainstorm\ntask_type: framework\n"
        "gate_approvals:\n  review: pending\n---\nbody\n"
    )
    with _scratch(status) as tmp:
        p = Path(tmp)
        rc, err = _write_snapshot(p)
        assert rc == 0, f"regen must succeed without task_size: {err}"
        snap = (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")
        assert "task_type: framework" in snap, f"missing task_type: {snap!r}"
        assert "task_size:" not in snap, f"unexpected task_size line: {snap!r}"


def test_malformed_frontmatter_keeps_existing_snapshot():
    """未終端 frontmatter へ破壊 → rc≠0・既存 snapshot は byte 同一で温存。"""
    with _scratch() as tmp:
        p = Path(tmp)
        snap_file = p / ".claude" / ".gate-snapshot"
        # 1) normal STATUS -> build a valid snapshot
        rc, err = _write_snapshot(p)
        assert rc == 0, f"initial write failed: {err}"
        before = snap_file.read_bytes()
        # 2) corrupt STATUS: unterminated frontmatter (no closing ---)
        (p / "docs" / "STATUS.md").write_text(
            "---\nmode: Dev\nphase: plan\ntask_type: framework\n",
            encoding="utf-8",
        )
        rc, err = _write_snapshot(p)
        assert rc != 0, "malformed frontmatter must fail-closed (rc!=0)"
        after = snap_file.read_bytes()
        assert after == before, "existing snapshot must be byte-identical"


def test_normal_status_snapshot_shape_pinned():
    """正常系 STATUS の出力形状（行集合・順序）を従来と同一にピン。"""
    status = (
        "---\nmode: Dev\nphase: plan\ntask_type: framework\n"
        "task_size: M\ngate_approvals:\n  brainstorm: approved\n"
        "  plan: pending\n---\nbody\n"
    )
    with _scratch(status) as tmp:
        p = Path(tmp)
        rc, err = _write_snapshot(p)
        assert rc == 0, f"helper failed: {err}"
        snap = (p / ".claude" / ".gate-snapshot").read_text(encoding="utf-8")
        assert snap == (
            "gate_approvals:\n  brainstorm: approved\n  plan: pending\n"
            "phase: plan\nmode: Dev\ntask_type: framework\ntask_size: M\n"
        ), f"shape drift: {snap!r}"
