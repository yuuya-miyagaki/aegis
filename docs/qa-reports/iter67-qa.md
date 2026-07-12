# iter67 QA レポート — judge test-fact 判定堅牢化（trust-scan）

- **対象**: `d2c4dd6..HEAD`（実装 7c0829d/2f5eaaa/6a4c0ef＋fix-forward 70ace79/0739a79）
- **review**: approved（docs/qa-reports/iter67-review.md・judge 🟢）
- **ui_surface**: false（qa-browser 委譲なし）
- **判定**: **PASS**

## 実施体制の注記

qa 一次は qa agent へ委譲したが、サブエージェントは plan mode 制約（非 readonly
手順にユーザー本人の解除が必要）で実行不能と報告（scoped 99 passed の先行実測と
実行計画のみ返却）。残項目（機能対照表・M1-M5・E2E）は**親セッション（fable）が
同一手順を直接実行**した。検証内容は委譲プロンプトと同一。

## 機能対照表（要件/plan → 検証対象 → 検証方法 → 判定）

| # | 要件/plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|----------------|---------|---------|------|
| 1 | 罠の根切り（noise が trusted green を破壊しない） | read_test_result trust-scan 分岐 | 系列テスト #1/2/6/9＋実環境 E2E 差分（下記） | PASS |
| 2 | red 洗浄経路の封鎖（厳格化） | 同上 | 系列テスト #3＋review 角度B C1-C7 実走 | PASS |
| 3 | undecidable-fail 終端 unverified 維持 | 同上 | 系列テスト #4＋3段系列（fix-forward 70ace79）＋M3 kill | PASS |
| 4 | fp backstop 無緩和 | 同上 | 系列テスト #5/#10＋既存 stale ピン2件＋M5 kill | PASS |
| 5 | decidable ゼロ→unverified（silent-green 下限） | 同上 | 系列テスト #8＋M1 kill | PASS |
| 6 | rotated `.1` 跨ぎ | 同上 | 系列テスト #9 | PASS |
| 7 | docstring/guidance 同期 | build-judge-card docstring・architecture-overview.md | review 角度A/D＋盲検 F1/F3 fix-forward 済 | PASS |
| 8 | 既存意味論の保存（単一エントリ・decidable-stale 終端） | 既存ピン群 | scoped 99 passed（既存23＋judge_card 65 含む） | PASS |

実装漏れなし（plan 全タスク＋fix-forward 2 件まで写像済み）。

## テスト強度（B1 drill＝sanctioned skip＋代替実証）

働き tree は per-task コミット済みで diff 空＝skip 宣言（`test-strength.drill`・
qa-verification skill 137-141・iter64 conf7 経路）。代替実証:

### qa 一次 fresh 変異 M1-M5（独立 scratch clone・scoped 99 テスト）

| 変異 | 内容 | 結果 | 代表 kill テスト |
|------|------|------|----------------|
| M1 | `src == "observed"` → `!=`（undecidable 述語反転） | **9 failed** | manual 信頼系＋noise-only＋透明化系 |
| M2 | `is not True` → `is not False`（marker 弱体化） | **19 failed** | marker=true green/red 系全滅 |
| M3 | undecidable-fail 終端 2 行削除 | **2 failed** | `test_undecidable_fail_stays_terminal_unverified`・`test_transparency_does_not_skip_undecidable_fail`（fix-forward テストに歯） |
| M4 | green/red 入替 | **21 failed** | 単一エントリピン含む全域 |
| M5 | fp backstop 2 行削除 | **3 failed** | `test_transparency_does_not_resurrect_stale_green`・`test_newest_stale_does_not_fall_back_to_older_fresh`・`test_stale_fp_is_unverified` |

**5/5 kill**（生き残りゼロ）。grill-code の変異 2 種（status 限定除去→#4 単独 kill／
fp 順序退行→#10 単独 kill）と合わせ、trust-scan 分岐の全構成要素に歯を実証。

### 実環境 E2E 差分実証（罠シナリオの dogfood 再現）

- 前提: record-test-result による manual green が evidence-log に存在（review 締めで記録・以後 docs-only 変更＝fp 不変）
- 操作: `python3 -m pytest --collect-only -q 2>&1 | tail -1`（**iter64/65/66 で3回 gate を降格させた操作そのもの**）
- 観測1: observer が `{src:"observed", status:"ok", marker_verified:false, fp:"2c101d8b…"(64hex)}` を追記（罠エントリの実物）
- 観測2: `build-judge-card.py --gate qa` preview → **「テスト: green」**（noise を透過して manual green が判定）
- 観測3（差分）: 同一リポジトリ状態に **旧実装（d2c4dd6 の read_test_result）**を適用 → **unverified**（罠発火）
- 判定: **OLD=unverified／NEW=green**＝罠の機構的根切りを実 observer パイプラインで確認・PASS

## スイート実測

- scoped（realness＋judge_card）: **99 passed**（qa agent 先行実測 16.15s・親再実測とも一致）
- full suite: record-test-result（trusted runner）で green 記録＝本承認直前の最新 decidable エントリ
- lint/type-check/build: 該当なし（pure python 標準ライブラリ・ビルド工程なし）
- 既知 flaky `test_update_gate_lock`: 本 iter の全 run で顕在化せず（diff 不接触＝回帰外）

## ブロッカー

なし。

```claims
tests_pass: true
no_stubs: true
verdict: approve
```
