# iteration 42 G1-G3 — Deploy Readiness

- date: 2026-06-24
- task: framework / L
- デプロイ形態: framework 変更＝main への commit + push（ランタイム target なし）。

## 事前条件（全 gate green）

| gate | 状態 | ref |
|------|------|-----|
| brainstorm | approved | docs/specs/2026-06-24-iter42-guard-coverage-brainstorm-record.md |
| plan | approved | docs/plans/2026-06-24-iter42-guard-coverage-plan.md |
| review | approved | docs/qa-reports/iter42-review.md |
| qa | approved | docs/qa-reports/test-strength.md |
| security | approved | docs/qa-reports/iter42-security.md |

## デプロイ前チェック

- [x] full suite green（1067 passed, 1 skipped・record green）
- [x] `check_framework_contract.py`（full）PASS（v1.14.0 据置）
- [x] `status_doctor.py` PASS
- [x] `bash -n`（patterns.sh / check-destructive / check-deploy-gate / check-cron-gate / check-secrets）PASS
- [x] version 1.14.0 据置（リリース/tag なし）
- [x] git mode-flip なし想定（最終 commit 前に確認）

## デプロイ手順

1. 関連ファイルを `git add`（patterns.sh / 3 hooks / check-secrets / tests / docs）。`.claude/settings.local.json` は gitignore＝対象外。
2. 単一 commit。
3. `git push`（yuuya-miyagaki アカウント＝現 shell の tigereye は 403）。

## ロールバック

- 単一 commit＝`git revert <sha>` で G1-G3 一括戻し。
- guard は emit_ask/deny の追加のみ＝挙動退行リスク低（既存 deny 弱体化なしを security で確認）。

## 残リスク

- F1（quoted-path-with-space の secret-staging miss）＝Low・baseline 同等・既知限界。
- 繰延: iter43（I3 task_type/size tamper-evidence・authorized-path 設計）。
