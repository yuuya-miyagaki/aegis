#!/usr/bin/env python3
"""Audit F1: the contract manifest must track every registered hook.

check_framework_contract enforces REQUIRED ⊆ registered (every required hook is
registered in the template). These tests enforce the OTHER direction —
registered ⊆ REQUIRED — so a hook added to a registration (template / example
settings) but forgotten in the manifest is caught. Together they pin the
manifest to reality.

⊆ (not ==) on purpose: a hook may legitimately be REQUIRED-but-unregistered in
the future (manual / non-event invocation), so we do not force equality.
lib/ helpers are excluded: the template never registers them.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_framework_contract as contract  # noqa: E402

# Same extraction the contract/drift use: "bash hooks/foo.sh" -> "foo.sh".
_HOOK_RE = re.compile(r"hooks/([a-z0-9_-]+\.sh)")


def _registered_hooks(settings_path: Path) -> set[str]:
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for entries in data.get("hooks", {}).values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for hook in entry.get("hooks", []):
                m = _HOOK_RE.search(hook.get("command", "") if isinstance(hook, dict) else "")
                if m:
                    found.add(m.group(1))
    return found


class TestHookRequiredCoverage(unittest.TestCase):
    def test_template_registered_hooks_are_in_required_hook_files(self):
        """B-1 root: hooks.template.json registrations ⊆ REQUIRED_HOOK_FILES."""
        registered = _registered_hooks(ROOT / "templates" / "hooks.template.json")
        required = {
            p.name
            for p in contract.REQUIRED_HOOK_FILES
            if p.parent == ROOT / "hooks" and p.suffix == ".sh"
        }
        missing = registered - required
        self.assertEqual(
            missing,
            set(),
            f"hooks registered in hooks.template.json but absent from "
            f"REQUIRED_HOOK_FILES (contract cannot track them): {sorted(missing)}",
        )

    def test_example_registered_hooks_are_in_required_example_files(self):
        """B-2 example: example settings.json registrations ⊆ REQUIRED_EXAMPLE_FILES."""
        registered = _registered_hooks(
            ROOT / "examples" / "minimal-project" / ".claude" / "settings.json"
        )
        example_hooks_dir = ROOT / "examples" / "minimal-project" / "hooks"
        required = {
            p.name
            for p in contract.REQUIRED_EXAMPLE_FILES
            if p.parent == example_hooks_dir and p.suffix == ".sh"
        }
        missing = registered - required
        self.assertEqual(
            missing,
            set(),
            f"hooks registered in example settings.json but absent from "
            f"REQUIRED_EXAMPLE_FILES: {sorted(missing)}",
        )


def _hook_commands(settings_path: Path) -> list[str]:
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    cmds: list[str] = []
    for entries in data.get("hooks", {}).values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for hook in entry.get("hooks", []):
                if isinstance(hook, dict) and "hooks/" in hook.get("command", ""):
                    cmds.append(hook["command"])
    return cmds


class TestScriptRelFromCommand(unittest.TestCase):
    """Contract validator must resolve both command forms to hooks/<name>.sh."""

    def test_fallback_form_resolves_to_hooks_path(self):
        self.assertEqual(
            contract.script_rel_from_command(
                'bash "${CLAUDE_PROJECT_DIR:-.}"/hooks/check-gate.sh'
            ),
            "hooks/check-gate.sh",
        )

    def test_plain_project_dir_form_resolves_to_hooks_path(self):
        self.assertEqual(
            contract.script_rel_from_command(
                'bash "$CLAUDE_PROJECT_DIR"/hooks/check-gate.sh'
            ),
            "hooks/check-gate.sh",
        )

    def test_bare_cwd_relative_form_resolves_to_hooks_path(self):
        self.assertEqual(
            contract.script_rel_from_command("bash hooks/check-gate.sh"),
            "hooks/check-gate.sh",
        )


class TestHookCommandForm(unittest.TestCase):
    """Hook commands must survive an unset CLAUDE_PROJECT_DIR (grill 🟡-2).

    Plain "$CLAUDE_PROJECT_DIR"/hooks/x.sh expands to ""/hooks/x.sh when the
    variable is unset → bash exits 127 → the runtime treats it as a
    non-blocking hook error → every moat hook silently fails open (same
    failure mode as audit F6). The ${CLAUDE_PROJECT_DIR:-.} form falls back
    to cwd-relative (pre-v1.4.0 behavior) instead.
    """

    FALLBACK = '"${CLAUDE_PROJECT_DIR:-.}"/hooks/'

    def _assert_fallback_form(self, settings_path: Path) -> None:
        cmds = _hook_commands(settings_path)
        self.assertTrue(cmds, f"no hook commands found in {settings_path}")
        bad = [c for c in cmds if self.FALLBACK not in c]
        self.assertEqual(
            bad, [],
            f"{settings_path} hook commands lack the unset-safe "
            f"{self.FALLBACK} form: {bad}",
        )

    def test_template_commands_use_fallback_form(self):
        self._assert_fallback_form(ROOT / "templates" / "hooks.template.json")

    def test_example_settings_commands_use_fallback_form(self):
        self._assert_fallback_form(
            ROOT / "examples" / "minimal-project" / ".claude" / "settings.json"
        )


if __name__ == "__main__":
    unittest.main()
