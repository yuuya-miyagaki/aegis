# v1.3.3 deploy チェックリスト（2026-06-10）

リリース形態: フレームワーク repo の patch リリース（コミット + tag `v1.3.3`、外部インフラなし）

## デプロイ前ゲート確認

- [x] review approved（docs/qa-reports/v133-review.md、--ack 理由は judge-review.md）
- [x] qa approved（docs/qa-reports/v133-qa.md。B1 ドリルは構造的制約によりスキップ宣言＝test-strength.drill に理由全文、LEARNINGS に所見記録）
- [x] security approved（docs/qa-reports/v133-security.md、残余リスクは v133-review.md「残余リスク」節に記録済み）
- [x] git config user.email 確認（リポジトリ既定のまま、push なしのローカルリリース）

## バージョン同期（リリース内容）

| 対象 | 変更 |
|------|------|
| `scripts/check_framework_contract.py` | FRAMEWORK_VERSION "1.3.2" → "1.3.3" |
| `templates/STATUS.template.md` | framework_version "1.3.2" → "1.3.3" |
| `docs/STATUS.md` | framework_version "1.3.2" → "1.3.3" |
| `README.md` | Migration 節「From v1.3.2 to v1.3.3」追加（既存プロジェクトへの hook 2 本差し替え案内） |
| `docs/architecture-overview.md` | 版表記 v1.3.3・バージョン履歴に v1.3.3 行を追加 |

## バンプ後の最終検証（本セッション実走）

| 検証 | 結果 |
|------|------|
| `python3 -m unittest discover -s tests` | **332 tests OK** |
| `check_framework_contract.py --profile=full` | PASS |
| `check_framework_contract.py --root examples/minimal-project --profile=standard` | PASS |
| `check_reference_drift.py` | PASS（mirror byte 同一含む） |
| `eval_scaffold_smoke.py` | PASS（minimal/standard/full、B-4/B-5 実発火シール含む） |

## SemVer 判定

patch（1.3.2 → 1.3.3）。運用契約に変更なし。挙動変更は「install 先での過剰 deny の解消」のみで、
防御方向の変更（deny→allow の新設経路）はバイパス探索表（v133-security.md）で全 deny 維持を確認済み。

## 残作業

- tag `v1.3.3` 作成（コミット後）
- origin への push は別途ユーザー判断（v1.3.2 は push 済み、以降のコミットは未 push）
