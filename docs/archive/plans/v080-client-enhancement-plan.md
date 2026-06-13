# v0.8.0 Client モード強化 — 実装計画

<!-- 正本: subagent-dev skill -->

## 目的

- Client モードに構造化された情報収集基盤（docs/client/）と翻訳層（docs/translation/）を導入する
- translation mapping を handover 前必須 artifact として gate 契約に組み込む
- Client モードの目的（purpose statement）を state-machine に明文化する
- フレームワーク全体の整合性を維持しつつ 25 ファイル（新規 13 + 更新 12）を確実に適用する

## 入力

- 参照設計: `docs/specs/v080-client-enhancement-brainstorm.md`
- 参照状態: `docs/STATUS.md`（v0.7.3 時点）

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: n/a（フレームワーク内部変更のみ）
- Database: n/a
- CI/CD: n/a（ローカル validator で検証）

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: n/a

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

feature branch (`feat/v080-client-enhancement`) + squash merge to main。
各フェーズ完了時に中間コミット。

## ファイル構造（変更マップ）

### 新規作成ファイル（13 ファイル）

| # | パス | 責務 |
|---|------|------|
| N1 | `templates/CLIENT-CONTEXT.template.md` | クライアント基本情報テンプレート（context.md 専用） |
| N2 | `templates/CLIENT-GLOSSARY.template.md` | 用語集テンプレート（glossary.md 専用） |
| N3 | `templates/CLIENT-OPEN-QUESTIONS.template.md` | 未解決事項テンプレート（open-questions.md 専用） |
| N4 | `templates/TRANSLATION-MAPPING.template.md` | 3 層マッピングテンプレート |
| N5 | `templates/DECISION.template.md` | 意思決定レコードテンプレート |
| N6 | `docs/client/context.md` | フレームワークリポジトリ内のサンプル実体（scaffold ソース検証用） |
| N7 | `docs/client/glossary.md` | 用語集サンプル実体 |
| N8 | `docs/client/open-questions.md` | 未解決事項サンプル実体 |
| N9 | `docs/translation/mapping.md` | マッピングサンプル実体 |
| N10 | `docs/decisions/.gitkeep` | 意思決定ログディレクトリ（空ディレクトリ保持用） |
| N11 | `.claude/agents/translation-specialist.md` | translation 支援 Agent 定義 |
| N12 | `.claude/skills/translation-mapping/SKILL.md` | mapping 作成ガイド Skill 定義 |
| N13 | `hooks/check-client-info.sh` | context.md 必須チェック Hook |

### 既存更新ファイル（12 ファイル）

| # | パス | 変更概要 |
|---|------|----------|
| U1 | `templates/STATUS.template.md` | `client_context` フィールド追加 + `current_refs.translation` 追加 |
| U2 | `scripts/check_status.py` | `OPTIONAL_TOP_LEVEL_KEYS` に `client_context` 追加、`EXPECTED_CURRENT_REF_KEYS` に `translation` 追加、`extract_client_context()` パーサー追加、`pre_approve_gate()` に `client_ready_for_dev` 時 mapping.md チェック追加 |
| U3 | `scripts/check_framework_contract.py` | `REQUIRED_TEMPLATE_FILES` に N1-N5 追加、`REQUIRED_AGENT_FILES` に N11 追加、`REQUIRED_SKILL_FILES` に N12 追加、`REQUIRED_HOOK_FILES` に N13 追加、`REQUIRED_EXAMPLE_FILES` に example 側の対応ファイル追加、`REQUIRED_EXAMPLE_SKILL_DIRS` に `translation-mapping` 追加、`REQUIRED_HOOK_REGISTRATIONS` に `check-client-info.sh` 追加、`FRAMEWORK_VERSION` を `"0.8.0"` に更新（最終タスク） |
| U4 | `bin/setup.sh` | `resolve_source()` に 5 マッピング追加（context→CLIENT-CONTEXT, glossary→CLIENT-GLOSSARY, open-questions→CLIENT-OPEN-QUESTIONS, mapping→TRANSLATION-MAPPING, decisions 用 mkdir） |
| U5 | `.claude/rules/state-machine.md` | Client mode purpose statement 追加 |
| U6 | `.claude/skills/client-workflow/SKILL.md` | translation artifact 要件追加、docs/client/ + docs/translation/ 参照追加、handover 前 mapping.md 必須の記述 |
| U7 | `.claude/commands/next.md` | handover 行に mapping.md 要件追記、Client mode テーブルに translation artifact 言及 |
| U8 | `templates/HANDOVER-TO-DEV.template.md` | 正本に `docs/translation/mapping.md` 参照追加 |
| U9 | `templates/profiles/full.json` | 新 agent/skill/hook 追加 + `docs/client/*` `docs/translation/*` 実ファイルパス追加（テンプレートは載せない — setup.sh が間接参照） |
| U10 | `templates/profiles/standard.json` | `docs/client/*` `docs/translation/*` 実ファイルパスを recommended に追加（テンプレートは載せない） |
| U11 | `hooks/session-start.sh` | Client handover ヒントに translation artifact 言及追加 |
| U12 | `templates/hooks.template.json` | `check-client-info.sh` の Hook 登録追加 |

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 (テンプレート N1-N5) | CLIENT-CONTEXT, CLIENT-GLOSSARY, CLIENT-OPEN-QUESTIONS, TRANSLATION-MAPPING, DECISION | なし |
| Task 2 (ディレクトリ + 実体 N6-N10) | docs/client/*, docs/translation/*, docs/decisions/ | N1-N4 (テンプレート構造を参考) |
| Task 3 (STATUS.template.md U1) | STATUS.template.md 更新版 | なし |
| Task 4 (check_status.py U2) | check_status.py 更新版 | U1 (スキーマ定義) |
| Task 5 (check_framework_contract.py U3 — REQUIRED 追加のみ、VERSION は後) | check_framework_contract.py 部分更新 | N1-N13 (パス一覧) |
| Task 6 (Agent N11) | translation-specialist.md | なし |
| Task 7 (Skill N12) | translation-mapping/SKILL.md | N11 (Agent 参照) |
| Task 8 (Hook N13 + hooks.template.json U12) | check-client-info.sh, hooks.template.json 更新 | なし |
| Task 9 (setup.sh U4) | setup.sh 更新版 | N1-N5 (テンプレートパス) |
| Task 10 (state-machine.md U5) | state-machine.md 更新版 | なし |
| Task 11 (client-workflow SKILL.md U6) | client-workflow/SKILL.md 更新版 | N1-N4 (テンプレート参照), N9 (mapping.md 参照) |
| Task 12 (next.md U7) | next.md 更新版 | なし |
| Task 13 (HANDOVER-TO-DEV.template.md U8) | HANDOVER-TO-DEV.template.md 更新版 | なし |
| Task 14 (session-start.sh U11) | session-start.sh 更新版 | なし |
| Task 15 (profiles U9, U10) | full.json, standard.json 更新版 | N6-N9 (実ファイルパス), N11-N13 (agent/skill/hook) |
| Task 16 (example 同期) | examples/minimal-project/ 更新 | 全新規ファイル |
| Task 17 (バリデーション) | 検証結果 | 全ファイル |
| Task 18 (バージョンバンプ) | FRAMEWORK_VERSION "0.8.0" | Task 17 pass |

## タスク分解

> 6 フェーズ、18 タスク。各フェーズは独立検証可能。

---

### Phase 1: Foundation（テンプレート + ディレクトリ + STATUS スキーマ）

このフェーズは他の全フェーズの前提。テンプレートとディレクトリ構造を確立する。

#### Task 1: テンプレート 5 ファイル作成

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `templates/CLIENT-CONTEXT.template.md`, `templates/CLIENT-GLOSSARY.template.md`, `templates/CLIENT-OPEN-QUESTIONS.template.md`, `templates/TRANSLATION-MAPPING.template.md`, `templates/DECISION.template.md`
**意図:** Client モードの構造化情報収集と翻訳層の雛形を提供する。各 docs ファイルに 1:1 で対応するテンプレートを用意し、setup.sh scaffold で正しく個別生成されるようにする。
**受入条件:**

- CLIENT-CONTEXT.template.md: プロジェクト概要、ステークホルダー、ビジネスコンテキスト、技術環境、制約条件
- CLIENT-GLOSSARY.template.md: 用語テーブル（Client Term / Definition / Context）
- CLIENT-OPEN-QUESTIONS.template.md: 未解決事項テーブル（Question / Raised / Status / Resolution）
- TRANSLATION-MAPPING.template.md: 3 層マッピング構造（Client Term / Functional Meaning / Implementation Hint）+ Invariants + Assumptions + Open Items
- DECISION.template.md: 日付、コンテキスト、選択肢、決定、理由
- 5 ファイルとも exit-check コメントを含む
- `templates/` ディレクトリの命名規則（大文字 + `.template.md`）に準拠

**Deliverable:** [ ] テンプレートが 5 ファイル存在し構造が正しい

#### Task 2: ディレクトリ + サンプル実体作成

**blockedBy:** Task 1 | **モデル:** `sonnet`
**ファイル:** `docs/client/context.md`, `docs/client/glossary.md`, `docs/client/open-questions.md`, `docs/translation/mapping.md`, `docs/decisions/.gitkeep`
**意図:** フレームワークリポジトリ自身の docs 内にサンプル実体を配置する。scaffold 検証と contract validator の参照先として使用。
**詳細:**
- `docs/client/context.md`: フレームワーク自身のクライアント情報（フレームワーク利用者 = クライアントとして記述）。テンプレートの構造に沿うが、プレースホルダではなく実際の値を記入。
- `docs/client/glossary.md`: フレームワーク固有用語の用語集（例: gate, phase, mode, hook, PaC など）。
- `docs/client/open-questions.md`: v0.8.0 時点の未解決事項（例: translation phase 昇格の判断基準は未定 → Phase B で検討）。
- `docs/translation/mapping.md`: フレームワーク用語のマッピングサンプル。3 層マッピングの実例。
- `docs/decisions/.gitkeep`: 空ディレクトリ保持。
**受入条件:**
- 5 ファイルが存在する
- context.md, glossary.md, open-questions.md はテンプレート placeholder (`<記入>`) を含まない（実値が入っている）
- mapping.md も実値入り
- check_framework_contract.py の PLACEHOLDER_PATTERN に引っかからない
**Deliverable:** [ ] ディレクトリ構造が正しく、サンプル実体にプレースホルダなし

#### Task 3: STATUS.template.md 更新

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `templates/STATUS.template.md`
**意図:** STATUS.md のスキーマに client_context と current_refs.translation を追加する。
**詳細:**
- `client_context` を optional フィールドとして frontmatter に追加（`failure_tracking: null` の直前あたり）:
  ```yaml
  client_context:
    client_id: ""
    context_loaded: false
  ```
- `current_refs` ブロックに `translation: null` を追加（`deploy: null` の直後）
- framework_version は変更しない（Task 18 でまとめて実施）
**受入条件:**
- client_context フィールドが frontmatter に存在
- current_refs.translation が null で初期化
- 既存フィールドが破壊されていない
**Deliverable:** [ ] テンプレートのスキーマが正しい

**Phase 1 検証チェックポイント:**
```bash
# テンプレートファイル存在確認
ls -la templates/CLIENT-CONTEXT.template.md templates/TRANSLATION-MAPPING.template.md templates/DECISION.template.md

# ディレクトリ構造確認
ls -la docs/client/ docs/translation/ docs/decisions/

# プレースホルダ検査（テンプレート以外に <記入> 等がないこと）
grep -r '<記入>' docs/client/ docs/translation/ && echo "FAIL: placeholder found" || echo "PASS"

# STATUS.template.md スキーマ確認
grep 'client_context:' templates/STATUS.template.md && grep 'translation:' templates/STATUS.template.md && echo "PASS" || echo "FAIL"
```

---

### Phase 2: Validators（check_status.py + check_framework_contract.py 部分更新）

Phase 1 のスキーマ定義を受けて、バリデータをスキーマに追従させる。

#### Task 4: check_status.py 更新

**blockedBy:** Task 3 | **モデル:** `opus`
**ファイル:** `scripts/check_status.py`
**意図:** STATUS.md の新フィールドをバリデータが認識し、gate 契約に mapping.md チェックを追加する。
**詳細:**

**(a) OPTIONAL_TOP_LEVEL_KEYS に `client_context` を追加**
- L30 付近: `"client_context"` を set に追加

**(b) EXPECTED_CURRENT_REF_KEYS に `translation` を追加**
- L68 付近: `"translation"` を set に追加

**(c) current_refs.translation の型検証追加**
- L498-501 付近: `for scalar_key in [...]` のリストに `"translation"` を追加
  （translation は scalar-or-null）

**(d) extract_client_context() パーサー追加**
- `extract_failure_tracking()` と同様のパターンで `client_context` ブロックを解析
- 必須フィールド: `client_id`, `context_loaded`
- `client_context: null` は未設定（None を返す）
- validate_status_file() 内で呼び出し:
  - `has_top_level_key(frontmatter, "client_context")` の場合のみ検証
  - `client_id` が空文字でないこと（WARNING、FAIL ではない）
  - `context_loaded` が `true` または `false` であること

**(e) pre_approve_gate() に mapping.md チェック追加**
- L686 付近: `client_ready_for_dev` の早期 return を条件付きに変更
- 新ロジック:
  ```python
  if gate_name == "client_ready_for_dev":
      mapping_path = root / "docs" / "translation" / "mapping.md"
      if not mapping_path.exists():
          print("ERROR: docs/translation/mapping.md が見つかりません。")
          print("       handover 前に translation mapping を作成してください。")
          print("       → translation-mapping skill を使用")
          return 1
      return 0
  ```
- `dev_ready_for_client` は引き続き早期 return 0

**受入条件:**
- `python3 scripts/check_status.py --root .` が現行 STATUS.md で PASS（client_context は optional なので未設定でも OK）
- STATUS.template.md に client_context を追加した状態でも PASS
- `--pre-approve-gate client_ready_for_dev` が mapping.md 不在時に ERROR を返す
- `--pre-approve-gate dev_ready_for_client` は従来通り即 return 0
**Deliverable:** [ ] バリデータが新スキーマを正しく検証

#### Task 5: check_framework_contract.py — REQUIRED リスト追加（VERSION 以外）

**blockedBy:** Task 1, Task 2 | **モデル:** `sonnet`
**ファイル:** `scripts/check_framework_contract.py`
**意図:** 新ファイルを contract validator の必須リストに追加する。FRAMEWORK_VERSION は最終 Task で更新。
**詳細:**

**(a) REQUIRED_TEMPLATE_FILES に 5 件追加**

- `ROOT / "templates/CLIENT-CONTEXT.template.md"`
- `ROOT / "templates/CLIENT-GLOSSARY.template.md"`
- `ROOT / "templates/CLIENT-OPEN-QUESTIONS.template.md"`
- `ROOT / "templates/TRANSLATION-MAPPING.template.md"`
- `ROOT / "templates/DECISION.template.md"`

**(b) REQUIRED_AGENT_FILES に 1 件追加**
- `ROOT / ".claude/agents/translation-specialist.md"`

**(c) REQUIRED_SKILL_FILES に 1 件追加**
- `ROOT / ".claude/skills/translation-mapping/SKILL.md"`

**(d) REQUIRED_HOOK_FILES に 1 件追加**
- `ROOT / "hooks/check-client-info.sh"`

**(e) REQUIRED_EXAMPLE_FILES に example 側対応ファイルを追加**
- `ROOT / "examples/minimal-project/docs/client/context.md"`
- `ROOT / "examples/minimal-project/docs/client/glossary.md"`
- `ROOT / "examples/minimal-project/docs/client/open-questions.md"`
- `ROOT / "examples/minimal-project/docs/translation/mapping.md"`
- `ROOT / "examples/minimal-project/hooks/check-client-info.sh"`

**(f) REQUIRED_EXAMPLE_SKILL_DIRS に追加**
- `"translation-mapping"` を配列に追加

**(g) REQUIRED_HOOK_REGISTRATIONS に追加**
- `"PreToolUse"` の配列に `"hooks/check-client-info.sh"` を追加

**(h) READ_ONLY_AGENT_FILES — translation-specialist は READ_ONLY ではない**
- translation-specialist は Write 権限を持つ（mapping.md の作成・更新）ため、READ_ONLY_AGENT_FILES には追加しない

**(i) PLACEHOLDER_ALLOWLIST — 必要に応じて追加**
- テンプレートの `<記入>` 等が example ファイル検査で誤検出される場合、PLACEHOLDER_ALLOWLIST に追加。ただし example の docs/client/* は実値入りなので原則不要。

**受入条件:**
- `python3 scripts/check_framework_contract.py` が（Phase 5 の example 同期完了後に）新ファイル不在を検出する
- FRAMEWORK_VERSION はこの時点では `"0.7.3"` のまま
**Deliverable:** [ ] REQUIRED リストが新ファイルを網羅

**Phase 2 検証チェックポイント:**
```bash
# check_status.py 単体テスト（現行 STATUS.md で PASS すること）
python3 scripts/check_status.py --root .

# pre_approve_gate テスト（mapping.md が存在するので PASS するはず）
python3 scripts/check_status.py --pre-approve-gate client_ready_for_dev --root .

# mapping.md を一時退避して FAIL を確認
mv docs/translation/mapping.md /tmp/mapping_backup.md
python3 scripts/check_status.py --pre-approve-gate client_ready_for_dev --root .
# → ERROR が出ること
mv /tmp/mapping_backup.md docs/translation/mapping.md

# contract validator は example 未同期のため一部 FAIL するが、新パスが REQUIRED に入っていることを確認
python3 scripts/check_framework_contract.py 2>&1 | grep -E "CLIENT-CONTEXT|TRANSLATION-MAPPING|DECISION|translation-specialist|translation-mapping|check-client-info"
```

---

### Phase 3: Core Logic（Agent, Skill, Hook, Scaffold）

フレームワークの機能拡張コアを実装する。

#### Task 6: translation-specialist Agent 作成

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `.claude/agents/translation-specialist.md`
**意図:** Client 用語から実装仕様への変換を支援する Agent を定義する。
**詳細:**
- frontmatter: description（CSO 形式 `"Trigger: ..."`）, model（`sonnet`）, maxTurns（`15`）, readOnly: false, permissionMode, effort, color
- 目的: Client 用語 → 実装仕様の変換支援
- 入力: docs/client/context.md, docs/client/glossary.md, docs/requirements/*
- 出力: docs/translation/mapping.md の作成・更新
- ツール制限: Read, Write, Grep, Glob（コード変更権限なし → allowedTools frontmatter で制限）
- hallucination guard: `do not claim completion without` 文を含む
- ## Known Rationalizations セクションは不要（core agent ではないため）
  ただし ## Boundaries セクションに `complete within 15 turns` を含む
- 呼び出しタイミング: handover 前（client-workflow skill から誘導）

**受入条件:**
- CSO description 形式に準拠
- maxTurns と Boundaries の値が一致
- hallucination guard 文が存在
- readOnly が false（Write 権限あり）
- allowedTools に Edit, Write, Grep, Glob, Read が含まれ、Bash は含まれない
**Deliverable:** [ ] Agent 定義が contract validator の構造チェックを通過

#### Task 7: translation-mapping Skill 作成

**blockedBy:** Task 6 | **モデル:** `sonnet`
**ファイル:** `.claude/skills/translation-mapping/SKILL.md`
**意図:** mapping.md の作成手順を構造化し、translation-specialist agent と連携するガイドを提供する。
**詳細:**
- frontmatter: name（`translation-mapping`）, description, disable-model-invocation: true, user-invocable: false
- セクション: いつ使うか、作成手順（3 層マッピングの埋め方）、テンプレート参照、Agent 連携（translation-specialist を呼ぶ方法）、コンテキスト予算
- 日本語で記述（client-workflow SKILL.md と同じ方針）

**受入条件:**
- frontmatter に name, description が存在
- テンプレートパス（templates/TRANSLATION-MAPPING.template.md）への参照がある
- Agent 連携の記述がある
**Deliverable:** [ ] Skill 定義が contract validator の構造チェックを通過

#### Task 8: check-client-info.sh Hook 作成 + hooks.template.json 更新

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `hooks/check-client-info.sh`, `templates/hooks.template.json`

**(a) check-client-info.sh**
**意図:** requirements 編集前に docs/client/context.md の存在を強制する。
**詳細:**
- トリガー: PreToolUse (Edit, Write)
- 対象パス: `docs/requirements/*` を含むファイルパスのみ
- チェック: `docs/client/context.md` が存在するか
- 不在なら deny + メッセージ:
  ```
  docs/client/context.md が見つかりません。
  requirements 編集の前にクライアント情報を記録してください。
  → client-workflow skill の onboard フェーズを実行
  ```
- 存在すれば `echo '{}'; exit 0`
- MODE が `Dev` の場合はスキップ（Dev モードでは requirements 編集は基本しないが、万一のため）
- `lib/extract-input.sh` を source する（既存 Hook と同じパターン）

**(b) hooks.template.json 更新**
- PreToolUse の Edit|Write|NotebookEdit matcher に `check-client-info.sh` を追加:
  ```json
  {
    "type": "command",
    "command": "bash hooks/check-client-info.sh"
  }
  ```

**受入条件:**
- Hook がファイルパスに `docs/requirements/` を含む場合のみ発火する
- context.md 存在時は `{}` を返す
- context.md 不在時は deny + メッセージを返す
- Dev モード時はスキップ
- hooks.template.json が valid JSON のまま
**Deliverable:** [ ] Hook が正しく deny/allow を返す

#### Task 9: setup.sh 更新

**blockedBy:** Task 1 | **モデル:** `sonnet`
**ファイル:** `bin/setup.sh`
**意図:** scaffold で新テンプレートから実体ファイルを生成する導線を追加する。
**詳細:**

- `resolve_source()` に以下の 1:1 マッピングを追加（各 docs ファイルに専用テンプレートが対応）:

  ```bash
  "docs/client/context.md")        echo "$FRAMEWORK_ROOT/templates/CLIENT-CONTEXT.template.md"; return ;;
  "docs/client/glossary.md")       echo "$FRAMEWORK_ROOT/templates/CLIENT-GLOSSARY.template.md"; return ;;
  "docs/client/open-questions.md") echo "$FRAMEWORK_ROOT/templates/CLIENT-OPEN-QUESTIONS.template.md"; return ;;
  "docs/translation/mapping.md")   echo "$FRAMEWORK_ROOT/templates/TRANSLATION-MAPPING.template.md"; return ;;
  ```

- `docs/decisions/` ディレクトリ作成: required/recommended の copy ループ外に `mkdir -p "$TARGET/docs/decisions"` を追加（profile に docs パスが含まれている場合）

**受入条件:**

- `resolve_source "docs/client/context.md"` が CLIENT-CONTEXT テンプレートを返す
- `resolve_source "docs/client/glossary.md"` が CLIENT-GLOSSARY テンプレートを返す
- `resolve_source "docs/client/open-questions.md"` が CLIENT-OPEN-QUESTIONS テンプレートを返す
- `resolve_source "docs/translation/mapping.md"` が TRANSLATION-MAPPING テンプレートを返す
- docs/decisions/ ディレクトリが scaffold 時に作成される
**Deliverable:** [ ] scaffold 導線が機能する

**Phase 3 検証チェックポイント:**
```bash
# Agent 構造チェック（手動）
grep 'description: "Trigger:' .claude/agents/translation-specialist.md && echo "PASS: CSO" || echo "FAIL"
grep 'do not claim completion without' .claude/agents/translation-specialist.md && echo "PASS: guard" || echo "FAIL"
grep 'maxTurns:' .claude/agents/translation-specialist.md && echo "PASS: turns" || echo "FAIL"

# Skill 構造チェック
grep 'name:' .claude/skills/translation-mapping/SKILL.md && echo "PASS" || echo "FAIL"

# Hook テスト（dry run: context.md が存在するので allow されるはず）
echo '{"tool_name":"Edit","tool_input":{"file_path":"docs/requirements/PRD.md","old_string":"a","new_string":"b"}}' | bash hooks/check-client-info.sh
# → {} が返ること

# hooks.template.json の JSON 妥当性
python3 -m json.tool templates/hooks.template.json > /dev/null && echo "PASS" || echo "FAIL"

# setup.sh の resolve_source テスト
source bin/setup.sh --help 2>/dev/null  # help で即終了
# （関数単体テストは bash -c で実施）
```

---

### Phase 4: Integration（state-machine, client-workflow, next, handover, session-start）

既存のルール・スキル・コマンド・テンプレートを新機能と統合する。

#### Task 10: state-machine.md 更新

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `.claude/rules/state-machine.md`
**意図:** Client モードの目的（purpose statement）を追加する。
**詳細:**
- `In \`Client\`, load the \`client-workflow\` skill.` の直前に以下を追加:
  ```markdown
  Client mode purpose: structure client information, translate client
  language into functional specs and implementation hints, and produce
  a verified handover package for Dev mode.
  ```
- 既存の example (`examples/minimal-project/.claude/rules/state-machine.md`) にも同じ文を追加（Task 16 で実施）

**受入条件:**
- purpose statement が state-machine.md に存在
- 既存の phase/gate/iteration ルールが変更されていない
**Deliverable:** [ ] purpose statement が追加され、既存ルール無変更

#### Task 11: client-workflow SKILL.md 更新

**blockedBy:** Task 1, Task 7 | **モデル:** `sonnet`
**ファイル:** `.claude/skills/client-workflow/SKILL.md`
**意図:** translation artifact 要件と新ディレクトリ参照を追加する。
**詳細:**

**(a) フェーズ進行表の `handover` 行に追記**
- 産出物列に `docs/translation/mapping.md` を追加
- 完了条件列に `translation mapping が作成済みであること` を追加

**(b) 新セクション「## Translation Artifact」を追加**
- 位置: `## 運用ルール` の直前
- 内容:
  ```markdown
  ## Translation Artifact

  handover フェーズに入る前に、`docs/translation/mapping.md` を作成すること。
  mapping.md はクライアント用語 → 機能仕様 → 実装ヒントの 3 層変換表。

  - テンプレート: `templates/TRANSLATION-MAPPING.template.md`
  - 支援 Agent: `translation-specialist`（mapping 作成・更新を委任可能）
  - 支援 Skill: `translation-mapping`（手順ガイド）
  - Gate 契約: `client_ready_for_dev` 承認時に mapping.md の存在がチェックされる

  ### 関連ディレクトリ

  - `docs/client/context.md` — クライアント基本情報（onboard で作成）
  - `docs/client/glossary.md` — 用語集（discovery で作成）
  - `docs/client/open-questions.md` — 未解決事項（随時更新）
  - `docs/translation/mapping.md` — 3 層マッピング（handover 前に作成）
  - `docs/decisions/` — 意思決定ログ（随時作成）
  ```

**(c) current_refs の更新セクションに追記**
- `handover` の記述に `current_refs.translation` の更新指示を追加:
  ```
  - `handover` で `docs/translation/mapping.md` を作成したら、`current_refs.translation` に設定する。
  ```

**受入条件:**
- handover 行の産出物に mapping.md が含まれる
- Translation Artifact セクションが存在
- current_refs.translation の更新指示がある
**Deliverable:** [ ] client-workflow が translation を統合

#### Task 12: next.md 更新

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `.claude/commands/next.md`
**意図:** handover → Dev 遷移の案内に mapping.md 要件を追記する。
**詳細:**
- Client mode テーブルの `handover` → `(Dev)` の行:
  - Gate to Approve 列はそのまま `client_ready_for_dev`
  - 行の後に注釈を追加: `handover 前に docs/translation/mapping.md が必要（gate チェックで検証）`
- または Client mode テーブルの下に補足注記として追記

**受入条件:**
- mapping.md への言及が next.md に存在
- 既存の Dev mode テーブルが変更されていない
**Deliverable:** [ ] handover 遷移案内に mapping.md 要件が含まれる

#### Task 13: HANDOVER-TO-DEV.template.md 更新

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `templates/HANDOVER-TO-DEV.template.md`
**意図:** 引き渡しテンプレートの正本ドキュメント一覧に mapping.md を追加する。
**詳細:**
- `## 正本ドキュメント` セクションに以下を追加:
  ```markdown
  - `docs/translation/mapping.md`
  ```
- `## 未解決事項` セクションに以下の参照を追加:
  ```markdown
  - → `docs/client/open-questions.md` 参照
  ```

**受入条件:**
- 正本ドキュメント一覧に mapping.md がある
- exit-check コメントが変更されていない
**Deliverable:** [ ] 引き渡しテンプレートが translation を参照

#### Task 14: session-start.sh 更新

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** `hooks/session-start.sh`
**意図:** Client モード handover フェーズのヒントに translation artifact を言及する。
**詳細:**
- L101 付近の `handover` case に、ヒントテキストを拡張:
  現在: `HINT="skill: client-workflow"`
  変更後: handover フェーズの場合のみ追加ヒントを付与
  ```bash
  handover)
    HINT="skill: client-workflow / mapping.md必須(translation-mapping skill)"
    ;;
  ```
  他の Client フェーズ（onboard|discovery|requirements|scope|acceptance）は変更しない。
  そのためには case 文を分割する必要がある:
  ```bash
  onboard|discovery|requirements|scope|acceptance)
    HINT="skill: client-workflow"
    ;;
  handover)
    HINT="skill: client-workflow / mapping.md必須(translation-mapping skill)"
    ;;
  ```

**受入条件:**
- handover フェーズ時に translation artifact のヒントが表示される
- 他の Client フェーズのヒントが変更されていない
- Dev フェーズのヒントが変更されていない
**Deliverable:** [ ] session-start が handover 時に translation ヒントを表示

**Phase 4 検証チェックポイント:**
```bash
# state-machine.md に purpose statement があること
grep 'Client mode purpose' .claude/rules/state-machine.md && echo "PASS" || echo "FAIL"

# client-workflow SKILL.md に Translation Artifact セクションがあること
grep '## Translation Artifact' .claude/skills/client-workflow/SKILL.md && echo "PASS" || echo "FAIL"

# next.md に mapping.md 言及があること
grep 'mapping.md' .claude/commands/next.md && echo "PASS" || echo "FAIL"

# HANDOVER-TO-DEV に mapping.md があること
grep 'mapping.md' templates/HANDOVER-TO-DEV.template.md && echo "PASS" || echo "FAIL"

# session-start.sh の handover ヒント確認
grep 'mapping.md' hooks/session-start.sh && echo "PASS" || echo "FAIL"
```

---

### Phase 5: Profiles + Example 同期

プロファイルを更新し、example プロジェクトを新ファイルと同期する。

#### Task 15: profiles 更新（full.json, standard.json）

**blockedBy:** Task 1-14 完了 | **モデル:** `sonnet`
**ファイル:** `templates/profiles/full.json`, `templates/profiles/standard.json`

**(a) full.json:**

- `recommended` 配列に以下の実ファイルパスを追加（テンプレートは載せない — setup.sh が間接参照する）:
  - `"docs/client/context.md"`
  - `"docs/client/glossary.md"`
  - `"docs/client/open-questions.md"`
  - `"docs/translation/mapping.md"`
  - `".claude/agents/translation-specialist.md"`
  - `".claude/skills/translation-mapping/SKILL.md"`
- `hooks_include` 配列に `"check-client-info.sh"` を追加

**(b) standard.json:**

- `recommended` 配列に以下の実ファイルパスを追加:
  - `"docs/client/context.md"`
  - `"docs/client/glossary.md"`
  - `"docs/client/open-questions.md"`
  - `"docs/translation/mapping.md"`
  注: standard は Agent を含まないため translation-specialist は追加しない。
  Hook も最小限のため check-client-info.sh は追加しない。

**受入条件:**

- full.json, standard.json が valid JSON
- full.json の hooks_include に check-client-info.sh が含まれる
- full.json の recommended に agent/skill + 実ファイルパスが含まれる
- profile に `templates/*.template.md` が直接含まれていないこと（テンプレートは setup.sh 経由で参照される）
**Deliverable:** [ ] profiles が新ファイルを参照

#### Task 16: example プロジェクト同期

**blockedBy:** Task 1-15 完了 | **モデル:** `sonnet`
**ファイル:** `examples/minimal-project/` 配下の複数ファイル
**意図:** example プロジェクトをフレームワーク本体と同期させ、contract validator を通過させる。
**詳細:**

**(a) 新規ファイルのコピー/作成:**
- `examples/minimal-project/docs/client/context.md` — 実値入り（example プロジェクト用）
- `examples/minimal-project/docs/client/glossary.md` — 実値入り
- `examples/minimal-project/docs/client/open-questions.md` — 実値入り
- `examples/minimal-project/docs/translation/mapping.md` — 実値入り
- `examples/minimal-project/docs/decisions/.gitkeep`
- `examples/minimal-project/.claude/agents/translation-specialist.md` — フレームワーク本体からコピー
- `examples/minimal-project/.claude/skills/translation-mapping/SKILL.md` — フレームワーク本体からコピー
- `examples/minimal-project/hooks/check-client-info.sh` — フレームワーク本体からコピー

**(b) 既存ファイルの更新:**
- `examples/minimal-project/.claude/rules/state-machine.md` — purpose statement 追加（Task 10 と同内容）
- `examples/minimal-project/.claude/skills/client-workflow/SKILL.md` — Translation Artifact セクション追加（Task 11 と同内容）
- `examples/minimal-project/.claude/commands/next.md` — mapping.md 言及追加（Task 12 と同内容）
- `examples/minimal-project/hooks/session-start.sh` — handover ヒント更新（Task 14 と同内容）
- `examples/minimal-project/.claude/settings.json` — check-client-info.sh の Hook 登録追加
- `examples/minimal-project/docs/STATUS.md` — current_refs.translation: null 追加（client_context は optional なので追加しない、または追加する場合は実値入り）

**(c) プレースホルダ回避:**
- example 内の docs/client/* と docs/translation/* はテンプレートプレースホルダ (`<記入>` 等) を含まないこと
- PLACEHOLDER_ALLOWLIST への追加は原則不要

**受入条件:**
- REQUIRED_EXAMPLE_FILES の全ファイルが存在
- REQUIRED_EXAMPLE_SKILL_DIRS に translation-mapping が存在
- example の settings.json に check-client-info.sh が登録
- example の STATUS.md が check_status.py を PASS
- プレースホルダが example に含まれない
**Deliverable:** [ ] example プロジェクトが contract validator を通過

**Phase 5 検証チェックポイント:**
```bash
# profiles の JSON 妥当性
python3 -m json.tool templates/profiles/full.json > /dev/null && echo "PASS: full.json" || echo "FAIL"
python3 -m json.tool templates/profiles/standard.json > /dev/null && echo "PASS: standard.json" || echo "FAIL"

# example ファイル存在確認
ls examples/minimal-project/docs/client/context.md \
   examples/minimal-project/docs/translation/mapping.md \
   examples/minimal-project/.claude/agents/translation-specialist.md \
   examples/minimal-project/.claude/skills/translation-mapping/SKILL.md \
   examples/minimal-project/hooks/check-client-info.sh && echo "PASS" || echo "FAIL"

# example STATUS.md 検証
python3 scripts/check_status.py --root examples/minimal-project

# example プレースホルダ検査
python3 scripts/check_framework_contract.py 2>&1 | grep "placeholder" && echo "FAIL" || echo "PASS: no placeholders"
```

---

### Phase 6: Validation + Version Bump

全ファイルの最終検証とバージョンバンプ。

#### Task 17: 最終バリデーション

**blockedBy:** Task 1-16 完了 | **モデル:** `opus`
**ファイル:** なし（検証のみ）
**意図:** 全ファイルが整合し、フレームワーク契約を満たすことを確認する。
**詳細:**

```bash
# 1. check_status.py（フレームワーク本体）
python3 scripts/check_status.py --root .

# 2. check_status.py（example プロジェクト）
python3 scripts/check_status.py --root examples/minimal-project

# 3. check_framework_contract.py（全体契約検証）
# 注: この時点では FRAMEWORK_VERSION が 0.7.3 のままなので
# STATUS.template.md との version sync チェックは PASS する（両方 0.7.3）
python3 scripts/check_framework_contract.py

# 4. hooks.template.json の JSON 妥当性 + Hook 登録網羅チェック
python3 -m json.tool templates/hooks.template.json > /dev/null

# 5. profile の JSON 妥当性
python3 -m json.tool templates/profiles/full.json > /dev/null
python3 -m json.tool templates/profiles/standard.json > /dev/null

# 6. pre_approve_gate テスト
python3 scripts/check_status.py --pre-approve-gate client_ready_for_dev --root .

# 7. setup.sh scaffold テスト（dry run: 一時ディレクトリに scaffold）
TMPDIR=$(mktemp -d)
bash bin/setup.sh --profile=full --target="$TMPDIR"
ls "$TMPDIR/docs/client/" "$TMPDIR/docs/translation/" "$TMPDIR/docs/decisions/"
rm -rf "$TMPDIR"
```

**受入条件:**
- 上記 7 チェックがすべて PASS
- FAIL が 1 つでもあれば修正して再検証
**Deliverable:** [ ] 全バリデーション PASS

#### Task 18: バージョンバンプ

**blockedBy:** Task 17 PASS | **モデル:** `sonnet`
**ファイル:** `scripts/check_framework_contract.py` L16, `templates/STATUS.template.md` L3, `docs/STATUS.md` L3, `examples/minimal-project/docs/STATUS.md` L3
**意図:** 全ファイルが検証を通過した後に FRAMEWORK_VERSION を 0.7.3 → 0.8.0 に更新する。
**詳細:**

**(a) check_framework_contract.py**
- L16: `FRAMEWORK_VERSION = "0.7.3"` → `FRAMEWORK_VERSION = "0.8.0"`

**(b) templates/STATUS.template.md**
- L3: `framework_version: "0.7.3"` → `framework_version: "0.8.0"`

**(c) docs/STATUS.md**
- L3: `framework_version: "0.7.3"` → `framework_version: "0.8.0"`

**(d) examples/minimal-project/docs/STATUS.md**
- `framework_version: "0.7.3"` → `framework_version: "0.8.0"`

**受入条件:**
- 4 ファイル全てで version が "0.8.0"
- 最終バリデーション再実行が PASS:
  ```bash
  python3 scripts/check_framework_contract.py
  python3 scripts/check_status.py --root .
  python3 scripts/check_status.py --root examples/minimal-project
  ```
**Deliverable:** [ ] FRAMEWORK_VERSION が 0.8.0 に統一

**Phase 6 検証チェックポイント:**
```bash
# 最終検証（バージョンバンプ後）
python3 scripts/check_framework_contract.py && echo "PASS: contract" || echo "FAIL"
python3 scripts/check_status.py --root . && echo "PASS: status" || echo "FAIL"
python3 scripts/check_status.py --root examples/minimal-project && echo "PASS: example status" || echo "FAIL"

# version 一致確認
grep 'FRAMEWORK_VERSION = "0.8.0"' scripts/check_framework_contract.py && echo "PASS" || echo "FAIL"
grep 'framework_version: "0.8.0"' templates/STATUS.template.md && echo "PASS" || echo "FAIL"
grep 'framework_version: "0.8.0"' docs/STATUS.md && echo "PASS" || echo "FAIL"
grep 'framework_version: "0.8.0"' examples/minimal-project/docs/STATUS.md && echo "PASS" || echo "FAIL"
```

---

## リスクと緩和策

| # | リスク | 影響 | 緩和策 | 対応フェーズ |
|---|--------|------|--------|-------------|
| R1 | check-client-info.sh が厳しすぎて開発体験悪化 | 中 | minimal profile では hook 無効化可能。Dev モード時はスキップロジック実装 | Phase 3 (Task 8) |
| R2 | mapping.md の粒度が定まらない | 低 | テンプレートで最小構造を提供。実運用で調整し Phase B で再検討 | Phase 1 (Task 1) |
| R3 | contract validator の REQUIRED 追加漏れ | 低 | Task 5 のチェックリストで全 11 新規ファイルのパスを網羅。Phase 6 で最終検証 | Phase 2 (Task 5) + Phase 6 |
| R4 | 既存テストとの整合性（example 同期漏れ） | 低 | Phase 5 で example を網羅的に同期。contract validator が不整合を検出 | Phase 5 (Task 16) |
| R5 | check_status.py schema drift（OPTIONAL_TOP_LEVEL_KEYS と EXPECTED_CURRENT_REF_KEYS の同時更新漏れ） | 高 | Task 4 で両方を同一タスクで更新。Phase 2 検証で即確認 | Phase 2 (Task 4) |
| R6 | setup.sh scaffold 漏れ（resolve_source 不足） | 中 | Task 9 で 4 マッピング追加 + profile パス追加を同一フェーズで実施。Phase 6 scaffold テストで検証 | Phase 3 (Task 9) + Phase 6 |
| R7 | STATUS.template.md と STATUS.md の乖離 | 中 | Phase 1 で template 更新後、Phase 6 で両方の version を同時バンプ。中間では version 差分が発生しないよう注意 | Phase 1 (Task 3) + Phase 6 (Task 18) |
| R8 | translation-specialist Agent の allowedTools 制限不足 | 低 | Bash を除外し Read/Write/Grep/Glob に限定。コード変更権限を排除 | Phase 3 (Task 6) |
| R9 | hooks.template.json 更新後の JSON parse エラー | 中 | Phase 3 検証で `python3 -m json.tool` を実行。Phase 6 でも再検証 | Phase 3 (Task 8) + Phase 6 |

## トレーサビリティ（設計判断 → Task）

| 設計判断（brainstorm） | 対応 Task | 検証方法 |
|------------------------|-----------|----------|
| translation は artifact-first | Task 1, 11, 13 | mapping.md テンプレート存在 + client-workflow + handover に言及 |
| Agent は 1 体（translation-specialist） | Task 6 | Agent ファイル存在 + contract validator |
| Hook は 1 つ（check-client-info.sh） | Task 8 | Hook ファイル存在 + hooks.template.json 登録 |
| STATUS.md は軽量拡張（client_context 2 フィールド） | Task 3, 4 | template + validator が整合 |
| Phase 追加なし | Task 10 | state-machine.md に新 phase がないこと |
| 新プロファイル延期 | Task 15 | full/standard のみ更新。client-heavy/solo-consultant は作成しない |
| mapping.md gate 必須化 | Task 4(e) | pre_approve_gate テスト |
| current_refs.translation 追加 | Task 3, 4(b) | template + validator が整合 |
| setup.sh scaffold 導線 | Task 9 | resolve_source テスト + scaffold dry run |
| Client mode purpose | Task 10 | state-machine.md に文言存在 |

## 自己レビュー

- [x] 仕様カバレッジ: brainstorm レコードの確定スコープ 23 ファイル全てにタスクが割り当てられている
- [x] 曖昧さ検出: 各タスクの変更内容が行レベルで特定可能
- [x] 型の整合性: OPTIONAL_TOP_LEVEL_KEYS, EXPECTED_CURRENT_REF_KEYS, REQUIRED_* リストが同一タスクで更新される
- [x] 境界整合性: Boundary Map の Consumes が対応する Produces に一致
- [x] リスク: brainstorm で特定された 7 リスク全てに緩和策が対応

## 完了条件

- [ ] 全 18 タスク完了
- [ ] `python3 scripts/check_framework_contract.py` PASS
- [ ] `python3 scripts/check_status.py --root .` PASS
- [ ] `python3 scripts/check_status.py --root examples/minimal-project` PASS
- [ ] `python3 scripts/check_status.py --pre-approve-gate client_ready_for_dev --root .` PASS（mapping.md 存在時）
- [ ] `bash bin/setup.sh --profile=full --target=<tmp>` で新ファイルが scaffold される
- [ ] FRAMEWORK_VERSION が全 4 箇所で "0.8.0"
- [ ] docs/STATUS.md の phase を implement に更新、plan gate を approved に更新、current_refs.plan に本計画のパスを設定
<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->
