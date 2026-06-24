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
- framework 変更＝main commit/push がデプロイ（runtime target なし）。全 gate green（review/qa/security approved）・full suite 1067 passed/1 skip（record green）・contract full PASS・bash -n 全 hook。readiness は docs/qa-reports/iter42-deploy.md。ロールバックは単一 commit の git revert。claims 未提出は runtime デプロイでないため。 （2026-06-24 17:53）
