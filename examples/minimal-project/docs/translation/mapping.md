# Translation Mapping

<!-- 3層マッピング: Client用語 → 機能仕様 → 実装ヒント -->
<!-- exit-check: 全クライアント用語がマッピング済み・Invariants記録済み → handover 可 -->

## 3層マッピング表

| Client Term | Functional Meaning | Implementation Hint |
|-------------|-------------------|---------------------|
| タスク | ユーザーが作成・更新・完了できる作業単位。担当者・期日・優先度・ステータス・ラベルを属性として持つ | `Task` テーブル（Firestore コレクション）: `id`, `title`, `assigneeId`, `dueDate`, `priority`, `status`, `labels[]`, `projectId`, `sprintId`, `createdAt`, `updatedAt` |
| ボード | 特定プロジェクト／スプリントのタスクをステータス列で可視化するビュー | `BoardView` コンポーネント: ステータス列（`KanbanColumn`）× タスクカード（`TaskCard`）。Firestore リアルタイムリスナーで列更新 |
| スプリント | 固定期間（2 週間）の作業サイクル。タスクの計画単位 | `Sprint` テーブル: `id`, `projectId`, `startDate`, `endDate`, `name`, `status`（planning/active/completed）。タスクの `sprintId` FK で紐づけ |
| 優先度 | タスクの重要度ランク。ボード表示順と通知頻度に影響 | `priority` フィールド: enum `high` / `medium` / `low`。UI は色バッジ（赤/黄/灰）で表示 |
| 担当者 | タスクの実施責任者。MVP では 1 タスク 1 名制約 | `assigneeId`: `User.id` の外部キー。UI は ユーザーアバター選択。担当なし = `null` |
| ラベル | タスクへの自由カテゴリタグ。複数付与可能 | `labels` フィールド: `string[]`。UI はテキスト入力＋オートコンプリート。フィルタ API に配列 contains クエリ |
| プロジェクト | 複数スプリントをまとめる業務テーマ | `Project` テーブル: `id`, `name`, `description`, `ownerId`, `memberIds[]`. ボードの親コンテキスト |
| コメント | タスクに紐づく非同期メッセージ | `Comment` サブコレクション（`tasks/{taskId}/comments`）: `id`, `authorId`, `body`, `createdAt`。新規投稿時に担当者へ通知（Firebase Cloud Messaging） |
| 期日 | タスクの完了目標日（datetime） | `dueDate`: ISO 8601 timestamp。期日超過判定: クライアントサイドで `now > dueDate && status !== 'completed'` を評価しバッジ表示 |
| ステータス | タスクの進行状態（5 種） | `status`: enum `todo` / `in_progress` / `review` / `done` / `cancelled`。ボード列にマッピング。`cancelled` はボード非表示（アーカイブ扱い） |

## Invariants（不変条件）

- タスクは必ずいずれかのプロジェクトに属する（孤立タスク不可）
- スプリントの期間は 2 週間固定（変更にはプロジェクトオーナー承認が必要）
- ステータスが `done` のタスクは担当者変更不可（完了後の責任追跡のため）
- `priority` は必ず 3 段階のいずれか（null 不可、デフォルト `medium`）

## Assumptions（前提条件）

- MVP では 1 タスク 1 担当者のみ（複数担当は次フェーズ）
- 認証は MVP では Google Workspace SSO ではなくメール+パスワードを採用（open-questions #3）
- スプリント繰り越しは手動操作とする（open-questions #2）
- オフライン操作は MVP スコープ外

## Open Items（未解決事項）

- open-questions #1: 複数担当者対応の要否 → MVP は 1 名制約で実装し、データモデルは拡張余地を残す（`assigneeId` → `assigneeIds[]` に将来変更可能な設計）
- open-questions #2: スプリント繰り越し挙動 → 確認中（クライアント回答待ち）
- open-questions #3: SSO 認証スコープ → MVP 除外方向で合意待ち

<!-- aegis-required-section: translation-mapping -->
