# iteration 41 Batch 1 — Deploy Readiness

- date: 2026-06-24
- task: framework / L
- デプロイ形態: **framework 自体の変更＝main への commit + push**（ランタイム deploy ターゲットなし）。

## 事前条件（全 gate green）

| gate | 状態 | ref |
|------|------|-----|
| brainstorm | approved | docs/specs/2026-06-24-iter41-batch1-distribution-integrity-brainstorm-record.md |
| plan | approved | docs/plans/2026-06-24-iter41-batch1-implementation-plan.md |
| review | approved | docs/qa-reports/iter41-review.md |
| qa | approved | docs/qa-reports/test-strength.md |
| security | approved | docs/qa-reports/iter41-security.md |

## デプロイ前チェック

- [x] full suite green（1053 passed, 1 skipped・record green・fingerprint bind 済）
- [x] `check_framework_contract.py`（full）PASS（版 1.14.0 据置）
- [x] `status_doctor.py` PASS
- [x] `bash -n` 構文チェック（setup.sh / post-status-audit.sh / safety.sh）PASS
- [x] standard 配布の実機検証（`setup.sh --profile=standard` → `--profile=standard` contract PASS・judge toolchain + Task hooks 同梱確認）
- [x] version: 1.14.0 据置（iter38-40 同様・リリース/tag なし＝MINOR bump 不要）
- [x] git mode-flip なし想定（最終 commit 前に `git status --porcelain` で確認）

## デプロイ手順

1. 関連ファイルを `git add`（profile/setup/hooks/scripts/tests/docs）。`.claude/settings.local.json` は gitignore＝コミット対象外（dogfood ローカル設定）。
2. 単一 commit（fix(dist+integrity): iter41 Batch 1）。
3. `git push`（yuuya-miyagaki）。

## ロールバック

- 単一 commit のため `git revert <sha>` で全 6 fix を一括戻し可能。
- D3 の挙動変更（再 install で framework 所有を .bak つき上書き）はユーザー環境では `.bak.*` から復元可能。

## 残リスク

- なし（Low/受容: D3 symlink follow＝SF-004 クラス・security-followups 記録済）。
- 繰延: Batch 2（I3 task_type/size tamper-evidence・G1-G3 guard 網羅）。
