# iter72 Review — marker count proof（SF-014 完結編）

- 対象: `git diff 1e70fa0..HEAD`（iter72 全コミット）
- 実装コミット: 5e10163(RED)→be77a85(count proof)→617a5c4(record docs)→925a8ae(SF/SKILL)→**fa97241(review fix-forward)**＋8e9d589(review test pins)→**06b4556(review round-2: M-1/M-2)**
- 設計正本: `docs/specs/2026-07-16-iter72-count-proof-design.md`
- 計画正本: `docs/plans/2026-07-16-iter72-count-proof-implementation-plan.md`

## 対照表（plan Task 0-4 × 実装）

| Task | 内容 | コミット | 状態 |
|---|---|---|---|
| Task 0 | baseline green・直列 | — | 完（exit 0 確認） |
| Task 1 | RED（正確に 10 failed） | 5e10163 | 完（実測 10 failed/34 passed 一致） |
| Task 2 | patterns.sh count 族＋marker.sh Stage 5 | be77a85 | 完（対象 44 OK・full 1103 OK・literal TAB 検証済み） |
| Task 3 | record docstring/メッセージ同期 | 617a5c4 | 完（all-skip 拒否 rc2＋no-log-write 実地裏取り） |
| Task 4 | SF-014 追記＋qa SKILL 同期 | 925a8ae | 完（budget cap 507 維持のため既存プローズ同量圧縮＝承認済み逸脱・意味保全） |
| review fix | 下記 findings の fix-forward | fa97241＋8e9d589 | 完 |

## レビュー体制

1次: aegis 4 角度 finder（opus・仕様準拠／テスト強度／敵対／保守性）＋公式 code-review workflow（high・16 agent・finder→独立 verify）。親 verify: 本セッション（fable）が全 finding を marker.sh stdin プローブ・BSD grep/python parity・1e70fa0 baseline battery で実測突合。盲検 2 次: fresh context reviewer（fable・fix-forward 後の状態・1次 verdict 非共有）。

## Findings（統合・重複排除後）

### fix-forward で対応（fa97241 / 8e9d589）

| # | severity | conf | 内容 | 対応 | pin |
|---|---|---|---|---|---|
| F-2 | Major（false-POSITIVE） | 8 | vitest アンカー緩和の副作用で実 vitest all-skip（`Test Files 1 passed`）が iter71 false→iter72 **true の false-GREEN** に反転。設計封鎖表の「vitest=false」主張が不成立 | count DETECT を `Tests N (passed\|failed\|skipped\|todo)` に拡張→`Tests N skipped` 検出→passed+failed=0 で veto | `test_vitest_all_skip_false_closed` |
| F0 | Major（false-negative・common） | 8 | unittest MINUS `skipped=[0-9]+` が全文無アンカー→本体印字の偶発 `skipped=N`（config/子出力）で過剰減算→実 green 誤拒否。実測: `config: skipped=10`+`Ran 2 OK`→false | MINUS を `[(,] ?skipped=[0-9]+` にアンカー | `test_unittest_stray_skipped_token_true` |
| F1 | Major（false-negative・common） | 8 | pytest DETECT `={3,} .* in [0-9.]+s` が CI/wrapper バナー（`===== build finished in 3.21s =====`）を誤検出→他ランナー（素 go）の実 green を cross-family veto。実測: banner+`ok pkg dur`→false | DETECT に `N (passed\|failed)` 必須化 | `test_bare_go_with_ci_banner_true` |
| F4 | Minor（GNU 限定・robustness） | 6 | GNU grep が UTF-8 locale で非 UTF-8 バイトを binary 検出→count 0 化（BSD は無影響・実測確認） | Stage 5 全 grep に `-a` | 実環境依存のため fixture pin なし（設計に根拠記録） |
| F5 | Minor（fail-open→closed） | 7 | DETECT grep の rc≥2（host grep 非対応 regex）を no-match と混同→family veto 沈黙無効化 | rc 判別: rc>1→rc3 fail-closed | rc3 経路（malformed pin で近接被覆） |
| F6 | Minor（fail-open→closed） | 7 | malformed COUNT_FAMILIES entry を silent continue（fail-open） | strict 5-field parse→malformed は rc3 | `test_rc3_when_count_families_missing`＋親 verify で malformed→rc3 実測 |
| 強度F-1 | Major（moat pin 欠落） | 8 | count DETECT の literal-TAB parity fixture 欠落（iter71 M10 と同型回帰を count 族では未捕捉） | parity に TAB fixture 追加 | `test_detect_fixture_parity`（TAB 形 3 件追加） |
| 強度F-4 | Minor | 5 | EXEC/MINUS の両エンジン behavioral parity 未実施 | `test_exec_minus_fixture_parity` 追加 | 同左 |
| 保守性 | Minor | 7 | record docstring「4-stage」が Stage 5 追加後も未更新 | 「5-stage」へ訂正＋残余 (c) 追記 | — |
| M-1 | Minor（fail-open 非対称・盲検2次） | 6 | MINUS/sum-EXEC grep の rc≥2 を `\|\| true` で握り潰し→broken MINUS で unittest all-skip が fail-open true（DETECT は rc3 済みで非対称） | EXEC/MINUS の pattern grep を rc 判別し rc>1→rc3 統一（06b4556） | `test_broken_minus_regex_rc3_not_failopen` |
| M-2 | Minor（doc・盲検2次） | 4 | body 中 paren 形 `(skipped=N)` 過剰減算の摩擦がコメント未明記 | patterns.sh コメント＋SF-014 に受容 fail-closed 残余として明記（06b4556） | — |

### 受容した残余（doctrine 準拠・非修正・文書化）

- **cross-family fail-closed 残余**: 素 go log に偶発的他族ゼロカウント行（`Tests: N skipped`/`test result: 0 passed`）が column-0 で出ると cross-family veto で実 go が false（friction・稀・**安全側**）。output-based 検出の原理コスト。command-keying は `npm test` ラッパで false-positive 方向へ倒れ moat 原則に反するため不採。設計 review 追補＋SF-014 に記録。
- **marker 層の天井（SF-014 (a)(b)(c)）**: (a) echo フォージ、(b) 素 go all-skip、(c) unittest の `addSkip` monkeypatch（`skipped=` 消失で実 N-pass と区別不能＝unittest CLOSED は「honest skip 自己申告」前提下の CLOSED）。いずれも drill が subsume（all-skip baseline は mutant を殺せず DRILL FAIL）。恒久策候補=execution attestation（iter73+）。
- **pre-existing（SF-015 起票）**: pytest all-xfail suite（`===== 3 xfailed in 0.5s =====`）は STRONG 不成立→false（実 body 実行済み green の誤拒否・fail-closed 摩擦・Low）。iter72 は STRONG 未改修。

## Evidence Checklist

- [x] diff を Read/Grep で実読（chat summary でなく実ファイル）
- [x] plan/spec の受入条件と突合（対照表）
- [x] 未カバーのエッジケースを列挙（受容残余・SF 起票）
- [x] 全 finding に severity と confidence 付与
- [x] 親 verify: 13 verdict battery（既存 7 pin 不変＋新 6 fix）・BSD grep+python parity・rc3 経路 全実測
- [x] full suite: 1107 tests OK（skipped=2）・既知 flaky test_update_gate_lock 非発火

## claims

```claims
tests_pass: true
no_stubs: true
verdict: approve
first_review_verdict: approve
second_opinion:
  verdict: approve_with_notes
  note: fresh context・1次verdict非共有・fix-forward後の状態をレビュー・結論は1次と収束
  new_false_green: 0
  new_false_negative: 0
  parity: 25/25 一致（BSD grep + python re）
  full_suite: 1107 OK (skipped=2)
  notes: [M-1（round-2 で是正済み）, M-2（doc・是正済み）]
  divergence_points: []
findings_resolved: [F-2, F0, F1, F4, F5, F6, M-1, M-2, 強度F-1, 強度F-4, 保守性]
residuals_documented: [cross-family fail-closed, SF-014(a)(b)(c), SF-015]
```

## Verdict（親・1次＋盲検2次 統合）

**approve**（fix-forward 2 ラウンド後）。核心目的（unittest/go -v/vitest all-skip の偽 green 封鎖・cargo/jest 偽陰性修正）は実測達成。多角レビュー（1次4角度＋code-review workflow＋親verify＋盲検2次）で摘発した false-GREEN 1 件（F-2）・false-negative 2 件（F0/F1）・fail-open 3 件（F5/F6/M-1）・moat pin 欠落（強度F-1）をすべて fix-forward し、fail-closed 原則を維持。**盲検 2 次（fix-forward 後の独立レビュー）は新規 false-GREEN・false-negative ゼロ**・parity 25/25・full suite 1107 OK を実測し、1次と収束（divergence なし）。残余はすべて doctrine 準拠（安全側 fail-closed 摩擦）または marker 層の原理的天井（SF-014 (a)(b)(c)・SF-015）で、B1 drill が subsume。Critical 0・未対応 Major 0。
