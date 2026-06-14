"""skill behavior contract（層1）の RED-GREEN 単体。"""
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


def _make_skill(root: Path, name: str, body: str) -> None:
    d = root / ".claude" / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    fm = ["---", f"name: {name}", "description: test skill",
          "disable-model-invocation: true", "---"]
    (d / "SKILL.md").write_text("\n".join(fm) + "\n" + body + "\n", encoding="utf-8")


def _make_manifest_marker(root: Path) -> None:
    # 注意: このファイルの「中身」は使われない。framework-root ガード
    # （scripts/skill_behavior_manifest.py の存在判定）を通すための存在マーカー専用。
    # check が実際に読むトークンは import 済みの実 SKILL_INVARIANTS（実 manifest）。
    # マーカーの中身を編集してもテスト挙動は変わらない。
    s = root / "scripts"
    s.mkdir(parents=True, exist_ok=True)
    (s / "skill_behavior_manifest.py").write_text("SKILL_INVARIANTS = {}\n", encoding="utf-8")


class TestSkillBehaviorContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_manifest_well_formed(self):
        self.assertIsInstance(drift.SKILL_INVARIANTS, dict)
        self.assertTrue(drift.SKILL_INVARIANTS)
        for name, tokens in drift.SKILL_INVARIANTS.items():
            self.assertIsInstance(name, str)
            self.assertTrue(tokens, f"{name}: tokens must be non-empty")
            for tok in tokens:
                self.assertIsInstance(tok, str)
                self.assertTrue(tok.strip(), f"{name}: blank token")

    def test_all_tokens_present_passes(self):
        _make_manifest_marker(self.root)
        for name, tokens in drift.SKILL_INVARIANTS.items():
            _make_skill(self.root, name, body="\n".join(tokens))
        failures, warnings = drift.check_skill_behavior_contract(self.root)
        self.assertEqual(failures, [], failures)
        self.assertEqual(warnings, [])

    def test_missing_token_fails(self):
        _make_manifest_marker(self.root)
        target, tokens = next(iter(drift.SKILL_INVARIANTS.items()))
        for name, toks in drift.SKILL_INVARIANTS.items():
            body = "\n".join(toks[1:]) if name == target else "\n".join(toks)
            _make_skill(self.root, name, body=body)
        failures, _ = drift.check_skill_behavior_contract(self.root)
        self.assertTrue(
            any(target in f and tokens[0] in f for f in failures),
            f"expected missing-token failure for {target}/{tokens[0]!r}, got {failures}",
        )

    def test_guard_inert_without_manifest(self):
        # tmp root に scripts/skill_behavior_manifest.py が無い＝installed 相当＝inert
        for name in drift.SKILL_INVARIANTS:
            _make_skill(self.root, name, body="")  # トークン皆無でも
        failures, _ = drift.check_skill_behavior_contract(self.root)
        self.assertEqual(failures, [])

    def test_manifest_skill_without_skillmd_fails(self):
        _make_manifest_marker(self.root)  # skills は作らない
        failures, _ = drift.check_skill_behavior_contract(self.root)
        self.assertEqual(len(failures), len(drift.SKILL_INVARIANTS))
        self.assertTrue(all("no SKILL.md" in f for f in failures), failures)

    def test_real_repo_skills_satisfy_contract(self):
        repo_root = SCRIPT.resolve().parent.parent
        failures, warnings = drift.check_skill_behavior_contract(repo_root)
        self.assertEqual(failures, [], failures)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
