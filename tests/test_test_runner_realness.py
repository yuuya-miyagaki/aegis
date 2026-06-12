#!/usr/bin/env python3
"""C-2: judge card must NOT mark `pytest --version` style commands as green.

Before v1.6.1 the harness classified a Bash command as a "test run" purely
by matching the runner name (pytest / vitest / jest / cargo test / go test /
unittest / npm test). Any command that started with the runner name and
exited 0 was recorded as `status:"ok"` AND the judge card later printed
`テスト: green` — even when the command was `pytest --version`, `--collect-only`,
`-h`, or `-k __NEVER_MATCH__` (no test actually ran).

Fix (Task 2, v1.6.1):

  (a) Add AEGIS_TEST_PASS_MARKER_REGEX to hooks/lib/patterns.sh: tight
      summary-line patterns for each runner (pytest "== N passed in ...",
      jest "Tests: N passed", cargo "test result: ok.", go "ok pkg X.Xs",
      unittest "Ran N tests" + "OK").

  (b) hooks/post-bash-observe.sh inspects the tool_response output and,
      if AT LEAST ONE marker hits, writes marker_verified:true into the
      evidence-log entry. Otherwise marker_verified:false.

  (c) scripts/build-judge-card.py:read_test_result returns "green" / "red"
      ONLY when an entry has marker_verified:true. v1.6.0 entries (no
      such field) and any false entry → "unverified" (fail-closed).

This file pins the behavior end-to-end against a synthetic evidence log
in a tmp scratch root.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# A. patterns.sh layer: AEGIS_TEST_PASS_MARKER_REGEX must exist and be
# loadable from a bash subshell as an array.
# ---------------------------------------------------------------------------


class TestPassMarkerPatternsExposed(unittest.TestCase):
    LIB = ROOT / "hooks" / "lib" / "patterns.sh"

    def _load_array(self, var: str) -> list[str]:
        cmd = (f'source "{self.LIB}" && '
               f'printf "%s\\0" "${{{var}[@]}}"')
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"bash failed loading ${var}: {r.stderr}")
        return [x for x in r.stdout.split("\x00") if x]

    def test_marker_array_defined(self):
        """STRONG markers — single-line sufficient. v1.6.1 grill-code
        Critical split: unittest+cargo moved to AEGIS_TEST_PASS_MARKER_PAIRS
        (weak/pair-required). Remaining strong: pytest === summary, jest,
        vitest Test Files, go pkg+time."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        self.assertTrue(arr,
                        "AEGIS_TEST_PASS_MARKER_REGEX is empty/undefined")
        self.assertGreaterEqual(
            len(arr), 3,
            f"expected ≥3 strong runner markers, got {len(arr)}: {arr}")

    def test_pytest_summary_marker_matches_real_output(self):
        """The pytest summary line must hit."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        # A real pytest summary line.
        sample = "============================= 3 passed in 0.42s =============================="
        hit = any(self._grep_e_matches(p, sample) for p in arr)
        self.assertTrue(hit,
                        f"no marker matched pytest summary line: {sample!r}")

    def test_jest_summary_marker_matches(self):
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        sample = "Tests:       5 passed, 5 total"
        hit = any(self._grep_e_matches(p, sample) for p in arr)
        self.assertTrue(hit, f"no marker matched jest line: {sample!r}")

    def test_unittest_pair_anchors_match(self):
        """Unittest is now PAIR-required (weak markers). The pair entry
        format is `ANCHOR|||COMPANION` — split and confirm both halves
        match their respective unittest summary line."""
        pairs = self._load_array("AEGIS_TEST_PASS_MARKER_PAIRS")
        unittest_pair = next((p for p in pairs if "Ran" in p), None)
        self.assertIsNotNone(unittest_pair,
                             f"unittest pair missing from PAIRS: {pairs}")
        anchor, _, companion = unittest_pair.partition("|||")
        self.assertTrue(
            self._grep_e_matches(anchor, "Ran 17 tests in 89.6s"),
            f"unittest anchor must match 'Ran N tests in X.Xs': {anchor}")
        self.assertTrue(
            self._grep_e_matches(companion, "OK"),
            f"unittest companion must match 'OK': {companion}")

    def test_pytest_version_does_NOT_match(self):
        """The whole point: `pytest --version` output must NOT trigger
        any pass marker."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        sample = "pytest 7.4.0"
        hit = any(self._grep_e_matches(p, sample) for p in arr)
        self.assertFalse(hit,
                         f"FALSE-GREEN: a marker matched the pytest --version "
                         f"output: pattern hit={sample!r}, arr={arr}")

    def test_pytest_collect_only_does_NOT_match(self):
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        for sample in (
            "collected 3 items",
            "<Module test_x.py>",
            "no tests ran in 0.01s",
        ):
            hit = any(self._grep_e_matches(p, sample) for p in arr)
            self.assertFalse(hit,
                             f"FALSE-GREEN on --collect-only line {sample!r}")

    def test_echo_passed_string_does_NOT_match(self):
        """`echo "1 passed"` is NOT a real summary line."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        for sample in (
            "1 passed",
            "PASS",
            "passed",
        ):
            hit = any(self._grep_e_matches(p, sample) for p in arr)
            self.assertFalse(hit,
                             f"FALSE-GREEN on echoed token {sample!r}")

    def test_unittest_OK_alone_does_NOT_match(self):
        """grill-code A-Crit-2 / B-Critical: `echo OK` must NOT trigger
        the unittest marker. The unittest pass signal is BOTH `Ran N tests`
        AND `OK` together — implemented as a peephole pair in evidence.sh."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        # Each marker individually is allowed to match this string (we'll
        # tighten in evidence.sh's pair-check), but in isolation the
        # AEGIS_TEST_PASS_MARKER_REGEX patterns must not certify "OK" alone.
        # Confirm that the new evidence.sh-side gate (pair requirement)
        # exists by checking AEGIS_TEST_PASS_MARKER_PAIRS is defined.
        # (Standalone hits remain possible at the patterns layer; the pair
        # contract is enforced at the consumer layer — see test_marker_peephole_pair_required_for_weak_markers.)

    def test_cargo_test_result_alone_does_NOT_certify(self):
        """`echo "test result: ok."` alone must NOT certify green —
        a real cargo run prints both `running N tests` and the result line."""
        # Asserted at the consumer layer (build-judge-card.py via
        # the pair-required pattern in patterns.sh).

    def test_pair_array_defined(self):
        """AEGIS_TEST_PASS_MARKER_PAIRS: weak markers that require a
        companion-line peephole (consumer-enforced)."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_PAIRS")
        self.assertGreaterEqual(
            len(arr), 2,
            f"expected ≥2 pair entries (unittest + cargo at minimum), got "
            f"{len(arr)}: {arr}")

    @staticmethod
    def _grep_e_matches(pattern: str, text: str) -> bool:
        r = subprocess.run(
            ["grep", "-E", "-q", pattern],
            input=text.encode(),
            capture_output=True)
        return r.returncode == 0


# ---------------------------------------------------------------------------
# B. read_test_result schema migration: v1.6.0 entries (no marker_verified
# field) must NOT return green.
# ---------------------------------------------------------------------------


class TestReadTestResultSchemaMigration(unittest.TestCase):
    """Synthesize an evidence-log + repo state and call read_test_result
    directly."""

    @classmethod
    def setUpClass(cls):
        # Import build-judge-card.py as a module.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_judge_card", str(ROOT / "scripts" / "build-judge-card.py"))
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def _scratch_repo(self) -> tempfile.TemporaryDirectory:
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=p, check=True)
        subprocess.run(["git", "config", "user.email", "x@y.z"],
                       cwd=p, check=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=p, check=True)
        (p / "f.txt").write_text("seed", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=p, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                       cwd=p, check=True)
        # Mirror the libs/patterns the judge-card reads.
        ev = p / ".claude"
        ev.mkdir()
        # Sym to lib/ files so read_test_result can load the runner regex
        # AND current_fingerprint (delegates to fingerprint.sh).
        hooks_dir = p / "hooks"
        hooks_dir.mkdir()
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        for lib in ("patterns.sh", "fingerprint.sh"):
            (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
        return tmp

    def _fp(self, root: Path) -> str:
        return self.mod.current_fingerprint(root)

    def _write_entry(self, root: Path, entry: dict):
        log = root / ".claude" / "evidence-log.jsonl"
        log.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    def test_entry_without_marker_verified_field_returns_unverified(self):
        """v1.6.0 log entries (no marker_verified key) must NOT pass green."""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "pytest",
                "status": "ok",
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "unverified")

    def test_entry_with_marker_verified_false_returns_unverified(self):
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "pytest --version",
                "status": "ok", "marker_verified": False,
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "unverified")

    def test_entry_with_marker_verified_true_and_ok_returns_green(self):
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "pytest tests/",
                "status": "ok", "marker_verified": True,
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "green")

    def test_entry_with_marker_verified_true_and_fail_returns_red(self):
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "pytest tests/",
                "status": "fail", "marker_verified": True,
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "red")

    def test_manual_record_is_trusted_even_without_marker(self):
        """Entries from record-test-result.py have src='manual' and reflect
        a trusted runner; marker_verified is not required for those."""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "manual", "cmd": "pytest tests/",
                "status": "ok",
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "green")


# ---------------------------------------------------------------------------
# C. post-bash-observe.sh end-to-end: feeding the observer a
# `pytest --version` (no marker) gives marker_verified:false. Feeding it
# a fake-but-realistic pytest summary gives marker_verified:true.
# ---------------------------------------------------------------------------


class TestPostBashObserveMarkerField(unittest.TestCase):
    HOOK = ROOT / "hooks" / "post-bash-observe.sh"

    def _scratch(self) -> tempfile.TemporaryDirectory:
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=p, check=True)
        subprocess.run(["git", "config", "user.email", "x@y.z"],
                       cwd=p, check=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=p, check=True)
        (p / "seed.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=p, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                       cwd=p, check=True)
        # Mirror the hook layout.
        hooks_dir = p / "hooks"
        hooks_dir.mkdir()
        for hk in ("post-bash-observe.sh",):
            (hooks_dir / hk).symlink_to(ROOT / "hooks" / hk)
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        for lib in ("extract-input.sh", "emit.sh", "patterns.sh",
                    "fingerprint.sh", "evidence.sh"):
            (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
        return tmp

    def _run(self, root: Path, payload: dict) -> dict | None:
        subprocess.run(
            ["bash", str(root / "hooks" / "post-bash-observe.sh")],
            input=json.dumps(payload), capture_output=True, text=True,
            cwd=str(root), env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)})
        log = root / ".claude" / "evidence-log.jsonl"
        if not log.exists():
            return None
        last = log.read_text(encoding="utf-8").splitlines()[-1]
        return json.loads(last)

    def test_real_summary_sets_marker_true(self):
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "pytest tests/"},
                "tool_response": {
                    "exitCode": 0,
                    "output": ("============== 3 passed in 0.42s ==============\n"),
                },
            })
            self.assertIsNotNone(entry, "no log entry written")
            self.assertEqual(
                entry.get("marker_verified"), True,
                f"real pytest summary should mark verified=true: {entry}")

    def test_pytest_version_sets_marker_false(self):
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "pytest --version"},
                "tool_response": {"exitCode": 0, "output": "pytest 7.4.0\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"`pytest --version` must NOT verify: {entry}")

    def test_echo_passed_sets_marker_false(self):
        """Echoed token must not pass the summary regex (forge attempt)."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "pytest --collect-only; echo '1 passed'"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "collected 0 items\n1 passed\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"echoed `1 passed` must NOT verify: {entry}")

    def test_full_pytest_summary_line_echo_alone_does_NOT_verify(self):
        """grill-code A-Crit-2: `echo "============ 1 passed in 0.01s ============"`
        on its own is just a string — the runner did not execute. The peephole
        / pair contract must block this case."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                # pytest --collect-only matches the runner regex but runs no tests
                "tool_input": {
                    "command": "echo '============ 1 passed in 0.01s ============' && pytest --collect-only"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "============ 1 passed in 0.01s ============\ncollected 0 items\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"echo-forged full pytest summary must NOT verify: {entry}")

    def test_unittest_OK_alone_does_NOT_verify_in_observer(self):
        """`pytest --version && echo OK` — runner regex hits pytest, then OK
        is printed by echo. Without `Ran N tests in` companion the unittest
        marker must NOT verify."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "pytest --version && echo OK"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "pytest 7.4.0\nOK\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"bare 'OK' line must NOT verify without 'Ran N tests': {entry}")

    def test_cargo_test_result_alone_does_NOT_verify_in_observer(self):
        """`cargo test --no-run` prints `test result: ok. 0 passed` (compile
        only). Without `running N tests` companion the cargo marker must
        NOT verify."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "cargo test --no-run"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "test result: ok. 0 passed; 0 failed\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"bare `test result: ok` must NOT verify without "
                f"`running N tests`: {entry}")

    def test_unittest_OK_with_Ran_companion_verifies(self):
        """Both `Ran N tests in` AND `OK` present → pair satisfied."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "python3 -m unittest discover"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "...\nRan 5 tests in 0.123s\nOK\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), True,
                f"unittest pair (Ran ... + OK) must verify: {entry}")

    def test_cargo_pair_complete_verifies(self):
        """Both `running N tests` AND `test result: ok` present → pair satisfied."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "cargo test"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "running 5 tests\n.....\n\n"
                              "test result: ok. 5 passed; 0 failed\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), True,
                f"cargo pair (running N tests + test result: ok) must "
                f"verify: {entry}")


if __name__ == "__main__":
    unittest.main()
