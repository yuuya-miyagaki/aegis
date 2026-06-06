#!/usr/bin/env python3
"""Unit tests for check_status.py extractor functions.

Tests individual parsing functions with edge cases that subprocess-level
tests cannot cover efficiently.
"""

from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_status import (
    check_gate_prerequisites,
    extract_approval_map,
    extract_blockers,
    extract_current_refs,
    extract_frontmatter,
    extract_scalar_value,
    extract_session_history,
    has_top_level_key,
)


class TestExtractFrontmatter(unittest.TestCase):
    """Unit tests for extract_frontmatter()."""

    def test_valid_frontmatter(self):
        text = "---\nkey: value\nphase: plan\n---\n## Body\n"
        result = extract_frontmatter(text)
        self.assertIsNotNone(result)
        self.assertIn("key: value", result)

    def test_missing_opening_marker(self):
        text = "key: value\n---\n"
        result = extract_frontmatter(text)
        self.assertIsNone(result)

    def test_missing_closing_marker(self):
        text = "---\nkey: value\n"
        result = extract_frontmatter(text)
        self.assertIsNone(result)

    def test_empty_frontmatter(self):
        text = "---\n\n---\n"
        result = extract_frontmatter(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.strip(), "")

    def test_frontmatter_with_embedded_dashes(self):
        text = "---\nkey: a-b-c\nother: --flag\n---\n"
        result = extract_frontmatter(text)
        self.assertIsNotNone(result)
        self.assertIn("key: a-b-c", result)


class TestHasTopLevelKey(unittest.TestCase):
    """Unit tests for has_top_level_key()."""

    def test_key_present(self):
        fm = "phase: plan\nmode: Dev"
        self.assertTrue(has_top_level_key(fm, "phase"))

    def test_key_absent(self):
        fm = "phase: plan\nmode: Dev"
        self.assertFalse(has_top_level_key(fm, "missing"))

    def test_nested_key_not_matched(self):
        fm = "gate_approvals:\n  review: pending"
        self.assertFalse(has_top_level_key(fm, "review"))


class TestExtractScalarValue(unittest.TestCase):
    """Unit tests for extract_scalar_value()."""

    def test_quoted_value(self):
        fm = 'phase: "plan"'
        self.assertEqual(extract_scalar_value(fm, "phase"), "plan")

    def test_unquoted_value(self):
        fm = "phase: plan"
        self.assertEqual(extract_scalar_value(fm, "phase"), "plan")

    def test_single_quoted_value(self):
        fm = "phase: 'plan'"
        self.assertEqual(extract_scalar_value(fm, "phase"), "plan")

    def test_missing_key(self):
        fm = "mode: Dev"
        self.assertIsNone(extract_scalar_value(fm, "phase"))

    def test_null_value(self):
        fm = "spec: null"
        self.assertEqual(extract_scalar_value(fm, "spec"), "null")

    def test_empty_string_value(self):
        fm = 'project_name: ""'
        self.assertEqual(extract_scalar_value(fm, "project_name"), "")


class TestExtractApprovalMap(unittest.TestCase):
    """Unit tests for extract_approval_map()."""

    def test_standard_approvals(self):
        fm = textwrap.dedent("""\
            gate_approvals:
              brainstorm: approved
              plan: pending
              review: n/a
            next_action: foo
        """)
        result = extract_approval_map(fm)
        self.assertEqual(result["brainstorm"], "approved")
        self.assertEqual(result["plan"], "pending")
        self.assertEqual(result["review"], "n/a")

    def test_empty_block(self):
        fm = "gate_approvals:\nnext_action: foo"
        result = extract_approval_map(fm)
        self.assertEqual(result, {})

    def test_stops_at_next_top_level_key(self):
        fm = textwrap.dedent("""\
            gate_approvals:
              brainstorm: approved
            current_refs:
              plan: null
        """)
        result = extract_approval_map(fm)
        self.assertEqual(len(result), 1, f"Expected 1 approval, got: {result}")
        self.assertNotIn("plan", result, "current_refs.plan should not leak into approvals")

    def test_quoted_values(self):
        fm = textwrap.dedent("""\
            gate_approvals:
              review: "approved"
        """)
        result = extract_approval_map(fm)
        self.assertEqual(result["review"], "approved")


class TestExtractCurrentRefs(unittest.TestCase):
    """Unit tests for extract_current_refs()."""

    def test_scalar_refs(self):
        fm = textwrap.dedent("""\
            current_refs:
              plan: "docs/plans/my-plan.md"
              spec: null
        """)
        result = extract_current_refs(fm)
        self.assertEqual(result["plan"], "docs/plans/my-plan.md")
        self.assertEqual(result["spec"], "null")

    def test_list_refs(self):
        fm = textwrap.dedent("""\
            current_refs:
              requirements:
                - docs/requirements/PRD.md
                - docs/requirements/SCOPE.md
              plan: null
        """)
        result = extract_current_refs(fm)
        self.assertIsInstance(result["requirements"], list)
        self.assertEqual(
            result["requirements"],
            ["docs/requirements/PRD.md", "docs/requirements/SCOPE.md"],
            "List refs should preserve order and exact paths",
        )

    def test_empty_list_ref(self):
        fm = textwrap.dedent("""\
            current_refs:
              requirements: []
              plan: null
        """)
        result = extract_current_refs(fm)
        self.assertIsInstance(result["requirements"], list)
        self.assertEqual(len(result["requirements"]), 0)


class TestExtractSessionHistory(unittest.TestCase):
    """Unit tests for extract_session_history()."""

    def test_empty_inline(self):
        fm = "session_history: []"
        result = extract_session_history(fm)
        self.assertEqual(result, [])

    def test_single_entry(self):
        fm = textwrap.dedent("""\
            session_history:
              - date: "2026-04-22"
                mode: Dev
                phase: implement
                note: "Did stuff"
        """)
        result = extract_session_history(fm)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["date"], "2026-04-22")
        self.assertEqual(result[0]["mode"], "Dev")

    def test_multiple_entries(self):
        fm = textwrap.dedent("""\
            session_history:
              - date: "2026-04-20"
                note: "First"
              - date: "2026-04-21"
                note: "Second"
        """)
        result = extract_session_history(fm)
        self.assertEqual(len(result), 2, f"Expected 2 entries, got: {result}")

    def test_stops_at_next_key(self):
        fm = textwrap.dedent("""\
            session_history:
              - date: "2026-04-22"
                note: "Entry"
            next_action: foo
        """)
        result = extract_session_history(fm)
        self.assertEqual(len(result), 1, "next_action should not be parsed as session entry")


class TestExtractBlockers(unittest.TestCase):
    """Unit tests for extract_blockers()."""

    def test_empty_inline(self):
        fm = "blockers: []"
        self.assertEqual(extract_blockers(fm), [])

    def test_block_form(self):
        fm = textwrap.dedent("""\
            blockers:
              - "Waiting for API key"
              - "Need design review"
        """)
        result = extract_blockers(fm)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "Waiting for API key")

    def test_inline_single(self):
        fm = 'blockers: "some blocker"'
        result = extract_blockers(fm)
        self.assertEqual(result, ["some blocker"])


class TestPreApproveGateMapping(unittest.TestCase):
    """Unit-test the deterministic gate-prerequisite mapping in isolation.

    Calls check_gate_prerequisites() directly — no subprocess, no git, no B1
    drill, no B2 judge — because this layer is pure gate-state logic (phase
    order, prerequisite approvals, strict-gate enforcement). The evidence-quality
    checks (drill, judge) are layered on by pre_approve_gate and are exercised by
    the integration tests in test_check_status (TestQaDrillGate / TestJudgeGate).
    """

    @staticmethod
    def _approvals(overrides: dict[str, str]) -> dict[str, str]:
        base = {
            "client_ready_for_dev": "approved",
            "brainstorm": "pending",
            "plan": "pending",
            "review": "pending",
            "qa": "pending",
            "security": "pending",
            "deploy": "pending",
            "dev_ready_for_client": "pending",
        }
        base.update(overrides)
        return base

    def _run(self, phase: str, gate: str, approvals: dict) -> tuple[int, str]:
        # ROOT is a valid existing dir; none of the gates exercised here read the
        # filesystem (only client_ready_for_dev does, which is not tested).
        rc = check_gate_prerequisites(
            gate, ROOT, phase, "feature", "L", self._approvals(approvals))
        return rc, ""

    def test_brainstorm_no_prerequisites(self):
        """brainstorm gate has no prerequisites."""
        rc, out = self._run("brainstorm", "brainstorm", {})
        self.assertEqual(rc, 0, f"brainstorm should have no prerequisites: {out}")

    def test_plan_requires_brainstorm(self):
        rc, _ = self._run("plan", "plan", {"brainstorm": "approved"})
        self.assertEqual(rc, 0)

    def test_plan_fails_without_brainstorm(self):
        rc, _ = self._run("plan", "plan", {})
        self.assertNotEqual(rc, 0)

    def test_qa_requires_review(self):
        """qa gate requires brainstorm + plan + review."""
        rc, out = self._run(
            "qa", "qa",
            {"brainstorm": "approved", "plan": "approved", "review": "approved"},
        )
        self.assertEqual(rc, 0, f"qa should pass: {out}")

    def test_qa_fails_without_review(self):
        rc, out = self._run(
            "qa", "qa",
            {"brainstorm": "approved", "plan": "approved"},
        )
        self.assertNotEqual(rc, 0, f"qa should fail without review: {out}")

    def test_security_requires_qa(self):
        rc, out = self._run(
            "security", "security",
            {"brainstorm": "approved", "plan": "approved",
             "review": "approved", "qa": "approved"},
        )
        self.assertEqual(rc, 0, f"security should pass: {out}")

    def test_security_fails_without_qa(self):
        rc, _ = self._run(
            "security", "security",
            {"brainstorm": "approved", "plan": "approved", "review": "approved"},
        )
        self.assertNotEqual(rc, 0)

    def test_ship_gate_handled(self):
        """ship is not a standard approvable gate — verify no crash."""
        rc, _ = self._run(
            "ship", "ship",
            {"brainstorm": "approved", "plan": "approved",
             "review": "approved", "qa": "approved",
             "security": "approved", "deploy": "approved"},
        )
        self.assertIn(rc, [0, 1])


if __name__ == "__main__":
    unittest.main()
