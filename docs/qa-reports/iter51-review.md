# iter51 レビュー — 確認(permission prompt)交通整理 第一スライス

- 対象: 安全な読み取り/診断系コマンドの `permissions.allow` 同梱
- 参照: plan `docs/plans/2026-06-28-permission-prompt-allowlist-implementation-plan.md` / spec `docs/specs/2026-06-28-permission-prompt-allowlist-design.md`
- diff: `templates/hooks.template.json` / `bin/setup.sh`(generate_settings) / `tests/test_permission_allowlist_install.py`(新規)

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 状態 | 備考 |
|---|------------|------------|------|------|
| 1 | テンプレに allow set | `templates/hooks.template.json` | 完了 | 10 エントリ（gadget 2件除外後） |
| 2 | filtered で permissions carry | `bin/setup.sh` generate_settings | 完了 | 全プロファイル同梱 |
| 3 | merge で allow union | `bin/setup.sh` generate_settings | 完了 | framework-authoritative＋user 保持・冪等 |
| 4 | negative/moat テスト | `tests/test_permission_allowlist_install.py` | 完了 | 9 テスト |

未着手タスクなし。

## findings（severity・confidence・disposition）

| severity | finding | 出所 | disposition |
|---|---|---|---|
| 🔴 Critical (conf9) | `record-test-result.py` は CLI 引数を `drill._execute` で実行する exec gadget。allow 化で任意コマンドが無プロンプト実行（`scripts/record-test-result.py:33`） | grill-code | **修正済**: allow から除外＋negative テスト |
| 🟡 Major (conf8) | `run-test-strength-drill.py` は `.drill` 由来コマンドを subprocess 実行 | grill-code | **修正済**: allow から除外 |
| 🟡 Major (conf8) | `out['permissions']` を無条件再代入＝将来テンプレに deny/ask が増えると全プロファイルで silent drop（`bin/setup.sh`） | 盲検2次 (reviewer-maintainability) Finding2 | **修正済**: `dict(out.get('permissions',{}))` で他キー保全＋fresh dict |
| 🟡 Major (conf7) | `build-judge-card.py` は drill モジュールを import（将来 `_execute` 配線リスク）。現状は `added_lines_by_file`/`resolve_diff_ref` のみで exec 到達なし | 盲検2次 Finding1 | **対応済**: JSON はコメント不可ゆえ guard テスト追加（allow-listed script が `._execute(` を呼ばないことを assert） |
| 🟢 Minor (conf8) | full profile の `out=dict(template)` 浅コピーで template['permissions'] を破壊的変更 | grill-code | **修正済**: fresh dict |
| 🟢 residual (conf7) | `pytest` と `check_status`（gate flow で drill を subprocess）は repo 由来のテスト/.drill コードを無プロンプト実行しうる | grill-code/2次 | **security ゲートで明記**: repo-write 必須＝攻撃者が既に侵入済みの前提・標準テストランナーと同クラス。deny-hooks は Bash コマンド自体を検査 |
| 🟢 Minor (conf7) | `Bash(git diff:*)` は `git --no-pager diff` に不一致（稀・呼び出し側回避） | 盲検2次 Finding4 | 受容・plan に明記済 |

## moat 確認

- deny/ask hooks（check-destructive/check-control-plane/check-secrets/check-*-gate）無改変＝`test_install_preserves_deny_hooks` で登録維持を assert。
- §0 検証: settings allow は hooks を bypass しない／複合コマンドはセグメント単位マッチ＝`cmd && rm` は auto-approve されない。
- `update-gate.sh`/`update-task.sh`/破壊系は allow 不在（negative assert）＝会話ハードゲート維持。

## tests

- full suite **1166 passed / 1 skipped**（手動実行）。新規テスト 9 件 green。
- 形式 evidence（record-test-result green）は qa ゲートで記録（review は test 実行の領分外＝tests 🟡 は ack 可）。

## verdict

Critical/Major は全て実装内で解消済み。残りは documented residual（security で扱う）と Minor 受容。**approve_with_notes**。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "2次が Finding2（full-profile での将来 deny/ask clobber）を独立指摘＝1次(grill-code)未検出→修正済"
    - "2次が build-judge-card の将来 exec 配線リスクを指摘→JSON コメント不可のため guard テストで対応"
```
