# iter71 review レポート — marker positive proof（SF-014 恒久策）

- 対象 diff: `33c110b..HEAD`（実装 Task1-5＋docs 層＋review fix-forward 9dc77b1）
- 設計正本: `docs/specs/2026-07-15-iter71-marker-positive-proof-design.md`
- 計画: `docs/plans/2026-07-15-iter71-marker-positive-proof-implementation-plan.md`
- 種別: framework / size L（control-plane＝反ガミング moat）
- レビュー方式: grill-code（親）→ 1次4角度並列（opus finder・read-only 6拘束）→ 親 verify → fix-forward → 盲検2次（claims 参照）

## 対照表（plan Task ↔ 実装 ↔ 状態）

| # | plan タスク | 実装コミット | 状態 |
|---|------------|------------|------|
| T1 | RED＋both-green 移行 | 037545c | ✅ RED 19失敗（期待一致）・both-green 移行 |
| T2 | marker.sh 抽出＋evidence.sh 委譲（挙動不変） | 12227ac | ✅ 逐語移動 byte 一致・patterns.sh リテラルTAB修正（pre-existing欠陥） |
| T3 | drill baseline no-test-proof | ec24c83 | ✅ marker_verdict＋no-test-proof BLOCKED |
| T4 | record green positive proof 必須 | c22bf6c | ✅ rc2拒否・ログ非書込・marker:true |
| T5 | SKILL 同期＋full suite | b6551de | ✅ SKILL追記＋realness fixture 回帰fix |
| docs | 残2fail解消＋整形 | 6125e05/6ce7447 | ✅ lib13・iter68 archive・contract green |
| fix-fwd | review finding 対応 | 9dc77b1 | ✅ skip-suite pin＋parity＋mocha修正＋SF-014 |

## Severity 分類済み findings

### 敵対角度（親 verify で独立実証）

- **F-A（Minor・confidence 9）**: unittest/go の all-skip suite が marker=true → record green → judge `tests:green`（qa gate 通過可能）。unittest は skip を `Ran N` に数える／go は全 `t.Skip()` でも `ok pkg dur`。**pytest（`N skipped in`）・cargo（`0 passed`）は marker=false で安全**（実測）。
  - **pre-existing**: marker.sh は evidence.sh の逐語移動（byte 一致・Task2 で確認）。pre-iter71 evidence.sh も all-skip 入力で同一 true を差分実走で確認。iter71 は net 改善（nomatch/npm-true zero-run を新規閉塞）で回帰ゼロ。
  - **contained**: drill が subsume（all-skip baseline は mutant を1件も殺せず DRILL FAIL・実測）。qa gate は drill＋judge の両層で守られ、本穴単独では破れない。
  - **対応**: denylist で塞がず（SF-014 の戒め）SF-014 に記録＋恒久策（passed/failed 実数カウント proof・iter72+）へ。moat 保護 pin を fix-forward（`TestSkipSuiteResidual`）。

### 仕様準拠角度（approve_with_notes）

- **F-1（Minor・confidence 8）**: patterns.sh のリテラル TAB 修正は計画「無変更 pin」からの逸脱だが、pre-existing BSD-grep 欠陥（bracket 内 `\t` 非展開）の semantics-preserving 修正で STATUS/コミットに記録済み・M10 が正の pin。**承認ブロックに当たらない**。
- **F-2（Minor・confidence 7）**: リテラル TAB 化した PASS_MARKER/ZERO_RUN が parity テスト覆域外だった（pre-existing ギャップ）。→ fix-forward で `TestMarkerZeroRunParity` 追加。**副産物**: この新テストが mocha `0 passing\b` の cross-engine 乖離（BSD grep で非機能）を摘発 → 共通部分集合形に修正。

### テスト強度角度（approve_with_notes）

- 4段（NO_RUN/STRONG/WEAK pair/zero-run 3軸）・record 5契約・drill D1 E2E は mutation 実験で殺傷力を実証。
- **F1（Minor・confidence 7）**: rc3 guard の個別条件除去を検知するテストがない（AND 条件の回帰網）。→ **iter72 hardening 推奨**（本 diff 導入の欠陥でなく既存カバレッジギャップ・fail-closed 方向）。
- **F2（Minor・confidence 6）**: companion-only pin なし。→ fix-forward で `TestWeakPairBoundary` 追加。
- **F3（confidence 5）**: TestQaDrillGate 移行の意味保存は本 finder 未検証だが、**Task1 タスクレビュー（Item 4）で実測済み**（blind=pass-only unittest で「生存 mutant→block」経路を保存・baseline BLOCKED での偶然 rc1 でないことを確認）。
- **F4（confidence 4）**: npm skip 確認漏れ → 敵対 finder が npm 実在環境で PoC 実行・仕様 finder も「当環境で実行」と確認済み。

### 保守性角度（approve_with_notes）

- 単一ソース原則達成（marker.sh に regex ハードコードなし・evidence.sh に stage 残骸なし）・drift ガード文書化・docstring 正確・配布契約（setup.sh glob）正しい。
- **Minor 2件（confidence 6）**: 命名語彙の分散（marker_verdict/aegis_marker_verdict/_check_test_marker/marker_proven）・record→drill 依存（`_load("drill_mod")`）の命名不透明性。→ iter72+ で語彙表の検討推奨（実害小・コメント緩和済み）。

## grill-code（親・Critical 0）

境界プローブ（whitespace/CRLF/NUL・すべて安全側 false）実走。Critical/Should fix なし。CRLF WEAK marker 非マッチは逐語移動元と同一挙動（iter71 新規乖離でない）。

## Evidence

- 影響範囲（fix-forward 後）: test_marker_lib(17)＋patterns_parity(14)＋record＋drill＋judge = 215 passed。
- full suite: fix-forward 後の再実測を本レポート脚注に追記（脚注参照）。
- 逐語移動 byte 一致・DrillError 4経路 raise・rc3 guard fail-closed・skip-suite の pre-existing を各タスクレビュー＋親 verify で実証。

## 判定

**PASS（approve）**。Critical/Major なし。全 finding は Minor 以下で、F-A（skip-suite）は pre-existing・contained・SF-014 恒久策トラックへ。fix-forward（9dc77b1）で skip-suite 残余の記録・moat 保護 pin・parity 覆域・mocha cross-engine 修正を追加済み。F1（rc3 guard 回帰網）と保守性 minor 2件は iter72 hardening 推奨。

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: []
```

## 盲検2次（fresh context・1次 findings 非開示・fable）

独立に検証し **approve_with_notes**。1次と収束（divergence なし）:
- zero-run positive proof を record/drill 両経路で実測（nomatch/`-q`/import プローブ拒否・正規 pytest 受理＋marker:true）
- fail-open 退行なし: marker.sh 欠落/空/構文破損・patterns.sh gutted の全破損で record rc2・drill BLOCKED を実測
- 挙動不変: old evidence.sh の Stage1-4 と marker.sh が byte 一致
- テスト判別力: zero-run Axis1 無効化ミューテーションで M7/M11 が退行を捕捉
- full suite 独立実測 1272 passed / 2 skipped / 0 failed
- 残余(a) echo-marker・(b) all-skip suite を独立に再発見 → 1次・親 verify と同一結論（pre-existing・contained・iter72 count-based proof へ）。新規の破れなし

## 脚注（実測ログ）

- full suite（fix-forward 9dc77b1 後）: 1272 passed / 2 skipped / 0 failed（253.10s）。fix-forward 前 1262 から +10（marker_lib +5・patterns_parity +5）で無退行。
