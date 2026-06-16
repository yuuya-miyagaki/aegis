#!/usr/bin/env python3
"""Task 1.3 (OBS-018): the control-plane allowlist must include the
evidence-recording scripts.

record-test-result.py (appends a Bash test observation to the evidence log) and
run-test-strength-drill.py (runs the B1 mutation drill) are invoked by the agent
during normal (non-framework) project work, but their `scripts/...` path matched
the control-plane regex and was DENIED — only check_framework_contract.py /
check_status.py / update-gate.sh were allowlisted. A bare (no-chain, no-redirect)
invocation of either must now be allowed; the allowlist's no-chain guard must be
preserved, so a chained command or a write redirect to control-plane still denies.

Harness mirrors tests/test_control_plane_var_expansion.py: a scratch root with a
feature-task STATUS.md (so the control-plane checks are active, not short-circuited
by task_type=framework), the hook, and the libs it sources.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch_root() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


class TestEvidenceScriptsAllowlisted(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_record_test_result_bare_is_allowed(self):
        out = _hook(
            self.root,
            "python3 scripts/record-test-result.py --cmd 'pytest tests/' --status ok")
        self.assertTrue(_allowed(out),
                        f"record-test-result must be allowed: {out[:200]!r}")

    def test_run_test_strength_drill_bare_is_allowed(self):
        out = _hook(
            self.root,
            "python3 scripts/run-test-strength-drill.py --root . "
            "--spec docs/qa-reports/test-strength.drill "
            "--report docs/qa-reports/test-strength.md")
        self.assertTrue(_allowed(out),
                        f"run-test-strength-drill must be allowed: {out[:200]!r}")

    def test_record_test_result_with_chain_still_denied(self):
        out = _hook(
            self.root,
            "python3 scripts/record-test-result.py --status ok "
            "&& rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out),
                        f"chained invocation must still deny: {out[:200]!r}")

    def test_run_drill_with_write_redirect_still_denied(self):
        out = _hook(
            self.root,
            "python3 scripts/run-test-strength-drill.py --root . "
            "> hooks/lib/emit.sh")
        self.assertTrue(_denied(out),
                        f"write redirect must still deny: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
