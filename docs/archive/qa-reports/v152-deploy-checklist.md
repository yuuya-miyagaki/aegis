# v1.5.2 deploy チェックリスト（2026-06-11）

リリース形態: フレームワーク repo の patch リリース（コミット + tag `v1.5.2`、外部インフラなし）

## デプロイ前ゲート確認

- [x] review approved（docs/qa-reports/v152-review.md、grill-code 独立 2 本=マージ可・🟡1/🟢6 全対応または理由付き記録）
- [x] qa approved（docs/qa-reports/v152-qa.md、479 tests OK・RED→GREEN 来歴記録済み）
- [x] security approved（docs/qa-reports/v152-security.md、v151 記録残余 5 系統の全消化・受容残余は明示記録）
- [x] push なしのローカルリリース（origin push は別途ユーザー判断）

## バージョン同期（リリース内容）

| 対象 | 変更 |
|------|------|
| `scripts/check_framework_contract.py` | FRAMEWORK_VERSION "1.5.1" → "1.5.2" |
| `templates/STATUS.template.md` | framework_version → "1.5.2" |
| `examples/minimal-project/docs/STATUS.md` | framework_version → "1.5.2" |
| `docs/STATUS.md` | framework_version → "1.5.2" |
| `README.md` | Migration 節「From v1.5.1 to v1.5.2」追加（T1 クォート言及の unverified 方向変化・T2〜T5） |
| `docs/architecture-overview.md` | 版表記 v1.5.2・バージョン履歴に v1.5.2 行を追加 |

## バンプ後の最終検証（本セッション実走、grill 修正後 = b79184a 時点）

| 検証 | 結果 |
|------|------|
| `python3 -m unittest discover -s tests` | **479 tests OK** |
| `check_framework_contract.py`（本体/example standard） | PASS / PASS |
| `check_reference_drift.py` | PASS（mirror byte 同一含む） |
| `eval_scaffold_smoke.py` | PASS（minimal/standard/full） |
| `check_status.py --strict` | PASS |

## SemVer 判定

patch（1.5.1 → 1.5.2）。運用契約（ゲート遷移・judge tri-state・hook 構成・配布物）への
追加・変更なし。内容は誤判定根治（クォート内言及の false-RED）・記録忠実度（`\/`）・
ロック自己修復（孤児 claim 復元＋O_EXCL 採用）・可用性（待機窓 10s）のみ。
light ゲート競合時の敗者挙動変化（rc=1 → 待機後自己取得で rc=0）は意図的是正で、
heavy ゲートの前提未承認 rc=1 は不変。クォート内ランナー起動形（`'"echo" pytest'` 等）が
green 偽装不能の unverified 方向へ倒れる変化は README Migration に利用者向け注意を記載。
破壊的変更なし。

## 残作業

- origin push（ユーザー判断）
