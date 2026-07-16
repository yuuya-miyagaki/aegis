"""iter71 Task1 RED — hooks/lib/marker.sh::aegis_marker_verdict unit tests.

marker.sh (new in Task 2) extracts the 4-stage positive-proof marker core out
of evidence.sh so the three consumers (evidence.sh via source, record and drill
via subprocess) share ONE implementation. The interface contract:

    aegis_marker_verdict <exit_code> <command>

  - stdin  : the FULL test output text
  - stdout : "true" / "false" (rc0)
  - rc3    : evaluation impossible (patterns.sh not loaded / pattern data empty)

The 4 stages, in order: NO_RUN flag disqualification -> STRONG marker ->
WEAK pair (both halves) -> zero-run gate (output signal / pytest exit 5 /
prologue absence). Logic is a verbatim MOVE of evidence.sh's _check_test_marker.

All tests here are RED until marker.sh exists: M2-M11 fail because
aegis_marker_verdict is undefined (source of a missing file -> exit 3, but the
subprocess helper below returns rc3 for that too, so the assertions on
(0,"true"/"false") fail); M1 raises FileNotFoundError copying the missing lib.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER_LIB = ROOT / "hooks" / "lib" / "marker.sh"


def _verdict(output: str, cmd: str, exit_code: str = "0", lib=None):
    lib = MARKER_LIB if lib is None else lib
    proc = subprocess.run(
        ["bash", "-c",
         'source "$1" >/dev/null 2>&1 || exit 3; aegis_marker_verdict "$2" "$3"',
         "_", str(lib), exit_code, cmd],
        input=output, capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stdout.strip()


PYTEST_REAL = ("platform darwin -- Python 3.9.6, pytest-8.4.2\n"
               "rootdir: /tmp/x\ncollected 3 items\n\n"
               "=========== 3 passed in 0.42s ===========\n")


class TestMarkerVerdict(unittest.TestCase):
    def test_rc3_when_patterns_missing(self):
        # M1: marker.sh sourced WITHOUT patterns.sh alongside -> rc3 (eval
        # impossible, pattern arrays empty). Today marker.sh does not exist, so
        # shutil.copy raises FileNotFoundError -> error RED, which is fine.
        with tempfile.TemporaryDirectory() as d:
            lib = Path(d) / "marker.sh"
            shutil.copy(MARKER_LIB, lib)  # no patterns.sh next to it
            rc, _out = _verdict(PYTEST_REAL, "python3 -m pytest tests/", "0", lib=lib)
            self.assertEqual(rc, 3)

    def test_strong_with_prologue_true(self):
        # M2: STRONG pytest marker + full prologue + exit 0 -> true.
        rc, out = _verdict(PYTEST_REAL, "python3 -m pytest tests/", "0")
        self.assertEqual((rc, out), (0, "true"))

    def test_strong_without_prologue_false(self):
        # M3: strong summary line ONLY (echo forge, no pytest prologue) -> false.
        rc, out = _verdict("=== 3 passed in 0.42s ===\n",
                           "python3 -m pytest tests/", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_pytest_exit5_false(self):
        # M4: pytest exit 5 (no tests collected) overrides the strong marker.
        rc, out = _verdict(PYTEST_REAL, "python3 -m pytest tests/", "5")
        self.assertEqual((rc, out), (0, "false"))

    def test_weak_pair_true(self):
        # M5: unittest WEAK pair (Ran N tests + OK) -> true.
        rc, out = _verdict("Ran 3 tests in 0.012s\n\nOK\n",
                           "python3 -m unittest t", "0")
        self.assertEqual((rc, out), (0, "true"))

    def test_weak_half_false(self):
        # M6: only one half of the WEAK pair (Ran N, no OK) -> false.
        rc, out = _verdict("Ran 3 tests in 0.012s\n",
                           "python3 -m unittest t", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_zero_run_false(self):
        # M7: Ran 0 tests + OK is a zero-run signal -> false.
        rc, out = _verdict("Ran 0 tests in 0.000s\n\nOK\n",
                           "python3 -m unittest t", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_no_run_flag_false(self):
        # M8: --collect-only is a NO_RUN flag -> disqualified regardless of output.
        rc, out = _verdict(PYTEST_REAL, "pytest --collect-only", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_empty_stdin_false(self):
        # M9: empty output cannot carry any positive proof -> false.
        rc, out = _verdict("", "python3 -m pytest tests/", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_go_marker_true(self):
        # M10: go test STRONG marker (ok <pkg> <dur>) -> true.
        rc, out = _verdict("ok  \texample.com/pkg\t0.123s\n", "go test ./...", "0")
        self.assertEqual((rc, out), (0, "true"))

    def test_forged_strong_plus_collected0_false(self):
        # M11: forged strong summary + `collected 0 items` zero-run signal -> false.
        rc, out = _verdict("===== 3 passed in 0.42s =====\ncollected 0 items\n",
                           "pytest -k x", "0")
        self.assertEqual((rc, out), (0, "false"))


class TestSkipSuiteResidual(unittest.TestCase):
    """iter71 review 敵対角度 F-A / 親 verify: an all-skip suite runs ZERO test
    bodies. Runners split by how their success marker treats a skipped test:

      - pytest (`N skipped in`), cargo (`0 passed`): the marker/zero-run gate
        rejects it -> false. These are MOAT-PROTECTION pins — a future marker
        edit that lets an all-skip pytest/cargo run read as `true` is a
        regression these lock down.
      - unittest (`Ran N tests ... OK (skipped=N)`), go (`ok pkg dur`): the
        runner counts a collected-then-skipped test as "run", so the WEAK pair
        (unittest) / STRONG `ok` line (go) is satisfied with zero bodies
        executed -> true. This is a PRE-EXISTING residual of an output-based
        proof (verified: pre-iter71 evidence.sh returns the same true; marker.sh
        is a verbatim move). Same class as the npm-echo residual, tracked in
        docs/security-followups.md SF-014; the permanent fix is a
        passed/failed-COUNT positive proof (iter72+). Contained: the B1 drill
        subsumes it (an all-skip baseline catches no mutant -> DRILL FAIL), so
        the qa gate (drill + judge) is not defeated by this alone. These tests
        PIN the split so a change in either camp is noticed."""

    def test_pytest_all_skip_false_moat_pin(self):
        out = ("platform darwin -- Python 3.9.6, pytest-8.4.2\n"
               "rootdir: /tmp/x\ncollected 1 item\n\n"
               "t.py s  [100%]\n\n=========== 1 skipped in 0.01s ===========\n")
        rc, verdict = _verdict(out, "python3 -m pytest t.py", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_cargo_all_ignored_false_moat_pin(self):
        out = ("running 3 tests\n"
               "test result: ok. 0 passed; 0 failed; 3 ignored\n")
        rc, verdict = _verdict(out, "cargo test", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_unittest_all_skip_true_known_residual(self):
        # PRE-EXISTING residual (SF-014): unittest counts skipped as `Ran N`.
        out = "Ran 1 test in 0.000s\n\nOK (skipped=1)\n"
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_go_all_skip_true_known_residual(self):
        # PRE-EXISTING residual (SF-014): go emits `ok pkg dur` even when every
        # test t.Skip()s.
        out = "ok  \texample.com/pkg\t0.012s\n"
        rc, verdict = _verdict(out, "go test ./...", "0")
        self.assertEqual((rc, verdict), (0, "true"))


class TestWeakPairBoundary(unittest.TestCase):
    """iter71 review テスト強度 F2: the WEAK pair needs BOTH anchor and
    companion. M6 pins anchor-only -> false; this pins companion-only -> false,
    so a refactor that drops the anchor requirement (accepting a bare `OK`) is
    caught."""

    def test_companion_only_false(self):
        rc, verdict = _verdict("OK\n", "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "false"))


if __name__ == "__main__":
    unittest.main()
