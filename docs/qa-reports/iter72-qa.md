# iter72 QA レポート — marker count proof（SF-014 完結編）

- 対象: HEAD（実装 5e10163〜06b4556＋qa fix 8f 未定）／参照: plan `docs/plans/2026-07-16-iter72-count-proof-implementation-plan.md`・review `docs/qa-reports/iter72-review.md`
- 検証方式: 独立 clone（`scratchpad/qa72clone`・本体 HEAD 一致）でのみ mutate/実走。本体 tree read-only。record は clone の --root でのみ実行（本体 evidence-log 非汚染）。

## B1 test-strength drill: sanctioned skip

実装は per-task コミット済み（5e10163〜06b4556）＝qa 承認時の `git diff HEAD` が空になる想定どおりの縁ケース（qa-verification SKILL 145-149・iter64-71 前例）。`.drill` は skip 宣言（reason に代替実証を明記）。代替実証を以下に完遂。

## 機能対照表

| # | plan の機能 | 検証方法 | 判定 |
|---|-----------|---------|------|
| 1 | Stage 5 count proof（executed=passed+failed・skip 除外・≧1） | 変異 M1/M2/M3/M5＋E2E 3/5 | PASS |
| 2 | family veto（検出族で count 0→false） | 変異 M1/M5＋E2E 3 | PASS |
| 3 | 9桁 cap（forged huge count overflow 回避） | 変異 M4 | PASS |
| 4 | strict 5-field parse→malformed rc3（fail-closed） | 変異 M6＋新規 pin | PASS（gap 是正） |
| 5 | MINUS grep rc>1→rc3（M-1 fix） | 変異 M7＋E2E 6 | PASS |
| 6 | vitest all-skip false-GREEN 封鎖（F-2 fix） | 変異 M8＋E2E 3 | PASS |
| 7 | record green の marker/count 必須（rc2 拒否・ログ非書込） | E2E 1/2 | PASS |

## A. clone baseline full suite

| action | expected | observed | verdict |
|---|---|---|---|
| `python3 -m pytest tests/ -p no:cacheprovider -q`（独立 clone） | 全 green | **1290 passed / 3 skipped（253.94s）** | PASS |

既知 flaky=test_update_gate_lock 非発火。対象サブスイート（marker+parity）49 passed OK。

## B. fresh 変異バッテリー（8 種）— 当初 7/8 KILLED → M6 gap 是正で 8/8

各 mutant を独立 clone で1つずつ適用→対象テスト実行→revert。

| # | mutant（marker.sh Stage 5 / patterns.sh） | 結果 | 捕捉テスト |
|---|---|---|---|
| M1 | `family_detected -eq 1`→`0 -eq 1`（veto off） | KILLED | all_skip 系 5 本 |
| M2 | `n=$((n + 10#$num))`→`+0`（EXEC 非計数） | KILLED | 9 本（partial/failed/stray/vitest/jest/cargo/weak/strong） |
| M3 | `n=$((n - m))`→`n + m`（MINUS 反転） | KILLED | unittest_all_skip_false・forged_huge |
| M4 | `num="${num:0:9}"`→cap 除去 | KILLED | forged_huge_count_stays_false_path |
| M5 | `-ge 1`→`-ge 0`（境界） | KILLED | all_skip 系 5 本 |
| **M6** | `nsep -eq 4 \|\| return 3`→`\|\| true`（strict parse off） | **当初 SURVIVED→pin 追加で KILLED** | **新規 `test_malformed_field_count_rc3_not_failopen`** |
| M7 | `mrc -gt 1 && return 3`→`&& true`（MINUS rc guard off） | KILLED | broken_minus_regex_rc3_not_failopen |
| M8 | patterns.sh vitest DETECT の `skipped\|todo` 除去（F-2 回帰） | KILLED | vitest_all_skip_false_closed・detect_fixture_parity |

### M6（Major・qa 検出→fix-forward 済み）

strict field-count guard（`nsep -eq 4`・marker.sh:175）は load-bearing だが当初**無 pin**。親 verify で実証: 4-field（MINUS 欠落）の malformed entry に all-skip 入力→**clean=rc3（fail-closed 正）／guard 除去 mutant=true（fail-OPEN）**。既存 rc3 テストは (a) 配列欠落・(b) 不正 grep regex のみで、区切り数不足の構造 malformed を突いていなかった＝反ガミング moat のテスト網羅性の穴（shipped コードは正しい・回帰保護のみ欠落）。**是正**: `test_malformed_field_count_rc3_not_failopen` 追加（clean で rc3 通過・M6 mutant を KILL することを実測）。

## C. 実環境 E2E（clone 内・6/6 PASS）

| # | 操作 | expected | observed | verdict |
|---|------|----------|----------|---------|
| 1 | unittest all-skip（2×`@skip`）→ record --root=clone | rc2・ログ非書込 | rc2・log 1→1（非書込）・positive proof 拒否メッセージ | PASS |
| 2 | unittest 混在（1 skip 1 pass）→ record | green・marker:true | recorded: green rc0・log 1→2・`"marker": true` | PASS |
| 3 | vitest all-skip fixture（`Test Files 1 passed`+`Tests 3 skipped`） | false | false rc0 | PASS |
| 4 | banner+go（`===== finished in 3.21s =====`+`ok pkg dur`） | true | true rc0 | PASS |
| 5 | unittest stray `skipped=5`（body 印字）+ 実 `Ran 3 OK` | true | true rc0 | PASS |
| 6 | broken unittest MINUS（不正 regex）+ all-skip（clone のみ・revert 済み） | rc3（fail-closed） | `grep: parentheses not balanced`→rc3 | PASS |

## D. 本体 full suite（marker+parity 再走）

M6 pin 追加後: `python3 -m unittest tests.test_marker_lib tests.test_patterns_parity` → **50 tests OK**。

## claims

```claims
tests_pass: true
no_stubs: true
verdict: approve
mutation: 8/8 KILLED（M6 gap は pin 追加で是正）
e2e: 6/6 PASS
baseline_clone: 1290 passed / 3 skipped
qa_finding: M6（strict field-count guard 無 pin・Major・shipped コードは正・fix-forward 済み）
```

## Verdict

**qa PASS（approve）**。Stage 5 count proof は 6/6 E2E で正しく動作。変異バッテリーは当初 7/8 KILLED、唯一の survivor M6（strict field-count guard の無 pin）を親 verify で「shipped コードは fail-closed 正・回帰保護のみ欠落」と切り分け、`test_malformed_field_count_rc3_not_failopen` を追加して 8/8 KILLED に是正。ブロッカーなし。残余（SF-014 (a)(b)(c)・SF-015）は marker 層天井・drill subsume。
