# Client から Dev への引き渡し

<!-- exit-check: 正本参照済み・優先順位/リスク/未解決事項記載・ユーザー承認済み → client_ready_for_dev ゲート申請 -->
<!-- 正本: client-workflow skill (framework repo) -->

## プロジェクト概要

- プロジェクト名: 社内ナレッジ検索アシスタント
- 目的: 社内資料探索の初回成功率を上げる
- 現在フェーズ: Client 完了 / Dev 開始

## 正本ドキュメント

- `docs/requirements/PRD.md`
- `docs/requirements/SCOPE.md`
- `docs/requirements/NFR.md`
- `docs/requirements/ACCEPTANCE.md`

## スコープ境界

- 対象範囲: 検索フォーム、結果一覧、フィルター、出典スニペット
- 対象外: 権限制御、取り込みパイプライン、分析ダッシュボード

## 優先順位

- Must: 検索、結果一覧、スニペット
- Should: ドキュメント種別フィルター
- Could: 検索候補表示

## 技術選定の背景

- 背景: まず UI と運用フローを固めてから検索基盤を差し替えたい
- 選定理由: mock index で実装すると UI / validation を先に確立できる

## リスクと制約

- リスク: 実検索基盤との差異で次フェーズに差し戻しが出る
- 制約: 初期版は社内 VPN 配下のみ
- 依存関係: 社内ドキュメント一覧 CSV

## 未解決事項

- 権限連携の方式は次フェーズで再検討

## 承認

- 承認者: Product Owner
- 日付: 2026-04-06

<!-- aegis-required-section: handover-to-dev -->
