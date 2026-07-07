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
ROUTING = (ROOT / ".claude" / "rules" / "routing.md").read_text(encoding="utf-8")
RG = (ROOT / ".claude" / "skills" / "aegis-review-gate" / "SKILL.md").read_text(encoding="utf-8")
SG = (ROOT / ".claude" / "skills" / "aegis-security-gate" / "SKILL.md").read_text(encoding="utf-8")
SD = (ROOT / ".claude" / "skills" / "subagent-dev" / "SKILL.md").read_text(encoding="utf-8")

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
        self.assertIn("共有可変資源", SD,
                      "並列規則の共有可変資源ルール（M2: テスト DB 衝突）が消えている")
        self.assertIn("同時に起動する1バッチ", SD,
                      "integration 実行タスクの同時1体運用（バッチ定義込み）が消えている")


class TestSubagentContinuationSoT(unittest.TestCase):
    """iter59: routing.md が SendMessage 継続の単一正本（SoT）。iter58 review 2次
    note1 の dangling（機構定義が正本ファイルに無い）を解消。load-bearing 核＝機構名
    SendMessage ＋ 非強制性 harness-enforced を短核 token pin。両トークンとも routing.md
    内で一意ゆえ単一削除で RED（iter58 の presence 保証教訓・重複は不発の反省を反映）。
    長文完全一致は正当な言い換えで false RED を招くため避ける。"""

    def test_continuation_mechanism_present(self):
        self.assertIn("SendMessage", ROUTING,
                      "サブエージェント継続機構（SendMessage）の定義が routing.md から消えている")

    def test_continuation_is_guidance_not_enforced(self):
        # 否定語 "not" を含む句で pin する（review 盲検2次）。単トークン
        # "harness-enforced" だと "not" 脱落による意味反転（guidance→強制の主張）を
        # presence-pin がすり抜ける（false-PASS）。"not harness-enforced" 句で
        # 節削除と "not" 反転の両方を捕捉する。
        self.assertIn("not harness-enforced", ROUTING,
                      "継続が guidance（非ハーネス強制・maxTurns/3-failure で有界）である旨が消えた/反転している")


class TestVerificationDelegationSoT(unittest.TestCase):
    """iter62: 検証系委譲の標準拘束雛形（全体レビュー R1 文言層）。routing.md が単一正本
    （6拘束・6点目 read-only は無条件）、qa-verification／aegis-review-gate／
    aegis-security-gate／subagent-dev の4経路が参照。iter60 事故（security 盲検2次の
    `git checkout docs/*` が親の未コミット gate 簿記を revert）の文言層防御＝
    機械層(patterns.sh)・復旧層(snapshot 退行ガード)は iter61 で封鎖済み。
    短核 token pin（長文完全一致は言い換えで false RED）＋否定句 pin（iter59: 単トークン
    だと NOT 脱落の意味反転を false-PASS）＋一意 count==1（単一削除・重複増殖の両方で RED）。
    正本節の拘束3は SendMessage の語を意図的に使わない（TestSubagentContinuationSoT の
    routing.md 内一意性〔単一削除で RED〕を保全するため。grill-plan 要検討2）。"""

    def test_sot_section_present_and_unique(self):
        self.assertEqual(
            ROUTING.count("## Verification delegation"), 1,
            "検証系委譲拘束の単一正本節が routing.md に1つだけ存在すべき（消失/重複）")

    def test_readonly_negation_phrase_present(self):
        # 否定句で pin（"NOT" 脱落による read-only→書込み許可の意味反転を捕捉）。
        self.assertIn("MUST NOT modify existing files", ROUTING,
                      "6点目 read-only の禁止句（MUST NOT modify existing files）が消えた/反転している")
        # 盲検2次 Minor-1: 6点目には否定が2つある（ファイル変更禁止・git コマンド実行禁止）。
        # 後半の "MUST NOT run" だけを "may run" 等へ反転させると、列挙 token
        # （checkout/...）と前半句を温存したまま iter60 事故そのものの許可文に
        # silent 変異するため、第2否定も独立に pin する。
        self.assertIn("MUST NOT run", ROUTING,
                      "6点目の git コマンド禁止句（MUST NOT run）が消えた/反転している")

    def test_banned_git_commands_enumerated(self):
        # 連結 token で pin（1コマンド脱落でも RED）。iter60 事故は checkout、iter61 機械層は
        # restore/stash も封鎖済み＝文言層は同じ集合＋reset/clean を列挙する。
        self.assertEqual(
            ROUTING.count("checkout/restore/reset/clean/stash"), 1,
            "禁止 git コマンド列挙（checkout/restore/reset/clean/stash）が消えた/欠けた/重複した")

    def test_dirty_tree_protocol_present(self):
        self.assertIn("stop, report, do not touch it", ROUTING,
                      "tree 汚染時の停止・報告・自己復旧禁止プロトコルが消えている")

    def test_readonly_is_unconditional(self):
        self.assertIn("6 is unconditional", ROUTING,
                      "6点目 read-only の無条件適用宣言が消えている（1-5 は itemized 作業向け）")

    def test_consumers_reference_sot(self):
        # 4経路すべてが正本節名を参照する（正本改名・節削除・参照落ちの両側検知）。
        for name, text in (("qa-verification", QA), ("aegis-review-gate", RG),
                           ("aegis-security-gate", SG), ("subagent-dev", SD)):
            with self.subTest(consumer=name):
                self.assertIn("Verification delegation", text,
                              f"{name} から委譲拘束 SoT への参照が消えている")

    def test_consumers_carry_readonly_core(self):
        # 参照だけでなく read-only 核（tree 変更禁止）を委譲文言側にも保持する
        # （iter60: 参照先を読まない subagent には届かない＝核はインライン必須）。
        for name, text in (("qa-verification", QA), ("aegis-review-gate", RG),
                           ("aegis-security-gate", SG), ("subagent-dev", SD)):
            with self.subTest(consumer=name):
                self.assertIn("tree 変更禁止", text,
                              f"{name} の委譲文言から read-only 核（tree 変更禁止）が消えている")

    def test_sendmessage_stays_unique_in_routing(self):
        # docstring の「拘束3は SendMessage の語を使わない」を機械強制する（iter62 review
        # 1次 verify で CONFIRMED のギャップ）。iter59 pin（test_continuation_mechanism_present）
        # は assertIn のため2つ目の SendMessage 追加では緑のまま＝docstring が根拠にする
        # 一意性〔単一削除で RED〕が silent 崩壊する。count==1 で増殖・削除の両方を捕捉。
        self.assertEqual(
            ROUTING.count("SendMessage"), 1,
            "routing.md の SendMessage は Subagent continuation 節の1回のみであるべき"
            "（増殖は iter59 pin の単一削除検知を無効化・消失は継続機構定義の喪失）")


if __name__ == "__main__":
    unittest.main()
