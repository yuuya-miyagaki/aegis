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
    (p / "scripts").mkdir()
    (p / "scripts" / "tool.py").write_text("print(1)\n")
    # A real, existing source file so `cp <src> <cp-target>` genuinely WOULD
    # write if the target were unlocked (avoids a false "blocked" that is really
    # a missing-source error — /etc/hostname is absent on macOS).
    (p / "src.txt").write_text("EVIL\n")
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
                'cp src.txt hooks/lib/emit.sh',                # plain
                'rm -f hooks/lib/emit.sh',                     # delete (dir write)
                "python3 -c \"open('hook'+chr(115)+'/lib/emit.sh','w').write('x')\"",  # SF-004
                "perl -e \"open(F,'>','hook'.'s'.'/lib/emit.sh'); print F 'x'\"",      # SF-004
                # iter57 grill catalog: forms the retired static hook missed or
                # only caught by regex — the syscall stops them form-independently.
                '(cd scripts && cp ../src.txt ../hooks/lib/emit.sh)',  # subshell cwd shift
                'cp src.txt hooks/lib/emit.s?',                # glob expands to real file
                "sh -c 'echo x > hooks/lib/emit.sh'",          # nested interpreter
                'find hooks -name emit.sh -exec cp src.txt {} \\;',  # find -exec write
            ]
            for f in forms:
                self._assert_blocked(root, f)
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_new_file_creation_blocked_under_lock(self):
        """dir a-w blocks CREATING a new CP file too (not just overwriting)."""
        tmp = _scratch()
        root = Path(tmp.name)
        try:
            _lock(tmp.name)
            subprocess.run(["bash", "-c", "touch hooks/evil.sh"],
                           capture_output=True, cwd=str(root))
            assert not (root / "hooks" / "evil.sh").exists(), \
                "lock must block creating a new file in a CP dir"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_control_case_unlocked_would_write(self):
        """対照: lock を外せば同じ書込みが通る＝テストが挙動を弁別している証拠
        （lock 下の INTACT が「元々書けない」の見かけ上の成功でないことを示す）。"""
        tmp = _scratch()
        root = Path(tmp.name)
        target = root / "hooks" / "lib" / "emit.sh"
        try:
            _lock(tmp.name)
            subprocess.run(["bash", "-c",
                            f'source "{LIB}"; aegis_cp_unlock "{tmp.name}"'],
                           check=True, cwd=tmp.name)
            subprocess.run(["bash", "-c", "echo changed > hooks/lib/emit.sh"],
                           capture_output=True, cwd=str(root))
            assert target.read_text() != "echo orig\n", \
                "unlock 後は書込みが通るはず（弁別性の確認）"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()
