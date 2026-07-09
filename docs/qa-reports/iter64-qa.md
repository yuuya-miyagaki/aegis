# QA 記録 — iter64（fingerprint tree-hash 化＋setup OR marker 厳格化）

## 対象

- 変更: hooks/lib/fingerprint.sh（head:<sha>→非 docs/.claude committed tree-hash）＋
  bin/setup.sh（selfheal 身元判定を stamp 単独へ）＋tests/test_fingerprint_lib.py（新規3）
  ＋tests/test_setup_locked_target_upgrade.py（新規1）。実装コミット済 HEAD=992ff4f。
- 参照: plan=docs/plans/2026-07-08-iter64-fingerprint-tree-hash-plan.md／
  spec=docs/specs/2026-07-08-iter64-fingerprint-tree-hash-design.md／
  review=docs/qa-reports/iter64-review.md（1次 in-session＋テスト強度＋盲検2次 approve_with_notes）

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | docs-only コミットで fp 不変（罠 r 根切り） | fingerprint.sh | test_docs_only_commit_does_not_change_fp（RED-first） | PASS |
| 2 | code コミットで fp 変化（silent-green 保存） | fingerprint.sh | test_new_commit_changes_fp（既存・tree-hash で維持） | PASS |
| 3 | `.claude/` 除外はリテラル（aclaude/ 誤除外なし） | fingerprint.sh | test_committed_dir_resembling_dotclaude_is_not_excluded | PASS |
| 4 | root 直下 `docs` ファイルは非除外（スラッシュ要件） | fingerprint.sh | test_root_file_named_docs_is_not_excluded | PASS |
| 5 | stamp 無しで self-heal 不発（LOW-1） | setup.sh | test_cplock_present_without_stamp_does_not_self_heal（RED-first） | PASS |
| 6 | token 契約・consumer 透過・移行 fail-closed | fingerprint.sh/consumer | grep（head: は fingerprint.sh のみ）＋実 fp 出力 64-hex | PASS |

## B1 テスト強度ドリル（skip・代替実証あり）

- spec: docs/qa-reports/test-strength.drill = `{"skip": true}`。
- **skip 理由**: framework 改修・実装を per-task でコミット済み（HEAD=992ff4f・`git diff HEAD` の
  code 差分=空）。実 mutant drill を試みたが、fingerprint.sh header／setup.sh 帰属コメント／
  test docstring の**純コメント/docstring ハンク**が coverage floor（全ハンクに捕捉 mutant 必須）を
  満たせない — コメントは挙動を持たず「捕捉される mutant」を置けない。これは全体レビュー §4
  Phase 1「1-5」で floor からのコメントラン除外を予定する**既知の限界**。iter63 はコメントが
  新規関数のコード連続ハンクだったため回避できたが、本 iter はコメント**修正**のため孤立ハンクになる。
  → コミット→skip 経路（skill 明記の sanctioned edge case）を採用。
- **代替実証（手動 mutation 同等・全て本セッションで実走・review レポートに tool-call evidence）**:
  1. **RED-first**: test_docs_only_commit_does_not_change_fp は旧 head:sha 実装で FAIL 実測
     （fp が docs コミットで動く）。test_cplock_present_without_stamp は旧 OR ゲートで
     rc0＋"OS-locked" ＝ FAIL 実測。
  2. **一時変異で歯を実証（scratch コピー・repo 不触）**:
     - `[.]claude/`→bare-dot `.claude/`（fingerprint.sh:73）→ resembling が RED
     - `printf 'tree:%s' "$committed"`→定数（:109）→ new_commit_changes＋resembling が RED
     - `${tab}docs/`→スラッシュ削除 `${tab}docs`（:73）→ root_file_named_docs が RED
     - stamp ガード→OR/常真化（setup.sh:645）→ without_stamp が RED
  3. **coverage 空白の安全確認（実 git）**: committed=""（docs-only）は has-code fp と非 alias／
     root `docs` ファイル包含／ls-tree 失敗→error（fail-closed）。全て silent-green ではない。

## full suite（コミット後・新 fp で record）

- `python3 scripts/record-test-result.py "python3 -m pytest -q"` → **recorded: green**
  （1080 passed / 2 skipped・新規4テスト含む・新 tree-hash fp で記録）
- 補足: 直前に fp 定義変更（head→tree）で「stale-ref-while-pending」の contract test が
  一過性 red 化する事象を観測（review ref を gate 承認前に置いた運用ミス）。ref を null 化→
  gate 整合で解消し、正しい順序（record green→ref 設定→承認）で再実施。全体レビュー 1-3
  「approve --ref 原子化」で将来機械化予定の罠。

## 判定

```claims
verdict: approve
notes: ["B1 drill=skip（実装コミット済・diff 空／純コメントハンクは floor 除外の既知限界=全体レビュー1-5）", "代替実証: 4新規テスト RED-first＋4種一時変異で歯を実証＋coverage空白3件を実gitで安全確認（review レポートに記録）", "full suite 1080 passed/2 skipped を新 tree-hash fp で recorded green", "移行: 既存 record は初回 unverified（fail-closed・ship note で周知）"]
```
