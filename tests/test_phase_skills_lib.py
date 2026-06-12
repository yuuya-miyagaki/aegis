#!/usr/bin/env python3
"""P1-A (OBS-004/020): hooks/lib/phase-skills.sh — phase→必読 skill マップの単一所有。

全 skill は disable-model-invocation:true のため、Read 指示の注入が唯一の起動経路。
このマップの欠落 = その skill は到達不能（行動レビューで実証）。
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "phase-skills.sh"


def paths_for(root: Path, phase: str, task_type: str = "feature") -> list[str]:
    script = (f'source "{LIB}"\n'
              f'aegis_phase_skill_paths "{root}" "{phase}" "{task_type}"\n')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError(f"lib failed: {r.stderr}")
    return [l for l in r.stdout.splitlines() if l]


def make_skills(root: Path, names: list[str]) -> None:
    for n in names:
        d = root / ".claude" / "skills" / n
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"---\nname: {n}\n---\n", encoding="utf-8")


class TestPhaseSkillPaths(unittest.TestCase):
    def test_review_includes_review_gate_skill(self):
        # OBS-020 再発防止: review フェーズで aegis-review-gate が必読に入る
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_skills(root, ["aegis-review-gate", "subagent-dev"])
            got = paths_for(root, "review")
            self.assertIn(".claude/skills/aegis-review-gate/SKILL.md", got)
            self.assertIn(".claude/skills/subagent-dev/SKILL.md", got)

    def test_ship_includes_back_half_skills(self):
        # 北極星後半 (OBS-031/032/034/035): ship/docs で配布系 skill が必読に入る
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            names = ["ship-and-docs", "user-manual", "uat", "maintenance", "docs-sync"]
            make_skills(root, names)
            got = paths_for(root, "ship")
            for n in names:
                self.assertIn(f".claude/skills/{n}/SKILL.md", got)

    def test_bugfix_brainstorm_routes_to_bug_diagnosis(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_skills(root, ["bug-diagnosis", "tdd", "aegis-brainstorm"])
            got = paths_for(root, "brainstorm", "bugfix")
            self.assertIn(".claude/skills/bug-diagnosis/SKILL.md", got)
            self.assertNotIn(".claude/skills/aegis-brainstorm/SKILL.md", got)

    def test_existence_filter_for_partial_installs(self):
        # minimal/standard install: 配布されていない skill の Read 指示を出さない
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_skills(root, ["subagent-dev"])  # tdd は未配布
            got = paths_for(root, "implement")
            self.assertEqual(got, [".claude/skills/subagent-dev/SKILL.md"])

    def test_unknown_phase_emits_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(paths_for(Path(d), "nonsense"), [])


if __name__ == "__main__":
    unittest.main()
