# 受入条件

<!-- exit-check: AC が FR/NFR と紐付き・判定基準明確・ユーザー承認済み → handover へ -->
<!-- 正本: client-workflow skill (framework repo) -->

## リリースゲート

- ゲート: 主要クエリで期待結果が返り、review / QA / security evidence が揃っていること

## 機能受入条件

- AC-001: キーワード入力で関連ドキュメント一覧が表示される
- AC-002: フィルター適用時に結果が絞り込まれる
- AC-003: 各結果に出典スニペットが表示される

## 非機能受入条件

- AC-NFR-001: 主要クエリ 10 件の p95 応答時間が 2 秒以内
- AC-NFR-002: mock index 停止時にエラーメッセージと再試行導線を表示する

## トレーサビリティ（要件 → AC）

> 優先度は SCOPE の MoSCoW に準拠する。FR / NFR の両方を含める。

| 要件 | AC | 優先度 | 検証方法 |
|------|----|--------|---------|
| FR-001 | AC-001 | Must | 自動テスト + 手動確認 |
| FR-002 | AC-003 | Must | 手動確認 |
| FR-003 | AC-002 | Should | 自動テスト + 手動確認 |
| NFR-perf | AC-NFR-001 | Must | 自動テスト（p95 計測） |
| NFR-reliability | AC-NFR-002 | Must | 手動確認 |

## 必要な証拠

- テスト: 主要クエリ手動検証と対象コマンド実行結果
- レビュー: `docs/qa-reports/search-review.md`
- レポート: `docs/qa-reports/search-qa.md`, `docs/qa-reports/search-security.md`

## 承認

- 承認者: Product Owner
- 日付: 2026-04-09

<!-- aegis-required-section: acceptance-criteria -->
