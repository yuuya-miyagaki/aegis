# iter55: ドッグフード一周目フィードバック反映 — 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 許可リスト3重管理（hook case 文 / template permissions / SCRIPT_CLASS テスト map）を
`hooks/lib/scripts-manifest.tsv` 単一正本に統合し、ドッグフードで実測したゲート戦闘 7 件の
原因（allowlist 漏れ・skill/hook 契約矛盾・メタ文書ロック・stderr リダイレクト誤爆・初見殺し
メッセージ）を封鎖する。

**Architecture:** manifest（4 クラス: allow/ask/framework-only/import-only）を hook が実行時に
pure-bash で読み（fail-closed）、check_framework_contract.py が 3 方向 drift 検査で縛り、
テストの SCRIPT_CLASS は manifest 由来ローダーに置換。設計書=
`docs/specs/2026-07-03-iter55-dogfood-feedback-design.md`（正本・必読）。

**Tech Stack:** bash 3.2 互換 hook（BSD/GNU 両対応・`\s` 禁止・`[[:space:]]` 使用）、
pytest（unittest スタイル併存）、python3 標準ライブラリのみ。

## Global Constraints

- hook は pure-bash（python3 依存を持ち込まない — emit.sh の fail-open 教訓）
- 判定変更は必ず fail-closed 方向を検証するテストとセット（moat 変更）
- 迷ったら DENY（allow を広げる変更は必ず負例テストを併設）
- BSD sed 互換: `sed -E` は可・`sed -i ''` は不可・`\s` 不可
- 版数 v1.15.0 → v1.16.0（Task 10 で一括。それまで既存 pin を壊さない）
- コミットは task 単位。メッセージは `feat(iter55): ...` / `test(iter55): ...` 形式
- 実行 dir は aegis repo root（`cd <repo>/aegis`）。全テストは `python3 -m pytest -q tests/<file>`

---

### Task 1: scripts-manifest.tsv 新設 + is_allowlisted の manifest 化

**Files:**
- Create: `hooks/lib/scripts-manifest.tsv`
- Modify: `hooks/check-control-plane.sh`（L18-20 ヘッダコメント・L809-830 is_allowlisted）
- Modify: `tests/test_control_plane_allowlist.py`（harness に manifest symlink 追加）
- Test: `tests/test_scripts_manifest_hook.py`（新規）

**Interfaces:**
- Produces: `hooks/lib/scripts-manifest.tsv`（`<scripts/path>\t<class>` 形式・# コメント可）、
  hook 内関数 `manifest_script_in <cmd>`（rc0=allow∪ask エントリを含む）と
  `SCRIPTS_MANIFEST` 変数（Task 6 が再利用）

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_scripts_manifest_hook.py`

```python
#!/usr/bin/env python3
"""iter55 P0: 実行可スクリプトの allowlist は hooks/lib/scripts-manifest.tsv が単一正本。

ドッグフード一周目（2026-07-03）でゲート戦闘 7 件中 6 件が allowlist 系だった。
settings permissions（8本）と hook のハードコード case（5本）が別管理でドリフトし、
skill が指示する status_doctor.py（/recover）・retro_report.py（/retro）・
build-judge-card.py（/gate）・update-task.sh（正規の task 変更手段）を hook が deny した。

本テストは manifest の class allow|ask 全 12 本の素の単体実行 ALLOW・framework-only の
DENY・manifest 欠落時の全 DENY（fail-closed）・チェーン/リダイレクト付き DENY 維持を pin する。
Harness は tests/test_control_plane_allowlist.py と同型。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch_root(include_manifest: bool = True) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    if include_manifest:
        (lib_dir / "scripts-manifest.tsv").symlink_to(
            ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


# manifest の class allow|ask 全 12 本の代表実呼び出し形。
RUNNABLE = [
    "python3 scripts/check_status.py",
    "python3 scripts/check_framework_contract.py --profile=standard --root .",
    "python3 scripts/status_doctor.py",
    "python3 scripts/retro_report.py --root .",
    "python3 scripts/build-judge-card.py --gate review",
    "python3 scripts/check_reference_drift.py",
    "python3 scripts/learnings_search.py --query mutation",
    "python3 scripts/lint_names.py",
    "bash scripts/update-gate.sh review approve",
    "bash scripts/update-task.sh --size L",
    "python3 scripts/record-test-result.py --cmd 'pytest' --status ok",
    "python3 scripts/run-test-strength-drill.py --root .",
]

# framework-only: 対象プロジェクトでは deny のまま（framework repo は task_type=framework で素通り）
FRAMEWORK_ONLY = [
    "python3 scripts/context_budget.py check",
    "python3 scripts/run_eval.py",
    "python3 scripts/eval_scaffold_smoke.py",
    "python3 scripts/eval_scenario.py",
]


class TestManifestRunnable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_all_runnable_scripts_allowed_bare(self):
        for cmd in RUNNABLE:
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_allowed(out), f"{cmd!r} must be allowed: {out[:200]!r}")

    def test_framework_only_scripts_stay_denied(self):
        for cmd in FRAMEWORK_ONLY:
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_denied(out), f"{cmd!r} must stay denied: {out[:200]!r}")

    def test_chained_runnable_still_denied(self):
        out = _hook(self.root,
                    "bash scripts/update-task.sh --size L && rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"chain must deny: {out[:200]!r}")

    def test_redirect_runnable_still_denied(self):
        out = _hook(self.root, "python3 scripts/retro_report.py > hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"redirect must deny: {out[:200]!r}")


class TestManifestFailClosed(unittest.TestCase):
    def test_missing_manifest_denies_everything(self):
        """manifest 欠落 = 全 deny（旧ハードコード5本も含む）。fail-closed の核心 pin。"""
        with _scratch_root(include_manifest=False) as name:
            root = Path(name)
            for cmd in ("python3 scripts/check_status.py",
                        "bash scripts/update-gate.sh review approve"):
                with self.subTest(cmd=cmd):
                    out = _hook(root, cmd)
                    self.assertTrue(_denied(out),
                                    f"missing manifest must deny {cmd!r}: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest -q tests/test_scripts_manifest_hook.py`
Expected: FAIL — `status_doctor.py` / `retro_report.py` / `build-judge-card.py` /
`check_reference_drift.py` / `learnings_search.py` / `lint_names.py` / `update-task.sh`
の 7 本が deny（現行ハードコードに無い）。manifest 欠落テストも FAIL
（現行は manifest 非依存で check_status が allow される）。

- [ ] **Step 3: manifest を作成** — `hooks/lib/scripts-manifest.tsv`（区切りは**実タブ**）

```
# scripts-manifest.tsv — scripts/ エントリポイントの分類（single owner・iter55）
# 消費者: hooks/check-control-plane.sh（allow|ask = 実行可）
#         scripts/check_framework_contract.py（3方向 drift 検査）
#         templates/hooks.template.json permissions（class=allow と双方向一致）
#         tests/test_permission_allowlist_install.py（SCRIPT_CLASS 由来元）
# class: allow          = hook 実行可 + permissions.allow 掲載（プロンプトなし）
#        ask            = hook 実行可 + permissions 非掲載（プロンプト＝人間のトリップワイヤ。
#                         update-gate/update-task は状態変異、record-test-result/run-test-
#                         strength-drill は引数コマンド実行ガジェットのため auto-allow 禁止）
#        framework-only = 対象プロジェクトでは hook が deny（framework 開発専用）
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

- [ ] **Step 4: hook を manifest 読込に置換** — `hooks/check-control-plane.sh`

L18-20 のヘッダコメントを更新:

```bash
# Control plane paths: STATUS.md, CLAUDE.md, .claude/, hooks/, scripts/
# Allowlist: hooks/lib/scripts-manifest.tsv の class allow|ask 行（single owner・iter55）。
#            manifest 欠落/読取不能 = 全 deny（fail-closed）。
```

L809-830 の `is_allowlisted()` ブロックを以下に置換:

```bash
# --- Allowlist check (iter55: manifest single-owner) ---
# 実行可スクリプトは hooks/lib/scripts-manifest.tsv の class allow|ask 行。
# 同じ manifest が templates/hooks.template.json permissions（contract 検査で
# 双方向一致）と tests の SCRIPT_CLASS の由来元 = 3重管理ドリフトの封鎖。
# record-test-result.py / run-test-strength-drill.py は class=ask（OBS-018:
# 自身の監査されたロジック経由でしか書かず、no-chain ガードが `x && evil` /
# `> hooks/...` を deny する前提は不変）。
SCRIPTS_MANIFEST="${SCRIPT_DIR}/lib/scripts-manifest.tsv"

# rc0 ⟺ $1 が manifest の class allow|ask スクリプトの実行形（interpreter+パス /
# パス / ./パス で始まる）。manifest が読めなければ常に rc1（fail-closed）。
# 【重要】substring マッチにしないこと＝`cp evil scripts/update-gate.sh`（許可
# スクリプトへの書込み）まで allow する脆弱規則になる（grill-code 🔴 で封鎖済み）。
manifest_script_in() {
  local cmd="$1" entry cls
  [ -r "$SCRIPTS_MANIFEST" ] || return 1
  while IFS=$'\t' read -r entry cls || [ -n "$entry" ]; do
    case "$entry" in ''|\#*) continue ;; esac
    case "$cls" in allow|ask) ;; *) continue ;; esac
    case "$cmd" in
      "$entry"|"$entry "*|"./$entry"|"./$entry "*|\
      "python3 $entry"|"python3 $entry "*|"python $entry"|"python $entry "*|\
      "bash $entry"|"bash $entry "*|"sh $entry"|"sh $entry "*)
        return 0 ;;
    esac
  done < "$SCRIPTS_MANIFEST"
  return 1
}

# Only if the command has NO chaining operators, check if it is solely an
# allowlisted script invocation.
is_allowlisted() {
  local cmd="$1"
  if printf '%s' "$cmd" | grep -qE "$CHAIN_OPS"; then
    return 1
  fi
  manifest_script_in "$cmd"
}
```

- [ ] **Step 5: 既存 harness に manifest を追加** — `tests/test_control_plane_allowlist.py`
  の `_scratch_root()` の symlink タプルの直後に 1 行追加:

```python
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    (lib_dir / "scripts-manifest.tsv").symlink_to(
        ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
```

- [ ] **Step 6: GREEN を確認**

Run: `python3 -m pytest -q tests/test_scripts_manifest_hook.py tests/test_control_plane_allowlist.py`
Expected: PASS（全件）

- [ ] **Step 7: 他の control-plane 系 harness と install 発火テストの追随**（grill 致命3対応）
  — 以下を実行し、(a) check-control-plane.sh を copy している harness で allow 系テストが
  落ちるものに Step 5 と同じ 1 行を足す（deny 系のみの harness は fail-closed でそのまま通る）、
  (b) **install 発火系（test_profile_moat_registration / test_permission_allowlist_install）が
  「installed tree に manifest が無い」ことで赤になった場合は、Task 2 Step 3 の setup.sh
  glob 修正（1 行）を本 Task のコミットに同梱する**（コミットを赤で残さない。その場合
  Task 2 は install 契約テストの追加のみになる）:

Run: `python3 -m pytest -q tests/test_control_plane_var_expansion.py tests/test_control_plane_chmod_unlock.py tests/test_control_plane_token_split.py tests/test_case_insensitive_fs.py tests/test_glob_expansion_hooks.py tests/test_hook_emit_failclosed.py tests/test_profile_moat_registration.py tests/test_permission_allowlist_install.py`
Expected: PASS（落ちた場合のみ上記 (a)(b) を適用して再実行）

- [ ] **Step 8: コミット**

```bash
git add hooks/lib/scripts-manifest.tsv hooks/check-control-plane.sh tests/test_scripts_manifest_hook.py tests/test_control_plane_allowlist.py
git commit -m "feat(iter55): scripts-manifest.tsv を単一正本に is_allowlisted を manifest 化（fail-closed）"
```

---

### Task 2: setup.sh の .tsv 配布 + install 契約テスト

**Files:**
- Modify: `bin/setup.sh:463`（lib 配布 glob）
- Test: `tests/test_permission_allowlist_install.py`（テスト2本追加）

**Interfaces:**
- Consumes: Task 1 の `hooks/lib/scripts-manifest.tsv`
- Produces: install 先に manifest が必ず存在する保証（F6 教訓の install 契約）

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_permission_allowlist_install.py` 末尾に追加

```python
# --- iter55: scripts-manifest.tsv must ship with hooks/lib (F6-class install gap) ---

def test_install_ships_scripts_manifest(tmp_path):
    """setup.sh の lib 配布は *.sh glob だったため .tsv が配布されず、install 先で
    allowlist が fail-closed 全 deny になる（F6 同型の install 死角）。"""
    target = tmp_path / "proj"
    _install(str(target), "full")
    installed = target / "hooks" / "lib" / "scripts-manifest.tsv"
    assert installed.is_file(), "scripts-manifest.tsv not shipped to install target"
    src = (ROOT / "hooks" / "lib" / "scripts-manifest.tsv").read_text()
    assert installed.read_text() == src, "installed manifest differs from source"


def test_installed_hook_allows_manifest_script(tmp_path):
    """installed tree での hook 実発火（scaffold smoke の精神）: feature タスク下で
    class=allow スクリプトの素実行が通る。"""
    target = tmp_path / "proj"
    _install(str(target), "full")
    (target / "docs").mkdir(exist_ok=True)
    (target / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": "python3 scripts/retro_report.py"}})
    r = subprocess.run(
        ["bash", str(target / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(target))
    assert r.stdout.strip() == "{}", f"installed hook must allow: {r.stdout[:200]!r}"
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest -q tests/test_permission_allowlist_install.py -k scripts_manifest or installed_hook`
（正確には: `python3 -m pytest -q "tests/test_permission_allowlist_install.py::test_install_ships_scripts_manifest" "tests/test_permission_allowlist_install.py::test_installed_hook_allows_manifest_script"`）
Expected: FAIL — manifest が install 先に無い / installed hook が deny

**注記（grill 致命4・2026-07-03 検証済）**: templates/profiles/*.json は hooks/scripts のみ
列挙し hooks/lib は列挙しない。copy_hooks は hooks_include が非空なら lib/ を glob で丸ごと
配布するため、**profiles JSON の変更は不要**（.tsv は glob 追加だけで全 profile に配布される）。

- [ ] **Step 3: setup.sh を修正**（Task 1 Step 7 (b) で同梱済みの場合はスキップ）
  — L457-466 のコメントとループ:

```bash
  # K-9 (v1.6.2): hooks/lib/*.sh / *.tsv are framework-owned. Always force-
  # overwrite, never SKIP, to prevent old libs from lingering across upgrades
  # and silently breaking new hooks (DIST-02 / F6 同型). iter55: the *.tsv glob
  # ships scripts-manifest.tsv — without it the installed allowlist is
  # fail-closed and denies every framework script. This calls copy_file_force
  # directly (rather than copy_file_routed) because the whole lib/ glob is
  # unconditionally framework-owned — is_framework_owned("hooks/lib/...") would
  # return the same routing anyway.
  for lib in "$FRAMEWORK_ROOT"/hooks/lib/*.sh "$FRAMEWORK_ROOT"/hooks/lib/*.tsv; do
    [[ -e "$lib" ]] || continue
    copy_file_force "$lib" "$target_dir/hooks/lib/$(basename "$lib")"
  done
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m pytest -q tests/test_permission_allowlist_install.py`
Expected: PASS（既存含む全件）

- [ ] **Step 5: コミット**

```bash
git add bin/setup.sh tests/test_permission_allowlist_install.py
git commit -m "fix(iter55): setup.sh が scripts-manifest.tsv を配布（F6 級 install 死角の封鎖）+ install 実発火テスト"
```

---

### Task 3: contract 3方向 drift 検査

**Files:**
- Modify: `scripts/check_framework_contract.py`（`check_scripts_manifest()` 追加 + main 配線。
  ファイル冒頭の import に `json` が無ければ追加）
- Test: `tests/test_scripts_manifest_contract.py`（新規）

**Interfaces:**
- Consumes: Task 1 の manifest
- Produces: `check_scripts_manifest(root: Path = ROOT) -> list[str]`（full contract で常時実行）

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_scripts_manifest_contract.py`

```python
#!/usr/bin/env python3
"""iter55 P0: scripts-manifest.tsv の 3 方向 drift 検査（check_framework_contract.py）。

方向1: manifest 健全性（実在・enum・重複・scripts/ 全 *.py|*.sh の完全分類）
方向2: class=allow ⟺ templates/hooks.template.json permissions（双方向。ask 等の混入は
       人間承認トリップワイヤの誤解除＝FAIL）
方向3: skill/command/rules が参照する scripts/*.{py,sh} は class allow|ask
       （skill が指示するスクリプトを hook が deny する事故クラスの構造的封鎖）
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "cfc", ROOT / "scripts" / "check_framework_contract.py")
cfc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfc)

TEMPLATE_JSON = {
    "permissions": {"allow": ["Bash(python3 scripts/good.py:*)"]},
    "hooks": {},
}


def _mkroot(tmp: Path, manifest: str, template: dict | None = None,
            scripts: tuple = ("good.py",), skill: str | None = None) -> Path:
    (tmp / "hooks" / "lib").mkdir(parents=True)
    (tmp / "hooks" / "lib" / "scripts-manifest.tsv").write_text(manifest, encoding="utf-8")
    (tmp / "scripts").mkdir()
    for name in scripts:
        (tmp / "scripts" / name).write_text("# stub\n", encoding="utf-8")
    (tmp / "templates").mkdir()
    (tmp / "templates" / "hooks.template.json").write_text(
        json.dumps(template if template is not None else TEMPLATE_JSON), encoding="utf-8")
    if skill is not None:
        d = tmp / ".claude" / "skills" / "demo"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(skill, encoding="utf-8")
    return tmp


class TestManifestHealth(unittest.TestCase):
    def test_real_repo_passes(self):
        self.assertEqual(cfc.check_scripts_manifest(), [],
                         "real repo must pass the 3-way drift check")

    def test_unclassified_script_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n",
                           scripts=("good.py", "new_tool.py"))
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("new_tool.py" in f for f in fails), fails)

    def test_row_for_missing_file_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/ghost.py\tallow\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("ghost.py" in f for f in fails), fails)

    def test_unknown_class_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tmaybe\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("maybe" in f for f in fails), fails)

    def test_duplicate_row_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\nscripts/good.py\task\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("duplicate" in f.lower() for f in fails), fails)

    def test_whitespace_in_field_fails(self):
        """grill 致命2: bash reader は完全一致＝空白入り行は silent deny になる。
        contract は寛容に strip して通してはならない（PASS/deny の非対称ドリフト）。"""
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow \n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("whitespace" in f.lower() for f in fails), fails)


class TestPermissionsBidirectional(unittest.TestCase):
    def test_allow_missing_from_permissions_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n",
                           template={"permissions": {"allow": []}})
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("good.py" in f for f in fails), fails)

    def test_non_allow_present_in_permissions_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(
                Path(t), "scripts/good.py\task\n",
                template={"permissions": {"allow": ["Bash(python3 scripts/good.py:*)"]}})
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("good.py" in f for f in fails), fails)


class TestSkillReferences(unittest.TestCase):
    def test_skill_ref_to_framework_only_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/tool.py\tframework-only\n",
                           scripts=("good.py", "tool.py"),
                           skill="Run `python3 scripts/tool.py` to do X.\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("tool.py" in f for f in fails), fails)

    def test_skill_ref_to_unknown_script_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t), "scripts/good.py\tallow\n",
                           skill="Run `python3 scripts/ghost.py`.\n")
            fails = cfc.check_scripts_manifest(root)
            self.assertTrue(any("ghost.py" in f for f in fails), fails)

    def test_skill_ref_to_ask_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/gate.sh\task\n",
                           scripts=("good.py", "gate.sh"),
                           skill="Run `bash scripts/gate.sh review approve`.\n")
            self.assertEqual(cfc.check_scripts_manifest(root), [])

    def test_overridden_local_command_not_scanned(self):
        """grill 致命1: templates/commands/ に同名 override がある .claude/commands/ の
        framework-repo ローカル変種（framework-only スクリプト参照可）は走査対象外。
        配布されるのは templates 版（setup.sh install resolver と同じ規則）。"""
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root = _mkroot(Path(t),
                           "scripts/good.py\tallow\nscripts/dev.py\tframework-only\n",
                           scripts=("good.py", "dev.py"))
            cmd_dir = root / ".claude" / "commands"
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "validate.md").write_text(
                "Run `python3 scripts/dev.py` (framework-local).\n", encoding="utf-8")
            tpl_dir = root / "templates" / "commands"
            tpl_dir.mkdir(parents=True)
            (tpl_dir / "validate.md").write_text(
                "Run `python3 scripts/good.py`.\n", encoding="utf-8")
            self.assertEqual(cfc.check_scripts_manifest(root), [],
                             "配布されない framework-local 変種の参照で FAIL してはならない")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest -q tests/test_scripts_manifest_contract.py`
Expected: FAIL — `AttributeError: module 'cfc' has no attribute 'check_scripts_manifest'`

- [ ] **Step 3: contract 検査を実装** — `scripts/check_framework_contract.py` に追加
  （`check_agent_names` の直後・`word_count` の前に配置。`import json` が冒頭に無ければ追加）:

```python
# --- iter55: scripts-manifest 3-way drift check -----------------------------
# ドッグフード一周目のゲート戦闘 7 件中 6 件の根本原因＝許可リストの3重管理
# （hook case 文 / template permissions / SCRIPT_CLASS テスト map）ドリフト。
# hooks/lib/scripts-manifest.tsv を単一正本とし、本検査が3方向で縛る。
# CLAUDE.md は走査対象外（platform_manifest.py の「定義場所」言及＝実行指示でない）。
SCRIPTS_MANIFEST_REL = "hooks/lib/scripts-manifest.tsv"
SCRIPTS_MANIFEST_CLASSES = {"allow", "ask", "framework-only", "import-only"}
SCRIPT_REF_RE = re.compile(r"scripts/[A-Za-z0-9_\-.]+\.(?:py|sh)")


def _distributed_md_files(root: Path) -> list:
    """方向3の走査集合＝install 先に配布される markdown（grill 致命1）。

    setup.sh の install resolver（bin/setup.sh L156-160）は .claude/commands/ のうち
    templates/commands/ に同名 override があるもの（validate.md / retro.md）を
    templates 版に差し替えて配布する。framework-repo ローカル変種（run_eval.py 参照など
    framework-only スクリプトを指示してよい側）を走査すると誤 FAIL するため、
    ここでも同じ差し替え規則で「配布される側」だけを集める。"""
    files = sorted(root.glob(".claude/skills/*/SKILL.md"))
    overridden = {p.name for p in root.glob("templates/commands/*.md")}
    files += [p for p in sorted(root.glob(".claude/commands/*.md"))
              if p.name not in overridden]
    files += sorted(root.glob("templates/commands/*.md"))
    files += sorted(root.glob(".claude/rules/*.md"))
    return files


def load_scripts_manifest(root: Path):
    """scripts-manifest.tsv → {'scripts/x.py': class}。壊れ行は ValueError。

    grill 致命2: bash 側（IFS=$'\\t' read + case 完全一致）と字句レベルで同じ厳格さで
    パースする。フィールドの前後空白は bash では黙って deny（class 不一致）になるため、
    ここで strip して通すと「contract PASS・hook silent deny」の新種ドリフトになる —
    whitespace 不一致は即 FAIL。"""
    manifest: dict[str, str] = {}
    path = root / SCRIPTS_MANIFEST_REL
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"line {lineno}: expected '<path>\\t<class>': {raw!r}")
        entry, cls = parts[0], parts[1]
        if entry != entry.strip() or cls != cls.strip():
            raise ValueError(
                f"line {lineno}: leading/trailing whitespace in fields "
                f"(bash reader matches exactly): {raw!r}")
        if entry in manifest:
            raise ValueError(f"line {lineno}: duplicate entry {entry}")
        manifest[entry] = cls
    return manifest


def check_scripts_manifest(root: Path = ROOT) -> list:
    failures: list[str] = []
    manifest_path = root / SCRIPTS_MANIFEST_REL
    if not manifest_path.is_file():
        return [f"scripts-manifest: missing {SCRIPTS_MANIFEST_REL}"]
    try:
        manifest = load_scripts_manifest(root)
    except ValueError as exc:
        return [f"scripts-manifest: parse error: {exc}"]

    # 方向1: 健全性（enum / 実在 / scripts/ 全エントリポイントの完全分類）
    for entry, cls in manifest.items():
        if cls not in SCRIPTS_MANIFEST_CLASSES:
            failures.append(f"scripts-manifest: {entry} has unknown class {cls!r}")
        if not (root / entry).is_file():
            failures.append(f"scripts-manifest: {entry} does not exist")
    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        actual = {f"scripts/{p.name}" for p in scripts_dir.iterdir()
                  if p.is_file() and p.suffix in (".py", ".sh")}
        for missing in sorted(actual - set(manifest)):
            failures.append(
                f"scripts-manifest: {missing} is not classified — add a row "
                "(allow/ask/framework-only/import-only)")

    # 方向2: class=allow ⟺ template permissions（双方向）
    template_path = root / "templates" / "hooks.template.json"
    if template_path.is_file():
        allow_entries = json.loads(template_path.read_text(encoding="utf-8")) \
            .get("permissions", {}).get("allow", [])
        joined = " ".join(allow_entries)
        for entry, cls in manifest.items():
            runner = "bash" if entry.endswith(".sh") else "python3"
            canonical = f"Bash({runner} {entry}:*)"
            if cls == "allow" and canonical not in allow_entries:
                failures.append(
                    f"scripts-manifest: class=allow {entry} missing from template "
                    f"permissions (expected {canonical})")
            if cls != "allow" and entry in joined:
                failures.append(
                    f"scripts-manifest: class={cls} {entry} must NOT appear in "
                    "template permissions (human-approval tripwire)")

    # 方向3: 配布される skill/command/rules の参照 ⊆ 実行可（allow|ask）
    runnable = {e for e, c in manifest.items() if c in ("allow", "ask")}
    for md in _distributed_md_files(root):
        for ref in sorted(set(SCRIPT_REF_RE.findall(read_text(md)))):
            if ref not in runnable:
                failures.append(
                    f"scripts-manifest: {md.relative_to(root)} references {ref} "
                    "which is not runnable (class allow|ask) — the control-plane "
                    "hook would deny the instruction")
    return failures
```

main() の full check セクション（`failures: list[str] = []` の後続・既存 check 呼び出し群の並び）に:

```python
    failures.extend(check_scripts_manifest())
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m pytest -q tests/test_scripts_manifest_contract.py && python3 scripts/check_framework_contract.py`
Expected: pytest PASS・contract `PASS`（rc 0）

- [ ] **Step 5: コミット**

```bash
git add scripts/check_framework_contract.py tests/test_scripts_manifest_contract.py
git commit -m "feat(iter55): scripts-manifest の3方向 drift 検査を contract に追加"
```

---

### Task 4: SCRIPT_CLASS を manifest 由来ローダーに置換（single-owner 完成）

**Files:**
- Modify: `tests/test_permission_allowlist_install.py:196-219`（SCRIPT_CLASS dict → ローダー）

- [ ] **Step 1: dict をローダーに置換**（L196 の `SCRIPT_CLASS = {` から L219 `}` までを置換。
  クラス分類の理由コメントは manifest 側 TSV ヘッダに集約済み）:

```python
# iter55: SCRIPT_CLASS は hooks/lib/scripts-manifest.tsv（single owner）由来。
# allow → safe_auto_allow / ask・framework-only → must_prompt / import-only → not_cli。
# 分類の理由（exec ガジェット・状態変異・--tighten 書込み等）は TSV ヘッダコメントに集約。
_CLASS_FROM_MANIFEST = {
    "allow": "safe_auto_allow",
    "ask": "must_prompt",
    "framework-only": "must_prompt",
    "import-only": "not_cli",
}


def _load_script_class():
    out = {}
    text = (ROOT / "hooks" / "lib" / "scripts-manifest.tsv").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entry, cls = line.split("\t")  # 厳格 split（strip しない — contract が清潔さを保証）
        out[pathlib.Path(entry).name] = _CLASS_FROM_MANIFEST[cls]
    return out


SCRIPT_CLASS = _load_script_class()
```

- [ ] **Step 2: スイート GREEN を確認**（意味等価の置換であること＝既存テストが全部通る）

Run: `python3 -m pytest -q tests/test_permission_allowlist_install.py`
Expected: PASS（全件・分類は 18 本とも旧 dict と同値）

- [ ] **Step 3: コミット**

```bash
git add tests/test_permission_allowlist_install.py
git commit -m "refactor(iter55): SCRIPT_CLASS を scripts-manifest.tsv 由来に（3重管理の最後の1枚を退役）"
```

---

### Task 5: 安全な stderr リダイレクトの正規化（ls deny の根治）

**Files:**
- Modify: `hooks/check-control-plane.sh`（CMD 抽出後・CHAIN_OPS 定義の後に正規化を挿入し、
  allow 側判定 3 箇所を正規化済み文字列に切替）
- Test: `tests/test_safe_stderr_redirect.py`（新規）

**Interfaces:**
- Consumes: Task 1 の manifest（allowlist 経由の検証に使用）
- Produces: `CMD_SAFE` 変数（Task 6 の tailored メッセージも使用）

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_safe_stderr_redirect.py`
  （harness は Task 1 の `_scratch_root`/`_hook`/`_allowed`/`_denied` と同一。コピーして使用）

```python
#!/usr/bin/env python3
"""iter55 P3d: 安全な stderr リダイレクト（2>/dev/null・2>&1）の正規化。

ドッグフードのゲート戦闘1の正体（2026-07-03 実プローブで確定）: 素の `ls templates/` は
read-only carve-out で ALLOW だが、エージェントが慣用的に付ける `2>/dev/null` / `2>&1` の
> / & が CHAIN_OPS に該当し read-only・allowlist 両 carve-out から脱落して DENY。
ファイル書込みが発生し得ない 2 形のみ除去し、それ以外（2>>, 2>file, 2>/dev/nullish,
fd1 の >/dev/null, 除去後も残る >）は fail-closed のまま。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch_root() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    (lib_dir / "scripts-manifest.tsv").symlink_to(
        ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


class TestSafeStderrRedirectAllowed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_ls_devnull_allowed(self):
        out = _hook(self.root, "ls templates/ 2>/dev/null")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_ls_devnull_with_space_allowed(self):
        out = _hook(self.root, "ls -la templates/ docs/ 2> /dev/null")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_ls_stderr_merge_allowed(self):
        out = _hook(self.root, "ls templates/ docs/ 2>&1")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_allowlisted_script_with_stderr_merge_allowed(self):
        out = _hook(self.root, "bash scripts/update-gate.sh review approve 2>&1")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_readonly_pipe_after_strip_allowed(self):
        out = _hook(self.root, "grep -rn foo scripts/ 2>/dev/null | head -5")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")


class TestUnsafeRedirectsStayDenied(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_append_to_devnull_style_denied(self):
        out = _hook(self.root, "ls hooks/ 2>>/dev/null")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_stderr_to_file_denied(self):
        out = _hook(self.root, "ls hooks/ 2>err.log")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_devnullish_suffix_denied(self):
        out = _hook(self.root, "ls hooks/ 2>/dev/nullish")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_fd1_devnull_not_tolerated(self):
        out = _hook(self.root, "ls hooks/ >/dev/null")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_merge_then_real_redirect_denied(self):
        out = _hook(self.root, "ls hooks/ 2>&1 > hooks/evil")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_script_merge_then_chain_denied(self):
        out = _hook(self.root,
                    "bash scripts/update-gate.sh review approve 2>&1 && rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest -q tests/test_safe_stderr_redirect.py`
Expected: FAIL — Allowed 系 5 件が deny（Unsafe 系は現行でも deny なので PASS）

- [ ] **Step 3: 正規化を実装** — `hooks/check-control-plane.sh` の `CHAIN_OPS=` 定義
  （L807 付近）の直後に挿入:

```bash
# --- iter55: SAFE stderr リダイレクトの正規化（allow 側判定の前処理） ---
# `2>/dev/null`（`2> /dev/null` 含む）と `2>&1` はファイル書込みが発生し得ないが、
# > / & が CHAIN_OPS に該当して read-only 検査（`ls templates/ 2>/dev/null`）や
# 素の allowlist スクリプトを carve-out から弾いていた（ドッグフード ゲート戦闘1）。
# この 2 形だけを単語境界で除去する。2>>, 2>file, 2>/dev/nullish, fd1 の
# >/dev/null は除去せず、除去後に残る演算子も従来どおり fail-closed。
# CONTROL_PLANE 検出は生の $CMD / $INPUT で実施済み（緩めるのは allow 側のみ）。
strip_safe_stderr_redirects() {
  printf '%s' "$1" | sed -E \
    -e 's,(^|[[:space:]])2>[[:space:]]?/dev/null([[:space:]]|$),\1\2,g' \
    -e 's,(^|[[:space:]])2>&1([[:space:]]|$),\1\2,g'
}
CMD_SAFE=$(strip_safe_stderr_redirects "$CMD")
```

続いて allow 側判定 3 箇所を `CMD_SAFE` に切替:

1. L863 付近: `if [ -n "$CMD" ] && is_allowlisted "$CMD"; then`
   → `if [ -n "$CMD_SAFE" ] && is_allowlisted "$CMD_SAFE"; then`
2. L879 付近: `CHECK_CMD="$CMD"` → `CHECK_CMD="$CMD_SAFE"`
3. L931 付近: `if [ -n "$CMD" ] && is_bare_git_stage "$CMD"; then`
   → `if [ -n "$CMD_SAFE" ] && is_bare_git_stage "$CMD_SAFE"; then`

- [ ] **Step 4: GREEN + 回帰を確認**

Run: `python3 -m pytest -q tests/test_safe_stderr_redirect.py tests/test_control_plane_allowlist.py tests/test_scripts_manifest_hook.py`
Expected: PASS（全件）

- [ ] **Step 5: コミット**

```bash
git add hooks/check-control-plane.sh tests/test_safe_stderr_redirect.py
git commit -m "fix(iter55): 2>/dev/null・2>&1 を allow 側判定前に正規化（read-only ls 誤 deny の根治・fail-closed 維持）"
```

---

### Task 6: エラーメッセージ改善（チェーン専用文言・正規手段の案内・mention ヒント）

**Files:**
- Modify: `hooks/check-control-plane.sh`（最終 deny 部 L936-938・git-stage ask 文言 L932）
- Test: `tests/test_control_plane_messages.py`（新規）

**Interfaces:**
- Consumes: Task 1 の `manifest_script_in`・Task 5 の `CMD_SAFE`

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_control_plane_messages.py`
  （harness は Task 5 と同一。コピーして使用。`_reason(out)` は
  `json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]` を返すヘルパー）

```python
#!/usr/bin/env python3
"""iter55 P3a-c: 初見殺し deny/ask メッセージの改善（ドッグフード ゲート戦闘5・6・docs 摩擦）。

- 許可済みスクリプト＋チェーン演算子 → 「単体で実行せよ」の専用文言
- 汎用 deny → update-gate.sh / update-task.sh の案内（「Edit/Write を使え」単独の矛盾解消）
- git add で CP ファイル名 mention → 「git add docs/ 形式なら確認なし」のヒント
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch_root() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    (lib_dir / "scripts-manifest.tsv").symlink_to(
        ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
    return tmp


def _out(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _reason(out: str) -> str:
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


class TestMessages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_chained_allowlisted_script_gets_standalone_hint(self):
        out = _out(self.root, "bash scripts/update-gate.sh review approve | tail -20")
        self.assertIn('"deny"', out)
        self.assertIn("単体", _reason(out))

    def test_generic_deny_names_canonical_scripts(self):
        out = _out(self.root, "touch hooks/newfile.sh")
        self.assertIn('"deny"', out)
        reason = _reason(out)
        self.assertIn("update-gate.sh", reason)
        self.assertIn("update-task.sh", reason)

    def test_git_add_status_mention_hint(self):
        out = _out(self.root, "git add docs/STATUS.md")
        self.assertIn('"ask"', out)
        self.assertIn("git add docs/", _reason(out))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest -q tests/test_control_plane_messages.py`
Expected: FAIL（3 件とも現行文言に該当語なし）

- [ ] **Step 3: メッセージを実装** — `hooks/check-control-plane.sh`

git-stage ask（L932）を置換:

```bash
  emit_ask "[integrity] git add で制御プレーン (hooks/scripts/.claude/STATUS.md 等) を staging しようとしています。ファイル内容は変更しません（baseline コミット等の正当な操作の可能性）。意図を確認してください。なおファイル名を含まない形（例: git add docs/）ならこの確認は出ません。"
```

最終 deny 部（L936-938）を置換:

```bash
# Default: deny. Control plane path present, not allowlisted, not read-only.
# iter55: 許可済みスクリプトを含むのにチェーン演算子で不適格になったケースは
# 専用文言で案内（ゲート戦闘6:「hook が不安定」誤認の解消）。
if [ -n "$CMD_SAFE" ] && manifest_script_in "$CMD_SAFE"; then
  emit_deny "[integrity] このコマンドは許可済みスクリプト（scripts-manifest）を含みますが、チェーン/リダイレクト演算子（; && || | > \$() \`）付きの複合コマンドでは実行できません。パイプ等を外し、スクリプトを単体コマンドとして実行してください。"
  exit 0
fi
REASON=$(printf '[integrity] 制御プレーン path（hooks/ scripts/ templates/ .claude/ CLAUDE.md STATUS.md）を参照する Bash コマンドは project work（task_type=%s）中はブロックされます。ゲート値は scripts/update-gate.sh、task_type/task_size は scripts/update-task.sh を単体で実行してください。一般ファイルの編集は Edit/Write ツールを使用。framework ファイル自体の変更は task_type=framework が必要です。なお path 文字列の言及だけでも発火します（例: git add docs/STATUS.md → git add docs/ とする）。' "$TASK_TYPE")
emit_deny "$REASON"
exit 0
```

- [ ] **Step 4: GREEN + 文言変更の回帰を確認**（旧英語文言を pin したテストが無いことは
  調査済みだが、全 control-plane 系テストを回す）

Run: `python3 -m pytest -q tests/test_control_plane_messages.py tests/test_control_plane_allowlist.py tests/test_control_plane_var_expansion.py tests/test_control_plane_token_split.py`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add hooks/check-control-plane.sh tests/test_control_plane_messages.py
git commit -m "feat(iter55): deny/ask メッセージを日本語化し正規手段（update-gate/update-task・単体実行・git add docs/）を案内"
```

---

### Task 7: check-gate.sh — repo 直下 *.md は prose として allow

**Files:**
- Modify: `hooks/check-gate.sh`（`is_root_external_absolute` の allow（L199-202）の直後に挿入）
- Test: `tests/test_gate_root_prose_md.py`（新規）

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_gate_root_prose_md.py`

```python
#!/usr/bin/env python3
"""iter55 P2: repo 直下の *.md（DOGFOOD-LOG.md 等のメタ文書）は Client モード・
plan 承認前でも編集可（ゲートはコードを守る・散文は対象外）。

ドッグフード ゲート戦闘2・4: 観測ログ DOGFOOD-LOG.md が Client 全期間＋Dev の plan
承認前に書けず、スクラッチパッドへのバッファ運用を強いられた。CLAUDE.md（control
検査で deny 済み）・サブディレクトリの .md・コードファイルは従来どおり。
Harness は tests/test_check_gate_root_external.py と同型。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_TMPL = (
    "---\nframework: aegis\nmode: {mode}\nphase: {phase}\n"
    "task_type: {task_type}\ngate_approvals:\n  plan: {plan}\n---\n"
)


def _scratch_root(mode: str = "Dev", task_type: str = "feature",
                  plan: str = "pending", phase: str = "implement"):
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        STATUS_TMPL.format(mode=mode, task_type=task_type, plan=plan, phase=phase),
        encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-gate.sh", hooks_dir / "check-gate.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, file_path: str) -> str:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-gate.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


class TestRootProseMdAllowed(unittest.TestCase):
    def test_client_mode_root_md_allowed(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            root = Path(name)
            out = _hook(root, f"{root}/DOGFOOD-LOG.md")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_plan_pending_root_md_allowed(self):
        with _scratch_root(mode="Dev", plan="pending", phase="brainstorm") as name:
            root = Path(name)
            out = _hook(root, f"{root}/NOTES.md")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_relative_root_md_allowed(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            out = _hook(Path(name), "DOGFOOD-LOG.md")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")


class TestGuardsUnchanged(unittest.TestCase):
    def test_client_mode_code_still_denied(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            root = Path(name)
            out = _hook(root, f"{root}/src/app.ts")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_client_mode_claude_md_still_denied(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            root = Path(name)
            out = _hook(root, f"{root}/CLAUDE.md")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_subdir_md_still_gated(self):
        with _scratch_root(mode="Dev", plan="pending") as name:
            root = Path(name)
            out = _hook(root, f"{root}/notes/inner.md")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest -q tests/test_gate_root_prose_md.py`
Expected: FAIL — allow 系 3 件が deny（Guards 系 3 件は現行でも deny なので PASS）

- [ ] **Step 3: 実装** — `hooks/check-gate.sh` の `is_root_external_absolute` allow ブロック
  （L199-202）の直後・`MODE=$(frontmatter_value ...)`（L204-206）の前に挿入:

```bash
# --- Repo-root prose (*.md): gates guard code, not prose (iter55) ---
# DOGFOOD-LOG.md / README.md など repo 直下のメタ文書は Client モード・plan 未承認
# でも編集可（ドッグフード ゲート戦闘2・4: 観測ログが書けずバッファ運用を強制された）。
# ここに到達する時点で CLAUDE.md・hooks/scripts/.claude/templates は上の control
# 検査で deny 済み、docs/* は先頭 allowlist で allow 済み。suffix は FS に合わせて
# case-fold（.MD 変種）。サブディレクトリの .md はコード木の可能性があるため対象外。
is_root_prose_md() {
  local t="$1" d rc=1
  d=$(dirname "$t")
  if [ "$CASE_FOLD" = "1" ]; then shopt -s nocasematch; fi
  case "$t" in
    *.md)
      case "$d" in
        "$ROOT"|"$ROOT_REAL"|.) rc=0 ;;
      esac ;;
  esac
  if [ "$CASE_FOLD" = "1" ]; then shopt -u nocasematch; fi
  return $rc
}

if is_root_prose_md "$TARGET_FILE"; then
  emit_allow
  exit 0
fi
```

- [ ] **Step 4: GREEN + 回帰を確認**

Run: `python3 -m pytest -q tests/test_gate_root_prose_md.py tests/test_check_gate_root_external.py`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add hooks/check-gate.sh tests/test_gate_root_prose_md.py
git commit -m "feat(iter55): repo 直下 *.md を prose として Client/plan ゲート対象外に（メタ文書ロック解消）"
```

---

### Task 8: client-workflow SKILL — translation ref タイミング修正 + テンプレ対応表

**Files:**
- Modify: `.claude/skills/client-workflow/SKILL.md`（L28 表・Translation Artifact 節・L89）
- Test: `tests/test_skill_guidance_tokens.py`（新規・Task 9 と共用）

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_skill_guidance_tokens.py`

```python
#!/usr/bin/env python3
"""iter55 P1/P4: skill 本文の load-bearing 文言の drift ガード（iter53 の
test_destructive_warning_language.py と同型の token pin）＋テンプレ対応表 parity。

ドッグフード ゲート戦闘3: client-workflow の「作成したら translation ref を設定」指示が
stale-ref 検査（pending gate + ref = FAIL）と正面衝突。正しい運用（承認の直前に設定→
承認を連続実行）を skill 本文に明文化し、旧文言の再発を token で封鎖する。
テンプレ対応表は scripts/_artifact_template_map.py（single owner）との parity で縛る。
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CW = (ROOT / ".claude" / "skills" / "client-workflow" / "SKILL.md").read_text(encoding="utf-8")
QA = (ROOT / ".claude" / "skills" / "qa-verification" / "SKILL.md").read_text(encoding="utf-8")

_spec = importlib.util.spec_from_file_location(
    "atm", ROOT / "scripts" / "_artifact_template_map.py")
atm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atm)

# Client フェーズで client-workflow が案内すべき産出物（TO-CLIENT は Dev 側なので除外）
CLIENT_PREFIXES = ("docs/requirements/", "docs/handover/", "docs/translation/")
CLIENT_EXCLUDE = {"docs/handover/TO-CLIENT.md"}


class TestTranslationRefTiming(unittest.TestCase):
    def test_timing_token_present(self):
        self.assertIn("承認の直前", CW,
                      "translation ref のタイミング規定（承認の直前）が消えている")
        self.assertIn("stale-ref", CW,
                      "stale-ref 違反への言及（なぜ直前なのか）が消えている")

    def test_old_contradicting_wording_gone(self):
        self.assertNotIn(
            "作成したら、`current_refs.translation` に設定する", CW,
            "hook 契約と矛盾する旧文言（作成時に ref 設定）が残っている")


class TestTemplateTableParity(unittest.TestCase):
    def test_client_artifacts_and_templates_listed(self):
        for artifact, template in atm.ARTIFACT_TO_TEMPLATE.items():
            if not artifact.startswith(CLIENT_PREFIXES) or artifact in CLIENT_EXCLUDE:
                continue
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, CW, f"{artifact} が client-workflow に未記載")
                self.assertIn(template, CW, f"{template} が client-workflow に未記載")


class TestQaBrowserDelegationGranularity(unittest.TestCase):
    def test_granularity_guidance_present(self):
        self.assertIn("5 項目程度", QA,
                      "qa-browser 委譲粒度ガイド（5 項目程度）が消えている")
        self.assertIn("19 項目", QA,
                      "委譲粒度の根拠（ドッグフード実測 19 項目で停止 3 回）が消えている")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest -q tests/test_skill_guidance_tokens.py`
Expected: FAIL（timing token 不在・parity 一部不在・qa granularity 不在。
old wording テストのみ FAIL する側＝旧文言が存在）

- [ ] **Step 3: client-workflow SKILL.md を修正**

(a) L28 の handover 行の完了条件セルの末尾を変更:
`translation mapping が作成済みであること` →
`translation mapping が作成済みであること（current_refs.translation はまだ設定しない — 下記 Translation Artifact 節）`

(b) Translation Artifact 節（L30-38）の Gate 契約行の直後に追加:

```markdown
- **ref 設定のタイミング**: `current_refs.translation` は `client_ready_for_dev`
  **承認の直前**に設定し、設定 → `bash scripts/update-gate.sh client_ready_for_dev approve`
  を**連続で**実行する。gate が pending のまま ref を設定して間に完了検査（TaskCompleted）を
  挟むと stale-ref 違反（pending gate + ref あり）で拒否される。
```

(c) L89 の bullet を置換:
`- \`handover\` で \`docs/translation/mapping.md\` を作成したら、\`current_refs.translation\` に設定する。` →
`- \`handover\` で \`docs/translation/mapping.md\` を作成する。\`current_refs.translation\` への設定はゲート承認の直前（Translation Artifact 節のタイミング規定に従う）。`

(d) 進行表（L21-28）の直後に新節を追加:

```markdown
## テンプレート対応表（正本: scripts/_artifact_template_map.py）

産出物は対応するテンプレートから作成する（テンプレ名は非自明 — TO-DEV は
HANDOVER-TO-DEV.template.md）。

| 産出物 | テンプレート |
|--------|-------------|
| docs/requirements/PRD.md | templates/PRD.template.md |
| docs/requirements/SCOPE.md | templates/SCOPE.template.md |
| docs/requirements/NFR.md | templates/NFR.template.md |
| docs/requirements/ACCEPTANCE.md | templates/ACCEPTANCE.template.md |
| docs/handover/TO-DEV.md | templates/HANDOVER-TO-DEV.template.md |
| docs/handover/CHANGES.md | templates/CHANGES.template.md |
| docs/translation/mapping.md | templates/TRANSLATION-MAPPING.template.md |
```

- [ ] **Step 4: 部分 GREEN を確認**（qa granularity 以外）

Run: `python3 -m pytest -q tests/test_skill_guidance_tokens.py -k "not Granularity"`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add .claude/skills/client-workflow/SKILL.md tests/test_skill_guidance_tokens.py
git commit -m "docs(iter55): client-workflow の translation ref タイミングを hook 契約に一致＋テンプレ対応表（token pin/parity テスト付き）"
```

---

### Task 9: qa-verification — 委譲粒度ガイド

**Files:**
- Modify: `.claude/skills/qa-verification/SKILL.md`（qa-browser 委譲ルール節 L66-75）

- [ ] **Step 1: 追記** — 「qa-browser 委譲ルール」の手順 3 の直後（`qa-browser は
  browser-assist スキル…` の行の前）に追加:

```markdown
4. **委譲粒度**: 長尺のブラウザ検証は 1 委譲あたり **5 項目程度**に分割して複数回委譲する。
   対話的な長尺検証はサブエージェントの途中停止と相性が悪い
   （ドッグフード一周目実測: 19 項目を 1 委譲にして途中停止 3 回・SendMessage 再開）。
```

- [ ] **Step 2: GREEN を確認**

Run: `python3 -m pytest -q tests/test_skill_guidance_tokens.py`
Expected: PASS（全件）

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/qa-verification/SKILL.md
git commit -m "docs(iter55): qa-browser 委譲粒度ガイド（5項目程度×複数委譲・実測根拠付き）"
```

---

### Task 10: 版数 v1.16.0 + 全体回帰

**Files:**
- Modify: `scripts/check_framework_contract.py:24`（FRAMEWORK_VERSION）
- Modify: `templates/STATUS.template.md:3`（framework_version）
- Modify: `docs/STATUS.md:3`（framework_version）
- Modify: 版数を pin する既存テスト（下記 grep で特定。既知: `tests/test_cp_lock_contract.py`）

- [ ] **Step 1: 版数 pin 箇所を列挙**

Run: `grep -rn '1\.15\.0' scripts/ templates/ tests/ docs/STATUS.md hooks/ bin/ .claude/ 2>/dev/null`
Expected: FRAMEWORK_VERSION・STATUS.template.md・docs/STATUS.md・テスト pin（あれば）が列挙される

- [ ] **Step 2: 全箇所を `1.16.0` に更新**（列挙された各箇所を Edit。docs/ 配下の
  過去イテレーションの履歴記述・アーカイブは対象外＝当時の事実なので触らない）

- [ ] **Step 3: full suite GREEN を確認**

Run: `python3 -m pytest -q`
Expected: 全件 PASS（1232+ 既存 + 本 iteration 新規）

- [ ] **Step 4: contract / status / reference drift の三点検**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/check_status.py && python3 scripts/check_reference_drift.py`
Expected: すべて PASS / rc 0

- [ ] **Step 5: コミット**

```bash
git add -A
git commit -m "chore(iter55): bump to v1.16.0（scripts-manifest 単一正本・ドッグフードFB反映）"
```

---

## 実装後のイテレーション運用（plan タスク外・aegis L サイズの通常フロー）

grill-code → review（盲検2次）→ qa（B1 drill — 罠(f)(l)。framework 混在 diff なら skip+手動
mutation: manifest 行削除で hook deny 化・contract FAIL 化を実証）→ security（moat 変更の
挙動 spot-check: fail-closed 3 形〔manifest 欠落/壊れ行/チェーン〕）→ deploy（setup.sh
install 実走＝Task 2 のテストで大半カバー済み）→ ship → docs（LEARNINGS 蒸留・
dev_ready_for_client）。push はユーザー確認後。

## Self-Review（作成時実施済み）

- スペック網羅: P0（Task 1-4）/ P1（Task 8）/ P2（Task 7）/ P3a-c（Task 6）/ P3d（Task 5）/
  P4（Task 9）/ install 契約（Task 2）/ 版数（Task 10）— 設計書の全節にタスクあり
- プレースホルダなし・全ステップ実コード付き
- 型/シグネチャ整合: `manifest_script_in`（Task 1 定義 → Task 6 使用）・`CMD_SAFE`
  （Task 5 定義 → Task 6 使用）— Task 6 は Task 1・5 の後に実施すること
