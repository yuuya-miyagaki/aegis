#!/usr/bin/env python3
"""iter55 P1/P4: skill 本文の load-bearing 文言の drift ガード（iter53 の
test_destructive_warning_language.py と同型の token pin）＋テンプレ対応表 parity。

ドッグフード ゲート戦闘3: client-workflow の「作成したら translation ref を設定」指示が
stale-ref 検査（pending gate + ref = FAIL）と正面衝突。正しい運用（承認の直前に設定→
承認を連続実行）を skill 本文に明文化し、旧文言の再発を token で封鎖する。
テンプレ対応表は scripts/_artifact_template_map.py（single owner）との parity で縛る。
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CW = (ROOT / ".claude" / "skills" / "client-workflow" / "SKILL.md").read_text(encoding="utf-8")
QA = (ROOT / ".claude" / "skills" / "qa-verification" / "SKILL.md").read_text(encoding="utf-8")

_spec = importlib.util.spec_from_file_location(
    "atm", ROOT / "scripts" / "_artifact_template_map.py")
atm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atm)

# Client フェーズで client-workflow が案内すべき産出物（TO-CLIENT は Dev 側なので除外）
CLIENT_PREFIXES = ("docs/requirements/", "docs/handover/", "docs/translation/")
CLIENT_EXCLUDE = {"docs/handover/TO-CLIENT.md"}


class TestTranslationRefTiming(unittest.TestCase):
    def test_timing_token_present(self):
        self.assertIn("承認の直前", CW,
                      "translation ref のタイミング規定（承認の直前）が消えている")
        self.assertIn("stale-ref", CW,
                      "stale-ref 違反への言及（なぜ直前なのか）が消えている")

    def test_old_contradicting_wording_gone(self):
        self.assertNotIn(
            "作成したら、`current_refs.translation` に設定する", CW,
            "hook 契約と矛盾する旧文言（作成時に ref 設定）が残っている")


class TestTemplateTableParity(unittest.TestCase):
    def test_client_artifacts_and_templates_listed(self):
        for artifact, template in atm.ARTIFACT_TO_TEMPLATE.items():
            if not artifact.startswith(CLIENT_PREFIXES) or artifact in CLIENT_EXCLUDE:
                continue
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, CW, f"{artifact} が client-workflow に未記載")
                self.assertIn(template, CW, f"{template} が client-workflow に未記載")


class TestQaBrowserDelegationGranularity(unittest.TestCase):
    def test_granularity_guidance_present(self):
        self.assertIn("5 項目程度", QA,
                      "qa-browser 委譲粒度ガイド（5 項目程度）が消えている")
        self.assertIn("19 項目", QA,
                      "委譲粒度の根拠（ドッグフード実測 19 項目で停止 3 回）が消えている")


if __name__ == "__main__":
    unittest.main()
