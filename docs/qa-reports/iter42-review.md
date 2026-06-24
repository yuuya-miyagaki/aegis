# iteration 42 G1-G3 — Review Report

- date: 2026-06-24
- task: framework / L / guard 網羅（G1 破壊パターン・G2 secrets git -C・G3 deploy/cron single-source）
- 参照: docs/full-review-2026-06-24-hooks-gates-distribution.md（G1/G2/G3）, docs/plans/2026-06-24-iter42-guard-coverage-plan.md

## 対照表

| # | plan タスク | 実装ファイル | テスト | 状態 |
|---|------------|------------|--------|------|
| G1 | dd of=/chmod -R/mkfs/shred/system-truncate を AEGIS_DESTRUCTIVE_CMD_REGEX へ | hooks/lib/patterns.sh | tests/test_check_destructive_coverage.py | 完了 |
| G3 | AEGIS_DEPLOY_REGEX single-source・deploy-gate 挙動保存・cron-gate import（G1 継承） | hooks/lib/patterns.sh, hooks/check-deploy-gate.sh, hooks/check-cron-gate.sh | tests/test_gate_pattern_single_source.py | 完了 |
| G2 | check-secrets が -C/--git-dir で対象 repo の staged-diff を scan | hooks/check-secrets.sh | tests/test_check_secrets_git_dir.py | 完了 |
| infra | hook 新 lib 依存に test scratch を同期 | tests/test_check_status.py（TempProjectWithHooks に patterns.sh symlink） | 既存 deploy-gate hook tests | 完了 |

未着手なし。out-of-scope（git-push-deploy / var-indirection / generic truncate / I3）は設計どおり不実施。

## findings（severity 付き・grill-code 由来は対処済）

- **Major（修正済）** `patterns.sh` truncate regex `(^|[^>])>` が `2>/etc/log`（fd redirect）を誤検知。**修正**: `(^|[^0-9>])>` で fd 番号を除外。test に `2>/etc/app.log` benign 追加。confidence 9。
- **Low（修正済）** `check-secrets.sh:_aegis_git_dir_args` が quoted `-C "/repo"` の引用符を保持。**修正**: 囲み引用符を strip（quoted-no-space を回復）。space を含む quoted path は既知限界（pre-G2 baseline と同等・SF-004 圏）。confidence 8。
- **Minor（据置・文書化）** chmod regex は `chmod 777 -R`（operand 後フラグ）を捕捉せず（常用形 `chmod -R` は捕捉）。broaden は filename `-R` 誤検知リスクで見送り。
- **Minor（据置）** `2>/etc/x` 以外の任意 fd redirect・複数 `-C` は first-match（git は last 採用）＝scope 差のみ・secret 秘匿には至らず。

## Evidence Checklist

- [x] diff を実読（git diff HEAD hooks/ + 新規 test 3 本 + test infra）
- [x] plan/spec 受入条件と突合（対照表）
- [x] エッジケース（>>/2>/`/dev/null`・chmod 複合フラグ・path 内 commit・quoted -C・複数 -C・--git-dir space/=）
- [x] 全 finding に severity+confidence
- [x] full suite 1067 passed/1 skip（record green）・contract full PASS・status_doctor PASS・bash -n 全 hook

## PASS/FAIL

**PASS。** Critical なし。grill-code の Major/Low は対処済、残り Minor は据置（文書化）。スコープ充足・退行なし（deploy-gate 挙動保存を既存 test で確認）。

```claims
second_opinion:
  reviewer_maintainability:
    verdict: approve_with_notes
    divergence_points: ["truncate regex の 2>/etc fd-redirect 誤検知（Major）→ [^0-9>] で修正済"]
  reviewer_security:
    verdict: approve_with_notes
    divergence_points: ["quoted -C path-with-space の miss（Low・pre-G2 baseline 同等・非 fresh hole）→ quote strip 追加"]
```
独立盲検2件（maintainability / security・1次 verdict 非共有・diff と spec/plan のみ）実走。両者 approve_with_notes、Critical/Major-blocking なし。両者の指摘（fd-redirect・quoted path）は本 review 確定前に修正反映済。
