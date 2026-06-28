# allow-list read-only 完全性ガード＋拡張 実装計画

> **For agentic workers:** TDD（テスト→FAIL→最小実装→PASS→commit）。Steps は checkbox。

**Goal:** iter51 で漏れた read-only framework スクリプト（3 件）と安全 git-read（`git show`）を `permissions.allow` に追加し、併せて「全 scripts が分類済・安全系のみ allow・状態変更/exec 系は allow から排除」を強制する分類駆動の完全性ガードを足して drift を防ぐ。

**Architecture:** production code 無改変。`templates/hooks.template.json` の `permissions.allow` にエントリ追加 ＋ 既存 `tests/test_permission_allowlist_install.py` に分類表（`SCRIPT_CLASS`）と完全性ガード 6 アサーションを追記。`generate_settings()` は既に template の allow を全 profile 配布するため改変不要。

**Tech Stack:** Python 3 / pytest / JSON（Claude Code settings）。

---

## 目的

- read-only スクリプトの無意味な確認を全プロファイルで消す（author 一次痛＋North Star）。
- スクリプト追加時に allow が drift しない監査可能な契約を敷く（iter49/50 と同型の参照整合性ガード）。

## 入力

- 参照要件: なし（internal framework iteration・requirements=[]）
- 参照設計: `docs/specs/2026-06-28-permission-allowlist-completeness-design.md`

## Deploy Target（必須）

### プラットフォーム
- Hosting: n/a（フレームワーク内部変更・配布物のみ）
- Database: n/a
- CI/CD: n/a

### 互換性確認
- next.config `output` 設定: n/a（Web アプリではない）
- デプロイ先と互換: Yes（デプロイ無し。M ＝ deploy ゲット size-exempt）

### 認証方式
- 認証プロバイダ: None
- DEMO_MODE: n/a

## Git 戦略

main 直コミット（既存フロー・iter49-51 と同様）。feature branch 不要（単一 author・小規模 framework iteration）。

**重要（commit timing・grill 致命1）**: implement 中は **commit しない**。review/qa/security は**未コミット作業ツリー**で実施する — 特に qa の **B1 drill は未コミット diff（`hooks.template.json` の追加 allow 行）を mutate** するため、早期 commit するとドリル不能になる。feat commit は **ship フェーズで 1 回**（全必須ゲート approved 後）。

## ファイル構造（変更マップ）

- 変更: `templates/hooks.template.json` — `permissions.allow` に 4 エントリ追加（read-only スクリプト 3 件＋`git show`）。
- 変更: `tests/test_permission_allowlist_install.py` — `SCRIPT_CLASS` 分類表＋完全性ガード 6 テスト＋既存「real invocations」集合に新コマンド追記。
- 変更: `README.md` — allow-list 節（件数 10→15、完全性ガードの存在を 1-2 行）。
- 無改変: `bin/setup.sh`（generate_settings は既に template allow を全 profile 配布）、production scripts/hooks 一切。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `SCRIPT_CLASS` 分類表＋完全性ガード 6 テスト（RED） | `_template_allow`, `_matches`（既存ヘルパー）, `scripts/` 実体 |
| Task 2 | `hooks.template.json` allow 4 エントリ追加（GREEN 化） | Task 1 のテスト |
| Task 3 | README allow 節更新 | Task 2 の最終 allow |

循環なし。Task 1 の Consumes（`_template_allow`/`_matches`）は既存ファイルに存在（line 45/50）。

## 分類表（確定・各 1 行根拠）

intent ベース分類（mechanism ではない）。`safe_auto_allow`＝pure reader か benign idempotent generator で、**arg/stdin 制御コマンドを実行しない**・risky な repo state mutation 無し → allow 必須。`must_prompt`＝state 変更 or exec gadget or scaffold/eval → allow 禁止。`not_cli`＝import 専用モジュール。

- `check_status.py` = safe_auto_allow（fixed-internal subprocess のみ・状態読取）
- `check_framework_contract.py` = safe_auto_allow（lint を fixed subprocess 実行・読取）
- `status_doctor.py` = safe_auto_allow（STATUS 読取診断）
- `retro_report.py` = safe_auto_allow（git log を fixed subprocess・読取集計）
- `build-judge-card.py` = safe_auto_allow（fixed-internal subprocess・evidence 再生成は冪等・iter51 security で gadget 不在確認済）
- `check_reference_drift.py` = safe_auto_allow（**iter52 新**・全パス sink 無し確認済）
- `learnings_search.py` = safe_auto_allow（**iter52 新**・全パス sink 無し確認済）
- `lint_names.py` = safe_auto_allow（**iter52 新**・全パス sink 無し確認済）
- `context_budget.py` = must_prompt（**grill-code 🔴 で再分類**：`check` は読取だが `--tighten`/`--seed` が追跡対象 `scripts/context-budgets.json` を書込む・blanket matcher で除外不能）
- `record-test-result.py` = must_prompt（`args.command` を実行＝exec gadget）
- `run-test-strength-drill.py` = must_prompt（mutation を subprocess 実行）
- `run_eval.py` = must_prompt（eval を subprocess 実行）
- `eval_scaffold_smoke.py` = must_prompt（scaffold＋install を subprocess 実行）
- `eval_scenario.py` = must_prompt（eval CLI・`__main__` あり・scenario 実行をオーケストレーション）
- `update-gate.sh` = must_prompt（STATUS＋snapshot 変更）
- `update-task.sh` = must_prompt（STATUS＋snapshot 変更）
- `_artifact_template_map.py` = not_cli（import 専用）
- `platform_manifest.py` = not_cli（import 専用・定数）

安全 git-read 固定集合（allow 必須）: `git status` / `git log` / `git diff` / `git show`。除外: `git branch`/`git remote`/`git checkout`（destructive 副形 `-D`/`remove`/`checkout .` を broad rule が拾うため）。

## タスク分解

### タスク 1: 分類駆動の完全性ガードを追加（RED）

**blockedBy:** なし | **モデル:** inherit
**ファイル:** `tests/test_permission_allowlist_install.py`
**意図:** 分類表＋6 アサーションを追記。allow 拡張前なので safe_auto_allow の新 3 件が未 allow ＝ RED になる。

- [ ] **Step 1: 分類表とヘルパー、6 テストを追記**

```python
# --- iter52: allow-list completeness guard (classification-map driven) ---
SCRIPTS_DIR = ROOT / "scripts"

# Every scripts/ CLI entrypoint classified by INTENT. A new file absent here
# trips test_every_script_is_classified (anti-drift). See plan for criteria.
SCRIPT_CLASS = {
    "check_status.py": "safe_auto_allow",
    "check_framework_contract.py": "safe_auto_allow",
    "status_doctor.py": "safe_auto_allow",
    "retro_report.py": "safe_auto_allow",
    "build-judge-card.py": "safe_auto_allow",
    "check_reference_drift.py": "safe_auto_allow",
    "learnings_search.py": "safe_auto_allow",
    "lint_names.py": "safe_auto_allow",
    "context_budget.py": "must_prompt",  # grill-code 🔴: --tighten/--seed write a tracked config
    "record-test-result.py": "must_prompt",
    "run-test-strength-drill.py": "must_prompt",
    "run_eval.py": "must_prompt",
    "eval_scaffold_smoke.py": "must_prompt",
    "eval_scenario.py": "must_prompt",
    "update-gate.sh": "must_prompt",
    "update-task.sh": "must_prompt",
    "_artifact_template_map.py": "not_cli",
    "platform_manifest.py": "not_cli",
}

SAFE_GIT_READS = ["git status", "git log", "git diff", "git show"]
DESTRUCTIVE_GIT = ["git branch -D x", "git remote remove origin", "git checkout ."]


def _enumerated_scripts():
    return {p.name for p in SCRIPTS_DIR.glob("*.py")} | \
           {p.name for p in SCRIPTS_DIR.glob("*.sh")}


def _allow_targets_script(entry, name):
    # name-mention check — used by the NEGATIVE/orphan tests where we want to
    # catch ANY allow entry that references a must_prompt/not_cli script.
    return f"scripts/{name}" in entry


def _rep_invocation(name):
    # representative real invocation, used by the POSITIVE membership test so we
    # prove the script is actually auto-allowed (a malformed entry lacking `:*`
    # name-mentions but does NOT auto-allow `... <args>`).
    return f"python3 scripts/{name} x"


def test_every_script_is_classified():
    enum = _enumerated_scripts()
    missing = enum - set(SCRIPT_CLASS)
    assert not missing, f"unclassified scripts/ entrypoints: {sorted(missing)}"
    stale = set(SCRIPT_CLASS) - enum
    assert not stale, f"SCRIPT_CLASS lists non-existent scripts: {sorted(stale)}"


def test_safe_auto_allow_scripts_are_allowed():
    allow = _template_allow()
    for name, cls in SCRIPT_CLASS.items():
        if cls == "safe_auto_allow":
            assert any(_matches(e, _rep_invocation(name)) for e in allow), \
                f"safe_auto_allow script not actually auto-allowed: {name}"


def test_non_safe_scripts_are_not_allowed():
    allow = _template_allow()
    for name, cls in SCRIPT_CLASS.items():
        if cls != "safe_auto_allow":
            assert not any(_allow_targets_script(e, name) for e in allow), \
                f"{cls} script must NOT be auto-allowed: {name}"


def test_safe_git_reads_allowed_destructive_excluded():
    allow = _template_allow()
    for cmd in SAFE_GIT_READS:
        assert any(_matches(e, cmd) for e in allow), f"safe git read not allowed: {cmd}"
    for cmd in DESTRUCTIVE_GIT:
        assert not any(_matches(e, cmd) for e in allow), f"destructive git auto-allowed: {cmd}"


def test_no_orphan_script_allow_entry():
    safe = {n for n, c in SCRIPT_CLASS.items() if c == "safe_auto_allow"}
    for entry in _template_allow():
        m = re.search(r"scripts/([\w.-]+)", entry)
        if m:
            assert m.group(1) in safe, \
                f"allow entry targets non-safe_auto_allow script: {entry}"


def test_script_class_consistent_with_should_lists():
    # single-source guard (grill 致命3): the matcher-form lists SHOULD_MATCH /
    # SHOULD_NOT_MATCH and SCRIPT_CLASS must never disagree — otherwise a future
    # editor updates one and silently diverges.
    def _script(cmd):
        m = re.search(r"scripts/([\w.-]+)", cmd)
        return m.group(1) if m else None
    for cmd in SHOULD_MATCH:
        n = _script(cmd)
        if n:
            assert SCRIPT_CLASS.get(n) == "safe_auto_allow", \
                f"SHOULD_MATCH {cmd!r} but SCRIPT_CLASS[{n}]={SCRIPT_CLASS.get(n)}"
    for cmd in SHOULD_NOT_MATCH:
        n = _script(cmd)
        if n:
            assert SCRIPT_CLASS.get(n) == "must_prompt", \
                f"SHOULD_NOT_MATCH {cmd!r} but SCRIPT_CLASS[{n}]={SCRIPT_CLASS.get(n)}"
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest tests/test_permission_allowlist_install.py -q`
Expected: FAIL — `test_safe_auto_allow_scripts_are_allowed`（check_reference_drift 等 3 件が未 allow）＋ `test_safe_git_reads_allowed_destructive_excluded`（git show 未 allow）。

### タスク 2: allow を拡張（GREEN）

**blockedBy:** Task 1 | **モデル:** inherit
**ファイル:** `templates/hooks.template.json`
**意図:** safe_auto_allow 新 3 件＋`git show` を allow に追加し Task 1 を GREEN 化。

- [ ] **Step 1: permissions.allow に 4 エントリ追加**（context_budget は grill-code 🔴 で除外）

`templates/hooks.template.json` の `permissions.allow`（既存 10 件）に追加:

```json
    "Bash(python3 scripts/check_reference_drift.py:*)",
    "Bash(python3 scripts/learnings_search.py:*)",
    "Bash(python3 scripts/lint_names.py:*)",
    "Bash(git show:*)"
```

- [ ] **Step 2: 既存「real invocations」集合に新コマンドを追記**

`tests/test_permission_allowlist_install.py` の SHOULD-allow 集合（既存 line ~19）に追加し、`test_allow_entries_match_real_invocations` でも二重に担保:

```python
    "python3 scripts/check_reference_drift.py --root .",
    "python3 scripts/learnings_search.py --query mutation",
    "python3 scripts/lint_names.py --root .",
    "git show HEAD",
```

- [ ] **Step 3: GREEN 確認**

Run: `python3 -m pytest tests/test_permission_allowlist_install.py -q`
Expected: PASS（全テスト）。

- [ ] **Step 4: install 実体で反映を確認（JSON 妥当性＋全 profile carry）**

Run: `python3 -m pytest tests/test_permission_allowlist_install.py -q -k install`
Expected: PASS（minimal/standard/full すべてに新 allow が乗る）。

### タスク 3: README allow 節更新

**blockedBy:** Task 2 | **モデル:** inherit
**ファイル:** `README.md`
**意図:** allow-list 節の件数（10→15）と完全性ガードの存在を反映。

- [ ] **Step 1: allow-list 節を更新**（件数と「分類駆動の完全性ガードで drift を検出」を 1-2 行）
- [ ] **Step 2: フル suite で回帰確認**

Run: `python3 -m pytest -q`
Expected: PASS（既存 + 新規）。contract/status_doctor も PASS。

## トレーサビリティ（設計 → Task → Test）

| 設計項目 | Task | テスト |
|------|------|--------|
| 分類表（全 scripts 分類） | T1 | `test_every_script_is_classified` |
| read-only ⊆ allow | T1+T2 | `test_safe_auto_allow_scripts_are_allowed` |
| mutating/exec ∩ allow = ∅ | T1 | `test_non_safe_scripts_are_not_allowed` |
| 安全 git-read 固定集合 ⊆ allow / destructive 除外 | T1+T2 | `test_safe_git_reads_allowed_destructive_excluded` |
| orphan allow 無し | T1 | `test_no_orphan_script_allow_entry` |
| SHOULD リスト ↔ SCRIPT_CLASS 整合（単一真実源） | T1 | `test_script_class_consistent_with_should_lists` |
| allow 拡張（実体） | T2 | `test_allow_entries_match_real_invocations` + install e2e |
| ドキュメント | T3 | （手動）README 反映 |

## 自己レビュー

- 仕様カバレッジ: 設計 6 アサーション＋拡張＋README すべてに Task 対応。✓
- 曖昧さ: 分類基準を intent ベースで明文化（subprocess 有無ではない）。✓
- 型整合: `_allow_targets_script`/`_enumerated_scripts`/`SCRIPT_CLASS` は T1 で定義し T1 内で消費。`_template_allow`/`_matches` は既存。✓
- 境界整合: Boundary Map の Consumes は既存ヘルパー or 先行 Task 生成物。✓

## リスク

- リスク: `safe_auto_allow` に誤って exec gadget を入れる → 既存 `test_allowed_scripts_do_not_invoke_command_executor`（line 104）＋新 `test_non_safe_scripts_are_not_allowed` が二重に捕捉。fail-closed。
- リスク: 新スクリプトが将来追加され未分類のまま allow 漏れ → `test_every_script_is_classified` が RED で強制。
- リスク: `git show:*` が想定外の mutation 副形を持つ → `git show` はオブジェクト表示のみ（mutation 副形なし）。確認済。
- リスク: B1 drill（qa）で coverage floor 割れ → 追加コードは全て behavioral（membership assertion）。純コメントハンクを作らない（罠 l）。**drill 対象面＝`hooks.template.json` の追加 allow 4 行**（各行 mutant→いずれかの completeness テストが赤で捕捉）。
- リスク: README 編集が `test_readme_profile_counts.py` と干渉 → 同テストは profile 必須ファイル数のみ検査で allow 件数は非対象（prose 追記は非干渉）。実装時 full suite で確認。

## 完了条件

- [ ] 全テスト pass（新 5 ＋既存 ＋フル suite）
- [ ] contract / status_doctor PASS
- [ ] review / qa / security ゲット approved（M：deploy size-exempt）
- [ ] README 反映

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->
