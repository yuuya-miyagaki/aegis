"""skill-pressure-drill 拡張の形式検査（層2・決定論・エージェント非実行）。"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extensions" / "skill-pressure-drill"
SCENARIOS = EXT / "scenarios"
SKILLS = ROOT / ".claude" / "skills"

REQUIRED_SECTIONS = ("## adversarial_prompt", "## expected_adherence", "## temptation")


def _scenarios():
    return sorted(SCENARIOS.glob("*.md"))


class TestSkillDrillFormat(unittest.TestCase):
    def test_extension_files_exist(self):
        self.assertTrue((EXT / "README.md").is_file())
        self.assertTrue((EXT / "WORKFLOW.md").is_file())
        self.assertTrue((EXT / "REPORT.template.md").is_file())
        self.assertTrue(SCENARIOS.is_dir())

    def test_at_least_one_scenario(self):
        self.assertTrue(_scenarios(), "no scenarios found")

    def test_scenarios_have_frontmatter_target_skill_and_sections(self):
        for path in _scenarios():
            text = path.read_text(encoding="utf-8")
            m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
            self.assertIsNotNone(m, f"{path.name}: missing frontmatter")
            tm = re.search(r"^target_skill:\s*(\S+)", m.group(1), re.MULTILINE)
            self.assertIsNotNone(tm, f"{path.name}: missing target_skill")
            target = tm.group(1).strip()
            self.assertTrue(
                (SKILLS / target / "SKILL.md").is_file(),
                f"{path.name}: target_skill '{target}' is not an existing skill",
            )
            for sec in REQUIRED_SECTIONS:
                self.assertIn(sec, text, f"{path.name}: missing section {sec}")

    def test_report_template_has_rubric_fields(self):
        text = (EXT / "REPORT.template.md").read_text(encoding="utf-8")
        for marker in ("対象 skill", "判定: PASS / FAIL", "観測した挙動", "rubric 照合"):
            self.assertIn(marker, text, f"REPORT.template.md missing {marker}")

    def test_workflow_references_template_and_report_dir(self):
        text = (EXT / "WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("REPORT.template.md", text)
        self.assertIn("docs/qa-reports/", text)


if __name__ == "__main__":
    unittest.main()
