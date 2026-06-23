# iteration 41 Batch 1 — Review Report

- date: 2026-06-24
- task: framework / L / 配布正常化（D1-D4）＋整合性 fail-closed 化（I1-I2）
- 参照: docs/full-review-2026-06-24-hooks-gates-distribution.md, docs/plans/2026-06-24-iter41-batch1-implementation-plan.md, docs/specs/2026-06-24-iter41-batch1-distribution-integrity-design.md

## 対照表（plan タスク ↔ 実装 ↔ 状態）

| # | plan タスク | 実装ファイル | テスト | 状態 |
|---|------------|------------|--------|------|
| D1 | standard に judge toolchain 同梱（required: builder+drill / recommended: record+fingerprint）＋README 件数 | templates/profiles/standard.json, README.md | tests/test_profile_judge_toolchain.py | 完了 |
| D2 | Task hooks を profile(hooks_include+required_hook_scripts)+active settings+contract self-check に配線 | templates/profiles/standard.json, .claude/settings.local.json(untracked), scripts/check_framework_contract.py | tests/test_task_hook_wiring.py | 完了 |
| D3 | upgrade で framework 所有を .bak つき上書き・user 所有は保全 | bin/setup.sh (copy_file_force diff-gated, is_framework_owned, copy_file_routed) | tests/test_setup_upgrade_overwrite.py | 完了 |
| D4 | 壊れ settings を無警告全消しせず警告 | bin/setup.sh (generate_settings heredoc) | tests/test_setup_broken_settings.py | 完了 |
| I1 | post-status-audit を PostToolUse fail-closed 化 | hooks/post-status-audit.sh, hooks/lib/safety.sh | tests/test_post_status_audit_fail_closed.py | 完了 |
| I2 | 完了evidence を STATUS 不在/None-frontmatter で violation 化 | scripts/check_status.py | tests/test_completion_evidence_fail_closed.py, tests/test_check_status.py(更新) | 完了 |

未着手タスクなし。スコープ外（I3/G1-G3/C1-C4・check-control-plane 再設計）は意図的に不実施（design のスコープ境界どおり）。

## findings（severity 付き）

- **Critical（修正済）** `scripts/check_framework_contract.py` — 当初 `check_active_settings_core_hooks` が gitignore された `.claude/settings.local.json` 不在を FAIL 扱い＝fresh clone / CI が非再現的に赤化。**修正済**: 不在＝skip（`[]`）、存在時 drift のみ FAIL。永続保証は追跡対象 profile/template 側。confidence 9。
- **Minor（修正済）** `bin/setup.sh:is_framework_owned` — `bin/*` 未分類（live defect なし）。完全性のため `bin/*` を追加＋注記。confidence 8。
- **Minor（修正済）** `bin/setup.sh` hooks/lib ループが `copy_file_force` 直呼びで `copy_file_routed` と二系統＝注記追加。confidence 9。
- **Low/residual（受容）** `bin/setup.sh` の `.bak`/上書きは symlink を辿る＝事前 CP 書込み済（既に game-over）でのみ悪用可＝SF-004 と同クラスで受容。confidence 8。
- **Minor（no action）** `safety.sh` の deny/block helper 重複は byte-identity 契約により意図的（LEARNINGS 記録済）。

## Evidence Checklist

- [x] diff を実読（git diff HEAD + 新規 test 6 本）
- [x] plan/spec 受入条件と突合（対照表）
- [x] エッジケース列挙（fresh clone 非再現・symlink・diff-gate no-op・byte-identity・fail-closed blast radius）
- [x] 全 finding に severity+confidence 付与
- [x] full suite 1053 passed/1 skipped・contract full PASS・status_doctor PASS・standard install で `--profile=standard` PASS（judge toolchain+Task hooks 同梱を実機確認）

## PASS/FAIL 判定

**PASS。** Critical は修正済、残りは Minor/受容。スコープ完全充足、退行なし。

```claims
second_opinion:
  reviewer_security:
    verdict: approve_with_notes
    divergence_points: ["D3 .bak/overwrite が symlink を辿る（Low/SF-004 受容クラス）"]
  reviewer_maintainability:
    verdict: approve_with_notes
    divergence_points: []
```
2 件の独立盲検（security / maintainability・1次 verdict 非共有・diff と spec/plan のみ）を実走。両者 approve_with_notes、Critical/Major なし、acceptance からの divergence なし。security の Low note と maintainability の Minor note は反映済（symlink は受容記録、bin/ 分類と lib ループ注記は是正）。
