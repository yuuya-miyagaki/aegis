# iter69 QA レポート — B1 drill 強化（NO_RUN 拒否＋mutant 構文検証＋コメントラン floor 除外＋since baseline）

## 対象

- 変更内容: `scripts/run-test-strength-drill.py`（新規4機能＋既存拡張）／`hooks/lib/patterns.sh`（NO_RUN denylist）／`tests/test_test_strength_drill.py`（新規テスト群）／`.claude/skills/qa-verification/SKILL.md`（利用手順）。commit 532611c..HEAD。
- 環境: darwin / python3 / bash / git。ui_surface: false（ブラウザ QA 非該当）。
- 計画正本: docs/plans/2026-07-14-iter69-drill-hardening-implementation-plan.md（受入条件6項目）

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | NO_RUN 拒否（collect-only 系 BLOCK） | check_no_run_command | E2E＋fresh 変異 M1／敵対フォージ battery | PASS |
| 2 | mutant 構文検証（構文破壊 BLOCK） | syntax_check_mutants/_parses | 単体5＋fresh 変異 M3 | PASS |
| 3 | コメント/docstring ラン floor 除外 | non_coverable_lines/anti_gaming exempt | 単体10＋fresh 変異 M5/M6 | PASS |
| 4 | since baseline＋report since 行 | resolve_since_ref/write_report/run_drill | E2E 2件＋fresh 変異 M4 | PASS |
| 5 | 全 pre-check fail-closed | 全経路 | 変異 kill＋敵対検証で fail-open ゼロ確認 | PASS |
| 6 | full suite/contract/SKILL 同期/budget | 全体 | full suite＋contract＋budget | PASS |
| F | shlex quoting 迂回閉塞（review 盲検2次 F-1） | check_no_run_command | 敵対再検証＋fresh 変異 M2 | PASS |

## 実施した確認

- [x] full suite 実行・record green（1211 passed / 2 skipped）
- [x] contract 整合（`PASS: aegis contract is aligned`）
- [x] qa fresh 変異バッテリ（コア新関数6変異）を隔離 clone で全 KILLED
- [x] since モード実環境の成立を実測（E2E＋scratch clone）
- [x] 敵対フォージ battery（flag 系・quoting 迂回）で偽 PASS ゼロ・過剰ブロックなし
- [x] B1 drill は sanctioned skip（下記・実測根拠付き）＋代替実証

## 実行コマンドと結果

```bash
python3 -m pytest tests/ -q            # 1211 passed, 2 skipped
python3 scripts/check_framework_contract.py   # PASS: aegis contract is aligned
python3 -m pytest tests/test_test_strength_drill.py -q   # 78 passed（clone baseline）
```

### qa fresh 変異バッテリ（隔離 clone・本体 tree 不接触・baseline 78 passed）

| 変異 | 破壊対象 | 対象テスト結果 | 判定 |
|------|---------|--------------|------|
| M1 | NO_RUN `rc == 0` 判定反転 | 2 failed | KILLED |
| M2 | shlex 正規化を生文字列のみに退行（＝F-1 の退行） | 2 failed（quoting 迂回テスト赤化） | KILLED |
| M3 | 構文検証 `is False`→`is True` | 3 failed | KILLED |
| M4 | since ancestor 検査を無効化 | 2 failed | KILLED |
| M5 | floor subset 除外を全通し（`if True`） | 3 failed | KILLED |
| M6 | non_coverable コメント検出破壊 | 5 failed | KILLED |

6/6 KILLED。各変異は clone に適用→scoped 実行→revert（clone diff 空を確認）。

### since モード実環境 E2E

- `test_since_mode_committed_change_pass`：committed 変更（HEAD diff 空）を since=基点で drill 成立し `verdict: PASS`＋report に `since:<sha>`。PASS。
- `test_since_non_ancestor_blocked`：非 ancestor ref は DRILL BLOCKED。PASS。
- 隔離 clone で `git diff <since>` の added 行番号と working-tree の行番号整合を確認（ズレなし）。

### 敵対フォージ battery（grill-code＋review 盲検2次＋fix 敵対再検証の統合結果）

- **flag 系フォージ**（`--collect-only`/`collectonly`/`--co`/`--setup-plan`/`--setup-only`/`--fixtures-per-test`）＋**quoting 迂回**（`"--collect-only"`/`'--collect-only'`/隣接連結/タブ改行同梱/`--`以降/case/全角/略記/`=`付き/env プレースホルダ）＝**すべて BLOCKED・偽 PASS ゼロ**。
- **構文破壊 mutant**（py/sh）＝BLOCKED。**構文保存 mutant**＝素通り（正常）。
- **過剰ブロックなし**：`pytest -k "a and b"` 等のクォート付き正当引数は NO_RUN 素通り（legit 11 コマンド実測）。
- **残余（非ブロッキング）**：非フラグ no-run コマンド（`python3 -c "import m"`）は pre-existing フォージ＝**SF-014**（差分実測で cbc49e7 でも同一偽 PASS＝iter69 は net 改善・回帰ゼロ）。

## B1 テスト強度ドリル（sanctioned skip・実測根拠付き）

- 本 iter は framework 改修を per-task コミット済み＝`git diff HEAD` 空。iter69 の since モードで基点(cbc49e7)へ向けると全反復 diff が surface するが、**scripts+patterns+tests+SKILL.md の多数ハンク（689 挿入）が coverage floor で mutant を要求し、tests ハンク（本体の大半）は assert を意味的に変異できず構造的に不成立**（`since=cbc49e7` で実際に `DRILL BLOCKED (anti-gaming)` を実測）。これは LEARNINGS conf9 の framework 混在 diff・tests-as-bulk の既知エッジ（since は罠 f＝空 diff を解くが、本 iter の律速は tests-bulk floor で別軸）。
- **代替実証** = 上記の (1) 全タスク RED-first TDD（Task1=32 failed）(2) fresh 変異 M1-M6 全 KILLED (3) since E2E＋実測 (4) 敵対フォージ battery (5) full suite 1211 passed / contract aligned。
- skip 宣言は `docs/qa-reports/test-strength.drill` に記録（承認時 `run_qa_drill` が `verdict: SKIP` を出す）。

## 結果

- Pass: 受入条件6項目＋F（shlex quoting 閉塞）すべて PASS。fresh 変異 6/6 KILLED。
- Fail: なし。
- Skip: B1 drill 本体（sanctioned・代替実証済み）。
- ブロッカー: なし。residual = SF-014（非フラグ no-run・pre-existing・iter70+ の positive-execution-proof で恒久対応）。

```claims
tests_pass: true
no_stubs: true
verdict: approve
drill: skip_with_alternative_evidence
residual: "SF-014 非フラグ no-run フォージ（pre-existing・非ブロッキング・iter70+）"
```
