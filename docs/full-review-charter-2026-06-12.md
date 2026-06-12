# 全力レビュー charter（第5回・2026-06-12、対象 v1.6.0）

## 目的

v1.6.0（iteration 21 締め・HEAD `437b857`）の aegis を、過去 4 回のレビューと**重複しない角度**から全面精査し、次の改善サイクルの入力となる所見を重大度付きで得る。

## 過去レビューとの差別化（重複禁止リスト）

| 回 | 日付 | 軸 | 出典 |
|----|------|-----|------|
| 1 | 2026-06-06 | 機械契約→哲学の 2 層監査＋最新フレーム web 調査 | docs/audit-report-2026-06-06.md |
| 2 | 2026-06-07 | 機能整合性（install 経路の死角） | docs/functional-integrity-audit-report-2026-06-07.md |
| 3 | 2026-06-10 | 哲学×Web比較×欠陥監査の 3 軸 | docs/evolution-review-2026-06-10.md |
| 4 | 2026-06-11〜12 | 行動レビュー（実運転検証） | docs/behavioral-review-report-2026-06-12.md |

上記で解決済み・受容済みの事項（v160-security.md 残余 9 件、v152-security.md 受容残余、各レビューの resolved 項目）の再報告は**ノイズとして禁止**。新規所見のみ。

## 今回の 5 軸

### 軸A: 敵対的バイパス監査（red-team）
deny/block 系 hook・evidence/judge 系・契約検査の**突破を能動的に試みる**。green 偽装、ゲート迂回、fail-open 化、環境変数・PATH・quoting・symlink・CLAUDE_PROJECT_DIR 操作。PoC 付き所見を最優先。

### 軸B: 保守性・コード健全性（3 年レンズ）
複雑性ホットスポット、bash↔python の二重実装、テストスイートの持続可能性（508 tests・実行 130s 超）、fixture 反復、ミラー byte-identical 機構の維持コスト、死蔵コード、単一所有原則の遵守実態。

### 軸C: 北極星 UX（非エンジニア体験）
北極星「非エンジニアが上流〜保守まで非スラップを作れる」への適合。README/setup の導入体験、エラーメッセージ・judge card の平易さ、Client ワークフローの摩擦、操作マニュアル/UAT/保守スキルの実用性、日英混在の一貫性。

### 軸D: アーキテクチャ整合・ドキュメント↔実装 drift
architecture-overview.md の主張と実装の乖離、3 層原則（保証=決定論/手順=モデル委譲/揮発値=隔離）の遵守実態、契約表面積の肥大（ALL_CHECKS 等）、state-machine の網羅性、版履歴の正確性。

### 軸E: エコシステム現行性（Claude Code 仕様追従）
hook 出力スキーマ（emit.sh の verified 2026-06-05 注記）、PostToolUse additionalContext・SessionStart 注入・skill frontmatter（disable-model-invocation / user-invocable）・matcher 構文・settings 登録形式が**現行の公式仕様**と一致しているかを公式ドキュメントで突合。

## 方法

- 軸ごとに独立サブエージェント（互いの所見を見ない）。軸E は公式ドキュメント参照可能なエージェント
- 読み取り専用（repo 変更禁止。/tmp への scaffold 実行は可）
- 所見は `file:line` ＋根拠＋修正方針、重大度 🔴（防御破綻・北極星阻害）/ 🟡（要修正）/ 🟢（任意）
- **監査と再設計の分離**: 本レビューは所見の提示まで。修正の実施・優先順位の確定は別途ユーザー判断

## 成果物

- 統合レポート: docs/full-review-2026-06-12.md（軸別所見＋横断テーマ＋優先順位付き提案バックログ）
