# QA レポート — iter78 pytest execution attestation
<!-- 正本: qa agent -->

## 対象

- 変更内容: pytest テスト実行証跡を出力テキスト解析から argv spawn＋pytest 構造化イベントの positive proof に一本化（SF-014/SF-022 根治・SF-015 attested 経路解消）。新規 scripts/attest-test-run.py・scripts/aegis_attest_plugin.py、judge/record 改修。
- 環境: darwin・python3.9.6・pytest 8.4.2・本体 tree（git clean）。

## 機能対照表（design/plan の全機能 → 検証）

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|---|---|---|---|
| 1 | argv spawn＋plugin 注入（shell なし） | attest-test-run.py:124-127 | e2e 実走（2 passed→green・出力非パース） | PASS |
| 2 | 構造化イベント（executed/passed/failed/skipped/errors/xfailed/xpassed/collection_error/exit） | aegis_attest_plugin.py＋attestor 集計 166-217 | e2e で counts.executed==実数を実測 | PASS |
| 3 | green 条件 exit0∧executed≥1∧failed=errors=collection_errors=0 | attestor 189-192,196 | passing/failing/all-skip/collect-only/xfail suite で実走 | PASS |
| 4 | src=attested のみ pytest decisive green | build-judge-card.py:402-412 | observed/manual pytest ok→transparent・attested→green を pin | PASS |
| 5 | fake 出力で green 不能 | attestor（出力継承・非パース） | 999 passed print×assert False→red 実走 | PASS |
| 6 | pytest exit5（収集0）=red | attestor 196 | 実走 rc1/status fail | PASS |
| 7 | record が pytest family を rc2 誘導 | record-test-result.py:137-153 | 整形式 pytest→rc2・非 pytest 不変 | PASS |
| 8 | read-time counts 検証（review fix） | build-judge-card.py:454-461 | counts 皆無/0/壊れ→unverified | PASS |
| 9 | scripts-manifest 2行＋full.json 配布 | manifest・full.json | check_framework_contract PASS | PASS |
| 10 | 非 pytest ランナー挙動不変 | judge/record | npm/unittest green のまま実走 | PASS |
| 11 | in-process 妨害 fail-closed | attestor 突合＋strict decode | sabotage/invalid-byte/forged-sessionfinish→rc2 or red | PASS |

- 実装漏れ 0（全 plan 機能に検証対象あり）。

## 実施した確認

- [x] full suite 実行・結果記録（1447 passed / 2 skipped）
- [x] ドッグフード attest（本体 suite を attestor で実走→attested green・executed=1447・judge 判定源 src=attested を実測）
- [x] plan 受入条件と突合（機能対照表 11/11 PASS）
- [x] テスト強度: `since:a5ef438` ドリル実走→DRILL BLOCKED (anti-gaming) 実測→sanctioned skip＋代替 mutation 実証（.drill 参照）
- [x] contract / drift / doctor / budget 全 PASS
- [x] 各項目に PASS 判定付与・FAIL 0

## 実行コマンド

```bash
python3 -m pytest                               # 1447 passed, 2 skipped
python3 scripts/attest-test-run.py --timeout 1800 "python3 -m pytest"   # attested: green (executed=1447)
python3 scripts/run-test-strength-drill.py --root . --spec docs/qa-reports/test-strength.drill --report docs/qa-reports/test-strength.md   # DRILL BLOCKED (framework 混在 diff)
python3 scripts/check_framework_contract.py     # PASS
python3 scripts/check_reference_drift.py        # PASS
python3 scripts/status_doctor.py                # PASS
python3 scripts/context_budget.py               # PASS (exit 0)
```

## 結果

- Pass: full 1447・機能対照 11/11・ドッグフード attest green・contract/drift/doctor/budget
- Fail: なし
- Skip: テスト強度ドリルは framework 混在 diff の構造的 BLOCKED ゆえ sanctioned skip（代替＝Task1 差分 RED 14件＋production 判断点 mutation 7/7 検知者確立〔M3 gap 摘発→pin 封鎖〕＋敵対7クラス実走バイパス0＋独立2次・全て review フェーズで実走・.drill に詳細）／test 2 skip は pre-existing（本変更外）

## テスト強度の扱い（sanctioned skip の根拠）

- `since:a5ef438` 実走で **DRILL BLOCKED (anti-gaming)**（exit1）を実測。coverage floor が新規/変更テストファイル4本・full.json・record redirect ハンクに mutant を要求＝テストコード自体への変異は循環・config は非コードで、framework 混在 diff の構造的不成立（LEARNINGS line33/54・iter76/77 同型）。
- 代替実証（`.drill` の reason に全文）: (1) 差分 RED（旧実装で 14 failed）(2) production 7 判断点 mutation で検知者確立（M3 突合の検知者不在を**摘発→pin 追加で封鎖**）(3) 敵対7クラス実走でバイパス0・load-bearing 不変（本物 red は偽イベントで green 化不能）実証 (4) 独立2次（drift/counts 堅牢/rotation/plugin 例外）。

## Blockers

- なし。残余は SF-024（in-process event 偽造＋attested 手書き＝OS-limit・drill subsume・load-bearing 不変は pin 保証）＝accepted residual・非ブロッキング。security フェーズで再検証。

## Claims（judge が機械読取する）

```claims
verdict: approve
```

<!-- exit-check: 全チェック実施・結果記入済み → security へ -->
