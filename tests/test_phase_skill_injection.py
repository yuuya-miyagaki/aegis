#!/usr/bin/env python3
"""P1-A: 正当な phase 遷移時、post-status-audit.sh が新 phase の必読 skill を
additionalContext で注入する（セッション途中の遷移は SessionStart 注入が届かない穴）。"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_TMPL = """---
framework: aegis
mode: Dev
phase: {phase}
task_type: feature
task_size: M
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  plan: null
---
"""

SNAPSHOT = """gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
phase: brainstorm
mode: Dev
"""


class TestPhaseTransitionInjection(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        (d / "docs").mkdir()
        (d / "docs" / "STATUS.md").write_text(
            STATUS_TMPL.format(phase="plan"), encoding="utf-8")
        (d / ".claude").mkdir()
        (d / ".claude" / ".gate-snapshot").write_text(SNAPSHOT, encoding="utf-8")
        sk = d / ".claude" / "skills" / "subagent-dev"
        sk.mkdir(parents=True)
        (sk / "SKILL.md").write_text("---\nname: subagent-dev\n---\n", encoding="utf-8")
        shutil.copytree(ROOT / "hooks", d / "hooks")
        (d / "scripts").mkdir()
        (d / "scripts" / "check_status.py").symlink_to(ROOT / "scripts" / "check_status.py")
        return d

    def _run(self, root: Path) -> dict:
        stdin = json.dumps({"tool_name": "Edit",
                            "tool_input": {"file_path": str(root / "docs" / "STATUS.md")}})
        r = subprocess.run(
            ["bash", str(root / "hooks" / "post-status-audit.sh")],
            input=stdin, capture_output=True, text=True, timeout=60,
            env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_legit_transition_injects_new_phase_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp))
            out = self._run(root)  # brainstorm -> plan（brainstorm approved 済 = 正当）
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn(".claude/skills/subagent-dev/SKILL.md", ctx)

    def test_no_transition_emits_allow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp))
            (root / ".claude" / ".gate-snapshot").write_text(
                SNAPSHOT.replace("phase: brainstorm", "phase: plan"), encoding="utf-8")
            out = self._run(root)
            self.assertEqual(out, {})  # 遷移なし → 素の allow


if __name__ == "__main__":
    unittest.main()
