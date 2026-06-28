# iter52 QA — allow-list read-only 完全性ガード＋拡張

- 参照: plan `docs/plans/2026-06-28-permission-allowlist-completeness-implementation-plan.md`
- ドリル証拠: `docs/qa-reports/test-strength.md`（承認時にハーネス再走）

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|------------|---------|---------|------|
| 1 | 全 scripts 分類済（drift trip） | `tests/test_permission_allowlist_install.py` | `test_every_script_is_classified`（missing/stale 双方向） | PASS |
| 2 | safe ⊆ allow（実 auto-allow 証明） | template + テスト | `test_safe_auto_allow_scripts_are_allowed`（`_matches` で実証） | PASS |
| 3 | 非 safe ∩ allow = ∅（fail-closed） | template + テスト | `test_non_safe_scripts_are_not_allowed` | PASS |
| 4 | 安全 git-read ⊆ allow・destructive 除外 | template + テスト | `test_safe_git_reads_allowed_destructive_excluded` | PASS |
| 5 | orphan allow 無し | template + テスト | `test_no_orphan_script_allow_entry` | PASS |
| 6 | SHOULD リスト ↔ SCRIPT_CLASS 整合 | テスト | `test_script_class_consistent_with_should_lists` | PASS |
| 7 | allow 拡張（3 scripts + git show）全 profile 同梱 | `templates/hooks.template.json` + install e2e | `test_allow_entries_match_real_invocations` / `test_install_ships_allow_all_profiles[minimal/standard/full]` | PASS |
| 8 | moat 健在（deny-hooks/exec gadget 除外） | install 出力＋テンプレ | `test_install_preserves_deny_hooks` / `test_allowed_scripts_do_not_invoke_command_executor` | PASS |

> README 更新（allow 節）は docs フェーズへ送り（docs-sync の領分＋B1 floor の非テスト面回避）。本 iteration の qa スコープ外。

## テスト強度ドリル（B1）

- **DRILL PASS — 5/5 mutant caught**（baseline green・冪等・承認時ハーネス再走）。
- mutants（追加ハンクごとに 1 個・tracked task code＝tests＋template、docs は floor 対象外）:
  - `tests/...py:12`（`import re`→破壊）→ 全 re 依存テストが赤化 = caught。
  - `tests/...py:31`（`"git show HEAD"`→`"git showZ HEAD"`）→ `test_allow_entries_match_real_invocations` 赤化 = caught。
  - `tests/...py:210`（`record-test-result.py` を `must_prompt`→`safe_auto_allow` に誤分類）→ `test_safe_auto_allow_scripts_are_allowed` 赤化 = caught（exec gadget 誤許可を捕捉）。
  - `templates/hooks.template.json:9`（`check_reference_drift.py`→`check_reference_driftX.py`）→ `test_safe_auto_allow_scripts_are_allowed` 赤化 = caught。
  - `templates/hooks.template.json:17`（`Bash(git show:*)`→`Bash(git showX:*)`）→ `test_safe_git_reads_allowed_destructive_excluded` 赤化 = caught。

## テストスイート

- full suite **1172 passed / 1 skipped**（`record-test-result` green・newest manual エントリ）。
- lint/type-check: 該当なし（python/JSON・contract PASS・status_doctor PASS）。

## 検証項目

### 検証項目: read-only スクリプトの確認削減（全プロファイル）
- 操作: install → `permissions.allow` に `check_reference_drift`/`learnings_search`/`lint_names`＋`git show` が乗ることを e2e で確認。
- 期待結果（plan AC）: 全プロファイルで拡張 allow 同梱・mutator/exec/destructive は不在。
- 実際結果: minimal/standard/full すべてで拡張 allow。`context_budget`（write モード持ち）/`record-test-result`/`update-*`/`git branch -D` 等は不在。
- 判定: PASS

### 検証項目: 分類ガードの fail-closed 性（drift 検出）
- 操作: B1 ドリルで「mutator を safe に誤分類」「safe スクリプトを allow から外す」を注入。
- 期待結果: いずれもテストが赤化し承認を阻止。
- 実際結果: 5/5 caught。未分類スクリプト・orphan も双方向 assert で捕捉。
- 判定: PASS

## ブロッカー

なし。

```claims
verdict: pass
```
