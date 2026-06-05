# v0.13.0 Phase 0b Review Brief

Date: 2026-05-15 着手 / 2026-05-16 Round 1 提出 / 2026-05-18 Round 2 NO-GO 修正反映
Branch: `feat/v0130-phase0b-compat`
Reviewer: External (IDE Chat Opus 4.6) — Round 2 修正完了、最終確認待ち
計画: `docs/plans/v0130-modernization-plan.md` Revision 5

## Verdict

**PENDING (Round 3 最終確認待ち)** — Round 1 (NO-GO 判定、P1×4 + P3×1) を Round 2 ですべて反映完了。174 tests + tier 1 PASS、本体/minimal-project 完全同期。

---

## 1. Phase 0b スコープと完了状態

| Task | 内容 | 状態 |
|---|---|---|
| 0b-1 | PreToolUse 系新 hook（Skill / CronCreate）+ Vercel MCP matcher 明示化 | ✅ 完了 |
| 0b-2 | TaskCreated / TaskCompleted event hook（用途別使い分け） | ✅ 完了 |
| 0b-3 | 既存 hook 拡張（secrets / destructive）+ extract_exit_code 両キー対応 | ✅ 完了 |
| 0b-4 | スキル名衝突解消（3 件改名 + 合成スキルへ再設計）| ✅ 完了 |

## 2. 実装サマリ

### 2.1 新規 hook 4 件

| ファイル | 種類 | 用途 | 制御方式 |
|---|---|---|---|
| `hooks/check-skill-gate.sh` | PreToolUse (Skill matcher) | control-plane Skill (update-config / keybindings-help / fewer-permission-prompts) を ask 化 | `hookSpecificOutput.permissionDecision: "ask"` |
| `hooks/check-cron-gate.sh` | PreToolUse (CronCreate matcher) | スケジュール対象 prompt の deploy / destructive 文字列を検知して ask | 同上 |
| `hooks/check-task-created.sh` | TaskCreated event | plan gate 未承認 + phase=implement で TaskCreate 試行を hard stop | **`{"continue": false, "stopReason": "..."}` JSON**（Round 4-C 採用方針）|
| `hooks/check-task-completed.sh` | TaskCompleted event | STATUS.md `next_action` 未更新で完了報告を差し戻し | **exit code 2 + stderr に reason**（Round 4-C 採用方針）|

### 2.2 既存 hook 拡張

| ファイル | 変更 |
|---|---|
| `hooks/check-destructive.sh` | パターン追加: `git filter-branch` / `git update-ref -d` / `git reflog expire --expire=now` / `npx rimraf` / `find ... -delete` |
| `hooks/check-secrets.sh` | 高リスク認証ファイル検知追加: `*.pem` / `id_rsa` / `*credentials*.json` / `service-account*.json` |
| `hooks/lib/extract-input.sh` | `extract_exit_code` を両キー対応（`tool_response.exitCode` / `tool_result.exit_code` 等 4 優先順位 probe）|
| `hooks/session-start.sh` | スキル改名反映（`brainstorming` → `aegis-brainstorm`、`security-review` → `aegis-security-gate`）|

### 2.3 スキル名衝突解消（破壊的変更）

| 旧名 | 新名 | 設計変更 |
|---|---|---|
| `.claude/skills/brainstorming/` | **`.claude/skills/aegis-brainstorm/`** | 合成スキル：公式 `Skill(skill="brainstorming")` を Step 0 で呼び出し → aegis 固有の record / spec 保存 / hard gate / STATUS 遷移を重畳 |
| `.claude/skills/review/` | **`.claude/skills/aegis-review-gate/`** | 同：公式 `review` 呼び出し → severity 分類 / 対照表 / evidence checklist を重畳 |
| `.claude/skills/security-review/` | **`.claude/skills/aegis-security-gate/`** | 同：公式 `security-review` 呼び出し → OWASP Top 10 / evidence requirements を重畳 |

参照箇所の更新（旧名→新名）：
- `.claude/agents/reviewer.md` の `skills: [aegis-review-gate]`
- `.claude/agents/security.md` の `skills: [aegis-security-gate]` + 本文「aegis-security-gate skill (OWASP...)」
- `CLAUDE.md` / `templates/CLAUDE.template.md` / `examples/minimal-project/CLAUDE.md` の Skills 列挙
- `examples/minimal-project/.claude/agents/{reviewer,security}.md`
- `hooks/session-start.sh` の phase hint
- `scripts/check_framework_contract.py` の `REQUIRED_SKILL_FILES` と `REQUIRED_EXAMPLE_SKILL_DIRS`
- `examples/minimal-project/.claude/skills/{aegis-brainstorm,aegis-review-gate,aegis-security-gate}/` 全 SKILL.md を本体と同期

### 2.4 settings / 設定変更

| ファイル | 変更 |
|---|---|
| `templates/hooks.template.json` | 新 PreToolUse matcher 3 件（Skill / CronCreate / Vercel deploy MCP 明示化）+ 新 event 2 件（TaskCreated / TaskCompleted）登録、`mcp__.*__deploy.*` → `mcp__claude_ai_Vercel__deploy_to_vercel` 明示化 |
| `examples/minimal-project/.claude/settings.json` | 本体と同期 |
| `.gitignore` | `.claude/.task-event-debug.log`（raw_input 失敗時の fail-safe ダンプ先）を追加 |

### 2.5 新規ドキュメント

- `docs/qa-reports/v0130-extract-exit-code.md`: extract_exit_code 両キー対応の検証ログ + 実機検証残課題

---

## 3. テスト結果

### 3.1 新規追加テストクラス（合計 30 ケース）

| クラス | ケース数 | 内容 |
|---|---|---|
| `TestSkillGateHook` | 5 | control-plane Skill 3 種類 ask + 通常 skill passthrough + 欠落フィールド passthrough |
| `TestCronGateHook` | 5 | vercel deploy / rm -rf / git force push ask + 安全 prompt / 空 prompt passthrough |
| `TestTaskCreatedHook` | 4 | hard stop (continue:false) / 承認済み passthrough / plan phase passthrough / 失敗時 dump+passthrough |
| `TestTaskCompletedHook` | 4 | exit 2 push back（次action 空 / "null"）/ next_action 設定済み passthrough / 失敗時 dump |
| `TestExtractExitCode` | 6 | camelCase / snake_case / legacy / 優先順位 / 欠落時 0 / exit 0 正しく返す |
| `TestCheckDestructiveExtensions` | 5 | filter-branch / update-ref -d / reflog expire / npx rimraf / find -delete 全件 ask |
| `TestCheckSecretsHighRisk` | 4 | pem / id_rsa / credentials.json / service-account.json 全件 deny |
| 既存テスト整合性更新 | - | `test_matcher_valid_js_regex` を `mcp__claude_ai_Vercel__deploy_to_vercel` 明示化に追従 |

### 3.2 検証結果

```
$ python3 -m unittest discover -s tests
Ran 167 tests in 6.098s
OK

$ python3 scripts/run_eval.py --tier 1
=== Tier 1 Evaluation ===
  check_status                   PASS
  status_doctor                  PASS
  check_framework_contract       PASS
  check_reference_drift          PASS
Result: PASS
```

- 本体と minimal-project の完全同期：`diff -r hooks/ examples/minimal-project/hooks/` → 差分 0 件
- settings 同期：`diff templates/hooks.template.json examples/minimal-project/.claude/settings.json` → 差分 0 件

---

## 4. 計画 Rev.5 との対応マトリクス

| 計画項目（Rev.5 Phase 0b） | 完了状態 | 検証 |
|---|---|---|
| Task 0b-1: 新 PreToolUse 系 hook (Skill, Cron, Vercel deploy MCP 明示化) | ✅ | TestSkillGateHook 5 + TestCronGateHook 5 PASS |
| Task 0b-2: TaskCreated/Completed event hook（用途別: TaskCreated=continue:false / TaskCompleted=exit 2 + stderr）| ✅ | TestTaskCreatedHook 4 + TestTaskCompletedHook 4 PASS、continue:false と exit 2 の使い分けを assertion で強制 |
| Task 0b-3: secrets/destructive 拡張 + extract_exit_code 両対応 | ✅ | TestExtractExitCode 6 + TestCheckDestructiveExtensions 5 + TestCheckSecretsHighRisk 4 PASS、検証ログを v0130-extract-exit-code.md に記録 |
| Task 0b-4: スキル名衝突解消（3 件 rename + 合成スキル再設計 + 全参照更新）| ✅ | 改名後の全参照を grep で確認、tier 1 framework_contract PASS（旧名不在 + 新名存在）|

---

## 5. レビュー時に確認したい点

### 5.1 TaskCreated/Completed の用途別使い分け実装

- `check-task-created.sh`: hard stop は `{"continue": false, "stopReason": "..."}` JSON で実装、`decision: "block"` は使わない（Round 4-C で確定）
- `check-task-completed.sh`: 差し戻しは `exit 2 + stderr` で実装、JSON `decision: "block"` は使わない（同上）
- 両 hook は **matcher 非対応で必ず発火**するため、payload 正規化を冒頭に配置、失敗時は `.claude/.task-event-debug.log`（gitignore 対象）にダンプして passthrough
- 環境変数 `AEGIS_ROOT_OVERRIDE` でテスト時のスコープ分離

### 5.2 check-skill-gate.sh の対象スキル選定

control-plane 系として ask 化するのは以下 3 件：
- `update-config`: `.claude/settings.json` を書き換える
- `keybindings-help`: キーバインドを変更する
- `fewer-permission-prompts`: 権限設定を緩める

他に追加すべき control-plane 系 skill があれば指摘してください（例: `permissions` 系の新 skill 等）。

### 5.3 check-cron-gate.sh の danger pattern 網羅性

検知パターン: `vercel deploy` / `firebase deploy` / `netlify deploy` / `gcloud app deploy` / `(npm|pnpm|yarn|bun) deploy` / `flyctl deploy` / `railway deploy` / `rm -[r]+` / `drop (table|database)` / `git push --force` / `git reset --hard` / `git filter-branch` / `git update-ref -d` / `git reflog expire --expire=now` / `npx rimraf` / `find ... -delete`

漏れ・誤検知の懸念があれば指摘してください。

### 5.4 extract_exit_code の優先順位

```
1. tool_response.exitCode (camelCase, Claude Code 2.x suspected)
2. tool_response.exit_code (snake_case under tool_response, defensive)
3. tool_result.exit_code   (legacy / aegis pre-v0.12.2)
4. tool_result.exitCode    (defensive)
```

`tool_response` を `tool_result` より優先する判断、camelCase を snake_case より優先する判断（推測）の妥当性を確認してください。実機 payload 確認は v0.13.0 ship 後の運用記録対象（`docs/qa-reports/v0130-extract-exit-code.md` 参照）。

### 5.5 スキル改名の合成スキル設計

3 つの新スキル（`aegis-brainstorm` / `aegis-review-gate` / `aegis-security-gate`）はすべて **Step 0 で公式同名スキルを `Skill(skill="...")` で呼び出し → aegis 固有の重畳ステップを追加** という構造で統一。

確認したい点：
- 「公式スキルを呼び出してから aegis 固有 step を加える」が公式の Skill 仕様で実行可能か（skill 内から他 skill を呼ぶケース）
- 旧スキル本文（重複する内容）は削除済み、aegis 固有部分のみ残置の判断は妥当か
- 公式版が将来変更されても aegis 側に過度な依存がない構造か

### 5.6 残存 prose 内の旧名（変更不要と判断）

grep で以下が残存していますが、いずれもスキル名ではなく gate 名 / 散文 / phase 名 の参照のため変更不要：

- `.claude/agents/qa.md:17 "- review is complete..."` → phase 名（"review phase"）の散文参照
- `.claude/agents/reviewer.md:45,53 "- review note...", "- review the active diff..."` → 散文の review 動詞
- `.claude/skills/aegis-review-gate/SKILL.md:61 "review gate 承認"` → gate 名 (gate_approvals.review) 参照
- `hooks/session-start.sh:48,134 "review"` → phase 名 / gate 名のループ要素

これらは aegis のフレームワーク内部用語（"review phase" / "review gate"）であり、スキル名 `aegis-review-gate` とは別物。

---

## 6. リスクと対策

| ID | リスク | 対策 |
|---|---|---|
| R1 | check-task-* の payload 仕様変更 | docs WATCH、payload 正規化、raw_input ダンプ fail-safe |
| R2 | スキル改名で外部プロジェクト（uccc 等）参照が壊れる | 本体 + minimal-project + scripts + hooks をすべて改名済み、Migration ドキュメント v0.13.0 リリース時に整備予定 |
| R3 | check-cron-gate.sh の payload キー仕様変更 | 複数キー probe（prompt / task / instructions / command）で堅牢化 |
| R4 | extract_exit_code の実機キー仕様 | 4 優先順位の probe で両対応、ship 後実機検証 |
| R5 | 合成スキルで Skill 呼び出しの再帰／無限ループ | aegis-* 内の Step 0 は同名でない公式 skill を呼ぶため再帰しない |

---

## 7. ユーザー判断待ち

- Phase 0b commit + push のタイミング（外部レビュー GO 後 or 即時）
- Phase 1（agent / effort 適正化）への移行タイミング

実装ファイル変更：
- 新規ファイル: `hooks/check-skill-gate.sh`, `hooks/check-cron-gate.sh`, `hooks/check-task-created.sh`, `hooks/check-task-completed.sh`, `docs/qa-reports/v0130-extract-exit-code.md`, `docs/qa-reports/v0130-phase0b-review.md`
- リネーム: `.claude/skills/{brainstorming,review,security-review}/` → `.claude/skills/aegis-{brainstorm,review-gate,security-gate}/`
- 更新: `hooks/{check-destructive,check-secrets,lib/extract-input,session-start}.sh`, `templates/hooks.template.json`, `tests/test_hook_output_schema.py`, `tests/test_check_status.py`, `scripts/check_framework_contract.py`, `.claude/agents/{reviewer,security}.md`, `CLAUDE.md`, `templates/CLAUDE.template.md`, `.gitignore`, examples/minimal-project/ 配下の対応ファイル

---

## 8. レビュー依頼テンプレ（IDE Chat 用）

```
@docs/qa-reports/v0130-phase0b-review.md を読み、§9 の Round 2 修正対応が
すべて反映されているか確認 + 最終 GO/NO-GO 判定をください。

エビデンス: 174 tests PASS、tier 1 PASS、本体/minimal-project diff 0 件。
判定 GO なら commit + push をユーザー側で実施します。
```

---

## 9. Round 2 レビュー対応（2026-05-18、NO-GO → 反映）

レビュアー Round 1 判定: **NO-GO** — 実装は test 通過するが scaffold 配布で破綻する 4 件 P1 + 1 件 P3 を指摘。**Round 2 ですべて反映完了**。

| # | 指摘 (Round 1) | Priority | 修正内容 |
|---|---|---|---|
| R1-1 | TaskCreated が公式 payload (`task_subject` / `task_description`) を読めず hard stop しない | **P1** | `check-task-created.sh` の python3 normalize に `task_subject` / `task_description` を**優先 probe** として追加。テスト fixture を `{"task_subject": subject}` に変更（公式キーで実発火を担保）|
| R1-2 | TaskCompleted も公式 payload で差し戻しが発火しない | **P1** | `check-task-completed.sh` も同様の対応。テスト fixture も `task_subject` に |
| R1-3 | full profile が改名後 skill と新 hook を配布しない | **P1** | `templates/profiles/full.json`: recommended から旧 `brainstorming` / `review` / `security-review` 削除 + `aegis-brainstorm` / `aegis-review-gate` / `aegis-security-gate` 追加。hooks_include に `check-skill-gate.sh` / `check-cron-gate.sh` / `check-task-created.sh` / `check-task-completed.sh` を追加 |
| R1-4 | 高リスク credential が `git add . / git commit` で素通り | **P1** | `check-secrets.sh`: broad staging (`git add -A` / `git add .`) に **find ベースの高リスクファイル recursive scan** を追加（既存の `.env` パターンと同じ仕組み）、`git commit` に **cached diff の高リスク pattern 検査**を追加。Template placeholder `<file>` 回避のためメッセージを書き換え |
| R1-5 | post-status-audit.sh の defense-in-depth コメントが旧 `if` 仕様のまま | P3 | コメントを「v0.12.2+ で `if` 削除済み、`case` が主フィルタ」表記に書き換え |

### Round 2 修正後の検証

```
$ python3 -m unittest discover -s tests
Ran 174 tests in 6.520s
OK

$ python3 scripts/run_eval.py --tier 1
  check_status                   PASS
  status_doctor                  PASS
  check_framework_contract       PASS
  check_reference_drift          PASS
Result: PASS
```

- `diff -r hooks/ examples/minimal-project/hooks/` → 差分 0 件
- `diff templates/hooks.template.json examples/minimal-project/.claude/settings.json` → 差分 0 件

### Round 2 で追加・更新されたテスト

- **`TestTaskCreatedHook`** / **`TestTaskCompletedHook`** の `_payload` を `{"task_subject": ...}` に変更：公式 payload で hard stop / push back が実発火することを担保（既存 4 + 4 ケースは全て公式キーで動作確認済み）
- **`TestCheckSecretsBroadStaging`** 新規 7 ケース追加：
  - `git add .` + `*.pem` / `id_rsa` / `credentials.json` / `service-account*.json` が repo 内に存在 → deny（find ベース）
  - `git commit` で `*.pem` / `id_rsa` が staged → deny（cached diff scan）
  - `git commit` で高リスクファイルなし → pass-through

### 未確認の残課題

- 実機 Claude Code セッションでの公式 `TaskCreated` / `TaskCompleted` 発火時の正規 payload を v0.13.0 ship 後の運用ログで記録する（`extract_exit_code` と同じ扱い）。コードは公式キーを優先 probe するため、実機キー変動には耐性あり
