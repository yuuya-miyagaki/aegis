# v1.5.0 deploy チェックリスト（2026-06-11）

リリース形態: フレームワーク repo の minor リリース（コミット + tag `v1.5.0`、外部インフラなし）

## デプロイ前ゲート確認

- [x] review approved（docs/qa-reports/v150-review.md、grill-code=マージ可・🔴1/🟡4 件は修正済み）
- [x] qa approved（docs/qa-reports/v150-qa.md、436 tests OK・RED→GREEN 来歴記録済み）
- [x] security approved（docs/qa-reports/v150-security.md、変化点は全て強化/可視化方向・受容リスクは設計明示）
- [x] push なしのローカルリリース（origin push は別途ユーザー判断）

## バージョン同期（リリース内容）

| 対象 | 変更 |
|------|------|
| `scripts/check_framework_contract.py` | FRAMEWORK_VERSION "1.4.0" → "1.5.0" |
| `templates/STATUS.template.md` | framework_version → "1.5.0" |
| `examples/minimal-project/docs/STATUS.md` | framework_version → "1.5.0" |
| `docs/STATUS.md` | framework_version → "1.5.0" |
| `README.md` | Migration 節「From v1.4.0 to v1.5.0」追加（evidence-log 化・test-result.json 廃止・新規配布物 3 ファイル・setup.sh 再実行・生存チェック） |
| `docs/architecture-overview.md` | 版表記 v1.5.0・バージョン履歴に v1.5.0 行を追加（deploy 段で是正、v1.4.0 と同パターン） |

## バンプ後の最終検証（本セッション実走、grill 修正後）

| 検証 | 結果 |
|------|------|
| `python3 -m unittest discover -s tests` | **436 tests OK** |
| `check_framework_contract.py` | PASS |
| `check_reference_drift.py` | PASS（mirror byte 同一含む） |
| `eval_scaffold_smoke.py` | PASS（minimal/standard/full、E1 観測系の成功側＋失敗側実発火含む） |

## SemVer 判定

minor（1.4.0 → 1.5.0）。運用契約への追加: evidence-log 観測（PostToolUse/Bash observer）、
judge card テスト行の観測ベース判定、TaskCompleted の observer 生存チェック、
`record-test-result.py` の手動フォールバック化（コマンドを信頼実行して記録）。
`test-result.json` 廃止は内部機構の置換（公開契約=運用契約は不変、judge の見え方は tri-state のまま）。
破壊的変更なし（既存 install は setup.sh 再実行で新 hook/lib を取得、未更新でも判定が unverified に倒れるだけで fail-open しない）。

## 残作業

- tag `v1.5.0` 作成（最終コミット後）
- origin への push は別途ユーザー判断
- 旧 `docs/qa-reports/test-result.json`（未追跡の残骸）の削除はユーザー確認後
