#!/usr/bin/env python3
"""Unit tests for check_reference_drift.check_mirror_identity (audit A5).

Control files copied into examples/minimal-project must stay byte-identical to
the framework root; templated files and allowlisted scaffold-safe variants are
excluded. These tests exercise the function logic against controlled fixtures,
independent of the real repository state.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_reference_drift import check_mirror_identity


class TestMirrorIdentity(unittest.TestCase):
    def _scaffold(self, tmp: Path) -> Path:
        """Create a minimal root + example layout. Returns the root path."""
        root = tmp / "fw"
        ex = root / "examples" / "minimal-project"
        for base in (root, ex):
            (base / ".claude" / "rules").mkdir(parents=True, exist_ok=True)
            (base / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
            (base / "hooks" / "lib").mkdir(parents=True, exist_ok=True)
        return root

    def test_identical_mirror_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            ex = root / "examples" / "minimal-project"
            for base in (root, ex):
                (base / ".claude" / "rules" / "routing.md").write_text("same\n")
                (base / "hooks" / "session-start.sh").write_text("#!/bin/sh\necho hi\n")
            failures, _ = check_mirror_identity(root)
            self.assertEqual(failures, [], f"identical mirrors must pass, got: {failures}")

    def test_content_drift_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            ex = root / "examples" / "minimal-project"
            (root / "hooks" / "session-start.sh").write_text("#!/bin/sh\necho NEW\n")
            (ex / "hooks" / "session-start.sh").write_text("#!/bin/sh\necho OLD\n")
            failures, _ = check_mirror_identity(root)
            self.assertEqual(len(failures), 1, f"expected one drift, got: {failures}")
            self.assertIn("session-start.sh", failures[0])

    def test_allowlisted_command_divergence_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            ex = root / "examples" / "minimal-project"
            # validate.md is an intentional scaffold-safe divergence → must NOT fail.
            (root / ".claude" / "commands" / "validate.md").write_text("ROOT variant\n")
            (ex / ".claude" / "commands" / "validate.md").write_text("EXAMPLE variant\n")
            failures, _ = check_mirror_identity(root)
            self.assertEqual(failures, [], f"allowlisted divergence must be ignored, got: {failures}")

    def test_file_present_only_in_root_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            # Root has an extra hook the example does not ship; presence is enforced
            # elsewhere, so the identity check must not fail on a one-sided file.
            (root / "hooks" / "root-only.sh").write_text("#!/bin/sh\n")
            failures, _ = check_mirror_identity(root)
            self.assertEqual(failures, [], f"one-sided file must be skipped, got: {failures}")

    def test_drill_runner_registered_in_mirror_files(self):
        from check_reference_drift import MIRROR_FILES
        self.assertIn(Path("scripts") / "run-test-strength-drill.py", MIRROR_FILES)


if __name__ == "__main__":
    unittest.main()
