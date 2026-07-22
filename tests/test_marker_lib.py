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
import re
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
    """iter71 review F-A / iter72 count proof: an all-skip suite runs ZERO test
    bodies. iter72's Stage 5 (count proof: executed = passed+failed, skips
    excluded, >=1 required per detected count family) CLOSES the unittest and
    `go test -v` halves of the residual; the remaining split:

      - pytest (`N skipped in`), cargo (`0 passed`), jest (no `passed`
        segment): false. MOAT-PROTECTION pins (cargo now via the Stage 5 sum
        — the zero-run line-deny was removed to fix the empty-doc-tests
        false negative — but the pin below is black-box identical).
      - unittest all-skip: false since iter72 (Ran N - skipped=N = 0). CLOSED.
      - go -v all-skip: false since iter72 (`--- SKIP:` only -> 0 PASS/FAIL
        lines). CLOSED for the top-level all-`t.Skip()` form; a parent
        t.Run holder still prints `--- PASS:` (its body DID run) — design
        addendum 4.
      - bare `go test`: `ok pkg dur` carries no counts; an all-skip package
        is byte-identical to a real pass (iter71 verified). PRE-EXISTING
        residual, SF-014 bucket, contained by the B1 drill (an all-skip
        baseline kills no mutant -> DRILL FAIL). Permanent-fix candidate:
        execution attestation (iter73+ track).

    iter72 review closed a vitest all-skip false-GREEN (STRONG anchor
    relaxation side effect) via the count DETECT — see
    TestCountProof.test_vitest_all_skip_false_closed."""

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

    def test_unittest_all_skip_false_closed(self):
        # iter72 CLOSED: Ran(2) - skipped(2) = 0 bodies. Real output captured
        # 2026-07-16 (python3 -m unittest, two @unittest.skip tests, rc=0).
        out = ("ss\n" + "-" * 70 +
               "\nRan 2 tests in 0.000s\n\nOK (skipped=2)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_unittest_partial_skip_true_boundary(self):
        # Boundary pin: Ran(2) - skipped(1) = 1 executed -> true. Real output
        # captured 2026-07-16.
        out = ("s.\n" + "-" * 70 +
               "\nRan 2 tests in 0.000s\n\nOK (skipped=1)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_go_verbose_all_skip_false_closed(self):
        # iter72 CLOSED: -v output present but zero `--- PASS:`/`--- FAIL:`.
        out = ("=== RUN   TestA\n--- SKIP: TestA (0.00s)\n"
               "=== RUN   TestB\n--- SKIP: TestB (0.00s)\n"
               "PASS\nok  \texample.com/pkg\t0.012s\n")
        rc, verdict = _verdict(out, "go test -v ./...", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_go_verbose_pass_true(self):
        out = ("=== RUN   TestA\n--- PASS: TestA (0.00s)\n"
               "PASS\nok  \texample.com/pkg\t0.010s\n")
        rc, verdict = _verdict(out, "go test -v ./...", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_go_bare_all_skip_true_known_residual(self):
        # PRE-EXISTING residual (SF-014): bare `go test` emits `ok pkg dur`
        # with no counts; all-skip and real pass are byte-identical (iter71
        # verified). No count family detects -> Stage 1-4 verdict -> true.
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


class TestCountProof(unittest.TestCase):
    """iter72 Stage 5 (count proof) — false-negative fixes and the guard.

    The two `..._fixed` tests pin REAL-WORLD summary shapes that the pre-iter72
    verdict REJECTED (both empirically demonstrated on 2026-07-16, see the
    design addendum): cargo's empty doc-tests section tripped the zero-run
    line-deny; jest's `skipped,` segment broke the STRONG marker adjacency."""

    def test_cargo_empty_doctests_section_true_fixed(self):
        # Real-world shape: unit section 5 passed + EMPTY doc-tests section
        # (`running 0 tests` -> `0 passed`). Pre-iter72: false (zero-run
        # line-deny). Stage 5 sums across ALL `test result:` lines: 5 >= 1.
        out = ("running 5 tests\n"
               "test a ... ok\ntest b ... ok\ntest c ... ok\n"
               "test d ... ok\ntest e ... ok\n"
               "test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; "
               "0 filtered out; finished in 0.00s\n\n"
               "   Doc-tests mylib\n\nrunning 0 tests\n\n"
               "test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; "
               "0 filtered out; finished in 0.00s\n")
        rc, verdict = _verdict(out, "cargo test", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_jest_skipped_mixed_true_fixed(self):
        # Real jest segment order is failed, skipped, todo, passed, total —
        # any skipped test broke the old `(N failed,)? N passed` adjacency.
        out = ("Tests:       2 skipped, 3 passed, 5 total\n"
               "Snapshots:   0 total\nTime:        1.2 s\n")
        rc, verdict = _verdict(out, "npx jest", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_jest_all_skip_false(self):
        # All-skip jest prints NO `passed` segment -> no STRONG hit -> false
        # (unchanged behavior, now double-covered by the count stage).
        out = "Tests:       3 skipped, 3 total\n"
        rc, verdict = _verdict(out, "npx jest", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_vitest_indented_summary_true(self):
        # Real vitest indents its summary lines (design addendum 2); the
        # anchors now allow leading blanks.
        out = (" Test Files  1 passed (1)\n"
               "      Tests  2 passed (2)\n")
        rc, verdict = _verdict(out, "npx vitest run", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_unittest_failed_with_skips_true(self):
        # Red-run verdict (the verdict proves "tests ran", not "green"):
        # Ran(5) - skipped(2) = 3 bodies executed -> true.
        out = ("Ran 5 tests in 0.010s\n\nFAILED (failures=1, skipped=2)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_cargo_hybrid_echo_forge_true_known_residual(self):
        # ACCEPTED RESIDUAL pin (design addendum 3): an echoed pair PLUS a
        # real zero-run cargo line now reads true (the removed line-deny
        # caught it). Accepted because the attacker strictly dominates by
        # just NOT running cargo (pure echo was already true pre-iter72 —
        # cargo has no prologue/exit-code second axis). Echo-class residual
        # (b), contained by drill/human preview. This pin makes the deny-
        # surface change explicit; flipping it back requires reintroducing
        # the empty-doc-tests false negative — do NOT "fix" without reading
        # SF-014.
        out = ("running 3 tests\n"
               "test result: ok. 3 passed; 0 failed; 0 ignored\n"
               "running 0 tests\n"
               "test result: ok. 0 passed; 0 failed; 0 ignored\n")
        rc, verdict = _verdict(out, "cargo test", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_forged_huge_count_stays_false_path(self):
        # A forged astronomically large count must not crash the arithmetic
        # (bash overflow) out of the normal verdict path: digit tokens are
        # capped at 9 chars before summation. unittest family: Ran(huge->cap)
        # - skipped(huge->cap) = 0 -> false (all-skip shape preserved).
        out = ("Ran 99999999999999999999 tests in 0.000s\n\n"
               "OK (skipped=99999999999999999999)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_rc3_when_count_families_missing(self):
        # The rc3 guard must cover the NEW array: a patterns.sh without
        # AEGIS_TEST_COUNT_FAMILIES (stale install) -> evaluation impossible.
        src = (ROOT / "hooks" / "lib" / "patterns.sh").read_text()
        kept, skip = [], False
        for ln in src.splitlines(keepends=True):
            if ln.startswith("AEGIS_TEST_COUNT_FAMILIES=("):
                skip = True
                continue
            if skip and ln.strip() == ")":
                skip = False
                continue
            if not skip:
                kept.append(ln)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "patterns.sh").write_text("".join(kept))
            shutil.copy(MARKER_LIB, Path(d) / "marker.sh")
            rc, _out = _verdict(
                PYTEST_REAL, "python3 -m pytest tests/", "0",
                lib=Path(d) / "marker.sh")
            self.assertEqual(rc, 3)

    def test_malformed_field_count_rc3_not_failopen(self):
        # iter72 qa (M6 survivor): the strict field-count guard (`nsep -eq 4`)
        # in marker.sh is load-bearing but was unpinned — the existing rc3 tests
        # only cover a MISSING array and a bad-GREP-regex, never a structurally
        # short entry. A COUNT_FAMILIES entry with the wrong separator count (4
        # fields = dropped MINUS) must fail CLOSED (rc3): without the guard the
        # misparse leaves `Ran N` un-subtracted and an all-skip unittest reads
        # true (fail OPEN — verified by the qa mutation battery).
        src = (ROOT / "hooks" / "lib" / "patterns.sh").read_text()
        five = ("'unittest|||(^|\\n)Ran [0-9]+ tests? in|||Ran [0-9]+ tests?"
                "|||sum|||[(,] ?skipped=[0-9]+'")
        four = ("'unittest|||(^|\\n)Ran [0-9]+ tests? in|||Ran [0-9]+ tests?"
                "|||sum'")
        self.assertIn(five, src)  # guard against the entry text drifting
        malformed = src.replace(five, four)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "patterns.sh").write_text(malformed)
            shutil.copy(MARKER_LIB, Path(d) / "marker.sh")
            rc, _out = _verdict(
                "Ran 2 tests in 0.001s\n\nOK (skipped=2)\n",
                "python3 -m unittest t", "0", lib=Path(d) / "marker.sh")
            self.assertEqual(rc, 3)

    def test_broken_minus_regex_rc3_not_failopen(self):
        # iter72 review round-2 (M-1): a corrupt patterns.sh whose unittest
        # MINUS is a regex the host grep REJECTS must fail CLOSED (rc3), not
        # swallow the subtraction. Before the fix the broken MINUS was `|| true`d
        # away, leaving `Ran N` un-subtracted -> an all-skip unittest read TRUE
        # (fail OPEN). Pin the DETECT/EXEC/MINUS grep paths to the same rc3.
        src = (ROOT / "hooks" / "lib" / "patterns.sh").read_text()
        broken = src.replace(
            "[(,] ?skipped=[0-9]+", "(((skipped=[0-9]+")  # unbalanced parens
        self.assertIn("(((skipped", broken)  # replacement actually applied
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "patterns.sh").write_text(broken)
            shutil.copy(MARKER_LIB, Path(d) / "marker.sh")
            rc, _out = _verdict(
                "Ran 2 tests in 0.001s\n\nOK (skipped=2)\n",
                "python3 -m unittest t", "0", lib=Path(d) / "marker.sh")
            self.assertEqual(rc, 3)

    def test_stray_byte_all_skip_stays_false_utf8_locale(self):
        # iter72 security F-CRIT-1 (blind-2nd): a stray non-UTF-8 byte on the
        # `OK (skipped=N)` line of an all-skip unittest run made the MINUS
        # extraction miss under a UTF-8 LC_CTYPE -> the skip was not subtracted
        # -> false GREEN. marker.sh now forces LC_ALL=C (byte-wise) internally,
        # so the verdict is false regardless of the caller's locale. Run the
        # helper under an explicit UTF-8 locale to pin the dangerous direction.
        import os
        env = dict(os.environ, LC_ALL="en_US.UTF-8", LC_CTYPE="en_US.UTF-8",
                   LANG="en_US.UTF-8")
        out = "Ran 2 tests in 0.001s\n\nOK (skipped=2)\xff\n"
        proc = subprocess.run(
            ["bash", "-c",
             'source "$1" >/dev/null 2>&1 || exit 3; '
             'aegis_marker_verdict "$2" "$3"',
             "_", str(MARKER_LIB), "0", "python3 -m unittest t"],
            input=out.encode("latin-1"), capture_output=True, env=env)
        self.assertEqual((proc.returncode, proc.stdout.decode().strip()),
                         (0, "false"))

    def test_stray_byte_zero_run_gate_stays_false_utf8_locale(self):
        # iter72 security F-CRIT-1 (pre-existing iter71 Stage-4 instance): a
        # forged STRONG pytest marker paired with a real `collected 0 items`
        # zero-run signal carrying a stray byte also flipped to true under a
        # UTF-8 locale (the zero-run veto missed). LC_ALL=C closes it too.
        import os
        env = dict(os.environ, LC_ALL="en_US.UTF-8", LC_CTYPE="en_US.UTF-8",
                   LANG="en_US.UTF-8")
        out = ("platform darwin -- Python 3.9.6\nrootdir: /x\n"
               "collected 0 items\xff\n\n===== 3 passed in 0.42s =====\n")
        proc = subprocess.run(
            ["bash", "-c",
             'source "$1" >/dev/null 2>&1 || exit 3; '
             'aegis_marker_verdict "$2" "$3"',
             "_", str(MARKER_LIB), "0", "python3 -m pytest t"],
            input=out.encode("latin-1"), capture_output=True, env=env)
        self.assertEqual((proc.returncode, proc.stdout.decode().strip()),
                         (0, "false"))

    def test_vitest_all_skip_false_closed(self):
        # iter72 review F-2: the STRONG anchor relaxation ([ \t]*Test Files)
        # made a real all-skip vitest file (which still prints `Test Files 1
        # passed` at file level) read as true — a false GREEN. Stage 5's vitest
        # DETECT now includes skipped/todo so the `Tests N skipped` line is
        # detected and count(passed+failed)=0 vetoes it back to false.
        out = (" Test Files  1 passed (1)\n"
               "      Tests  3 skipped (3)\n"
               "   Start at  10:00:00\n   Duration  1.20s\n")
        rc, verdict = _verdict(out, "npx vitest run", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_unittest_stray_skipped_token_true(self):
        # iter72 review F0: a genuinely green unittest run whose test body
        # prints an incidental `skipped=N` token (config dump / captured child
        # output) must NOT be over-subtracted to false. The MINUS anchor
        # `[(,] ?skipped=` only matches unittest's own summary tokens.
        out = ("config: retries=3 skipped=10\n..\n"
               + "-" * 70 + "\nRan 2 tests in 0.001s\n\nOK\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_bare_go_with_ci_banner_true(self):
        # iter72 review F1: a CI/wrapper banner `===== ... finished in N.Ns =====`
        # (no passed/failed token) must not false-detect the pytest family and
        # cross-family-veto a real green bare `go test` run.
        out = ("===== integration suite finished in 3.21s =====\n"
               "ok  \texample.com/pkg\t0.012s\n")
        rc, verdict = _verdict(out, "npm test", "0")
        self.assertEqual((rc, verdict), (0, "true"))


PYTEST_FAILED = ("platform darwin -- Python 3.9.6, pytest-8.4.2\n"
                 "rootdir: /tmp/x\ncollected 3 items\n\n"
                 "=========== 1 failed, 2 passed in 0.42s ===========\n")


class TestGreenContradictionVeto(unittest.TestCase):
    """iter76 SF-012(a) Stage 6: 出力に positive な failure 証拠があるのに
    exit code が 0 ＝ exit が洗浄された（`pytest -q; true`）か出力が偽造
    された run ＝ green を証明できない → false。実 red run（exit≠0）は
    軸の対象外＝verdict true のまま（judge の red 信号を守る）。"""

    def test_w2b1_failed_summary_with_exit0_is_false(self):
        # W2b-1（differential: pre-fix true）: washed-green の核。
        rc, out = _verdict(PYTEST_FAILED, "python3 -m pytest -q; true", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_w2b2_failed_summary_with_exit1_stays_true(self):
        # W2b-2（非退行）: 正直な red run — marker は「テストが走った」
        # 証明として true を維持（status=fail 側が red を出す）。
        rc, out = _verdict(PYTEST_FAILED, "python3 -m pytest -q", "1")
        self.assertEqual((rc, out), (0, "true"))

    def test_w2b3_cargo_zero_failed_green_stays_true(self):
        # W2b-3（非退行）: cargo は green でも常に `0 failed` を出力する。
        # 非ゼロアンカーが誤発火しないこと。
        out_text = ("running 3 tests\n"
                    "test tests::a ... ok\n"
                    "test result: ok. 3 passed; 0 failed; 0 ignored; "
                    "0 measured; 0 filtered out; finished in 0.01s\n")
        rc, out = _verdict(out_text, "cargo test", "0")
        self.assertEqual((rc, out), (0, "true"))

    def test_w2b4_unittest_failed_banner_with_exit0_is_false(self):
        # W2b-4（differential: pre-fix true）: unittest は Ran 行に failed
        # カウントを持たない＝FAILED バナー自体が証拠。
        out_text = "Ran 3 tests in 0.010s\n\nFAILED (failures=1)\n"
        rc, out = _verdict(out_text, "python3 -m unittest; true", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_w2b5_rc3_when_fail_token_regex_emptied(self):
        # W2b-5（differential: pre-fix rc0）: fail-token regex は 8 ソース
        # rc3 ガードの一員 — 空にされた install は「veto が黙って無効」
        # （fail-open）ではなく評価不能（rc3）。
        with tempfile.TemporaryDirectory() as d:
            lib_dir = Path(d)
            shutil.copy(MARKER_LIB, lib_dir / "marker.sh")
            pats = (ROOT / "hooks" / "lib" / "patterns.sh").read_text(
                encoding="utf-8")
            pats = re.sub(r"^AEGIS_TEST_FAIL_TOKEN_REGEX=.*$",
                          "AEGIS_TEST_FAIL_TOKEN_REGEX=''",
                          pats, flags=re.M)
            (lib_dir / "patterns.sh").write_text(pats, encoding="utf-8")
            rc, _out = _verdict(PYTEST_REAL, "python3 -m pytest tests/",
                                "0", lib=lib_dir / "marker.sh")
            self.assertEqual(rc, 3)


if __name__ == "__main__":
    unittest.main()
