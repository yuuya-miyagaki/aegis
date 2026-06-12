#!/usr/bin/env python3
"""hooks/lib/secrets-patterns.sh の単一所有契約。

C-9: check-secrets.sh が 4 形式（command-text regex / case glob / find -name /
staged regex）で credential リテラルを重複保持していた。Task 0 で lib を
新設し、Task 6 で check-secrets.sh を lib 経由に書き換える。本テストは
lib の存在・構文・変数定義・credential 集合カバレッジを契約化する。

Task 6 の「リテラル除去」assert は test_secrets_pattern_consumer.py 側で扱う。
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "secrets-patterns.sh"

# The credential basenames the lib must collectively detect across all 4 forms.
# Derived from check-secrets.sh v1.6.0 behavior.
REQUIRED_BASENAMES = [
    "server.pem",
    "id_rsa", "id_rsa.pub",
    "id_ed25519", "id_ed25519.pub",
    "id_ecdsa", "id_ecdsa.pub",
    "credentials.json", "gcp-credentials.json",
    "service-account.json", "service-account-prod.json",
]

# Basenames that must NOT match (false-positive guard).
MUST_NOT_MATCH = [
    "README.md", "app.py", "config.yaml",
    "credential.txt",          # missing 's' and not .json
    "id_rsa.bak",              # not exact key — but case glob `id_rsa*` would match
                                # → keep this OUT of MUST_NOT_MATCH (see test_case_glob)
    "myservice-account.txt",   # not .json
]


class TestSecretsPatternsLib(unittest.TestCase):
    """Task 0 AC: lib new file is sourceable, defines 4 variables, covers
    the credential set the four-form duplicate in check-secrets.sh covered."""

    def test_lib_file_exists(self):
        """The new single-owner lib file must be present at the documented path."""
        self.assertTrue(
            LIB.exists(),
            f"hooks/lib/secrets-patterns.sh missing — Task 0 not yet implemented")

    def test_lib_passes_bash_syntax_check(self):
        """`bash -n` must accept the file (no syntax errors)."""
        rc = subprocess.run(
            ["bash", "-n", str(LIB)],
            capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0,
                         f"bash -n failed: {rc.stderr}")

    def test_lib_passes_shellcheck_if_available(self):
        """If shellcheck is installed, lib must pass with no findings."""
        sc = shutil.which("shellcheck")
        if not sc:
            self.skipTest("shellcheck not installed in this env")
        rc = subprocess.run(
            [sc, "-x", "-e", "SC2034", str(LIB)],
            capture_output=True, text=True)
        # SC2034: variable defined but unused (we EXPECT these — they're a public API)
        self.assertEqual(rc.returncode, 0,
                         f"shellcheck findings: {rc.stdout}")

    def _source_and_print(self, var: str) -> str:
        """Source the lib in a fresh bash and print the named variable."""
        cmd = f'source "{LIB}" && printf "%s" "${{{var}}}"'
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"source failed for ${var}: {r.stderr}")
        return r.stdout

    def _source_and_print_array(self, var: str) -> list[str]:
        """Source the lib and print an array's elements, NUL-separated."""
        cmd = (f'source "{LIB}" && '
               f'printf "%s\\0" "${{{var}[@]}}"')
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"source failed for ${var}: {r.stderr}")
        return [x for x in r.stdout.split("\x00") if x]

    def test_high_risk_re_is_defined(self):
        """Command-text regex (consumed by `grep -qE` in check-secrets.sh:32).

        Checks the regex mentions each credential type's discriminating token.
        The regex may use alternation (id_(rsa|ed25519|ecdsa)) so we test the
        type-name fragments individually. Functional coverage is verified by
        test_high_risk_re_matches_required_basenames."""
        val = self._source_and_print("AEGIS_HIGH_RISK_RE")
        self.assertTrue(val, "AEGIS_HIGH_RISK_RE is empty/undefined")
        for marker in ("pem", "rsa", "ed25519", "ecdsa",
                       "credentials", "service-account"):
            self.assertIn(marker, val,
                          f"AEGIS_HIGH_RISK_RE missing {marker!r}")
        # id_ prefix must exist (anchors the SSH key family)
        self.assertIn("id_", val,
                      "AEGIS_HIGH_RISK_RE missing 'id_' prefix anchor")

    def test_case_glob_is_defined(self):
        """basename case glob (consumed by `case` in check-secrets.sh:60)."""
        val = self._source_and_print("AEGIS_HIGH_RISK_CASE_GLOB")
        self.assertTrue(val, "AEGIS_HIGH_RISK_CASE_GLOB is empty/undefined")
        # must cover the exact glob patterns from the original
        for pat in ("*.pem", "id_rsa", "id_ed25519", "id_ecdsa",
                    "*credentials*.json", "service-account*.json"):
            self.assertIn(pat, val,
                          f"AEGIS_HIGH_RISK_CASE_GLOB missing {pat!r}")

    def test_find_names_is_defined(self):
        """find -name globs as an array (consumed by `find` in check-secrets.sh:64)."""
        arr = self._source_and_print_array("AEGIS_HIGH_RISK_FIND_NAMES")
        self.assertTrue(arr, "AEGIS_HIGH_RISK_FIND_NAMES is empty/undefined")
        for pat in ("*.pem", "id_rsa*", "id_ed25519*", "id_ecdsa*",
                    "*credentials*.json", "service-account*.json"):
            self.assertIn(pat, arr,
                          f"AEGIS_HIGH_RISK_FIND_NAMES missing {pat!r}")

    def test_staged_re_is_defined(self):
        """staged-path regex (consumed by `grep -E` in check-secrets.sh:99)."""
        val = self._source_and_print("AEGIS_HIGH_RISK_STAGED_RE")
        self.assertTrue(val, "AEGIS_HIGH_RISK_STAGED_RE is empty/undefined")
        # the four anchor forms from the original
        for marker in (r"\.pem", "id_(rsa|ed25519|ecdsa)",
                       "credentials", "service-account"):
            self.assertIn(marker, val,
                          f"AEGIS_HIGH_RISK_STAGED_RE missing {marker!r}")

    def test_high_risk_re_matches_required_basenames(self):
        """AEGIS_HIGH_RISK_RE must match every required credential basename
        in a `git add` command-text context (grep -qE invocation)."""
        re = self._source_and_print("AEGIS_HIGH_RISK_RE")
        for bn in REQUIRED_BASENAMES:
            cmd = f"git add {bn}"
            r = subprocess.run(
                ["bash", "-c",
                 f"printf '%s' {subprocess.list2cmdline([cmd])} | grep -qE '{re}'"],
                capture_output=True)
            self.assertEqual(r.returncode, 0,
                             f"AEGIS_HIGH_RISK_RE did not match {bn!r}")

    def test_high_risk_re_does_not_match_false_positives(self):
        """AEGIS_HIGH_RISK_RE must NOT match non-credential basenames."""
        re = self._source_and_print("AEGIS_HIGH_RISK_RE")
        for bn in ("README.md", "app.py", "config.yaml", "credential.txt"):
            cmd = f"git add {bn}"
            r = subprocess.run(
                ["bash", "-c",
                 f"printf '%s' {subprocess.list2cmdline([cmd])} | grep -qE '{re}'"],
                capture_output=True)
            self.assertEqual(r.returncode, 1,
                             f"AEGIS_HIGH_RISK_RE wrongly matched {bn!r}")

    # Task 6 (consumer-side: hook sources the lib, literals removed) is
    # contracted by tests/test_secrets_pattern_consumer.py added in the
    # Task 6 commit. Keeping the two commits' test sets disjoint ensures CI
    # stays green commit-by-commit.


if __name__ == "__main__":
    unittest.main()
