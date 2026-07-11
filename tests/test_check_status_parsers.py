#!/usr/bin/env python3
"""iter66 Fix⑤: check_status.py パーサの行順 first-match / 先勝ち契約（F-1）。"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_status", ROOT / "scripts" / "check_status.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


class TestExtractScalarFirstMatch(unittest.TestCase):
    def test_quoted_later_does_not_override_first_unquoted(self):
        # F-1 再現: M の後に "S" を追記しても M（bash grep -m1 と同値）
        fm = 'task_size: M\nother: x\ntask_size: "S"'
        self.assertEqual(cs.extract_scalar_value(fm, "task_size"), "M")

    def test_quoted_value_still_normalized(self):
        fm = 'task_size: "M"'
        self.assertEqual(cs.extract_scalar_value(fm, "task_size"), "M")

    def test_duplicate_unquoted_first_wins(self):
        fm = "task_size: M\ntask_size: S"
        self.assertEqual(cs.extract_scalar_value(fm, "task_size"), "M")

    def test_absent_returns_none(self):
        self.assertIsNone(cs.extract_scalar_value("mode: Dev", "task_size"))


class TestApprovalMapFirstWins(unittest.TestCase):
    def test_duplicate_gate_key_first_wins(self):
        fm = ("gate_approvals:\n  review: approved\n  review: pending\n"
              "phase: qa")
        self.assertEqual(cs.extract_approval_map(fm)["review"], "approved")

    def test_normal_map_unchanged(self):
        fm = "gate_approvals:\n  review: approved\n  qa: pending\nphase: qa"
        m = cs.extract_approval_map(fm)
        self.assertEqual(m["review"], "approved")
        self.assertEqual(m["qa"], "pending")


if __name__ == "__main__":
    unittest.main()
