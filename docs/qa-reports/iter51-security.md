# iter51 セキュリティレビュー — 確認(permission prompt)交通整理 第一スライス

- 参照: plan `docs/plans/2026-06-28-permission-prompt-allowlist-implementation-plan.md` / spec `docs/specs/2026-06-28-permission-prompt-allowlist-design.md`
- diff: `templates/hooks.template.json` / `bin/setup.sh` / `tests/test_permission_allowlist_install.py`

## 脅威モデル

`permissions.allow` のエントリにマッチした Bash コマンドは**無プロンプトで実行**される。よって核心リスクは「allow-listed コマンドが任意/攻撃者影響下のコマンドを無プロンプト実行できるか」。決定論 deny-hooks は allow とは独立に常時実行され moat の本体。

## OWASP 該当チェック

- [x] **Injection（Command）**: allow-listed 5 スクリプト全ての subprocess/exec sink を監査。いずれも**固定 argv**（`["bash", fp_lib, root]`／lint／git read）で `shell=True` 無し・CLI 引数が argv[0] に流れない。**実引数を実行する gadget（`record-test-result.py:33` `drill._execute(args.command)`／`run-test-strength-drill.py`）は allow から除外済み**。`test_allowed_scripts_do_not_invoke_command_executor` が「allow-listed script が `._execute(` を呼ばない」ことを回帰固定。`drill._execute`（`run-test-strength-drill.py:233-247`）自体も `shlex.split`＋`subprocess.run(argv)`＝no-shell でチェーン/リダイレクト不可（除外は defense-in-depth）。
- [x] **Sensitive Data Exposure**: diff に secrets 無し（grep 済み）。allow エントリはコマンドパターンのみ。
- [x] **Security Misconfiguration**: allow-list は狭い（個別スクリプト prefix）。複合コマンドはセグメント単位マッチ＝`git status && rm` の `rm` は auto-approve されず再プロンプト。`update-gate.sh`/`update-task.sh`/`git push`/`rm` は不在（`test_template_allow_excludes_mutators_and_dangerous`）。
- [x] **Vulnerable Dependencies**: 新規依存ゼロ（stdlib `json`/`subprocess` のみ）。
- [x] **Broken Auth**: 認証フロー変更なし（該当なし）。

## moat 健在

- hook ファイル無改変（diff は templates/setup.sh/test のみ）＝deny/ask hooks（check-destructive/control-plane/secrets/gate）はそのまま全コマンドを検査。
- merge は union のみ（ユーザ deny/ask を削除しない）。Claude Code precedence でユーザ rule が allow を上書き＝opt-out 可能。冪等。

## findings（severity・remediation）

| severity | finding | remediation |
|---|---|---|
| （修正済） record-test-result/run-test-strength-drill の exec gadget を allow から除外 | grill-code/review で発見・実装内で解消＋guard テスト | 完了 |
| 🟢 residual (Low) | `pytest`/`check_status`（gate flow で drill subprocess）は repo 由来のテスト/.drill コードを無プロンプト実行しうる | **by-design・受容**: テスト実行＝対象コード実行は不可分。攻撃には repo-write が必要（攻撃者が既に侵入済みの前提）。deny-hooks が test が shell out する危険 Bash を引き続き gate |

material finding ゼロ。deploy blocker なし。

## 検証

- full suite 1166 passed/1 skip（record green）・新規9テスト green・contract PASS。
- 盲検2次（security エージェント・fresh context）= **approve**（独立に全 allow-listed script の exec sink を監査し gadget 不在を確認・moat intact・secrets/deps clean）。1次と相違なし。

```claims
verdict: approve
tests_pass: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve
  divergence_points: []
```
