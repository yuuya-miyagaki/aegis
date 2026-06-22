import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "cp-lock.sh"

WINDOWS = sys.platform.startswith("win")
# root bypasses the write permission bit, so a-w does not block root writes.
# CI often runs as root — skip the moat assertions there (they are meaningless).
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    WINDOWS or ROOTUSER,
    reason="chmod write-bit is a no-op on native Windows / bypassed by root")


def _make_scratch() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    # CP files (must become read-only when locked)
    (p / "hooks" / "lib").mkdir(parents=True)
    (p / "hooks" / "check-x.sh").write_text("echo hi\n")
    (p / "hooks" / "lib" / "util.sh").write_text("echo lib\n")
    (p / "scripts").mkdir()
    (p / "scripts" / "tool.py").write_text("print(1)\n")
    (p / "CLAUDE.md").write_text("# rules\n")
    (p / ".claude" / "skills").mkdir(parents=True)
    (p / ".claude" / "skills" / "s.md").write_text("skill\n")
    (p / ".claude" / "settings.json").write_text("{}\n")
    # runtime-state (must stay writable)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text("---\n---\n")
    (p / ".claude" / ".gate-snapshot").write_text("phase: x\n")
    (p / ".claude" / "settings.local.json").write_text("{}\n")
    return tmp


def _bash(snippet: str, root: str):
    return subprocess.run(
        ["bash", "-c", f'source "{LIB}"; {snippet}'],
        capture_output=True, text=True, cwd=root,
    )


def _can_write(path: Path) -> bool:
    r = subprocess.run(["bash", "-c", f'printf x >> "{path}"'],
                       capture_output=True, text=True)
    return r.returncode == 0


@NO_FS_LOCK
class TestCpLock:
    def test_paths_lists_only_existing(self):
        tmp = _make_scratch()
        try:
            out = _bash('aegis_cp_paths "$PWD"', tmp.name).stdout
            listed = {line.split("/")[-1] for line in out.split() if line}
            assert "hooks" in listed and "scripts" in listed
            assert "CLAUDE.md" in listed
            # settings (json AND local) / docs / .gate-snapshot must NOT be listed
            assert "settings.json" not in out and "settings.local.json" not in out
            assert "/docs" not in out and ".gate-snapshot" not in out
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_lock_blocks_all_write_forms(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            cp_file = p / "hooks" / "lib" / "util.sh"
            assert not _can_write(cp_file), "locked CP file must reject append"
            # all listed CP dirs are locked uniformly, not just hooks/
            assert not _can_write(p / "scripts" / "tool.py"), \
                "scripts/ must also be locked"
            assert subprocess.run(
                ["bash", "-c", f'cp /etc/hostname "{cp_file}"'],
                capture_output=True).returncode != 0
            assert subprocess.run(
                ["bash", "-c", f'rm "{cp_file}"'],
                capture_output=True).returncode != 0
            assert subprocess.run(
                ["python3", "-c", f"open('{cp_file}','w').write('x')"],
                capture_output=True).returncode != 0
            assert subprocess.run(
                ["bash", "-c", f'printf x > "{p / "hooks" / "evil.sh"}"'],
                capture_output=True).returncode != 0
            assert cp_file.read_text() == "echo lib\n", "file content INTACT"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_runtime_state_stays_writable_under_lock(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            assert _can_write(p / "docs" / "STATUS.md")
            assert _can_write(p / ".claude" / ".gate-snapshot")
            assert _can_write(p / ".claude" / "settings.json")
            assert _can_write(p / ".claude" / "settings.local.json")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_unlock_restores_writability(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            _bash('aegis_cp_lock "$PWD"', tmp.name)
            assert not _can_write(p / "hooks" / "lib" / "util.sh")
            assert _bash('aegis_cp_unlock "$PWD"', tmp.name).returncode == 0
            assert _can_write(p / "hooks" / "lib" / "util.sh")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_lock_is_idempotent(self):
        tmp = _make_scratch()
        try:
            assert _bash('aegis_cp_lock "$PWD"; aegis_cp_lock "$PWD"',
                         tmp.name).returncode == 0
            assert _bash('aegis_cp_unlock "$PWD"; aegis_cp_unlock "$PWD"',
                         tmp.name).returncode == 0
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_apply_framework_unlocks(self):
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            _bash('aegis_cp_lock "$PWD"', tmp.name)  # start locked
            assert not _can_write(p / "hooks" / "lib" / "util.sh")
            assert _bash('aegis_cp_apply "$PWD" framework', tmp.name).returncode == 0
            assert _can_write(p / "hooks" / "lib" / "util.sh"), "framework => unlock"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_apply_nonframework_locks(self):
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            assert _can_write(p / "hooks" / "lib" / "util.sh")  # fresh = unlocked
            assert _bash('aegis_cp_apply "$PWD" feature', tmp.name).returncode == 0
            assert not _can_write(p / "hooks" / "lib" / "util.sh"), "feature => lock"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_apply_empty_task_type_locks(self):
        # default-lock: empty/unknown task_type must lock (safe default)
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            assert _bash('aegis_cp_apply "$PWD" ""', tmp.name).returncode == 0
            assert not _can_write(p / "hooks" / "lib" / "util.sh")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_apply_idempotent_keeps_state(self):
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            _bash('aegis_cp_lock "$PWD"', tmp.name)  # locked
            assert _bash('aegis_cp_apply "$PWD" feature', tmp.name).returncode == 0
            assert not _can_write(p / "hooks" / "lib" / "util.sh"), "already locked stays locked"
            _bash('aegis_cp_unlock "$PWD"', tmp.name)  # unlocked
            assert _bash('aegis_cp_apply "$PWD" framework; aegis_cp_apply "$PWD" framework',
                         tmp.name).returncode == 0
            assert _can_write(p / "hooks" / "lib" / "util.sh"), "already unlocked stays unlocked"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()


# Platform-independent (no chmod): runs even on Windows/root CI.
def test_empty_root_is_rejected():
    # An empty root must fail loud (rc 1), never silently chmod absolute /hooks etc.
    assert _bash('aegis_cp_lock ""', ".").returncode == 1
    assert _bash('aegis_cp_unlock ""', ".").returncode == 1


def test_apply_empty_root_is_rejected():
    assert _bash('aegis_cp_apply "" feature', ".").returncode == 1


def test_cp_lock_paths_cover_expected_roots():
    # Drift guard (reviewer-maintainability): aegis_cp_paths must enumerate the
    # canonical control-plane roots that exist in the framework repo. Catches an
    # accidental drop from the list (e.g. removing 'scripts'). The layer-1 regex
    # lives in hooks/check-control-plane.sh (CP_DIRS) — keep the two in sync.
    out = _bash('aegis_cp_paths "$PWD"', str(ROOT)).stdout
    basenames = {line.rsplit("/", 1)[-1] for line in out.split() if line}
    for expected in ("hooks", "scripts", "templates", "CLAUDE.md",
                     "rules", "skills", "commands", "agents"):
        assert expected in basenames, f"aegis_cp_paths dropped {expected!r}: {out!r}"
