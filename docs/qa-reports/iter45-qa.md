# iter45 QA Report — C2 setup arg parser / C3 version heredoc

- 日付: 2026-06-25
- task_type/size: framework / M（qa 必須）
- qa 証拠: 本ファイル（可読 QA ドキュメント・claims 付き）／B1 ドリル結果は `docs/qa-reports/test-strength.md`
- 参照: plan `docs/plans/2026-06-25-iter45-setup-arg-version-implementation-plan.md` / review `docs/qa-reports/iter45-review.md`

## 機能対照表（plan の機能 → 検証）

| # | plan の機能 | 検証対象（`tests/test_setup_arg_version.py`） | 検証方法 | 判定 |
|---|-----------|---------------------------------------------|---------|------|
| 1 | C2 `--profile`/`--target` 両形式（=/空白） | `test_space_form_profile_and_target` / `test_mixed_form` / `test_target_space_form_alone` / `test_equals_form_still_works` | pytest（RED-first 実測済） | PASS |
| 2 | C2 値欠落 fail-closed・決定的メッセージ | `test_profile_missing_value_fails_with_clear_message` | pytest | PASS |
| 3 | C2 不明引数 fail-closed（回帰） | `test_unknown_arg_still_fails` | pytest | PASS |
| 4 | C2 value-mistake（`--profile --force`）fail-closed | `test_profile_consumes_flag_lookalike_then_fails_validation` | pytest | PASS |
| 5 | C2 明示空値 fail-closed | `test_profile_explicit_empty_value_fails_closed` | pytest | PASS |
| 6 | C2 `--force` 無限ループなし | `test_force_flag_does_not_hang` | pytest（timeout=60） | PASS |
| 7 | C2 `--help` rc0 + 空白形式ヒント | `test_help_exits_zero_with_usage` | pytest | PASS |
| 8 | C3 heredoc argv（静的 dead-path 除去） | `test_heredoc_uses_argv_not_framework_root_var` | pytest | PASS |
| 9 | C3 python 主経路が実値（positive-control） | `test_python_primary_path_resolves_version` | pytest | PASS |
| 10 | C3 実 install で stamp==実 version（回帰） | `test_real_install_stamps_actual_version` | pytest | PASS |

実装漏れなし（全機能に検証対象が存在）。

## エビデンス

- テストスイート: full suite **green**（`record-test-result.py` で記録・fingerprint bound）。新規 test: **13 passed**（`tests/test_setup_arg_version.py`）。
- `bash -n bin/setup.sh` → OK。空白形式 smoke（`--profile full --target <mktemp>`）→ rc 0・stamp `1.14.0`。
- lint/type-check/build: 該当なし（bash installer + python test）。
- 依存追加: ゼロ（python3/bash/git の既存依存のみ）。

## テスト強度ドリル（B1・mutation）

`docs/qa-reports/test-strength.drill` に 4 mutant を定義し実走（`run-test-strength-drill.py`）。未コミットの追加実行行が明確で、テストが実 `bin/setup.sh` を subprocess 実走するため**本物の mutation drill が成立**:

| # | 変異対象（追加行） | 変異 | 壊す振る舞い | 捕捉テスト |
|---|------------------|------|------------|-----------|
| 1 | `bin/setup.sh:54` `[ $# -ge 2 ]` guard | `-ge 2` → `-ge 1` | `--profile` 値欠落の fail-closed | `test_profile_missing_value_…`（unbound→メッセージ不一致で RED） |
| 2 | `bin/setup.sh:63` help hint echo | テキスト → `MUTANT` | `--help` の空白形式ヒント | `test_help_exits_zero_with_usage` |
| 3 | `bin/setup.sh:67` unknown-arg echo | `Unknown argument` → `MUTANT` | 不明引数メッセージ | `test_unknown_arg_still_fails` |
| 4 | `bin/setup.sh:118` argv read | `sys.argv[1]` → `"/dev/null"` | python 主経路が実値を返す | `test_python_primary_path_…` / `test_heredoc_uses_argv_…` |

結果: **DRILL PASS — all 4 mutants caught**（プレビュー実走で確認・承認時にハーネスが再実走）。
mutant #4 は C3 の核心（dead first path 解消）を直接守る: argv を潰すと grep フォールバックの誤値が漏れ positive-control が RED 化する。

## 判定

**PASS。** 全 10 機能 PASS・B1 ドリル PASS（4 mutant caught）・full suite green・依存追加ゼロ。ブロッカーなし。

```claims
tests_pass: true
no_stubs: true
verdict: approve
b1_drill: PASS (4 mutants caught)
```
