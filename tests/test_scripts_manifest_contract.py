#!/usr/bin/env python3
"""iter55 P0: scripts-manifest.tsv の 3 方向 drift 検査（check_framework_contract.py）。

方向1: manifest 健全性（実在・enum・重複・厳格パース・scripts/ 全 *.py|*.sh の完全分類）
方向2: class=allow ⟺ templates/hooks.template.json permissions（双方向。ask 等の混入は
       人間承認トリップワイヤの誤解除＝FAIL）
方向3: 配布される skill/command/rules が参照する scripts/*.{py,sh} は class allow|ask
       （skill が指示するスクリプトを hook が deny する事故クラスの構造的封鎖）
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_framework_contract as cfc  # noqa: E402

TEMPLATE_JSON = {
    "permissions": {"allow": ["Bash(python3 scripts/good.py:*)"]},
    "hooks": {},
}


def _mkroot(tmp: Path, manifest: str, template: dict | None = None,
            scripts: tuple = ("good.py",), skill: str | None = None) -> Path:
    (tmp / "hooks" / "lib").mkdir(parents=True)
    (tmp / "hooks" / "lib" / "scripts-manifest.tsv").write_text(manifest, encoding="utf-8")
    (tmp / "scripts").mkdir()
    for name in scripts:
        (tmp / "scripts" / name).write_text("# stub\n", encoding="utf-8")
    (tmp / "templates").mkdir()
    (tmp / "templates" / "hooks.template.json").write_text(
        json.dumps(template if template is not None else TEMPLATE_JSON), encoding="utf-8")
    if skill is not None:
        d = tmp / ".claude" / "skills" / "demo"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(skill, encoding="utf-8")
    return tmp


class TestManifestHealth(unittest.TestCase):
    def test_real_repo_passes(self):
        self.assertEqual(cfc.check_scripts_manifest(), [],
                         "real repo must pass the 3-way drift check")

    def test_unclassified_script_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n",
                           scripts=("good.py", "new_tool.py"))
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("new_tool.py" in f for f in fails), fails)

    def test_row_for_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/ghost.py\tallow\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("ghost.py" in f for f in fails), fails)

    def test_unknown_class_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tmaybe\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("maybe" in f for f in fails), fails)

    def test_duplicate_row_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\nscripts/good.py\task\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("duplicate" in f.lower() for f in fails), fails)

    def test_whitespace_in_field_fails(self):
        """grill 致命2: bash reader は完全一致＝空白入り行は silent deny になる。
        contract は寛容に strip して通してはならない（PASS/deny の非対称ドリフト）。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow \n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("whitespace" in f.lower() for f in fails), fails)


class TestPermissionsBidirectional(unittest.TestCase):
    def test_allow_missing_from_permissions_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n",
                           template={"permissions": {"allow": []}})
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("good.py" in f for f in fails), fails)

    def test_non_allow_present_in_permissions_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(
                Path(t), "scripts/good.py\task\n",
                template={"permissions": {"allow": ["Bash(python3 scripts/good.py:*)"]}})
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("good.py" in f for f in fails), fails)


class TestSkillReferences(unittest.TestCase):
    def test_skill_ref_to_framework_only_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/tool.py\tframework-only\n",
                           scripts=("good.py", "tool.py"),
                           skill="Run `python3 scripts/tool.py` to do X.\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("tool.py" in f for f in fails), fails)

    def test_skill_ref_to_unknown_script_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n",
                           skill="Run `python3 scripts/ghost.py`.\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("ghost.py" in f for f in fails), fails)

    def test_skill_ref_to_ask_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/gate.sh\task\n",
                           scripts=("good.py", "gate.sh"),
                           skill="Run `bash scripts/gate.sh review approve`.\n")
            self.assertEqual(cfc.check_scripts_manifest(root), [])

    def test_overridden_local_command_not_scanned(self):
        """grill 致命1: templates/commands/ に同名 override がある .claude/commands/ の
        framework-repo ローカル変種（framework-only スクリプト参照可）は走査対象外。
        配布されるのは templates 版（setup.sh install resolver と同じ規則）。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/dev.py\tframework-only\n",
                           scripts=("good.py", "dev.py"))
            cmd_dir = root / ".claude" / "commands"
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "validate.md").write_text(
                "Run `python3 scripts/dev.py` (framework-local).\n", encoding="utf-8")
            tpl_dir = root / "templates" / "commands"
            tpl_dir.mkdir(parents=True)
            (tpl_dir / "validate.md").write_text(
                "Run `python3 scripts/good.py`.\n", encoding="utf-8")
            self.assertEqual(cfc.check_scripts_manifest(root), [],
                             "配布されない framework-local 変種の参照で FAIL してはならない")


if __name__ == "__main__":
    unittest.main()
