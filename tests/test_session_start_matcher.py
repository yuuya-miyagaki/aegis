#!/usr/bin/env python3
"""C-4: SessionStart matcher must include `resume`.

Claude Code's SessionStart hook fires for 4 documented events: `startup`,
`resume`, `clear`, `compact`. The v1.6.0 templates had the matcher set to
`startup|clear|compact` (full review axis E, finding C-4) — so on `--resume`
or conversation-restore the SessionStart hook silently does not fire and
the v1.6.0 P1-A invariants (STATUS.md additionalContext injection, gate
snapshot regeneration, evidence-log rotation) all skip.

This test pins the matcher in the framework template to include all four
events, preventing the silent-fail-open regression.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = ROOT / "templates" / "hooks.template.json"

REQUIRED_EVENTS = {"startup", "resume", "clear", "compact"}


def _session_start_matchers(settings_json_path: Path) -> list[str]:
    data = json.loads(settings_json_path.read_text(encoding="utf-8"))
    hooks_config = data.get("hooks") or {}
    entries = hooks_config.get("SessionStart") or []
    return [e.get("matcher", "") for e in entries]


class TestSessionStartMatcher(unittest.TestCase):
    def test_template_matcher_includes_all_4_events(self):
        matchers = _session_start_matchers(TEMPLATE)
        self.assertTrue(matchers,
                        f"{TEMPLATE} has no SessionStart hook entries")
        # at least one entry must include all 4 events
        ok = any(REQUIRED_EVENTS.issubset(set(m.split("|"))) for m in matchers)
        self.assertTrue(
            ok,
            f"None of the SessionStart matchers cover all 4 events "
            f"({REQUIRED_EVENTS}). matchers={matchers}")

    def test_resume_specifically_present_in_template(self):
        """Regression-pin the specific missing event from the C-4 finding."""
        matchers = _session_start_matchers(TEMPLATE)
        all_events = set()
        for m in matchers:
            all_events.update(m.split("|"))
        self.assertIn("resume", all_events,
                      f"`resume` event missing from SessionStart matcher "
                      f"in {TEMPLATE} — restored sessions skip the hook. "
                      f"matchers={matchers}")


if __name__ == "__main__":
    unittest.main()
