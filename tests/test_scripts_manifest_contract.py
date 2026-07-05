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

    def test_crlf_line_ending_fails(self):
        """grill-code 🟢: CRLF 混入は bash 側で class 不一致＝silent deny になるため、
        contract が \\r を whitespace として即 FAIL することを pin（fail-visible）。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\r\n")
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

    def test_ghost_permission_entry_fails(self):
        """盲検2次(review) 逆方向の隙間: scripts/ にも manifest にも無い permission
        allow 行（幽霊エントリ）が腐っても沈黙していた。scripts/ を指す全 allow 行は
        manifest の class=allow に対応することを縛る。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(
                Path(t), "scripts/good.py\tallow\n",
                template={"permissions": {"allow": [
                    "Bash(python3 scripts/good.py:*)",
                    "Bash(python3 scripts/ghost.py:*)"]}})
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("ghost.py" in f for f in fails), fails)

    def test_non_script_permission_entries_ignored(self):
        """scripts/ を指さない allow 行（pytest・git status 等）は逆方向検査の対象外。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(
                Path(t), "scripts/good.py\tallow\n",
                template={"permissions": {"allow": [
                    "Bash(python3 scripts/good.py:*)",
                    "Bash(python3 -m pytest:*)",
                    "Bash(git status:*)"]}})
            self.assertEqual(cfc.check_scripts_manifest(root), [])


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

    def test_agent_ref_to_framework_only_fails(self):
        """盲検2次(review) 方向3の死角: .claude/agents/*.md も配布され実行指示を
        書き得る。framework-only スクリプトを指示していれば hook が deny する。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/tool.py\tframework-only\n",
                           scripts=("good.py", "tool.py"))
            ag = root / ".claude" / "agents"
            ag.mkdir(parents=True)
            (ag / "demo.md").write_text(
                "Run `python3 scripts/tool.py` in your workflow.\n", encoding="utf-8")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("tool.py" in f for f in fails), fails)

    def test_direction4_runnable_scripts_distributed_in_full_profile(self):
        """方向4 (iter56 ⑥): manifest の実行可クラス（allow|ask）は full プロファイル
        が配布する。M2 実測: retro_report.py が hook ALLOW なのに install 先に無く
        /retro が手動フォールバック化（F6=install 経路の死角の再発形）。"""
        manifest = cfc.load_scripts_manifest(ROOT)
        full = json.loads(
            (ROOT / "templates" / "profiles" / "full.json").read_text(encoding="utf-8"))
        distributed = set(full["required"]) | set(full["recommended"])
        unshipped = set(full.get("intentional_unshipped", {}))
        runnable = {e for e, c in manifest.items() if c in ("allow", "ask")}
        self.assertLessEqual(runnable - unshipped, distributed,
                             sorted(runnable - unshipped - distributed))

    def test_direction4_detects_missing_distribution(self):
        """合成違反: allow スクリプトが full.json に無ければ FAIL する。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n")
            prof = root / "templates" / "profiles"
            prof.mkdir(parents=True)
            (prof / "full.json").write_text(
                json.dumps({"required": [], "recommended": []}), encoding="utf-8")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("full profile" in f for f in fails), fails)

    def test_direction4_skipped_when_full_profile_absent(self):
        """full.json の無い合成 root（既存テスト群）では方向4は発火しない。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n")
            self.assertEqual(cfc.check_scripts_manifest(root), [])

    def test_direction4_intentional_unshipped_exempts_with_reason(self):
        """意図的非同梱は full.json の intentional_unshipped（理由必須）で明示すれば
        FAIL しない（例: check_framework_contract.py = maintainer 専用）。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n")
            prof = root / "templates" / "profiles"
            prof.mkdir(parents=True)
            (prof / "full.json").write_text(json.dumps({
                "required": [], "recommended": [],
                "intentional_unshipped": {"scripts/good.py": "maintainer 専用"},
            }), encoding="utf-8")
            self.assertEqual(cfc.check_scripts_manifest(root), [])

    def test_direction4_unshipped_empty_reason_fails(self):
        """理由なしの除外＝サイレント許容は禁止。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n")
            prof = root / "templates" / "profiles"
            prof.mkdir(parents=True)
            (prof / "full.json").write_text(json.dumps({
                "required": [], "recommended": [],
                "intentional_unshipped": {"scripts/good.py": ""},
            }), encoding="utf-8")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("non-empty reason" in f for f in fails), fails)

    def test_direction4_unshipped_stale_entry_fails(self):
        """実際は同梱済みのエントリが intentional_unshipped に残っていたら rot＝FAIL。"""
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n")
            prof = root / "templates" / "profiles"
            prof.mkdir(parents=True)
            (prof / "full.json").write_text(json.dumps({
                "required": [], "recommended": ["scripts/good.py"],
                "intentional_unshipped": {"scripts/good.py": "理由"},
            }), encoding="utf-8")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("stale" in f for f in fails), fails)

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
