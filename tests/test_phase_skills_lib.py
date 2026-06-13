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


class TestSessionStartInjection(unittest.TestCase):
    """session-start.sh が phase の必読 skill を path-form で注入する。"""

    def _scaffold(self, d: Path, phase: str, skills: list[str],
                  runbook: bool = False) -> Path:
        (d / "docs").mkdir(parents=True)
        (d / "docs" / "STATUS.md").write_text(
            f"---\nframework: aegis\nmode: Dev\nphase: {phase}\n"
            "task_type: feature\ntask_size: M\n"
            "gate_approvals:\n  review: pending\n"
            "current_refs:\n  review: null\n---\n", encoding="utf-8")
        make_skills(d, skills)
        if runbook:
            (d / "docs" / "handover").mkdir(parents=True)
            (d / "docs" / "handover" / "RUNBOOK.md").write_text("# r\n", encoding="utf-8")
        # hook 一式を実体 copy（session-start.sh は dirname 基準で lib を解決）
        import shutil
        shutil.copytree(ROOT / "hooks", d / "hooks")
        (d / "scripts").mkdir()
        (d / "scripts" / "check_status.py").symlink_to(ROOT / "scripts" / "check_status.py")
        return d

    def _run(self, root: Path, extra_env: dict | None = None) -> str:
        env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)}
        if extra_env:
            env.update(extra_env)
        r = subprocess.run(
            ["bash", str(root / "hooks" / "session-start.sh")],
            capture_output=True, text=True, timeout=60,
            env=env)
        return r.stdout

    def test_review_phase_injects_read_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "review",
                                  ["aegis-review-gate", "subagent-dev"])
            out = self._run(root)
            self.assertIn(".claude/skills/aegis-review-gate/SKILL.md", out)

    def test_runbook_triggers_maintenance_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "docs", ["ship-and-docs", "maintenance"],
                                  runbook=True)
            out = self._run(root)
            self.assertIn(".claude/skills/maintenance/SKILL.md", out)

    # --- AEGIS_NUDGE opt-out (P2-a / v1.7.0) -------------------------------
    def test_nudge_default_injects_phase_hint(self):
        # 未設定（既定 on）: implement 期の HINT 説教が文脈に乗る
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "implement", ["tdd", "subagent-dev"])
            out = self._run(root)
            self.assertIn("TDD必須", out, "nudge on: HINT must be present")
            self.assertIn(".claude/skills/tdd/SKILL.md", out)

    def test_nudge_off_drops_hint_keeps_enforcement(self):
        # off: HINT 説教は消えるが、state/skill パス等の enforcement は残る
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "implement", ["tdd", "subagent-dev"])
            out = self._run(root, {"AEGIS_NUDGE": "off"})
            self.assertNotIn("TDD必須", out, "nudge off: HINT sermon must be gone")
            self.assertIn("phase=implement", out, "off must keep phase state")
            self.assertIn("必読skill", out, "off must keep skill boot path")
            self.assertIn(".claude/skills/tdd/SKILL.md", out)

    def test_nudge_non_exact_off_keeps_hint(self):
        # fail-safe: 小文字 off 以外（大文字/末尾空白/別語）は on のまま
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "implement", ["tdd", "subagent-dev"])
            for value in ("OFF", "Off", "off ", "on", "1", "true"):
                with self.subTest(value=value):
                    out = self._run(root, {"AEGIS_NUDGE": value})
                    self.assertIn("TDD必須", out, f"{value!r} must keep HINT (fail-safe)")

    def test_nudge_off_keeps_unknown_phase_warning(self):
        # grill 致命: unknown-phase は診断であり nudge ではない。off でも残す。
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "bogus_phase", ["tdd"])
            out = self._run(root, {"AEGIS_NUDGE": "off"})
            self.assertIn("unknown phase", out, "off must keep misconfig diagnostic")


if __name__ == "__main__":
    unittest.main()
