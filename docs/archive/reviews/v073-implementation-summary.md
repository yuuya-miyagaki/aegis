# Ultra Framework CC v0.7.3 実装サマリ

> 日付: 2026-04-17
> 前バージョン: v0.7.2 (commit 2604ccb)
> スコープ: Skills & MCP 改善（3 本柱）
> 仕様書: `docs/specs/skills-mcp-improvement-report.md`

---

## 1. 背景と目的

v0.7.2 までの Skills と MCP を、ワークスペース内の 4 フレームワーク
（Superpowers, gstack, ECC, claude-code-best-practice）および最新の
Claude Code 公式機能と比較調査。**薄さを壊さず不均一な部分を統一し、
欠けているピースを埋める** 方針で 3 本柱に絞った。

---

## 2. 変更内容（3 本柱）

### 柱 1: qa-verification スキル新設

**課題:** Dev フェーズ 9 つの中で、qa フェーズのみスキルが紐づいていなかった。

**変更:**
- `.claude/skills/qa-verification/SKILL.md` を新設
  - テストスイート実行手順
  - 再現手順の構造化テンプレート
  - エビデンス収集チェックリスト
  - qa-browser エージェントへの委譲ルール
  - QA レポート出力テンプレート
  - 禁止事項（エビデンスなき PASS 防止）

### 柱 2: エージェント skills preload 統一

**課題:** implementer だけ `skills: [tdd]` があり、reviewer/security/qa は
スキルなしで不均一だった。

**変更:**

| エージェント | 変更前 | 変更後 |
|-------------|--------|--------|
| qa.md | skills なし | `skills: [qa-verification]` |
| reviewer.md | skills なし | `skills: [review]` |
| security.md | skills なし | `skills: [security-review]` |
| implementer.md | `skills: [tdd]` | 変更なし |

- 全エージェントの `readOnly: true` + `permissionMode: plan` は維持
- 信頼境界に影響なし（スキルは参照文書として preload されるのみ）

### 柱 3: MCP カタログを extensions/mcp/ で提供

**課題:** MCP サーバーの推奨カタログ・設定テンプレートがなかった。

**変更:**
- `extensions/mcp/README.md` — 推奨サーバー一覧、フェーズ別マッピング、注意事項
- 5 つの JSON テンプレート:

| ファイル | パッケージ / URL | 推奨フェーズ |
|----------|------------------|-------------|
| `playwright.json` | `@playwright/mcp` | qa |
| `github.json` | `@modelcontextprotocol/server-github` | deploy, review |
| `context7.json` | `@upstash/context7-mcp` | implement, brainstorm |
| `vercel.json` | `https://mcp.vercel.com/sse` (remote) | deploy |
| `figma.json` | `figma-developer-mcp` | brainstorm, implement |

- core 契約外（manual opt-in）。settings.json から自動参照されない
- `.mcp.json` に実トークンを入れた場合の gitignore 警告を README に記載

---

## 3. 付帯変更

| 変更 | 対象ファイル |
|------|-------------|
| session-start.sh qa ヒントに `skill: qa-verification` 追加 | `hooks/session-start.sh` |
| session-start.sh security ヒントに `skill: security-review` 追加 | 同上 |
| CLAUDE.md Skills 一覧に `qa-verification` 追加 | `CLAUDE.md`, `templates/CLAUDE.template.md`, `examples/.../CLAUDE.md` |
| バージョン 0.7.2 → 0.7.3 | `STATUS.md` x2, `STATUS.template.md`, `check_framework_contract.py` |
| バリデータに qa-verification 追加 | `scripts/check_framework_contract.py` (REQUIRED_SKILL_FILES, REQUIRED_EXAMPLE_SKILL_DIRS) |
| README マイグレーションセクション追加 | `README.md` |
| スキル数 11 → 12 | `docs/STATUS.md` Summary |

---

## 4. Example プロジェクト同期

以下を root → example にミラー:

- `.claude/skills/qa-verification/SKILL.md`（新規コピー）
- `.claude/agents/qa.md`, `reviewer.md`, `security.md`（skills 追加）
- `hooks/session-start.sh`（ヒント更新）
- `CLAUDE.md`（スキル一覧更新）
- `docs/STATUS.md`（バージョン更新）

`docs/STATUS.md` はバージョンのみ同期（内容は root が実稼働状態を保持するため異なる）。
それ以外は `diff` で identical 確認済み。

---

## 5. 変更ファイル一覧

### 新規ファイル（8 件）

| ファイル | 内容 |
| -------- | ---- |
| `.claude/skills/qa-verification/SKILL.md` | QA 検証プロセススキル |
| `examples/.../skills/qa-verification/SKILL.md` | 同上（example ミラー） |
| `extensions/mcp/README.md` | MCP カタログ README |
| `extensions/mcp/playwright.json` | Playwright MCP テンプレート |
| `extensions/mcp/github.json` | GitHub MCP テンプレート |
| `extensions/mcp/context7.json` | Context7 MCP テンプレート |
| `extensions/mcp/vercel.json` | Vercel MCP テンプレート |
| `extensions/mcp/figma.json` | Figma MCP テンプレート |

### 編集ファイル（17 件）

| ファイル | 変更内容 |
| -------- | -------- |
| `.claude/agents/qa.md` | `skills: [qa-verification]` 追加 |
| `.claude/agents/reviewer.md` | `skills: [review]` 追加 |
| `.claude/agents/security.md` | `skills: [security-review]` 追加 |
| `CLAUDE.md` | Skills 一覧に qa-verification 追加 |
| `README.md` | v0.7.2→v0.7.3 マイグレーションセクション追加 |
| `docs/STATUS.md` | v0.7.3 状態更新 |
| `examples/.../agents/qa.md` | skills 追加（root ミラー） |
| `examples/.../agents/reviewer.md` | 同上 |
| `examples/.../agents/security.md` | 同上 |
| `examples/.../CLAUDE.md` | Skills 一覧更新 |
| `examples/.../docs/STATUS.md` | バージョン更新 |
| `examples/.../hooks/session-start.sh` | ヒント更新 |
| `hooks/session-start.sh` | qa/security ヒント更新 |
| `scripts/check_framework_contract.py` | VERSION + REQUIRED_SKILL 追加 |
| `templates/CLAUDE.template.md` | Skills 一覧更新 |
| `templates/STATUS.template.md` | バージョン更新 |
| `templates/profiles/full.json` | qa-verification を recommended に追加 |

### レビュー・記録成果物（4 件）

| ファイル | 内容 |
| -------- | ---- |
| `docs/qa-reports/v073-review.md` | コードレビューレポート |
| `docs/qa-reports/v073-qa.md` | QA 検証レポート |
| `docs/qa-reports/v073-security.md` | セキュリティレビューレポート |
| `docs/v073-implementation-summary.md` | 本サマリ |

---

## 6. レビュー結果サマリ

| フェーズ | 結果 | 主な指摘 |
|----------|------|---------|
| Review | PASS | Minor x2: MCP パッケージ名誤り、メタデータフィールド注記不足 → 修正済み |
| QA | PASS | 38/38 項目 PASS、ブロッカーなし |
| Security | PASS | P2 x1 (gitignore 警告不足 → 修正済み)、P3 x2 (残留リスク: @latest ピンニング、将来の skill セマンティクス変更) |

---

## 7. 検証結果

```
$ python3 scripts/check_framework_contract.py
PASS: ultra-framework-claude-code contract is aligned

$ python3 scripts/check_status.py --root .
PASS: status file is valid

CLAUDE.md 語数: 373 / 375 / 378（上限 650）
```

---

## 8. 未実施・将来検討

以下は v0.7.3 スコープ外として見送り（仕様書 Section 5 "将来検討" 参照）:

- `allowed-tools` スキル frontmatter（v0.8.0 候補）
- `paths` 自動アクティベーション
- MCP 検出（session-start.sh）
- Agent Teams
- Stop Hook
- Preamble System
- `disallowedTools` エージェント拡張
- スキルテスト基盤

---

## 9. 残フェーズ

| フェーズ | 状態 |
|----------|------|
| brainstorm | approved（調査レポート）|
| plan | approved（同上）|
| implement | 完了 |
| review | approved |
| qa | approved |
| security | approved |
| **deploy** | **未実施（コミット待ち）** |
| ship | 未実施 |
| docs | 未実施 |
