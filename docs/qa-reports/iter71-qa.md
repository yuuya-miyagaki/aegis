# iter71 QA レポート — marker positive proof（SF-014 恒久策）

- 対象: HEAD=aa0c692（実装 9dc77b1＋review docs）
- 参照: plan `docs/plans/2026-07-15-iter71-marker-positive-proof-implementation-plan.md`／review `docs/qa-reports/iter71-review.md`
- 検証方式: 独立 clone（`scratchpad/qa71clone`・HEAD 一致）でのみ mutate/実走。本体 tree read-only（検証後 `git status --porcelain` 空を確認）。

## B1 test-strength drill: sanctioned skip

実装は per-task コミット済み（037545c〜9dc77b1）＝qa 承認時の `git diff HEAD` が空になる想定どおりの縁ケース（qa-verification SKILL 145-147・iter64-70 前例）。代替実証を以下に完遂。`.drill` は skip 宣言（reason に代替実証を明記）。

## 機能対照表

| # | plan の機能 | 検証方法 | 判定 |
|---|-----------|---------|------|
| 1 | marker.sh 4段検証コア（挙動不変抽出） | 変異 M1/M2＋review byte 一致 | PASS |
| 2 | record green の marker 必須（rc2 拒否・ログ非書込） | E2E C1/C2＋変異 M3/M4 | PASS |
| 3 | record red は marker 不要 | review R5＋full suite | PASS |
| 4 | drill baseline no-test-proof BLOCKED | E2E C4＋変異 M5 | PASS |
| 5 | 64KiB×末尾 marker（verdict は全文） | review R7 | PASS |
| 6 | patterns.sh リテラル TAB（cross-engine） | 変異 M6＋parity テスト | PASS |

## A. clone baseline full suite

| action | expected | observed | verdict |
|---|---|---|---|
| `python3 -m pytest tests/ -q`（独立 clone） | 全 green | **1271 passed / 3 skipped（251.26s）** | PASS |

（本体 full suite も fix-forward 後 1272 passed/2 skipped/0 failed を実測済み＝review 脚注。skip 数の微差は環境依存の flaky skip 判定・fail なし。）

## B. fresh 変異バッテリー（反ガミング契約の殺傷力）— 全6 KILLED

各 mutant を独立 clone で1つずつ適用→対象テスト実行→revert。

| mutant | 内容 | 結果 | 捕捉テスト |
|---|---|---|---|
| M1 | marker.sh Stage4 Axis1 zero-run ループ空振り | KILLED | `test_marker_lib.py` M11 (forged_strong_plus_collected0) |
| M2 | WEAK pair companion 要件除去 | KILLED | `test_marker_lib.py` test_weak_half_false |
| M3 | record green-gate バイパス | KILLED | `test_record_test_result.py` test_npm_true_green_rejected |
| M4 | record DrillError fail-open | KILLED | `test_record_test_result.py` test_marker_lib_missing_fail_closed |
| M5 | drill check_baseline の marker 要求除去 | KILLED | `test_test_strength_drill.py` test_green_without_marker_is_no_test_proof |
| M6 | patterns.sh go marker の TAB を `\t` へ回帰 | KILLED | `test_marker_lib.py` M10 (go_marker_true) |

**survivor 切り分け**: M2 の対称変異（anchor 要件除去・companion だけで hit）は当初 survivor に見えたが、`test_companion_only_false`（入力 `OK\n`）が KILL することを追試で実測（rc1）。WEAK pair は「anchor 除去→companion-only テスト」「companion 除去→weak_half テスト」の二層で両方向被覆＝**subsumed（真の穴でない）**。

## C. 実環境 E2E（clone 内・使い捨て tmp git repo）

| # | 操作 | rc | 実測 | 判定 |
|---|------|----|------|------|
| C1 | `record "python3 -m unittest discover -p 'nomatch*'"` | rc2 | evidence-log 不生成・stderr に positive proof 案内 | PASS |
| C2 | `record "python3 -m pytest -q tests/"` | rc2 | 不生成・stderr に「`-q` を外して」案内 | PASS |
| C3 | `record "python3 -m pytest tests/"`（-q なし・trivial pass） | rc0 | `recorded: green`・エントリに `"marker": true` | PASS |
| C4 | 非ランナー `python3 -c "import m"` の .drill を drill 実走 | rc1 | `DRILL BLOCKED (baseline no-test-proof)`・report に `baseline: no-test-proof` | PASS |

## 残余（qa 非ブロック・iter72 トラック）

F-A（unittest/go all-skip suite が marker true→green）は pre-existing・contained（drill が subsume＝all-skip baseline は mutant を殺せず FAIL）。SF-014 の恒久策（passed/failed 実数カウント proof）へ。qa の変異バッテリーでも「all-skip baseline は drill を通らない」を M5/C4 経路で裏付け。

## 判定

**qa verdict: PASS**。baseline green・反ガミング6 mutant 全 KILL（対称変異も subsumed）・record 4経路と drill baseline が実環境で fail-closed・本体 tree 無変更。

```claims
tests_pass: true
no_stubs: true
verdict: approve
```
