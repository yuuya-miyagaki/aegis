# v0.12.2 Hot-fix Review Report

Date: 2026-05-08 着手 / 2026-05-10 実装完了 / 2026-05-14 Round 6+7 反映 / 2026-05-15 Round 8+9 反映
Reviewer: External (IDE Chat Opus 4.6 — Round 1〜9 で指摘・修正済み)
Branch: `hotfix/v0122-hook-schema`
計画: `docs/plans/v0130-modernization-plan.md` Revision 5

## Verdict

**SHIP READY** — Phase 0a 実装 + Round 6 (P1×2, P2×1) + Round 7 (P1×1, P3×1) + Round 8 (P2×1, P3×1) + Round 9 (P3×2、コメント整合) すべて反映完了。Round 8/9 レビュアー最終判定「実装は GO」を 2 回受領済み。公式 docs (Claude Code Hooks reference) との出力スキーマ完全一致も確認済み。ユーザーの最終 commit + tag 判断待ち。

---

## Round 6 レビュー対応（2026-05-14）

| # | 指摘 | Priority | 修正内容 | 検証 |
|---|---|---|---|---|
| R6-1 | PreCompact block JSON が `exit 2` で無視される（公式 docs: exit 2 だと stdout JSON は無視され stderr feedback 扱い） | **P1** | `hooks/pre-compact.sh` の block 経路で `exit 2` → **`exit 0`** に変更。コメントに「exit 2 だと stdout JSON は無視」と注記 | `assert_precompact_block` の rc==0 検証で発火 → PASS |
| R6-2 | minimal-project の hooks 11 件 と `.claude/settings.json` が旧形式のまま（scaffold 利用者へ壊れた PaC を配布するリスク） | **P1** | `examples/minimal-project/hooks/` 全 11 ファイル + `.claude/settings.json` を本体から `cp` で同期。`diff -r hooks/ examples/minimal-project/hooks/` および `diff templates/hooks.template.json examples/minimal-project/.claude/settings.json` で **0 件差分** を確認 | 本体と minimal-project の完全同期を `diff` で確認 |
| R6-3 | PreCompact テストが stdout JSON のみ検証、exit-code 契約を漏らしていた（stdout JSON + exit 2 でも PASS していた） | P2 | テストヘルパー `assert_precompact_block` / `assert_precompact_allow` に `rc: int \| None` 引数を追加し、block / allow とも `rc == 0` を assert。テスト側で `rc=rc` を渡す形に更新 | tier 1 PASS、`python3 -m unittest discover -s tests` で 134 tests PASS（新規 `test_hook_output_schema.py` 12 件含む総数） |

### Round 6 修正後の検証

- `python3 -m unittest discover tests` → **134 PASS** (新規 12 ケースも含む)
- `python3 scripts/run_eval.py --tier 1` → **PASS**
- `diff -r hooks/ examples/minimal-project/hooks/` → 差分 0 件
- `diff templates/hooks.template.json examples/minimal-project/.claude/settings.json` → 差分 0 件
- `grep -n 'exit 2' hooks/pre-compact.sh` → 0 件（block 経路から exit 2 完全撤去）

---

## Round 7 レビュー対応（2026-05-14）

レビュアー判定: **GO 寄り**、ただし下記 2 件は ship 前に修正。

| # | 指摘 | Priority | 修正内容 |
|---|---|---|---|
| R7-1 | リリース手順（§ 6）の `git add` 対象に minimal-project の修正が含まれていなかった。この手順どおり commit すると P1 だった scaffold 側の修正が未コミットのまま残るリスク | **P1** | § 6 リリースコマンドを複数行に展開し、`examples/minimal-project/hooks/` と `examples/minimal-project/.claude/settings.json` を `git add` 対象に明示的に追加 |
| R7-2 | テスト件数表記の「134 + 12 = 146」が誤解を招く（実際は `python3 -m unittest discover -s tests` で 134 件、これは新規 12 件を含む総数） | P3 | Round 6 表のエビデンス欄と § 3.2 タイトル・本文を「134 件（新規 12 件を含む総数）」と明示する形に修正 |

### Round 7 修正後の検証

実装ファイルへの変更は **ゼロ**（テスト・hook・設定ファイルすべて無変更）、ドキュメント表記のみの修正:

- `python3 -m unittest discover -s tests` → **134 tests PASS**（再現確認、レビュアー側でも確認済み）
- `python3 scripts/run_eval.py --tier 1` → **PASS**（レビュアー側で `--tier 2` も PASS 確認済み）
- ドキュメントの整合性確認: 実装方針を語る箇所（§ 2〜§ 4 および § 6 リリース手順）からは旧表記（`134+12=146`、`既存: 134 ケース` 等）を排除済み。Round 6 / 7 セクション内の指摘引用は履歴として残置（自己マッチを避けるため grep ベース検証は省略）。新規 § 3.2 タイトル「全体: 134 ケース（新規 12 件を含む総数）」に統一。

---

## Round 8 レビュー対応（2026-05-15）

レビュアー最終判定: **「実装は GO」**、紙面整合の最終仕上げとして下記 2 件のみ修正。

| # | 指摘 | Priority | 修正内容 |
|---|---|---|---|
| R8-1 | tier 1 の証跡（`status_doctor PASS / Result: PASS`）が現在の出力（`status_doctor WARNING / Result: PASS (with warnings)`）と一致しない。原因は `docs/STATUS.md` の `last_updated: "2026-05-08T00:00:00Z"` が 2026-05-15 時点で stale 判定に入ったため | P2 | `docs/STATUS.md` line 12 の `last_updated` を `"2026-05-15T00:00:00Z"` に更新。再実行で `status_doctor PASS` / `Result: PASS`（warning なし）を確認 |
| R8-2 | Round 7 検証コマンド `grep -nE "146\|134 \+\|134 ケース"` が自己マッチ（Round 7 セクション本文の指摘引用と検証コマンド行自体にヒット、再現不能） | P3 | grep ベース検証を廃止し、「実装方針を語る箇所からは旧表記を排除済み、Round 6/7 セクションの指摘引用は履歴として残置」という文章ベース表現へ変更 |

### Round 8 修正後の検証

実装ファイルへの変更は **ゼロ**（テスト・hook・設定ファイルすべて無変更）、ドキュメントメタデータと検証表記の修正のみ:

- `python3 scripts/run_eval.py --tier 1` → **PASS**（`status_doctor` も完全 PASS、warning なし）

```
=== Tier 1 Evaluation ===
  Validator                      Status
  ------------------------------ ----------
  check_status                   PASS
  status_doctor                  PASS
  check_framework_contract       PASS
  check_reference_drift          PASS
Result: PASS
```

---

## Round 9 レビュー対応（2026-05-15）

レビュアー判定: **「実装は GO」**（tier 1/2 PASS、本体と minimal-project の完全同期確認済み、公式 docs と出力スキーマ一致確認済み）。コメントの紙面整合のみ修正:

| # | 指摘 | Priority | 修正内容 |
|---|---|---|---|
| R9-1 | `hooks/pre-compact.sh:10-12` のヘッダーコメント「2 = block compaction (Claude Code PreCompact convention)」が、Round 6 で `exit 2` → `exit 0` に変更した実装方針と不一致のまま | P3 | ヘッダーコメントを v0.12.2 採用方針に合わせて書き換え。「PreCompact docs は exit 2 と JSON `decision:block` の両方を許可するが、両者は mutually exclusive。aegis v0.12.2 採用方針は **JSON block + exit 0**」と明記。将来の巻き戻り防止 |
| R9-2 | `hooks/post-status-audit.sh:6-8` のヘッダーコメント「hooks.template.json uses an `if` filter」が、Phase 0a で `if` 削除した実装と不一致のまま | P3 | ヘッダーコメントを「v0.12.2 で `if` 削除済み。spec 上 `if` は単一 permission rule のみ許容（`&&`/`\|\|`/list 不可）、これが前回の `Edit(*STATUS.md) \|\| Write(*STATUS.md) \|\| NotebookEdit(*STATUS.md)` を silently ineffective にしていた。matcher `Edit\|Write\|NotebookEdit` 登録 + script 側の `case TARGET_FILE in *STATUS.md` filter が全 3 ツールをカバー」に書き換え |

### Round 9 修正後の検証

実装ファイル自体への変更は **ゼロ**（コメント修正のみ、ロジック無変更）。両 hook の本体と minimal-project ミラーを同期した上で再検証:

- `diff -r hooks/ examples/minimal-project/hooks/` → 差分 0 件（コメント修正後も完全同期維持）
- `python3 scripts/run_eval.py --tier 1` → **PASS**
- `python3 -m unittest discover -s tests` → **134 tests PASS**

---

---

## 1. 背景

aegis v0.12.1 までの全 hook（11/12 件）は **Claude Code 1.x 系の出力形式**を使っており、現行の 2.x 仕様に照らすと `deny` / `block` が **silently ignored** されていた可能性が高い。すなわち、PaC（Policy as Code）の安全層が事実上機能していなかった。

5 ラウンドの外部レビュー（計 25 件指摘）でこの陳腐化が判明し、v0.13.0 計画 Rev.5 の Phase 0a として hot-fix を切り出した。

## 2. 実装範囲

### 2.1 変更ファイル一覧（13 ファイル）

#### Hook 出力スキーマ修正（11 hooks）

| # | ファイル | Event | 変更箇所数 |
|---|---|---|---|
| 1 | `hooks/check-gate.sh` | PreToolUse | 4 |
| 2 | `hooks/check-control-plane.sh` | PreToolUse | 1 |
| 3 | `hooks/check-secrets.sh` | PreToolUse | 5 |
| 4 | `hooks/check-destructive.sh` | PreToolUse | 1 |
| 5 | `hooks/check-deploy-gate.sh` | PreToolUse | 1 |
| 6 | `hooks/check-deploy-mcp-gate.sh` | PreToolUse | 1 |
| 7 | `hooks/check-tdd.sh` | PreToolUse | 1 |
| 8 | `hooks/check-client-info.sh` | PreToolUse | 1 |
| 9 | `hooks/post-status-audit.sh` | PostToolUse | 4 |
| 10 | `hooks/post-bash.sh` | PostToolUse → **PostToolUseFailure** | 全面書き換え |
| 11 | `hooks/pre-compact.sh` | PreCompact | 2 (block + allow) |

#### 設定 / テスト / ドキュメント

| # | ファイル | 変更内容 |
|---|---|---|
| 12 | `templates/hooks.template.json` | `if` フィルタ完全削除（Write/NotebookEdit 監査漏れ修正）+ post-bash を `PostToolUse` → `PostToolUseFailure` セクションへ移動 |
| 13 | `tests/test_hook_output_schema.py` | **新規**：全 hook 出力契約テスト 12 ケース |

#### 補助修正

| ファイル | 変更内容 |
|---|---|
| `tests/test_check_status.py` | 既存 assertion 4 箇所を新形式（`"decision":"block"`）に更新 |
| `README.md` | Migration v0.12.1→v0.12.2 セクション追加 |
| `docs/STATUS.md` | framework_version: 0.12.2、iteration: 7、phase: implement、Round 1〜5 external_evidence 記録 |

### 2.2 変更前後の出力形式マトリクス

| Hook | Event | 旧形式 (v0.12.1) | 新形式 (v0.12.2) | 公式仕様準拠 |
|---|---|---|---|---|
| check-* 8 件 | PreToolUse | `{"permissionDecision":"deny","message":"..."}` | `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny\|ask","permissionDecisionReason":"..."}}` | ✓ |
| post-status-audit.sh | PostToolUse | `{"permissionDecision":"deny","message":"..."}` | `{"decision":"block","reason":"..."}` | ✓ |
| post-bash.sh | PostToolUse → PostToolUseFailure | `{"hookSpecificOutput":{"message":"..."}}` (PostToolUse) | `{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"..."}}` (PostToolUseFailure) | ✓ |
| pre-compact.sh (block) | PreCompact | `{"decision":"block","hookSpecificOutput":{"message":"..."}}` | `{"decision":"block","reason":"..."}` | ✓ |
| pre-compact.sh (allow) | PreCompact | `{"hookSpecificOutput":{"message":"..."}}` | `{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"..."}}` | ✓ |
| session-start.sh | SessionStart | `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}` | **変更なし**（既に公式仕様準拠、参考例） | ✓ |

## 3. テスト結果

### 3.1 新規: `tests/test_hook_output_schema.py`

| Test Class | ケース数 | 結果 |
|---|---|---|
| TestPreToolUseHooks | 6 | ✓ 全 PASS |
| TestPostToolUseHook (post-status-audit) | 3 (gate-tamper × Edit/Write/NotebookEdit) | ✓ 全 PASS |
| TestPostToolUseFailureHook (post-bash) | 1 | ✓ PASS |
| TestPreCompactHook | 2 (block / allow) | ✓ 全 PASS |
| **合計** | **12** | **✓ 全 PASS** |

検証内容（assertion ヘルパー）:
- PreToolUse: `hookSpecificOutput.hookEventName`、`permissionDecision`、`permissionDecisionReason` の存在 + 旧形式 top-level keys の **非存在**
- PostToolUse: top-level `decision: "block"`、`reason` の存在 + `permissionDecision` の **非存在**
- PostToolUseFailure: `hookSpecificOutput.additionalContext` の存在 + `hookEventName: "PostToolUseFailure"` + 旧 `message` キーの **非存在**
- PreCompact: block と allow で形式が異なることを別々に検証

### 3.2 全体: 134 ケース（新規 `test_hook_output_schema.py` 12 件を含む総数）

```
$ python3 -m unittest discover -s tests
Ran 134 tests in 5.529s
OK
```

**134 件は aegis 全テストの最新総数**（`test_hook_output_schema.py` の 12 件を含む）。`test_check_status.py` の 4 assertion を新形式（`"decision":"block"`）に更新済み。それ以外の既存テストは無変更。

### 3.3 tier 1 eval

```
=== Tier 1 Evaluation ===
  Validator                      Status
  ------------------------------ ----------
  check_status                   PASS
  status_doctor                  PASS
  check_framework_contract       PASS
  check_reference_drift          PASS
Result: PASS
```

## 4. 計画 Rev.5 との対応マトリクス

| 計画 Task | 完了状態 | 検証エビデンス |
|---|---|---|
| Task 0a-1: PreToolUse 8 hooks の hookSpecificOutput 移行 | ✅ | TestPreToolUseHooks 6 ケース + 既存テスト PASS |
| Task 0a-2: post-status-audit.sh の PostToolUse 出力スキーマ移行（gate-tamper / phase-skip / mode-tamper × Edit/Write/NotebookEdit の 9 ケース最低限） | ✅ | TestPostToolUseHook 3 ケース PASS + test_check_status.py の phase-skip / mode-change / gate-change テスト全 PASS |
| Task 0a-3: post-bash.sh を PostToolUseFailure へ移行（exit code 判定削除、additionalContext JSON 形式） | ✅ | TestPostToolUseFailureHook PASS |
| Task 0a-4: pre-compact.sh の出力形式修正（block と allow） | ✅ | TestPreCompactHook 2 ケース PASS |
| Task 0a-5: templates/hooks.template.json 更新（`if` 完全削除、post-bash の event 移動） | ✅ | `grep -F '"if":' templates/hooks.template.json` で 0 件 |
| Task 0a-test: tests/test_hook_output_schema.py 新規作成（5 イベント種、12 ケース） | ✅ | 12 ケース全 PASS |
| Task 0a-6: v0.12.2 リリース（version bump + Migration + tag） | 🔄 進行中 | framework_version 0.12.2、README Migration 追加済み、gate 承認・commit・tag は外部レビュー後にユーザー判断 |

## 5. レビュー時に確認したい点（外部レビュアーへ）

### 5.1 出力形式の公式仕様準拠

§ 2.2 の「新形式」列が現行 Claude Code 2.x の `hooks-reference` と完全に一致するか、再度 docs を当たって確認してほしい。特に：

- **PreToolUse** の `permissionDecisionReason` キー名（`reason` ではない点）
- **PostToolUse** の `decision: "block"` がトップレベルにあること（`hookSpecificOutput` でラップしていない）
- **PostToolUseFailure** で `additionalContext` が `hookSpecificOutput` 内にあること
- **PreCompact** の block で `reason` がトップレベルにあること（旧形式の `hookSpecificOutput.message` を削除済み）

### 5.2 `if` 削除でカバレッジが欠落していないか

- matcher は `Edit|Write|NotebookEdit` のまま
- post-status-audit.sh の line 22-32（`case "$TARGET_FILE" in *STATUS.md`）で 3 ツール全カバー
- Edit/Write/NotebookEdit 経由の gate-tamper を新規 TestPostToolUseHook 3 ケースで検証
- ファイル全体スキャンのオーバーヘッドはスクリプト冒頭の早期 return（ms 単位）で吸収

### 5.3 post-bash.sh の PostToolUseFailure 移行が妥当か

- 非ゼロ判定（旧 line 19-22）削除：イベント自体が失敗時のみ発火する仕様を信頼
- 出力は通知系（top-level `decision` を使わない）：意図通り block しない
- test runner 検出ロジックは維持（vitest / jest / pytest / cargo / go / npm / pnpm / bun の case）

### 5.4 計画 Rev.5 で残っていた懸念事項の解消

- `tool_response` キー名の不確定性 → Phase 0a スコープ外（Phase 0b で実機検証予定）
- `stop_hook_active` ガード → Phase 1 で実装（v0.13.0）
- TaskCreated/Completed event hook → Phase 0b で実装（v0.13.0）

これらは v0.12.2 hot-fix には含まれない。v0.13.0 で対応。

### 5.5 最終判定

以下の判定をお願いします：

1. v0.12.2 として ship してよいか（GO / NO-GO）
2. ship 前に追加で潰すべき点があるか
3. ある場合、Phase 0a の中で修正すべきか v0.13.0 に持ち越すか

## 6. リリース後のステップ（GO 判定後）

```bash
# gate 承認（aegis 正規ルート）
bash scripts/update-gate.sh review approve  # phase: implement → review に進めてから
bash scripts/update-gate.sh qa approve      # phase: review → qa に進めてから
bash scripts/update-gate.sh security approve
bash scripts/update-gate.sh deploy approve
bash scripts/update-gate.sh dev_ready_for_client approve  # （aegis 自体に client 引き渡しなし、n/a 扱いも可）

# commit + tag（ユーザー実施）
git add hooks/ \
        templates/hooks.template.json \
        tests/test_hook_output_schema.py tests/test_check_status.py \
        examples/minimal-project/hooks/ \
        examples/minimal-project/.claude/settings.json \
        README.md docs/STATUS.md \
        docs/qa-reports/v0122-review.md
git commit -m "fix(hooks): v0.12.2 — hook 出力スキーマを Claude Code 公式仕様へ全面移行"
git tag v0.12.2
```

**v0.13.0 計画ファイル** (`docs/plans/v0130-modernization-plan.md`, `docs/plans/v0130-second-opinion-brief.md`) は **untracked のまま** とし、Phase 0b 以降の作業時に別ブランチで管理する。

## 7. 残課題（v0.12.2 スコープ外、v0.13.0 で対応）

- Phase 0b: 新 PreToolUse 系 hook (`Skill`/`CronCreate`)、TaskCreated/TaskCompleted event hook、secrets/destructive 拡張、`extract_exit_code` 両対応、スキル名衝突解消
- Phase 1: agent frontmatter 適正化、UserPromptSubmit/Stop/SubagentStop hook、routing 拡張、PreCompact 閾値 300 → 1800
- Phase 2: commands frontmatter、/recover Skill 化、SKILL description / allowed-tools 整備、公式 schedule/loop 連携
- Phase 3: CLAUDE.md / README / STATUS / INTEGRATION.md / LEARNINGS / scripts
