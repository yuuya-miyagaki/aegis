# iter55: ドッグフード一周目フィードバック反映 — 設計書

- 日付: 2026-07-03
- 対象版: v1.15.0 → v1.16.0
- task_type: framework / task_size: L
- 一次情報（正本・repo 外）: `~/Desktop/personal/yoga-tsukinowa-lp` の
  `DOGFOOD-LOG.md`（観測正本）・`docs/LEARNINGS.md`「フレームワーク改善」節（修正候補5件・confidence 6〜8）・
  `docs/retro-2026-07-03.md`（KPT）

## 背景と成果サマリ（ドッグフード一周目）

実案件シミュレーション（予約 LP・Client→Dev 全16フェーズ・全8ゲート）を約1.5日で完走。
迷子 0・blocking 0・[P4] 見逃し 0。仮説 H1/H2/H3 すべて実証。
摩擦は「ゲート戦闘 7 件」に集約され、**うち 6 件が許可リスト系（allowlist の漏れ・指示と hook の矛盾）**、
1 件は呼び出しミス（hook 仕様自体は妥当）。

根本原因の構造: **settings permissions（配布 8 スクリプト）と check-control-plane.sh の
allowlist（5 スクリプト・重なり 2 本のみ）が別管理でドリフト**しており、skill/command が指示する
スクリプトを hook が阻止する。調査で /retro・/gate に加え **/recover（session-recovery →
status_doctor.py）も対象プロジェクトでは実行不可**という未発火の同類バグを確認した。

## 現状の3リストの実態（2026-07-03 調査）

| スクリプト | permissions.allow（hooks.template.json） | hook allowlist（check-control-plane.sh） | skill/command 参照 |
|---|---|---|---|
| check_status.py | ✅ | ✅ | /validate |
| check_framework_contract.py | ✅ | ✅ | /validate |
| status_doctor.py | ✅ | ❌ | session-recovery（/recover） |
| retro_report.py | ✅ | ❌ | /retro |
| build-judge-card.py | ✅ | ❌ | /gate・/judge |
| check_reference_drift.py | ✅ | ❌ | —（framework 開発用） |
| learnings_search.py | ✅ | ❌ | —（session-start hook 内部） |
| lint_names.py | ✅ | ❌ | —（framework 開発用） |
| update-gate.sh | ❌ | ✅ | 各ゲート skill・/gate |
| record-test-result.py | ❌ | ✅ | qa 系 |
| run-test-strength-drill.py | ❌ | ✅ | qa-verification |
| **update-task.sh** | ❌ | ❌ | aegis-brainstorm・bug-diagnosis |

前提知識: check-control-plane.sh は task_type=framework では発火しない（allowlist は
**対象プロジェクト＝target project でのみ**効く）。hook 内部（session-start.sh 等）からの
スクリプト実行は Bash tool を経由しないため allowlist の対象外。

## P0: 許可リストの単一ソース化【最優先】

### 前提発見（2026-07-03 調査）

iter52 が既に **scripts/ 全 18 エントリポイントの意図分類マップ** `SCRIPT_CLASS`
（safe_auto_allow / must_prompt / not_cli）を `tests/test_permission_allowlist_install.py` に構築済み。
record-test-result.py / run-test-strength-drill.py は「引数コマンドを実行するガジェット＝auto-allow
すると permission バイパス」、update-gate.sh / update-task.sh は「状態変異＝プロンプト必須」という
先行判断があり、本設計の tier 判断と完全に一致する。ただしこの分類はテストファイル内の dict であり、
hook の case 文・template の permissions と**3重管理**のまま。本 iteration でこの分類を昇格させ
単一正本にする。

もう一つの死角: `bin/setup.sh` の lib 配布は `hooks/lib/*.sh` glob（L463）のため、
**そのままでは .tsv manifest が install 先に配布されず fail-closed で全 deny**（F6 級の install 死角）。
setup.sh の配布修正＋install テストを必須スコープに含める。

### 決定

新規 manifest `hooks/lib/scripts-manifest.tsv` を single owner とする（scripts/ 全エントリポイントの分類）。

```
# 形式: <scripts/ パス><TAB><class>
# class: allow          = hook 実行可 + permissions.allow 掲載（許可プロンプトなし）
#        ask            = hook 実行可 + permissions 非掲載（プロンプト＝人間のトリップワイヤ）
#        framework-only = 対象プロジェクトでは hook が deny（framework 開発専用ツール）
#        import-only    = CLI でなく import 専用モジュール
scripts/check_status.py	allow
scripts/check_framework_contract.py	allow
scripts/status_doctor.py	allow
scripts/retro_report.py	allow
scripts/build-judge-card.py	allow
scripts/check_reference_drift.py	allow
scripts/learnings_search.py	allow
scripts/lint_names.py	allow
scripts/update-gate.sh	ask
scripts/update-task.sh	ask
scripts/record-test-result.py	ask
scripts/run-test-strength-drill.py	ask
scripts/context_budget.py	framework-only
scripts/run_eval.py	framework-only
scripts/eval_scaffold_smoke.py	framework-only
scripts/eval_scenario.py	framework-only
scripts/_artifact_template_map.py	import-only
scripts/platform_manifest.py	import-only
```

（タブ区切り。# 行と空行は無視。hook 実行可 = allow∪ask の 12 本。
context_budget.py は --tighten/--seed が契約ゲート設定を書くため framework-only〔iter52 grill 🔴 踏襲〕）

### 消費側1: check-control-plane.sh

`is_allowlisted()` のハードコード case 5 本を manifest 読込（class ∈ {allow, ask} の行）に置換。

- 読込は pure-bash（`while IFS=$'\t' read`）。python 依存を持ち込まない（emit.sh の教訓:
  python3 依存 = fail-open リスク）
- **fail-closed**: manifest が欠落・空・読取不能なら従来どおり全 deny（is_allowlisted が常に 1）
- マッチ規則: チェーン演算子（`[;&|>]|\$\(|` バッククォート）拒否 → 残った単体コマンドが
  manifest エントリの**実行形**（`python3|python|bash|sh <path>` / `<path>` / `./<path>` で
  **始まる**）であること。**substring マッチは禁止**（`cp evil scripts/update-gate.sh` のような
  許可スクリプトへの書込みまで allow する脆弱な規則＝grill-code 🔴 で封鎖済み）。env 代入
  プレフィックスや quoted パスは不一致＝deny（安全側・汎用 deny が単体実行形を案内）
- manifest 自体は hooks/lib/ 配下＝control plane。非 framework タスクからの改変は
  check-gate.sh（Edit/Write）と check-control-plane.sh 自身（Bash）が既に封鎖している —
  置換前の hook ハードコードと同じ信頼水準

### 消費側2: bin/setup.sh（配布）

lib 配布 glob に `hooks/lib/*.tsv` を追加。install テストで「installed tree に manifest が存在し、
installed hook の実発火で allow スクリプトが通る」ことを契約化（F6 の教訓: install 出力を無検査にしない）。

### 消費側3: check_framework_contract.py（drift 検査 3 方向）

1. **manifest 健全性**: 全行がパース可能・`scripts/<name>` が実在ファイル・class が enum 内・重複なし・
   **scripts/ の全 *.py / *.sh が漏れなく分類されている**（完全性）
2. **permissions 双方向一致**: class=allow ⟺ `templates/hooks.template.json` の permissions.allow に
   canonical 形式（`.py` → `Bash(python3 scripts/X.py:*)` / `.sh` → `Bash(bash scripts/X.sh:*)`）で存在。
   allow 以外のエントリが permissions に**あれば FAIL**（人間トリップワイヤの誤解除を検知）
3. **skill/command 参照の包含**: `.claude/skills/**/SKILL.md`・`.claude/commands/*.md`・
   `templates/commands/*.md`・`.claude/rules/*.md` に現れる全 `scripts/<name>.(py|sh)` トークンの
   class ∈ {allow, ask}。**skill が指示するスクリプトは必ず hook を通る**ことを契約化
   （今回の事故クラスの構造的封鎖）。CLAUDE.md は走査対象外
   （platform_manifest.py への「定義場所」言及＝実行指示でない mention があるため）

### 消費側4: tests/test_permission_allowlist_install.py

`SCRIPT_CLASS` dict を manifest 由来のローダーに置換（allow→safe_auto_allow・
ask/framework-only→must_prompt・import-only→not_cli）。iter52 の完全性テスト
（新スクリプト追加時に未分類なら FAIL）はそのまま manifest の完全性強制として働く＝
**新スクリプトを足すと manifest 1 行の追加を強制され、hook/permissions/テストが同時に整合**する。

### 採用しなかった代替案

- **B: hook が settings.local.json の permissions を直接参照**（LEARNINGS 提案の一方）:
  ユーザ可変ファイルに integrity moat を委ねることになり弱体化。意味論も不一致
  （permissions の allow=「許可プロンプトなし」 ≠ 「control plane に触れる資格」。
  現に update-gate.sh は「実行可だがプロンプトは残す」が正しい）。bash からの JSON パースも脆い
- **C: 二重リスト維持＋drift 検査のみ**: リスト自体は残るため追加のたび2箇所編集。
  「declarative な第3ミラーは沈黙して腐る」（M1/P1/P2 で確立した single-owner パターンの教訓）に反する

### 設計判断（明記）

- **update-gate.sh を permissions に載せない（ask 維持）は仕様**: ハードゲート承認時の
  許可プロンプトが「人間の明示承認」の harness 側トリップワイヤとして機能している。
  自動許可にすると LLM 単独でゲート承認が完結してしまう
- ask 4 本は現行挙動から**プロンプト有無を変えない**（挙動変更ゼロで漏れだけ塞ぐ）
- 将来の構造リアーキ（文字列判定→FS 実解決/OS-lock・check-control-plane 退役）でも
  正準スクリプトリストは必要＝manifest は前方互換の投資

## P1: client-workflow と hook の契約矛盾解消

### 1a. translation ref のタイミング（ゲート戦闘3）

現状の正面衝突:
- client-workflow SKILL.md（現 L89 付近）「handover で mapping.md を作成したら
  current_refs.translation に設定する」
- check_status.py の stale-ref 検査（gate→ref 対応 `client_ready_for_dev: translation`）:
  gate pending 中に ref が入っていると FAIL（TaskCompleted / contract 経由で発火）
- update-gate.sh: 承認時に ref が無いと ADVISORY

修正: SKILL.md の当該記述（進行表 L28 の exit 条件と L89）を hook 契約に合わせて書き換える。
正しい運用を一文で明文化:

> mapping.md は handover フェーズ中に作成する。`current_refs.translation` への設定は
> **client_ready_for_dev 承認の直前**に行い、設定 → `update-gate.sh` 承認を**連続で**実行する
> （gate pending のまま ref を設定して完了検査を挟むと stale-ref 違反になる）。

（aegis 自身の STATUS next_action 罠 (b)(c) として既知だった運用知識を、対象プロジェクトに
配布される skill 本文へ昇格させる）

### 1b. テンプレ発見性（requirements/handover の摩擦）

PRD/SCOPE/NFR/ACCEPTANCE/TO-DEV のテンプレパスが client-workflow から辿れず 2 回誤推測した。
既存 single owner `scripts/_artifact_template_map.py`（ARTIFACT_TO_TEMPLATE）の Client 側
エントリを client-workflow SKILL.md に artifact→template 対応表として追記し、
**parity テスト**（SKILL.md の表 ⊇ map の Client gate artifacts）で drift を封鎖する。

## P2: メタ文書（repo 直下 *.md）の書込許可

現状: check-gate.sh は docs/* を先頭で許可 → control 検査（hooks/scripts/.claude/CLAUDE.md）→
Client モード全 deny／plan pending 全 deny。repo 直下の DOGFOOD-LOG.md・README.md 等の
prose が Client モード＋plan 承認前の全期間で書けない（ゲート戦闘2・4）。

修正: control 検査の**後**・Client/plan 判定の**前**に「repo 直下の `*.md` は allow」を追加。

- 意味論: **ゲートはコードを守る。散文（Markdown）は対象外**
- 挿入位置が本質: CLAUDE.md（および case-fold 変種）は直前の control 検査で既に deny 済みなので
  穴にならない。docs/STATUS.md は docs/* 許可＋post-status-audit 監査の既存経路のまま不変
- サフィックス判定は case-fold（`.MD` 等・iter54 の case-insensitive FS moat と整合）
- 対象は **repo 直下のみ**（最小修正）。サブディレクトリの .md は従来どおり
  （docs/ 配下は既に書ける。src/ 等のコード木に紛れた .md まで開けない）

## P3: エラーメッセージ改善＋ ls deny の再現調査

### 3a. チェーン演算子の専用メッセージ（ゲート戦闘6・LEARNINGS #5）

is_allowlisted が「manifest エントリを含むがチェーン演算子で不適格」と判定できるケースを検出し、
専用 deny メッセージを出す:

> このスクリプトは許可済みですが、チェーン演算子（; && || | > $() バッククォート）付きでは
> 実行できません。パイプ等を外して単体で実行してください。

### 3b. 汎用 deny メッセージの矛盾解消（ゲート戦闘5の残骸）

現行 L937 の「Use Edit/Write tools for auditable changes」は、対象が STATUS の gate/task 制御値の
場合 state-machine.md の「raw edits = tamper」と矛盾する。書き換え:

- ゲート値は `scripts/update-gate.sh`、task_type/size は `scripts/update-task.sh` を単体実行で
- 一般ファイルは Edit/Write を使用
- framework ファイルの変更は task_type=framework が必要

### 3c. mention 発火のヒント（docs フェーズの摩擦）

`git add docs/STATUS.md` のようにコマンド文字列中のファイル名 mention だけで発火する仕様への
ヒントを ask/deny メッセージに追加（例: 「`git add docs/` のようにディレクトリ単位で指定すると
通ります」）。

### 3d.【調査済・原因確定】読み取り専用 `ls` deny の正体＝安全な stderr リダイレクト（ゲート戦闘1）

2026-07-03 に実 hook プローブで確定:

- `ls templates/ docs/`（素）→ **ALLOW**（read-only carve-out は正常）
- `ls templates/ 2>/dev/null`・`ls templates/ docs/ 2>&1` → **DENY**
  （`>`/`&` が CHAIN_OPS に該当し read-only 判定から脱落）

つまり LOG の deny は「エージェントが慣用的に付ける stderr リダイレクト」が原因。
`bash scripts/update-gate.sh … 2>&1` も同様に落ちる（allowlist 側も同じ CHAIN_OPS ガード）。

修正: **安全な stderr リダイレクトの正規化** — `2>/dev/null`（`2> /dev/null` 含む）と `2>&1` を
コマンド文字列から除去してから allowlist / read-only / git-stage 判定を行う。除去対象は
ファイル書き込みが発生し得ない 2 形のみ（完全一致・単語境界）。fail-closed を維持する縁ケース:

- `2>>/dev/null`・`2>file`・`2>/dev/nullish` は除去しない → 従来どおり deny
- `cmd 2>&1 > hooks/evil` → 除去後も `>` が残る → deny
- fd1 の `>/dev/null` は対象外（観測された摩擦は stderr 形のみ・YAGNI）
- CONTROL_PLANE 検出そのものは生文字列のまま（判定緩和は allow 側 carve-out のみ）

## P4: qa-verification に委譲粒度ガイド

実測（19 項目 1 委譲でサブエージェント停止 3 回・SendMessage 再開）に基づき、
qa-verification SKILL.md の qa-browser 委譲節へ 1〜2 行追記:

> 長尺のブラウザ検証は 1 委譲あたり約 5 項目に分割して複数回委譲する。
> 対話的な長尺検証はサブエージェントの停止と相性が悪い（一周目実測: 19 項目 1 委譲で停止 3 回）。

## スコープ外（バックログ・次周以降のテーマ）

- scope+acceptance 統合承認の軽量ルート（小規模案件向け。onboard+discovery 統合は既許可）
- discovery の exit チェックリスト（最低限聞くべき項目群）
- 委譲プロンプト標準化（テスト実行スコープ限定・ファイル競合なし・自己申告の正直さ）の skill テンプレ昇格
- security ロールの ref 設定＋ゲート承認のオーケストレーター作業自動化
- 構造リアーキ（FS 実解決/OS-lock 昇格・check-control-plane 退役）— 一周後の最有力テーマとして維持。
  本 iteration は現行文字列判定アーキ内の戦術修正であり、manifest はリアーキ後も生きる。
  **追加論拠（grill-plan 2026-07-03）**: 文字列判定は symlink を見抜けない
  （例: repo 直下 `x.md → hooks/lib/emit.sh` の symlink 経由 Edit は path 文字列上 prose）。
  既存クラスの穴で layer-2 cp-lock（chmod）が実書込みを止めるが、根治は FS 実解決＝リアーキ側

## テスト戦略（TDD・RED-first）

- P0: manifest パース（正常/欠落/空/壊れ行/重複）・fail-closed（manifest 欠落＝全 deny）・
  allow∪ask 12 本の hook 実発火 ALLOW・framework-only の DENY・チェーン付き deny 維持・
  contract 3 方向検査の RED→GREEN（意図的 drift を仕込んで FAIL を確認）・
  setup.sh install 先での manifest 実在＋installed hook 実発火（F6 教訓の install 契約）
- P1: SKILL.md parity テスト（_artifact_template_map の Client 産出物 ⊆ SKILL 記載）・
  translation タイミング文は token pin テストで固定（「承認の直前」の存在＋旧文言の不在を assert。
  iter53 の test_destructive_warning_language.py と同型のドリフトガード）
- P2: repo 直下 .md allow（Client モード/plan pending 両方）・CLAUDE.md deny 不変・
  case-fold 変種（.MD / claude.md）・サブディレクトリ .md は従来どおり
- P3: メッセージ内容の assert（チェーン専用文言・update-task.sh 案内）・ls 再現テスト
- 既存 full suite（1232+）非回帰

## 版・ゲート計画

- v1.16.0（minor: 新機能=manifest+contract 検査・後方互換。既存 install への影響は
  setup.sh 再実行で manifest 配布＋settings 再生成）
- iter55 rollover（iteration=55・dev gates reset・task_type=framework・task_size=L）
- L=全ゲート: brainstorm→plan→implement→review→qa→security→deploy→ship→docs
