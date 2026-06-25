# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-25-iter46-threat-model-boundary-brainstorm-record.md`
- 要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（backlog の C4・G4）

## 問題整理

- 背景: full-review backlog の C4（gate 値パーサ乖離）と G4（secret ゲート scope）が「未消化のセキュリティ課題」として残っている。iter46 で両者を grill-premise + 実測検証した結果、**いずれもコード修正を要する脆弱性ではない**（C4=NOT-A-VULN、G4=by-design 境界）。残る作業は「検証済みの verdict を durable に明文化してクローズする」こと。
- 判断が必要な論点: verdict の置き場所（既存 security-followups.md 拡張 vs 新規 doc）。→ ブレインストーミングで A（既存拡張）に決定。
- 制約条件: コードは書かない。脅威モデル（LLM self-bypass）から逸脱した過大な security 主張をしない（「限界主張は実証してから」）。第3の同期先を作らない。

## 推奨アプローチ

- 採用方針: `docs/security-followups.md` を 3 点拡張する（① canonical 脅威モデル節 ② SF-007=C4 ③ SF-008=G4）。あわせて full-review doc の backlog 行を closed 化、README posture を必要に応じ整合。
- 採用理由: 既存の durable security 正典に集約＝drift/同期先最小・読み手一貫。空だった CLOSED 節を初めて埋める。
- 検討した代替案と不採用理由: 新規 THREAT-MODEL.md＝同期先増の YAGNI／full-review doc 内だけ＝durable 性不足（記録は brainstorm-record 参照）。

## コンポーネント分解

- 分割方針: 1 つの durable doc（security-followups.md）への追記が主。波及更新が 2 ファイル。
- 各ユニットの責務:
  - ユニット A（`docs/security-followups.md`）: canonical 脅威モデル節 + SF-007 + SF-008（CLOSED 節へ）。本イテレーションの主成果物。
  - ユニット B（`docs/full-review-2026-06-24-...md`）: backlog 行の C4/G4 を closed 化し SF-007/008 へポインタ。
  - ユニット C（`README.md` §95 posture 表）: secret ゲートが「ファイル名・commit-stage 限定／content・exfil は対象外」である旨を**必要なら**一行整合（既存記述で十分なら触らない＝YAGNI）。

## インターフェース定義

- 該当なし（ドキュメント変更・公開 API/関数の追加なし）。
- 記録フォーマット契約: SF-007/008 は既存 SF エントリの節構成（発見・種別・重大度・再現/根拠・なぜ accept/CLOSED・状態）に揃える。

## データフロー / 構造

- 入力: C4 の実測証拠（12 形 probe で bypass-direction 0 行・strict 化が tamper backstop を弱める）、G4 の境界分析（D2 scope・commit chokepoint・exfil はモデル外/futile）。
- 処理: 既存 SF 様式で文章化。脅威モデル文言を canonical 節へ集約。
- 出力: security-followups.md の OPEN/CLOSED 更新、backlog 行更新。

## 依存関係

- 依存方向: A（security-followups.md）が正本 → B/C はそこへポインタ。循環なし。
- 外部依存: なし。

## エラーハンドリング

- 想定失敗: verdict の過大主張（C4 を「修正した」と誤記載／exfil を「防げる」と誤記載）。
- 対応: SF-007 は「NOT-A-VULN（実証）・コード変更なし」、SF-008 は「by-design・exfil はモデル外で futile」と明記。security ゲートで verdict の正確性を独立検証（盲検 security エージェント）。
- エラー伝播の方針: 不正確な verdict は security ゲートで reject → 修正。

## テスト戦略

- 単体/結合: 該当なし（テスト可能な production code を追加しない）。
- エッジケース: C4 verdict の根拠（probe 結果）が再現可能であること＝SF-007 に再現手順を残し、必要時に再実行できる形にする。
- 手動確認: (1) status_doctor PASS (2) framework contract PASS（ref 整合）(3) ドキュメント lint/リンク整合 (4) review ゲート（doc の明瞭性・正確性）(5) qa ゲート＝B1 drill は **auditable skip**（`{"skip":true,"reason":"docs-only: テスト可能な production code を追加しない"}`）(6) security ゲート＝verdict の正確性・脅威モデル整合を盲検 security エージェントが検証。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-25-iter46-threat-model-boundary-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
