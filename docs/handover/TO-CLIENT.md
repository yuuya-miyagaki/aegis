# 納品サマリー — iteration 58（v1.19.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の guidance 改修。「client」＝フレームワーク保守者
> （次に aegis を使う自分自身）。外部クライアントへの製品納品ではない。

## 納品サマリー

- リリース / ビルド: **v1.18.0 → v1.19.0（MINOR）**
- 日付: 2026-07-05
- 担当者: Dev（Aegis 自己改修イテレーション）
- 操作マニュアル: **生成せず** — エンドユーザー製品でなくフレームワーク（利用者＝保守者自身）。
- 運用 RUNBOOK: **生成せず** — 運用者なし（CI 相当は contract/drift/context-budget の機械検査）。
- UAT 結果: **生成せず** — `docs/requirements/ACCEPTANCE.md` なし（受入基準を要する外部案件でない）。

## 実装範囲

- **完了**: qa→qa-browser の委譲を標準委譲プロンプト雛形へ昇格（guidance のみ）。
  - `qa-verification SKILL.md` の「qa-browser 委譲ルール」節を拘束5点に置換:
    ①1委譲 ≤5 項目・連番 ②**全項目のエビデンスが揃うまで最終報告を出さない**（partial を final と偽らない）
    ③途中停止は **SendMessage** で同一エージェント継続 ④`[n/N done]` 進捗 ⑤エビデンス形式。
  - `qa.md` の Browser QA 節を skill 参照へ縮約＝**委譲 guidance の単一正本化**（重複 drift 源を除去）。
  - `tests/test_skill_guidance_tokens.py` に load-bearing トークン pin（完了拘束の短核＋SendMessage）を追加＝
    核心命令の silent 消失を機械検出する決定論トリップワイヤ。
  - 語数相殺（intro 圧縮＋確認事項冗長ブロック除去）で `context_budget` を割らず 449/455（headroom 6）維持。
- **保留**: SendMessage 継続機構の SoT 定義（subagent-dev/routing.md への1行追記）＝次イテレーション候補（下記ギャップ）。

## 主要な設計判断

- **guidance のみ**（hook で決定論強制しない）＝aegis の『harness=構造/LLM=判断』に整合。silent 消失は token pin で機械検出。
- **token pin は短核**（`全項目のエビデンス`＋`最終報告を出さない`＋`SendMessage`）＝長文完全一致の false RED を回避しつつ核心を守る。
- **budget 引き上げでなく圧縮で対処**（tighten-only ラチェットの anti-bloat 趣旨を尊重）。

## 変更ファイル

- `.claude/skills/qa-verification/SKILL.md`（委譲節 rewrite＋語数相殺2箇所）
- `.claude/agents/qa.md`（Browser QA 節を skill 参照へ縮約）
- `tests/test_skill_guidance_tokens.py`（token pin 追加＋クラス改名）
- version bump: `scripts/check_framework_contract.py`・`templates/STATUS.template.md`・`docs/STATUS.md`

## 証拠

- 仕様: `docs/specs/2026-07-05-iter58-qa-browser-delegation-design.md`
- 計画: `docs/plans/2026-07-05-iter58-qa-browser-delegation-plan.md`（grill-plan 致命1＋要検討1-5 反映済）
- レビュー: `docs/qa-reports/iter58-review.md`（1次 approve・盲検2次 approve_with_notes・全 notes 処理済）
- QA: `docs/qa-reports/iter58-qa.md`（B1 SKIP＋RED-first 代替実証・full suite 1050 passed / 2 skipped）
- セキュリティ: `docs/qa-reports/iter58-security.md`（1次 approve・盲検2次 approve・後退なし・deps🟡 は依存ゼロで ack）
- リリースノート: 本 TO-CLIENT ＋ `docs/LEARNINGS.md`（docs フェーズ追記）

## 既知のギャップ

- **SendMessage 継続機構の SoT 未定義**（review 2次 note1）: `subagent-dev`/`routing.md` に「サブエージェント継続＝
  SendMessage」の機構定義がなく、skill だけからは再構築しにくい。→ 次イテレーション候補として起票（本 iter はスコープ規律で分離）。
- `[n/N done]` を token pin しない判断（review 2次 note3）: false RED とのトレードオフで妥当。途中停止再発時の第一被疑箇所として
  test docstring に監視項目を記載済。

## 配備と運用

- 環境: フレームワーク本体（`aegis/`）。install 先は `bin/setup.sh` 経由。
- アクセス: GitHub `yuuya-miyagaki/aegis`（push は `gh auth switch --user yuuya-miyagaki` 後）。
- 影響: skill/agent guidance の後方互換な追加。**公開/運用契約は不変**（SemVer MINOR）。既存 install への破壊的変更なし。
- 監視: `check_framework_contract` / `check_reference_drift` / `context_budget` の機械検査で回帰検出。

## 次の推奨アクション

- 次: push（`gh auth switch --user yuuya-miyagaki` 後）＝**ユーザー確認待ちで停止中**。次イテレーションで SendMessage SoT 定義を検討。
- リスク: なし（guidance のみ・moat 非該当・全機械検査 PASS）。

## 承認

- 作成者: Dev（Aegis iter58）
- 日付: 2026-07-05
