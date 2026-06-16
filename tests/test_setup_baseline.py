#!/usr/bin/env python3
"""Task 1.1 (OBS-017): setup.sh creates a framework baseline commit.

Without an initial commit, the first dogfood review gate sees the installed
framework files as new uncommitted code and emits a framework-origin stub 🔴.
setup.sh therefore creates a one-time baseline commit on a fresh install:

- a clean (no-git or empty) target → exactly one baseline commit;
- an existing repo WITH history → untouched (no-op);
- staging is scoped (`git add <paths>`, never `git add -A`) so unrelated files
  in the target are not committed.

The git env is made hermetic (GIT_CONFIG_GLOBAL/SYSTEM → /dev/null) so the test
is deterministic regardless of the developer/CI machine's global git identity
and exercises setup.sh's identity fallback.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SH = ROOT / "bin" / "setup.sh"


def _hermetic_env():
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return env


def _git(target, *args):
    return subprocess.run(
        ["git", "-C", str(target), *args],
        capture_output=True, text=True, env=_hermetic_env(),
    )


def _run_setup(proj, profile="standard"):
    return subprocess.run(
        [str(SETUP_SH), f"--profile={profile}", f"--target={proj}"],
        capture_output=True, text=True, env=_hermetic_env(),
    )


class TestSetupBaseline(unittest.TestCase):

    def test_clean_install_creates_single_baseline_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run_setup(proj)
            self.assertEqual(
                r.returncode, 0,
                f"setup failed: {r.stdout[-400:]} {r.stderr[-400:]}")
            log = _git(proj, "log", "--oneline")
            self.assertEqual(
                log.returncode, 0,
                f"target is not a git repo after install: {log.stderr}")
            lines = [ln for ln in log.stdout.splitlines() if ln.strip()]
            self.assertEqual(
                len(lines), 1,
                f"expected exactly 1 baseline commit, got:\n{log.stdout}")
            msg = _git(proj, "log", "-1", "--pretty=%s").stdout
            self.assertIn(
                "baseline", msg.lower(),
                f"baseline commit message expected, got: {msg!r}")

    def test_existing_repo_with_history_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            proj.mkdir(parents=True)
            self.assertEqual(_git(proj, "init", "-q").returncode, 0)
            (proj / "README.md").write_text("pre-existing\n")
            _git(proj, "add", "README.md")
            commit = subprocess.run(
                ["git", "-C", str(proj),
                 "-c", "user.name=Pre", "-c", "user.email=pre@x.local",
                 "commit", "-q", "-m", "pre-existing initial commit"],
                capture_output=True, text=True, env=_hermetic_env(),
            )
            self.assertEqual(commit.returncode, 0, commit.stderr)
            head_before = _git(proj, "rev-parse", "HEAD").stdout.strip()

            r = _run_setup(proj)
            self.assertEqual(
                r.returncode, 0,
                f"setup failed: {r.stdout[-400:]} {r.stderr[-400:]}")
            head_after = _git(proj, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(
                head_before, head_after,
                "setup must NOT add a baseline commit to a repo with history")

    def test_baseline_does_not_stage_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            proj.mkdir(parents=True)
            (proj / "UNRELATED.txt").write_text("do not commit me\n")
            r = _run_setup(proj)
            self.assertEqual(
                r.returncode, 0,
                f"setup failed: {r.stdout[-400:]} {r.stderr[-400:]}")
            tracked = _git(proj, "ls-files", "UNRELATED.txt").stdout.strip()
            self.assertEqual(
                tracked, "",
                "baseline must not stage unrelated files (no git add -A)")


if __name__ == "__main__":
    unittest.main()
