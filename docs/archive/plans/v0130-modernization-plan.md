# Plan: v0.13.0 — Aegis Modernization (Claude Code 進化追従) — Revision 4

> **このリビジョンについて**: 初版（Rev.1）に対し IDE Chat (Opus 4.6) からセカンドオピニオンを 3 ラウンド受け、計 15 件の指摘 (Round 1: P1×3, P2×2 / Round 2: P1×3, P2×1, 補足×1 / Round 3: P1 不足×1, 条件付き×1, 同種見落とし×1, 追加条件×3, 出力形式詳細×4) と私自身の追加検証 5 件（うち Rev.4 で 1 件 = 全 hook 出力形式 grep で pre-compact.sh の破損詳細判明）を反映した改訂版。
>
> **公式 docs 検証日**: 2026-05-03（[Skills](https://code.claude.com/docs/en/skills), [Hooks](https://code.claude.com/docs/en/hooks), [Subagents](https://code.claude.com/docs/en/sub-agents), [CLI Reference](https://code.claude.com/docs/en/cli-reference)）

## 改訂履歴

| Revision | 契機 | 主な変更 |
|---|---|---|
| Rev.1 | 初版 | 4 観点監査 + effort/model 監査の集約 |
| Rev.2 | Round 1 レビュー | user-invocable 削除撤回、TaskCreated/Completed event 採用、Plan 方針統一、allowed-tools 表現修正、effort 二層運用簡素化、v0.12.2 緊急 ship 分離 |
| Rev.3 | Round 2 レビュー | post-status-audit.sh も Phase 0a へ追加、`if` 完全削除（Write/NotebookEdit 漏れ修正）、TaskCreated/Completed の制御を `continue:false` 化、ScheduleWakeup を公式 schedule スキル経由に置換、post-bash.sh を PostToolUseFailure へ移行 |
| **Rev.4** | **Round 3 レビュー + 全 hook grep 確認** | **`if` 削除を Phase 0a に前倒し、post-bash.sh の出力を `hookSpecificOutput.additionalContext` に明確化、pre-compact.sh の出力形式破損 2 箇所を Phase 0a に追加（同種見落とし）、stop_hook_active ガード要件追加、Stop/SubagentStop/UserPromptSubmit/PreCompact の出力形式を全件公式仕様に揃え、E2E に Edit/Write/NotebookEdit × STATUS.md tamper を必須化** |
| **Rev.5** | **Round 4 レビュー（4-C 是認 + 旧表現残存指摘）** | **TaskCompleted の制御方式を変更マップ・Verification・TDD で `continue:false` 残存表現を撲滅し exit 2 + stderr に統一、raw_input ダンプ先を `.claude/.task-event-debug.log` (gitignore 対象) に限定、TaskCreated/Completed の matcher 非対応に伴う早期 return テストを必須化** |

## 改訂サマリ（Round 3 指摘の反映 — Rev.4 で追加修正）

| # | Round 3 指摘 | 対応 |
|---|---|---|
| R3-1 (P1 不足) | `if` 削除を Phase 0b ではなく Phase 0a に前倒すべき。v0.12.2 で post-status-audit を直すなら同時に if も削除しないと Write/NotebookEdit 漏れが残る | **Phase 0a に Task 0a-5 として前倒し**。Task 0b-4 を撤回 |
| R3-2 (条件付き十分) | post-bash.sh の「exit 0 + stdout でメッセージ表示」は曖昧、JSON 形式に統一推奨 | **Task 0a-3 で `{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"..."}}` JSON 形式に確定** |
| R3-3 (同種見落とし) | 既存 pre-compact.sh も要修正。`{"decision":"block","hookSpecificOutput":{"message":...}}` ではなく、`reason` をトップレベル | **私の判断で Phase 0a に Task 0a-6 として追加**（レビュアーは Phase 1 と提案したが、全 hook grep で同種破損を Phase 0a で一気に潰す方が hot-fix の一貫性として筋が通るため。最終レビュアー判定を仰ぐ） |
| R3-4 (追加条件 C4) | `stop_hook_active` で無限継続を避ける条件を check-completion.sh の実装要件に明記 | **Task 1-3 に追加** |
| R3-5 (追加条件 C5) | post-status-audit.sh のテストは gate / phase / mode × Edit / Write / NotebookEdit を最低限カバー | **Task 0a-2 のテスト粒度に明記**（9 ケース：3 違反種 × 3 ツール）|
| R3-6 (追加条件 C6) | UserPromptSubmit hook は `hookSpecificOutput.additionalContext` で文脈注入（block しない） | **Task 1-2 の出力形式に明記** |
| R3-7 (出力形式詳細) | UserPromptSubmit の追加文脈は `hookSpecificOutput: {hookEventName:"UserPromptSubmit", additionalContext}` が公式例 | Task 1-2 で明示 |
| R3-8 (出力形式詳細) | Stop / SubagentStop はトップレベル `decision:"block"`/`reason` で stop 阻止可。`stop_hook_active` ガードで無限継続を避ける | Task 1-3 で明示 |
| R3-9 (出力形式詳細) | PreCompact は exit code 2 または JSON `decision:"block"` で block 可、既存 pre-compact.sh の JSON は `reason` 欠落 | **Task 0a-6 として Phase 0a に追加**（同種見落としと併合） |
| R3-10 (出力形式詳細) | PostToolUseFailure の `additionalContext` は `hookSpecificOutput` 内が公式例。stdout 表示に頼らない | Task 0a-3 で明示 |

## 改訂サマリ（Round 2 指摘 — Rev.3 で対応済み、参考）

| # | Round 2 指摘 | 対応 |
|---|---|---|
| R2-1 (P1) | `if` を `Edit(*STATUS.md)` 単体に絞ると Write/NotebookEdit 監査漏れ | `if` 完全削除（→ Rev.4 で Phase 0a に前倒し最終確定） |
| R2-2 (P1) | post-status-audit.sh の出力形式が壊れている | Phase 0a に追加 |
| R2-3 (P1) | TaskCreated/Completed は `decision:"block"` 不可 | `{"continue": false, "stopReason": "..."}` または exit code 2 |
| R2-4 (P2) | ScheduleWakeup と self-review 矛盾 | 公式 `schedule` スキル経由に統一 |
| R2-5 (補足) | post-bash.sh は PostToolUseFailure へ | 移行（→ Rev.4 で出力形式を JSON 限定に確定） |

## 改訂サマリ（Round 1 指摘 — Rev.2 で対応済み、参考）

| # | Round 1 指摘 | 対応 |
|---|---|---|
| R1-1 (P1) | `user-invocable` は公式 frontmatter | Task 0-4 撤回 |
| R1-2 (P1) | `if` は公式（→ Rev.3/4 で完全削除に最終確定） | — |
| R1-3 (P1) | `TaskCreated`/`TaskCompleted` event 採用 | 反映 |
| R1-4 (P2) | `Plan` 不採用と条件付き許可が矛盾 | 「条件付き許可」で統一 |
| R1-5 (P2) | `allowed-tools` は事前許可 | 「事前許可」と明記 |

## 改訂サマリ（私の追加発見 — Rev.2/3/4）

| # | 自己発見 | 対応 |
|---|---|---|
| S-1 | `permissionDecision` ラップは PreToolUse のみ | Rev.2 で反映 |
| S-2 | subagent frontmatter `effort` は完全公式（5 値） | Rev.2 で反映 |
| S-3 | `tool_response` キー名は公式 docs に明記なし | Rev.2 で両キー対応 |
| S-4 | hook event は計 29 種、未活用が多数 | Rev.2 で 5 種採用 |
| **S-5** | **全 hook grep 確認で pre-compact.sh の出力形式破損を 2 箇所詳細判明（block 時の reason 欠落、allow 時の message キー）。post-bash.sh の現状出力も `hookSpecificOutput.message` で additionalContext ではない** | **Rev.4 で Phase 0a に追加** |

---

## Context

aegis は v0.12.1（2026-04-22 ship）以降ほぼ手付かずだが、その間に Claude Code 側で以下の進化があった：

- Opus 4.7 / 1M context、Sonnet 4.6 / Haiku 4.5
- `Skill` ツール標準化、ビルトインスキル多数（brainstorming / review / security-review / writing-plans / simplify / **schedule** / loop / find-skills 等）
- Built-in subagent: `Explore`, `Plan`
- Subagent isolation: `isolation: "worktree"`、`background: true`
- 永続 Task 系: `TaskCreate / TaskGet / TaskList / TaskUpdate / TaskStop / TaskOutput`
- フックイベント拡張（公式 29 種）
- フック出力スキーマ（公式仕様確定）:
  - **PreToolUse**: `hookSpecificOutput.permissionDecision: "deny"|"ask"|"allow"` + `permissionDecisionReason`
  - **PostToolUse / Stop / SubagentStop / UserPromptSubmit / ConfigChange / PreCompact**: トップレベル `{"decision": "block", "reason": "..."}`
  - **PostToolUseFailure / SessionStart / UserPromptSubmit (情報注入時)**: `hookSpecificOutput: {"hookEventName": "<event>", "additionalContext": "..."}`
  - **TaskCreated**（安全境界違反 = hard stop）: `{"continue": false, "stopReason": "..."}` JSON
  - **TaskCompleted**（軽微な不整合 = 差し戻し）: exit code 2 + stderr に reason
  - **Stop / SubagentStop の無限継続防止**: 入力 JSON の `stop_hook_active: true` を見て早期 return
- effort 5 段階 `low / medium / high / xhigh / max`（subagent / skill frontmatter / CLI すべて公式）

並列で 4 観点 + 1 観点 + 全 hook grep 監査の結果、aegis は次の 3 層で陳腐化：

1. **互換性層（v0.12.2 hot-fix 必須）**：PreToolUse 8 件 + PostToolUse 1 件 (post-status-audit.sh) + PostToolUse 1 件 (post-bash.sh) + PreCompact 1 件 (pre-compact.sh) が誤った出力スキーマ。**全 hook 12 件中 11 件で出力形式が公式仕様と不一致**（適合は session-start.sh のみ）。**deny / block が事実上無効化されている**
2. **安全層**：Skill / TaskCreated / TaskCompleted / CronCreate / Vercel deploy MCP に対する PaC 未対応
3. **生産性層**：ビルトインスキル / `Explore` / `Plan` / worktree / background / argument-hint / 公式 schedule スキル等を活用できていない。スキル名衝突 3 件

## Approach

破壊的変更を含むため、4 Phase に分割し段階的にリリース：

- **Phase 0a (v0.12.2 緊急 ship)**: hook 出力スキーマ移行 — PreToolUse 8 + PostToolUse (post-status-audit.sh) + PostToolUseFailure 移行 (post-bash.sh) + PreCompact 出力修正 (pre-compact.sh) + `if` 削除。deny / block 機能の正常化が最優先
- **Phase 0b (v0.13.0)**: 新ツール matcher / event hook、スキル改名、その他互換修正
- **Phase 1 (v0.13.0)**: subagent 機能取り込み + effort/model 適正化、UserPromptSubmit/Stop/SubagentStop hook、PreCompact 閾値見直し（300→1800）
- **Phase 2 (v0.13.0)**: commands / skills 現行化
- **Phase 3 (v0.13.0)**: 設計哲学・ドキュメント更新

### 設計上の確定事項

- **リスク許容しない**：思考品質の低下を伴うコスト削減は採用しない
- **effort は max / xhigh / high が基本**：medium/low は本当に思考不要な単純作業のみ
- **frontmatter `effort` は公式機能**：subagent / skill 双方で公式、frontmatter 一元化
- **built-in `Explore` 限定委譲**、**built-in `Plan` 条件付き許可**（最終計画は `docs/plans/*.md` に成文化、aegis planner / plan gate を経由）
- **スキル名衝突 3 件は改名**：`aegis-brainstorm` / `aegis-review-gate` / `aegis-security-gate`
- **`user-invocable: false` 維持**
- **self-review 経路は公式 `schedule` スキル経由**
- **同種見落とし防止**: 全 hook の出力形式は session-start.sh を「正しい形式の唯一の参考例」として、公式仕様に揃える

## Deploy Target / Git 戦略

省略（Phase 0a は `hotfix/v0122-hook-schema` ブランチ → v0.12.2 tag、Phase 0b〜3 は v0.13.0 PR）。

---

## ファイル構造（変更マップ）

### Phase 0a — v0.12.2 緊急 ship（hook 出力スキーマ全面移行）

| 区分 | ファイル | hook イベント | 変更内容 |
|---|---|---|---|
| 更新 | `hooks/check-gate.sh` | PreToolUse | `hookSpecificOutput.permissionDecision`/`permissionDecisionReason` 形式へ |
| 更新 | `hooks/check-control-plane.sh` | PreToolUse | 同上 |
| 更新 | `hooks/check-secrets.sh` | PreToolUse | 同上 |
| 更新 | `hooks/check-destructive.sh` | PreToolUse | 同上 |
| 更新 | `hooks/check-deploy-gate.sh` | PreToolUse | 同上 |
| 更新 | `hooks/check-deploy-mcp-gate.sh` | PreToolUse | 同上 |
| 更新 | `hooks/check-tdd.sh` | PreToolUse | 同上 |
| 更新 | `hooks/check-client-info.sh` | PreToolUse | 同上 |
| 更新 | `hooks/post-status-audit.sh` | PostToolUse | トップレベル `{"decision":"block","reason":"..."}` 形式へ移行（4 箇所：line 55/72/91/97） |
| 更新 | `hooks/post-bash.sh` | PostToolUse → PostToolUseFailure 移行 | `{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"..."}}` JSON 形式に確定。非ゼロ終了判定削除、test runner 判定のみ |
| **更新** | **`hooks/pre-compact.sh`** | **PreCompact** | **block (line 61): `{"decision":"block","reason":"..."}` 形式へ（`hookSpecificOutput.message` 削除）。allow (line 69): `{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"..."}}` 形式へ（`message` → `additionalContext`、`hookEventName` 追加）** |
| 更新 | `templates/hooks.template.json` | — | post-status-audit.sh の **`if` 完全削除**（matcher は `Edit\|Write\|NotebookEdit` のまま、script 側 `case TARGET_FILE` で絞り込み）、post-bash.sh を `PostToolUse` → `PostToolUseFailure` セクションへ移動 |
| 新規 | `tests/test_hook_output_schema.py` | — | 全 hook の出力契約テスト：PreToolUse 8（hookSpecificOutput.permissionDecision）+ PostToolUse 1（top-level decision/reason）+ PostToolUseFailure 1（hookSpecificOutput.additionalContext）+ PreCompact 2 ケース（block / allow）+ SessionStart 1（既存形式維持確認） |

**変更しない**（Phase 0a スコープ外）:
- `hooks/session-start.sh`（既に公式仕様適合、唯一の参考例）
- `hooks/lib/extract-input.sh`（exit_code 取得は Phase 0b で実機検証後に修正）

### Phase 0b — v0.13.0 互換性残り

| 区分 | ファイル | 変更内容 |
|---|---|---|
| 新規 | `hooks/check-skill-gate.sh` | `Skill` matcher：control-plane 系（`update-config`/`keybindings-help`/`fewer-permission-prompts`）を `ask` 化 |
| 新規 | `hooks/check-task-created.sh` | `TaskCreated` event hook：plan gate 未承認で実装系 Task 作成を `{"continue": false, "stopReason": "..."}` で hard stop（teammate 全体停止、安全境界違反扱い） |
| 新規 | `hooks/check-task-completed.sh` | `TaskCompleted` event hook：完了報告整合性チェック、不整合時 **exit code 2 + stderr に reason**（task action の差し戻し、モデルへ修正フィードバック） |
| 新規 | `hooks/check-cron-gate.sh` | `CronCreate` matcher：payload 内 deploy / destructive 文字列スキャン |
| 更新 | `hooks/check-deploy-mcp-gate.sh` | matcher を `mcp__claude_ai_Vercel__deploy_to_vercel` に明示化 |
| 更新 | `hooks/check-secrets.sh` | `*.pem` `id_rsa` `*credentials*.json` `service-account*.json` 検知追加 |
| 更新 | `hooks/check-destructive.sh` | `git filter-branch` `git update-ref -d` `git reflog expire --expire=now --all` `npx rimraf` `find ... -delete` 追加 |
| 更新 | `hooks/lib/extract-input.sh` | `extract_exit_code` 実機検証の上、`tool_response.exitCode` / `tool_result.exit_code` 両対応 |
| 更新 | `templates/hooks.template.json` | 新 matcher 登録：`Skill`, `CronCreate`, `mcp__claude_ai_Vercel__deploy_to_vercel`、新 event hook 登録：`TaskCreated`, `TaskCompleted` |
| ~~削除~~ | ~~`hooks/post-status-audit.sh` の `if` 削除~~ | **Phase 0a Task 0a-5 へ前倒し（撤回）** |
| ~~削除~~ | ~~`ScheduleWakeup` / `RemoteTrigger` matcher~~ | 公式 docs 未掲載のため対象外 |
| リネーム | `.claude/skills/{brainstorming,review,security-review}/` → `aegis-{brainstorm,review-gate,security-gate}/` | 公式同名衝突回避 |
| 更新 | 上記 3 スキル本文 | 「公式 `Skill(skill="brainstorming")` 呼び出し → 出力に aegis 固有の gate / OWASP severity 重畳」の合成スキル |
| 更新 | `.claude/agents/reviewer.md` | `skills: [aegis-review-gate]` |
| 更新 | `.claude/agents/security.md` | `skills: [aegis-security-gate]` |
| 更新 | `CLAUDE.md`, `templates/CLAUDE.template.md` | Skills 列挙の改名反映 |
| 更新 | examples/minimal-project/ | 上記の対応する変更をミラー |

### Phase 1 — subagent + effort

| 区分 | ファイル | 変更内容 |
|---|---|---|
| 更新 | `.claude/agents/planner.md` | `model: opus`, `effort: max`, `disallowedTools: [Edit, Write, NotebookEdit]` |
| 更新 | `.claude/agents/security.md` | `model: opus`, `effort: max`, `disallowedTools` |
| 更新 | `.claude/agents/reviewer.md` | `model: opus`, `effort: xhigh`, `disallowedTools` |
| 更新 | `.claude/agents/implementer.md` | `model: inherit`, `effort: high`, `isolation: "worktree"` |
| 更新 | `.claude/agents/qa.md` | `model: inherit`, `effort: high`, `disallowedTools` |
| 更新 | `.claude/agents/qa-browser.md` | `model: inherit`, `effort: high` |
| 更新 | `.claude/agents/ui.md` | `model: inherit`, `effort: high` |
| 更新 | `.claude/agents/integration-specialist.md` | `model: inherit`, `effort: high` |
| 更新 | `.claude/agents/translation-specialist.md` | `model: sonnet`, `effort: medium → high` |
| 更新 | `.claude/agents/reviewer-{testing,performance,maintainability}.md` | `model: haiku → sonnet`, `effort: medium → high` |
| 更新 | `.claude/rules/routing.md` | Built-in subagent delegation セクション、Plan 条件付き許可、Session effort policy |
| 新規 | `hooks/user-prompt-submit.sh` | UserPromptSubmit hook：blockers / failure_tracking / health を **`{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}`** で注入（block しない） |
| 新規 | `hooks/check-completion.sh` | Stop / SubagentStop hook：完了申告時に STATUS.md `next_action` 更新と evidence 存在を検査、未充足ならトップレベル `{"decision":"block","reason":"..."}`。**`stop_hook_active` ガード**で無限継続防止（入力 JSON で `stop_hook_active: true` を見たら早期 return）。env var `AEGIS_COMPLETION_GUARD=0` でバイパス可、bypass 時は STATUS.md にログ記録 |
| 更新 | `hooks/session-start.sh` | UserPromptSubmit へ動的部分を移管後の縮減（mode/phase/next_action のみ） |
| 更新 | `hooks/pre-compact.sh` | **stale 閾値 300s → 1800s。`phase=null` 時は警告のみ**（出力形式は Phase 0a で修正済み） |
| 更新 | `templates/hooks.template.json` | `UserPromptSubmit` `Stop` `SubagentStop` ハンドラ追加 |
| 更新 | `CLAUDE.md` | Operating Contract に「Session effort policy」追記 |

### Phase 2 — commands / skills 現行化

| 区分 | ファイル | 変更内容 |
|---|---|---|
| 更新 | `.claude/commands/status.md` | `argument-hint`, `model: claude-haiku-4-5`, `allowed-tools` |
| 更新 | `.claude/commands/gate.md` | `argument-hint: "[approve\|na\|reset] <gate-name>"`, 引数パース修正 |
| 更新 | `.claude/commands/recover.md` | `Skill(skill="session-recovery")` 直呼び |
| 更新 | `.claude/commands/validate.md` | `argument-hint: "[tier]"`, `model: claude-haiku-4-5` |
| 更新 | `.claude/commands/{next,retro,tutorial}.md` | frontmatter 整備 |
| 更新 | 全 15 スキル `SKILL.md` の description | find-skills 検索向け最適化 |
| 更新 | 必要なスキルに `allowed-tools` 追加 | 「事前許可」と本文注記、permission deny rules 併用と明記 |
| 更新 | 一部スキルの `model` / `effort` 明示 | tdd / bug-diagnosis / qa-verification → opus + high、docs-sync / translation-mapping → sonnet + high |

### Phase 3 — 哲学・ドキュメント

| 区分 | ファイル | 変更内容 |
|---|---|---|
| 更新 | `CLAUDE.md`, `templates/CLAUDE.template.md`, `examples/minimal-project/CLAUDE.md` | Plan 条件付き許可、TaskCreate 方針更新、3-failure recovery を公式 `schedule` スキル経由（`/schedule`）、Session effort policy |
| 更新 | `README.md` | Migration v0.12.1→v0.12.2→v0.13.0 セクション、`--effort xhigh` 推奨 |
| 更新 | `docs/STATUS.md`, `templates/STATUS.template.md` | iteration: 6→7、`task_ids: []` 追加、framework_version 0.13.0 |
| 新規 | `docs/INTEGRATION.md` | Claude Agent SDK / context7 / ultrareview / claude-api skill 接続点、公式 `schedule` / `loop` スキル連携パターン |
| 更新 | `docs/LEARNINGS.md` | v0.12.2 / v0.13.0 知見追記 |
| 更新 | `scripts/check_framework_contract.py`, `scripts/check_status.py` | 改名反映、`task_ids` 検証、VERSION bump |
| 更新 | `examples/minimal-project/` | 全変更のミラー |

---

## Boundary Map

| Phase | Produces | Consumes |
|---|---|---|
| Phase 0a | hook 出力スキーマ準拠の 11 ファイル + template + 契約テスト + `if` 削除 | 既存 hooks 構造 |
| Phase 0b | 新 PreToolUse / event hook、スキル改名 | Phase 0a の出力スキーマ |
| Phase 1 | agent frontmatter、UserPromptSubmit/Stop/SubagentStop hook、routing 拡張、PreCompact 閾値 | Phase 0b の改名スキル |
| Phase 2 | commands / skills 現行化 | Phase 1 の routing |
| Phase 3 | 哲学アップデート | Phase 0a〜2 |

循環なし。

---

## タスク分解

### Phase 0a — v0.12.2 緊急 ship

#### Task 0a-1: PreToolUse hook 出力スキーマ移行（8 ファイル）
- **blockedBy**: なし | **モデル**: opus
- **ファイル**: `hooks/check-{gate,control-plane,secrets,destructive,deploy-gate,deploy-mcp-gate,tdd,client-info}.sh`
- **意図**: トップレベル `permissionDecision`/`message` を `hookSpecificOutput.permissionDecision`/`permissionDecisionReason` でラップ
- **TDD**: `tests/test_hook_output_schema.py` の PreToolUse セクション、各 hook で deny + 通過の最低 2 ケース
- **Deliverable**: [ ] 8 hook 更新 [ ] 出力契約テスト PASS

#### Task 0a-2: PostToolUse hook 出力スキーマ移行（post-status-audit.sh）
- **blockedBy**: なし（0a-1 と並列可） | **モデル**: opus
- **ファイル**: `hooks/post-status-audit.sh`
- **意図**: line 55/72/91/97 の 4 箇所を `{"decision":"block","reason":"..."}` 形式へ
- **TDD**: gate-tamper / phase-skip / mode-tamper × Edit / Write / NotebookEdit = **9 ケース**最低限カバー
- **Deliverable**: [ ] 1 hook 更新（4 箇所） [ ] 9 ケース PASS

#### Task 0a-3: post-bash.sh を PostToolUseFailure へ移行
- **blockedBy**: なし | **モデル**: sonnet
- **ファイル**: `hooks/post-bash.sh`, `templates/hooks.template.json`
- **意図**: 非ゼロ終了判定（line 19-22）削除、test runner 判定のみ。出力を **`{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"..."}}`** JSON 形式に確定（stdout 表示や exit code に頼らない）
- **TDD**: PostToolUseFailure サンプル payload で test runner 失敗時のメッセージ出力確認
- **Deliverable**: [ ] 1 hook 更新 [ ] template.json matcher 更新 [ ] テスト追加

#### Task 0a-4: pre-compact.sh の出力形式修正
- **blockedBy**: なし（0a-1〜0a-3 と並列可） | **モデル**: opus
- **ファイル**: `hooks/pre-compact.sh`
- **意図**:
  - line 61 (block 時): `{"decision":"block","hookSpecificOutput":{"message":"..."}}` → **`{"decision":"block","reason":"..."}`** （hookSpecificOutput 削除、reason をトップレベルへ）
  - line 69 (allow 時): `{"hookSpecificOutput":{"message":"..."}}` → **`{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"..."}}`** （message → additionalContext、hookEventName 追加）
- **TDD**: stale 検出時 (block) と current 時 (allow) の 2 ケース
- **Deliverable**: [ ] 2 箇所修正 [ ] 出力契約テスト PASS

#### Task 0a-5: post-status-audit.sh の `if` フィルタ完全削除
- **blockedBy**: 0a-2 | **モデル**: sonnet
- **ファイル**: `templates/hooks.template.json`
- **意図**: post-status-audit エントリの `"if": "Edit(*STATUS.md) || Write(*STATUS.md) || NotebookEdit(*STATUS.md)"` を完全削除（公式仕様で `||` 構文は不可）。matcher は `Edit\|Write\|NotebookEdit` のまま、post-status-audit.sh の既存 `case TARGET_FILE in *STATUS.md` 判定で 3 ツール全カバー
- **検証**: Write(STATUS.md) と NotebookEdit(STATUS.md) で gate tamper を発火させる E2E 2 ケース
- **Deliverable**: [ ] template.json 更新 [ ] Write/NotebookEdit 経由の発火テスト PASS

#### Task 0a-6: v0.12.2 リリース
- **blockedBy**: 0a-1, 0a-2, 0a-3, 0a-4, 0a-5 | **モデル**: sonnet
- **ファイル**: `docs/STATUS.md`, `templates/STATUS.template.md`, `README.md`, `scripts/check_framework_contract.py`
- **意図**: framework_version 0.12.2、Migration v0.12.1→v0.12.2 セクション、tag 付与
- **Deliverable**: [ ] version bump [ ] git tag v0.12.2 [ ] PR merge

### Phase 0b — v0.13.0 互換性残り

#### Task 0b-1: PreToolUse 系新 hook 追加
- **blockedBy**: 0a-1 | **モデル**: opus
- **ファイル**: 新規 `hooks/check-skill-gate.sh`, `hooks/check-cron-gate.sh`、更新 `hooks/check-deploy-mcp-gate.sh`, `templates/hooks.template.json`
- **Deliverable**: [ ] 2 新規 hook [ ] hooks.template.json 更新 [ ] テスト追加

#### Task 0b-2: TaskCreated / TaskCompleted event hook 追加
- **blockedBy**: 0a-2 | **モデル**: opus
- **ファイル**: 新規 `hooks/check-task-created.sh`, `hooks/check-task-completed.sh`、更新 `templates/hooks.template.json`
- **制御方式（最終レビュー Round 4 で是認、確定）**:
  - **TaskCreated（安全境界違反 = hard stop）**: `{"continue": false, "stopReason": "..."}` JSON で teammate/agent 全体を停止。例: plan gate 未承認で実装系 Task を起こそうとした場合
  - **TaskCompleted（軽微な不整合 = 差し戻し）**: **exit code 2 + stderr に reason** で該当 task action のみ止めてモデルへ修正フィードバック。例: STATUS.md `next_action` 未更新、evidence ファイル不在
- **TDD**:
  - **TaskCreated**: hard stop ケース（plan gate 未承認で `continue:false` 発火）+ 通過ケース（gate 承認済み）
  - **TaskCompleted**: 差し戻しケース（next_action 未更新で exit 2 + stderr）+ 通過ケース（整合済み）
  - 共通: payload 正規化、**matcher 非対応で必ず発火するため不該当ケースの早期 return も必ずテスト**
- **raw_input ダンプの取り扱い**: payload 正規化に失敗した場合の fail safe ダンプ先は **`.claude/.task-event-debug.log`（gitignore 対象）に限定**。task_description / stopReason 等に機密が混入する可能性があるため、リポジトリ内のトラッキング対象には絶対に書かない
- **Deliverable**: [ ] 2 新規 hook [ ] hooks.template.json に TaskCreated/TaskCompleted 登録 [ ] payload 正規化を冒頭に [ ] `.claude/.task-event-debug.log` を `.gitignore` に追加 [ ] テスト 4 ケース以上 + 早期 return テスト追加

#### Task 0b-3: 既存 hook の検知拡張 + extract_exit_code 両対応
- **blockedBy**: 0a-1 | **モデル**: sonnet
- **ファイル**: `hooks/check-secrets.sh`, `hooks/check-destructive.sh`, `hooks/lib/extract-input.sh`, `hooks/post-bash.sh`
- **検証**: `tool_response.exitCode` / `tool_result.exit_code` の現在挙動を実機確認、ログを `docs/qa-reports/v0130-extract-exit-code.md` に保存
- **Deliverable**: [ ] 4 ファイル更新 [ ] 実機検証ログ

#### Task 0b-4: スキル名衝突解消（3 件改名）
- **blockedBy**: なし（並列可） | **モデル**: opus
- **意図**: 公式同名衝突回避、本文を「公式スキル + aegis 固有 gate 重畳」へ
- **Deliverable**: [ ] 3 スキル rename + 本文再設計 [ ] 全参照更新 [ ] reference drift check PASS

### Phase 1 — subagent + effort

#### Task 1-1: agent frontmatter 一括適正化
- **blockedBy**: 0b-4 | **モデル**: opus
- **意図**: model 明示化、effort 5 段階で再配分（max=2, xhigh=1, 残り high）、disallowedTools 冗長化、implementer に worktree
- **Deliverable**: [ ] 12 agent 更新 [ ] frontmatter 検証テスト

#### Task 1-2: UserPromptSubmit hook 新設
- **blockedBy**: 0a-1 | **モデル**: opus
- **ファイル**: 新規 `hooks/user-prompt-submit.sh`、更新 `hooks/session-start.sh`, `templates/hooks.template.json`
- **意図**: blockers / failure_tracking / health を毎ターン軽量注入、SessionStart 縮減
- **出力形式**: **`{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}`**（block しない通知系）
- **Deliverable**: [ ] 新フック [ ] SessionStart 縮減 [ ] 出力契約テスト

#### Task 1-3: Stop / SubagentStop hook 新設
- **blockedBy**: 0a-1 | **モデル**: opus
- **ファイル**: 新規 `hooks/check-completion.sh`、更新 `templates/hooks.template.json`
- **意図**: 完了申告時に STATUS.md `next_action` 更新と evidence 存在を検査
- **出力形式**: 未充足時はトップレベル `{"decision":"block","reason":"..."}`（Stop / SubagentStop は block 可）。**`stop_hook_active` ガード**：入力 JSON で `stop_hook_active: true` を見たら早期 return（無限継続防止）。env var `AEGIS_COMPLETION_GUARD=0` でバイパス可、bypass 時は STATUS.md にログ
- **Deliverable**: [ ] 新フック [ ] `stop_hook_active` ガードテスト [ ] バイパステスト [ ] 誤検知抑制テスト

#### Task 1-4: routing.md 拡張
- **blockedBy**: 1-1 | **モデル**: opus
- **Deliverable**: [ ] 2 ファイル更新（aegis 本体 + minimal-project ミラー）

#### Task 1-5: PreCompact 閾値見直し
- **blockedBy**: 0a-4 | **モデル**: sonnet
- **ファイル**: `hooks/pre-compact.sh`
- **意図**: STALE_THRESHOLD 300 → 1800、phase=null 時は警告のみ（出力形式は Phase 0a で修正済み）
- **Deliverable**: [ ] 閾値変更 [ ] phase=null 動作テスト

### Phase 2 — commands / skills 現行化

#### Task 2-1: 7 slash commands frontmatter 整備
- **blockedBy**: なし | **モデル**: sonnet | **Deliverable**: [ ] 7 ファイル更新

#### Task 2-2: /recover の Skill 直呼び化
- **blockedBy**: 2-1 | **モデル**: sonnet | **Deliverable**: [ ] 1 ファイル更新

#### Task 2-3: SKILL.md description / allowed-tools 整備
- **blockedBy**: 0b-4 | **モデル**: sonnet
- **意図**: find-skills 向け最適化、`allowed-tools` 追加（**「事前許可」と本文注記**）
- **Deliverable**: [ ] 15 SKILL.md 更新

#### Task 2-4: 公式 schedule / loop スキル連携
- **blockedBy**: 2-1 | **モデル**: sonnet
- **Deliverable**: [ ] 2 ファイル更新

### Phase 3 — 哲学・ドキュメント

#### Task 3-1: CLAUDE.md Operating Contract 改訂
- **blockedBy**: Phase 1 完了 | **モデル**: opus
- **意図**: Plan 条件付き許可、TaskCreate 方針更新、3-failure recovery を公式 `schedule` スキル経由、Session effort policy
- **Deliverable**: [ ] 3 ファイル更新、word count <= 800

#### Task 3-2: README.md 大幅更新
- **blockedBy**: 全Phase | **モデル**: opus | **Deliverable**: [ ] README 更新

#### Task 3-3: docs/INTEGRATION.md 新設
- **blockedBy**: なし | **モデル**: sonnet | **Deliverable**: [ ] 新規ドキュメント

#### Task 3-4: STATUS.md / templates / scripts 更新
- **blockedBy**: 3-1 | **モデル**: sonnet | **Deliverable**: [ ] 4 ファイル更新

#### Task 3-5: LEARNINGS.md 追記
- **blockedBy**: 全Phase | **モデル**: sonnet
- **意図**: v0.12.2 / v0.13.0 知見（PreToolUse 限定 hookSpecificOutput、PostToolUse はトップレベル decision、**TaskCreated は continue:false で hard stop / TaskCompleted は exit 2 + stderr で差し戻し**、`if` 単一 rule 制約、`user-invocable` の正しい使い方、frontmatter effort 公式化、self-review は公式 schedule 経由、**全 hook 出力形式を grep で一斉確認する習慣の重要性**、**TaskCreated/Completed は matcher 非対応で必ず発火するため payload 正規化と早期 return が必須**、**raw_input ダンプ先は gitignore 対象に限定**）
- **Deliverable**: [ ] LEARNINGS.md 追記

---

## Verification

### Phase 0a (v0.12.2)
1. `tests/test_hook_output_schema.py` 全 PASS（PreToolUse 8 + PostToolUse 1 + PostToolUseFailure 1 + PreCompact 2 + SessionStart 1）
2. 既存 118 テスト PASS
3. `python3 scripts/run_eval.py --tier 1` PASS
4. 実機セッションで PreToolUse hook の deny / PostToolUse hook の block / PostToolUseFailure の通知 / PreCompact の block と allow が動作
5. **gate tamper / phase skip / mode tamper × Edit / Write / NotebookEdit の 9 ケース** すべて新形式（top-level decision）で発火
6. **Write(STATUS.md) と NotebookEdit(STATUS.md) で gate tamper が発火**（`if` 削除確認）
7. pre-compact.sh の block 時 reason がトップレベルに出る、allow 時 additionalContext + hookEventName が出る

### Phase 0b
8. 新 PreToolUse hook（2 件）動作
9. **TaskCreated event hook が `{"continue": false, "stopReason": "..."}` で hard stop、TaskCompleted event hook が exit code 2 + stderr で task 差し戻し** がそれぞれ動作。`raw_input` ダンプ先が `.claude/.task-event-debug.log` (gitignore 対象) に限定されている
10. `tool_response.exitCode` / `tool_result.exit_code` 両キー対応の実機検証ログ
11. 旧スキル名 `brainstorming` / `review` / `security-review` の参照ゼロ

### Phase 1
12. 12 agent frontmatter が推奨マトリクス通り
13. UserPromptSubmit hook が毎ターン `additionalContext` で軽量注入
14. Stop hook が STATUS.md 未更新時に block を返す、`stop_hook_active: true` で早期 return、env var バイパス動作
15. routing.md / CLAUDE.md の Plan 方針が一致
16. PreCompact 閾値 1800 + phase=null 警告のみが動作

### Phase 2
17. 全 7 commands に `argument-hint`、/recover が `Skill` 直呼び
18. SKILL.md `allowed-tools` 本文注記が「事前許可」を明記

### Phase 3
19. CLAUDE.md word count <= 800
20. README に Migration v0.12.1→v0.12.2→v0.13.0 完備
21. CLAUDE.md / routing.md / Phase 3 の self-review 経路がすべて「公式 schedule スキル経由」で一致
22. STATUS.md `task_ids` 存在、validator PASS
23. `python3 scripts/check_reference_drift.py` PASS
24. `python3 scripts/check_framework_contract.py --profile=full` PASS

---

## トレーサビリティ（監査所見 → Task）

| 監査所見 | Task |
|---|---|
| PreToolUse hook 出力スキーマ陳腐化 | 0a-1 |
| PostToolUse (post-status-audit.sh) 出力スキーマ陳腐化 | 0a-2 |
| post-bash.sh の PostToolUseFailure 移行 + JSON 形式統一 | 0a-3 |
| **pre-compact.sh の PreCompact 出力形式破損 2 箇所（grep で発見）** | **0a-4** |
| **`if` フィルタの Write/NotebookEdit 漏れを Phase 0a で前倒し** | **0a-5** |
| 新 PreToolUse 系 matcher 不在 | 0b-1 |
| TaskCreated/Completed event hook 不在 | 0b-2 |
| secrets / destructive パターン不足、`tool_response` キー不確定 | 0b-3 |
| スキル名衝突 3 件 | 0b-4 |
| effort/model/isolation 未活用 | 1-1 |
| UserPromptSubmit / SessionStart 肥大 | 1-2 |
| Stop / SubagentStop 未活用、`stop_hook_active` ガード不在 | 1-3 |
| routing が Explore/Plan/effort/worktree 未対応 | 1-4 |
| PreCompact 閾値陳腐化 | 1-5 |
| commands frontmatter 不整備 | 2-1 |
| /recover 手書き Read | 2-2 |
| skill description / allowed-tools 「事前許可」明記 | 2-3 |
| 公式 schedule/loop スキル未連携 | 2-4 + 3-1 + 3-3 |
| Plan 方針矛盾 | 3-1 + 1-4 |
| 3-failure recovery を ScheduleWakeup 依存 → 公式 schedule 経由へ | 3-1 |
| Migration / INTEGRATION ガイド不在 | 3-2, 3-3 |
| task_ids フィールド不在 | 3-4 |
| LEARNINGS 未更新 + grep 習慣の記録 | 3-5 |

## 自己レビュー

- 仕様カバレッジ: Round 1 (5) + Round 2 (5) + Round 3 (10) + 自己発見 (5) = 計 25 件すべてに Task 対応 ✓
- 矛盾解消: Plan 方針、self-review 経路の二箇所いずれも全文統一 ✓
- 撤回項目の明示: Task 0-4 (user-invocable)、ScheduleWakeup/RemoteTrigger matcher、`if` を Edit() に絞る案、PostToolUse 変更不要、Phase 0b への `if` 削除振り分け ✓
- 全 hook 出力形式の grep 確認実施、同種見落としを一気に Phase 0a で潰す ✓
- 制御方式の正確性: PreToolUse=hookSpecificOutput / PostToolUse/Stop/SubagentStop/PreCompact=トップレベル decision / **TaskCreated=continue:false (hard stop) / TaskCompleted=exit 2 + stderr (差し戻し)** / UserPromptSubmit/PostToolUseFailure/SessionStart=hookSpecificOutput.additionalContext ✓
- `stop_hook_active` ガード明示 ✓

## リスク

- **R1: hook 出力スキーマ移行で deny/block が想定通り効かない** → 対策: 0a-1〜0a-4 で全 hook の出力契約テスト必須化、E2E で gate tamper を Edit/Write/NotebookEdit 全て発火確認
- **R2: スキル改名で外部プロジェクト（uccc）参照が壊れる** → 対策: README に Migration、reference drift check
- **R3: `tool_response` キー名の不確定性** → 対策: 両キー対応 + 実機検証ログ
- **R4: reviewer-* Sonnet 昇格コスト増** → 対策: 既知トレードオフ（リスク回避優先）
- **R5: Stop hook 誤検知** → 対策: `stop_hook_active` ガード + env var バイパス
- **R6: TaskCreated（continue:false hard stop）/ TaskCompleted（exit 2 差し戻し）の制御仕様変更** → 対策: docs WATCH、payload 正規化、両方式の互換テスト、`raw_input` ダンプは gitignore 対象に限定
- **R7: Plan 条件付き許可が gate 素通り** → 対策: CLAUDE.md / routing.md 二重記載
- **R8: `if` 削除でフック起動コスト増** → 対策: script 早期 return（ms 単位完了）、ベンチマーク取得（許容範囲内なら 1 handler 維持、超過なら 3 handler 分割へ後退）
- **R9: PostToolUseFailure 移行で成功時通知消失** → 対策: 意図通り（成功時通知に意味なし）
- **R10: 公式 `schedule` スキル仕様変更** → 対策: docs WATCH、INTEGRATION.md に依存箇所集約
- **R11 (新)**: pre-compact.sh の出力形式変更でユーザーの compaction フローが変わる → 対策: Migration v0.12.1→v0.12.2 で動作変化を明記、reason がメッセージとして見える形になる旨を周知

## 完了条件

- [ ] Phase 0a〜3 全 Task の Deliverable
- [ ] 既存 118 テスト + 新規テスト全 PASS
- [ ] tier 1/2 eval PASS
- [ ] check_framework_contract.py / check_reference_drift.py / check_status.py 全 PASS
- [ ] CLAUDE.md word count <= 800
- [ ] STATUS.md framework_version: 0.13.0、iteration: 7、全 gate approved
- [ ] README に Migration v0.12.1→v0.12.2→v0.13.0 完備
- [ ] LEARNINGS.md 追記
- [ ] git tag v0.12.2 + v0.13.0
- [ ] external_evidence に Round 1 / Round 2 / Round 3 / 最終レビュー結果記録

## QA チェックリスト

- [ ] PreToolUse hook の deny を 5 ケース以上確認
- [ ] PostToolUse hook の block を gate/phase/mode × Edit/Write/NotebookEdit の 9 ケース確認
- [ ] PostToolUseFailure の `additionalContext` 通知動作確認
- [ ] **PreCompact の block (top-level reason) と allow (additionalContext + hookEventName) を確認**
- [ ] Write(STATUS.md) / NotebookEdit(STATUS.md) で gate tamper 発火確認（`if` 削除確認）
- [ ] **TaskCreated hook が `{"continue": false, "stopReason": "..."}` で hard stop**、**TaskCompleted hook が exit code 2 + stderr で差し戻し** 動作確認
- [ ] TaskCreated/Completed の matcher 非対応に伴う**早期 return**（不該当ペイロード）テスト確認
- [ ] `raw_input` ダンプ先が `.claude/.task-event-debug.log`（gitignore 対象）に限定されている
- [ ] **Stop hook の `stop_hook_active: true` で早期 return 確認**
- [ ] スキル改名後の grep で旧名残存ゼロ
- [ ] agent frontmatter 全 12 件で推奨マトリクス通り
- [ ] /gate /validate /recover の argument-hint Tab 補完
- [ ] examples/minimal-project でフレームワーク契約テスト PASS
- [ ] `tool_response` キー実機検証ログが存在
- [ ] CLAUDE.md / routing.md / Phase 3 から `ScheduleWakeup` 文字列が consumer 文脈で消滅

<!-- exit-check: タスク分解完了・トレーサビリティ充足・矛盾解消済み・全 hook 出力形式 grep 確認済み・実機検証保留点明示・hook 制御方式の正確性確認済み → 最終レビュー → implement -->
