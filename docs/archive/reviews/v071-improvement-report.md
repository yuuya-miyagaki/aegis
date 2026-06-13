# Ultra Framework Claude Code v0.7.1 改善報告書

> 対象: `ultra-framework-claude-code/` v0.7.0 → v0.7.1
> 日付: 2026-04-15

## 変更概要

v0.7.1 は **Claude Code ネイティブ機能の活用度改善** に焦点を当てたリリース。
Codex セカンドオピニオン（ネイティブ機能評価 8.5/10）の指摘に基づき、
独自検証を経て 3 つの改善と release metadata 修正を実施。

## Phase 1: ネイティブ機能改善（3 件）

### 1-1. PreCompact フック追加

| 項目 | 内容 |
|------|------|
| ファイル | `hooks/pre-compact.sh` (root + example) |
| 登録 | `templates/hooks.template.json`, `examples/.claude/settings.json` |
| バリデータ | `check_framework_contract.py` に REQUIRED_HOOK_FILES + REQUIRED_HOOK_REGISTRATIONS 追加 |

**挙動:**
- STATUS.md の最終更新から 5 分以上経過 + アクティブフェーズあり → `exit 2` + `{"decision":"block"}` でコンパクション阻止
- STATUS.md が最近更新済み or フェーズなし → `exit 0` で許可（コンテキストサマリー付き）

**設計判断:**
- PostCompact フックはランタイムスキーマ検証が拒否（"Invalid key in record" エラー）。
  SessionStart の compact マッチャーが post-compact コンテキスト復元を提供済みのため不採用。

### 1-2. qa-browser エージェント分離

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/agents/qa-browser.md` (root + example) |
| 修正 | `.claude/agents/qa.md` (root + example) |
| ルーティング | `.claude/rules/routing.md` (root + example) |
| バリデータ | `check_framework_contract.py` に REQUIRED_AGENT_FILES + REQUIRED_EXAMPLE_FILES 追加 |

**責務分担:**
- qa-browser: Playwright MCP で証拠を収集し、結果を呼び出し元に返す。ファイル書き込み不可。
- qa: qa-browser から返された証拠を QA レポートに追記する責任。

**権限設計:**
- `readOnly: false` + `disallowedTools: [Edit, Write, NotebookEdit, Bash]`
- Bash を除外する理由: issue #31292（Bash 経由で `sed -i`, `echo >` 等のファイル変更が可能）

### 1-3. auto-memory ポリシー緩和

| 項目 | 内容 |
|------|------|
| 変更 | `CLAUDE.md` x3 (root + template + example) |

**変更前:** `Persist lessons in docs/LEARNINGS.md, not auto-memory.`
**変更後:** `Persist lessons in docs/LEARNINGS.md. Auto-memory may store personal preferences only; it must not duplicate LEARNINGS.`

## Phase 2: Codex レビュー修正（3 件）

| ID | 指摘 | 修正内容 |
|----|------|---------|
| P2-1 | PreCompact が warning だけで block していない | staleness チェック + exit 2 + decision:block を実装 |
| P2-2 | PostCompact 不採用理由が曖昧 | STATUS.md の記述を「ランタイムスキーマ検証が拒否」に具体化 |
| P2-3 | qa-browser の成果物定義と権限が矛盾 | 「証拠を返す」のみに責務を限定、qa 側に追記責任を明記 |

## Phase 3: Release metadata 修正（4 件）

| ID | 内容 |
|----|------|
| A-1 | バージョン bump 0.7.0 → 0.7.1（4 ファイル） |
| A-2 | README エージェント数 9→10、PreCompact 説明を block 挙動に更新 |
| P3 | STATUS.md Summary 冒頭を v0.7.1 に更新 |
| A-3 | 本報告書の作成 |

## Phase 4: 持ち越し課題修正（3 件）

| ID | 内容 |
|----|------|
| B-1 | external_evidence.type の WARNING lint（check_status.py + template） |
| B-2 | /next コマンドで body Session History 整理リマインダー |
| C-4 | subagent-dev の TaskCreate 文言を session-local に弱める |

## レビュー経緯

- ネイティブ機能評価: Codex セカンドオピニオン 1 回（8.5/10 評価、4 件採用推奨）
- 独自検証: 4 並列リサーチエージェントで Codex の主張を検証（PreCompact/PostCompact、disallowedTools、/loop、Agent Teams）
- 実装後レビュー: Codex セカンドオピニオン 1 回（P2 x3）
- Release metadata レビュー: Codex セカンドオピニオン 1 回（P1 x1, P2 x2, P3 x1）
- レビュー文書は `docs/reviews/` にアーカイブ予定

## バリデーション結果

```
PASS: ultra-framework-claude-code contract is aligned
PASS: status file is valid: docs/STATUS.md
PASS: status file is valid: examples/minimal-project/docs/STATUS.md
```

## 変更ファイル数

| カテゴリ | ファイル数 |
|----------|-----------|
| フック | 2 (pre-compact.sh x2) |
| エージェント | 4 (qa-browser.md x2, qa.md x2) |
| ルーティング | 2 (routing.md x2) |
| 制御ファイル | 3 (CLAUDE.md x3) |
| フック登録 | 2 (hooks.template.json, example settings.json) |
| バリデータ | 1 (check_framework_contract.py) |
| ドキュメント | 5 (STATUS.md, README.md, v071-improvement-report.md, STATUS.template.md, example STATUS.md) |
| **合計** | **~19 ファイル** |

## 残課題

v0.7.1 スコープ外とし、次バージョンで検討する項目:

- narrow YAML パーサーの PyYAML 移行判断（3 段ネスト必要時に再検討）
- body Session History の自動アーカイブ（v0.7.1 で /next リマインダーを追加済み。自動アーカイブ自体は次バージョンで検討）
