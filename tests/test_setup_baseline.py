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

    def test_baseline_does_not_stage_preexisting_file_in_framework_dir(self):
        """C1 (E1): docs/ 等の framework ディレクトリに既存ユーザーファイルが
        あっても baseline に巻き込まない。setup.sh はディレクトリ単位ではなく
        実際にコピー/生成した path だけを stage すべき。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            (proj / "docs").mkdir(parents=True)
            user_note = proj / "docs" / "user-note.md"
            user_note.write_text("my pre-existing note — keep out of baseline\n")
            r = _run_setup(proj, profile="minimal")
            self.assertEqual(
                r.returncode, 0,
                f"setup failed: {r.stdout[-400:]} {r.stderr[-400:]}")
            # framework files ARE committed (sanity: the baseline is real)
            self.assertEqual(
                _git(proj, "ls-files", "CLAUDE.md").stdout.strip(), "CLAUDE.md",
                "framework files should be in the baseline commit")
            # the pre-existing user file is NOT swept in
            self.assertEqual(
                _git(proj, "ls-files", "docs/user-note.md").stdout.strip(), "",
                "pre-existing docs/user-note.md must NOT be staged into baseline "
                "(dir-granular `git add docs` swept it in)")

    def test_standard_baseline_includes_installed_framework_files(self):
        """C1 完全性: scoped staging が installed framework file を取りこぼさない。
        INSTALLED_PATHS が将来あるカテゴリ（hooks / scripts / .claude）を漏らしても
        baseline が痩せたまま気づかない退行を防ぐ（grill-code 🟡）。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run_setup(proj, profile="standard")
            self.assertEqual(
                r.returncode, 0,
                f"setup failed: {r.stdout[-400:]} {r.stderr[-400:]}")
            for rel in ("CLAUDE.md", "docs/STATUS.md",
                        "hooks/session-start.sh", "scripts/check_status.py",
                        ".claude/rules/state-machine.md"):
                with self.subTest(path=rel):
                    self.assertEqual(
                        _git(proj, "ls-files", rel).stdout.strip(), rel,
                        f"standard baseline must include installed {rel}")


if __name__ == "__main__":
    unittest.main()
