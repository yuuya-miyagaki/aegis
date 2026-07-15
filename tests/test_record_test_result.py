"""iter70 Task1 RED — record-test-result.py argument pre-validation.

record-test-result.py is the MANUAL fallback writer: it executes a test
command and appends src:"manual" to the evidence log. Because a manual entry
is treated as decidable by the judge (bypasses marker_verified), a caller who
records a NON-runner command (or a no-run flag like --collect-only, or a
shell-operator/env-prefix smuggle) can forge a green judge fact.

iter70 (1) adds pre-execution, pre-record validation to record.main:
  (i)  runner match via judge.runner_cmd_matches (judge-identical normalization)
  (ii) non-shell-compat check (env-assign prefix / shell-operator argv tokens)
  (iii) drill.check_no_run_command (no-run flag rejection)
A rejection MUST be rc2, a stderr message, NO evidence-log write, and the
command MUST NOT be executed. The accept path (a legitimate runner) is
unchanged: rc0, src=manual record.

These tests fix that contract. Tests 1-8 fail against current code (which
executes any command and returns 0 with no validation); test 9 is a
regression pin that passes today and must keep passing.
"""
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess as sp
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = ROOT_DIR / "scripts" / "build-judge-card.py"
RECORDER = ROOT_DIR / "scripts" / "record-test-result.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Distinct module names to avoid colliding with test_judge_card.py's imports.
record = _load("record_mod_rr", RECORDER)
judge = _load("judge_rr", SCRIPT)


def _copy_lib(root: Path) -> None:
    """Same shutil.copytree contract as test_judge_card.py._copy_lib:
    record/judge delegate to hooks/lib/{fingerprint,patterns}.sh."""
    shutil.copytree(ROOT_DIR / "hooks" / "lib", root / "hooks" / "lib")


def _run_main(argv):
    """Call record.main(argv), capturing stderr. Returns (rc, stderr_text).
    rc comes from the return value (record.main returns an int)."""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = record.main(argv)
    return rc, buf.getvalue()


class _RecordFixture(unittest.TestCase):
    """tmp git repo + hooks/lib + trivial pass/fail pytest files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        sp.run(["git", "-C", str(self.root), "init", "-q"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "config", "user.email", "t@t"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "config", "user.name", "t"],
               check=True, capture_output=True)
        (self.root / "a.py").write_text("x=1\n", encoding="utf-8")
        (self.root / "t_pass.py").write_text(
            "def test_a():\n    pass\n", encoding="utf-8")
        (self.root / "t_fail.py").write_text(
            "def test_a():\n    assert False\n", encoding="utf-8")
        sp.run(["git", "-C", str(self.root), "add", "-A"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "commit", "-qm", "i"],
               check=True, capture_output=True)
        _copy_lib(self.root)
        self.log = self.root / ".claude" / "evidence-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()


class TestRecordRejection(_RecordFixture):
    def test_non_runner_command_rejected(self):
        # 1: a non-runner command must not forge a manual entry.
        rc, err = _run_main(["--root", str(self.root), "ls -la"])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists(),
                         "rejected command must not write the evidence log")
        self.assertTrue(
            ("record-test-result" in err) or ("pytest" in err),
            f"stderr should carry usage guidance, got: {err!r}")

    def test_no_run_flag_rejected(self):
        # 2: --collect-only runs zero tests → reject (drill.check_no_run_command).
        rc, err = _run_main(
            ["--root", str(self.root), "pytest --collect-only -q"])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists())

    def test_quoted_no_run_flag_rejected(self):
        # 3: quoting the no-run flag (shlex-normalized) must not evade the gate.
        rc, err = _run_main(
            ["--root", str(self.root), 'pytest "--collect-only" -q'])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists())

    def test_missing_patterns_fail_closed(self):
        # 4: no patterns.sh → runner match cannot run → fail-closed reject.
        (self.root / "hooks" / "lib" / "patterns.sh").unlink()
        rc, err = _run_main(
            ["--root", str(self.root), "python3 -m pytest -q t_pass.py"])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists())

    def test_rejected_command_not_executed(self):
        # 5: validation precedes execution — a non-runner side-effecting command
        # (touch) must be rejected BEFORE it can create its marker file.
        marker = self.root / "marker"
        rc, err = _run_main(
            ["--root", str(self.root), f"touch {marker}"])
        self.assertEqual(rc, 2, err)
        self.assertFalse(marker.exists(),
                         "rejected command must not have been executed")
        self.assertFalse(self.log.exists())

    def test_empty_command_rejected(self):
        # 6: empty command matches no runner → reject.
        rc, err = _run_main(["--root", str(self.root), ""])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists())

    def test_env_prefix_rejected(self):
        # 7: an env-assignment prefix (FOO=1 ...) is a shell-only construct;
        # shlex argv[0] contains '=' → non-shell-compat → reject.
        rc, err = _run_main(
            ["--root", str(self.root), "FOO=1 python3 -m pytest -q"])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists())

    def test_shell_operator_token_rejected(self):
        # 8: a shell operator token (&&) is not interpreted by shlex-exec; a
        # bare '&&' argv token → non-shell-compat → reject.
        rc, err = _run_main(
            ["--root", str(self.root), "pytest -q && echo ok"])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists())

    def test_unparseable_quote_rejected(self):
        # iter70 review テスト強度 Finding 2: a command that MATCHES the runner
        # regex but has an unterminated quote reaches shlex.split → ValueError.
        # That path (record-test-result.py step 2) was previously unpinned; a
        # mutation replacing shlex.split with str.split (no ValueError) would
        # have survived. The command must fail-closed: rc2, no log write, and a
        # quoting-related message.
        rc, err = _run_main(
            ["--root", str(self.root), 'python3 -m pytest -q "abc'])
        self.assertEqual(rc, 2, err)
        self.assertFalse(self.log.exists())
        self.assertIn("クォート", err)


class TestRecordAccept(_RecordFixture):
    def test_valid_runner_still_records(self):
        # 9: the accept path is unchanged — a legitimate runner executes and
        # appends a decidable src=manual / status=ok entry (rc0). Passes today
        # (regression pin for the accept path).
        cmd = f"python3 -m pytest -q {self.root / 't_pass.py'}"
        self.assertLess(len(cmd), 500, "cmd must stay under the 500-char cap")
        rc, err = _run_main(["--root", str(self.root), cmd])
        self.assertEqual(rc, 0, err)
        self.assertTrue(self.log.exists())
        row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(row["src"], "manual")
        self.assertEqual(row["status"], "ok")


if __name__ == "__main__":
    unittest.main()
