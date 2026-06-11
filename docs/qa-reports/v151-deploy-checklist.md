# v1.5.1 deploy チェックリスト（2026-06-11）

リリース形態: フレームワーク repo の patch リリース（コミット + tag `v1.5.1`、外部インフラなし）

## デプロイ前ゲート確認

- [x] review approved（docs/qa-reports/v151-review.md、grill-code 独立 2 本=マージ可・🟡1/🟢6 全対応）
- [x] qa approved（docs/qa-reports/v151-qa.md、461 tests OK・RED→GREEN 来歴記録済み）
- [x] security approved（docs/qa-reports/v151-security.md、v140/v150 記録残余 5 系統の解消・受容/残余リスクは明示記録）
- [x] push なしのローカルリリース（origin push は別途ユーザー判断）

## バージョン同期（リリース内容）

| 対象 | 変更 |
|------|------|
| `scripts/check_framework_contract.py` | FRAMEWORK_VERSION "1.5.0" → "1.5.1" |
| `templates/STATUS.template.md` | framework_version → "1.5.1" |
| `examples/minimal-project/docs/STATUS.md` | framework_version → "1.5.1" |
| `docs/STATUS.md` | framework_version → "1.5.1" |
| `README.md` | Migration 節「From v1.5.0 to v1.5.1」追加（T1 分類挙動変化・ラッパー形の注意・T2〜T5） |
| `docs/architecture-overview.md` | 版表記 v1.5.1・バージョン履歴に v1.5.1 行を追加 |

## バンプ後の最終検証（本セッション実走、grill 修正後）

| 検証 | 結果 |
|------|------|
| `python3 -m unittest discover -s tests` | **461 tests OK** |
| `check_framework_contract.py`（本体/example standard） | PASS / PASS |
| `check_reference_drift.py` | PASS（mirror byte 同一含む） |
| `eval_scaffold_smoke.py` | PASS（minimal/standard/full） |
| `check_status.py --root . --strict` | PASS |

## SemVer 判定

patch（1.5.0 → 1.5.1）。運用契約（ゲート遷移・judge tri-state・hook 構成・配布物）への
追加・変更なし。内容は防御強化（find 書込形 deny・TOCTOU/ロック）と誤判定緩和
（false-RED・false-deny・stderr 混入）のみ。テストランナー分類の挙動変化
（引数言及の非分類化）は意図的な是正で、unverified 方向＝fail-closed を維持
（README Migration に利用者向け注意を記載）。破壊的変更なし。

## 残作業

- origin push（ユーザー判断）
