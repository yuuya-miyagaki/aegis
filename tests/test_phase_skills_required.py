#!/usr/bin/env python3
"""S-11: hooks/lib/phase-skills.sh must be a REQUIRED hook file.

F6 (functional-integrity audit, 2026-06-07) showed lib/ files are the
hooks' life support — a missing lib silently fail-opens every sourcing
hook. The fix at that time enumerated lib/extract-input.sh, lib/emit.sh,
lib/patterns.sh, lib/frontmatter.sh, lib/evidence.sh, lib/fingerprint.sh
in REQUIRED_HOOK_FILES so the contract test would FAIL on install if any
were missing.

When v1.6.0 added hooks/lib/phase-skills.sh (Task P1-A) for skill
reachability, the new lib was NOT registered. The same silent fail-open
class of bug as F6 applies: an install missing phase-skills.sh would
have session-start.sh and post-status-audit.sh fail at source time,
and the contract test would not catch it.

This test pins phase-skills.sh into REQUIRED_HOOK_FILES (and the example
mirror counterpart in REQUIRED_EXAMPLE_FILES) at the contract level so
the F6 lesson stays applied to all subsequent lib additions too.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "scripts" / "check_framework_contract.py"
SCRIPTS = ROOT / "scripts"


def _load_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "check_framework_contract", str(CONTRACT))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestPhaseSkillsRequired(unittest.TestCase):
    def test_phase_skills_sh_in_required_hook_files(self):
        m = _load_module()
        rels = [str(p.relative_to(m.ROOT)) for p in m.REQUIRED_HOOK_FILES]
        self.assertIn(
            "hooks/lib/phase-skills.sh", rels,
            f"hooks/lib/phase-skills.sh missing from REQUIRED_HOOK_FILES. "
            f"F6 lesson: lib/ files are hook life support; a missing lib "
            f"silently fail-opens every sourcing hook. Current REQUIRED libs: "
            f"{[r for r in rels if 'lib/' in r]}")

    def test_secrets_patterns_sh_in_required_hook_files(self):
        """grill-code B-S2 / S-11 (v1.6.1): same class of fail-open as
        phase-skills.sh. check-secrets.sh sources secrets-patterns.sh — if
        the lib is missing at install, the entire credential-pattern deny
        path silently fails."""
        m = _load_module()
        rels = [str(p.relative_to(m.ROOT)) for p in m.REQUIRED_HOOK_FILES]
        self.assertIn(
            "hooks/lib/secrets-patterns.sh", rels,
            f"hooks/lib/secrets-patterns.sh missing from REQUIRED_HOOK_FILES. "
            f"Sourced by check-secrets.sh — a missing lib silently fail-opens "
            f"the secret-staging deny path.")

    def test_example_mirror_phase_skills_in_required_example_files(self):
        m = _load_module()
        rels = [str(p.relative_to(m.ROOT)) for p in m.REQUIRED_EXAMPLE_FILES]
        self.assertIn(
            "examples/minimal-project/hooks/lib/phase-skills.sh", rels,
            f"examples/minimal-project/hooks/lib/phase-skills.sh missing from "
            f"REQUIRED_EXAMPLE_FILES.")

    def test_example_mirror_secrets_patterns_in_required_example_files(self):
        m = _load_module()
        rels = [str(p.relative_to(m.ROOT)) for p in m.REQUIRED_EXAMPLE_FILES]
        self.assertIn(
            "examples/minimal-project/hooks/lib/secrets-patterns.sh", rels,
            f"examples/minimal-project/hooks/lib/secrets-patterns.sh missing "
            f"from REQUIRED_EXAMPLE_FILES — mirror byte-identity is not "
            f"covered for this lib.")

    def test_phase_skills_sh_actually_exists(self):
        """Sanity: the file the contract requires must really be there."""
        self.assertTrue(
            (ROOT / "hooks" / "lib" / "phase-skills.sh").exists(),
            "hooks/lib/phase-skills.sh missing from working tree")
        self.assertTrue(
            (ROOT / "examples" / "minimal-project" / "hooks" / "lib"
             / "phase-skills.sh").exists(),
            "examples/minimal-project/hooks/lib/phase-skills.sh missing")


if __name__ == "__main__":
    unittest.main()
