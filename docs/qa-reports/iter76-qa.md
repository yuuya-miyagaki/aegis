# iter76 QA — evidence 整合＋locale 掃討完了

- 対象: iter76 実装 `097c103..c1dc9a8`（W1=SF-018／W2b=marker Stage 6／W2a+W3=judge washed transparent＋src allowlist＋errors-gap 緩和）
- 参照: plan `docs/plans/2026-07-22-iter76-evidence-integrity-locale-implementation-plan.md`／review `docs/qa-reports/iter76-review.md`
- 前提: per-task commit 済み＝working-tree diff 空

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | SF-018 byte fail-open 封鎖 | check-runtime-state.sh | hook 直接発火 E2E-1 | PASS |
| 2 | washed-green veto（marker Stage 6） | marker.sh | marker 直接発火 E2E-2 | PASS |
| 3 | washed transparent＋src allowlist | build-judge-card.py | judge e2e E2E-3 | PASS |
| 4 | errors 語形封鎖（盲検2次 divergence） | patterns.sh/marker.sh | E1/E2 実測（review c1dc9a8） | PASS |
| 5 | 旧赤/新緑 differential | tests ×4 | RED-first 10/8＋mutation 歯 | PASS |

## テストスイート

- full suite: **1394 passed / 2 skipped**（record green・src=manual・marker:true・ts=2026-07-22T08:56:27Z）
- 影響 6 ファイル: 191 passed
- `check_framework_contract.py`: PASS／`status_doctor.py`: PASS

## 検証項目（再現手順・メイン tree 実測）

### 検証項目: SF-018 — 0xFF byte で silent-allow に落ちない（E2E-1）
- 前提: 非 framework（feature）scratch・UTF-8 locale
- 操作: `echo <0xFF> x > docs/STATUS.md` を check-runtime-state.sh に直接発火
- 期待: deny（byte 汚染で pattern-miss せず runtime-state 書込みを検出）
- 実際: **deny**（ASCII 書込みも deny＝非退行）
- 判定: **PASS**

### 検証項目: washed-green — marker Stage 6 veto（E2E-2）
- 操作: `1 failed, 2 passed`（exit0）と `3 passed`（exit0）を marker に発火
- 期待: washed→false・本物 green→true
- 実際: **false / true**
- 判定: **PASS**

### 検証項目: judge src allowlist（E2E-3）
- 操作: `src:"forged"`・fp一致・marker_verified=true のエントリを judge に読ませる
- 期待: unverified（decidable-by-default に落ちず終端🟡）
- 実際: **unverified**
- 判定: **PASS**

## テスト強度ドリル（B1）＝ sanctioned skip（実証付き）

per-task commit 済みで working-tree diff 空＝想定どおりの縁ケース（SKILL 147-150）。`since:097c103` 案は実走で **DRILL BLOCKED**（coverage floor が 8 tracked 非docs ファイルの全ハンク＝test 追加 105/108/97 行の巨大ハンク含む＝framework 混在 diff で構造的不成立・LEARNINGS line33/54）を実測。代替実証:

| 軸 | mutant/操作 | 実測 | 歯 |
|---|---|---|---|
| RED-first（Task1） | 全機能未実装 | 10 RED/8 PASS（fail 理由＝機能欠如） | ○ |
| W3-2 | src allowlist :336 terminal→continue | unverified→green（pin RED 化） | ○ |
| W2a-2 | washed transparent continue→terminal | green→unverified（pin RED 化） | ○ |
| W2b-6b | fail-token :319 TAB→space degrade | false→true（M10 罠捕捉） | ○ |
| errors-gap | 第5 alt 追加前 | marker true/judge green→false（E1/E2） | ○ |
| SF-018 | LC_ALL 追加前（RS1） | silent-allow(rc0 None)→deny flip | ○ |

詳細は `docs/qa-reports/iter76-review.md`（対照表D・バッテリA/B/C/E/V・10綴り washed 全封鎖）。

## エビデンス収集チェックリスト

- [x] テストスイート実行・記録（1394 passed/2 skipped・record green）
- [x] contract/status_doctor 実行（PASS）
- [x] plan 受入条件と突合（機能対照表・全 PASS）
- [x] 各検証項目に PASS 判定
- [x] FAIL 項目なし（ブロッカーなし）

```claims
tests_pass: true
no_stubs: true
scope_creep: false
b1_drill: skip_sanctioned
verdict: approve
second_opinion:
  verdict: approve
  divergence_points: []
```

> qa は SECOND_OPINION_GATES 非対象（review/security のみ）＝2次は形式上の同値記入。実質の独立検証は review 盲検2次（errors-gap divergence）で完了済み。

## Exit 判定

**approve**（全機能対照 PASS・E2E 3項目メイン tree 実測 PASS・full green/contract/doctor PASS・B1 は DRILL BLOCKED 実証のうえ sanctioned skip＋6軸の mutation 代替実証で歯を確認・ブロッカーなし）。
