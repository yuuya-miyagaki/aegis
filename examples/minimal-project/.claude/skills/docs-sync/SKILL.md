---
name: docs-sync
description: "Document consistency verification for STATUS, LEARNINGS, and project artifacts."
disable-model-invocation: true
user-invocable: false
---

# ドキュメント整合性チェック

> docs フェーズで ship-and-docs skill から参照する。STATUS.md・LEARNINGS.md・
> 成果物参照の整合性を確認し、drift を防止する。

## いつ使うか

- docs フェーズの冒頭（ship-and-docs skill の Step 4 から呼ばれる）
- ドキュメント drift が疑われるとき
- フェーズ完了前の最終確認として

## 整合性チェックリスト

- [ ] STATUS.md の `current_refs` が実ファイルを指している（リンク切れなし）
- [ ] LEARNINGS.md に今回の教訓が反映されている（「該当なし」も明記）
- [ ] plan/spec に記載の受入条件がすべて evidence にリンクしている
- [ ] README / CHANGELOG が変更内容を反映している（該当する場合）
- [ ] マニュアルが該当する案件なら `docs/handover/MANUAL.md` が存在し、front-matter の宣言読者と手順章が1対1（宣言ごとに章があり、宣言の無い孤児章も無い）。該当なしなら理由が記録されている
- [ ] 保守が該当する案件なら `docs/handover/RUNBOOK.md` が存在し、front-matter（product/environment/owners）と必須節（監視/インシデント対応（トリアージ）/エスカレーション/インシデント履歴/用語）が埋まっている。該当なしなら理由が記録されている
- [ ] UAT が該当する案件（ACCEPTANCE あり）なら `docs/handover/UAT-RESULTS.md` が存在し、全 Must-AC に合否・証拠・client サインオフがある。該当なしなら理由が記録されている

## Exit Criteria

- 全チェック項目を実施した
- drift があれば一覧化し、修正 or 残件として記録した
- drift なしの場合も「確認完了、drift なし」と明記した

## 禁止事項

- 未確認の項目を「問題なし」としない
- リンク先を Read/Grep で確認せずに「参照 OK」としない
- チェック結果を省略して「特に問題なし」で済ませない
