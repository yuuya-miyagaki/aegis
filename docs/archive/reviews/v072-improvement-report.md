# Ultra Framework Claude Code v0.7.2 改善報告書

> 対象: `ultra-framework-claude-code/` v0.7.1 → v0.7.2
> 日付: 2026-04-15

## 変更概要

v0.7.2 は **scaffold 自己完結性修正** と **信頼境界ハードニング** に焦点を当てたリリース。
Codex 最終レビュー（P1x2, P2x3, P3x1）のうち即時修正対象 3 件（P1-1, P1-2, P2-5 部分）を実施。

## Phase 1: テンプレート参照名ドリフト修正（5 ファイル 7 箇所）

v0.6.0 の skills 移行時に更新漏れした旧名を正名に統一。

| ファイル | 旧 | 新 |
|---------|---|---|
| `templates/PLAN.template.md` | `subagent-development` | `subagent-dev` |
| `templates/VERIFICATION.template.md` | `test-driven-development` (x2) | `tdd` |
| `templates/DEPLOY-CHECKLIST.template.md` | `deploy-platforms` | `deploy` スキル（platforms.md） |
| `hooks/session-start.sh` | `subagent-development` (x3) | `subagent-dev` |
| `examples/.../hooks/session-start.sh` | 同上 (x3) | `subagent-dev` |
| `examples/.../README.md` | `9 agents` | `10 agents` |

## Phase 2: /validate scaffold 対応（3 ファイル）

| 項目 | 内容 |
|------|------|
| 問題 | scaffold project で `/validate` 実行時に `check_framework_contract.py` が失敗する |
| 原因 | `check_framework_contract.py` は framework-repo 専用（全ファイル存在チェック） |
| 修正 | example の `validate.md` を `check_status.py` のみ実行に書き換え |
| 同梱 | `scripts/check_status.py` を example project に同梱（実体コピー） |
| 追加 | README Quick Start に step 11（check_status.py コピー手順）を追加 |
| 追加 | example README に `scripts/check_status.py` を Included セクションに追記 |
| バリデータ | `REQUIRED_EXAMPLE_FILES` に `examples/.../scripts/check_status.py` を追加 |

**設計判断:**
- root 側の `/validate` は両バリデータ実行を維持（framework repo 用）
- scaffold 側は `check_status.py` のみ（STATUS.md スキーマ検証で十分）
- example は自己完結（`/validate` 実行に framework repo 依存なし）

## Phase 3: 信頼境界ハードニング（8 ファイル）

### 3A. check-control-plane.sh 新規作成

| 項目 | 内容 |
|------|------|
| ファイル | `hooks/check-control-plane.sh` (root + example) |
| 種別 | Bash PreToolUse フック |
| 判定 | `deny`（ハードブロック） |
| 戦略 | **allowlist 方式**（blacklist ではない） |
| 対象 | control plane パス（STATUS.md, CLAUDE.md, .claude/, hooks/, scripts/）を参照する Bash コマンド全般 |
| 例外 | `task_type=framework` 時は許可 |
| Allowlist | `update-gate.sh`, `check_status.py`, `check_framework_contract.py` + 読み取り専用コマンド |

**判定ロジック:**
1. コマンドが control plane パスを含まない → 許可
2. チェーン演算子（`;`, `&&`, `||`, `|`, `$()`, `` ` ``）を含むか判定
3. チェーンなし + Allowlist スクリプトのみ → 許可
4. task_type=framework → 許可
5. チェーンなし + 既知の読み取り専用コマンド（cat, grep, ls 等）+ 書き込みインジケータなし → 許可
6. 上記いずれにも該当しない → deny

**チェーン演算子ガード:**
- `validator && malicious` のような連結 bypass を防止
- チェーン演算子を含むコマンドは allowlist/read-only チェックをスキップし、原則 deny に落とす
- python3 JSON パーサーによるフル抽出で引用符truncation も回避

**設計判断の経緯:**
1. 初版: write-op blacklist → `python3 -c "Path(...).write_text(...)"` で bypass
2. 第2版: allowlist 方式（raw input チェック）→ `validator && malicious` チェーンで bypass
3. 最終版: allowlist + チェーン演算子ガード + python3 フル抽出。21 テストケース全 OK

### 3B. NotebookEdit マッチャー追加

| 項目 | 内容 |
|------|------|
| 変更 | `templates/hooks.template.json`, `examples/.../settings.json` |
| PreToolUse | `Edit|Write` → `Edit|Write|NotebookEdit` |
| PostToolUse | 同上 + `if` 条件に `NotebookEdit(*STATUS.md)` 追加 |

**設計判断:**
- NotebookEdit は `.ipynb` 専用ツール（STATUS.md には到達不可能）
- defense-in-depth としてマッチャーの網羅性を担保

### 3C. extract_file_path notebook_path フォールバック

| 項目 | 内容 |
|------|------|
| 変更 | `hooks/lib/extract-input.sh` (root + example) |
| 内容 | `file_path` が空なら `notebook_path` を試行 |
| 影響 | 全依存フック（check-gate, check-tdd, post-status-audit）が恩恵 |

### 3D. フック登録順序

Bash PreToolUse: `check-control-plane.sh` → `check-destructive.sh`（deny が先、warn が後）

## Phase 4: Metadata 更新

| ID | 内容 |
|----|------|
| 4-1 | バージョン bump 0.7.1 → 0.7.2（4 ファイル） |
| 4-2 | バリデータ更新（REQUIRED_HOOK_FILES + REGISTRATIONS に check-control-plane.sh 追加） |
| 4-3 | STATUS.md Summary, Recent Decisions, session_history 更新 |
| 4-4 | README Hooks セクション + Migration セクション更新 |
| 4-5 | 本報告書の作成 |

## レビュー経緯

- Codex 最終レビュー: 6 件（P1x2, P2x3, P3x1）
- 即時修正: P1-1（scaffold /validate）, P1-2（信頼境界）, P2-5 部分（参照名ドリフト）
- 延期（v0.8.0）: P2-3（/gate 文脈妥当性）, P2-4（lean/full 一本化）, P3-6（STATUS 劣化対策）
- レビュー文書は `docs/reviews/` にアーカイブ

## バリデーション結果

```
PASS: ultra-framework-claude-code contract is aligned
PASS: status file is valid: docs/STATUS.md
PASS: status file is valid: examples/minimal-project/docs/STATUS.md
```

## 変更ファイル数

| カテゴリ | ファイル数 |
|----------|-----------|
| フック（新規） | 2 (check-control-plane.sh x2) |
| フック（修正） | 4 (session-start.sh x2, extract-input.sh x2) |
| テンプレート | 3 (PLAN, VERIFICATION, DEPLOY-CHECKLIST) |
| コマンド | 1 (example validate.md) |
| フック登録 | 2 (hooks.template.json, example settings.json) |
| バリデータ | 1 (check_framework_contract.py) |
| スクリプト（同梱） | 1 (example check_status.py) |
| ドキュメント | 6 (STATUS.md x3, README.md x2, 本報告書) |
| **合計** | **新規 3 + コピー 1 + 編集 16 = 20 ファイル** |

## 延期事項（v0.8.0）

- P2-3: /gate の phase/gate/ref 条件チェック
- P2-4: lean 導入方針と validator profile 化
- P2-5 残り: skill/agent/command 名の自動 lint
- P3-6: body history 長 warning、archive lint、last_updated 同期
