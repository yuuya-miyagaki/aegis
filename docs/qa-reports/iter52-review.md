# iter52 レビュー — allow-list read-only 完全性ガード＋拡張

- 対象: scripts 分類駆動の `permissions.allow` 完全性ガード＋読み取り専用スクリプト 3 件＋`git show` の allow 拡張
- 参照: plan `docs/plans/2026-06-28-permission-allowlist-completeness-implementation-plan.md` / spec `docs/specs/2026-06-28-permission-allowlist-completeness-design.md`
- diff: `tests/test_permission_allowlist_install.py`（分類表＋6 テスト追記）/ `templates/hooks.template.json`（allow 4 エントリ追加）/ `README.md`（allow 節更新）。production code 無改変。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 状態 | 備考 |
|---|------------|------------|------|------|
| 1 | SCRIPT_CLASS 分類表＋完全性ガード 6 テスト（RED） | `tests/test_permission_allowlist_install.py` | 完了 | 18 entrypoints 全分類・RED 2件確認後 GREEN |
| 2 | allow 4 エントリ追加（GREEN） | `templates/hooks.template.json` | 完了 | check_reference_drift/learnings_search/lint_names＋git show（context_budget は除外） |
| 3 | README allow 節更新 | `README.md` | 完了 | readers 列挙更新＋完全性ガード言及 |

未着手タスクなし。

## findings（severity・confidence・disposition）

| severity | finding | 出所 | disposition |
|---|---|---|---|
| 🔴 Critical (conf9) | `context_budget.py` は `check` モードは読取だが `--tighten`/`--seed` で追跡対象 `scripts/context-budgets.json`（contract ゲーティング config）を `save_budgets()`→`write_text` で書込む。blanket matcher `Bash(...:*)` は write モードを除外できず、auto-allow すると無プロンプトで config 改変可能（`scripts/context_budget.py:36`） | grill-code | **修正済**: `must_prompt` に再分類し allow から除外＋`test_non_safe_scripts_are_not_allowed` でガード |
| 🟡 Should (conf7) | `_rep_invocation` が `python3` 固定＝将来 `safe_auto_allow` な `.sh` が出ると membership テストが false RED | grill-code | **修正済**: 拡張子で runner 分岐（`.sh`→`bash`） |
| 🟢 Minor (conf7) | `SHOULD_MATCH` の `learnings_search.py` 呼出例が positional `mutation`＝実体は `--query`（`tests/...:33`）。テストは prefix 一致のみで非実行ゆえ無破壊だが例として不正確 | 盲検2次 (reviewer-testing) Minor1 | **修正済**: `--query mutation` に訂正（plan も同期） |
| 🟢 Minor (conf6) | `test_script_class_consistent_with_should_lists` は SHOULD リストに載るスクリプトのみ照合＝大半は cross-check されず冗長 | 盲検2次 Minor2 | **受容**: primary 2 テスト（safe⊆allow / 非safe∩allow=∅）が全数担保。2次も「保護に gap なし」と評価 |
| 🟢 Minor (conf5) | `_enumerated_scripts` は非再帰 glob＝将来 `scripts/lib/*.py` 入れ子は drift trip を素通り | grill-code | **受容**: 現状 `scripts/` はフラット・入れ子は規約外。将来入れ子化時に rglob 化 |

## moat 確認

- allow はプロンプト抑制のみ＝deny/ask hooks（check-destructive/check-control-plane/check-secrets/check-*-gate）無改変・独立発火。`test_install_preserves_deny_hooks` で登録維持を assert。
- `must_prompt` 分類（context_budget・record-test-result〔exec gadget〕・run-test-strength-drill・run_eval・eval_*・update-gate・update-task）は allow 不在を `test_non_safe_scripts_are_not_allowed` で negative assert＝会話ハードゲート維持。
- 安全 git-read は `status/log/diff/show` のみ。`git branch -D`/`remote remove`/`checkout .` 等 destructive 副形は allow 不在を `test_safe_git_reads_allowed_destructive_excluded` で assert。
- 完全性ガードは fail-closed：未分類スクリプト・mutator の allow 混入・orphan エントリをいずれも赤で検出（2次が 4 脅威シナリオ全カバーを独立確認）。

## tests

- allowlist テストファイル **15 passed**（grill-code＋Minor1 修正後・手動実行）。新規 6 テスト＋既存 9 件 green。
- full suite は T3 で **1172 passed / 1 skipped**。以降の修正は allowlist テストファイル＋hooks.template.json（data）＋docs のみ＝影響範囲は allowlist ファイルに限定（再実行 15 passed）。**権威ある full suite 再走は qa ゲートで実施**（test 実行は qa の領分）。

## verdict

🔴 Critical（context_budget 誤分類）は実装内で解消（安全側＝allow から除外）。🟡 Should も解消。残りは Minor 受容。安全側に倒れ設計（read-only のみ allow）に忠実。**approve_with_notes**。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "2次(reviewer-testing)は classification を独自にソース照合し全件正当と確認＝1次(grill-code)の context_budget 是正後の分類を独立追認"
    - "2次が SHOULD_MATCH の learnings_search 呼出例の不正確（positional vs --query）を独立指摘→修正済"
    - "2次が consistency テストの coverage が冗長と指摘＝保護 gap なしと評価し受容"
```
