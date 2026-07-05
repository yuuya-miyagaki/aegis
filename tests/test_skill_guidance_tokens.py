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

_spec2 = importlib.util.spec_from_file_location(
    "check_status", ROOT / "scripts" / "check_status.py")
check_status = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(check_status)

# Client フェーズの産出物集合は check_status.CLIENT_GATE_ARTIFACTS（gate 検査の
# 単一正本）＋ SPEC_DELTA_ARTIFACT（反復2回目以降の CHANGES.md）由来。
# prefix ベースの推測は docs/handover/ 配下の Dev 側 ship 産出物
# （MANUAL.md 等）を誤って要求する（初版 grill で検出）。
CLIENT_ARTIFACTS = [p for p, _ in check_status.CLIENT_GATE_ARTIFACTS] + [
    check_status.SPEC_DELTA_ARTIFACT[0]]


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
        for artifact in CLIENT_ARTIFACTS:
            template = atm.ARTIFACT_TO_TEMPLATE[artifact]
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, CW, f"{artifact} が client-workflow に未記載")
                self.assertIn(template, CW, f"{template} が client-workflow に未記載")


class TestQaBrowserDelegation(unittest.TestCase):
    """iter58: qa-browser 標準委譲プロンプトの load-bearing トークン pin。
    完了拘束・再開プロトコルの核心命令が silent 消失したら FAIL（決定論トリップワイヤ）。
    長文完全一致は正当な言い換えで false RED を招くため、短核トークンで pin する
    （grill-plan 要検討1）。進捗形式 `[n/N done]`・エビデンス brace は軟らかい要素＝pin しない。"""

    def test_granularity_guidance_present(self):
        self.assertIn("5 項目程度", QA,
                      "qa-browser 委譲粒度ガイド（5 項目程度）が消えている")
        self.assertIn("19 項目", QA,
                      "委譲粒度の根拠（ドッグフード実測 19 項目で停止 3 回）が消えている")

    def test_completion_constraint_present(self):
        # 完全性の核＋報告抑制の核を短核で pin（長文完全一致は言い換えで false RED）。
        self.assertIn("全項目のエビデンス", QA,
                      "完了拘束の完全性（全項目のエビデンス充足）が消えている")
        self.assertIn("最終報告を出さない", QA,
                      "完了拘束の報告抑制（最終報告を出さない）が消えている")

    def test_resume_protocol_present(self):
        self.assertIn("SendMessage", QA,
                      "再開プロトコル（SendMessage で同一エージェント継続）が消えている")


class TestQaRefIsClaimsReport(unittest.TestCase):
    """iter56 ②: qa ref の正本＝claims 付き QA レポート（judge は ref 先の claims
    しか読まない）。test-strength.md を ref にする旧規約は claims を構造的に置けず
    毎回 🟡 ack（M2 実測）＝skill×judge の契約矛盾。"""

    def test_qa_ref_points_to_claims_report(self):
        self.assertIn("claims 付き QA レポート", QA,
                      "qa ref の正本規定（claims 付き QA レポート）が消えている")

    def test_old_test_strength_ref_rule_gone(self):
        # grill 致命3: 旧文言は途中に改行が入るため exact NotIn はすり抜ける。
        # 空白正規化してから assert する。
        normalized = " ".join(QA.split())
        self.assertNotIn(
            "`current_refs.qa` を `docs/qa-reports/test-strength.md` にする", normalized,
            "judge が claims を読めない旧規約（test-strength.md を ref）が残っている")
        self.assertNotIn(
            "`docs/qa-reports/test-strength.md` にすること", normalized,
            "skip 経路の旧規約が残っている")


class TestSharedMutableResourceRule(unittest.TestCase):
    """iter56 ④: 並列規則の共有可変資源ルール（M2 実測: 並行 integration テストが
    同一テスト DB を TRUNCATE し合い偽 fail）。"""

    def test_shared_resource_rule_present(self):
        sd = (ROOT / ".claude" / "skills" / "subagent-dev" / "SKILL.md"
              ).read_text(encoding="utf-8")
        self.assertIn("共有可変資源", sd,
                      "並列規則の共有可変資源ルール（M2: テスト DB 衝突）が消えている")
        self.assertIn("同時に起動する1バッチ", sd,
                      "integration 実行タスクの同時1体運用（バッチ定義込み）が消えている")


if __name__ == "__main__":
    unittest.main()
