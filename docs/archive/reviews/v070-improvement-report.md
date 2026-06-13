# Ultra Framework Claude Code v0.7.0 改善報告書

> 対象: `ultra-framework-claude-code/` v0.6.0 → v0.7.0
> 日付: 2026-04-15

## 変更概要

v0.7.0 は **STATUS.md スキーマ拡張とコンテキスト効率改善** に焦点を当てたリリース。
Phase A（即時修正）、Phase B（スキーマ変更）、Phase C（ファイナライズ）の 3 段階で実施。

## Phase A: 即時修正

| ID | 内容 | 変更ファイル |
|----|------|-------------|
| P1-01 | `check-tdd.sh` に実行権限付与 | `hooks/check-tdd.sh` (root + example) |
| P2-01 | CLAUDE.md Skills 行を template と同期 | `CLAUDE.md` |
| P2-02/03 | `post-status-audit.sh` に defense-in-depth ファイルパスフィルタ追加 | `hooks/post-status-audit.sh` (root + example) |
| P2-10 | LEARNINGS grep を POSIX 互換パターンに修正、1行制約を追加 | `hooks/session-start.sh`, `templates/LEARNINGS.template.md`, `scripts/check_framework_contract.py` |
| P3-03 | QA エージェントにブラウザ QA ハンドオフ手順を追加 | `.claude/agents/qa.md` (root + example) |

## Phase B: STATUS.md スキーマ変更

### Step 1: アーカイブ制限 (P2-09 + P3-01)

- `session_history`: MAX 5 → 3。古いエントリは body の Session History に退避
- `external_evidence`: MAX 3 を新設。古いエントリは `docs/evidence-archive.md` に退避
- `state-machine.md`: iteration リセット時の external_evidence アーカイブルールを追記
- `/next` コマンド: 上限到達時のアーカイブ提案を追加

**設計判断**: アーカイブ基準は iteration ベースではなく latest N。
理由: root STATUS.md は iteration=1 のまま多数のレビューを蓄積しており、
iteration ベースではアーカイブが発動しない。

### Step 2: failure_tracking (P2-08)

```yaml
failure_tracking:
  goal: "目標の説明"
  count: 2
  last_attempt: "最後に試みた内容"
```

- `check_status.py`: OPTIONAL_TOP_LEVEL_KEYS に追加、スキーマ検証（goal/count/last_attempt）
- `CLAUDE.md` (root + template + example): 3-failure ルールに failure_tracking 記録を追記
- `implementer.md` (root + example): failure_tracking 更新ルールを追記
- `session-start.sh` (root + example): failure_tracking 検出時に WARNING を注入

**設計判断**: attempts 配列を持たず goal/count/last_attempt の薄い構造を採用。
理由: check_status.py の narrow YAML パーサーが 3 段ネストに対応していない。
last_attempt 1 件で直近の試行を追跡でき、実用上十分。

### Step 3: task_size_rationale (P2-07)

- `check_status.py`: OPTIONAL_TOP_LEVEL_KEYS に追加、task_size 設定時に未記入で WARNING（FAIL ではない）
- `templates/STATUS.template.md`: コメントで使い方を案内
- `brainstorming/SKILL.md` (root + example): Step 10 に rationale 記録手順を追加
- `bug-diagnosis/SKILL.md` (root + example): Gate 処理に rationale 記録手順を追加

**設計判断**: WARNING レベル（FAIL にしない）。
理由: 既存プロジェクトとの後方互換性を優先。

### Step 4: バージョン bump

`scripts/check_framework_contract.py`, `docs/STATUS.md`, `templates/STATUS.template.md`,
`examples/minimal-project/docs/STATUS.md` を 0.6.0 → 0.7.0 に更新。

## Phase C: ファイナライズ

| ID | 内容 |
|----|------|
| P2-05 | session_history に Phase A+B+C の実装記録を追加 |
| P2-02/03 | STATUS.md Summary のスキル数（9→8）・フック数（7→6）を repo 横断で修正 |
| P2-04 | Recent Decisions を v0.7.0 寄りに整理、歴史的判断を除去 |
| P2-01 | README に Migration セクション追加（v0.6.0→v0.7.0、v0.5.0→v0.6.0 並列） |
| P3-01/02 | `docs/reviews/` 新設、完了済み second-opinion ファイルをアーカイブ |

## レビュー経緯

- Phase A: P2-10 について Codex セカンドオピニオン 1 回（POSIX regex, 1行制約）
- Phase B: スキーマ設計について Codex セカンドオピニオン 1 回（6 質問）
- Phase C: ファイナライズ方針について Codex セカンドオピニオン 1 回（6 質問）
- レビュー文書は `docs/reviews/` にアーカイブ済み

## バリデーション結果

```
PASS: ultra-framework-claude-code contract is aligned
PASS: status file is valid: docs/STATUS.md
PASS: status file is valid: examples/minimal-project/docs/STATUS.md
```

## 変更ファイル数

| カテゴリ | ファイル数 |
|----------|-----------|
| スキーマ / バリデータ | 3 (check_status.py, check_framework_contract.py, STATUS.template.md) |
| 制御ファイル | 6 (CLAUDE.md x3, state-machine.md x2, next.md x2) |
| エージェント | 4 (implementer.md x2, qa.md x2) |
| スキル | 4 (brainstorming x2, bug-diagnosis x2) |
| フック | 4 (session-start.sh x2, post-status-audit.sh x2) |
| ドキュメント | 5 (STATUS.md, README.md, evidence-archive.md, v070-improvement-report.md, reviews/) |
| **合計** | **~26 ファイル** |

## 残課題

v0.7.0 スコープ外とし、次バージョンで検討する項目:

- external_evidence の type 命名規則の標準化（現状はフリーテキスト）
- body Session History の自動アーカイブ（現状は手動退避）
- narrow YAML パーサーの PyYAML 移行判断（nested 構造追加時に再検討）
