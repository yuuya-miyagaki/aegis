# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-24-iter41-batch1-distribution-integrity-brainstorm-record.md`
- 要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md` ＋ `docs/security-followups.md` SF-006

## 問題整理

- 背景: ドッグフード full は堅いが、配布形態（standard profile・reinstall 型 upgrade）が core 保証を提供しない（RC-2）。STATUS.md が制御面と自由編集 doc を兼ね、間に立つ post-status-audit が自身 fail-open（RC-1）。
- 判断が必要な論点: 各 finding の最小十分な修正範囲。特に D3 の上書き分類と I1 の PostToolUse fail-closed 設計。
- 制約条件: check-control-plane 本体を触らない。dogfood の curated settings を壊さない。既存 1038-test suite を green に保つ。framework_version を bump。

## 推奨アプローチ（finding 別）

### D1 — standard で judge ツールチェーンを提供
- 採用方針: `templates/profiles/standard.json` の `recommended` に `scripts/build-judge-card.py`・`scripts/run-test-strength-drill.py`・`scripts/record-test-result.py`・`hooks/lib/fingerprint.sh` を追加。
- 採用理由: `check_status.py:944-947` で builder 不在→return 1（fail-closed）＝review/qa/security/deploy が standard で承認不能。`build-judge-card.py:33` が `run-test-strength-drill.py` を importlib で**必須**ロード（fallback 無し）＝同梱必須。`record-test-result.py` は green record 生成に必要。`fingerprint.sh` は nolib fallback ありだが functional な judge には必要。
- 代替案却下: builder 1 ファイルのみ追加→importlib で即クラッシュ。
- 配置: `required` ではなく `recommended`（judge は full の主機能・standard では「あると承認できる」位置づけ。ただし profile の `required_hook_scripts` とは別軸＝ファイル存在は recommended で十分、警告で可視化）。**plan で required/recommended を最終確定**。

### D2 — Task hook を profile・active settings・contract に配線
- ユニット (a) `standard.json`: `hooks_include` に `check-task-created.sh`/`check-task-completed.sh` 追加。`required_hook_scripts` にも追加（contract が active 登録を強制）。
- ユニット (b) `.claude/settings.local.json`: `PostToolUse` ではなく Task イベントとして `TaskCreated`/`TaskCompleted` セクションを新設し両 hook を登録（テンプレ `templates/hooks.template.json:132-151` 準拠）。
- ユニット (c) `check_framework_contract.py`: full self-check に「active settings が CORE 強制 hook を登録」検査を追加。CORE = `check-task-created.sh`,`check-task-completed.sh`,`check-gate.sh`,`post-status-audit.sh`,`check-control-plane.sh`（完了強制＋gate/audit/moat）。full の hooks_include 全集合は要求しない（dogfood は check-tdd/skill-gate/cron-gate 等を意図的に省略）。

### D3 — upgrade で framework 資産を上書き・user 資産を保全
- 採用方針: `bin/setup.sh` の `install_file`（既存を SKIP）を、**version bump を伴う upgrade 時に framework 所有パスは上書き（既存を `.bak` 退避）**するよう変更。
- 分類:
  - framework 所有（上書き対象）: `hooks/**`, `scripts/**`, `templates/**`, `.claude/skills/**`, `.claude/agents/**`, `.claude/commands/**`, `.claude/rules/**`
  - user 所有（保全）: `docs/**`, `CLAUDE.md`, `.claude/settings.json`, `.claude/settings.local.json`, `.claude/.gate-snapshot`, `.gitignore`
- 採用理由: security 修正（hooks/scripts）が既存ユーザーに届く。`.bak` で復元可能＝可逆。
- **要ユーザー確認**: `.claude/rules/**` と `CLAUDE.md` の扱い。既定は rules=上書き（framework 定義）・CLAUDE.md=保全（customする人が多い）。

### D4 — 壊れた既存設定の無警告全消しを是正
- 採用方針: `bin/setup.sh:272-281` の `except Exception: existing = {}` で、stderr に明示警告（既存 settings が JSON parse 不能・permissions/env を引き継げない・`.bak` から手動復元を案内）を出す。
- 採用理由: 非エンジニアが `//` コメント混入等で権限を無自覚に失う事故防止。abort ではなく警告＋継続（.bak は既に退避される）。

### I1 — post-status-audit を fail-closed 化
- 採用方針: `safety.sh` に PostToolUse 版 fail-closed helper（`_aegis_emit_fail_closed_block` ＝ `{"decision":"block","reason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}` 静的）と `aegis_require_lib_block`（block schema 版）を追加。`post-status-audit.sh` 冒頭に **PostToolUse 用** fallback block（`AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN/END`）を置き、その後 `aegis_require_lib_block` で extract-input/emit/frontmatter/phase-skills を必須ロード。
- 採用理由: lib source 失敗（set -e で死ぬ）→空 stdout＝PostToolUse spec で allow＝fail-open を塞ぐ。gate/mode tamper は bash のみで python3 非依存＝lib さえあれば検知可能。
- スコープ限定: **task_type tamper は I3=Batch 2**＝I1 では追加しない。phase-transition python3 部は現挙動維持（最小変更／advisory 化は plan/grill で再評価）。

### I2 — 完了evidence を fail-closed 化
- 採用方針: `check_status.py` の `--check-completion-evidence` 経路（:1484-1497）で `not status_path.exists()` または `frontmatter is None` を violation（exit 1）化。
- 採用理由: `validate_status_file` は同条件 fail-closed＝対称化。呼び元 check-task-completed.sh は STATUS 不在時に手前で early-allow するため正常フロー無影響。

## コンポーネント分解

- 分割方針: finding ごとに独立ユニット。共有変更は `safety.sh`（I1）と `check_framework_contract.py`（D2c）。
- 各ユニットの責務: 上記「推奨アプローチ」参照。

## インターフェース定義

- `safety.sh`: 既存 `_aegis_emit_fail_closed_deny`（PreToolUse deny）に加え `_aegis_emit_fail_closed_block`（PostToolUse block）＋`aegis_require_lib_block`。reason は静的（JSON injection 面ゼロ・drift 面ゼロ）。
- `setup.sh install_file`: 引数に上書き可否を渡すか、パス分類関数 `is_framework_owned <relpath>` を追加し upgrade 判定（旧 stamp < 新 stamp）と組み合わせる。
- `check_framework_contract.py`: CORE_ENFORCEMENT_HOOKS 定数＋full self-check 内の登録検査関数。

## データフロー / 構造

- gate 承認: update-gate.sh → check_status.run_judge_card → build-judge-card.py → (importlib) run-test-strength-drill.py。D1 はこの依存鎖を standard に揃える。
- 完了強制: TaskCompleted → check-task-completed.sh → check_status `--check-completion-evidence`（I2 で fail-closed）。D2 はこの hook を配線。
- STATUS 編集監査: Edit(STATUS) → post-status-audit.sh（I1 で lib source を fail-closed）。

## 依存関係

- I1 は I3（Batch 2）の前提。I2 は単独。D1/D2/D3/D4 は相互独立。循環なし。
- 外部依存: なし（pure bash / python3 stdlib）。

## エラーハンドリング

- 想定失敗: lib 欠損（I1=block）、STATUS 欠損（I2=violation／hook は手前で allow）、parse 失敗（D4=警告）、importlib 失敗（D1=同梱で回避）。
- エラー伝播: fail-closed を基本（deny=PreToolUse, block=PostToolUse, violation=exit 1, 警告=stderr+継続）。

## テスト戦略

- 単体: D1=standard profile に judge toolchain が含まれる／run_profile_check が standard で judge 承認可能。D2=standard hooks_include/required_hook_scripts に Task hooks／contract full self-check が active 未登録を FAIL／settings.local.json に Task hook 登録。D3=upgrade で hooks/ が上書き・docs/ は保全・.bak 生成／同 version では SKIP 維持。D4=壊れ JSON で警告出力＋既存 settings .bak。I1=lib 欠損で post-status-audit が block・libあれば従来通り。byte-identity test は 6 PreToolUse 同一＋PostToolUse 別 canonical。I2=STATUS 不在/None-frontmatter で exit 1。
- 結合: full suite（既存 ~1038）green。`check_framework_contract.py`（full）PASS。`run_profile_check standard` PASS（dogfood を標準 install に見立てた fixture）。status_doctor PASS。
- エッジケース: D3 で symlink/space パス・upgrade 判定（stamp 比較）境界。I1 で emit.sh 自体の欠損。
- 手動確認: dogfood の Task hook 配線後、実 TaskUpdate(completed) が通る（next_action 有・evidence-log 有・completion-evidence rc=0 を維持）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-24-iter41-batch1-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートを PLAN の「参照設計」に記載
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->
