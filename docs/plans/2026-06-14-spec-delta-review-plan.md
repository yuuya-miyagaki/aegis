# spec delta review（P2）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development（推奨）または superpowers:executing-plans でタスク単位に実装する。各ステップは `- [ ]` チェックボックスで進捗管理。

**Goal:** `client_ready_for_dev` **ゲート承認時に**、反復2回目以降は前回承認時点からの要件差分を平易な日本語で記す成果物 `docs/handover/CHANGES.md` を必須にし、非エンジニアがコードを読まずに「何がどう変わるか」を確認・承認できるようにする。

**Architecture:** 単一 artifact 検査を `_artifact_content_issue` に切り出し、`iteration > 1`（決定論・STATUS.md）のとき `_spec_delta_issues` として **ゲート承認分岐のみ**で CHANGES を1件検査する。完了検査（共有 `_client_artifact_issues`）には載せない（毎反復の過剰要求を避ける）。ゲートは初回承認後 sticky-approved なので、要件改訂での Client 再入時に `client_ready_for_dev` を reset する手順を docs に明記し、reset→approve で検査が発火することを統合テストで保証する。

**Tech Stack:** Python 3（`scripts/check_status.py`）、Bash（`scripts/update-gate.sh`）、JSON profile、unittest、Makefile（example mirror / context budget ratchet）。

**設計書:** `docs/specs/2026-06-14-spec-delta-review-design.md`（grill-plan C1/C2/C3 反映済み）

---

## 前提知識（実装者向け・本リポジトリ固有）

- **Client ゲート検査**: `scripts/check_status.py` の `_client_artifact_issues(root)`（`:66`）が6成果物を検査。2か所から呼ばれる——ゲート承認時（`check_gate_prerequisites` の `client_ready_for_dev` 分岐 `:945-960`）と完了時（`--check-completion-evidence` の `:514-519`、`client_ready_for_dev == approved` のとき）。
- **本計画の核（C1）**: CHANGES は **`_client_artifact_issues` に入れない**。完了経路は client_ready_for_dev が初回承認後ずっと approved 据え置きのため、共有関数に入れると iteration≥2 の全 Dev 完了で CHANGES を強制してしまう。よって単一検査を `_artifact_content_issue` に切り出し、ゲート分岐でのみ `_spec_delta_issues` を足す。
- **C2（sticky-approved）**: `update-gate.sh approve` は `CURRENT==approved` で「No change needed」即 exit（`:197-200`）し検査を呼ばない。iteration リセットは dev ゲートのみ pending 化（`state-machine.md:24-26`）。要件改訂で Client 再入する際は `client_ready_for_dev` を `reset` してから approve する手順を docs 化し、統合テストで担保する。
- **検査内容**: 各成果物は `(相対パス, sentinel名)`。存在＋`CLIENT_ARTIFACT_MIN_BYTES`（200）以上＋`<!-- aegis-required-section: {sentinel} -->`。deny は `ARTIFACT_TO_TEMPLATE`（`scripts/_artifact_template_map.py`）からテンプレ名を補う。
- **`iteration`**: STATUS.md フロントマター top-level の任意整数（`extract_scalar_value`）。末尾空白を残しうるので `.strip()` 後に `.isdigit()` 判定（要検討1）。
- **テンプレ登録3契約**（`tests/test_profile_checker_parity.py`）: ARTIFACT_TO_TEMPLATE に入れたテンプレは ①full profile recommended に含まれ ②disk 実在。さらに `check_framework_contract.py` の `REQUIRED_TEMPLATE_FILES` にも登録。minimal/standard は Client テンプレを配らない（0/6・full のみ 6/6）ので CHANGES も full のみで一貫。
- **version 同期（suite を落とす hard 要件は3点）**: `FRAMEWORK_VERSION`（`check_framework_contract.py:24`）＝ `templates/STATUS.template.md:3` ＝ `examples/minimal-project/docs/STATUS.md`（contract `:921-935`・mirror 対象外＝手動）。ルート `docs/STATUS.md` は contract 非照合。
- **example mirror**: `scripts/check_status.py`・`scripts/_artifact_template_map.py`・`.claude/skills/client-workflow/SKILL.md`・`.claude/rules/state-machine.md` は `examples/minimal-project/` に byte-identical mirror（`test_mirror_identity.py`）。**編集後 `make example` を実行し再生成物を同じコミットに含める。** templates/・profiles/・check_framework_contract.py・context-budgets.json・docs/ は mirror 対象外。
- **コンテキスト予算（P1）**: `scripts/context_budget.py check` が skill/rule の語数上限を強制（contract `:649` 配線・`tests/test_context_budget.py::TestRealRepo`）。現状 client-workflow=366語/予算387、state-machine=263語/予算290。**手動で `scripts/context-budgets.json` の数値を上げる「明示的拡大」は許可**（Makefile コメント）。
- **全チェック**: `python3 -m pytest tests/`（762件・contract/drift/mirror/eval はテスト内実行）。

---

## File Structure

| 種別 | パス | 責務 |
|------|------|------|
| 新規 | `templates/CHANGES.template.md` | 差分レビュー雛形（5節＋「変更なし」弁＋末尾 sentinel） |
| 変更 | `scripts/check_status.py` | `_artifact_content_issue` 切り出し＋`_spec_delta_required`/`_spec_delta_issues`＋ゲート分岐に CHANGES 検査（完了経路は不変） |
| 変更 | `scripts/_artifact_template_map.py` | `docs/handover/CHANGES.md` → `templates/CHANGES.template.md` |
| 変更 | `templates/profiles/full.json` | `recommended` に CHANGES テンプレ |
| 変更 | `.claude/rules/state-machine.md` | iteration 記述に「Client 再入時は client_ready_for_dev を reset」 |
| 変更 | `.claude/skills/client-workflow/SKILL.md` | handover 行 ＋ Spec Delta 節（reset＋作成手順） |
| 変更 | `scripts/context-budgets.json` | client-workflow / state-machine の予算を明示的拡大 |
| 変更 | `scripts/check_framework_contract.py` | `REQUIRED_TEMPLATE_FILES` 追加 ＋ `FRAMEWORK_VERSION` 1.9.0 |
| 変更 | `templates/STATUS.template.md` | version 1.9.0 |
| 変更 | `examples/minimal-project/docs/STATUS.md` | version 1.9.0（手動） |
| 新規 | `tests/test_spec_delta_review.py` | 単体（pre-approve）＋統合（update-gate reset→approve） |
| 自動 | `examples/minimal-project/...` | `make example` 再生成 |

---

## Task 1: CHANGES テンプレートと登録

ゲートの振る舞いはまだ変えない。テンプレを作り、登録3契約（mapping / profile / contract REQUIRED）を満たす。version は据え置き（Task 4 で bump）。

**Files:**
- Create: `templates/CHANGES.template.md`
- Modify: `scripts/_artifact_template_map.py`、`templates/profiles/full.json`、`scripts/check_framework_contract.py`（REQUIRED のみ）

- [ ] **Step 1: CHANGES テンプレートを作成**

`templates/CHANGES.template.md`:

```markdown
# 変更サマリ（spec delta review）

> このファイルは反復2回目以降（`iteration > 1`）の `client_ready_for_dev`
> ゲートで必須です。前回ゲート承認時点からの要件の差分を、コードを読まなくても
> 分かる平易な日本語で記します。依頼者（非エンジニア）がここを読んで「今回あらたに
> 何を作る／変えるよう依頼しているか」を確認・承認します。
>
> 書き方: `git log -- docs/requirements/` と `git diff` で前回からの変化を把握し、
> 各セクションを埋めてください。要件を変えない反復では、下の「変更なし」に
> チェックを入れ、各セクションは「該当なし」で構いません。

## 今回は要件変更なし

- [ ] 今回の反復では要件を変更していない（理由: ____ ）

（↑にチェックした場合、以下の各セクションは「該当なし」と書いてください）

## この反復で変える理由

（1〜2文。なぜ今回この変更が必要か）

## 追加（新しく作るもの）

-

## 変更（やり方が変わるもの）

-

## 削除・取りやめ

-

## 受入条件・スコープへの影響

（受入条件 `ACCEPTANCE.md` やスコープ `SCOPE.md` にどう影響するか。「影響なし」も明記）

<!-- aegis-required-section: spec-delta -->
```

- [ ] **Step 2: ARTIFACT_TO_TEMPLATE に登録**

`scripts/_artifact_template_map.py`、`"docs/handover/TO-DEV.md"` 行の直後:

```python
    "docs/handover/TO-DEV.md":         "templates/HANDOVER-TO-DEV.template.md",
    "docs/handover/CHANGES.md":        "templates/CHANGES.template.md",
    "docs/translation/mapping.md":     "templates/TRANSLATION-MAPPING.template.md",
```

- [ ] **Step 3: full profile に登録**

`templates/profiles/full.json` の `recommended` 配列に1要素追加（`templates/HANDOVER-TO-DEV.template.md` の隣など）。JSON のカンマに注意:

```json
    "templates/HANDOVER-TO-DEV.template.md",
    "templates/CHANGES.template.md",
```

- [ ] **Step 4: contract の REQUIRED_TEMPLATE_FILES に登録**

`scripts/check_framework_contract.py` の `REQUIRED_TEMPLATE_FILES`、`HANDOVER-TO-DEV.template.md` 行の直後:

```python
    ROOT / "templates/HANDOVER-TO-DEV.template.md",
    ROOT / "templates/CHANGES.template.md",
    ROOT / "templates/HANDOVER-TO-CLIENT.template.md",
```

- [ ] **Step 5: mirror 再生成**

Run: `make example`
Expected: `copy scripts/_artifact_template_map.py`（差分があれば）。

- [ ] **Step 6: 登録契約テストが green**

Run: `python3 -m pytest tests/test_profile_checker_parity.py tests/test_mirror_identity.py -q`
Expected: PASS。

- [ ] **Step 7: 全スイートが green（回帰なし・version 未変更）**

Run: `python3 -m pytest tests/ -q`
Expected: PASS。

- [ ] **Step 8: コミット**

```bash
git add templates/CHANGES.template.md scripts/_artifact_template_map.py templates/profiles/full.json scripts/check_framework_contract.py examples/minimal-project/scripts/_artifact_template_map.py
git commit -m "feat(spec-delta): add CHANGES template and register it (P2)"
```

---

## Task 2: ゲート承認時のみ CHANGES を必須化（振る舞いの核・C1）

`_artifact_content_issue` を切り出し、`_spec_delta_required`/`_spec_delta_issues` を追加して **ゲート分岐のみ**に CHANGES 検査を足す。完了経路 `_client_artifact_issues` は6成果物のまま。テスト先行（RED→GREEN）。

**Files:**
- Test: `tests/test_spec_delta_review.py`（新規）
- Modify: `scripts/check_status.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_spec_delta_review.py`:

```python
#!/usr/bin/env python3
"""P2 (v1.9.0): spec delta review.

client_ready_for_dev GATE-APPROVE requires a plain-language CHANGES.md on the
2nd+ iteration so a non-engineer reviews what changed before re-approving
Client->Dev. iteration <= 1 or absent = not required (fail-open). Enforced at
the gate only (NOT the task-completion symmetric check) so later pure-Dev
iterations are not forced to produce a delta.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_STATUS = ROOT / "scripts" / "check_status.py"

SIX_ARTIFACTS = [
    ("docs/requirements/PRD.md", "prd-context"),
    ("docs/requirements/SCOPE.md", "scope-in-out"),
    ("docs/requirements/NFR.md", "nfr"),
    ("docs/requirements/ACCEPTANCE.md", "acceptance-criteria"),
    ("docs/handover/TO-DEV.md", "handover-to-dev"),
    ("docs/translation/mapping.md", "translation-mapping"),
]


def _filled(sentinel: str) -> str:
    body = ("# Document\n\nSufficient meaningful text exists to clear the "
            "minimum-bytes check. This sample passes 200 bytes and embeds "
            "the machine-readable sentinel comment the harness greps.\n\n")
    return body + f"<!-- aegis-required-section: {sentinel} -->\n"


def _status_md(iteration, gate="pending") -> str:
    iter_line = f"iteration: {iteration}\n" if iteration is not None else ""
    return (
        '---\nframework: aegis\nframework_version: "1.9.0"\n'
        'project_name: "test"\nmode: Client\nphase: handover\n'
        'task_type: feature\ntask_size: M\n' + iter_line +
        'ui_surface: false\nlast_updated: "2026-06-14T00:00:00Z"\n'
        'gate_approvals:\n'
        f'  client_ready_for_dev: {gate}\n  brainstorm: pending\n'
        '  plan: pending\n  review: pending\n  qa: pending\n'
        '  security: pending\n  deploy: pending\n'
        '  dev_ready_for_client: pending\n'
        'current_refs:\n  requirements: []\n  plan: null\n  spec: null\n'
        '  review: null\n  qa: null\n  security: null\n  deploy: null\n'
        '  translation: null\n'
        'external_evidence: []\nfailure_tracking: null\n'
        'next_action: "test"\nblockers: []\nsession_history: []\n---\n\n'
        '## Summary\n\ntest\n')


def _make_project(tmp: Path, iteration, changes, gate="pending") -> None:
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "STATUS.md").write_text(
        _status_md(iteration, gate), encoding="utf-8")
    for rel, sentinel in SIX_ARTIFACTS:
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(_filled(sentinel), encoding="utf-8")
    if changes is not None:
        cp = tmp / "docs" / "handover" / "CHANGES.md"
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(changes, encoding="utf-8")


def _pre_approve(tmp: Path) -> tuple[int, str]:
    r = subprocess.run(
        ["python3", str(CHECK_STATUS), "--root", str(tmp),
         "--pre-approve-gate", "client_ready_for_dev"],
        capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


VALVE = (
    "# 変更サマリ\n\n## 今回は要件変更なし\n\n"
    "- [x] 今回の反復では要件を変更していない（理由: バグ修正のみ）\n\n"
    "## この反復で変える理由\n\n該当なし\n\n"
    "## 追加（新しく作るもの）\n\n該当なし\n\n"
    "## 変更（やり方が変わるもの）\n\n該当なし\n\n"
    "## 削除・取りやめ\n\n該当なし\n\n"
    "## 受入条件・スコープへの影響\n\n影響なし\n\n"
    "<!-- aegis-required-section: spec-delta -->\n")


class TestFirstIterationDoesNotRequireDelta(unittest.TestCase):
    def test_iteration_1_approves_without_changes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 1, changes=None)
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"iteration 1 must approve w/o CHANGES.md. out=\n{out}")

    def test_iteration_absent_approves_without_changes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, None, changes=None)
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"absent iteration must approve (fail-open). out=\n{out}")


class TestLaterIterationRequiresDelta(unittest.TestCase):
    def test_iteration_2_without_changes_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=None)
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"iteration 2 must DENY w/o CHANGES.md. out=\n{out}")
            self.assertIn("docs/handover/CHANGES.md", out)

    def test_iteration_2_short_changes_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2,
                changes="<!-- aegis-required-section: spec-delta -->\n")
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"<200 byte CHANGES.md must DENY. out=\n{out}")

    def test_iteration_2_no_sentinel_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes="x" * 1024)
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"missing sentinel must DENY. out=\n{out}")

    def test_iteration_2_filled_changes_approves(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=_filled("spec-delta"))
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"properly filled CHANGES.md must APPROVE. out=\n{out}")

    def test_iteration_2_no_change_valve_approves(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=VALVE)
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"no-change valve must APPROVE. out=\n{out}")

    def test_iteration_with_trailing_space_is_failopen(self):
        # iteration "2 " (trailing space) must be treated as not-required
        # only if strip makes it digit; we assert strip => required.
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "docs").mkdir(parents=True, exist_ok=True)
            (p / "docs" / "STATUS.md").write_text(
                _status_md("2 "), encoding="utf-8")
            for rel, sentinel in SIX_ARTIFACTS:
                (p / rel).parent.mkdir(parents=True, exist_ok=True)
                (p / rel).write_text(_filled(sentinel), encoding="utf-8")
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"iteration '2 ' must strip->require CHANGES. out=\n{out}")


class TestTemplateCarriesSentinel(unittest.TestCase):
    def test_changes_template_has_sentinel(self):
        p = ROOT / "templates" / "CHANGES.template.md"
        self.assertTrue(p.exists(),
                        "templates/CHANGES.template.md missing")
        text = p.read_text(encoding="utf-8")
        self.assertIn("<!-- aegis-required-section: spec-delta -->", text)


class TestCompletionPathDoesNotRequireDelta(unittest.TestCase):
    """C1: the task-completion symmetric check (client_ready_for_dev approved)
    must NOT demand CHANGES.md even at iteration>1 — only the 6 artifacts."""

    def test_completion_evidence_iteration2_approved_no_changes_ok(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=None, gate="approved")
            r = subprocess.run(
                ["python3", str(CHECK_STATUS), "--root", str(p),
                 "--check-completion-evidence"],
                capture_output=True, text=True)
            combined = r.stdout + r.stderr
            self.assertNotIn("CHANGES.md", combined,
                f"completion check must not demand CHANGES.md. out=\n{combined}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストを実行して RED を確認**

Run: `python3 -m pytest tests/test_spec_delta_review.py -q`
Expected: FAIL。`TestLaterIterationRequiresDelta`（iteration2 で CHANGES なしでも現状 approve）と `test_iteration_with_trailing_space_is_failopen` が失敗。`TestFirstIteration*`・`TestTemplateCarriesSentinel`・`TestCompletionPathDoesNotRequireDelta` は PASS。

- [ ] **Step 3: SPEC_DELTA_ARTIFACT 定数を追加**

`scripts/check_status.py`、`CLIENT_ARTIFACT_MIN_BYTES = 200`（`:63`）の直後:

```python
CLIENT_ARTIFACT_MIN_BYTES = 200

# P2 (v1.9.0): spec delta review. On the 2nd+ iteration the client must review
# what changed since the last cycle before client_ready_for_dev re-approves.
# Enforced at the GATE ONLY (see _spec_delta_issues) — kept OUT of
# CLIENT_GATE_ARTIFACTS and _client_artifact_issues so the task-completion
# symmetric check (which fires while client_ready_for_dev stays approved) does
# not demand a delta on every later Dev iteration. Same existence + min-bytes +
# sentinel contract as the 6.
SPEC_DELTA_ARTIFACT = ("docs/handover/CHANGES.md", "spec-delta")
```

- [ ] **Step 4: `_artifact_content_issue` を切り出す**

`scripts/check_status.py:66-100` の `_client_artifact_issues` を、単一検査ヘルパーに分離する。現状の関数全体を以下に置換:

```python
def _artifact_content_issue(
    root: Path, rel: str, sentinel: str, template_map: dict
) -> str | None:
    """Existence + min-bytes + sentinel check for one artifact.

    Returns a human-readable issue string, or None if it passes. template_map
    (ARTIFACT_TO_TEMPLATE) supplies the deny-message template hint (K-12).
    """
    template_hint = ""
    tmpl = template_map.get(rel)
    if tmpl:
        template_hint = f"（テンプレ: {tmpl}）"
    p = root / rel
    if not p.exists():
        return f"- {rel}: 不在 {template_hint}"
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return f"- {rel}: 読み取り失敗"
    if len(text.encode("utf-8")) < CLIENT_ARTIFACT_MIN_BYTES:
        return (f"- {rel}: 内容が {CLIENT_ARTIFACT_MIN_BYTES} バイト未満 "
                f"（テンプレを実際に埋めてください） {template_hint}")
    marker = f"<!-- aegis-required-section: {sentinel} -->"
    if marker not in text:
        return (f"- {rel}: 必須 sentinel `{marker}` が見つかりません "
                f"（テンプレ末尾のコメントを残してください） {template_hint}")
    return None


def _client_artifact_issues(root: Path) -> list[str]:
    """Return human-readable issues, empty list if all 6 artifacts pass.

    The 6 CLIENT_GATE_ARTIFACTS only. SPEC_DELTA_ARTIFACT is NOT checked here
    (gate-only via _spec_delta_issues) so the task-completion symmetric caller
    is unaffected.
    """
    try:
        from _artifact_template_map import ARTIFACT_TO_TEMPLATE
    except ImportError:
        ARTIFACT_TO_TEMPLATE = {}
    issues: list[str] = []
    for rel, sentinel in CLIENT_GATE_ARTIFACTS:
        issue = _artifact_content_issue(root, rel, sentinel, ARTIFACT_TO_TEMPLATE)
        if issue:
            issues.append(issue)
    return issues


def _spec_delta_required(root: Path) -> bool:
    """True when STATUS.md iteration > 1 (a prior cycle exists, so the client
    must review what changed). iteration absent / non-integer / <=1 => False
    (fail-open). Never raises. Value is stripped before the digit test so a
    trailing space does not silently disable the check."""
    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        return False
    try:
        fm = extract_frontmatter(status_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return False
    if not fm:
        return False
    it = extract_scalar_value(fm, "iteration")
    if it is None:
        return False
    it = it.strip()
    if not it.isdigit():
        return False
    return int(it) > 1


def _spec_delta_issues(root: Path) -> list[str]:
    """Gate-only: when iteration > 1, require docs/handover/CHANGES.md with the
    same existence + min-bytes + sentinel contract. Returns [] when not
    required. Intentionally separate from _client_artifact_issues (C1)."""
    if not _spec_delta_required(root):
        return []
    try:
        from _artifact_template_map import ARTIFACT_TO_TEMPLATE
    except ImportError:
        ARTIFACT_TO_TEMPLATE = {}
    rel, sentinel = SPEC_DELTA_ARTIFACT
    issue = _artifact_content_issue(root, rel, sentinel, ARTIFACT_TO_TEMPLATE)
    return [issue] if issue else []
```

（注: 既存の deny メッセージ文字列は完全に保存される＝`test_profile_checker_parity.py` の "templates/PRD.template.md" 等の部分一致も無傷。`extract_frontmatter`/`extract_scalar_value` は後方定義だが呼び出し時解決で問題なし。）

- [ ] **Step 5: ゲート分岐に CHANGES 検査を足す**

`scripts/check_status.py:950`（`check_gate_prerequisites` の `client_ready_for_dev` 分岐）。現状:

```python
        issues = _client_artifact_issues(root)
        if issues:
```

を:

```python
        issues = _client_artifact_issues(root)
        issues.extend(_spec_delta_issues(root))  # P2: gate-only spec delta (iteration>1)
        if issues:
```

（完了経路 `:514-519` は `_client_artifact_issues` のみを呼ぶので不変。）

- [ ] **Step 6: テストを実行して GREEN を確認**

Run: `python3 -m pytest tests/test_spec_delta_review.py -q`
Expected: PASS（全テスト）。

- [ ] **Step 7: mirror 再生成**

Run: `make example`
Expected: `copy scripts/check_status.py`。

- [ ] **Step 8: 既存テストと全スイートが green（回帰なし）**

Run: `python3 -m pytest tests/test_client_ready_artifact_content.py tests/ -q`
Expected: PASS。`test_client_ready_artifact_content.py`（fixture iteration:1＝CHANGES 不要）が無傷であること。

- [ ] **Step 9: コミット**

```bash
git add tests/test_spec_delta_review.py scripts/check_status.py examples/minimal-project/scripts/check_status.py
git commit -m "feat(spec-delta): require CHANGES.md at iteration>1 gate approval (P2)"
```

---

## Task 3: 再入リセットの明文化＋作成手順（C2）＋統合テスト

要件改訂で Client 再入する際に `client_ready_for_dev` を reset する手順を docs に明記し、reset→approve でゲート検査が発火することを update-gate.sh 経由の統合テストで保証する。skill には作成手順（git diff から執筆）も足す。skill/rule に語を足すと予算を超えるので明示的に拡大する。

**Files:**
- Modify: `.claude/rules/state-machine.md`、`.claude/skills/client-workflow/SKILL.md`、`scripts/context-budgets.json`
- Modify: `tests/test_spec_delta_review.py`（統合テスト追記）

- [ ] **Step 1: 統合テストを追記（RED）**

`tests/test_spec_delta_review.py` の末尾 `if __name__` の前に追記:

```python
UPDATE_GATE = ROOT / "scripts" / "update-gate.sh"


def _run_gate(root: Path, action: str) -> tuple[int, str]:
    # update-gate.sh resolves root via SCRIPT_DIR/..; symlink read-only trees.
    # .claude must be a REAL dir (not a symlink) so the gate snapshot/lock do
    # not leak into the framework repo's live .claude (order-dependent flake).
    for d in ("scripts", "hooks", "templates"):
        if not (root / d).exists():
            (root / d).symlink_to(ROOT / d)
    (root / ".claude").mkdir(exist_ok=True)
    r = subprocess.run(
        ["bash", str(root / "scripts" / "update-gate.sh"),
         "client_ready_for_dev", action, "--ack", "test"],
        capture_output=True, text=True, cwd=str(root))
    return r.returncode, r.stdout + r.stderr


class TestReEntryResetWorkflow(unittest.TestCase):
    """C2: sticky-approved gate short-circuits; after reset the gate-time
    spec-delta check fires. Exercises the real update-gate.sh path."""

    def test_sticky_approved_then_reset_enforces_delta(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            # iteration 2, gate already approved (post first-cycle), no CHANGES.
            _make_project(p, 2, changes=None, gate="approved")

            # 1) approve while already approved => short-circuit, no check.
            rc, out = _run_gate(p, "approve")
            self.assertEqual(rc, 0,
                f"already-approved approve must short-circuit. out=\n{out}")

            # 2) reset => pending.
            rc, out = _run_gate(p, "reset")
            self.assertEqual(rc, 0, f"reset must succeed. out=\n{out}")

            # 3) approve now runs the check; iteration>1 + no CHANGES => DENY.
            rc, out = _run_gate(p, "approve")
            self.assertNotEqual(rc, 0,
                f"post-reset approve must DENY w/o CHANGES. out=\n{out}")
            self.assertIn("docs/handover/CHANGES.md", out)

            # 4) add CHANGES => approve succeeds.
            (p / "docs" / "handover" / "CHANGES.md").write_text(
                _filled("spec-delta"), encoding="utf-8")
            rc, out = _run_gate(p, "approve")
            self.assertEqual(rc, 0,
                f"approve with filled CHANGES must succeed. out=\n{out}")
```

Run: `python3 -m pytest tests/test_spec_delta_review.py::TestReEntryResetWorkflow -q`
Expected: PASS（Task 2 の実装で既にゲート検査は入っているので、この統合テストは緑になるはず。RED 確認のため Task 2 未実装で走らせると step3 が緑＝偽陽性になる点に注意——本テストは「reset 手順が機能する」ことの回帰固定であり、実装は Task 2 で完了済み）。

- [ ] **Step 2: state-machine.md に reset を明記**

`.claude/rules/state-machine.md:24-26` の Iteration 段落の直後に1文追加:

```
Iteration: after `dev_ready_for_client`, new task resets to `brainstorm`,
clears dev gates to `pending`, sets non-requirements refs to null,
increments `iteration`, keeps `current_refs.requirements`.
When re-entering `Client` to revise requirements, also `reset`
`client_ready_for_dev` before re-requesting it; an approved gate short-circuits
re-approval and skips the spec-delta check.
```

- [ ] **Step 3: client-workflow skill に handover 行＋Spec Delta 節**

`.claude/skills/client-workflow/SKILL.md` の handover 行（`:28`）産出物セルに `（反復2回目以降は docs/handover/CHANGES.md も）` を追記。さらに `## Translation Artifact` 節の直後に新節:

```markdown
## Spec Delta（反復2回目以降）

要件改訂で Client モードに再入し `client_ready_for_dev` を申請するときは、
`docs/handover/CHANGES.md` を作成すること。前回ゲート承認時点からの要件差分を、
コードを読まなくても分かる平易な日本語で記し、依頼者が「何がどう変わるか」を確認・承認できるようにする。

- まず `client_ready_for_dev` を `reset` する（approved 据え置きだと再承認が短絡し検査が走らない）
- テンプレート: `templates/CHANGES.template.md`
- 書き方: `git log -- docs/requirements/` と `git diff` で前回からの変化を把握して埋める
- 要件を変えない反復では、テンプレ冒頭「変更なし」にチェックし各セクションを「該当なし」にする
- Gate 契約: `iteration > 1` のとき存在＋200バイト＋sentinel を検査（初回・iteration 無しは不要）
```

- [ ] **Step 4: 予算超過を確認（RED）**

Run: `python3 scripts/context_budget.py check`
Expected: FAIL。`client-workflow/SKILL.md: NNN words > 387` と `state-machine.md: MMM words > 290` の行。

- [ ] **Step 5: 予算を明示的に拡大**

`wc -w .claude/skills/client-workflow/SKILL.md .claude/rules/state-machine.md` で実語数を確認し、`scripts/context-budgets.json` の2行を実測×1.1 を上回る整数へ引き上げる。例（client-workflow が 460語・state-machine が 290語の場合）:

```json
    ".claude/skills/client-workflow/SKILL.md": 510,
```
```json
    ".claude/rules/state-machine.md": 320,
```

（P1 の sanctioned「明示的拡大」。値は必ず `wc -w` 実測×1.1 以上にする。）

- [ ] **Step 6: 予算チェックが green**

Run: `python3 scripts/context_budget.py check && python3 -m pytest tests/test_context_budget.py -q`
Expected: PASS。

- [ ] **Step 7: mirror 再生成**

Run: `make example`
Expected: `copy .claude/rules/state-machine.md` と `copy .claude/skills/client-workflow/SKILL.md`。

- [ ] **Step 8: 全スイートが green**

Run: `python3 -m pytest tests/ -q`
Expected: PASS（mirror identity・context budget・skill reachability すべて）。

- [ ] **Step 9: コミット**

```bash
git add .claude/rules/state-machine.md .claude/skills/client-workflow/SKILL.md scripts/context-budgets.json tests/test_spec_delta_review.py examples/minimal-project/.claude/rules/state-machine.md examples/minimal-project/.claude/skills/client-workflow/SKILL.md
git commit -m "docs(spec-delta): document client gate reset on re-entry + authoring (P2 C2)"
```

---

## Task 4: バージョン bump（1.9.0）と全回帰

**Files:**
- Modify: `scripts/check_framework_contract.py`（FRAMEWORK_VERSION）、`templates/STATUS.template.md`、`examples/minimal-project/docs/STATUS.md`

- [ ] **Step 1: FRAMEWORK_VERSION を 1.9.0 へ**

`scripts/check_framework_contract.py:24`:

```python
FRAMEWORK_VERSION = "1.9.0"
```

- [ ] **Step 2: STATUS.template の version を 1.9.0 へ**

`templates/STATUS.template.md:3`:

```
framework_version: "1.9.0"
```

- [ ] **Step 3: example STATUS.md の version を 1.9.0 へ**

`examples/minimal-project/docs/STATUS.md` の `framework_version:` 行（mirror 対象外＝手動）を `"1.9.0"` に。確認: `grep -n framework_version examples/minimal-project/docs/STATUS.md`

- [ ] **Step 4: contract が green**

Run: `python3 scripts/check_framework_contract.py; echo "rc=$?"`
Expected: `rc=0`（version mismatch なし）。

- [ ] **Step 5: 全回帰（pytest 全件 ＋ mirror 確認）**

Run: `make example && python3 -m pytest tests/ -q`
Expected: `make example` は追加差分なし（version 系は mirror 対象外）。pytest 全件 PASS（既知 flake `test_failure_policy` を除き新規失敗ゼロ）。

- [ ] **Step 6: コミット**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md examples/minimal-project/docs/STATUS.md
git commit -m "chore(spec-delta): bump framework version to 1.9.0 (P2)"
```

---

## グリル（実装後・必須）

`grill-code` で実装済みコードをグリル。重点:
- `_spec_delta_required` の fail-open（iteration 欠落・非数値・末尾空白・読取失敗）が「不要」に倒れるか。`.strip()` が効いているか。
- 完了経路（`--check-completion-evidence`・iteration>1・approved・no-CHANGES）が CHANGES を要求しない（C1 の核）。`TestCompletionPathDoesNotRequireDelta` で固定済み。
- sticky-approved→reset→approve で検査が発火（C2）。`TestReEntryResetWorkflow` で固定済み。
- deny に `templates/CHANGES.template.md` のヒントが載るか。
- 「変更なし」弁が approve するか。

---

## Self-Review（計画↔仕様の突合）

- **仕様カバレッジ**: 設計 §4.2（構造）→Task1、§4.3（C1 ゲート限定）→Task2 Step4-5、§4.4/§6（C2 reset）→Task3、§5/§5.1（トリガ・strip）→Task2 Step3-4、§8（一覧）→全Task、§9（テスト）→Task2/3、§10（版3点）→Task4。漏れなし。
- **C1 反映**: CHANGES を `_spec_delta_issues` に隔離しゲート分岐のみ。完了経路 `_client_artifact_issues` は6成果物のまま＝`TestCompletionPathDoesNotRequireDelta` で固定。
- **C2 反映**: state-machine＋skill に reset 明記、`TestReEntryResetWorkflow` が update-gate.sh 経由で実証。
- **型整合**: `_artifact_content_issue(root,rel,sentinel,map)->str|None`、`_spec_delta_required(root)->bool`、`_spec_delta_issues(root)->list[str]`、`_client_artifact_issues(root)->list[str]`（シグネチャ不変）。
- **version 3点**: FRAMEWORK_VERSION / STATUS.template / example STATUS.md を Task4 で同時 bump。
- **mirror**: check_status.py・_artifact_template_map.py・state-machine.md・client-workflow skill の4つで `make example` を各 Task に配線。
- **No Placeholders**: 全ステップに実コード・実コマンド・期待値。Task3 Step5 の予算値のみ `wc -w` 実測依存だが算出規則（実測×1.1 以上）を明示。
