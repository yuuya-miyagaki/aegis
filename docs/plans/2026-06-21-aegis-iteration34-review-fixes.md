# Aegis iteration 34 — レビュー所見の集中修正 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`（推奨）or `superpowers:executing-plans` でタスク単位に実装。各タスクは TDD（RED→GREEN）で進め、ステップは `- [ ]` で追跡する。

**Goal:** 全力レビュー（内製5レンズ）＋外部レビューで確定した所見のうち、moat 整合性・machinery 真実性・install 正しさ・ドキュメント真実性の修正を、フレームワーク自身のゲート規律で潰す。

**Architecture:** 既存の fail-closed 設計（`hooks/lib/safety.sh` の `aegis_require_lib`／byte 同一 fallback ブロック）と単一所有 manifest 思想に**寄せて**修正する。新しい抽象は作らない（YAGNI）。挙動を変えるのは moat hook の corruption 時挙動と profile contract の検査範囲のみで、正常系の deny/allow/ask ロジックは不変。

**Tech Stack:** bash 3.2（macOS system）, python3（stdlib のみ）, pytest, JSON profiles。

## Global Constraints（全タスク共通・spec から逐語）

- **bash 3.2 互換**: 連想配列・`${var^^}`・`local -n`・`sed -i`・`grep -P` 禁止。配列反復は `"${ARR[@]:-}"` ガード。
- **fail-closed 不変条件**: deny/ask hook は lib 欠損・source 失敗時に「空 stdout＋rc≠0（=fail-open）」を出してはならない。必ず構造化 deny を emit する。
- **byte 同一 fallback**: `AEGIS_SAFETY_FALLBACK_BEGIN/END` ブロックは全対象 hook で SHA256 一致（`tests/test_safety_fallback_identity.py` が強制）。reason 文字列は静的（`%s`/`$VAR` 禁止）。
- **silent-green 禁止**: テスト緑認証ロジック（`evidence.sh`／`build-judge-card.py` reader／fingerprint binding）は byte 不変。本計画はこれに触れない。
- **言語**: 制御ファイル（hooks/scripts/CLAUDE.md）は英語、docs は日本語。
- **version**: 挙動修正を含むため PATCH bump `1.12.0 → 1.12.1`（contract 定数・template・live STATUS を同期）。gate 名・gate→ref 結合・hook 出力スキーマは不変＝MAJOR/MINOR 非該当。
- **commit gotcha**: メッセージに `${...}`/`~+`/brace を入れない。`git commit -F <file>` を使う。
- **承認待ち**: plan ゲートは本計画への明示承認。E2/E3 は moat に触るため **security ゲート必須**。

## ロックされた方針（ユーザー承認 2026-06-21「推奨で進めて」）

1. ask hook も corruption 時は **deny に倒す**（保守的・byte 同一 fallback を流用）。
2. E3 は **moat 4 hook**（control-plane/destructive/secrets/deploy-gate）を required-registration 化（`hooks_include` 全部ではない）。
3. **iteration 34** として正式フルゲート（review+qa+security+deploy）で進める。
4. 案A immutable moat PoC は **別タスク**（今回は層1 bug-fix に集中）。

## バッチとシーケンス

`Batch 0（STATUS 衛生）→ A（moat 整合性）→ B（machinery 真実性）→ C（install 正しさ）→ D（docs 真実性）`。
Batch E（保守性 refactor: model 方針集約・version-sync 集約・P3 群）は **本 iteration 範囲外**＝別計画に分離（writing-plans の scope-check に従い、独立 subsystem として切る）。

---

## Batch 0: STATUS 衛生（前提・非コード）

### Task 0: iteration 34 起票＋ stale blocker 解消

**Files:**
- Modify: `docs/STATUS.md`（frontmatter: iteration 33→34, phase→plan, dev gates→pending, 非 requirements refs→null, current_refs.plan→本ファイル）
- Move: `docs/second-opinion.md` → `docs/archive/2026-06-18-second-opinion-sf001.md`（SF-001 は解決済み・`docs/security-followups.md` に記録済み。session-start blocker を解消）

> **検証で確定した mechanics（grill 反映）**: (a) second-opinion blocker は `session-start.sh:87` の**完全一致** `docs/second-opinion.md` → `git mv` で確実解消。(b) **gate 値は `post-status-audit.sh:77-89` が STATUS 直接編集を tamper として block する**。gate 変化は全て `scripts/update-gate.sh <gate> [approve|reset]` 経由（Bash 実行＝監査を自然回避・snapshot を atomic 更新・`reset` は ref も null 化）。(c) phase 変化は `--check-phase-transition` で監査される。

- [ ] **Step 1**: `mkdir -p docs/archive && git mv docs/second-opinion.md docs/archive/2026-06-18-second-opinion-sf001.md`。`check_framework_contract.py --profile=full` が PASS（second-opinion.md の存在を要求しないことを確認）。
- [ ] **Step 2（gate rollover・update-gate.sh のみ）**: iteration 33 の approved dev gate を pending へ戻す: `bash scripts/update-gate.sh <g> reset` を brainstorm/plan/review/qa/security に対して実行（deploy は既に pending・ref も自動 null 化）。
- [ ] **Step 3（非 gate frontmatter）**: `docs/STATUS.md` を Edit で iteration 33→34・task_size=L・task_size_rationale 更新・`current_refs.requirements` 維持・`current_refs.plan` を本計画へ。phase を security→plan へ（`check_status.py:1243` **Rule 3「backward/same は常に許可（rework）」** で後方遷移＝監査を通る・検証済み）。`next_action` の旧 strata は `session_history` へ移送（M2 同時対応）。
- [ ] **Step 4（brainstorm 承認・ユーザー authorization）**: 本会話で scope 合意済みのため `bash scripts/update-gate.sh brainstorm approve`（ユーザーの「進んでください」を明示承認として扱う）。plan は本計画の承認まで pending 据置。
- [ ] **Step 5**: `python3 scripts/check_status.py --root . --strict` と `check_framework_contract.py --profile=full` が PASS。commit（`-F`）。

---

## Batch A: moat 整合性（security-critical・TDD）

### Task A1: emit.sh 利用 hook の fail-closed 統一

**背景（検証で確定）**: `AEGIS_SAFETY_FALLBACK_BEGIN` を持つのは 6 hook（control-plane/gate/secrets/task-created/destructive/task-completed）。一方 `emit.sh` を直 source して fallback を持たないのは **6 hook**: `check-deploy-gate.sh`（**deny**）, `check-deploy-mcp-gate.sh`（**deny**）, `check-skill-gate.sh`（ask）, `check-cron-gate.sh`（ask）, `check-client-info.sh`, `check-tdd.sh`（ask backstop）。`set -euo pipefail` 下で emit.sh 欠損 → source 失敗で rc≠0＋空 stdout ＝ Claude Code 仕様で**非ブロッキングエラー＝ツール続行＝fail-open**。deploy 2 hook の fail-open が最重大（外部レビューは deploy-mcp のみ指摘・**deploy-gate を取りこぼし**）。

**不変条件（新規・確立する）**: emit.sh を使う全 hook は、lib 欠損・source 失敗時に `safety.sh` の byte 同一 fallback 経由で **deny を emit**（fail-closed）。

**Files:**
- Modify: `hooks/check-deploy-gate.sh`, `hooks/check-deploy-mcp-gate.sh`, `hooks/check-skill-gate.sh`, `hooks/check-cron-gate.sh`, `hooks/check-client-info.sh`, `hooks/check-tdd.sh`（各先頭に `AEGIS_SAFETY_FALLBACK_BEGIN/END` ブロックを挿入し、`source .../lib/emit.sh` を `aegis_require_lib ".../lib/emit.sh"` へ置換。他 lib も同様に `aegis_require_lib` 化）
- Modify: `hooks/lib/safety.sh`（コメントの「6 deny hooks」→ 実集合に更新）
- Test: `tests/test_safety_fallback_identity.py`（対象 hook 集合を 6→12 へ拡張・SHA256 一致）
- Test: `tests/test_hook_emit_failclosed.py`（**新規**・不変条件の回帰ガード）

- [ ] **Step 1（RED・回帰ガード）**: `tests/test_hook_emit_failclosed.py` を新規作成。(a) ソース走査テスト: `hooks/check-*.sh` のうち `lib/emit.sh` を参照する全 hook が `AEGIS_SAFETY_FALLBACK_BEGIN` を持つことを assert（現状 6 hook で FAIL）。(b) 実行テスト: 一時 dir に各対象 hook と空の `lib/` を置き emit.sh を欠損させて実行 → stdout に `"permissionDecision":"deny"` を含み rc=0（構造化 deny）であることを assert。
- [ ] **Step 2**: RED 確認（`pytest tests/test_hook_emit_failclosed.py -v` で 6 hook 分 FAIL）。
- [ ] **Step 3（GREEN）**: 各対象 hook の `SCRIPT_DIR=` 直後に、`check-gate.sh:8-23` と **byte 同一**の `AEGIS_SAFETY_FALLBACK_BEGIN/END` ブロックを挿入し、`source "${SCRIPT_DIR}/lib/emit.sh"`（および他 lib）を `aegis_require_lib "${SCRIPT_DIR}/lib/<lib>.sh"` へ置換。ask hook も deny に倒す（方針1）。
- [ ] **Step 4**: `tests/test_safety_fallback_identity.py` の対象集合を全 12 hook へ拡張。
- [ ] **Step 5（GREEN 確認）**: `pytest tests/test_hook_emit_failclosed.py tests/test_safety_fallback_identity.py -v` PASS。
- [ ] **Step 6（後退ゼロ）**: 各対象 hook の**正常系**（emit.sh 存在時の deny/ask/allow）が不変であることを既存 hook テスト＋手動 1 ケースで確認。`pytest tests/ -q` フル green。
- [ ] **Step 7**: `safety.sh` コメントを実集合に更新。commit（`-F`）。

**注意**: `check-tdd.sh` は corruption 時 deny で「全 Edit/Write をブロック」になる（full profile のみ）。corrupt install では正しい挙動だが、plan レビューで UX を確認すること。

### Task A2: standard profile で moat hook の登録を required 化

**背景（確定）**: `check_framework_contract.py:451` は `required_hook_scripts`（standard=3）の登録のみ検査。`hooks_include`（10）の moat hook（control-plane/destructive/secrets/deploy-gate）登録を消しても PASS＝登録ドリフト無検出。

**Files:**
- Modify: `templates/profiles/standard.json`（`required_hook_scripts` に moat 4 hook を追加: `hooks/check-control-plane.sh`, `hooks/check-destructive.sh`, `hooks/check-secrets.sh`, `hooks/check-deploy-gate.sh`）
- Test: `tests/test_profile_moat_registration.py`（**新規** or 既存 `test_profile_checker_parity.py` に追加）

- [ ] **Step 1（RED）**: 一時 scaffold（`--profile=standard`）を作り settings から moat hook 登録を1つ削除 → `check_framework_contract.py --profile=standard --root <t>` が rc≠0＋`missing hook registration` を出すことを assert（現状 PASS で FAIL）。
- [ ] **Step 2**: RED 確認。
- [ ] **Step 3（GREEN）**: `standard.json` の `required_hook_scripts` に moat 4 hook を追加。`recommended` からは外さない（ファイル存在は別検査）。
- [ ] **Step 4**: GREEN 確認＋`make example` 等のミラー差分ゼロ・`pytest tests/ -q` フル green。
- [ ] **Step 5**: commit（`-F`）。

---

## Batch B: machinery 真実性（緑＝本物に戻す・TDD）

### Task B1: vacuous な full-scaffold safety テストを実効化

**背景（確定）**: `test_safety_lib_registered_in_profiles.py:89-97` は safety.sh 削除後 `--profile=full --root` で rc≠0 を期待するが、`check_framework_contract.py:481-488` が `--profile=full --root` を**常に** ERROR で rc=1 にするため、safety.sh の有無に関係なく通る＝偽の安心。

**Files:**
- Modify: `tests/test_safety_lib_registered_in_profiles.py:89-97`

- [ ] **Step 1**: テストを `--profile=standard --root <target>` に変更（safety.sh は standard の `required`＝削除で「missing required file: hooks/lib/safety.sh」で正しく FAIL）。さらに**安全側の二重化**: 削除前に同じ standard 検査が PASS することも assert し、「削除が原因で FAIL」を因果的に固定。
- [ ] **Step 2**: 変更後テスト実行で PASS、かつ「safety.sh を消さない版では PASS」を確認（テストが本当に safety.sh 削除を捉えていることを実証）。
- [ ] **Step 3**: commit（`-F`）。

### Task B2: clean-tree で DRILL BLOCKED を出す e2e

**背景（確定）**: `run-test-strength-drill.py` は working-tree が空のとき全 mutant が `added` 外で「DRILL BLOCKED（anti-gaming）」＝fail-closed。だが `test_test_strength_drill.py:152-159` は `added_lines_by_file=={}` の単体のみで、`run_drill` の orchestration を e2e で固定していない。

**Files:**
- Modify/Add: `tests/test_test_strength_drill.py`

- [ ] **Step 1（RED 不要・gap 埋め）**: clean な一時 git repo＋`.drill` spec を与え `run_drill(...)` を呼び、出力に `DRILL BLOCKED` が含まれ非緑であることを assert する e2e を追加。
- [ ] **Step 2**: 実行 PASS。`run_drill` の戻り/出力契約が現実装と一致することを確認（不一致なら現実装を正とし assert を合わせる）。
- [ ] **Step 3**: commit（`-F`）。

### Task B3: missing-ref テストに rc 検証を追加

**背景（確定）**: `test_check_status.py:2497-2503`（`test_approved_gate_missing_file_violates`）は出力に `EVIDENCE:` を確認するが `rc==1` を未検証（`:2485` は rc も見る）。exit code 退行を取りこぼす。

**Files:**
- Modify: `tests/test_check_status.py:2497-2503`

- [ ] **Step 1**: 当該テストに `self.assertEqual(rc, 1, ...)`（`:2485` と同形）を追加。
- [ ] **Step 2**: PASS 確認。commit（`-F`）。

### Task B4: ~~phase↔gate 後方検査~~ → **本 iteration から削除（Batch E へ繰延）**

**grill-plan 判断（YAGNI＋ロジック不全）**: 当初案「phase index ≥ 最高 approved gate index」は、動機ケース（iteration 33 の security 承認＋phase=security ＝**同値**）を**捕まえられない**。真に捕えるべきは「type に必要な全 gate approved ⇒ phase∈{deploy,ship,docs}/idle」。加えて bugfix の n/a・size-skip・gate 承認直後の過渡状態で**誤検出**が出やすく、nudge 疲労を悪化させうる（「自己整合機械の儀式化」というレビュー自身の警告に該当）。低ハーム（next_action が実態を明示）。
**→ 即時のドリフトは Task 0 で phase を正す対応に留め、自動カップリング検査は advisory-only で別途ちゃんと設計（Batch E）。**

---

## Batch C: install 正しさ（TDD）

### Task C1: baseline commit を実コピー path に限定

**背景（確定）**: `bin/setup.sh:382` がトップ階層を**ディレクトリ単位**で `git add`。fresh repo に既存 `docs/user-note.md` があれば baseline に混入（OBS-017 の「scoped add」意図がディレクトリ粒度に留まる）。

**Files:**
- Modify: `bin/setup.sh`（`create_framework_baseline` ＋ copy 経路: `copy_file`/`copy_hooks`/`generate_settings`/version stamp/gitignore が **実際に書いた dest rel_path** をグローバル配列 `INSTALLED_PATHS` に蓄積し、baseline はそれだけを stage）
- Test: `tests/test_setup_baseline.py`（既存に追加）

- [ ] **Step 1（RED）**: 一時 dir に `docs/user-note.md`（pre-existing）を置き `git init`（commit 0）→ `setup.sh --profile=minimal` 実行 → baseline commit の `git show --stat HEAD`（or `git ls-tree -r --name-only HEAD`）に `docs/user-note.md` が**含まれない**ことを assert（現状含まれて FAIL）。同時に framework ファイル（CLAUDE.md 等）は含まれることを assert。
- [ ] **Step 2**: RED 確認。
- [ ] **Step 3（GREEN）**: `INSTALLED_PATHS=()` を導入。`copy_file` 成功時に dest rel_path を append（既存呼び出し全経路をカバー）。`copy_hooks`・`generate_settings`（`.claude/settings.local.json`）・version stamp（`.claude/.aegis-install-version`）・`ensure_target_gitignore`（`.gitignore`）・`docs/decisions` も append。`create_framework_baseline` は配列を受け取り `git add -- "${INSTALLED_PATHS[@]}"`。ハードコードのディレクトリ列挙を撤去。空配列ガード維持。
- [ ] **Step 4**: GREEN 確認。既存 baseline テスト（fresh-only・既存リポ no-op・identity fallback）が後退しないことを確認。
- [ ] **Step 5**: `pytest tests/test_setup_baseline.py tests/test_setup_distribution.py -q` PASS。commit（`-F`）。

---

## Batch D: ドキュメント真実性（低リスク）

### Task D1: README の profile 数字と guarantee 表現を是正

**背景（確定）**: README:167 は「minimal 4 core / standard 15 required + 8」だが実際は minimal `required`=**8**、standard `required`=**18**/`recommended`=8。README:95 の "deterministic hooks-as-guarantees … cannot give the same guarantee" は **Bash 面で過大**（`python3 -c` 構築パスは SF-004 で素通り＝原理的限界。Edit/Write 面のみ真の決定論）。

**Files:**
- Modify: `README.md:167`（数字）, `README.md:95`（guarantee 限定）
- Test: `tests/test_readme_profile_counts.py`（**新規**・再 stale 防止: profiles JSON から数えて README と機械突合）

- [ ] **Step 1（RED）**: profiles JSON の `required`/`recommended` 件数を読み、README の該当数字と一致を assert するテストを追加（現状 4/15 で FAIL）。
- [ ] **Step 2**: RED 確認。
- [ ] **Step 3（GREEN）**: README:167 を「minimal (8 required), standard (18 required + 8 recommended)」へ。README:95 を「層1＝閾値を上げる静的層。Bash 面は SF-004 の原理的限界がある（`docs/security-followups.md` 参照）。決定論的“保証”は path ベースの Edit/Write moat に限る」と限定。
- [ ] **Step 4**: GREEN＋`pytest tests/ -q` フル green。
- [ ] **Step 5**: commit（`-F`）。

### Task D2: check-secrets の scope を明記

**背景（確定）**: `check-secrets.sh` は secret **ファイル名**ゲート（`.env`/`id_*`/`*.pem`/`credentials*.json`）で内容スキャナではない（`echo "AKIA…" > config.yaml` は allow）。名称が広く読める。

**Files:**
- Modify: `hooks/check-secrets.sh`（先頭コメントに scope 明記）, `README.md`（hook 説明行に「ファイル名ベース」を一語）

- [ ] **Step 1**: コメント追記のみ（挙動不変）。`pytest tests/test_secrets_* -q` PASS で後退ゼロ確認。commit（`-F`）。

---

## バージョン＆クローズアウト

### Task V1: version bump と STATUS 反映
- [ ] `1.12.0 → 1.12.1`（PATCH）を contract 定数・`templates/STATUS.template.md`・`docs/STATUS.md`・install version stamp 経路で同期。`pytest tests/ -q`＋`check_framework_contract.py --profile=full`＋`run_eval.py --tier 1` PASS。

### ゲート（フルゲート・iteration 34）
- review（盲検 break-attempt 含む）→ qa（証拠）→ security（**A1/A2 は moat ゆえ必須**・盲検2次）→ deploy。各ゲートは `docs/qa-reports/` に証拠、`bash scripts/update-gate.sh <gate> approve` はユーザー明示承認で。

---

## Self-Review（spec 突合）

- **網羅**: 外部 E1→C1, E2→A1（**6 hook へ拡張**）, E3→A2, E4→B1, E5→D1。内製 M1→D1, M2→B4＋Task0, M5→B2, M6→B3, M9→D2。✅
- **範囲外（別計画）**: M3/M4（model 方針・version-sync 集約）と P3 群（M7 STATUS.md tool 非対称, M8 `.git/`, M10 `${#…[@]}`, M11 ALL_CHECKS 結合, M12 test env 依存）＝Batch E。戦略「案A immutable moat PoC」「ターゲットユーザー検証」も別タスク。
- **TDD**: 挙動変更タスク（A1/A2/B1-B4/C1/D1）は全て RED→GREEN を明記。D2 はコメントのみ＝後退ゼロ確認。
- **placeholder 無し**: 各タスクに exact file・exact 検査観点。実コードは TDD ステップで実装（フレームワークの implementer 経路）。
- **依存順**: Batch 0 →（A,B,C,D は相互独立・並行可）→ V1 → gates。A1 は安全境界ゆえ最初に着手推奨。
