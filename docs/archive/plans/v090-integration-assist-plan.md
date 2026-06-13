# Plan: integration-assist — gstack $B を活用した外部サービス連携スキル

## Context

ユーザー課題: 外部サービス連携（Slack, Stripe, Firebase 等）の際、API キー取得・OAuth 設定などの「技術的橋渡し」が非エンジニアにはハードル。

解決策: gstack の `$B handoff/resume` を活用し、Claude Code がブラウザ操作で 90% 自動化。ユーザーはパスワード入力・承認クリックだけ。

gstack `$B` は CLI バイナリ（`~/.claude/skills/gstack/browse/dist/browse`）で、Bash から直接呼べる。MCP 不要。handoff で可視ブラウザに切替→ユーザー操作→resume で AI に制御復帰。状態（Cookie, localStorage, タブ）は完全保持。

## Approach

Ultra Framework に `integration-assist` スキルを追加する。v0.9.0 スコープ。

## 実装内容

### 1. integration-assist スキル（新規）

**ファイル**: `.claude/skills/integration-assist/SKILL.md`

**内容**:
- $B バイナリ解決ロジック（gstack 標準パターン）
- サービス連携の 6 ステップワークフロー:

```
Step 1: サービス特定
  ユーザー: 「Slack と繋げたい」
  → Claude: サービス名を特定

Step 2: ドキュメント調査
  → Firecrawl/Context7/WebSearch でAPI ドキュメントを検索・読解
  → 必要な情報（Token, API Key, Webhook URL 等）を特定
  → セットアップ手順を把握

Step 3: 自動ブラウザ操作
  $B goto <サービスの設定ページ URL>
  $B snapshot -i
  $B fill @eN "<アプリ名>"
  $B fill @eN "<コールバック URL>"
  $B fill @eN "<スコープ等の設定値>"
  → フォームの自動入力（アプリ名、URL、説明文等）

Step 4: handoff（ユーザー最小介入）
  $B handoff "パスワードを入力して「Allow」を押してください"
  → 可視ブラウザが開く（同じページ、同じ入力状態）
  → ユーザー: パスワード入力 / 承認クリック / 2FA のみ
  $B resume
  → AI に制御復帰

Step 5: 結果取得 + 設定生成
  $B snapshot
  → Token/Key が表示されたページからテキスト抽出
  → .env ファイル生成（.gitignore 確認含む）
  → 接続コード実装

Step 6: 接続テスト + 最終承認
  → テストコード実行（API 疎通確認）
  → 結果をユーザーに表示
  → ユーザー: 「OK」で完了
```

- セキュリティルール:
  - パスワードは handoff 経由でユーザーが直接入力（Claude に渡さない）
  - Token/Key は .env に書き、.gitignore に追加
  - コミット前に .env がステージングされていないか確認
- $B 未インストール時のフォールバック:
  - 「案内型」に切り替え（URL とステップを提示、ユーザーが手動操作）

### 2. integration-specialist エージェント（新規）

**ファイル**: `.claude/agents/integration-specialist.md`

**frontmatter**:
```yaml
---
description: "Trigger: external service integration, API setup, OAuth configuration, connect to third-party service"
model: inherit
maxTurns: 30
readOnly: false
permissionMode: default
effort: high
color: "#4A90D9"
skills:
  - integration-assist
allowedTools:
  - Edit
  - Write
  - Read
  - Grep
  - Glob
  - Bash
  - WebSearch
  - WebFetch
---
```

**役割**:
- 外部サービス連携の専門エージェント
- $B コマンドを使ったブラウザ操作
- API ドキュメント調査→自動設定→テスト
- ユーザー介入を最小化する設計

**制約**:
- handoff 時にパスワード/シークレットを要求しない
- .env に書いた値をログ/レポートに含めない
- 30 ターン以内に完了
- hallucination guard: 接続テスト成功なしに完了を主張しない

### 3. 既存ファイル更新

| ファイル | 変更内容 |
|---------|---------|
| `CLAUDE.md` | Skills リストに `integration-assist` 追加 |
| `templates/CLAUDE.template.md` | 同上 |
| `examples/minimal-project/CLAUDE.md` | 同上 |
| `.claude/rules/routing.md` | integration-specialist のルーティング追加 |
| `templates/profiles/full.json` | agent + skill を recommended に追加 |
| `scripts/check_framework_contract.py` | 新 agent + skill をバリデーション対象に追加、FRAMEWORK_VERSION bump |
| `docs/STATUS.md` | version bump, phase/gates リセット |
| `README.md` | agent count 11→12, skill count 13→14, Migration セクション追加 |
| `hooks/session-start.sh` | implement フェーズのヒントに integration-assist を追加（該当する場合） |

### 4. $B 依存の扱い

**方針**: gstack をバンドルしない。オプショナル依存として扱う。

- スキル冒頭で $B バイナリの存在チェック
- 存在する場合: $B を使った自動操作フロー
- 存在しない場合: フォールバック（URL + 手順の案内型）
- `README.md` に gstack browse のセットアップ手順を Extensions セクションに記載

```bash
# $B 解決ロジック（スキル冒頭）
_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
B=""
[ -n "$_ROOT" ] && [ -x "$_ROOT/.claude/skills/gstack/browse/dist/browse" ] && \
  B="$_ROOT/.claude/skills/gstack/browse/dist/browse"
[ -z "$B" ] && [ -x ~/.claude/skills/gstack/browse/dist/browse ] && \
  B=~/.claude/skills/gstack/browse/dist/browse
# $B が見つからない場合はフォールバック案内
```

## ファイル一覧

| # | ファイル | Action |
|---|---------|--------|
| 1 | `.claude/skills/integration-assist/SKILL.md` | CREATE |
| 2 | `.claude/agents/integration-specialist.md` | CREATE |
| 3 | `CLAUDE.md` | EDIT |
| 4 | `templates/CLAUDE.template.md` | EDIT |
| 5 | `examples/minimal-project/CLAUDE.md` | EDIT |
| 6 | `.claude/rules/routing.md` | EDIT |
| 7 | `examples/minimal-project/.claude/rules/routing.md` | EDIT |
| 8 | `templates/profiles/full.json` | EDIT |
| 9 | `scripts/check_framework_contract.py` | EDIT |
| 10 | `docs/STATUS.md` | EDIT |
| 11 | `README.md` | EDIT |

推定変更ファイル: 11 → task_size: M〜L

## Verification

1. `python3 scripts/check_status.py --root .` → PASS
2. `python3 scripts/check_framework_contract.py` → PASS
3. `python3 scripts/check_status.py --root examples/minimal-project` → PASS
4. スキル構造: frontmatter (name, description, disable-model-invocation) 存在確認
5. エージェント構造: CSO description, maxTurns, hallucination guard, rationalization table 存在確認
6. $B 解決ロジックのテスト: バイナリ存在時とフォールバック時の両方を確認
7. CLAUDE.md word count < 650
