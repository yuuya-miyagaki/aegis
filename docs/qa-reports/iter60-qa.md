# iter60 QA レポート（qa ゲート）

- 対象: iter60・実装 `acc2ad4`＋grill-code fix-forward `c971894`＋review fix-forward `f8974f1`（budget ratchet policy 見直し＝drift 支配構造の計数除外）
- 仕様: `docs/specs/2026-07-06-iter60-budget-exclusion-design.md`
- 計画: `docs/plans/2026-07-06-iter60-budget-exclusion-plan.md`
- review ゲート: approved（`docs/qa-reports/iter60-review.md`・1次 approve / 盲検2次 approve_with_notes・note1/2 fix-forward 解消）

## 機能対照表（plan 受入条件 × 検証）

| # | plan の受入条件 | 検証方法 | 判定 |
|---|----------------|---------|------|
| 1 | 除外ロジック（`_strip_excluded`/`_budget_word_count`）を check/tighten/seed の3経路統一 | context_budget.py 実読・3経路とも `_budget_word_count`・M2 mutation で実証 | ✅ PASS |
| 2 | routing.md roster をマーカーで囲み budget 90→70（strip 後 prose のみ） | `_budget_word_count(routing.md)`=70・budget 70/70 境界 PASS | ✅ PASS |
| 3 | fail-graceful（unmatched は全計数＝bloat を隠さない） | `test_unmatched_marker_counts_everything` PASS（実測 unmatched=93全計数） | ✅ PASS |
| 4 | 濫用ガード（除外領域==roster・多領域封鎖・allowlist） | 行単位 ==roster＋`len==1`＋allowlist トリップワイヤ・smuggle 検知を実走 | ✅ PASS |
| 5 | drift 回帰なし（マーカー追加で roster 引き続き pin） | `check_reference_drift.py` exit 0（backtick 抽出に非干渉） | ✅ PASS |
| 6 | 後方互換（他19ファイル計数不変・CLAUDE.md 650 内） | 既存 TestCheck/TestRatchet PASS・CLAUDE.md 641/650・contract exit 0 | ✅ PASS |
| 7 | full suite が緑 | `python3 -m pytest -q` 1056 passed / 2 skipped | ✅ PASS |

未達項目なし・ブロッカーなし。

## テスト強度ドリル（B1 SKIP＋実 mutation demo）

**B1 SKIP**（`docs/qa-reports/test-strength.drill` に `{"skip": true, ...}`）。理由＝コードは per-task コミット済み（acc2ad4/c971894/f8974f1）で qa 承認時の working-tree diff が空＝auto-drill が拾う未コミット追加行が無い（qa-verification skill の想定内縁ケース）。ただし context_budget.py は振る舞いコードゆえ、**実 mutation を手動で実演**（iter59 の token-pin demo より強い・実測）：

- **M1** `_strip_excluded` を恒等（`return text`）に変異 → `test_excluded_region_not_counted` **FAILED** → revert で GREEN。除外ロジックの中核を守る。
- **M2** `_budget_word_count` を strip 抜き（`word_count(text)`）に変異 → `test_real_repo_check_is_green` **FAILED**（routing.md 90>70）→ revert で GREEN。3経路統一を守る。
- **RED-first**: 実装時に除外2＋濫用ガードが実装/マーカー前に FAILED（116>20／0領域）→ 後 GREEN。
- **fix 実証**: allowlist トリップワイヤ（偽マーカーが `_EXCLUDE_RE` にマッチ＝別 target で FAIL）＋行単位 ==roster ガード（smuggle prose 行を検知）を実走確認。

## テスト実行結果

| 検査 | コマンド | 結果 |
|------|---------|------|
| context_budget | `pytest tests/test_context_budget.py -v` | 14 passed（除外2＋濫用ガード2 新規） |
| フルスイート | `python3 -m pytest -q` | **1056 passed, 2 skipped, 0 failed**（HEAD f8974f1・manual green 記録） |
| 予算 | `python3 scripts/context_budget.py` | exit 0（routing.md 70/70 境界 PASS） |
| 参照ドリフト | `python3 scripts/check_reference_drift.py` | exit 0（roster 引き続き pin） |
| フレームワーク契約 | `python3 scripts/check_framework_contract.py` | exit 0（CLAUDE.md 641/650） |

## 判定

**PASS。** plan 受入条件7項目すべて PASS・ブロッカーなし。B1 は縁ケースで SKIP＋実 mutation demo（M1/M2 で実 RED を実測）＋RED-first＋fix 実証を提示。

```claims
verdict: approve
tests_green: true
no_stubs: true
```
