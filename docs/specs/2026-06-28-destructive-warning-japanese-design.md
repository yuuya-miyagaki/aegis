# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-28-destructive-warning-japanese-brainstorm-record.md`
- 要件: なし（internal framework iteration）

## 問題整理

- 背景: 破壊的コマンドの permission prompt（ask）reason だけが英語。framework の他の全プロンプト・ドキュメントは日本語。北極星は日本語話者の知識の乏しい運用者で、最高リスク（誤った yes が致命的）の局面で英語の危険説明を読まされる内部不整合。
- 判断が必要な論点: 訳文フォーマット（解決＝A）／ドリフトガード機構（解決＝日本語文字必須）／スコープ（解決＝破壊的＋フォールバックのみ）。
- 制約条件: 判定ロジック無改変＝moat 不変。emit.sh の JSON エスケープは日本語（マルチバイト）を透過。

## 推奨アプローチ

- 採用方針: WARN 本文のみ日本語化（format「破壊的: <コマンド>。<何が起きるか>（<復元可否>）。」）＋ patterns.sh の WARN 配列に「日本語文字を1要素以上含む」ドリフトガード。
- 採用理由: 既存様式との一貫性・コマンドトークン保持による正確性・復元可否の明示・ASCII トークンを許す誤検知しないガード。
- 検討した代替案と不採用理由: 冗長な novice 寄せ版（統一感が緩む）／近似逐語簡潔版（判断材料が薄い）。

## コンポーネント分解

- 分割方針: データ（patterns.sh の WARN 文字列）と発火点（hooks）と検証（test）を分離。
- 各ユニットの責務:
  - `hooks/lib/patterns.sh`: AEGIS_DESTRUCTIVE_LOWER_WARN（2）＋AEGIS_DESTRUCTIVE_CMD_WARN（16）の文字列を日本語化。regex 配列は無改変。
  - `hooks/check-destructive.sh`: inline `rm -r/-R` WARN ＋抽出失敗フォールバックを日本語化。`emit_ask "[careful] $WARN"` の構造は据置。
  - `hooks/check-secrets.sh`: 抽出失敗フォールバックを日本語化。
  - `tests/test_destructive_warning_language.py`（新規）: ドリフトガード＋inline 発火テスト＋フォールバックのカバー。

## インターフェース定義

- 変更対象は `permissionDecisionReason` 文字列のみ。hook の出力契約（`{"hookSpecificOutput":{"permissionDecision":"ask","permissionDecisionReason":"<JP>"}}`）は不変。
- ドリフトガードの読み出し契約: `bash -c 'source hooks/lib/patterns.sh; printf "%s\n" "${AEGIS_DESTRUCTIVE_LOWER_WARN[@]}"'`（CMD_WARN も同様）で配列要素を1行1要素で取得。

## データフロー / 構造

- 入力: 破壊的コマンド（tool_input.command）。
- 処理: regex 照合（無改変）→ 一致時に対応する WARN（日本語）を選択。
- 出力: `permissionDecision:"ask"` ＋ 日本語 `permissionDecisionReason` → Claude Code 確認 UI に表示。

## 依存関係

- 依存方向: check-destructive.sh → patterns.sh（WARN データ）＋ emit.sh（出力）。循環なし。
- 外部依存: なし（ドリフトガードは bash＋python3 標準のみ）。

## エラーハンドリング

- 想定失敗: 将来パターン追加時に英語 WARN を混入 → ドリフトガードが RED。
- 対応: 日本語文字必須 assert。
- エラー伝播の方針: 判定ロジック無改変のため ask/deny の安全挙動は不変。emit.sh のマルチバイト透過で日本語 reason は有効 JSON。

## テスト戦略

- 単体: 両 WARN 配列の各要素が日本語文字（U+3040–309F／U+30A0–30FF／U+4E00–9FFF）を1つ以上含む（ドリフトガード）。
- 結合: `rm -rf foo/` を check-destructive.sh に流し reason に日本語が含まれる（inline カバー）。
- エッジケース: 抽出失敗フォールバック2件 — 実発火が可能ならそれで、困難ならソース行に日本語必須を assert（plan で確定）。build-artifact 再帰削除は allow のまま（誤検知しない）。
- 手動確認: 主要破壊的コマンド数件を実際に発火させ、確認プロンプトに日本語 reason が表示されることを確認。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-28-destructive-warning-japanese-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->
