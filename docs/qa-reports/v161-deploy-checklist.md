# v1.6.1 deploy チェックリスト（2026-06-13）

## デプロイ形態

aegis はフレームワーク本体（distribution）。CI/CD やランタイムサービスはない。「deploy」は **tag 付与＋origin push** を指す。よって本ファイルは `n/a` 宣言と schema migration 注記を主目的とする。

## デプロイ対象

| 項目 | 状態 |
|------|------|
| Hosting | n/a |
| Database | n/a |
| CI/CD | n/a |
| 環境変数 | 変更なし（`AEGIS_TDD_MODE`、`AEGIS_ROOT_OVERRIDE`、`CLAUDE_PROJECT_DIR` 等の挙動は v1.6.0 と互換） |

## Schema migration（evidence-log）

v1.6.1 は `hooks/post-bash-observe.sh` が evidence-log の各 entry に **新フィールド `marker_verified` を追加**する。

### 後方互換規則

| ログ世代 | `marker_verified` | `read_test_result` の判定 |
|---------|-------------------|-------------------------|
| v1.6.0 以前（フィールド不在） | `null`（不在） | 強制 `unverified`（fail-closed） |
| v1.6.1 以降・偽装系 | `false` | `unverified` |
| v1.6.1 以降・本物テスト | `true` | `status:ok` なら `green`、`fail` なら `red` |

### マイグレーション手順（ユーザ側）

1. **アップグレード後の初回**: 過去の v1.6.0 ログは強制 `unverified` 化される
2. **テスト再走**: 通常の TDD ループ（テスト実行）で entry が新スキーマに上書きされる
3. **gate 再承認**: `record-test-result.py` 経由の manual entry はマイグレーション不要（src=manual は marker_verified を要求しない）

## 公開契約の変更点（SemVer 影響）

- **追加のみ・破壊的変更なし**: SemVer に従い patch リリース（v1.6.0 → v1.6.1）
- public surface（hook 入出力スキーマ、state machine、プロファイル名、JUDGE_GATES）は変更なし
- 新規 lib `hooks/lib/secrets-patterns.sh`、新規 pattern `AEGIS_TEST_PASS_MARKER_REGEX` / `AEGIS_TEST_PASS_MARKER_PAIRS` / `AEGIS_TEST_NO_RUN_FLAG_REGEX` / `AEGIS_HIGH_RISK_RE` / `AEGIS_HIGH_RISK_CASE_GLOB(_ARR)` / `AEGIS_HIGH_RISK_FIND_NAMES` / `AEGIS_HIGH_RISK_STAGED_RE` は追加
- SessionStart matcher の `resume` 追加は SemVer compatible（既存挙動を残しつつ追加イベントを処理）

## デプロイ手順

```bash
# 1. ブランチ確認
git checkout fix/v1.6.1-critical-bypasses
git log --oneline main..HEAD | wc -l    # commit 数を確認

# 2. main へマージ
git checkout main
git merge --ff-only fix/v1.6.1-critical-bypasses    # squash しない（commit ごとに revert 可能）

# 3. tag 付与
git tag -a v1.6.1 -m "v1.6.1: fix-forward Critical 7 + S-3 + S-11 + grill-code"

# 4. origin push（ユーザ判断）
git push origin main
git push origin v1.6.1
```

## ロールバック手順

万一の場合：

```bash
# 個別 commit revert（commit プランどおり 1 commit/Task）
git revert <commit-hash>

# tag 削除
git tag -d v1.6.1
git push origin :refs/tags/v1.6.1
```

## 完了条件

- [x] `framework_version: "1.6.1"` 一斉更新（templates / docs / examples / scripts/check_framework_contract.py）
- [x] `docs/qa-reports/v161-review.md` 作成
- [x] `docs/qa-reports/v161-qa.md` 作成
- [x] `docs/qa-reports/v161-security.md` 作成
- [x] `docs/qa-reports/v161-deploy-checklist.md` 作成（本ファイル）
- [x] `docs/architecture-overview.md` の版履歴行に v1.6.1 を追加（commit 内に含む）
- [x] `docs/full-review-2026-06-12.md` の close 記録（v1.6.1 で消化）
- [ ] `git tag v1.6.1`（次の commit 内）
- [ ] `git push origin main && git push origin v1.6.1`（ユーザ判断）
