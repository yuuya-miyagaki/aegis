import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = sys.platform.startswith("win")
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    WINDOWS or ROOTUSER, reason="chmod no-op on Windows / bypassed by root")
LIBS = ("emit.sh", "frontmatter.sh", "phase-skills.sh", "sanitize.sh",
        "evidence.sh", "cp-lock.sh",
        # evidence.sh transitive deps (else session-start aborts before lock).
        "extract-input.sh", "fingerprint.sh", "patterns.sh")


def _install(task_type: str) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        f"task_type: {task_type}\n---\n")
    (p / "hooks" / "lib").mkdir(parents=True)
    (p / "hooks" / "session-start.sh").write_bytes(
        (ROOT / "hooks" / "session-start.sh").read_bytes())
    for lib in LIBS:
        (p / "hooks" / "lib" / lib).write_bytes(
            (ROOT / "hooks" / "lib" / lib).read_bytes())
    (p / "scripts").mkdir()
    (p / "scripts" / "tool.py").write_text("print(1)\n")
    (p / "CLAUDE.md").write_text("# rules\n")
    return tmp


def _run_session_start(root: str):
    return subprocess.run(
        ["bash", str(Path(root) / "hooks" / "session-start.sh")],
        input="{}", capture_output=True, text=True, cwd=root)


def _writable(path: Path) -> bool:
    return subprocess.run(["bash", "-c", f'printf x >> "{path}"'],
                          capture_output=True).returncode == 0


@NO_FS_LOCK
class TestSessionStartLock:
    def test_feature_locks_control_plane(self):
        tmp = _install("feature")
        p = Path(tmp.name)
        try:
            r = _run_session_start(tmp.name)
            assert r.returncode == 0
            assert not _writable(p / "hooks" / "lib" / "frontmatter.sh"), \
                "feature session must lock CP"
            assert not _writable(p / "CLAUDE.md")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_framework_unlocks_control_plane(self):
        tmp = _install("framework")
        p = Path(tmp.name)
        try:
            subprocess.run(["chmod", "-R", "a-w", str(p / "hooks")])
            r = _run_session_start(tmp.name)
            assert r.returncode == 0
            assert _writable(p / "hooks" / "lib" / "frontmatter.sh"), \
                "framework session must unlock CP"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_missing_lib_does_not_crash(self):
        tmp = _install("feature")
        p = Path(tmp.name)
        try:
            (p / "hooks" / "lib" / "cp-lock.sh").unlink()
            r = _run_session_start(tmp.name)
            assert r.returncode == 0, "missing cp-lock must not fail session-start"
            assert "layer-1" in r.stdout or "cp-lock" in r.stdout, \
                "should warn that layer-2 was skipped"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()


# Standalone (no real chmod): the rc=1 fail-soft branch runs on all platforms,
# incl. root-CI, so it is not gated by NO_FS_LOCK.
def test_lock_failure_warns_not_crashes():
    # cp-lock present but the lock function returns non-zero (e.g. chmod fails on
    # some path under set -euo pipefail): session-start must still exit 0 and
    # surface a warn, never abort. Covers the `|| CONTEXT=...warn` branch
    # (reviewer-testing rc=1 gap).
    tmp = _install("feature")
    p = Path(tmp.name)
    try:
        (p / "hooks" / "lib" / "cp-lock.sh").write_text(
            "aegis_cp_paths() { :; }\n"
            "aegis_cp_lock() { return 1; }\n"
            "aegis_cp_unlock() { return 1; }\n")
        r = _run_session_start(tmp.name)
        assert r.returncode == 0, "lock rc=1 must not abort session-start"
        assert "一部失敗" in r.stdout, "should warn on partial lock failure"
    finally:
        subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()
