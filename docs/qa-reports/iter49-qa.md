# iter49 QA — 配布 self-containment 射程拡大（skill→script 検査＋update-task.sh 同梱）

- 参照: plan=`docs/plans/2026-06-27-command-skill-ref-integrity-implementation-plan.md`／
  review=`docs/qa-reports/iter49-review.md`（approve_with_notes・1次/盲検2次一致）
- ui_surface: false（ブラウザ検証 N/A）

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|------------|---------|---------|------|
| 1 | skill→script 参照整合性検査 | `test_every_profile_skill_script_ref_is_self_contained` | full suite 実走＋手動 mutation | PASS |
| 2 | 抽出純関数 `_skill_script_edges` | 単体5（code-fence/inline/散文除外/hooks-lib除外/空） | pytest | PASS |
| 3 | helper drift ガード | `test_shipped_scripts_helpers_consistent` | pytest | PASS |
| 4 | update-task.sh 同梱（standard+full required） | `test_update_task_shipped_in_dev_profiles` | pytest＋手動 rename mutation | PASS |
| 5 | allow-list reason/rot | `test_skill_allowlist_reasons_nonempty`/`_no_stale_entries` | pytest（空＝vacuous・将来活性） | PASS |
| 6 | README 件数同期 | `test_readme_profile_counts.py` | pytest | PASS |
| 7 | regression（全 suite） | 全テスト | pytest -q | PASS（1142+ green） |

実装漏れ（検証対象なし）= ゼロ。

## エビデンス

### テストスイート
- `python3 -m pytest -q`（全 suite）green（record-test-result で manual 記録）。
- `tests/test_profile_referential_integrity.py` 単体: 23 passed。
- contract: `python3 scripts/check_framework_contract.py` PASS。

### テスト強度（B1）— 手動 mutation 実証

auto-drill（`run-test-strength-drill.py`）は anti-gaming の coverage-floor が、本変更に必要な
**module-docstring 精度更新**（iter48→iter49 のスコープ注記＝`test_profile_referential_integrity.py:24-34/41`）
と衝突する。docstring は behavior-catching mutant を置けないため全 hunk 被覆が原理的に不能。
no-commit 制約により empty-diff スキップ経路（committed-framework 縁ケース）も使えない。
よって `.drill` は **auditable skip** を宣言し、強度は**手動 mutation で実証**した:

| mutant | 変異 | 捕捉テスト | 結果 |
|--------|------|-----------|------|
| M1 | full.json `update-task.sh`→`update-taskX.sh` | skill 横断検査（aegis-brainstorm 参照が未同梱化） | RED ✅ |
| M2 | standard.json `update-task.sh`→`update-taskX.sh` | `test_update_task_shipped_in_dev_profiles` | RED ✅ |
| M3 | `_SKILL_SCRIPT_RE` から `sh` を除去 | `test_skill_edges_picks_code_fence_sh`（抽出単体） | RED ✅ |
| M4 | `_shipped_scripts_any` から `.sh` を除去 | skill 横断検査（update-task.sh が未 shipped 化） | RED ✅ |

4/4 が RED で捕捉（survivor ゼロ）。各 mutant 適用→テスト実行→原状復帰を自動ループで実測。
加えて **RED-first TDD**: update-task.sh 未同梱で横断検査が RED（`[full] aegis-brainstorm→update-task.sh`
文言一致）→ 同梱で GREEN を二度測り済。

> coverage-floor が surface したのは standard.json:10 の rename が無保護だった点（盲検2次 F3・grill #3）。
> これは `test_update_task_shipped_in_dev_profiles` を追加して封鎖済（M2 が RED で実証）＝real weakness を是正した。

## ブロッカー

- なし。

## 判定

**PASS**。全機能に検証対象あり・全テスト green・テスト強度は手動 mutation 4/4 捕捉＋RED-first TDD で実証。
B1 auto-drill は documentation-accuracy hunk との構造的衝突により skip（理由は `.drill` に auditable に記録）。

```claims
verdict: pass
tests: "full pytest suite green (recorded manual green); test_profile_referential_integrity.py 23 passed; contract PASS"
b1_drill: "SKIP (auditable); 手動 mutation 4/4 caught (full/standard update-task.sh rename, _SKILL_SCRIPT_RE .sh drop, _shipped_scripts_any .sh drop) + RED-first TDD. coverage-floor が必要な module-docstring 精度 hunk と衝突するため auto-drill skip。"
blockers: none
```
