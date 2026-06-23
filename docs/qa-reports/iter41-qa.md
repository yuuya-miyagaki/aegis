# iteration 41 Batch 1 — QA Report

- date: 2026-06-24
- task: framework / L
- test command: `python3 -m pytest -q`（record-test-result で green 記録）／`python3 scripts/check_framework_contract.py`／`python3 scripts/status_doctor.py --root .`

## 機能対照表

| # | 要件/plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|----------------|---------|---------|------|
| D1 | standard で judge gate 承認可能 | standard install の judge toolchain 同梱 | 一時 target に `setup.sh --profile=standard` → scripts/{build-judge-card,run-test-strength-drill,record-test-result}.py 同梱を ls 確認＋`check_framework_contract.py --profile=standard` PASS | PASS |
| D2 | completion 強制 hook が配線される | standard install + active settings の Task hook 登録 | 同 install で hooks/check-task-{created,completed}.sh 同梱＋生成 settings に TaskCreated/TaskCompleted 確認・contract full に check_active_settings_core_hooks 追加 PASS | PASS |
| D3 | upgrade で framework 上書き・user 保全 | re-install 挙動 | tests/test_setup_upgrade_overwrite.py（stale hook 上書き＋.bak／user STATUS 保全／identical で .bak 無し） | PASS |
| D4 | 壊れ settings を警告 | setup.sh parse 失敗経路 | tests/test_setup_broken_settings.py（WARNING+could not be parsed+.bak） | PASS |
| I1 | post-status-audit fail-closed | lib 欠落時の挙動 | tests/test_post_status_audit_fail_closed.py（safety.sh 欠落→PostToolUse block・exit0／POSTTOOL marker／12-hook identity 非破壊） | PASS |
| I2 | 完了evidence fail-closed | check-completion-evidence | tests/test_completion_evidence_fail_closed.py（STATUS 不在/None-frontmatter→exit1）＋test_check_status.py 更新 | PASS |

実装漏れなし（全機能に検証対象が存在）。

## テスト強度（mutation drill）

- **skip-drill**（`docs/qa-reports/test-strength.drill`）。理由: framework 混在 L diff に B1 が構造的に適用不能（LEARNINGS conf9）。
- **代替実証＝RED-first TDD**: 6 fix すべてで失敗テストを先に書き、fix 無し状態（=mutant 相当）で赤化を実測してから GREEN 化。
  - D1: `test_standard_requires_gate_blocking_judge_scripts` → 不在で FAIL 実測。
  - D2: `test_standard_profile_includes_task_hooks` / `test_contract_core_hook_check_behaviour`（AttributeError→定義後 PASS）。
  - D3: `test_upgrade_overwrites_framework_hook_but_preserves_user_docs` → stale hook 残存で FAIL 実測。
  - D4: `test_broken_existing_settings_emits_warning` → 警告なしで FAIL 実測。
  - I1: `test_fail_closed_when_safety_lib_missing` / `test_posttool_fallback_emits_block_schema` → marker 不在で FAIL 実測。
  - I2: `test_absent_status_is_violation` / `test_frontmatter_none_is_violation` → rc0 で FAIL 実測。

## エビデンス

- full suite: **1053 passed, 1 skipped**（record-test-result で green 記録・fingerprint bind 済）。
- contract（full）: PASS（版 1.14.0 据置）。
- status_doctor: PASS。
- standard 配布検証: `setup.sh --profile=standard` rc=0 → `check_framework_contract.py --profile=standard` PASS（judge toolchain + Task hooks 同梱を実機確認）。
- lint/type-check/build: 該当なし（bash + python stdlib・`bash -n` 構文チェック PASS）。

## 判定

**PASS。** ブロッカーなし。
