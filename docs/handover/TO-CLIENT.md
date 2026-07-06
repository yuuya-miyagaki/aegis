# 納品サマリー — iteration 59（v1.20.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の guidance 改修。「client」＝フレームワーク保守者
> （次に aegis を使う自分自身）。外部クライアントへの製品納品ではない。

## 納品サマリー

- リリース / ビルド: **v1.19.0 → v1.20.0（MINOR）**
- 日付: 2026-07-06
- 担当者: Dev（Aegis 自己改修イテレーション）
- 操作マニュアル: **生成せず** — エンドユーザー製品でなくフレームワーク（利用者＝保守者自身）。
- 運用 RUNBOOK: **生成せず** — 運用者なし（CI 相当は contract/drift/context-budget の機械検査）。
- UAT 結果: **生成せず** — `docs/requirements/ACCEPTANCE.md` なし（受入基準を要する外部案件でない）。

## 実装範囲

- **完了**: サブエージェント継続機構 `SendMessage` の **SoT（単一正本）定義**（iter58 review 2次 note1 の dangling を解消）。
  - `.claude/rules/routing.md` に「## Subagent continuation」節を追加＝継続機構の単一正本:
    「停止したサブエージェントを新規再委譲でなく **SendMessage** で同一コンテキスト再開する」／
    「**guidance であり harness 強制ではない**・`maxTurns` と 3-failure ルールで有界」。
  - `principle` を2文→1文に圧縮（意味不変・"else" が旧 "when in doubt" を論理包摂）。
  - `tests/test_skill_guidance_tokens.py` に継続定義の token pin（`SendMessage`＋`not harness-enforced` 句）を追加＝
    継続定義の silent 消失**と意味反転**を機械検出する決定論トリップワイヤ。
  - `scripts/context-budgets.json` の routing.md budget を **75→90** に引き上げ（下記の設計判断参照）。
- **効果**: qa-verification/qa.md に既存の `SendMessage` 用法が routing.md の定義で裏打ちされ、「3年後に SendMessage とは何か・
  実際に呼べるのか」を skill だけから再構築できない dangling が解消。iter58 の既知ギャップをクローズ。

## 主要な設計判断

- **配置は routing.md**（subagent-dev でなく）＝サブエージェント機構の正本ファイルが右文脈。qa→qa-browser 継続の適用は qa-verification に残す。
- **guidance のみ**（hook で決定論強制しない）＝aegis の『harness=構造/LLM=判断』に整合。継続定義の silent 消失/反転は token pin で機械検出。
- **予算引き上げの正当化（この iter の核心）**: iter58 は budget-raise を**却下**した（qa-verification に圧縮可能な冗長があった）。
  iter59 は routing.md が **100% load-bearing で圧縮パスが存在しない**（agent roster は `check_reference_drift #1` が
  agents/ と双方向 mirror で drift-pin＝削除不能）。よって本 bump は「圧縮回避の水増し」でなく「**圧縮不能な pinned ファイルへの
  正当な rule 追加の受容**」。bump は追加サイズ分に限定（75→90）＝tighten-only ラチェットの anti-bloat 趣旨を守る。
- **pin 強化（review 盲検2次 fix-forward）**: `harness-enforced` 単トークン→`not harness-enforced` 句。否定語 "not" を含めることで、
  節削除だけでなく「"not" 脱落による guidance→強制の意味反転（保護回帰）」も RED で捕捉。

## 変更ファイル

- `.claude/rules/routing.md`（継続節追加＋principle 1文化＝68→90 words）
- `scripts/context-budgets.json`（routing.md budget 75→90）
- `tests/test_skill_guidance_tokens.py`（`TestSubagentContinuationSoT` 追加＝2 assertion）
- version bump: `scripts/check_framework_contract.py`・`templates/STATUS.template.md`・`docs/STATUS.md`
- コミット: 実装 `b2c2851`・review fix-forward `89fb52f`

## 証拠

- 仕様: `docs/specs/2026-07-06-iter59-subagent-continuation-sot-design.md`（＋`-brainstorm-record.md`）
- 計画: `docs/plans/2026-07-06-iter59-subagent-continuation-sot-plan.md`（grill-plan 致命ゼロ・要検討 headroom-0/単一コミット/相対緑基準 反映済）
- レビュー: `docs/qa-reports/iter59-review.md`（1次 approve・盲検2次 approve_with_notes・divergence=pin 反転 false-PASS を fix-forward で解消）
- QA: `docs/qa-reports/iter59-qa.md`（B1 SKIP＋RED-first/反転捕捉/drift 回帰の代替実証・full suite 1052 passed / 2 skipped）
- セキュリティ: `docs/qa-reports/iter59-security.md`（1次 approve・盲検2次 approve・findings ゼロ・moat/enforcement 不変・secrets 0・deps🟡 は依存ゼロで ack）
- リリースノート: 本 TO-CLIENT ＋ `docs/LEARNINGS.md`（docs フェーズ追記）

## 既知のギャップ

- **headroom-0（routing.md content 90 / budget 90）**: 設計承認済の「最小 bump」に忠実だが、以後 routing.md に加筆する変更は
  **同一 diff で budget も共 bump 必須**（さもないと `context_budget` が即 FAIL）。review/security 両2次も「設計意図どおり・
  セキュリティ影響なし・運用メモ」と評価。→ LEARNINGS に co-bump ルールとして記録。
- **pin `not harness-enforced` の言い換え脆さ**: "not enforced by the harness" 等へ言い換えると false RED。ただし
  load-bearing 文言の書換えはテスト同時更新を強制する**意図した tripwire**（対応不要・test docstring に記載）。

## 配備と運用

- 環境: フレームワーク本体（`aegis/`）。install 先は `bin/setup.sh` 経由。
- アクセス: GitHub `yuuya-miyagaki/aegis`（push は `gh auth switch --user yuuya-miyagaki` 後）。
- 影響: rule guidance の後方互換な追加。**公開/運用契約は不変**（SemVer MINOR）。既存 install への破壊的変更なし。
- 監視: `check_framework_contract` / `check_reference_drift` / `context_budget` の機械検査で回帰検出。

## 次の推奨アクション

- 次: push（`gh auth switch --user yuuya-miyagaki` 後）＝**ユーザー確認待ちで停止中**。
- リスク: なし（guidance のみ・moat 非該当・全機械検査 PASS）。
- 次イテレーション候補: SendMessage 継続の**運用機構の SoT 深掘り**（iter58 review 2次 note1 の後続・routing.md 定義を起点に subagent-dev の継続手順を精緻化）、または budget ratchet policy 全体見直し（brainstorm-record で descope した別候補）。

## 承認

- 作成者: Dev（Aegis iter59）
- 日付: 2026-07-06
