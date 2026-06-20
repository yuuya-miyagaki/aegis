# M4 QA レポート（iteration 33）

対象: 観測 hook の fingerprint/marker を hot-path から外す（commits `457f632..HEAD`）。

## 多層検証（全緑）

| 層 | コマンド | 結果 |
|----|---------|------|
| pytest | `python3 -m pytest -q` | 998 passed / 1 skipped |
| contract | `python3 scripts/check_framework_contract.py` | PASS（1.12.0 整合） |
| Tier1 | `python3 scripts/run_eval.py --tier 1` | PASS（check_status/status_doctor/contract/reference_drift） |
| scaffold smoke | `python3 scripts/eval_scaffold_smoke.py` | PASS（minimal/standard/full） |
| REDTEAM PoC | `bash tests/poc/v162-redteam-rerun.sh` | 18/18 passed（marker forge 防御不変） |
| 想定外参照 | `grep -rn is_test_runner_cmd …` | 空（定義＋想定呼出元のみ） |

baseline（着手前 992 passed）→ 実装後 998 passed（新規6＝is_test_runner 2・append 2・不変条件ガード 1・パリティ 1）。回帰ゼロ。

## B1 テスト強度ドリルの扱い（skip 宣言＋代替実証）

run-test-strength-drill.py は**未コミットのプロダクトコード追加行**を mutate する設計。本タスクは全変更を per-task commit 済み（working-tree diff 空）＝B1 の構造的適用不能（iteration 30/31 と同じ縁ケース）。代替のテスト強度実証:

- **RED 実証（TDD）**: `test_non_runner_cmd_skips_fingerprint` を実装前に RED（`65b2…hex != skipped`）→実装後 GREEN。`TestIsTestRunnerCmd` も RED（空 stdout）→GREEN。＝テストが対象挙動の不在を検知することを実証。
- **mutation 同等**: `test_fixtures_is_test_runner_cmd`（40+ 形）は分類器が1形でも分岐すれば即 FAIL＝単一 sed/grep への変異を捕捉。`'"echo" pytest'→False` は「置換→削除」変異を RED で封鎖（既存 fixture）。
- **REDTEAM 18/18**: marker forge（`pytest -k __NEVER__ + echo`→false）が M4 後も fail-closed。

## 判定: PASS

```claims
verdict: approve
tests_pass: true
no_stubs: true
b1_drill: skip_with_manual_evidence
```
