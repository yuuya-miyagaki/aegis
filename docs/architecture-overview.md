# Aegis — アーキテクチャ概観

> 作成日: 2026-04-17
> バージョン: v0.7.3
> 対象: フレームワーク全体の構造・設計思想・構成要素の解説

---

## 1. フレームワーク概要

Aegis は、Claude Code ネイティブの運用フレームワークである。
Ultra Framework v7 の設計原則（明示的フェーズ制御、ハードゲート、エビデンスベース完了）を
Claude Code 固有の機能（Skills, Agents, Commands, Hooks）に最適化して再構成したもの。

### 設計原則

| 原則 | 理由 |
|------|------|
| **薄い CLAUDE.md**（<700語） | 常駐コンテキストを小さく保ち、フェーズ固有のスキルに予算を残す |
| **STATUS.md による状態管理** | プレーンテキストで diff・grep・手動編集が可能。セッション再開時の状態復元に使う |
| **Pull-based スキル** | 全スキル同時読込はノイズ。現フェーズに必要なものだけ読み込む |
| **Hard Gates + Hook PaC** | ルールの文言だけでは飛ばされる。フックがランタイムでツール呼び出しを制御する |
| **Claude Code 専用** | クロスハーネス対応の抽象化を排除し、ネイティブ機能を最大活用する |

---

## 2. ディレクトリ構成

```text
aegis/
├── CLAUDE.md                         # 制御カーネル（~370語）
├── README.md                         # 利用ガイド・マイグレーション情報
├── .gitignore                        # ランタイム成果物の除外
│
├── .claude/                          # Claude Code ネイティブ構成
│   ├── agents/                       # 10 サブエージェント定義
│   │   ├── implementer.md
│   │   ├── planner.md
│   │   ├── reviewer.md               # skills: [review]
│   │   ├── reviewer-testing.md
│   │   ├── reviewer-performance.md
│   │   ├── reviewer-maintainability.md
│   │   ├── qa.md                     # skills: [qa-verification]
│   │   ├── qa-browser.md
│   │   ├── security.md               # skills: [security-review]
│   │   └── ui.md
│   ├── commands/                     # 7 スラッシュコマンド
│   │   ├── status.md                 # /status
│   │   ├── gate.md                   # /gate
│   │   ├── recover.md                # /recover
│   │   ├── validate.md               # /validate
│   │   ├── next.md                   # /next
│   │   ├── retro.md                  # /retro
│   │   └── tutorial.md               # /tutorial
│   ├── rules/                        # 常時読込ルール
│   │   ├── state-machine.md          # フェーズ遷移定義
│   │   └── routing.md                # エージェントルーティング
│   └── skills/                       # 12 Pull-based スキル
│       ├── brainstorming/SKILL.md
│       ├── bug-diagnosis/SKILL.md
│       ├── tdd/SKILL.md
│       ├── subagent-dev/SKILL.md
│       ├── deploy/
│       │   ├── SKILL.md
│       │   └── platforms.md
│       ├── client-workflow/SKILL.md
│       ├── session-recovery/SKILL.md
│       ├── ship-and-docs/SKILL.md
│       ├── review/SKILL.md
│       ├── security-review/SKILL.md
│       ├── qa-verification/SKILL.md
│       └── docs-sync/SKILL.md
│
├── hooks/                            # ランタイムフック（PaC）
│   ├── session-start.sh              # SessionStart: コンテキスト注入
│   ├── check-gate.sh                 # PreToolUse(Edit/Write): ゲートチェック
│   ├── check-tdd.sh                  # PreToolUse(Edit/Write): TDD チェック
│   ├── check-control-plane.sh        # PreToolUse(Bash): 制御面保護
│   ├── check-destructive.sh          # PreToolUse(Bash): 破壊コマンド検出
│   ├── post-bash.sh                  # PostToolUse(Bash): テスト失敗→ReAct
│   ├── post-status-audit.sh          # PostToolUse(Edit/Write): ゲート改竄検出
│   ├── pre-compact.sh                # PreCompact: 状態未保存時ブロック
│   └── lib/
│       └── extract-input.sh          # 共有ユーティリティ
│
├── scripts/                          # バリデータ・ユーティリティ
│   ├── check_framework_contract.py   # フレームワーク契約検証
│   ├── check_status.py               # STATUS.md YAML検証
│   ├── check_reference_drift.py      # 参照名ドリフト検出
│   ├── eval_scaffold_smoke.py        # scaffold スモークテスト
│   ├── eval_scenario.py              # シナリオ評価
│   ├── run_eval.py                   # 統合評価ランナー
│   ├── update-gate.sh                # ゲート更新スクリプト
│   ├── learnings_search.py           # LEARNINGS 検索
│   ├── retro_report.py               # レトロスペクティブ生成
│   └── status_doctor.py              # STATUS 修復ツール
│
├── templates/                        # プロジェクト初期化テンプレート
│   ├── CLAUDE.template.md            # CLAUDE.md テンプレート
│   ├── STATUS.template.md            # STATUS.md テンプレート
│   ├── LEARNINGS.template.md         # LEARNINGS.md テンプレート
│   ├── hooks.template.json           # settings.local.json 生成元
│   ├── profiles/                     # セットアッププロファイル
│   │   ├── minimal.json              # 最小構成（4ファイル）
│   │   ├── standard.json             # 推奨構成（14必須+7推奨）
│   │   └── full.json                 # 全構成（エージェント含む）
│   └── *.template.md                 # 各種ドキュメントテンプレート（17種）
│
├── extensions/                       # オプショナル拡張（手動 opt-in）
│   ├── CONVENTIONS.md                # 拡張規約
│   ├── cost-tracking/                # コスト追跡テンプレート
│   ├── mcp/                          # MCP サーバーカタログ（5種）
│   │   ├── README.md
│   │   ├── playwright.json
│   │   ├── github.json
│   │   ├── context7.json
│   │   ├── vercel.json
│   │   └── figma.json
│   └── qa-browser/                   # ブラウザ QA ワークフロー
│       ├── README.md
│       └── WORKFLOW.md
│
├── examples/minimal-project/         # 自己完結サンプルプロジェクト
│   ├── CLAUDE.md
│   ├── .claude/ (全構造ミラー)
│   ├── docs/ (STATUS, LEARNINGS, 要件, 計画, レポート)
│   ├── hooks/ (全フック)
│   └── scripts/ (check_status, update-gate)
│
├── docs/                             # フレームワーク自身のドキュメント
│   ├── STATUS.md                     # 運用状態
│   ├── LEARNINGS.md                  # 蓄積教訓
│   ├── MIGRATION-FROM-v7.md          # v7 からの移行ガイド
│   ├── evidence-archive.md           # 外部エビデンスアーカイブ
│   ├── plans/                        # 設計計画
│   ├── specs/                        # 仕様・調査レポート
│   ├── reviews/                      # セカンドオピニオン
│   ├── qa-reports/                   # QA/レビュー/セキュリティレポート
│   ├── requirements/                 # 要件定義（プロジェクト用）
│   ├── handover/                     # ハンドオーバー文書
│   ├── skills/                       # スキル関連ドキュメント
│   └── v0*-*.md                      # バージョン別改善レポート
│
└── bin/
    └── setup.sh                      # モジュラーインストーラ
```

---

## 3. 制御カーネル（CLAUDE.md）

CLAUDE.md はフレームワークの中核であり、常時コンテキストに読み込まれる。
約 370 語（上限 700 語）に抑え、以下の役割を担う。

- **Operating Contract**: 運用規約（エビデンスベース完了、3回失敗ルール、pull-based 読込）
- **Session Start**: セッション開始手順（STATUS.md 読取 → 参照読取 → 必要時サブエージェント）
- **State Machine**: モード（Client/Dev）とフェーズの宣言（詳細は `.claude/rules/`）
- **Routing**: サブエージェントルーティング方針（詳細は `.claude/rules/`）
- **Context Budget Policy**: L0〜L3 の4段階文書読込ポリシー
- **Skills**: 12スキルの一覧と pull-based 読込方針
- **Source of Truth**: 情報の正規ソース定義
- **Completion Rule**: 完了条件（成果物存在、ゼロツールコール禁止、STATUS 更新）

---

## 4. ステートマシン

### 4.1 モード

| モード | フェーズ | 用途 |
|--------|---------|------|
| **Client** | onboard → discovery → requirements → scope → acceptance → handover | 上流工程（要件定義〜ハンドオーバー） |
| **Dev** | brainstorm → plan → implement → review → qa → security → deploy → ship → docs | 開発工程（設計〜ドキュメント） |

### 4.2 ハードゲート

モード間の遷移に2つのハードゲートが存在する:

- `client_ready_for_dev`: Client → Dev の遷移に必要
- `dev_ready_for_client`: Dev → Client へのハンドバックに必要

### 4.3 タスクサイズによるフェーズ省略

| タイプ | 必須ゲート | S（1ファイル） | M（2-5） | L（6+） |
|--------|-----------|--------------|---------|--------|
| feature/refactor/framework | review+qa+security+deploy | impl→review→ship | deploy 省略 | 全フェーズ |
| bugfix | review; brainstorm+plan=n/a | 同上 | 同上 | 同上 |
| hotfix | review 推奨; brainstorm+plan=n/a | 同上 | 同上 | 同上 |

### 4.4 イテレーション

`dev_ready_for_client` 後に新タスクを開始すると:
- `brainstorm` にリセット
- Dev ゲートを `pending` にクリア
- `iteration` をインクリメント
- `current_refs.requirements` は維持
- 3件を超える `external_evidence` は `docs/evidence-archive.md` にアーカイブ

---

## 5. サブエージェント

### 5.1 コアエージェント（6）

| エージェント | 役割 | 信頼境界 |
|-------------|------|---------|
| `planner` | 設計・計画作成 | — |
| `implementer` | コード・テスト実装 | skills: [tdd] |
| `reviewer` | フレッシュコンテキストレビュー | readOnly, permissionMode: plan, skills: [review] |
| `qa` | 検証・QAレポート作成 | readOnly, permissionMode: plan, skills: [qa-verification] |
| `security` | セキュリティレビュー | readOnly, permissionMode: plan, skills: [security-review] |
| `ui` | UI/UX 作業 | — |

### 5.2 スペシャリストエージェント（4）

| エージェント | 役割 | 起動条件 |
|-------------|------|---------|
| `reviewer-testing` | テストカバレッジ特化レビュー | diff-scope が大きい場合 |
| `reviewer-performance` | パフォーマンス特化レビュー | 同上 |
| `reviewer-maintainability` | 保守性特化レビュー | 同上 |
| `qa-browser` | ブラウザ QA | qa エージェントから委譲。disallowedTools で Edit/Write/Bash 禁止 |

### 5.3 信頼境界

- `reviewer`, `qa`, `security` は `readOnly: true` + `permissionMode: plan`
- `qa-browser` は `disallowedTools` で書込系ツールを明示的に禁止
- `skills:` frontmatter で preload されるスキルは `disable-model-invocation: true`

---

## 6. スキル

12 の pull-based スキルが `.claude/skills/` に配置されている。
各スキルは `SKILL.md` に frontmatter（`disable-model-invocation: true`）を持ち、
Claude Code がフェーズに応じて自動的に読み込む参照文書として機能する。

| スキル | 対応フェーズ | user-invocable |
|--------|------------|---------------|
| brainstorming | brainstorm | true |
| bug-diagnosis | brainstorm（bugfix/hotfix） | true |
| tdd | implement | true |
| subagent-dev | plan, implement, review | true |
| deploy | deploy | true |
| client-workflow | Client 全フェーズ | true |
| session-recovery | 任意（障害復旧） | true |
| ship-and-docs | ship, docs | true |
| review | review | false |
| security-review | security | false |
| qa-verification | qa | false |
| docs-sync | docs | true |

---

## 7. フック（Policy as Code）

8 つのランタイムフックが Claude Code のツール呼び出しを制御する。
フック設定は `templates/hooks.template.json` に定義され、
`bin/setup.sh` が `settings.local.json` として生成する。

### 7.1 フック一覧

| フック | イベント | マッチャー | 機能 |
|--------|---------|----------|------|
| **session-start.sh** | SessionStart | startup\|clear\|compact | STATUS.md を読取り、モード・フェーズ・ブロッカー・スキルヒント・高信頼度 LEARNINGS をコンテキストに注入。ゲートスナップショット初期化 |
| **check-gate.sh** | PreToolUse | Edit\|Write\|NotebookEdit | plan ゲート未承認時にコード編集をブロック。Client モード中の編集もブロック。framework 以外の task_type で制御ファイル編集をブロック |
| **check-tdd.sh** | PreToolUse | Edit\|Write\|NotebookEdit | テストファイルの変更なしにプロダクションコードを編集しようとすると警告（`ask`） |
| **check-control-plane.sh** | PreToolUse | Bash | STATUS.md, CLAUDE.md, .claude/, hooks/, scripts/ への Bash 操作を非 framework タスク時にブロック。allowlist + 読取専用コマンド例外あり |
| **check-destructive.sh** | PreToolUse | Bash | `rm -r`, `DROP TABLE`, `git push -f`, `git reset --hard` 等の破壊的コマンドを検出して確認要求（`ask`）。ビルド成果物は例外 |
| **post-bash.sh** | PostToolUse | Bash | テストコマンドの失敗を検出し、ReAct アプローチ（Observe→Think→Act）を提案 |
| **post-status-audit.sh** | PostToolUse | Edit\|Write\|NotebookEdit | STATUS.md 編集後にゲート改竄を検出。セッション開始時のスナップショットと比較し、不正な `approved` 遷移をブロック |
| **pre-compact.sh** | PreCompact | — | STATUS.md が 5 分以上未更新かつアクティブフェーズ中の場合、コンテキスト圧縮をブロック（exit code 2） |

### 7.2 フック連携図

```
SessionStart
  └─ session-start.sh → .gate-snapshot 初期化 + コンテキスト注入

PreToolUse(Edit/Write/NotebookEdit)
  ├─ check-gate.sh    → plan ゲート / Client モード / 制御ファイル保護
  └─ check-tdd.sh     → TDD 遵守チェック

PreToolUse(Bash)
  ├─ check-control-plane.sh → 制御面ファイル保護
  └─ check-destructive.sh   → 破壊コマンド警告

PostToolUse(Bash)
  └─ post-bash.sh → テスト失敗時 ReAct ヒント

PostToolUse(Edit/Write/NotebookEdit) [if: *STATUS.md]
  └─ post-status-audit.sh → ゲート改竄検出

PreCompact
  └─ pre-compact.sh → 状態保存チェック
```

---

## 8. スラッシュコマンド

| コマンド | 用途 |
|----------|------|
| `/status` | STATUS.md のフォーマット済みサマリ表示 |
| `/gate` | ゲート一覧表示・承認操作 |
| `/recover` | セッションリカバリ起動 |
| `/validate` | 階層化フレームワーク評価実行 |
| `/next` | 次アクション・フェーズ遷移提案 |
| `/retro` | レトロスペクティブレポート生成 |
| `/tutorial` | フェーズ遷移ウォークスルーガイド |

---

## 9. バリデータ・スクリプト

### 9.1 主要バリデータ

| スクリプト | 用途 |
|-----------|------|
| `check_framework_contract.py` | フレームワーク契約検証（ファイル存在、CLAUDE.md 語数、スキル/エージェント/コマンド/フック整合性、プロファイル検証） |
| `check_status.py` | STATUS.md YAML frontmatter 検証（必須フィールド、ゲート整合性、型チェック） |
| `check_reference_drift.py` | 参照名ドリフト検出（テンプレートと実体の不整合） |
| `run_eval.py` | 統合評価ランナー（Tier 1: 契約、Tier 2: scaffold スモーク、Tier 3: シナリオ） |
| `eval_scaffold_smoke.py` | scaffold 後のプロジェクト整合性テスト |
| `eval_scenario.py` | シナリオベース評価 |

### 9.2 ユーティリティ

| スクリプト | 用途 |
|-----------|------|
| `update-gate.sh` | ゲート値の更新（STATUS.md の sed 置換） |
| `learnings_search.py` | LEARNINGS.md 検索 |
| `retro_report.py` | レトロスペクティブレポート生成 |
| `status_doctor.py` | STATUS.md の自動修復 |

---

## 10. テンプレート

17 のドキュメントテンプレートと 3 つのセットアッププロファイルを提供する。

### 10.1 ドキュメントテンプレート

| テンプレート | 出力先 |
|-------------|-------|
| CLAUDE.template.md | CLAUDE.md |
| STATUS.template.md | docs/STATUS.md |
| LEARNINGS.template.md | docs/LEARNINGS.md |
| PRD.template.md | docs/requirements/PRD.md |
| NFR.template.md | docs/requirements/NFR.md |
| SCOPE.template.md | docs/requirements/SCOPE.md |
| ACCEPTANCE.template.md | docs/requirements/ACCEPTANCE.md |
| BRAINSTORM-RECORD.template.md | docs/specs/*-brainstorm-record.md |
| SPEC.template.md | docs/specs/*-design.md |
| PLAN.template.md | docs/plans/*-plan.md |
| REVIEW.template.md | docs/qa-reports/*-review.md |
| QA-REPORT.template.md | docs/qa-reports/*-qa.md |
| SECURITY-REVIEW.template.md | docs/qa-reports/*-security.md |
| VERIFICATION.template.md | docs/qa-reports/*-verification.md |
| DEPLOY-CHECKLIST.template.md | docs/qa-reports/*-deploy-checklist.md |
| HANDOVER-TO-DEV.template.md | docs/handover/TO-DEV.md |
| HANDOVER-TO-CLIENT.template.md | docs/handover/TO-CLIENT.md |
| SECOND-OPINION.template.md | docs/second-opinion.md |

### 10.2 セットアッププロファイル

| プロファイル | 必須 | 推奨 | フック |
|------------|------|------|-------|
| minimal | 4 ファイル | — | session-start のみ |
| standard | 14 ファイル | 7 ファイル | session-start, check-gate, post-status-audit, pre-compact |
| full | 18 ファイル | 22 ファイル（全スキル+全エージェント） | 全 8 フック |

---

## 11. 拡張（Extensions）

コア契約外のオプショナルアドオン。`setup.sh` には含まれず、手動コピーで opt-in する。

### 11.1 拡張規約（CONVENTIONS.md）

- core は extension に依存してはならない（依存方向: extension → core）
- 拡張固有ファイルは `check_framework_contract.py` に登録しない
- core の安定契約（STATUS.md, ゲート機構, Hook PaC, バリデータ）には依存可能

### 11.2 提供拡張

| 拡張 | 内容 |
|------|------|
| **qa-browser/** | Playwright MCP を使ったブラウザ QA ワークフロー（4ステップ: Snapshot→Interact→Verify→Evidence） |
| **cost-tracking/** | セッションコスト追跡テンプレート |
| **mcp/** | MCP サーバー設定カタログ（5サーバー: Playwright, GitHub, Context7, Vercel, Figma） |

---

## 12. サンプルプロジェクト

`examples/minimal-project/` は自己完結したサンプルプロジェクトで、
フレームワークの全構成要素（エージェント、スキル、コマンド、ルール、フック、スクリプト）を含む。

実際のプロジェクト利用例として、「検索機能の実装」シナリオのドキュメント一式
（要件定義、設計、計画、レビュー、QA、デプロイチェックリスト）を含んでおり、
Client → Dev の全フローを追跡できる。

---

## 13. コンテキスト予算ポリシー

文書読込は4段階のレベルで制御される:

| レベル | 内容 | 読込タイミング |
|--------|------|--------------|
| L0 | CLAUDE.md + STATUS.md | 常時（always-on） |
| L1 | フェーズ参照（current_refs） | フェーズ開始時 |
| L2 | タスクファイル | 作業中 |
| L3 | オンデマンド | 依存出現時 |

原則: リポジトリファイルをチャット履歴より優先。最大3文書同時読込。
フェーズ遷移時にサマリ。一時停止前に STATUS.md 更新。

---

## 14. セットアップフロー

```bash
# 自動セットアップ（推奨）
bin/setup.sh --profile=standard --target=<your-project-dir>

# 検証
python3 scripts/check_framework_contract.py --profile=standard --root <your-project-dir>
```

`setup.sh` は以下を行う:

1. プロファイル JSON（`templates/profiles/*.json`）を読取
2. `required` ファイルをコピー（テンプレート → 実ファイルのマッピングあり）
3. `recommended` ファイルをコピー
4. `hooks_include` に基づきフックスクリプトをコピー
5. `hooks.template.json` からフィルタリングして `settings.local.json` を生成

---

## 15. ファイル数サマリ

| カテゴリ | ファイル数 |
|----------|----------|
| 制御カーネル（CLAUDE.md） | 1 |
| ルール（.claude/rules/） | 2 |
| エージェント（.claude/agents/） | 10 |
| スキル（.claude/skills/） | 13（SKILL.md x12 + platforms.md x1） |
| コマンド（.claude/commands/） | 7 |
| フック（hooks/） | 9（メイン8 + lib/extract-input.sh） |
| スクリプト（scripts/） | 10 |
| テンプレート（templates/） | 21（.md x17 + .json x4） |
| 拡張（extensions/） | 10 |
| サンプル（examples/） | 43 |
| ドキュメント（docs/） | 18 |
| その他（README, .gitignore, bin/） | 3 |
| **合計（.git 除く）** | **約 147** |

---

## 16. バージョン履歴

| バージョン | 主な変更 |
|-----------|---------|
| v0.5.0 | 初期 Claude Code ネイティブ移行 |
| v0.6.0 | Skills → `.claude/skills/` 移行、Commands 導入、信頼境界ハードニング |
| v0.7.0 | STATUS.md スキーマ拡張（failure_tracking, task_size_rationale）、アーカイブ制限 |
| v0.7.1 | PreCompact フック追加、qa-browser エージェント分離、auto-memory ポリシー緩和 |
| v0.7.2 | check-control-plane.sh 新規、NotebookEdit マッチャー追加、/validate 分離 |
| v0.7.3 | qa-verification スキル新設、エージェント skills preload 統一、MCP カタログ追加 |
