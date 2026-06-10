# v1.4.0 deploy チェックリスト（2026-06-10）

リリース形態: フレームワーク repo の minor リリース（コミット + tag `v1.4.0`、外部インフラなし）

## デプロイ前ゲート確認

- [x] review approved（docs/qa-reports/v140-review.md、grill-code=マージ可・🟡2件は修正済み）
- [x] qa approved（docs/qa-reports/v140-qa.md、389 tests OK・RED→GREEN 来歴記録済み）
- [x] security approved（docs/qa-reports/v140-security.md、防御強度の変化点は全て強化/可視化方向）
- [x] push なしのローカルリリース（origin push は別途ユーザー判断）

## バージョン同期（リリース内容）

| 対象 | 変更 |
|------|------|
| `scripts/check_framework_contract.py` | FRAMEWORK_VERSION "1.3.3" → "1.4.0"（example STATUS との同期チェック新設） |
| `templates/STATUS.template.md` | framework_version "1.3.3" → "1.4.0" |
| `examples/minimal-project/docs/STATUS.md` | framework_version → "1.4.0" |
| `docs/STATUS.md` | framework_version → "1.4.0"（本チェックリストと同コミット） |
| `README.md` | Migration 節「From v1.3.3 to v1.4.0」追加（standard ガード4種・deploy gate 拡大・env 改名・settings 再生成・failure policy 表） |
| `docs/architecture-overview.md` | 版表記 v1.4.0・バージョン履歴に v1.4.0 行を追加（T16 で漏れ、deploy 段で是正） |

## バンプ後の最終検証（本セッション実走、b448c01 時点）

| 検証 | 結果 |
|------|------|
| `python3 -m unittest discover -s tests` | **389 tests OK** |
| `check_framework_contract.py` | PASS |
| `check_reference_drift.py` | PASS（mirror byte 同一含む） |
| `check_status.py --strict` | PASS |
| `eval_scaffold_smoke.py` | PASS（minimal/standard/full） |

## SemVer 判定

minor（1.3.3 → 1.4.0）。運用契約への追加: standard プロファイルの Bash ガード4種、
deploy gate の ask 経路（RC=2＋`ASK:`）、`AEGIS_PRECOMPACT_INTERVAL`（旧名は本リリース限定 fallback）、
settings の hook 参照形式変更（`"${CLAUDE_PROJECT_DIR:-.}"`、setup.sh 再実行で移行）。
破壊的変更なし（旧形式は移行ガイドで案内、fallback 維持）。

## 残作業

- tag `v1.4.0` 作成（最終コミット後）
- origin への push は別途ユーザー判断（v1.3.2 以降のコミットが未 push）
