#!/usr/bin/env python3
"""check-secrets.sh が lib/secrets-patterns.sh を単一所有として消費する契約。

Task 6: lib (Task 0) が新設された後、check-secrets.sh は 4 形式すべてを
lib 経由に置き換える。本テストは「(a) hook が lib を source する」「(b) hook
本体にクレデンシャル名のリテラル列挙が残っていない（emit_* のエラー文を
除く）」「(c) 4 形式すべての検出が機能を維持する」を契約化する。
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-secrets.sh"
LIB = ROOT / "hooks" / "lib" / "secrets-patterns.sh"

_PERMISSION_DENY = '"permissionDecision":"deny"'


def _run_hook(cmd: str, *, cwd: Path | None = None) -> tuple[int, str]:
    payload = (
        '{"tool_name":"Bash","tool_input":{"command":'
        + subprocess.list2cmdline([cmd]).encode("unicode_escape").decode()
        + "}}"
    )
    # Build the JSON safely.
    import json as _json
    payload = _json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(HOOK)],
        input=payload, capture_output=True, text=True,
        cwd=str(cwd) if cwd else None)
    return r.returncode, r.stdout


class TestCheckSecretsConsumesLib(unittest.TestCase):
    def test_hook_sources_the_lib(self):
        """check-secrets.sh must source hooks/lib/secrets-patterns.sh."""
        text = HOOK.read_text(encoding="utf-8")
        self.assertIn(
            "secrets-patterns.sh", text,
            "check-secrets.sh does not source hooks/lib/secrets-patterns.sh")

    def test_hook_has_no_literal_credential_tokens(self):
        """After refactor, the hook body must not duplicate the credential
        token lists that live in the lib. Allowed: comments and emit_*
        error-message prose that mention these names for the user."""
        text = HOOK.read_text(encoding="utf-8")
        kept = []
        for ln in text.splitlines():
            stripped = ln.lstrip()
            if stripped.startswith("#"):
                continue
            if "emit_" in ln:
                continue
            kept.append(ln)
        body = "\n".join(kept)
        # The lib variable names are allowed (they contain "id_" / "pem"-ish
        # substrings depending on how we test). We assert the structural
        # tokens that should NOT appear bare in the hook body.
        for tok in ("id_rsa", "id_ed25519", "id_ecdsa",
                    "service-account*.json"):
            self.assertNotIn(
                tok, body,
                f"check-secrets.sh still has literal {tok!r} outside "
                f"comments/emit lines (it should live only in the lib)")


class TestCheckSecretsBehaviorPreserved(unittest.TestCase):
    """Form 1+2+3+4 detection paths still fire after the lib refactor.

    We invoke the hook end-to-end (the same way Claude Code does) and assert
    deny is emitted for the existing credential scenarios.
    """

    def test_form1_command_text_regex_denies_pem_in_git_add(self):
        """Form 1 (command-text regex / HIGH_RISK_RE): direct `git add cert.pem`."""
        rc, out = _run_hook("git add server.pem")
        self.assertIn(_PERMISSION_DENY, out,
                      f"PEM via git add should deny; got: {out[:120]}")

    def test_form1_command_text_regex_denies_id_rsa_in_git_add(self):
        rc, out = _run_hook("git add id_rsa")
        self.assertIn(_PERMISSION_DENY, out,
                      f"id_rsa via git add should deny; got: {out[:120]}")

    def test_form1_command_text_regex_denies_credentials_json(self):
        rc, out = _run_hook("git add gcp-credentials.json")
        self.assertIn(_PERMISSION_DENY, out,
                      f"credentials.json via git add should deny; got: {out[:120]}")

    def test_form1_command_text_regex_denies_service_account(self):
        rc, out = _run_hook("git add service-account-prod.json")
        self.assertIn(_PERMISSION_DENY, out,
                      f"service-account*.json should deny; got: {out[:120]}")

    def test_form2_3_broad_staging_detects_repo_credentials(self):
        """Form 2 (case glob) + Form 3 (find -name): `git add -A` in a repo
        containing a high-risk credential basename should deny."""
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            # Initialize a real git repo so `git rev-parse --show-toplevel` works.
            subprocess.run(["git", "init", "-q"], cwd=tdir, check=True)
            # Drop a credential file at the root.
            (tdir / "id_ed25519").write_text("FAKE-KEY", encoding="utf-8")
            rc, out = _run_hook("git add -A", cwd=tdir)
            self.assertIn(_PERMISSION_DENY, out,
                          f"git add -A with id_ed25519 present should deny; "
                          f"got: {out[:120]}")

    def test_form4_staged_path_regex_denies_pem_in_commit(self):
        """Form 4 (staged-path regex): commit with PEM in staged diff denies."""
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=tdir, check=True)
            subprocess.run(["git", "config", "user.email", "x@y.z"],
                           cwd=tdir, check=True)
            subprocess.run(["git", "config", "user.name", "t"],
                           cwd=tdir, check=True)
            # Stage a PEM file directly (so the staged regex hits).
            (tdir / "leaked.pem").write_text("FAKE-PEM", encoding="utf-8")
            subprocess.run(["git", "add", "leaked.pem"],
                           cwd=tdir, check=True)
            rc, out = _run_hook("git commit -m wip", cwd=tdir)
            self.assertIn(_PERMISSION_DENY, out,
                          f"commit with staged PEM should deny; got: {out[:120]}")

    def test_unrelated_command_still_allows(self):
        """Regression guard: harmless commands must remain allowed."""
        rc, out = _run_hook("ls -la")
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"ls should not deny; got: {out[:120]}")
        rc, out = _run_hook("git add README.md")
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"README.md should not deny; got: {out[:120]}")


if __name__ == "__main__":
    unittest.main()
