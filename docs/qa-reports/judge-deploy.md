# Judge カード: deploy ゲート（機械生成）

## 総合: 🟡 要確認

## ティア1: 機械事実（✅検証済・高信頼）
- テスト: unverified
- 未完成マーカー(変更行): なし

## 🟡 要確認
- テスト結果が未検証（記録なし/コード変更後）
- claims 未提出（要確認）

## あなたが取るアクション
（LLM が平易日本語で記述）

## ACK
- 配布リスク低: 層1 は framework-dev 専用（installed 非配布）・層2 は手動 opt-in addon（contract 非登録）・全変更が非ミラー面で make example 差分ゼロ。ロールバックは関連コミット revert で完全復元。根拠 v1100-deploy-checklist.md。 （2026-06-14 22:15）
