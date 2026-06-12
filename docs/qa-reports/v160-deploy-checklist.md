# v1.6.0 deploy チェックリスト（2026-06-12）

リリース形態: フレームワーク repo の minor リリース（コミット + tag `v1.6.0`、外部インフラなし）

## デプロイ前ゲート確認

- [ ] review approved（docs/qa-reports/v160-review.md、grill-code 独立 2 本＝マージ可・合流点 S1 は a8411fb で充足・Critical 0）
- [ ] qa approved（docs/qa-reports/v160-qa.md、508 tests OK・RED→GREEN 来歴記録済み）
- [ ] security approved（docs/qa-reports/v160-security.md、deny/block 緩和ゼロ・受容残余 9 件明示記録）
- [ ] push なしのローカルリリース（origin push は別途ユーザー判断）

## バージョン同期（リリース内容）

| 対象 | 変更 |
|------|------|
| `scripts/check_framework_contract.py` | FRAMEWORK_VERSION "1.5.2" → "1.6.0" |
| `templates/STATUS.template.md` | framework_version → "1.6.0" |
| `examples/minimal-project/docs/STATUS.md` | framework_version → "1.6.0" |
| `docs/STATUS.md` | framework_version → "1.6.0" |
| `README.md` | Migration 節「From v1.5.2 to v1.6.0」追加（P1-A 注入の advisory 性質・path 形式起動・card push・client 検査・vendor 除外） |
| `docs/architecture-overview.md` | 版表記 v1.6.0・バージョン履歴に v1.6.0 行を追加 |

## バンプ後の最終検証（本セッション実走、grill 修正後 = a8411fb 時点）

| 検証 | 結果 |
|------|------|
| `python3 -m unittest discover tests/` | **508 tests OK** |
| `check_framework_contract.py`（本体/example standard） | PASS / PASS |
| `check_reference_drift.py` | PASS（mirror byte 同一・skill 到達性含む） |
| `run_eval.py --tier 0/1/2/3` | PASS / PASS (with warnings) / PASS / PASS |
| `check_status.py --strict` | PASS |

## SemVer 判定

minor（1.5.2 → 1.6.0）。機能追加＝phase 必読 skill の構造起動（SessionStart／phase 遷移の
advisory 注入＋到達性契約）、full への テンプレート 6 件配布、judge card の承認時 transcript
push、client_ready_for_dev の成果物対称検査、scanner の decode 耐性、drill の vendor 除外。
既存の運用契約（ゲート遷移・judge tri-state・deny/block 系 hook の挙動）に破壊変更なし。
注入は additionalContext（advisory）のみで、未対応クライアントでも従来動作が維持される。
新設の到達性・テンプレ参照チェックは framework 開発側の契約（drift／smoke）であり、
install 先プロジェクトの実行時挙動には影響しない。
