# evidence 完了強制化（TaskCompleted）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `validate_status_file` が既に持つ gate-ref 整合性＋ref 実在の不変条件をヘルパに切り出して再利用し、`check-task-completed.sh` から TaskCompleted 時に強制する（exit 2 差し戻し）。

**Architecture:** `check_status.py:546-586` のロジックを `evidence_integrity_violations(refs, approvals, root)` に抽出し、`validate_status_file`（出力不変）と新フラグ `--check-completion-evidence` の両方が呼ぶ。重複インライン `gate_ref_mapping`（`547`/`747`）を定数 `GATE_REF_MAPPING` に統一。新規ロジックは書かない＝drift ゼロ。

**Tech Stack:** Python（unittest・正規表現パーサ・PyYAML 非依存）、Bash hook、Markdown 規約。

**設計書:** `docs/plans/2026-06-06-v1-evidence-completion-hook-design.md`（grill-plan 反映改訂版）

---

## ベースライン（着手前に確認）

`aegis/` で実行:

- `python3 -m unittest discover -s tests -q 2>&1 | tail -2` → `Ran 186 tests ... OK`
- `python3 scripts/check_framework_contract.py` → exit 0 / `python3 scripts/check_reference_drift.py` → exit 0
- 現行 version: `FRAMEWORK_VERSION = "0.12.5"`（`scripts/check_framework_contract.py:17`）/ `framework_version: "0.12.5"`（`templates/STATUS.template.md:3`）
- 既存の canonical `gate_ref_mapping`（`scripts/check_status.py:547` と `:747` にインライン重複）= `{plan:plan, review:review, qa:qa, security:security, deploy:deploy, client_ready_for_dev:translation}`

> **⚠ footgun**:
> - `scripts/check_status.py`・`hooks/check-task-completed.sh` は root/example **IDENTICAL** → 同一変更を両方に。
> - ヘルパ抽出は **`validate_status_file` の出力メッセージ不変**が必須（既存テストを壊さない）。`546-586` の置換と `747` の定数化を**両方**やる。
> - hook はスクリプトを `${DEFAULT_ROOT}/scripts/check_status.py`、検査対象を `--root "$ROOT"`（`AEGIS_ROOT_OVERRIDE` 尊重）。ROOT とスクリプト所在を混同しない。
> - 逆 stale チェック（pending ゲートに ref 残存＝違反）も再利用に含まれる。clean テストは全ゲート pending＋全 ref null にすること。
> - **ドッグフード自己ブロック**: 実装中の live `docs/STATUS.md` を整合に保つ（現状 plan pending・spec 実在で安全）。
> - `session_history` は contract が**最大3件**で FAIL 強制。

---

## Task 1: evidence_integrity_violations 抽出＋フラグ（TDD）

**Files:**
- Test: `tests/test_check_status.py`（新規 `TestCheckCompletionEvidence` クラス）
- Modify: `scripts/check_status.py`（定数抽出・ヘルパ抽出・`validate_status_file`/`pre_approve_gate` 置換・フラグ）
- Modify: `examples/minimal-project/scripts/check_status.py`（IDENTICAL 同期）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_check_status.py` 末尾（`if __name__` の前）に追加。`make_status_md`・`run_check`・`TempProject` は既存ヘルパ。

```python
# =============================================================================
# --check-completion-evidence tests (reuses evidence_integrity_violations)
# =============================================================================

# Evidence-coupled gates forced pending to isolate each test (DEFAULT_APPROVALS
# marks plan/brainstorm approved otherwise).
ALL_PENDING = {
    "review": "pending", "qa": "pending", "security": "pending",
    "deploy": "pending", "plan": "pending", "client_ready_for_dev": "pending",
}


class TestCheckCompletionEvidence(unittest.TestCase):
    """--check-completion-evidence: gate-ref integrity + ref existence at completion."""

    def test_clean_status_no_violations(self):
        content = make_status_md(approvals=dict(ALL_PENDING))  # gates pending, refs null
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-completion-evidence")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "", f"clean STATUS must yield no violations, got: {out}")

    def test_approved_gate_null_ref_violates(self):
        for gate in ("review", "qa", "security", "deploy", "plan"):
            appr = dict(ALL_PENDING)
            appr[gate] = "approved"
            content = make_status_md(approvals=appr)  # matching ref stays null
            with self.subTest(gate=gate), TempProject(content) as root:
                rc, out = run_check(root, "--check-completion-evidence")
                self.assertIn("EVIDENCE:", out, f"{gate} approved+null must violate")
                self.assertIn(gate, out)

    def test_approved_gate_existing_ref_ok(self):
        content = make_status_md(approvals={**ALL_PENDING, "qa": "approved"},
                                 refs={"qa": "docs/qa-reports/qa1.md"})
        with TempProject(content) as root:
            (Path(root) / "docs" / "qa-reports").mkdir(parents=True)
            (Path(root) / "docs" / "qa-reports" / "qa1.md").write_text("ok")
            rc, out = run_check(root, "--check-completion-evidence")
            self.assertEqual(out, "", f"approved gate + real ref must pass, got: {out}")

    def test_approved_gate_missing_file_violates(self):
        content = make_status_md(approvals={**ALL_PENDING, "qa": "approved"},
                                 refs={"qa": "docs/qa-reports/missing.md"})
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-completion-evidence")
            self.assertIn("EVIDENCE:", out, "approved gate + missing file must violate")
            self.assertIn("missing", out)

    def test_pending_gate_with_ref_is_stale_violation(self):
        # reuse semantics: a ref present under a pending gate is a stale-ref violation
        content = make_status_md(approvals=dict(ALL_PENDING),
                                 refs={"qa": "docs/qa-reports/qa1.md"})
        with TempProject(content) as root:
            (Path(root) / "docs" / "qa-reports").mkdir(parents=True)
            (Path(root) / "docs" / "qa-reports" / "qa1.md").write_text("ok")
            rc, out = run_check(root, "--check-completion-evidence")
            self.assertIn("EVIDENCE:", out, "pending gate + present ref must be stale violation")
            self.assertIn("stale", out)

    def test_requirements_missing_file_violates(self):
        # extract_current_refs only parses a multi-line YAML list (4-space "- item")
        # as a list; an inline "[x]" on one line is read as a scalar string and would
        # be skipped. So write the STATUS directly with a real list (not make_status_md).
        content = (
            '---\nframework: aegis\nframework_version: "0.12.0"\n'
            "project_name: test\nmode: Dev\nphase: implement\n"
            'task_type: feature\ntask_size: L\nlast_updated: "2026-01-01"\n'
            "gate_approvals:\n  review: pending\n  qa: pending\n  security: pending\n"
            "  deploy: pending\n  plan: pending\n  client_ready_for_dev: pending\n"
            "current_refs:\n  requirements:\n    - docs/requirements/r1.md\n"
            "  plan: null\n  spec: null\n  review: null\n  qa: null\n"
            "  security: null\n  deploy: null\n  translation: null\n"
            "next_action: test\nblockers: []\nsession_history: []\n---\n"
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-completion-evidence")
            self.assertIn("EVIDENCE:", out, "missing requirements file must violate")
            self.assertIn("requirements", out)

    def test_missing_status_no_violations(self):
        with tempfile.TemporaryDirectory() as empty_root:
            rc, out = run_check(empty_root, "--check-completion-evidence")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "", f"missing STATUS must be fail-safe, got: {out}")
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m unittest tests.test_check_status -v 2>&1 | grep -E "CompletionEvidence|FAIL|ERROR|OK"`
Expected: 全メソッドが FAIL/ERROR（`--check-completion-evidence` フラグ未定義で argparse exit 2）。

- [ ] **Step 3: GATE_REF_MAPPING 定数を追加（root）**

`scripts/check_status.py` の `REF_CHECK_ERROR_VERSION = "0.13.0"`（line 33 付近）の直後に追加:

```python
# Canonical gate -> evidence-ref mapping. Single source of truth reused by
# validate_status_file, pre_approve_gate, and evidence_integrity_violations
# (mirrored in bash by update-gate.sh's get_ref_key).
GATE_REF_MAPPING = {
    "plan": "plan",
    "review": "review",
    "qa": "qa",
    "security": "security",
    "deploy": "deploy",
    "client_ready_for_dev": "translation",
}
```

- [ ] **Step 4: ヘルパ `evidence_integrity_violations` を追加（root）**

`def validate_status_file(` の**直前**に追加:

```python
def evidence_integrity_violations(
    refs: "dict[str, list[str] | str]",
    approvals: "dict[str, str]",
    root: Path,
) -> list[str]:
    """Gate<->ref consistency + ref-file existence. Returns bare violation
    messages WITHOUT a path prefix, so validate_status_file can prepend the
    path and --check-completion-evidence can use them directly. Never raises."""
    violations: list[str] = []
    try:
        for gate_key, ref_key in GATE_REF_MAPPING.items():
            gate_value = approvals.get(gate_key)
            ref_value = refs.get(ref_key)
            ref_is_empty = ref_value is None or ref_value == "null" or ref_value == []
            if gate_value == "approved" and ref_is_empty:
                violations.append(
                    f"gate '{gate_key}' is approved but current_refs.{ref_key} is empty"
                )
            if gate_value in {"pending", "n/a"} and not ref_is_empty:
                violations.append(
                    f"gate '{gate_key}' is '{gate_value}' but current_refs.{ref_key} "
                    f"still has a value (stale ref: {ref_value})"
                )

        for key in ("plan", "spec", "review", "qa", "security", "deploy", "translation"):
            value = refs.get(key)
            if isinstance(value, str) and value != "null":
                if not (root / value).exists():
                    violations.append(f"points to missing {key} ref: {value}")

        requirements = refs.get("requirements")
        if isinstance(requirements, list):
            for rel_path in requirements:
                if not (root / rel_path).exists():
                    violations.append(f"points to missing requirements ref: {rel_path}")
    except Exception:
        return []
    return violations
```

- [ ] **Step 5: `validate_status_file` を置換（root・出力不変）**

`scripts/check_status.py` の「`# Validate gate ↔ ref consistency.`」（現 546 付近）から **requirements 実在チェックの末尾（現 586）まで**を、以下へ置換（インライン `gate_ref_mapping` 定義＋approved/stale の2チェック＋`root = path.parent.parent`＋scalar/requirements 実在の2ループ、を**まとめて削除**して置換）:
- new:
```python
    # Gate<->ref consistency + ref existence (shared with --check-completion-evidence;
    # messages identical to the previous inline form via the path prefix below).
    root = path.parent.parent
    for m in evidence_integrity_violations(refs, approvals, root):
        failures.append(f"{path} {m}")
```
> ⚠ 境界厳守: `refs` は既に `528`、`approvals` も既出なので**再取得しない**（上記 new は既存変数を使う）。置換は **`588` の `history = extract_session_history(...)` の手前まで**。旧 scalar/requirements 実在ループ（旧 573-586）の**消し残し＝二重出力**を必ず目視確認。検出は Step 8/10 の「`validate_status_file` 既存テスト緑」で担保。

- [ ] **Step 6: `pre_approve_gate` のインライン dict を定数参照に（root）**

`scripts/check_status.py:747` 付近のインライン `gate_ref_mapping = { ... }` を削除し、参照箇所を `GATE_REF_MAPPING` に変更:
- old:
```python
    gate_ref_mapping = {
        "plan": "plan",
        "review": "review",
        "qa": "qa",
        "security": "security",
        "deploy": "deploy",
        "client_ready_for_dev": "translation",
    }
    if gate_name in gate_ref_mapping:
        ref_key = gate_ref_mapping[gate_name]
```
- new:
```python
    if gate_name in GATE_REF_MAPPING:
        ref_key = GATE_REF_MAPPING[gate_name]
```

- [ ] **Step 7: argparse フラグと dispatch を追加（root）**

`--check-status-health` の add_argument 直後に追加:
```python
    parser.add_argument("--check-completion-evidence", dest="check_completion_evidence",
                        action="store_true",
                        help="Check STATUS.md gate-ref evidence integrity at task "
                             "completion (used by check-task-completed.sh)")
```
dispatch を `check_status_health` 分岐の直後に追加:
```python
    if args.check_completion_evidence:
        status_path = root / "docs" / "STATUS.md"
        if status_path.exists():
            frontmatter = extract_frontmatter(read_text(status_path))
            if frontmatter is not None:
                refs = extract_current_refs(frontmatter)
                approvals = extract_approval_map(frontmatter)
                for v in evidence_integrity_violations(refs, approvals, root):
                    print(f"EVIDENCE: {v}")
        return 0
```

- [ ] **Step 8: テストを実行して PASS を確認（root）**

Run: `python3 -m unittest tests.test_check_status -v 2>&1 | grep -E "CompletionEvidence|gate|ref|FAIL|ERROR|OK" | tail -25`
Expected: 新 7 メソッド全 ok、かつ `validate_status_file` 既存テスト（gate-ref / missing ref 系）も緑のまま。FAIL/ERROR なし。

- [ ] **Step 9: example に同一同期（IDENTICAL）**

`examples/minimal-project/scripts/check_status.py` に Step 3〜7 と**完全同一**の変更を適用。

- [ ] **Step 10: IDENTICAL / drift / contract / 全テスト**

Run: `diff scripts/check_status.py examples/minimal-project/scripts/check_status.py && echo IDENTICAL; python3 scripts/check_reference_drift.py; echo "drift=$?"; python3 scripts/check_framework_contract.py; echo "contract=$?"; python3 -m unittest tests.test_check_status -v 2>&1 | grep -E "translation_ref|gate_ref|FAIL|ERROR" ; python3 -m unittest discover -s tests -q 2>&1 | tail -2`
Expected: `IDENTICAL`、`drift=0`、`contract=0`。message 不変の名指し確認として `test_translation_ref_missing_file_fails`/`test_translation_ref_exists_passes`/`test_*_gate_ref_*` が ok（FAIL/ERROR なし）。`Ran 193 tests ... OK`（186 + 新 7）。件数は実値に合わせる。

- [ ] **Step 11: コミット**

```bash
git add scripts/check_status.py examples/minimal-project/scripts/check_status.py tests/test_check_status.py
git commit -m "$(cat <<'EOF'
refactor(status): extract evidence_integrity_violations + --check-completion-evidence

Factors the gate<->ref consistency and ref-existence checks out of
validate_status_file into a reusable helper (output unchanged), dedupes the
gate_ref_mapping into a GATE_REF_MAPPING constant (was inline in 3 places),
and exposes --check-completion-evidence for the TaskCompleted hook. No new
logic — the completion check now stays lock-step with the contract.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: check-task-completed.sh の配線（TDD）

**Files:**
- Test: `tests/test_hook_output_schema.py`（`TestTaskCompletedHook` に2メソッド＋ヘルパ追加）
- Modify: `hooks/check-task-completed.sh`（next_action 分岐の後・`# Pass-through.` の前）
- Modify: `examples/minimal-project/hooks/check-task-completed.sh`（IDENTICAL 同一 Edit）

- [ ] **Step 1: 失敗するテストを書く**

`TestTaskCompletedHook` クラス内に追加（`run_hook` は同ファイルの env-merge 版）:

```python
    def _write_status_full(self, *, next_action: str, approvals: dict, refs: dict):
        gate_lines = "\n".join(f"  {k}: {v}" for k, v in approvals.items())
        ref_lines = "\n".join(f"  {k}: {v}" for k, v in refs.items())
        path = Path(self.tmp) / "docs" / "STATUS.md"
        path.write_text(
            "---\n"
            "phase: implement\n"
            "mode: Dev\n"
            f"next_action: {next_action}\n"
            "gate_approvals:\n"
            f"{gate_lines}\n"
            "current_refs:\n"
            f"{ref_lines}\n"
            "---\n"
        )

    def test_push_back_when_evidence_missing(self):
        """qa approved but current_refs.qa null → exit 2 with evidence reason."""
        self._write_status_full(
            next_action="Move to security phase",
            approvals={"qa": "approved", "review": "pending", "security": "pending",
                       "deploy": "pending", "plan": "pending"},
            refs={"qa": "null", "review": "null", "security": "null",
                  "deploy": "null", "plan": "null", "spec": "null", "translation": "null"},
        )
        rc, out, err = run_hook(
            "check-task-completed.sh", self._payload("QA done"),
            cwd=Path(self.tmp), env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 2, "evidence violation must push back via exit 2")
        self.assertEqual(out, {}, "stdout empty on push-back; stderr carries reason")
        self.assertIn("task-completed", err)
        self.assertIn("qa", err)

    def test_pass_through_when_evidence_clean(self):
        """All coupled gates pending, refs null, next_action set → pass through."""
        self._write_status_full(
            next_action="Move to qa phase",
            approvals={"qa": "pending", "review": "pending", "security": "pending",
                       "deploy": "pending", "plan": "pending"},
            refs={"qa": "null", "review": "null", "security": "null",
                  "deploy": "null", "plan": "null", "spec": "null", "translation": "null"},
        )
        rc, out, err = run_hook(
            "check-task-completed.sh", self._payload("Impl step done"),
            cwd=Path(self.tmp), env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0, f"clean evidence must pass through, got rc={rc} err={err}")
        self.assertEqual(out, {})
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m unittest tests.test_hook_output_schema -v 2>&1 | grep -E "evidence|FAIL|ERROR|OK"`
Expected: `test_push_back_when_evidence_missing` が FAIL（現行 hook は evidence 未検査で rc 0）、`test_pass_through_when_evidence_clean` は PASS。

- [ ] **Step 3: hook に evidence チェックを実装（root）**

`hooks/check-task-completed.sh` を Edit:
- old:
```bash
  printf '[task-completed] TaskCompleted (subject: %s) しましたが STATUS.md next_action が未更新です。完了前に next_action を更新してください。\n' "$SUBJECT_PREVIEW" >&2
  exit 2
fi

# Pass-through.
emit_allow
exit 0
```
- new:
```bash
  printf '[task-completed] TaskCompleted (subject: %s) しましたが STATUS.md next_action が未更新です。完了前に next_action を更新してください。\n' "$SUBJECT_PREVIEW" >&2
  exit 2
fi

# Evidence integrity: reuse validate_status_file's gate<->ref + existence checks
# at completion time. python3 absent → pass-through (soft 差し戻し, not a deny).
EVIDENCE=$(python3 "${DEFAULT_ROOT}/scripts/check_status.py" --root "$ROOT" --check-completion-evidence 2>/dev/null || true)
if [ -n "$EVIDENCE" ]; then
  SUBJECT_PREVIEW=$(printf '%s' "$SUBJECT" | head -c 80 | tr '\n' ' ')
  printf '[task-completed] TaskCompleted (subject: %s) しましたが evidence 整合性に違反があります:\n%s\n完了前に STATUS.md を修正してください。\n' "$SUBJECT_PREVIEW" "$EVIDENCE" >&2
  exit 2
fi

# Pass-through.
emit_allow
exit 0
```

- [ ] **Step 4: example に同一 Edit（IDENTICAL）**

`examples/minimal-project/hooks/check-task-completed.sh` に Step 3 と**完全同一**の Edit。

- [ ] **Step 5: IDENTICAL 確認**

Run: `diff hooks/check-task-completed.sh examples/minimal-project/hooks/check-task-completed.sh && echo IDENTICAL`
Expected: `IDENTICAL`

- [ ] **Step 6: テストを実行して PASS**

Run: `python3 -m unittest tests.test_hook_output_schema -v 2>&1 | grep -E "evidence|FAIL|ERROR|OK"`
Expected: 両テスト ok、FAIL/ERROR なし。

- [ ] **Step 7: コミット**

```bash
git add hooks/check-task-completed.sh examples/minimal-project/hooks/check-task-completed.sh tests/test_hook_output_schema.py
git commit -m "$(cat <<'EOF'
feat(hooks): enforce gate-ref evidence integrity on TaskCompleted

check-task-completed.sh now runs check_status.py --check-completion-evidence
after the next_action check; any violation pushes back via exit 2. Reuses the
contract's gate<->ref + ref-existence invariant at completion time. Routine
todos in brainstorm/implement (gates pending) pass freely. No bypass.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: CLAUDE.md に enforcement を明文化（致命1）

**Files:**
- Modify: `CLAUDE.md`（Completion Rule 節）
- Modify: `examples/minimal-project/CLAUDE.md`（同節・同一文）

- [ ] **Step 1: root CLAUDE.md の Completion Rule に追記**

`CLAUDE.md` の `## Completion Rule` リスト末尾（`- the completion summary is evidence-based` の後）に1項目追加:
- 追記: `- Approved `review`/`qa`/`security`/`deploy`/`plan` gates must declare their `current_refs` entry (and `pending`/`n/a` gates must leave it null); every declared ref must point to an existing file. Enforced at task completion by the TaskCompleted hook (same invariant as `check_framework_contract`).`

- [ ] **Step 2: example CLAUDE.md に同一追記**

`examples/minimal-project/CLAUDE.md` の同節に Step 1 と同一文を追記（両ファイルの Completion Rule は同一）。

- [ ] **Step 3: word budget / contract / drift 確認**

Run: `python3 -c "print('root', len(open('CLAUDE.md').read().split()))"; python3 -c "print('example', len(open('examples/minimal-project/CLAUDE.md').read().split()))"; python3 scripts/check_framework_contract.py; echo "contract=$?"; python3 scripts/check_reference_drift.py; echo "drift=$?"`
Expected: root word ≤ 650（追記後 ~520）、example も budget 内、contract=0、drift=0。

- [ ] **Step 4: コミット**

```bash
git add CLAUDE.md examples/minimal-project/CLAUDE.md
git commit -m "$(cat <<'EOF'
docs(rules): document gate-ref evidence enforcement in Completion Rule

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: version 0.12.6 ＋ 全検証

**Files:**
- Modify: `scripts/check_framework_contract.py:17`
- Modify: `templates/STATUS.template.md:3`

- [ ] **Step 1: FRAMEWORK_VERSION を 0.12.6 へ** — old `FRAMEWORK_VERSION = "0.12.5"` → new `"0.12.6"`
- [ ] **Step 2: STATUS.template.md を 0.12.6 へ** — old `framework_version: "0.12.5"` → new `"0.12.6"`

- [ ] **Step 3: contract / drift / 全テスト**

Run: `python3 scripts/check_framework_contract.py; echo "contract=$?"; python3 scripts/check_reference_drift.py; echo "drift=$?"; python3 -m unittest discover -s tests -q 2>&1 | tail -2`
Expected: `contract=0`、`drift=0`、`Ran 195 tests ... OK`（186 + Task1 の7 + Task2 の2）。件数は実値に合わせる。

- [ ] **Step 4: コミット**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md
git commit -m "$(cat <<'EOF'
chore(version): bump framework to 0.12.6 (evidence-completion enforcement)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: bookkeeping ＋ 実装計画 commit ＋ memory ＋ push（要ユーザー確認）

- [ ] **Step 1: §3 evidence 行に完了注記**

`docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md` の §3 `evidence 必須完了` 行（着手前に `grep -n "evidence 必須完了\|Stop/TaskCompleted"` で確認）末尾に追記:
- 追記: ` → **完了**（2026-06-06・v0.12.6・(B) check-task-completed.sh が check_status.py の evidence_integrity_violations（validate_status_file から抽出・再利用）を完了時に強制。Stop hook 新設は却下。`2026-06-06-v1-evidence-completion-hook-design.md`）`

- [ ] **Step 2: §11 チェックリストに追記**

`- [ ] evidence 完了の Stop/TaskCompleted hook 強制化（旧確定案を採用）` を（`grep -n "evidence 完了の"` 確認後）`[x]` 化:
- 変更後: `- [x] evidence 完了の TaskCompleted hook 強制化（2026-06-06・v0.12.6・validate_status_file ロジック再利用＋hook 配線。Stop hook 不採用）`

- [ ] **Step 3: STATUS.md を完了状態へ更新**（着手前に現値確認）
- `gate_approvals.plan: pending → approved`
- `phase: plan → implement`
- `current_refs.plan: null → docs/plans/2026-06-06-v1-evidence-completion-hook-implementation.md`
- `framework_version: 0.12.5 → 0.12.6`
- `next_action`: 「evidence 完了強制化 実装完了（v0.12.6・全テスト green）。次は grill-code → review ゲート」
- `last_updated`: 当日 / session_history は frontmatter 最大3件厳守（最古を落として3件）＋ body に1行

- [ ] **Step 4: bookkeeping をコミット**

```bash
git add docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md docs/STATUS.md
git commit -m "$(cat <<'EOF'
docs(plans): mark evidence-completion enforcement done, STATUS to 0.12.6

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: 実装計画を tracked 化**

```bash
git add docs/plans/2026-06-06-v1-evidence-completion-hook-implementation.md
git commit -m "$(cat <<'EOF'
docs(plans): track evidence-completion impl plan as dated snapshot

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: memory 更新**

`aegis-rearchitecture-direction.md` に evidence 完了強制化を追記（Phase R 第4手・main・v0.12.6。validate_status_file の gate-ref＋実在ロジックを evidence_integrity_violations に抽出・再利用、check-task-completed.sh が exit2 差し戻し、Stop hook 不採用、gate_ref_mapping を GATE_REF_MAPPING 定数化、バイパス無し）。未着手リストから外す。git 管理外。

- [ ] **Step 7: push 前の最終状態確認**

Run: `git log --oneline origin/main..HEAD`
Expected: 設計コミット群＋Task 1〜4＋Task 5 Step 4・5。`docs/architecture-overview.pdf` は含めない。

- [ ] **Step 8: push（ユーザー確認の上で実行）**

実行直前にユーザーへ push 可否を確認してから `git push origin main`。

---

## Self-Review

**Spec coverage（設計書 → タスク）:** §3 再利用アーキ（抽出＋定数化＋フラグ）→ Task 1。§5 ロジック（gate-ref 両方向＋実在＋requirements）→ Task 1 Step 4・テスト。hook 配線 → Task 2。§4 CLAUDE.md 明文化（致命1）→ Task 3。version → Task 4。§6 fail-safe（try/except・|| true・clean）→ Task 1 Step 4・Task 2 Step 3・テスト。§8 footgun（IDENTICAL×2・出力不変・DRY 完遂・dogfood）→ ベースライン＋各 Step。bookkeeping → Task 5。

**Placeholder scan:** 各 Edit に厳密 old/new、テストは完全コード、コマンドは期待出力付き。requirements テストの list パース注意を Step 1 注記。プレースホルダなし。

**Type/identifier consistency:** 定数 `GATE_REF_MAPPING`、ヘルパ `evidence_integrity_violations(refs, approvals, root)`、フラグ `--check-completion-evidence`、出力 prefix `EVIDENCE:`、env `AEGIS_ROOT_OVERRIDE`、hook 変数 `DEFAULT_ROOT`/`ROOT`/`EVIDENCE`/`SUBJECT` を全タスク一貫。version old `0.12.5`→new `0.12.6`。メッセージは `validate_status_file` 既存と一致（path 接頭辞のみ呼び出し側付与）。

**重要リスク:** Task 1 Step 5 の置換で旧インライン実在チェックの**消し残しによる二重出力**に注意（Step 5 注記で明示）。`validate_status_file` 既存テストが緑のままであることを Step 8・10 で確認＝メッセージ不変の保証。
