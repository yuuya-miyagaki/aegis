# Judge カード: review ゲート（機械生成）

## 総合: 🟡 要確認

## ティア1: 機械事実（✅検証済・高信頼）
- テスト: unverified
- 未完成マーカー(変更行): なし

## ティア2: 🔍 第2意見（self-attested・自己申告・低信頼）
- あり: approve_with_notes

## 🟡 要確認
- テスト結果が未検証（記録なし/コード変更後）
- 1次/2次レビューの相違（self-attested）: 1次=approve / 2次=approve_with_notes

## あなたが取るアクション
（LLM が平易日本語で記述）

## ACK
- テスト: full suite 830 passed/1 skip 実走（fp一致）。marker自動検証はharnessがPostToolUseにtool_response.outputを渡さない環境由来で不可（合成入力でロジック正常を確認）。1次/2次相違=SF-001(pre-existing)繰延のみで両者ともBatch1後退ゼロに一致。詳細 docs/qa-reports/iter31-batch1-review.md （2026-06-17 18:48）
