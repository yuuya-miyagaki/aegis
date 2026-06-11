# Judge カード: security ゲート（機械生成）

## 総合: 🟡 要確認

## ティア1: 機械事実（✅検証済・高信頼）
- テスト: green
- 未完成マーカー(変更行): なし
- シークレット: なし
- 依存監査: unverified

## ティア2: 🔍 第2意見（self-attested・自己申告・低信頼）
- なし

## 🟡 要確認
- 依存監査が未検証
- claims 未提出（要確認）
- 第2意見なし（self-attested・要確認）

## あなたが取るアクション
（LLM が平易日本語で記述）

## ACK
- v151 記録残余 5 系統を全消化（T1〜T5）。新規 fail-open 方向の残余なし — 受容残余（混在クォート横断・SIGSTOP >2分窓・PID 再利用）は全て unverified/可用性方向で green 偽装・deny バイパス不能、v152-security.md に明示記録。deny 系 3 hook へのマスク不波及を TestMaskScopeBoundary で契約化、grill A/B が独立に偽装ベクトルなしを実証。証跡 docs/qa-reports/v152-security.md （2026-06-11 19:13）
