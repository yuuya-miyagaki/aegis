import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    sys.platform.startswith("win") or ROOTUSER,
    reason="chmod write-bit is a no-op on native Windows / bypassed by root")

STATUS_TMPL = """---
framework: aegis
mode: Dev
phase: implement
task_type: {tt}
gate_approvals:
  plan: approved
---
"""


def _scaffold(d: Path, task_type: str) -> Path:
    (d / "docs").mkdir()
    (d / "docs" / "STATUS.md").write_text(STATUS_TMPL.format(tt=task_type), encoding="utf-8")
    (d / ".claude").mkdir()
    shutil.copytree(ROOT / "hooks", d / "hooks")
    (d / "scripts").mkdir()
    # COPY (not symlink) — never symlink real repo files into a lockable scratch.
    shutil.copy2(ROOT / "scripts" / "check_status.py", d / "scripts" / "check_status.py")
    return d


def _run_audit(root: Path) -> None:
    payload = json.dumps({"tool_name": "Edit",
                          "tool_input": {"file_path": str(root / "docs" / "STATUS.md")}})
    subprocess.run(["bash", str(root / "hooks" / "post-status-audit.sh")],
                   input=payload, capture_output=True, text=True, timeout=60,
                   env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)})


def _can_write(p: Path) -> bool:
    return subprocess.run(["bash", "-c", f'printf x >> "{p}"'],
                          capture_output=True).returncode == 0


@NO_FS_LOCK
def test_status_edit_to_nonframework_relocks():
    with tempfile.TemporaryDirectory() as tmp:
        root = _scaffold(Path(tmp), "feature")
        try:
            subprocess.run(["chmod", "-R", "u+w", f"{root}/hooks"])  # start unlocked
            assert _can_write(root / "hooks" / "session-start.sh")
            _run_audit(root)
            assert not _can_write(root / "hooks" / "session-start.sh"), \
                "非 framework への STATUS 編集で post-status-audit が再 lock するべき"
        finally:
            subprocess.run(["chmod", "-R", "u+w", str(root)])


def test_post_status_audit_without_cp_lock_lib_does_not_crash():
    # cp-lock.sh absent => `command -v aegis_cp_apply` is false => re-lock is
    # skipped and post-status-audit still runs to a clean exit (optional-lib load
    # is non-fatal). No chmod happens, so this is platform-independent (no skip).
    with tempfile.TemporaryDirectory() as tmp:
        root = _scaffold(Path(tmp), "feature")
        (root / "hooks" / "lib" / "cp-lock.sh").unlink()
        payload = json.dumps({"tool_name": "Edit",
                              "tool_input": {"file_path": str(root / "docs" / "STATUS.md")}})
        r = subprocess.run(["bash", str(root / "hooks" / "post-status-audit.sh")],
                           input=payload, capture_output=True, text=True, timeout=60,
                           env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)})
        assert r.returncode == 0, \
            f"absent cp-lock.sh must not crash post-status-audit: {r.stderr}"


@NO_FS_LOCK
def test_status_edit_to_framework_unlocks():
    with tempfile.TemporaryDirectory() as tmp:
        root = _scaffold(Path(tmp), "framework")
        try:
            subprocess.run(["chmod", "-R", "a-w", f"{root}/hooks"])  # start locked
            assert not _can_write(root / "hooks" / "session-start.sh")
            _run_audit(root)
            assert _can_write(root / "hooks" / "session-start.sh"), \
                "framework への STATUS 編集で post-status-audit が unlock するべき"
        finally:
            subprocess.run(["chmod", "-R", "u+w", str(root)])
