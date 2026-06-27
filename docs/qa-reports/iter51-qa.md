# iter51 QA — 確認(permission prompt)交通整理 第一スライス

- 参照: plan `docs/plans/2026-06-28-permission-prompt-allowlist-implementation-plan.md`
- ドリル証拠: `docs/qa-reports/test-strength.md`（承認時にハーネス再走）

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|------------|---------|---------|------|
| 1 | テンプレに allow set | `templates/hooks.template.json` | `test_template_has_allow_set` / `test_allow_entries_match_real_invocations` | PASS |
| 2 | 全プロファイルで同梱 | `bin/setup.sh` generate_settings | `test_install_ships_allow_all_profiles[minimal/standard/full]` install e2e | PASS |
| 3 | 再 install で union・冪等 | `bin/setup.sh` generate_settings | `test_reinstall_unions_user_allow_and_preserves` | PASS |
| 4 | moat 健在（deny-hooks/除外） | install 出力＋テンプレ | `test_install_preserves_deny_hooks` / `test_template_allow_excludes_mutators_and_dangerous` / `test_allowed_scripts_do_not_invoke_command_executor` | PASS |

## テスト強度ドリル（B1）

- **DRILL PASS — 3/3 mutant caught**（baseline green・冪等）。
- mutants（追加ハンクごとに1個・tracked task code）:
  - `bin/setup.sh:334`（carry: `perms['allow']=list(...)`→`[]`）→ `test_install_ships_*` が赤化 = caught。
  - `bin/setup.sh:367`（union: `list(fw_allow)+list(...)`→`list(...)`）→ `test_reinstall_*` が赤化 = caught。
  - `templates/hooks.template.json:11`（`Bash(git status:*)`→`Bash(git xxx:*)`）→ `test_template_has_allow_set` が赤化 = caught。
- 新規 untracked テストファイルは coverage-floor の対象外（tracked task code のみ＝`bin/setup.sh`/`templates`）。

## テストスイート

- full suite **1166 passed / 1 skipped**（record-test-result green・newest manual）。
- lint/type-check: 該当なし（bash/JSON/python・contract PASS）。

## 検証項目

### 検証項目: 知識の乏しいユーザーの確認削減（量）
- 操作: 各プロファイルで install → `permissions.allow` に安全コマンドが入ることを e2e で確認。
- 期待結果（plan AC）: 全プロファイルで allow set 全件同梱・状態変更/危険系は不在。
- 実際結果: minimal/standard/full すべてで allow set 全件。`update-gate.sh`/`update-task.sh`/破壊系は不在。
- 判定: PASS

### 検証項目: 既存ユーザ設定の非破壊（union・冪等）
- 操作: ユーザ allow＋deny＋env を置いて install ×2。
- 期待結果: framework allow ∪ user allow（重複なし）・deny/env 保持・再々 install で不変。
- 実際結果: 一致。
- 判定: PASS

## ブロッカー

なし。

```claims
verdict: pass
```
