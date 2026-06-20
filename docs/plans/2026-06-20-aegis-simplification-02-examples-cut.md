# examples ミラー廃止（抽出→撤去）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development（タスクごとにフレッシュ subagent＋レビュー）。Steps はチェックボックスで追跡。
>
> 正典設計: `docs/plans/2026-06-20-aegis-simplification-design.md`（判定#1）。簡素化5ワークストリームの**第2**。**本簡素化で唯一 blast radius が大きい工程＝最大の注意**。承認済み実装方針 A/B/C（2026-06-20）に従う。

**Goal:** `examples/minimal-project` byte ミラー（99ファイル/約11k行）と同期機械（sync/drift/contract/専用テスト）を撤去する。配布前の先行投資かつ作者のみの保守負債で、ユーザーのプロダクト価値ゼロ（親基準 No）。

**Architecture:** ミラーは隠れて3役を兼ねる——(1) `bin/setup.sh` の scaffold-safe コマンド source、(2) `eval_scaffold_smoke` の byte 参照、(3) 3つの hook テストの「フル install 見本」fixture。撤去の前に各 consumer を `templates/` へ付け替え、実 install 検証（`eval_scaffold_smoke` は既に setup.sh で temp へ実 scaffold している＝良い検証）を残す。consumer 付替え（examples/ 温存）→ ミラー＆機械撤去、の順で**各タスク境界を緑**に保つ。

**Tech Stack:** bash（setup.sh）/ Python 3・pytest / git。

**前提:** カレント＝framework root。`python3 -m pytest -q` で全テスト。M3（層1＋層2）は撤去済み・ALL_CHECKS=14。

---

## File Structure

**新規（scaffold-safe コマンドの正規の住所）:**
- Create: `templates/commands/validate.md`（examples 版の copy）
- Create: `templates/commands/retro.md`（examples 版の copy）

**変更:**
- `bin/setup.sh` — `resolve_source()` の validate.md/retro.md 参照を examples/ → `templates/commands/`
- `scripts/eval_scaffold_smoke.py` — `verify_command_surface()` の `example_root` を `templates/commands/` へ／import 名更新／フル install の「template hook ⊆ 実 scaffold settings」検証を追加（test から移設）
- `scripts/check_reference_drift.py` — `MIRROR_DIRS`/`MIRROR_FILES`/`check_mirror_identity`/`check_example_readme_counts`/`check_example_commands` と ALL_CHECKS の3エントリ削除。`MIRROR_ALLOWLIST` は `SCAFFOLD_SAFE_COMMANDS` に改名して存続（eval が利用）
- `scripts/check_framework_contract.py` — `REQUIRED_EXAMPLE_FILES`（177-約258行・81エントリ）と利用2箇所（591・977行）削除。`templates/commands/{validate,retro}.md` を `REQUIRED_TEMPLATE_FILES` に追加
- `tests/test_hook_required_coverage.py` — B-2（example⊆REQUIRED_EXAMPLE）と example fallback-form を削除、「template hook ⊆ example」は eval の実 scaffold 検証へ移設（本ファイルからは削除）、残り（B-1・ScriptRelFromCommand・template fallback-form）は維持
- `tests/test_session_start_matcher.py` — `EXAMPLE` を `templates/hooks.template.json` へ repoint
- `tests/test_hook_timeout_declared.py` — `TEMPLATES` から example settings エントリを除去（hooks.template.json 検査は維持）
- `docs/architecture-overview.md` — ドリフト数 14→11・mirror-identity 文言除去（L407）・ミラー説明（L488 付近）・ディレクトリツリーの examples 行（L58 付近）・§15 scripts 数（→13）
- `Makefile` — `example` ターゲット削除
- `README.md` — examples/ 参照（ツリー・`make example`・`--root examples/minimal-project`）除去

**削除:**
- `examples/minimal-project/`（99ファイル）
- `scripts/sync_example_mirror.py`
- `tests/test_mirror_identity.py`・`tests/test_sync_example_mirror.py`

---

### Task 1: ベースライン確認

- [ ] **Step 1: 全テスト緑を確認**

Run: `python3 -m pytest -q`
Expected: 全 PASS。総数をメモ。

- [ ] **Step 2: ALL_CHECKS=14 を確認**

Run: `python3 -c "import re,pathlib; s=pathlib.Path('scripts/check_reference_drift.py').read_text(encoding='utf-8'); b=re.search(r'ALL_CHECKS = \[(.*?)\]', s, re.S); print(b.group(1).count('(\"'))"`
Expected: `14`

- [ ] **Step 3: 実 scaffold smoke が緑を確認（後の回帰基準）**

Run: `python3 scripts/eval_scaffold_smoke.py`（または `make` 経由の該当 tier）
Expected: 全 profile PASS。

---

### Task 2: scaffold-safe コマンドを templates/ へ抽出し consumer を付替え（examples/ は温存）

> **copy であって move ではない**：examples/ から `git mv` すると `REQUIRED_EXAMPLE_FILES`（validate.md/retro.md の存在を要求）と `check_example_commands` が即 FAIL する。examples/ を温存したまま正規の住所を増やし consumer を付替える。examples/ 本体の撤去は Task 4。

- [ ] **Step 1: テンプレート住所を作成**

`templates/commands/` を作り、現 `examples/minimal-project/.claude/commands/validate.md` と `retro.md` の**内容をそのまま** `templates/commands/validate.md`・`templates/commands/retro.md` にコピーする（scaffold-safe 版＝validate は `check_status.py` 実行、retro は retro_report.py 不在時の graceful guard 「`scripts/retro_report.py` is available」を含む）。

- [ ] **Step 2: setup.sh の resolve_source を付替え**

`bin/setup.sh` の case を変更:
```bash
    ".claude/commands/validate.md")
      echo "$FRAMEWORK_ROOT/templates/commands/validate.md"; return ;;
    ".claude/commands/retro.md")
      # Scaffold-safe variant: degrades gracefully when retro_report.py is absent.
      echo "$FRAMEWORK_ROOT/templates/commands/retro.md"; return ;;
```

- [ ] **Step 3: contract に新住所を必須登録**

`scripts/check_framework_contract.py` の `REQUIRED_TEMPLATE_FILES` に追加:
```python
    ROOT / "templates/commands/validate.md",
    ROOT / "templates/commands/retro.md",
```

- [ ] **Step 4: eval の byte 参照を templates/ へ付替え**

`scripts/eval_scaffold_smoke.py:306` の参照元を変更（`example_root` → templates/commands を指す）:
```python
    command_source = REPO_ROOT / "templates" / "commands"
```
ループ内 `example = example_root / rel` を `source = command_source / rel.name`（rel は `.claude/commands/validate.md` 形なので basename を使う）に修正し、エラーメッセージの "example variant" を "scaffold-safe template variant" に更新。`retro_guard` チェックは不変で維持。

- [ ] **Step 5: 検証（緑のまま）**

Run: `python3 -m pytest -q`
Expected: 全 PASS（examples/ も REQUIRED_EXAMPLE_FILES も健在＝既存テストは緑、新 templates/commands も contract 必須化で存在）。

Run: `python3 scripts/eval_scaffold_smoke.py`
Expected: 全 profile PASS（scaffold 出力＝templates/commands/ と一致）。

- [ ] **Step 6: コミット**（メッセージは `git commit -F <file>`／パスはクォート）

`refactor(simplification): relocate scaffold-safe commands to templates/ (examples cut 準備)`

---

### Task 3: fixture テストを templates/ へ付替え・再設計（examples 参照を test から除去）

- [ ] **Step 1: test_session_start_matcher を repoint**

`tests/test_session_start_matcher.py` の `EXAMPLE = ROOT / "examples"/...settings.json` を `ROOT / "templates" / "hooks.template.json"` に変更。SessionStart matcher が4イベント（startup/resume/clear/compact）を覆う検証は維持（hooks.template.json の hooks ブロックを同じ抽出で読む。構造差があればパースを合わせる）。

- [ ] **Step 2: test_hook_timeout_declared を repoint**

`tests/test_hook_timeout_declared.py` の `TEMPLATES` リストから `examples/.../settings.json` エントリを削除（`templates/hooks.template.json` の PreToolUse timeout 5-60 検証は維持）。

- [ ] **Step 3: test_hook_required_coverage を再設計**

`tests/test_hook_required_coverage.py`:
- **削除** `test_example_registered_hooks_are_in_required_example_files`（B-2：example settings⊆REQUIRED_EXAMPLE_FILES。両辺撤去）。
- **削除** `test_example_settings_commands_use_fallback_form`（example settings の form 検査。template 版 `test_template_commands_use_fallback_form` が同等を担保）。
- **移設** `test_template_registered_hooks_are_registered_in_example`（template hook ⊆ example settings＝フル install で観測系 hook 欠落を防ぐ E1 不変条件）→ Task3 Step4 で eval の**実 full scaffold**検証に移す。本ファイルからは削除。
- **維持** B-1（template⊆REQUIRED_HOOK_FILES）・`TestScriptRelFromCommand`・`test_template_commands_use_fallback_form`。

- [ ] **Step 3b: test_phase_skills_required.py の example 結合を除去（grill-plan 致命#1）**

`tests/test_phase_skills_required.py`:
- **削除** `test_example_mirror_phase_skills_in_required_example_files`（:67-73。REQUIRED_EXAMPLE_FILES 依存）。
- **削除** `test_example_mirror_secrets_patterns_in_required_example_files`（:75-82。同上）。
- `test_phase_skills_sh_actually_exists`（:84-92）から **examples 存在 assert（:89-92）のみ削除**し、root の `hooks/lib/phase-skills.sh` 存在 assert（:84-88）は維持。
- **維持** root 側（`*_in_required_hook_files`＝REQUIRED_HOOK_FILES 対応）。

- [ ] **Step 4: 移設先＝eval の full scaffold に E1 不変条件を追加**

`scripts/eval_scaffold_smoke.py` の full profile 検証（:455 付近）に、実 scaffold した `target/.claude/settings.local.json` の登録 hook 集合 ⊇ `templates/hooks.template.json` の登録 hook 集合、を検証する関数を追加（不足は FAIL）。＝「フル install が template の全 hook を実装する」を*実 install で*担保（旧 test の意図を実体で再現）。

- [ ] **Step 5: 検証（緑のまま）**

Run: `python3 -m pytest -q`
Expected: 全 PASS。Task1 から減るのは：hook_required_coverage の2（B-2＋example fallback-form）＋phase_skills の2（example_mirror_*）＝計4テスト分。`test_template_registered_hooks_are_registered_in_example` は eval 側へ移行（test 数は実質 -1、eval は CLI 検証で pytest 件数には乗らない）。**この時点で `tests/` の examples 参照はゼロ**（残るは Task4 撤去対象の機械のみ: drift/contract/sync/Makefile/README）。

Run: `python3 scripts/eval_scaffold_smoke.py`
Expected: 全 profile PASS（新 E1 不変条件含む）。

- [ ] **Step 6: コミット**

`refactor(simplification): repoint hook fixtures off examples mirror (examples cut 準備)`

> この時点で **examples/ を参照するのは「撤去対象の機械のみ」**（mirror identity / example checks / REQUIRED_EXAMPLE_FILES / sync / Makefile / README）。

---

### Task 4: ミラー本体・同期機械・examples/ を撤去（最大 blast radius）

- [ ] **Step 1: drift から example 系3チェックと MIRROR 定義を除去**

`scripts/check_reference_drift.py`:
- 関数 `check_mirror_identity`・`check_example_readme_counts`・`check_example_commands` を削除。
- ALL_CHECKS から該当3エントリ（"example README counts"・"example commands"・"mirror identity"）を削除（14→11）。
- `MIRROR_DIRS`・`MIRROR_FILES` 定義を削除。
- `MIRROR_ALLOWLIST` を `SCAFFOLD_SAFE_COMMANDS` に改名（中身＝`.claude/commands/validate.md`・retro.md）。eval の import（:33）も新名に更新。

- [ ] **Step 2: contract から REQUIRED_EXAMPLE_FILES を除去**

`scripts/check_framework_contract.py`:
- `REQUIRED_EXAMPLE_FILES` ブロック（177-約258行）を削除。
- 利用2箇所（:591 の存在ループの連結、:977 のループ）から `REQUIRED_EXAMPLE_FILES` を除去。

- [ ] **Step 3: ファイル・ターゲット撤去**

Run（パスはクォート）:
```bash
git rm -r "examples/minimal-project"
git rm "scripts/sync_example_mirror.py" "tests/test_mirror_identity.py" "tests/test_sync_example_mirror.py"
```
`Makefile` の `.PHONY` から `example` を外し `example:` ターゲット2行を削除。`README.md` の examples 参照（ディレクトリツリー行・`make example` 節・`--root examples/minimal-project` 記述）を除去。

- [ ] **Step 4: full suite を走らせ、期待される失敗集合を確認**

Run: `python3 -m pytest -q`
Expected RED（**唯一・想定内**）: `tests/test_arch_overview_currency.py` のドリフト件数（"claims 14 ... ALL_CHECKS = 11"）の1件のみ。grill-plan 実証で `check_readme_counts` は examples 非依存・test 側の examples 参照は Task3 で除去済みのため、他の RED は出ない想定。**currency 以外が1件でも RED なら STOP して報告**（examples への隠れ依存の最終網）。

- [ ] **Step 5: arch-overview と README 件数を同期（GREEN へ）**

`docs/architecture-overview.md`:
- L407 を 11 に、`本体↔example の mirror-identity を byte 比較。` 句を削除（残: platform_manifest…staleness を含む）。
- ミラー説明（L488 付近「本体とは制御ファイルが byte 一致でミラー…」）・ディレクトリツリーの examples 行（L58 付近）を削除。
- §15 ファイル数サマリ: scripts 行を 13 に、example 行があれば削除。
README の件数・ツリーを実体に合わせる。Step 4 で出た想定内 RED が全て解消するまで修正。

Run: `python3 -m pytest -q`
Expected: 全 PASS。

- [ ] **Step 6: dangling 参照ゼロを確認**

Run（クォート）:
```bash
grep -rn "minimal-project\|sync_example_mirror\|check_mirror_identity\|REQUIRED_EXAMPLE_FILES\|MIRROR_DIRS\|MIRROR_FILES" --include='*.py' --include='*.sh' --include='*.json' --include='Makefile' .
```
Expected: 出力なし（0件）。docs の歴史記述はワークストリーム5で掃除。

Run: `python3 scripts/eval_scaffold_smoke.py`
Expected: 全 profile PASS（実 install 経路は templates/ ベースで健全）。

- [ ] **Step 7: ステージ確認 → コミット ＋ Aegis ゲート**

Run: `git status --short`
Expected: examples/minimal-project 配下の大量 `D`＋`sync_example_mirror.py`/`test_mirror_identity.py`/`test_sync_example_mirror.py` の `D`＋`check_reference_drift.py`/`check_framework_contract.py`/`eval_scaffold_smoke.py`/`Makefile`/`README.md`/`docs/architecture-overview.md`/各 test の `M`。想定外の path が混ざっていないか目視。

メッセージは `Write` で作成し `git commit -F <file>`（シェル glitch 回避・パスはクォート）:
`refactor(simplification): remove examples/minimal-project byte-mirror (examples cut)`

その後 `docs/STATUS.md` の phase/current_refs/failure_tracking 更新＋`review` ゲートへ。

---

## Self-Review

- **Spec coverage:** 設計#1（抽出→撤去）と方針 A/B/C を完全実装。3役（runtime source・byte 参照・fixture）を templates/＋実 scaffold smoke へ移し、ミラー＋機械を撤去。
- **green-between-tasks:** consumer 付替え（Task2/3・examples 温存）→ 機械撤去（Task4）の順。Task4 内の RED は currency/README 件数で、同タスクで GREEN 化。**copy-then-delete** で REQUIRED_EXAMPLE_FILES 途中割れを回避。
- **隠れ結合の処理:** `test_hook_required_coverage` は単純 repoint 不可（example settings＋REQUIRED_EXAMPLE_FILES 両依存）→ 削除2＋eval 実 scaffold へ移設1。`MIRROR_ALLOWLIST`→`SCAFFOLD_SAFE_COMMANDS` 改名で eval 利用を存続。`test_arch_overview_currency` 14→11 を RED→GREEN 証拠に。
- **検証の質向上:** byte ミラー（自己整合機械）→ 実 scaffold smoke（実 install 経路）に検証の重心が移る＝North Star の「良い検証」。
- **Placeholder:** 行番号は撤去で動くため symbol 名で指定（implementer が現コードを読む）。新規/変更の小コードは明示。
- **スコープ外:** docs 歴史記述（旧 plan/spec/qa-reports・STATUS メモ）はワークストリーム5。難読化 moat はスコープ外。

## 注記（grill-plan 反映済み・2026-06-20）
- **致命#1 解消**: `test_phase_skills_required.py` の examples 結合（example_mirror 2メソッド＋存在 assert 1行）を Task3 Step3b で除去。これで Task4 の期待 RED は currency 1件に絞れた。
- **実証で確認済み**: `check_readme_counts` は examples 非依存（Task4 の RED は currency のみ）／`hooks.template.json` は SessionStart matcher `startup\|resume\|clear\|compact` を持つ（Task3 Step1 repoint 可能）／`tests/`・`scripts/`・`bin/`・`Makefile` の examples 参照は11ファイルで Task で全網羅。
- **実装時の注意（残）**: eval の rel basename 取り回し（`.claude/commands/validate.md` → `validate.md`）／`test_session_start_matcher` の hooks.template.json パース微調整（hooks ブロック形は settings.json と同形＝SessionStart 配列の matcher を読む）。
- Task4 Step4 の「currency 以外が1件でも RED なら STOP」＝隠れ依存の最終網は維持。
