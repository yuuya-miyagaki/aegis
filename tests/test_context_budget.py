#!/usr/bin/env python3
"""context_budget の単体テスト。"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import context_budget  # noqa: E402


def _mk(root: Path, rel: str, words: int) -> Path:
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(" ".join(["w"] * words) + "\n", encoding="utf-8")
    return p


def _registry(root: Path, data: dict) -> None:
    (Path(root) / "scripts").mkdir(parents=True, exist_ok=True)
    (Path(root) / "scripts" / "context-budgets.json").write_text(
        json.dumps(data), encoding="utf-8")


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_over_budget_fails(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 100)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(
            any("foo/SKILL.md" in f and "100 words > 50" in f for f in failures),
            failures)

    def test_within_budget_passes(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 40)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        self.assertEqual(context_budget.check(self.tmp), [])

    def test_default_guards_unlisted_skill(self):
        _mk(self.tmp, ".claude/skills/big/SKILL.md", 2000)
        _registry(self.tmp, {"default_skill_words": 1500, "budgets": {}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("big/SKILL.md" in f for f in failures), failures)

    def test_rule_default_guards(self):
        _mk(self.tmp, ".claude/rules/r.md", 2000)
        _registry(self.tmp, {"default_rule_words": 500, "budgets": {}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("rules/r.md" in f for f in failures), failures)


class TestRatchet(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-r-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _read(self):
        return json.loads(
            (self.tmp / "scripts" / "context-budgets.json").read_text())

    def test_tighten_lowers_to_current(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 30)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 100}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/foo/SKILL.md"], 30)

    def test_tighten_never_raises(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 80)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/foo/SKILL.md"], 50)

    def test_tighten_adds_new_file_at_current(self):
        _mk(self.tmp, ".claude/skills/new/SKILL.md", 42)
        _registry(self.tmp, {"budgets": {}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/new/SKILL.md"], 42)

    def test_seed_uses_headroom_and_skips_existing(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 100)
        _mk(self.tmp, ".claude/skills/bar/SKILL.md", 50)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 999}})
        context_budget.seed(self.tmp, headroom=1.1)
        data = self._read()
        self.assertEqual(data["budgets"][".claude/skills/foo/SKILL.md"], 999)
        self.assertEqual(data["budgets"][".claude/skills/bar/SKILL.md"], 55)
        self.assertIn("default_skill_words", data)


if __name__ == "__main__":
    unittest.main()
