# iter56: M2 フィードバック反映 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M2 ドッグフードで露出した摩擦6件＋可視性小玉2件を TDD で一括修正する（設計書 `docs/specs/2026-07-05-iter56-m2-feedback-design.md` 準拠）。

**Architecture:** hook 判定（check-secrets）・judge（build-judge-card）・ゲート検査（check_status）・install 契約（full.json＋contract 方向4）・配布 skill 文言（qa-verification / subagent-dev）の5面を、それぞれ独立タスクとして修正。judge/hook はテスト先行（RED→GREEN）、skill/テンプレは機械検査（guidance token・reference drift・context budget）で固定する。

**Tech Stack:** bash（hooks）・Python 3 stdlib のみ（scripts/tests）・pytest。

## Global Constraints

- moat 変更（check-secrets）は**緩和方向のみ**・fail-closed 方針を変えない
- claims 読取は narrow YAML subset（依存ゼロ）を維持・書式変更禁止
- minimal/standard プロファイルの意図的劣化（scaffold-safe retro.md 変種）は不変
- context budget: `.claude/skills/qa-verification/SKILL.md` は **448/455 words**（残7語・
  words=`len(text.split())`＝空白区切り。日本語連続文は1語）→ 追記は空白増を最小化し、
  必要なら同ファイル内の冗長文を削って相殺。subagent-dev は 401/442（残41語）
- guidance token 維持: qa-verification の「5 項目程度」「19 項目」は削除禁止
  （tests/test_skill_guidance_tokens.py が固定）
- コミット単位はタスクごと。**push はしない**（ユーザー確認待ち）
- 各タスク完了時に `python3 -m pytest -q tests/<該当テスト>` green を確認してからコミット

---

### Task 1: ① check-secrets broad-staging 先頭ドット誤検知の修正（P1・moat）

**Files:**
- Modify: `hooks/check-secrets.sh:149`（broad 正規表現）・`:141` 付近（直接 .env deny 文言）
- Test: `tests/test_secrets_broad_dot_token.py`（新規）

**Interfaces:**
- Consumes: 既存 `_run` テストパターン（`tests/test_check_secrets_git_dir.py` と同形）
- Produces: broad-dot 判定は「`.` `..` `./ ` `../`（直後が空白 or 行末）」のみ

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_secrets_broad_dot_token.py` を新規作成:

```python
"""iter56 ①: broad-staging 検出の `\\.` がトークン境界非アンカーで、
.env.example / .gitignore 等の先頭ドットファイル名に前方一致していた
（M2 で2回再現）。broad-dot は「ディレクトリ全体を指すトークン」のみに限定する。"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-secrets.sh"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _mkrepo(path):
    """repo に実 .env を置く: broad 判定が真なら deny になる状態を作る。"""
    path.mkdir()
    _git(path, "init")
    (path / ".env").write_text("SECRET=x\n")
    (path / ".env.example").write_text("SECRET=\n")
    (path / ".gitignore").write_text(".env\n")
    return path


def _run(cmd, cwd):
    return subprocess.run(
        ["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True, text=True, cwd=str(cwd),
    ).stdout


# --- 負例: 先頭ドットの個別ファイル add は broad ではない（修正の本体） ---

def test_add_env_example_is_not_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r1")
    out = _run("git add .env.example", cwd=repo)
    assert '"permissionDecision":"deny"' not in out, out


def test_add_gitignore_is_not_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r2")
    out = _run("git add .gitignore", cwd=repo)
    assert '"permissionDecision":"deny"' not in out, out


def test_add_dot_dir_path_is_not_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r3")
    (repo / ".github").mkdir()
    (repo / ".github" / "ci.yml").write_text("x\n")
    out = _run("git add .github/ci.yml", cwd=repo)
    assert '"permissionDecision":"deny"' not in out, out


# --- 正例: broad staging は引き続き deny（回帰ガード） ---

def test_add_bare_dot_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r4")
    out = _run("git add .", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dot_before_shell_delimiter_still_broad(tmp_path):
    """grill 致命1: `.` の直後がシェルデリミタでも broad（境界を空白/行末に
    限定すると `git add .&&git commit` がすり抜け＝moat 後退）。"""
    repo = _mkrepo(tmp_path / "r10")
    out = _run("git add .&&git commit -m x", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out
    out = _run("git add .;true", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dot_with_following_arg_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r5")
    out = _run("git add . foo.txt", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dot_slash_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r6")
    out = _run("git add ./", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dotdot_still_broad(tmp_path):
    sub = _mkrepo(tmp_path / "r7") / "sub"
    sub.mkdir()
    out = _run("git add ..", cwd=sub)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dash_a_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r8")
    out = _run("git add -A", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


# --- 付随: 直接 .env deny 文言に safe variant 案内がある ---

def test_direct_env_deny_mentions_safe_variant(tmp_path):
    repo = _mkrepo(tmp_path / "r9")
    out = _run("git add .env", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out
    assert ".env.example" in out, out
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest -q tests/test_secrets_broad_dot_token.py`
Expected: 負例3件＋文言1件が FAIL（正例5件は PASS）

- [ ] **Step 3: 最小実装**

`hooks/check-secrets.sh:149` の正規表現を変更:

```bash
# 変更前
if printf '%s' "$CMD_LC" | grep -qE "git[[:space:]]+${GIT_PRE_OPTS}add[[:space:]]+(-a|--all|\.)" 2>/dev/null; then
# 変更後（iter56 ①: `\.` はトークン境界非アンカーで .env.example 等の先頭ドット
# ファイル名に前方一致していた。broad-dot は「ディレクトリ全体を指すトークン」
# = . / .. / ./ / ../ に限定する。境界は空白・行末に加えシェルデリミタ ; & | を
# 含める（`git add .&&git commit` のすり抜け＝moat 後退を防ぐ／grill 致命1）
if printf '%s' "$CMD_LC" | grep -qE "git[[:space:]]+${GIT_PRE_OPTS}add[[:space:]]+(-a|--all|\.\.?/?([[:space:];&|]|$))" 2>/dev/null; then
```

（`-a` の非アンカー〔`git add -am` 等への前方一致〕も同型だが pre-existing かつ
deny 方向＝安全側のためスコープ外・記録のみ）

直接 .env deny（`:141` 付近）の文言に safe variant 案内を追記:

```bash
# 変更前
  emit_deny "[secrets] .env ファイルを git に追加しないでください。認証情報がリポジトリに漏洩します。"
# 変更後（iter56 ①付随: .env.test 等は safe-list に入れない設計判断＝中身無検査で
# 「テスト用だから安全」は成立しない。回避策の案内のみ文言で行う）
  emit_deny "[secrets] .env ファイルを git に追加しないでください。認証情報がリポジトリに漏洩します。プレースホルダのみのテンプレートは .env.example / .env.template / .env.sample 名なら追加できます。"
```

- [ ] **Step 4: GREEN 確認＋既存回帰**

Run: `python3 -m pytest -q tests/test_secrets_broad_dot_token.py tests/test_check_secrets_git_dir.py tests/test_secrets_git_variants.py tests/test_secrets_quoted_var_and_cmdsub.py`
Expected: all PASS

- [ ] **Step 5: コミット**

```bash
git add hooks/check-secrets.sh tests/test_secrets_broad_dot_token.py
git commit -m "fix(iter56): check-secrets broad-staging の先頭ドット誤検知を封鎖（①・M2 実測2回）"
```

---

### Task 2: ⑥ full プロファイル配布整合（P1・install 契約）

**Files:**
- Modify: `templates/profiles/full.json`（recommended に4本追加）
- Modify: `scripts/check_framework_contract.py::check_scripts_manifest`（方向4追加）
- Test: `tests/test_scripts_manifest_contract.py`（方向4のテスト追加）
- Test: `tests/test_permission_allowlist_install.py` または新規 `tests/test_full_profile_runnable_scripts.py`（install 実在検証）

**Interfaces:**
- Consumes: `load_scripts_manifest(root)` → `{'scripts/x.py': class}`
- Produces: 方向4検査「manifest の allow|ask ⊆ full プロファイル required+recommended」

- [ ] **Step 1: 失敗するテストを書く（contract 方向4）**

`tests/test_scripts_manifest_contract.py` に追加（既存テストの fixture 流儀に合わせる）:

```python
def test_direction4_runnable_scripts_distributed_in_full_profile():
    """方向4: manifest の実行可クラス（allow|ask）は full プロファイルが配布する。
    M2 実測: retro_report.py が hook ALLOW なのに install 先に無く /retro が
    手動フォールバック化（F6=install 経路の死角の再発形）。"""
    import json
    failures = cfc.check_scripts_manifest(ROOT)
    assert not failures, failures
    # 実データ整合: allow|ask の全エントリが full.json に載っている
    manifest = cfc.load_scripts_manifest(ROOT)
    full = json.loads((ROOT / "templates/profiles/full.json").read_text(encoding="utf-8"))
    distributed = set(full["required"]) | set(full["recommended"])
    runnable = {e for e, c in manifest.items() if c in ("allow", "ask")}
    assert runnable <= distributed, sorted(runnable - distributed)


def test_direction4_detects_missing_distribution(tmp_path):
    """合成違反: allow スクリプトが full.json に無ければ FAIL する。"""
    _copy_fixture_repo(tmp_path)  # 既存 fixture ヘルパに合わせて調整
    full_path = tmp_path / "templates/profiles/full.json"
    import json
    full = json.loads(full_path.read_text(encoding="utf-8"))
    full["recommended"] = [e for e in full["recommended"]
                           if e != "scripts/build-judge-card.py"]
    full_path.write_text(json.dumps(full), encoding="utf-8")
    failures = cfc.check_scripts_manifest(tmp_path)
    assert any("full profile" in f for f in failures), failures
```

（既存ファイルの import 形式・fixture ヘルパ名は現物に合わせる。無ければ最小の
tmp repo 構築ヘルパを同ファイル内に書く）

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest -q tests/test_scripts_manifest_contract.py`
Expected: 新テスト2件 FAIL（方向4未実装＋full.json 4本欠落）

- [ ] **Step 3: 実装（contract 方向4＋full.json）**

`scripts/check_framework_contract.py::check_scripts_manifest` の方向3の後に追加:

```python
    # 方向4 (iter56 ⑥): 実行可クラス（allow|ask）のスクリプトは full プロファイル
    # が配布する。hook が ALLOW してもファイルが install されなければ silent
    # 手動フォールバック（M2 実測: /retro）— F6（install 経路の死角）の再発形。
    # minimal/standard は意図的劣化（scaffold-safe 変種）のため対象外。
    full_profile_path = root / "templates" / "profiles" / "full.json"
    if full_profile_path.is_file():
        try:
            full_profile = json.loads(full_profile_path.read_text(encoding="utf-8"))
            distributed = set(full_profile.get("required", [])) \
                | set(full_profile.get("recommended", []))
            for entry, cls in manifest.items():
                if cls in ("allow", "ask") and entry not in distributed:
                    failures.append(
                        f"scripts-manifest: class={cls} {entry} is not distributed "
                        "by the full profile (add to templates/profiles/full.json)")
        except (json.JSONDecodeError, OSError) as exc:
            failures.append(f"scripts-manifest: cannot read full profile: {exc}")
```

`templates/profiles/full.json` の `recommended` に追加（`scripts/status_doctor.py` の後）:

```json
    "scripts/retro_report.py",
    "scripts/check_reference_drift.py",
    "scripts/learnings_search.py",
    "scripts/lint_names.py",
```

- [ ] **Step 4: install 実在検証テスト**

新規 `tests/test_full_profile_runnable_scripts.py`:

```python
"""iter56 ⑥: full install 先で manifest の実行可スクリプトが実在することを検証。
iter55 の install テストは「hook が allow する」ことのみ検証し、
「ファイルが存在する」ことを検証していなかった。"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_manifest():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cfc", ROOT / "scripts" / "check_framework_contract.py")
    cfc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfc)
    return cfc.load_scripts_manifest(ROOT)


def test_full_install_contains_all_runnable_scripts(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    subprocess.run(
        ["bash", str(ROOT / "bin" / "setup.sh"), "--profile=full",
         "--target", str(target)],
        check=True, capture_output=True, text=True)
    manifest = _load_manifest()
    missing = [e for e, c in manifest.items()
               if c in ("allow", "ask") and not (target / e).is_file()]
    assert not missing, missing
```

（`setup.sh` の target 指定フラグは現物の CLI に合わせる — `--target` が無い場合は
cwd 実行形式に調整）

- [ ] **Step 5: GREEN 確認**

Run: `python3 -m pytest -q tests/test_scripts_manifest_contract.py tests/test_full_profile_runnable_scripts.py tests/test_permission_allowlist_install.py tests/test_profile_referential_integrity.py tests/test_readme_profile_counts.py`
Expected: all PASS（README のプロファイル数記載がズレたら README も更新）

- [ ] **Step 6: コミット**

```bash
git add templates/profiles/full.json scripts/check_framework_contract.py tests/test_scripts_manifest_contract.py tests/test_full_profile_runnable_scripts.py
git commit -m "feat(iter56): full プロファイル配布整合 — 未配布4本追加＋contract 方向4＋install 実在検証（⑥）"
```

---

### Task 3: ② qa ref を claims 付き QA レポートに統一＋テンプレ claims 雛形（⑦b）

**Files:**
- Modify: `.claude/skills/qa-verification/SKILL.md`（手順6・skip 経路・誤記述修正）
- Modify: `templates/QA-REPORT.template.md`・`templates/REVIEW.template.md`・`templates/SECURITY-REVIEW.template.md`（claims 雛形）
- Test: `tests/test_skill_guidance_tokens.py`（新 token 追加）
- Test: `tests/test_judge_card.py`（qa ref=QA レポートで claims が読める）

**Interfaces:**
- Consumes: `read_claims(report_path)`・`resolve_gate_report(root, "qa")`
- Produces: 配布 skill の新規約「`current_refs.qa` = claims 付き QA レポート」

- [ ] **Step 1: 失敗するテストを書く（guidance token）**

`tests/test_skill_guidance_tokens.py` に追加:

```python
class TestQaRefIsClaimsReport(unittest.TestCase):
    def test_qa_ref_points_to_claims_report(self):
        self.assertIn("claims 付き QA レポート", QA,
                      "qa ref の正本規定（claims 付き QA レポート）が消えている")

    def test_old_test_strength_ref_rule_gone(self):
        # grill 致命3: 現文は途中に改行が入るため exact NotIn はすり抜ける。
        # 空白正規化してから assert する。
        normalized = " ".join(QA.split())
        self.assertNotIn(
            "`current_refs.qa` を `docs/qa-reports/test-strength.md` にする", normalized,
            "judge が claims を読めない旧規約（test-strength.md を ref）が残っている")
        self.assertNotIn(
            "`docs/qa-reports/test-strength.md` にすること", normalized,
            "skip 経路の旧規約が残っている")
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest -q tests/test_skill_guidance_tokens.py`
Expected: 新2件 FAIL

- [ ] **Step 3: SKILL.md 修正（語数中立を意識）**

`.claude/skills/qa-verification/SKILL.md`:

1. 手順6を変更:
   - 変更前: `` 6. `current_refs.qa` を `docs/qa-reports/test-strength.md` にする。``
   - 変更後: `` 6. QA レポート（claims 付き・下記）を書き、`current_refs.qa` はその QA レポートにする（judge は ref 先の claims しか読まない。test-strength.md は固定パスの証拠として自動参照される）。``
2. skip 経路の変更:
   - 変更前: 「スキップ時もハーネスがレポートを生成するので、`current_refs.qa` を
     `docs/qa-reports/test-strength.md` にすること（さもないと完了時に証拠不足で弾かれる）。」
   - 変更後: 「スキップ時も claims 付き QA レポートを書き、`current_refs.qa` はそれを
     指すこと（ref は実在ファイルなら受理される。test-strength.md は drill 再生成で
     claims を置けない）。」
3. 「5 項目程度」「19 項目」の文は**触らない**
4. 語数確認: `python3 -c "print(len(open('.claude/skills/qa-verification/SKILL.md').read().split()))"` ≤ 455。
   **削減先を固定（grill 致命5）**: (a) skip 経路の「ただし framework 自体の改修など〜」
   段落の重複説明を圧縮（趣旨は1文で足りる）、(b) 手順6の新文の括弧内補足を最小化。
   置換文は正味 +15〜20 語相当のため削減は必須で発生する

- [ ] **Step 4: テンプレ claims 雛形（⑦b）**

`templates/QA-REPORT.template.md`・`templates/REVIEW.template.md`・
`templates/SECURITY-REVIEW.template.md` の末尾（sentinel コメントの前）に追加:

````markdown
## Claims（judge が機械読取する）

```claims
verdict: <記入: approve / approve_with_notes / reject / blocked>
second_opinion:
  verdict: <記入>
  notes: <2次レビューの要旨 / なし>
```
````

（REVIEW/SECURITY-REVIEW のみ second_opinion を含める。QA-REPORT は `verdict` のみ＝
qa は SECOND_OPINION_GATES 非対象。**grill 致命2/YAGNI**: `approve` プリフィルは
未記入レポートの自己承認化＝禁止。`tests_green` は judge 非消費キーのため入れない。
未記入プレースホルダは Task 4 の未知 verdict 🟡 で必ず可視化される）

- [ ] **Step 5: judge 読取テスト**

`tests/test_judge_card.py` に追加（既存の STATUS/report fixture 流儀に合わせる）:

```python
def test_qa_ref_claims_report_no_claims_yellow(tmp_repo):
    """qa ref が claims 付き QA レポートを指すとき「claims 未提出」🟡 が出ない。"""
    write_status(tmp_repo, refs={"qa": "docs/qa-reports/iter1-qa.md"})
    (tmp_repo / "docs/qa-reports").mkdir(parents=True, exist_ok=True)
    (tmp_repo / "docs/qa-reports/iter1-qa.md").write_text(
        "# QA\n```claims\nverdict: approve\ntests_green: true\n```\n",
        encoding="utf-8")
    v = bjc.compute_verdict(
        "qa", bjc.read_claims(tmp_repo / "docs/qa-reports/iter1-qa.md"),
        _neutral_facts(), None)
    assert not any("claims" in y for y in v.yellow), v.yellow
```

- [ ] **Step 6: GREEN 確認＋周辺検査**

Run: `python3 -m pytest -q tests/test_skill_guidance_tokens.py tests/test_judge_card.py tests/test_completion_evidence_fail_closed.py && python3 scripts/check_reference_drift.py && python3 -c "import importlib.util,pathlib; s=importlib.util.spec_from_file_location('cb','scripts/context_budget.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); f=m.check(pathlib.Path('.')); assert not f, f"`
Expected: all PASS・drift PASS・budget PASS

- [ ] **Step 7: コミット**

```bash
git add .claude/skills/qa-verification/SKILL.md templates/QA-REPORT.template.md templates/REVIEW.template.md templates/SECURITY-REVIEW.template.md tests/test_skill_guidance_tokens.py tests/test_judge_card.py
git commit -m "fix(iter56): qa ref を claims 付き QA レポートに統一＋gate テンプレに claims 雛形（②⑦b・skill×judge 契約整合）"
```

---

### Task 4: ③ verdict 名目差の段階化＋notes 情報行＋⑦a 是正手順文言

**Files:**
- Modify: `scripts/build-judge-card.py`（compute_verdict・Verdict・render_card・build）
- Test: `tests/test_judge_card.py`

**Interfaces:**
- Consumes: claims dict（`verdict:` トップレベル・`second_opinion.verdict`/`second_opinion.notes`）
- Produces: `Verdict.info: list[str]`（非ブロッキング情報行・overall 不算入）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_judge_card.py` に追加:

```python
OK_PAIR = {"verdict": "approve",
           "second_opinion": {"verdict": "approve_with_notes",
                               "notes": "minor 2件は解消済み"}}

def test_ok_class_pair_no_divergence_yellow():
    v = bjc.compute_verdict("review", OK_PAIR, _neutral_facts(),
                            OK_PAIR["second_opinion"])
    assert not any("相違" in y for y in v.yellow), v.yellow

def test_ok_class_pair_emits_notes_info():
    v = bjc.compute_verdict("review", OK_PAIR, _neutral_facts(),
                            OK_PAIR["second_opinion"])
    assert any("minor 2件" in i for i in v.info), v.info

def test_reject_divergence_still_yellow():
    claims = {"verdict": "approve", "second_opinion": {"verdict": "reject"}}
    v = bjc.compute_verdict("review", claims, _neutral_facts(),
                            claims["second_opinion"])
    assert any("相違" in y for y in v.yellow), v.yellow

def test_unknown_verdict_still_yellow():
    claims = {"verdict": "approve", "second_opinion": {"verdict": "lgtm"}}
    v = bjc.compute_verdict("review", claims, _neutral_facts(),
                            claims["second_opinion"])
    assert any("相違" in y for y in v.yellow), v.yellow

def test_placeholder_verdict_pair_is_visible():
    """grill 致命2: 未記入テンプレ（両側とも既知集合外の同値）は相違 🟡 が出ない
    ＝沈黙通過を許さない。既知集合外の verdict 値は値不正 🟡 を出す。"""
    claims = {"verdict": "<記入: approve / approve_with_notes / reject / blocked>",
              "second_opinion": {"verdict": "<記入>"}}
    v = bjc.compute_verdict("review", claims, _neutral_facts(),
                            claims["second_opinion"])
    assert any("verdict" in y and "不正" in y for y in v.yellow), v.yellow

def test_tests_unverified_message_has_remediation():
    facts = _neutral_facts(); facts["tests"] = "unverified"
    v = bjc.compute_verdict("review", None, facts, None)
    assert any("record-test-result" in y for y in v.yellow), v.yellow
```

（`_neutral_facts()` ヘルパが無ければ追加: stubs/secrets 空・tests="green"・deps="clean"）

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest -q tests/test_judge_card.py`
Expected: 新5件 FAIL（`Verdict.info` 不在で AttributeError 含む）

- [ ] **Step 3: 実装**

`scripts/build-judge-card.py`:

```python
# Verdict に info を追加
    def __init__(self, overall: int, red=None, yellow=None, info=None):
        ...（既存）
        self.info = info if info is not None else []   # 非ブロッキング・overall 不算入

# compute_verdict 内の tier-2 比較を置換
    OK_VERDICTS = {"approve", "approve_with_notes"}       # モジュール定数として定義
    KNOWN_VERDICTS = OK_VERDICTS | {"reject", "blocked"}  # 同上
    if gate in SECOND_OPINION_GATES:
        if second_opinion is None:
            yellow.append("第2意見なし（self-attested・要確認）")
        elif claims:
            v1, v2 = claims.get("verdict"), second_opinion.get("verdict")
            both_ok = v1 in OK_VERDICTS and v2 in OK_VERDICTS
            if v1 != v2 and not both_ok:
                # iter56 ③: ok class 同士（approve×approve_with_notes）の名目差は
                # 🟡 にしない（M2 で3ゲート連続 ack＝形骸化）。未知値は ok に含めない
                # （fail-visible）。
                yellow.append(
                    f"1次/2次レビューの相違（self-attested）: 1次={v1} / 2次={v2}")
            # grill 致命2: 既知集合外の verdict 値（テンプレ未記入プレースホルダ含む）
            # は同値でも沈黙させず値不正 🟡 で可視化する。
            for label, val in (("1次", v1), ("2次", v2)):
                if val is not None and val not in KNOWN_VERDICTS:
                    yellow.append(f"{label} verdict 値が不正/未記入: {val}")
            if "approve_with_notes" in (v1, v2):
                notes = second_opinion.get("notes")   # 正位置のみ（YAGNI: top-level fallback なし）
                info.append(f"approve_with_notes の notes: {notes}" if notes
                            else "approve_with_notes — notes の解消状況を確認")

# tests unverified 文言（⑦a）
    elif facts["tests"] == "unverified":
        yellow.append(
            "テスト結果が未検証（記録なし/コード変更後）— 全編集後に "
            "`python3 scripts/record-test-result.py \"python3 -m pytest -q\"` で再記録")

# render_card: yellow の後に info 節
    if v.info:
        lines += ["", "## 💬 情報（非ブロッキング）"] + [f"- {i}" for i in v.info]

# build(): red/yellow の後
    for i in v.info:
        print(f"💬 {i}")
```

（`info = []` の初期化と `Verdict(overall=..., red=red, yellow=yellow, info=info)` への
受け渡しを忘れない）

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m pytest -q tests/test_judge_card.py tests/test_judge_card_push.py`
Expected: all PASS

- [ ] **Step 5: コミット**

```bash
git add scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "feat(iter56): judge の verdict 名目差を段階化＋notes 情報行＋未検証文言に是正手順（③⑦a）"
```

---

### Task 5: ⑤ spec-delta 合格時の1行肯定出力

**Files:**
- Modify: `scripts/check_status.py`（client_ready_for_dev の pre-approve 分岐）
- Test: `tests/test_spec_delta_review.py`

**Interfaces:**
- Consumes: `_spec_delta_required(root)`・`_spec_delta_issues(root)`（判定は不変）
- Produces: stdout 1行 `[spec-delta] CHANGES.md 検査 OK（iteration=N）`（update-gate.sh が承認ログに中継）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_spec_delta_review.py` に追加（既存 fixture 流儀に合わせる）:

```python
def test_pass_emits_positive_line(tmp_repo, capsys):
    """iteration>1 かつ CHANGES.md 合格時、承認ログで「検査が走って合格」と
    「対象外」を区別できる1行を出す（M2: 合格が無言でコード読解が必要だった）。"""
    _write_status(tmp_repo, iteration=2)
    _write_valid_changes_md(tmp_repo)
    rc = check_status.pre_approve_gate(tmp_repo, "client_ready_for_dev")
    out = capsys.readouterr().out
    assert rc == 0
    assert "[spec-delta] CHANGES.md 検査 OK（iteration=2）" in out

def test_iteration1_stays_silent(tmp_repo, capsys):
    _write_status(tmp_repo, iteration=1)
    rc = check_status.pre_approve_gate(tmp_repo, "client_ready_for_dev")
    out = capsys.readouterr().out
    assert rc == 0
    assert "[spec-delta]" not in out
```

（`pre_approve_gate` 相当の関数名・fixture は現物に合わせる）

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest -q tests/test_spec_delta_review.py`
Expected: 新1件目 FAIL

- [ ] **Step 3: 実装**

`scripts/check_status.py` の `client_ready_for_dev` 分岐（`issues` 空で `return 0` する
直前）に追加:

```python
        if issues:
            ...（既存の ERROR 出力）
            return 1
        # iter56 ⑤: required かつ合格時のみ肯定1行（対象外は無言のまま）。
        # 出力のみの追加 — 判定ロジックは動かさない。
        if _spec_delta_required(root):
            print(f"[spec-delta] CHANGES.md 検査 OK（iteration={_iteration_value(root)}）")
        return 0
```

`_iteration_value(root)` が無ければ `_spec_delta_required` が読む iteration 取得部を
小関数に抽出して共用する（重複パースを作らない）。

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m pytest -q tests/test_spec_delta_review.py tests/test_check_status.py tests/test_client_ready_artifact_content.py`
Expected: all PASS

- [ ] **Step 5: コミット**

```bash
git add scripts/check_status.py tests/test_spec_delta_review.py
git commit -m "feat(iter56): spec-delta 合格時に承認ログへ肯定1行を出力（⑤・可視性）"
```

---

### Task 6: ④ subagent-dev 並列規則に共有可変資源の項を追記

**Files:**
- Modify: `.claude/skills/subagent-dev/SKILL.md`（並列実行ルール節）
- Test: `tests/test_skill_guidance_tokens.py`（token 追加）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_skill_guidance_tokens.py` に追加（ファイル冒頭に
`SD = (ROOT / ".claude" / "skills" / "subagent-dev" / "SKILL.md").read_text(encoding="utf-8")` を追加）:

```python
class TestSharedMutableResourceRule(unittest.TestCase):
    def test_shared_resource_rule_present(self):
        self.assertIn("共有可変資源", SD,
                      "並列規則の共有可変資源ルール（M2: テスト DB 衝突）が消えている")
        self.assertIn("同時に起動する1バッチ", SD,
                      "integration 実行タスクの同時1体運用（バッチ定義込み）が消えている")
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest -q tests/test_skill_guidance_tokens.py`
Expected: 新2件 FAIL

- [ ] **Step 3: SKILL.md 追記（残41語以内）**

`.claude/skills/subagent-dev/SKILL.md` の「並列実行ルール」に追加:

```markdown
- **共有可変資源**（テスト DB・ポート・グローバル状態）で衝突するタスクの並列起動は禁止
  （M2 実測: 並行 integration テストが同一テスト DB を TRUNCATE し合い偽 fail。
  vitest の fileParallelism:false はプロセス内のみ有効）
- 標準運用: integration テストを実行するタスクは同時に起動する1バッチにつき 1 体まで
  （unit のみのタスクと組む）。代替: per-agent の DB/スキーマ分離
```

（grill 致命4: 「wave」は本 skill 内で未定義のため「同時に起動する1バッチ」と表現する）

- [ ] **Step 4: GREEN 確認＋budget/drift**

Run: `python3 -m pytest -q tests/test_skill_guidance_tokens.py && python3 scripts/check_reference_drift.py && python3 -c "import importlib.util,pathlib; s=importlib.util.spec_from_file_location('cb','scripts/context_budget.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); f=m.check(pathlib.Path('.')); assert not f, f"`
Expected: all PASS

- [ ] **Step 5: コミット**

```bash
git add .claude/skills/subagent-dev/SKILL.md tests/test_skill_guidance_tokens.py
git commit -m "docs(iter56): subagent-dev 並列規則に共有可変資源ルールを追記（④・M2 テスト DB 衝突）"
```

---

### Task 7: 統合検証

**Files:** なし（検証のみ）

- [ ] **Step 1: full suite**

Run: `python3 -m pytest -q tests/`
Expected: all PASS（前回基準 1285 passed から増加）

- [ ] **Step 2: 決定論検査一式**

```bash
python3 scripts/check_status.py
python3 scripts/check_framework_contract.py
python3 scripts/check_reference_drift.py
python3 scripts/lint_names.py
```

Expected: すべて PASS

- [ ] **Step 3: 実地スモーク（①⑤の実挙動）**

```bash
# ①: 本 repo で（.env なしなので deny 条件は踏まないが、判定行の regex を目視確認）
printf '%s' '{"tool_input":{"command":"git add .env.example"}}' | bash hooks/check-secrets.sh
# ⑤: pre-approve 出力（iteration=56>1 だが Dev モードのため client gate は対象外＝無言で正常）
python3 scripts/check_status.py --pre-approve-gate client_ready_for_dev; echo "rc=$?"
```

- [ ] **Step 4: コミット（残があれば）＋ grill-code へ**

---

## 完了条件

- 候補①〜⑥＋⑦a/b がすべて実装され、各タスクのテストが green
- full suite green・contract/status/drift/lint PASS・context budget PASS
- guidance token（既存「5 項目程度」「19 項目」＋新規4件）green
- コミットはタスク単位・push はユーザー確認まで保留
