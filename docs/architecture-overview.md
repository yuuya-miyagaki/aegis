# Aegis — アーキテクチャ概観

> 作成日: 2026-04-17（最終更新: 2026-06-10）
> バージョン: v1.4.0
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

設計の土台は「**保証＝決定論的強制（hooks）／手順＝モデル委譲（skills）／揮発値＝隔離**」の3層分解
（v1.0.0 future-proof 再アーキ）。公開契約は運用契約のみで、SemVer に従う。

---

## 2. ディレクトリ構成

```text
aegis/
├── CLAUDE.md                         # 制御カーネル（~370語）
├── README.md                         # 利用ガイド・マイグレーション情報
├── .gitignore                        # ランタイム成果物の除外
│
├── .claude/                          # Claude Code ネイティブ構成
│   ├── agents/                       # 12 サブエージェント定義
│   │   ├── planner.md
│   │   ├── implementer.md
│   │   ├── reviewer.md               # skills: [aegis-review-gate]
│   │   ├── reviewer-testing.md
│   │   ├── reviewer-performance.md
│   │   ├── reviewer-maintainability.md
│   │   ├── qa.md                     # skills: [qa-verification]
│   │   ├── qa-browser.md
│   │   ├── security.md               # skills: [aegis-security-gate]
│   │   ├── ui.md
│   │   ├── translation-specialist.md
│   │   └── integration-specialist.md
│   ├── commands/                     # 8 スラッシュコマンド
│   │   ├── status.md                 # /status
│   │   ├── gate.md                   # /gate
│   │   ├── judge.md                  # /judge
│   │   ├── recover.md                # /recover
│   │   ├── validate.md               # /validate
│   │   ├── next.md                   # /next
│   │   ├── retro.md                  # /retro
│   │   └── tutorial.md               # /tutorial
│   ├── rules/                        # 常時読込ルール
│   │   ├── state-machine.md          # フェーズ遷移定義
│   │   └── routing.md                # エージェントルーティング
│   └── skills/                       # 18 Pull-based スキル
│       ├── aegis-brainstorm/SKILL.md
│       ├── bug-diagnosis/SKILL.md
│       ├── tdd/SKILL.md
│       ├── subagent-dev/SKILL.md
│       ├── deploy/
│       │   ├── SKILL.md
│       │   └── platforms.md
│       ├── client-workflow/SKILL.md
│       ├── session-recovery/SKILL.md
│       ├── ship-and-docs/SKILL.md
│       ├── aegis-review-gate/SKILL.md
│       ├── aegis-security-gate/SKILL.md
│       ├── qa-verification/SKILL.md
│       ├── docs-sync/SKILL.md
│       ├── translation-mapping/SKILL.md
│       ├── integration-assist/SKILL.md
│       ├── browser-assist/SKILL.md
│       ├── user-manual/SKILL.md
│       ├── maintenance/SKILL.md
│       └── uat/SKILL.md
│
├── hooks/                            # ランタイムフック（PaC）
│   ├── session-start.sh              # SessionStart: コンテキスト注入
│   ├── check-gate.sh                 # PreToolUse(Edit/Write): ゲートチェック
│   ├── check-tdd.sh                  # PreToolUse(Edit/Write): TDD チェック（full のみ）
│   ├── check-client-info.sh          # PreToolUse(Edit/Write): Client 情報ガード
│   ├── check-control-plane.sh        # PreToolUse(Bash): 制御面保護
│   ├── check-destructive.sh          # PreToolUse(Bash): 破壊コマンド検出
│   ├── check-secrets.sh              # PreToolUse(Bash): .env/鍵の commit 阻止
│   ├── check-deploy-gate.sh          # PreToolUse(Bash): deploy ゲート
│   ├── check-deploy-mcp-gate.sh      # PreToolUse(mcp deploy): deploy ゲート
│   ├── check-skill-gate.sh           # PreToolUse(Skill): 制御層スキル確認
│   ├── check-cron-gate.sh            # PreToolUse(CronCreate): スケジュール payload 確認
│   ├── post-bash.sh                  # PostToolUseFailure(Bash): テスト失敗→ReAct
│   ├── post-status-audit.sh          # PostToolUse(Edit/Write): ゲート改竄検出
│   ├── pre-compact.sh                # PreCompact: 状態未保存時ブロック
│   ├── check-task-created.sh         # TaskCreated: gate ブロック時 hard stop
│   ├── check-task-completed.sh       # TaskCompleted: evidence 差し戻し
│   └── lib/
│       ├── emit.sh                   # hook 出力スキーマ単一ソース（pure-bash・fail-closed）
│       ├── patterns.sh               # 破壊コマンドパターンデータ
│       └── extract-input.sh          # 共有入力抽出ユーティリティ
│
├── scripts/                          # バリデータ・ユーティリティ
│   ├── check_framework_contract.py   # フレームワーク契約検証
│   ├── check_status.py               # STATUS.md YAML検証
│   ├── check_reference_drift.py      # 参照名ドリフト検出（mirror-identity 含む）
│   ├── lint_names.py                 # 名前クロスリファレンス lint
│   ├── eval_scaffold_smoke.py        # scaffold スモーク（hook/script を実発火検証）
│   ├── eval_scenario.py              # シナリオ評価
│   ├── run_eval.py                   # 統合評価ランナー
│   ├── update-gate.sh                # ゲート更新スクリプト
│   ├── run-test-strength-drill.py    # テスト強度ドリル（B1・qa 承認時に実走）
│   ├── build-judge-card.py           # judge カードビルダー（B2・承認時に実走）
│   ├── record-test-result.py         # テスト結果記録（judge が指紋照合で read）
│   ├── learnings_search.py           # LEARNINGS 検索
│   ├── retro_report.py               # レトロスペクティブ生成
│   └── status_doctor.py              # STATUS 運用健全性チェック
│
├── templates/                        # プロジェクト初期化テンプレート
│   ├── CLAUDE.template.md            # CLAUDE.md テンプレート
│   ├── STATUS.template.md            # STATUS.md テンプレート
│   ├── LEARNINGS.template.md         # LEARNINGS.md テンプレート
│   ├── hooks.template.json           # settings.local.json 生成元
│   ├── profiles/                     # セットアッププロファイル
│   │   ├── minimal.json              # 最小構成
│   │   ├── standard.json             # 推奨構成
│   │   └── full.json                 # 全構成（エージェント・全スキル・全フック含む）
│   └── *.template.md                 # 各種ドキュメントテンプレート（計26種）
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
├── examples/minimal-project/         # 自己完結サンプルプロジェクト（本体とミラー）
│   ├── CLAUDE.md
│   ├── .claude/ (全構造ミラー)
│   ├── docs/ (STATUS, LEARNINGS, 要件, 計画, レポート)
│   ├── hooks/ (全フック + lib)
│   └── scripts/ (check_status, update-gate, status_doctor, build-judge-card 等)
│
├── docs/                             # フレームワーク自身のドキュメント
│   ├── STATUS.md                     # 運用状態
│   ├── LEARNINGS.md                  # 蓄積教訓
│   ├── MIGRATION-FROM-v7.md          # v7 からの移行ガイド
│   ├── evidence-archive.md           # 外部エビデンスアーカイブ
│   ├── plans/                        # 設計計画
│   ├── specs/                        # 仕様・調査レポート
│   ├── qa-reports/                   # QA/レビュー/セキュリティレポート
│   ├── requirements/                 # 要件定義（プロジェクト用）
│   └── handover/                     # ハンドオーバー文書
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
- **Model Policy**: 役割ティアごとの model/effort ピン（quality=opus / cost=sonnet / default=inherit）
- **Context Budget Policy**: L0〜L3 の4段階文書読込ポリシー
- **Skills**: 18スキルの一覧と pull-based 読込方針
- **Source of Truth**: 情報の正規ソース定義
- **Completion Rule**: 完了条件（成果物存在、ゼロツールコール禁止、STATUS 更新、ゲート ref 整合）

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
- `dev_ready_for_client`: Dev → Client へのハンドバックに必要（ACCEPTANCE があれば UAT-RESULTS の存在を要求）

**qa ゲートのテスト強度ドリル（B1）**: qa ゲートを承認するとき、`pre_approve_gate`
が `scripts/run-test-strength-drill.py` を**承認の瞬間に実走**する。変更コードに
仕込んだ mutant をテストが全て捕まえない限り承認を拒否する（verdict はその場で
計算＝偽造・staleness 不能）。入力は `docs/qa-reports/test-strength.drill`、機械生成
レポートは `docs/qa-reports/test-strength.md`（`current_refs.qa`）。テスト対象コードが
無いタスクは `.drill` にスキップ宣言（`{"skip": true, "reason": "..."}`）を書く。

**judge カード（B2）**: review/qa/security/deploy を承認するとき、`pre_approve_gate`
が `scripts/build-judge-card.py` を**承認の瞬間に実走**し、tri-state（🟢/🔴/🟡）の
判定カードを生成する。ティア1の機械事実（変更行のスタブ scan・secret scan・指紋検証
済みテスト結果・B1 verdict）が記録済み `claims:` と決定論的に矛盾すれば🔴ブロック。
第2意見（self-attested）の相違・claims/証拠の不足・依存監査は🟡（`update-gate.sh
<gate> approve --ack "理由"` で承認可、理由はカードに記録）。テスト結果は純 read を
保つため別スクリプト `scripts/record-test-result.py` が
`docs/qa-reports/test-result.json`（status＋コード指紋）に記録する。`/judge` で同じ
カードを読み取り専用でプレビューできる。

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

合計 12 のサブエージェント。`model`/`effort` は役割ティアでピン留めされる
（quality=opus / cost=sonnet / default=inherit。`haiku` は不使用。`check_framework_contract.py` が検証）。

### 5.1 コアエージェント（6）

| エージェント | 役割 | 信頼境界 |
|-------------|------|---------|
| `planner` | 設計・計画作成 | readOnly, opus/max |
| `implementer` | コード・テスト実装 | skills: [tdd], inherit |
| `reviewer` | フレッシュコンテキストレビュー | readOnly, permissionMode: plan, skills: [aegis-review-gate], opus/xhigh |
| `qa` | 検証・QAレポート作成 | readOnly, permissionMode: plan, skills: [qa-verification], opus/high |
| `security` | セキュリティレビュー | readOnly, permissionMode: plan, skills: [aegis-security-gate], opus/max |
| `ui` | UI/UX 作業 | inherit |

### 5.2 スペシャリストエージェント（6）

| エージェント | 役割 | 起動条件 |
|-------------|------|---------|
| `reviewer-testing` | テストカバレッジ特化レビュー | diff-scope が大きい場合（sonnet/high） |
| `reviewer-performance` | パフォーマンス特化レビュー | 同上（sonnet/high） |
| `reviewer-maintainability` | 保守性特化レビュー | 同上（sonnet/high） |
| `qa-browser` | ブラウザ QA | qa から委譲。disallowedTools で Edit/Write 禁止 |
| `translation-specialist` | Client→Dev ハンドオーバー翻訳 | handover 時（sonnet/high） |
| `integration-specialist` | 外部サービス統合（API/OAuth/webhook） | skills: [browser-assist, integration-assist] |

### 5.3 信頼境界

- `planner`, `reviewer`, `qa`, `security`, `reviewer-*` は `readOnly: true`（`reviewer`/`qa`/`security` は `permissionMode: plan`）
- `qa-browser` は `disallowedTools` で書込系ツールを明示的に禁止
- `skills:` frontmatter で preload されるスキルは `disable-model-invocation: true`

---

## 6. スキル

18 の pull-based スキルが `.claude/skills/` に配置されている。
各スキルは `SKILL.md` に frontmatter を持ち、Claude Code がフェーズに応じて読み込む参照文書として機能する。
v1.0.0 で公式同名スキルとの衝突回避のため一部を `aegis-*` に改名した。

| スキル | 対応フェーズ／用途 | user-invocable |
|--------|------------------|---------------|
| aegis-brainstorm | brainstorm | true |
| bug-diagnosis | brainstorm（bugfix/hotfix） | true |
| tdd | implement | true |
| subagent-dev | plan, implement, review | true |
| deploy | deploy | true |
| client-workflow | Client 全フェーズ | true |
| session-recovery | 任意（障害復旧） | true |
| ship-and-docs | ship, docs | true |
| aegis-review-gate | review | false |
| aegis-security-gate | security | false |
| qa-verification | qa | false |
| docs-sync | docs | true |
| translation-mapping | Client→Dev 翻訳 | true |
| integration-assist | 外部サービス統合 | true |
| browser-assist | ブラウザ自動操作基盤（gstack $B + Playwright MCP） | true |
| user-manual | docs（操作マニュアル生成・B3a） | true |
| maintenance | 保守ライフサイクル（RUNBOOK・本番インシデント・B3c） | true |
| uat | ship（受入テスト記録・B3b） | true |

---

## 7. フック（Policy as Code）

16 のランタイムフックが Claude Code のツール呼び出しを制御する。
フック設定は `templates/hooks.template.json` に定義され、`bin/setup.sh` が `settings.local.json` として生成する。
共有ライブラリは `hooks/lib/`（出力スキーマ＝`emit.sh`、破壊パターン＝`patterns.sh`、入力抽出＝`extract-input.sh`）。
`emit.sh` は pure-bash で外部依存ゼロ＝deny/block が fail-open しない。

### 7.1 フック一覧

| フック | イベント | マッチャー | 機能 |
|--------|---------|----------|------|
| **session-start.sh** | SessionStart | startup\|clear\|compact | STATUS.md を読取り、モード・フェーズ・ブロッカー・スキルヒント・高信頼度 LEARNINGS を注入。ゲートスナップショット初期化。second-opinion.md 検出 |
| **check-gate.sh** | PreToolUse | Edit\|Write\|NotebookEdit | plan ゲート未承認時にコード編集をブロック。Client モード中の編集もブロック。非 framework タスクでの制御ファイル編集をブロック |
| **check-tdd.sh** | PreToolUse | Edit\|Write\|NotebookEdit | テスト変更なしのプロダクションコード編集を警告（`ask`）。full のみ。`AEGIS_TDD_MODE=off` で無効化 |
| **check-client-info.sh** | PreToolUse | Edit\|Write\|NotebookEdit | Client モードで `docs/client/context.md` が無い場合に要件編集をブロック |
| **check-control-plane.sh** | PreToolUse | Bash | STATUS.md/CLAUDE.md/.claude/hooks/scripts への Bash 操作を非 framework タスク時にブロック（読取専用例外あり） |
| **check-destructive.sh** | PreToolUse | Bash | `rm -r`/`DROP TABLE`/`git push -f`/`git reset --hard` 等を検出して確認要求（`ask`）。ビルド成果物は例外 |
| **check-secrets.sh** | PreToolUse | Bash | `.env`・PEM/SSH 鍵・credentials.json 等の `git add`/commit を deny。`.gitignore` 不備は `ask` |
| **check-deploy-gate.sh** | PreToolUse | Bash | deploy コマンドを deploy ゲート未承認時に確認/ブロック |
| **check-deploy-mcp-gate.sh** | PreToolUse | mcp Vercel deploy | MCP 経由デプロイを deploy ゲートで制御 |
| **check-skill-gate.sh** | PreToolUse | Skill | 制御層を変更しうるスキル（update-config 等）を `ask` |
| **check-cron-gate.sh** | PreToolUse | CronCreate | スケジュール payload にデプロイ/破壊コマンドを含む場合 `ask` |
| **post-bash.sh** | PostToolUseFailure | Bash | テストコマンド失敗時に ReAct（Observe→Think→Act）を提案（informational） |
| **post-status-audit.sh** | PostToolUse | Edit\|Write\|NotebookEdit | STATUS.md 編集後にゲート改竄を検出。スナップショットと比較し不正な `approved` 遷移をブロック |
| **pre-compact.sh** | PreCompact | — | STATUS.md が 5 分以上未更新かつアクティブフェーズ中はコンテキスト圧縮をブロック |
| **check-task-created.sh** | TaskCreated | — | phase=implement で plan ゲート未承認なら新タスク作成を hard stop（`continue:false`） |
| **check-task-completed.sh** | TaskCompleted | — | 完了時に next_action 未更新／evidence 不整合を `exit 2` で差し戻し |

### 7.2 フック連携図

```
SessionStart
  └─ session-start.sh → .gate-snapshot 初期化 + コンテキスト注入 + second-opinion 検出

PreToolUse(Edit/Write/NotebookEdit)
  ├─ check-gate.sh         → plan ゲート / Client モード / 制御ファイル保護
  ├─ check-tdd.sh          → TDD 遵守チェック（full のみ）
  └─ check-client-info.sh  → Client 情報ガード

PreToolUse(Bash)
  ├─ check-control-plane.sh → 制御面ファイル保護
  ├─ check-destructive.sh   → 破壊コマンド警告
  ├─ check-secrets.sh       → .env/鍵の commit 阻止
  └─ check-deploy-gate.sh   → deploy ゲート

PreToolUse(Skill / CronCreate / mcp deploy)
  ├─ check-skill-gate.sh        → 制御層スキル確認
  ├─ check-cron-gate.sh         → スケジュール payload 確認
  └─ check-deploy-mcp-gate.sh   → MCP デプロイ制御

PostToolUseFailure(Bash)
  └─ post-bash.sh → テスト失敗時 ReAct ヒント

PostToolUse(Edit/Write/NotebookEdit) [case: *STATUS.md]
  └─ post-status-audit.sh → ゲート改竄検出

PreCompact
  └─ pre-compact.sh → 状態保存チェック

TaskCreated / TaskCompleted
  ├─ check-task-created.sh   → gate ブロック時 hard stop
  └─ check-task-completed.sh → evidence 差し戻し
```

すべての hook は `hooks/lib/emit.sh` を source して出力する。`setup.sh` は hook を含む profile で
`hooks/lib/*.sh` 全てを配布する（v1.3.2 で修正＝それ以前は emit.sh/patterns.sh 未配布で install 先の hook が全死していた）。

---

## 8. スラッシュコマンド

| コマンド | 用途 |
|----------|------|
| `/status` | STATUS.md のフォーマット済みサマリ表示 |
| `/gate` | ゲート一覧表示・承認操作（authorized script 経由） |
| `/judge` | judge カードのプレビュー（機械事実 vs claims・読取専用） |
| `/recover` | セッションリカバリ起動（session-recovery スキル） |
| `/validate` | 階層化フレームワーク評価実行 |
| `/next` | 次アクション・フェーズ遷移提案 |
| `/retro` | レトロスペクティブレポート生成（retro_report.py があれば／無ければ手動要約） |
| `/tutorial` | フェーズ遷移ウォークスルーガイド |

---

## 9. バリデータ・スクリプト

### 9.1 主要バリデータ

| スクリプト | 用途 |
|-----------|------|
| `check_framework_contract.py` | フレームワーク契約検証（ファイル存在、CLAUDE.md 語数、スキル/エージェント/コマンド/フック整合性、model/effort policy、name lint、プロファイル検証、example placeholder/mirror） |
| `check_status.py` | STATUS.md YAML frontmatter 検証（必須フィールド、ゲート整合性、tri-state pre-approve、完了 evidence） |
| `check_reference_drift.py` | 参照名ドリフト検出（11 チェック。本体↔example の mirror-identity を byte 比較） |
| `lint_names.py` | 名前クロスリファレンス lint（種別ごとの抽出器） |
| `run_eval.py` | 統合評価ランナー（Tier 0: unittest、Tier 1: 契約、Tier 2: scaffold スモーク、Tier 3: シナリオ） |
| `eval_scaffold_smoke.py` | scaffold 後に hook/script を実発火して install 経路を検証 |
| `eval_scenario.py` | シナリオベース評価 |

### 9.2 ユーティリティ

| スクリプト | 用途 |
|-----------|------|
| `update-gate.sh` | ゲート値の更新（STATUS.md の sed 置換・tri-state 解釈と `--ack` 記録・prereq 強制） |
| `run-test-strength-drill.py` | テスト強度ドリル（B1・qa 承認時に実走） |
| `build-judge-card.py` | judge カードビルダー（B2・review/qa/security/deploy 承認時に実走・tri-state） |
| `record-test-result.py` | テスト結果記録（test-result.json・judge が指紋照合で read） |
| `learnings_search.py` | LEARNINGS.md 検索（retro_report が利用） |
| `retro_report.py` | レトロスペクティブレポート生成 |
| `status_doctor.py` | STATUS.md の運用健全性チェック（鮮度・gate/ref 整合・second-opinion 有無。/recover が利用） |

---

## 10. テンプレート

26 のドキュメントテンプレートと 3 つのセットアッププロファイルを提供する。

### 10.1 ドキュメントテンプレート（主なもの）

| テンプレート | 出力先 |
|-------------|-------|
| CLAUDE.template.md | CLAUDE.md |
| STATUS.template.md | docs/STATUS.md |
| LEARNINGS.template.md | docs/LEARNINGS.md |
| PRD / NFR / SCOPE / ACCEPTANCE.template.md | docs/requirements/*.md |
| BRAINSTORM-RECORD / SPEC.template.md | docs/specs/*.md |
| PLAN.template.md | docs/plans/*-plan.md |
| REVIEW / QA-REPORT / SECURITY-REVIEW / VERIFICATION / DEPLOY-CHECKLIST.template.md | docs/qa-reports/*.md |
| HANDOVER-TO-DEV / HANDOVER-TO-CLIENT.template.md | docs/handover/TO-*.md |
| MANUAL.template.md | docs/handover/MANUAL.md（B3a） |
| RUNBOOK.template.md | docs/handover/RUNBOOK.md（B3c） |
| UAT-RESULTS.template.md | docs/handover/UAT-RESULTS.md（B3b） |
| CLIENT-CONTEXT / CLIENT-GLOSSARY / CLIENT-OPEN-QUESTIONS.template.md | docs/client/*.md |
| TRANSLATION-MAPPING.template.md | docs/translation/mapping.md |
| DECISION.template.md | docs/decisions/*.md |
| SECOND-OPINION.template.md | docs/second-opinion.md |

### 10.2 セットアッププロファイル

| プロファイル | 同梱 hook | 主な用途 |
|------------|----------|---------|
| minimal | session-start のみ | 最小（コア文書＋STATUS 検証） |
| standard | session-start, check-gate, post-status-audit, pre-compact | 推奨（基本ゲート＋状態保護） |
| full | 全 16 フック | 全構成（全スキル・全エージェント・全スクリプト・TDD backstop） |

`setup.sh` は profile の `required`/`recommended` に列挙されたファイルと `hooks_include` の hook を配布し、
hook を含む場合は `hooks/lib/*.sh` を全て配布する。

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
| **qa-browser/** | Playwright MCP を使ったブラウザ QA ワークフロー（Snapshot→Interact→Verify→Evidence） |
| **cost-tracking/** | セッションコスト追跡テンプレート |
| **mcp/** | MCP サーバー設定カタログ（5サーバー: Playwright, GitHub, Context7, Vercel, Figma） |

---

## 12. サンプルプロジェクト

`examples/minimal-project/` は自己完結したサンプルプロジェクトで、
フレームワークの全構成要素（エージェント、スキル、コマンド、ルール、フック、スクリプト）を含む。
本体とは制御ファイルが byte 一致でミラーされ、`check_reference_drift.py` の mirror-identity が同期を強制する。

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

原則: リポジトリファイルをチャット履歴より優先。フェーズ遷移時にサマリ。一時停止前に STATUS.md 更新。

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
4. `hooks_include` に基づきフックスクリプトをコピー（＋`hooks/lib/*.sh` を全配布）
5. `hooks.template.json` からフィルタリングして `settings.local.json` を生成

---

## 15. ファイル数サマリ

| カテゴリ | ファイル数 |
|----------|----------|
| 制御カーネル（CLAUDE.md） | 1 |
| ルール（.claude/rules/） | 2 |
| エージェント（.claude/agents/） | 12 |
| スキル（.claude/skills/） | 19（SKILL.md x18 + platforms.md x1） |
| コマンド（.claude/commands/） | 8 |
| フック（hooks/） | 19（メイン16 + lib/ 3: emit/patterns/extract-input） |
| スクリプト（scripts/） | 14 |
| テンプレート（templates/） | 30（.template.md x26 + hooks.template.json + profiles x3） |
| 拡張（extensions/） | 11 |
| サンプル（examples/minimal-project/） | 約90（本体ミラー＋検索シナリオ一式・随時増減） |
| ドキュメント（docs/） | 約96（plans/specs/qa-reports 等を含み随時増減） |
| その他（README, .gitignore, bin/） | 3 |
| **合計（.git 除く）** | **約 305** |

> サンプル・ドキュメントは作業に伴い増減する。構造的カテゴリ（エージェント〜テンプレート）の数値が正本。

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
| v0.8.0 | Client モード強化: translation-specialist + translation-mapping + check-client-info.sh + Client テンプレ群（agents 10→11, skills 12→13） |
| v0.9.0 | integration-specialist + integration-assist（agents 11→12, skills 13→14） |
| v0.10.0 | browser-assist スキル新設、qa-browser/integration-specialist 更新（skills 14→15） |
| v0.11.0 | 実運用振り返り（Hair Salon Bloom）7施策の反映 |
| v0.12.0 | MCP deploy gate、参照ドリフトチェック、name lint、status_doctor（health check） |
| v0.12.2 | hotfix: hook 出力スキーマを現行 Claude Code 仕様へ移行（deny/block が実際に効くように） |
| v1.0.0 | future-proof 再アーキ（F→R→A→D）。skill 改名（brainstorming→aegis-brainstorm 等）、新 gate hook（skill/cron/task）、evidence 完了強制、model/effort pin、emit.sh/patterns.sh 単一ソース、SemVer 安定契約 |
| v1.1.0 | B1 テスト強度ドリル + B2 judge カード（tri-state）+ ゲート exit code の tri-state 化 |
| v1.2.0 | B3a 操作マニュアル（user-manual スキル + MANUAL テンプレ） |
| v1.3.0 | B3b UAT（uat スキル）+ B3c maintenance（maintenance スキル + RUNBOOK）+ UAT ゲート結合 |
| v1.3.1 | B4 native 委譲マップ（docs-only） |
| v1.3.2 | 機能整合性監査の install 配送修正（emit.sh/patterns.sh 配布で moat 復活、/judge・graceful retro・status_doctor 配布、contract の hook 追跡、scaffold smoke の実行検証化） |
| v1.3.3 | integrity hook の可用性修正（進化レビュー P1×2: control-plane の transcript_path 衝突で install 先のほぼ全 Bash deny／check-gate glob の src/hooks/ 等衝突）。防御強度維持（バイパス形は全 deny 固定）、smoke の検証入力を実運用スキーマ化 |
| v1.4.0 | 進化レビュー P2×6/P3×6/K-2 の一括 fix。fail-open/closed ポリシー表（実発火突合テスト付き）、frontmatter.sh 共通化、deploy gate RC 契約＋size-skip ask 化、update-gate 排他ロック、B1 ドリル docs/** 除外、standard プロファイル Bash ガード4種、hooks 参照の `"${CLAUDE_PROJECT_DIR:-.}"` 化（未設定でも fail-open しない）、実リポジトリミラー同一性の unittest 化 |
