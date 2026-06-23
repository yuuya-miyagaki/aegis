# Judge カード: deploy ゲート（機械生成）

## 総合: 🟡 要確認

## ティア1: 機械事実（✅検証済・高信頼）
- テスト: green
- 未完成マーカー(変更行): なし

## 🟡 要確認
- claims 未提出（要確認）

## あなたが取るアクション
（LLM が平易日本語で記述）

## ACK
- framework 変更＝main commit/push がデプロイ（ランタイム target なし）。全 gate green（review/qa/security approved）・full suite 1053 passed/1 skip（record green）・contract full PASS・standard install 実機検証 PASS・version 1.14.0 据置。claims 未提出は deploy が runtime デプロイでないため＝readiness は docs/qa-reports/iter41-deploy.md に記載。ロールバックは単一 commit の git revert。 （2026-06-24 02:28）
