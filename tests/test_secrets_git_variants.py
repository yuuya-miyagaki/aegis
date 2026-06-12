#!/usr/bin/env python3
"""S-3: `.env` staging via git variants must be denied.

The baseline regex `git\\s+add\\s+.*\\.env` (check-secrets.sh:46) misses
`git --git-dir=...`, `git -C dir`, `git stage`, and `git update-index --add`.
Each of these can stage a .env without triggering the existing deny.

v1.6.1 scope: deny 4 bypass variants plus the baseline. `git stash push .env`
is OUT OF SCOPE (legitimate use cases dominate) — see receive list in
docs/qa-reports/v161-security.md.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-secrets.sh"

_PERMISSION_DENY = '"permissionDecision":"deny"'


def _hook(cmd: str) -> tuple[int, str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(HOOK)], input=payload, capture_output=True, text=True)
    return r.returncode, r.stdout


class TestGitVariantBypass(unittest.TestCase):
    """The 5 must-deny variants. Each is a real-world `git add .env` form."""

    def test_baseline_git_add_env_denies(self):
        """Sanity: the unchanged baseline still denies."""
        _, out = _hook("git add .env")
        self.assertIn(_PERMISSION_DENY, out,
                      f"baseline git add .env: {out[:120]}")

    def test_git_with_git_dir_flag_denies(self):
        """`git --git-dir=.git --work-tree=. add .env` must deny."""
        _, out = _hook("git --git-dir=.git --work-tree=. add .env")
        self.assertIn(_PERMISSION_DENY, out,
                      f"--git-dir bypass: {out[:120]}")

    def test_git_dash_C_flag_denies(self):
        """`git -C /tmp/repo add .env` must deny."""
        _, out = _hook("git -C /tmp/repo add .env")
        self.assertIn(_PERMISSION_DENY, out,
                      f"-C bypass: {out[:120]}")

    def test_git_stage_command_denies(self):
        """`git stage .env` is an alias of `git add` — must deny."""
        _, out = _hook("git stage .env")
        self.assertIn(_PERMISSION_DENY, out,
                      f"git stage bypass: {out[:120]}")

    def test_git_update_index_add_denies(self):
        """`git update-index --add .env` plumbing path must deny."""
        _, out = _hook("git update-index --add .env")
        self.assertIn(_PERMISSION_DENY, out,
                      f"update-index bypass: {out[:120]}")

    def test_git_c_kv_flag_denies(self):
        """`git -c safe.directory=foo add .env` (config override) must deny."""
        _, out = _hook("git -c safe.directory=foo add .env")
        self.assertIn(_PERMISSION_DENY, out,
                      f"-c kv bypass: {out[:120]}")


class TestGitVariantAllowList(unittest.TestCase):
    """False-positive guards: legitimate commands must NOT deny."""

    def test_git_status_allows(self):
        _, out = _hook("git status")
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"git status should allow: {out[:120]}")

    def test_git_add_non_env_file_allows(self):
        _, out = _hook("git add main.py")
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"git add main.py should allow: {out[:120]}")

    def test_git_stash_push_env_allowed_v1_6_1_residual(self):
        """v1.6.1 受容済みリスク: git stash push .env is OUT OF SCOPE.

        Stash has legitimate use cases (e.g. temporarily setting aside .env
        during a clean checkout). v1.6.2 may revisit with narrower deny.
        For v1.6.1 the test pins the documented allow-behavior to make the
        receive list explicit.
        """
        _, out = _hook("git stash push .env")
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"git stash push .env: v1.6.1 受容済み・allow 必須 "
                         f"({out[:120]})")

    def test_git_add_safe_env_variants_still_allowed(self):
        """Safe variants (`.env.example` etc.) must keep their existing allow."""
        for safe in (".env.example", ".env.template", ".env.sample"):
            _, out = _hook(f"git add {safe}")
            self.assertNotIn(_PERMISSION_DENY, out,
                             f"safe variant {safe}: {out[:120]}")

    def test_unrelated_command_allows(self):
        _, out = _hook("npm test")
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"npm test: {out[:120]}")


if __name__ == "__main__":
    unittest.main()
