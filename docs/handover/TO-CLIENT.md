# 納品サマリー — iteration 56（v1.17.0）

> 本タスクは Aegis フレームワーク自身の改善（M2 ドッグフード由来）。「client」＝
> フレームワーク保守者（次に aegis を使う自分自身）。外部クライアントへの製品納品ではない。

## 何を作ったか

M2 ドッグフード（yoga-tsukinowa-lp 二周目）で観測した摩擦6件＋可視性2件を反映。

| # | テーマ | 主な変更 |
|---|--------|---------|
| ① | secrets hook の先頭ドット誤検知 | `.env.example`/`.gitignore` の個別 add を解放（broad 判定を否定クラス＋グロブ考慮に） |
| ② | drill skip 経路の claims 契約矛盾 | qa ref を claims 付き QA レポートに統一（skill×judge を整合） |
| ③ | verdict 名目差の 🟡 形骸化 | approve×approve_with_notes は 🟡 抑止＋notes 情報行。未記入は値不正 🟡 |
| ④ | 並行テストの共有資源衝突 | subagent-dev に共有可変資源ルール（integration は同時1体） |
| ⑤ | spec-delta 合格の無言 | 承認ログに肯定1行を出力 |
| ⑥ | full プロファイル配布漏れ | 未配布スクリプト追加＋contract 方向4＋install 実在検証 |
| ⑦ | 可視性 | judge 未検証文言に是正手順・gate テンプレに claims 雛形 |

## 主要な設計判断

- moat 緩和（①）は「具体的な個別ドットファイル名のみ解放」＝グロブ・複合区切りは deny 維持
  （否定クラス＋グロブ節。`.env` 直接検査は独立に不変）。
- 配布整合（⑥）の意図的非同梱は full.json の `intentional_unshipped`（理由必須）で
  自己記述＝テストとプロファイルの二重管理を最小化。
- 値検査（③⑦）は claims 存在時に全ゲート常時＝未記入テンプレの沈黙通過を封鎖。

## 変更ファイル一覧

- hook: `hooks/check-secrets.sh`
- scripts: `scripts/build-judge-card.py`・`scripts/check_status.py`・`scripts/check_framework_contract.py`
- 配布: `templates/profiles/full.json`・`templates/{QA-REPORT,REVIEW,SECURITY-REVIEW}.template.md`・`templates/STATUS.template.md`
- skill: `.claude/skills/qa-verification/SKILL.md`・`.claude/skills/subagent-dev/SKILL.md`
- テスト: 新規3ファイル＋既存5ファイル拡張
- version: v1.16.0 → v1.17.0（minor: 後方互換の判定緩和＋可視性強化）

## テスト・QA・セキュリティ結果の要約（証拠参照）

- テスト: full suite **1322 passed / 3 skipped**（+8 新規）・`docs/qa-reports/iter56-qa.md`
- レビュー: 10並列ファインダー＋盲検2次（approve_with_notes → 指摘全解消）・`docs/qa-reports/iter56-review.md`
- セキュリティ: moat バイパスを実 repo で実測（全 deny 維持）・盲検2次が add-moat 回帰
  （先頭ドットグロブ）を検出→修正済み・`docs/qa-reports/iter56-security.md`
- deploy: install 契約検証済み（外部デプロイなし）・`docs/qa-reports/iter56-deploy.md`
- 決定論検査: contract/status/drift/lint/budget すべて PASS

## 残留リスク・既知の制限事項

- check-secrets 否定クラスの残穴: `.~x`・`.@foo` 等（2文字目が非パス文字の先頭ドット
  ファイル）は broad 誤検知＝deny 側（安全方向）。`git add -- <file>` で回避可・コードに Known residual 明記。
- full.json `intentional_unshipped` と test 側 `INTENTIONAL_UNSHIPPED` の2レジストリは
  用途が異なるが概念的に近い。双方に staleness トリップワイヤあり。統合は iter56 後の構造リアーキ候補。

## 運用上の注意点

- 既存 install は `bin/setup.sh` 再実行で改善版 hook/プロファイルに更新される。
- gate テンプレの ```claims 雛形は `<記入>` を必ず埋める（未記入は judge が 🟡 で弾く）。
- qa ref は今後 claims 付き QA レポートを指す（test-strength.md ではない）。
- ロールバック: iter56 コミット群の revert で完全復元（状態移行なし）。

## 操作マニュアル / 運用 RUNBOOK / UAT

- **MANUAL: 生成せず** — エンドユーザー製品ではなくフレームワーク（利用者＝保守者自身）。
- **RUNBOOK: 生成せず** — 運用者なし（CI 相当は contract/drift の機械検査）。
- **UAT: 生成せず** — `docs/requirements/ACCEPTANCE.md` なし（受入基準を要する外部案件ではない）。
