---
description: Preview the judge card for the current/specified gate (read-only)
allowed-tools: Bash, Read
---

# /judge

非エンジニア向けの judge カードをプレビューする（承認はしない）。

1. 引数があればそのゲート、無ければ `docs/STATUS.md` の phase から対象ゲートを決める:
   - phase が review/qa/security/deploy → そのゲート
   - フェーズ間（implement 等）→ 次に控える judge ゲート（implement→review）
2. 実行: `python3 scripts/build-judge-card.py --gate <gate> --root .`
3. 生成された `docs/qa-reports/judge-<gate>.md` を読んで提示し、🔴/🟡/🟢 と
   「あなたが取るアクション」を平易日本語で説明する（判定は機械が決定済み）。
