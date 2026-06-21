import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "cp-lock.sh"
WINDOWS = sys.platform.startswith("win")
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    WINDOWS or ROOTUSER, reason="chmod no-op on Windows / bypassed by root")


def _scratch():
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "hooks" / "lib").mkdir(parents=True)
    (p / "hooks" / "lib" / "emit.sh").write_text("echo orig\n")
    return tmp


def _lock(root: str):
    subprocess.run(["bash", "-c", f'source "{LIB}"; aegis_cp_lock "{root}"'],
                   check=True, cwd=root)


@NO_FS_LOCK
class TestSfCatalogUnderLock:
    """Each SF form, run as a real shell command under an active lock, must
    fail to mutate the CP file — the OS enforces this form-independently."""

    def _assert_blocked(self, root: Path, shell_cmd: str):
        target = root / "hooks" / "lib" / "emit.sh"
        before = target.read_text()
        subprocess.run(["bash", "-c", shell_cmd], capture_output=True, cwd=str(root))
        assert target.read_text() == before, f"CP mutated by: {shell_cmd!r}"

    def test_sf_catalog_all_blocked_under_lock(self):
        tmp = _scratch()
        root = Path(tmp.name)
        try:
            _lock(tmp.name)
            forms = [
                'echo evil > "hoo""ks/lib/emit.sh"',          # SF-001 quote-split
                'echo evil > hooks\\/lib/emit.sh',             # SF-001 backslash
                'cp /etc/hostname hooks/lib/emit.sh',          # plain
                'rm -f hooks/lib/emit.sh',                     # delete (dir write)
                "python3 -c \"open('hook'+chr(115)+'/lib/emit.sh','w').write('x')\"",  # SF-004
                "perl -e \"open(F,'>','hook'.'s'.'/lib/emit.sh'); print F 'x'\"",      # SF-004
            ]
            for f in forms:
                self._assert_blocked(root, f)
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()
