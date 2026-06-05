# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- この変更で達成すること: <記入>

## 入力

- 参照要件: <docs/requirements/ のパス>
- 参照設計: <docs/specs/ のパス>

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: <Vercel / Cloud Run / Docker / VPS / n/a>
- Database: <Neon / Cloud SQL / Supabase / PlanetScale / n/a>
- CI/CD: <Vercel Git / GitHub Actions / Cloud Build / n/a>

### 互換性確認

- next.config `output` 設定: <default / standalone / export / n/a>
- 上記がデプロイ先と互換であることを確認: <Yes / No + 理由>

### 認証方式

- 認証プロバイダ: <Firebase Auth / Google OAuth / Auth.js / None>
- DEMO_MODE 予定: <開発のみ / ステージングまで / 本番は認証必須>

## Git 戦略

Git 戦略は Project Overrides に定義。未定義なら feature branch + squash merge。

## ファイル構造（変更マップ）

変更前に、対象ファイルと責務を確定する。

- 新規: <正確なパス> — <責務>
- 変更: <正確なパス:行範囲> — <変更概要>
- テスト: <正確なパス> — <検証対象>

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | <型名/関数名> | <なし or 他タスク生成物> |

循環依存 → 再分割。Consumes が Produces にない → 事前準備に記載。

## タスク分解

> 各タスクは 2-5 分単位。「and」が入るなら分割。共通ヘルパーは Task 0 として先行実装。

### タスク 1: <コンポーネント名>

**blockedBy:** なし | **モデル:** `inherit`/`sonnet`/`opus`
**ファイル:** 対象 `<パス>` / テスト `<パス>`
**意図:** <1-2 文>
**TDD:** テスト → FAIL確認 → 最小実装 → PASS確認 → コミット
**受入条件:** <完了条件>
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

(タスク 2 以降も同じ形式で繰り返す)

## External Integrations（該当する場合のみ記載）

| 連携先 | テスト方式 | テスト環境 | 本番後テスト手順 |
|--------|-----------|-----------|----------------|
| <記入> | <Mock + E2E 等> | <テストチャンネル等> | <記入> |

## 事前準備

実装開始前に確認する:

- [ ] 必要な環境・API キー・外部サービスへのアクセスがある
- [ ] 依存パッケージがインストールされている
- [ ] ベースブランチが最新である

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| FR-001 | AC-001 | Task 1 | `tests/path/to/test.ts` |

全 FR/NFR がいずれかの Task でカバーされていること。

## 自己レビュー

- 仕様カバレッジ（全要件にタスクがあるか）
- 曖昧さ検出（2 通りに解釈できる記述がないか）
- 型の整合性（タスク間で名前が一致しているか）
- 境界整合性（Consumes が対応する Produces に一致しているか）

## リスク

- リスク: <記入>
- 対策: <記入>

## 完了条件

- [ ] 全テスト pass
- [ ] レビュー完了
- [ ] <追加条件>
## QA チェックリスト（ui_surface: true の場合）

- [ ] <検証 URL とページ表示確認>
- [ ] <主要操作>
- [ ] コンソールエラーなし
- [ ] ネットワーク 4xx/5xx なし
- [ ] <受入条件との突合>

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->
