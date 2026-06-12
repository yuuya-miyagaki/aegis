"""skill 到達性 drift チェックのユニットテスト（P1-A 再発封鎖）。"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_reference_drift.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_reference_drift", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


drift = _load()


def _make_skill(root: Path, name: str, body: str = "", user_invocable: bool = False) -> None:
    d = root / ".claude" / "skills" / name
    d.mkdir(parents=True)
    fm = ["---", f"name: {name}", "description: test skill"]
    if user_invocable:
        fm.append("user-invocable: true")
    fm.append("disable-model-invocation: true")
    fm.append("---")
    (d / "SKILL.md").write_text("\n".join(fm) + "\n" + body + "\n", encoding="utf-8")


def _make_phase_map(root: Path, names: str) -> None:
    lib = root / "hooks" / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "phase-skills.sh").write_text(
        '#!/bin/bash\ncase "$phase" in\n  implement) names="%s" ;;\nesac\n' % names,
        encoding="utf-8",
    )


class TestSkillReachability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_unreachable_skill_fails(self):
        _make_skill(self.root, "orphan")
        failures, warnings = drift.check_skill_reachability(self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("orphan", failures[0])
        self.assertIn("no boot path", failures[0])
        self.assertEqual(warnings, [])

    def test_phase_map_skill_is_root(self):
        _make_skill(self.root, "tdd")
        _make_phase_map(self.root, "tdd")
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_user_invocable_skill_is_root(self):
        _make_skill(self.root, "session-recovery", user_invocable=True)
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_control_file_path_ref_is_root(self):
        _make_skill(self.root, "deploy")
        cmd = self.root / ".claude" / "commands"
        cmd.mkdir(parents=True)
        (cmd / "ship.md").write_text(
            ".claude/skills/deploy/SKILL.md を Read して従う\n", encoding="utf-8"
        )
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_transitive_skill_edge_reaches(self):
        _make_skill(
            self.root, "parent",
            body="次に .claude/skills/child/SKILL.md を Read する",
            user_invocable=True,
        )
        _make_skill(self.root, "child")
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_edge_from_unreachable_skill_does_not_rescue(self):
        _make_skill(self.root, "island-a", body=".claude/skills/island-b/SKILL.md")
        _make_skill(self.root, "island-b")
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(len(failures), 2)

    def test_existence_manifest_does_not_rescue(self):
        # check_framework_contract.py は全 skill の存在リスト（メタデータ）を持つ。
        # boot 指示ではないので到達性の root にしてはならない（恒久 CLEAN 化＝空洞化の防止）。
        _make_skill(self.root, "orphan")
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "check_framework_contract.py").write_text(
            'REQUIRED = [".claude/skills/orphan/SKILL.md"]\n', encoding="utf-8"
        )
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("orphan", failures[0])


if __name__ == "__main__":
    unittest.main()
