# iter60 レビューレポート（review ゲート）

- 対象: 実装 `acc2ad4` ＋ grill-code fix-forward `c971894` ＋ review 盲検2次 fix-forward（`test_context_budget.py`/`context_budget.py` コメント/design）（iter60・budget ratchet policy 見直し＝drift 支配構造の計数除外）
- 仕様正本: `docs/specs/2026-07-06-iter60-budget-exclusion-design.md`
- 実装計画: `docs/plans/2026-07-06-iter60-budget-exclusion-plan.md`
- 1次レビュー方式: セッション内フルコンテキスト実読＋grill-code（実装後に完走・Critical 0／Major=🟡1件を fix-forward）＋決定論検査（RED-first／full suite／contract／drift／budget）。盲検2次は fresh context の general-purpose エージェントで独立実施（1次結論非開示・diff/spec/plan のみ）。

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | 除外ロジック（`_strip_excluded`/`_budget_word_count`＋3経路統一） | `scripts/context_budget.py`＋`tests/test_context_budget.py`（`TestBudgetExclude`×2） | ✅ 完了 | check/tighten/seed の3経路を `_budget_word_count` に統一（乖離不能）・非貪欲 DOTALL・fail-graceful |
| 2 | routing.md マーカー＋budget 90→70＋濫用ガード＋CLAUDE.md policy | `.claude/rules/routing.md`＋`scripts/context-budgets.json`＋`CLAUDE.md`＋test（`TestRoutingExcludeAntiAbuse`） | ✅ 完了 | strip 後 70・濫用ガード（除外==roster／findall+len==1／prose 除外）・CLAUDE.md terse policy |
| — | grill-code fix-forward（allowlist トリップワイヤ） | `tests/test_context_budget.py`（`test_only_routing_uses_exclude_markers`） | ✅ 完了 | 新 excluder の無ガード混入を機械検知（c971894） |

未着手タスクなし。

## Findings（1次・実測検証済みのみ）

### Critical — 該当なし
### Major — 該当なし（grill-code 🟡 は fix-forward 済）

### Minor / Nice-to-have

- **`tests/test_context_budget.py`（濫用ガード・confidence 8）** — grill-code で「濫用ガードが routing.md 特化＝2つ目の excluder は無ガード」を検出→**fix-forward `c971894`**で allowlist トリップワイヤ（除外マーカーは routing.md のみ許可・`iter_targets` に実 `_EXCLUDE_RE` を当てる）を追加。新 excluder は即 FAIL＝「専用ガードを付けてから allowlist 更新」を機械強制。実証: 偽マーカー文字列が `_EXCLUDE_RE` にマッチ＝別 target に置けば test FAIL。
- **`scripts/context_budget.py:26`（nested マーカー・confidence 7・据置）** — nested（`start…start…end`）は fail-safe（余分に計数）だが未テスト。意図は fail-graceful で安全側＝据置（任意で nested テスト追加可）。
- **`CLAUDE.md`（policy・confidence 8）** — 実装時に **CLAUDE.md kernel budget（`MAX_CLAUDE_WORDS=650`・baseline 618）** を踏み、verbose 2項（715>650 で FAIL）→ **terse 1行（23語・641/650）**に訂正。design/plan の「CLAUDE.md 対象外」記述も実態に修正済。全文 policy は spec＋context_budget.py コメントに存置。

## Evidence Checklist

- [x] diff を実読した（`git diff acc2ad4~1 c971894`）
- [x] plan/spec の受入条件と突合（§確定文言A/B/C・スコープ境界・訂正後の CLAUDE.md 制約と一致）
- [x] 未カバーのエッジケース列挙（unmatched=fail-graceful／nested=fail-safe／多領域=len==1／新 excluder=allowlist）
- [x] 全 finding に severity と confidence 付与

### 決定論検査の実測

| 検査 | 結果 |
|------|------|
| RED-first | 除外・濫用ガード 2件が実装前 FAIL（116>20／0領域）→ 実装後 GREEN |
| 除外 strip | routing.md `_budget_word_count`=70（roster 20＋マーカー6 を除外） |
| 予算 | `context_budget.py` exit 0（routing.md 70/70 境界 PASS） |
| 参照ドリフト | `check_reference_drift.py` exit 0（マーカーは backtick 抽出に非干渉＝roster 引き続き pin） |
| フレームワーク契約 | `check_framework_contract.py` exit 0（CLAUDE.md 641/650） |
| フルスイート | **1055 passed, 2 skipped, 0 failed**（iter59 baseline 1052 +3）＋fix-forward 後 再走（下記 claims） |

## PASS/FAIL 判定

**PASS（1次）。** Critical/Major 0（grill-code 🟡 は fix-forward 済）・設計 §確定文言と一致・全 harness 緑・除外機構は fail-graceful＋濫用ガード＋allowlist で堅牢・drift 回帰なし。

## 盲検 第2意見（self-attested）

fresh context の general-purpose エージェントに diff（acc2ad4~1..c971894）＋spec＋plan のみを渡し、1次結論を非開示で独立2次レビューを1回ディスパッチ（6論点: 除外機構／濫用ガード堅牢性／後方互換／drift 回帰／budget 値・CLAUDE.md 650／仕様乖離）。実走検証済（正規表現7ケース・pytest 14 passed・full 1056・contract/drift/budget exit0・routing strip=70・excluders==[routing.md]）。

**2次 verdict = approve_with_notes。** 6論点すべて健全（機構・後方互換・drift 回帰なし・budget 一致・仕様一致）。2件の非ブロッカー note を提起し、**両方 fix-forward で解消**：

### divergence への対応（fix-forward）
- **note1（nested コメント誤り）**: `context_budget.py:27` の「Unmatched/nested markers strip nothing」は事実誤り＝非貪欲は nested で first-start..first-end を strip する（unmatched のみ strip 0）。→ コメントを「unmatched は strip 0／nested は非対応（strip-safe でない）＝入れ子禁止」に訂正＋design §エラー処理も同期。
- **note2（ガードが ⊆ で == でない）**: 濫用ガードの docstring は「除外領域==roster」だが実述語は「⊇ agent 名 ∧ ∌ 3 sentinel」＝sentinel を避けた自由 prose を roster 領域に混ぜると素通り。→ **各行が roster 行（backtick agent 名を含む or 既知 scaffold 行）であることを assert** する行単位チェックへ強化＝真に「==roster」を担保（agent 追加にも追従）。実測: smuggle prose 行を検知。

```claims
verdict: approve
tests_green: true
no_stubs: true
second_opinion:
  verdict: approve_with_notes
  notes: 6論点（除外機構/濫用ガード/後方互換/drift 回帰/budget値・CLAUDE.md650/仕様乖離）を実走検証し全て健全。2件の非ブロッカー note を fix-forward で解消＝note1(nested コメント誤り→訂正)・note2(濫用ガードが ⊆ で == でない→各行 roster 行を assert する行単位チェックへ強化で真の ==roster を担保)。除外機構・後方互換・drift・budget 値は 1次と一致。
  divergence_points: ["context_budget.py:27 コメント『nested strips nothing』が事実誤り（nested は first-start..first-end を strip）→ 訂正済", "test_context_budget.py 濫用ガードが ⊆ agent名∧∌sentinel で docstring の ==roster より弱い→ 行単位『各行が roster 行』チェックへ強化済"]
```
