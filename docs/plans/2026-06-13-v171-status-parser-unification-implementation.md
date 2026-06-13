# STATUS パーサ bash 一本化 実装計画（M3 / v1.7.1）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `lib/frontmatter.sh` に `frontmatter_value`/`gate_value` を追加し、散在する scalar/gate 抽出（`extract_value` 2定義＋インライン約11箇所＋gate抽出4箇所）を単一所有者へ集約する（挙動不変）。

**Architecture:** 値抽出は現行 `grep -m1 "^key:" | sed | sed` を**whole-file grep のまま**関数化（STATUS.md・bare `.gate-snapshot` 両対応・byte 一致）。各 hook はローカル `extract_value` を廃し `frontmatter_value "$FILE" "$key"` を直接呼ぶ。Python 側は既に一本化済みのため変更なし。

**Tech Stack:** bash + awk/sed/grep（pure・外部依存なし）、Python unittest。

設計書: `docs/plans/2026-06-13-status-parser-unification-design.md`

---

## File Structure

- `hooks/lib/frontmatter.sh` — `frontmatter_value` / `gate_value` を追加（既存 read_frontmatter/section の隣）。
- `hooks/session-start.sh`, `hooks/pre-compact.sh` — ローカル `extract_value` 定義を削除し `frontmatter_value` 呼出へ。
- `hooks/check-gate.sh`, `check-control-plane.sh`, `check-task-completed.sh`, `check-task-created.sh`, `check-client-info.sh` — インライン scalar/gate を関数呼出へ（4 hook は `source frontmatter.sh` 追加）。
- `hooks/post-status-audit.sh` — scalar×7（snapshot/STATUS）を `frontmatter_value` へ。
- `tests/test_frontmatter_lib.py` — `frontmatter_value`/`gate_value` の単体＋equivalence テスト。
- `examples/minimal-project/` — 編集した frontmatter.sh＋全 hook の byte-identical ミラー。
- 版数4箇所（v1.7.0→v1.7.1）。

---

## Task 1: frontmatter.sh に frontmatter_value / gate_value を追加

**Files:**
- Test: `tests/test_frontmatter_lib.py`（クラス追加）
- Modify: `hooks/lib/frontmatter.sh`（`raw_section` の後に追加）

- [ ] **Step 1: 単体テストを追加（RED）**

`tests/test_frontmatter_lib.py` の `class TestCallSitesUse20PlusLines` の**直前**に追加する:

```python
class TestFrontmatterValue(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        p = tmp / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_quoted_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), '---\nmode: "Dev"\nphase: implement\n---\n')
            rc, out = run_fn("frontmatter_value", str(p), "mode")
            self.assertEqual(out, "Dev\n")

    def test_unquoted_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\nphase: implement\n---\n")
            rc, out = run_fn("frontmatter_value", str(p), "phase")
            self.assertEqual(out, "implement\n")

    def test_empty_string_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), '---\nnext_action: ""\n---\n')
            rc, out = run_fn("frontmatter_value", str(p), "next_action")
            self.assertEqual(out, "\n")

    def test_value_with_spaces_and_colon(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), '---\nnext_action: "do X: then Y"\n---\n')
            rc, out = run_fn("frontmatter_value", str(p), "next_action")
            self.assertEqual(out, "do X: then Y\n")

    def test_absent_key_empty_rc0(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\nmode: Dev\n---\n")
            rc, out = run_fn("frontmatter_value", str(p), "nonexistent")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_bare_snapshot_value(self):
        # --- 無しの .gate-snapshot からも読める（post-status-audit 依存）
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("phase: implement\nmode: Dev\n", encoding="utf-8")
            rc, out = run_fn("frontmatter_value", str(p), "phase")
            self.assertEqual(out, "implement\n")

    def test_missing_file_empty_rc0(self):
        rc, out = run_fn("frontmatter_value", "/nonexistent/x.md", "mode")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")


class TestGateValue(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        p = tmp / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_gate_present(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan: approved\n  qa: pending\n---\n")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "approved\n")

    def test_gate_null(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan: null\n---\n")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "null\n")

    def test_gate_absent_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan: approved\n---\n")
            rc, out = run_fn("gate_value", str(p), "deploy")
            self.assertEqual(out, "")

    def test_gate_anchor_no_substring_match(self):
        # 2スペース anchor: "plan" が "plan_extra" を誤って拾わない
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan_extra: approved\n  plan: pending\n---\n")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "pending\n")

    def test_gate_bare_snapshot(self):
        # grill 致命1: --- 無し .gate-snapshot からも読める（raw_section fallback）
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("gate_approvals:\n  plan: approved\n  qa: pending\nphase: implement\n",
                         encoding="utf-8")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "approved\n")
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m unittest tests.test_frontmatter_lib.TestFrontmatterValue tests.test_frontmatter_lib.TestGateValue -v`
Expected: 全 FAIL（`frontmatter_value: command not found` / `gate_value: command not found`）。

- [ ] **Step 3: frontmatter.sh に2関数を実装**

`hooks/lib/frontmatter.sh` の末尾（`raw_section` の `}` の後）に追加する:

```bash

# frontmatter_value <file> <key>
#   stdout: top-level scalar value (surrounding double-quotes stripped).
#   Whole-file `^key:` match so bare frontmatter files (.gate-snapshot, no `---`)
#   work identically. Empty stdout + RC 0 when the file or key is absent
#   (callers test -n/-z; matches the prior `... || true` inline behavior).
frontmatter_value() {
  local file="$1" key="$2"
  [ -f "$file" ] || return 0
  grep -m1 "^${key}:" "$file" | sed "s/^${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}

# gate_value <file> <gate>
#   stdout: the value of `<gate>:` under the gate_approvals section.
#   frontmatter_section || raw_section: works on BOTH ---delimited STATUS.md
#   AND bare .gate-snapshot (no ---), same as frontmatter_value handles both.
#   2-space anchor prevents substring matches (e.g. `plan` vs `plan_extra`).
#   Empty stdout + RC 0 when absent.
gate_value() {
  local file="$1" gate="$2"
  { frontmatter_section "$file" gate_approvals 2>/dev/null || raw_section "$file" gate_approvals; } \
    | grep -m1 "  ${gate}:" | sed "s/.*${gate}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}
```

> grill 致命1: 当初の frontmatter_section-only 版は bare `.gate-snapshot` で silent-empty になり frontmatter_value と非対称＝罠。fallback 連鎖で両対応にする（既存 post-status-audit `extract_gate` と同形）。

- [ ] **Step 4: テストを実行して緑を確認**

Run: `python3 -m unittest tests.test_frontmatter_lib.TestFrontmatterValue tests.test_frontmatter_lib.TestGateValue -v`
Expected: 全 PASS。

- [ ] **Step 5: equivalence テストを追加（挙動不変の実証）**

`tests/test_frontmatter_lib.py` の `TestGateValue` の後に追加する:

```python
class TestValueEquivalenceWithLegacyPipeline(unittest.TestCase):
    """frontmatter_value が旧3段パイプ grep|sed|sed と全キーで一致することを実証。"""
    STATUS = ('---\nframework: aegis\nframework_version: "1.7.0"\n'
              'mode: Dev\nphase: implement\ntask_type: framework\n'
              'task_size: M\nnext_action: "do X: then Y"\nblockers: []\n---\nbody\n')

    def _legacy(self, path: str, key: str) -> str:
        cmd = (f'grep -m1 "^{key}:" "{path}" | sed "s/^{key}:[[:space:]]*//" '
               f"| sed 's/^\"//;s/\"$//' || true")
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        return r.stdout

    def test_all_keys_match(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text(self.STATUS, encoding="utf-8")
            for key in ("mode", "phase", "task_type", "task_size",
                        "next_action", "framework_version", "missing"):
                _, new = run_fn("frontmatter_value", str(p), key)
                old = self._legacy(str(p), key)
                self.assertEqual(new, old, f"divergence for key {key!r}")
```

- [ ] **Step 6: equivalence を実行して緑を確認**

Run: `python3 -m unittest tests.test_frontmatter_lib.TestValueEquivalenceWithLegacyPipeline -v`
Expected: PASS（全キーで新旧一致）。

- [ ] **Step 7: Commit**

```bash
git add hooks/lib/frontmatter.sh tests/test_frontmatter_lib.py
git commit -m "$(cat <<'EOF'
feat(frontmatter): add frontmatter_value/gate_value accessors (M3)

scalar/gate 値抽出を frontmatter.sh の単一所有者に。whole-file grep で
bare snapshot 両対応・旧3段パイプと byte 一致（equivalence テストで実証）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: session-start.sh / pre-compact.sh の extract_value 廃止

**Files:**
- Modify: `hooks/session-start.sh:40-48,77`
- Modify: `hooks/pre-compact.sh:25,33-41`

- [ ] **Step 1: session-start.sh の extract_value 定義を削除**

`hooks/session-start.sh` の現 39-43 行:

```bash
# Extract a scalar value from YAML frontmatter.
extract_value() {
  local key="$1"
  grep -m1 "^${key}:" "$STATUS_FILE" | sed "s/^${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}
```

を削除する（frontmatter.sh は既に line 10 で source 済み）。

- [ ] **Step 2: session-start.sh の extract_value 呼出を frontmatter_value へ**

現 45-48 行:

```bash
MODE=$(extract_value "mode")
PHASE=$(extract_value "phase")
TASK_TYPE=$(extract_value "task_type")
NEXT_ACTION=$(extract_value "next_action")
```

を:

```bash
MODE=$(frontmatter_value "$STATUS_FILE" "mode")
PHASE=$(frontmatter_value "$STATUS_FILE" "phase")
TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
NEXT_ACTION=$(frontmatter_value "$STATUS_FILE" "next_action")
```

現 77 行:

```bash
TASK_SIZE=$(extract_value "task_size")
```

を:

```bash
TASK_SIZE=$(frontmatter_value "$STATUS_FILE" "task_size")
```

- [ ] **Step 3: pre-compact.sh に frontmatter.sh の source を追加し extract_value 廃止**

現 25 行 `source "${SCRIPT_DIR}/lib/emit.sh"` の直後に追加:

```bash
source "${SCRIPT_DIR}/lib/frontmatter.sh"
```

現 33-37 行:

```bash
# Extract a scalar value from YAML frontmatter.
extract_value() {
  local key="$1"
  grep -m1 "^${key}:" "$STATUS_FILE" | sed "s/^${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}
```

を削除し、現 39-41 行:

```bash
MODE=$(extract_value "mode")
PHASE=$(extract_value "phase")
NEXT_ACTION=$(extract_value "next_action")
```

を:

```bash
MODE=$(frontmatter_value "$STATUS_FILE" "mode")
PHASE=$(frontmatter_value "$STATUS_FILE" "phase")
NEXT_ACTION=$(frontmatter_value "$STATUS_FILE" "next_action")
```

- [ ] **Step 4: 全テストで挙動不変を確認**

Run: `python3 -m unittest tests.test_phase_skills_lib tests.test_hook_output_schema -v 2>&1 | tail -5`
Expected: OK（session-start/pre-compact 関連が全緑）。

- [ ] **Step 5: Commit**

```bash
git add hooks/session-start.sh hooks/pre-compact.sh
git commit -m "$(cat <<'EOF'
refactor(hooks): session-start/pre-compact use frontmatter_value (M3)

ローカル extract_value 定義を廃し単一所有者 frontmatter_value へ委譲。挙動不変。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: インライン scalar/gate hook の rewire

**Files:**
- Modify: `hooks/check-gate.sh:106,132,143,144`
- Modify: `hooks/check-control-plane.sh`（source追加 + :226）
- Modify: `hooks/check-task-completed.sh`（source追加 + :98）
- Modify: `hooks/check-task-created.sh:107,108`
- Modify: `hooks/check-client-info.sh`（source追加 + :37）

- [ ] **Step 1: check-gate.sh の scalar×3 と gate を rewire**

`hooks/check-gate.sh:106` と `:132`（同一内容）:

```bash
  TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を各々:

```bash
  TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
```

`:143`:

```bash
MODE=$(grep -m1 "^mode:" "$STATUS_FILE" | sed "s/^mode:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を:

```bash
MODE=$(frontmatter_value "$STATUS_FILE" "mode")
```

`:144`:

```bash
PLAN_GATE=$(frontmatter_section "$STATUS_FILE" gate_approvals | grep -m1 "plan:" | sed "s/.*plan:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を:

```bash
PLAN_GATE=$(gate_value "$STATUS_FILE" "plan")
```

（check-gate.sh は frontmatter.sh を source 済み。）

- [ ] **Step 2: check-task-created.sh の gate+scalar を rewire**

`hooks/check-task-created.sh:107`:

```bash
PLAN_GATE=$(frontmatter_section "$STATUS_FILE" gate_approvals | grep -m1 "plan:" | sed "s/.*plan:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を `PLAN_GATE=$(gate_value "$STATUS_FILE" "plan")` に。

`:108`:

```bash
PHASE=$(grep -m1 "^phase:" "$STATUS_FILE" | sed "s/^phase:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を `PHASE=$(frontmatter_value "$STATUS_FILE" "phase")` に。
（check-task-created.sh は frontmatter.sh を source 済み。）

- [ ] **Step 3: check-control-plane.sh に source 追加し scalar を rewire**

`hooks/check-control-plane.sh` の `aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"` 行（現 44 付近）の直後に追加:

```bash
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"
```

`:226`:

```bash
TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を `TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")` に。

- [ ] **Step 4: check-task-completed.sh に source 追加し scalar を rewire**

`hooks/check-task-completed.sh` の `aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"` 行（現 37 付近）の直後に追加:

```bash
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"
```

`:98`:

```bash
NEXT_ACTION=$(grep -m1 "^next_action:" "$STATUS_FILE" | sed "s/^next_action:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を `NEXT_ACTION=$(frontmatter_value "$STATUS_FILE" "next_action")` に。

- [ ] **Step 5: check-client-info.sh に source 追加し scalar を rewire**

`hooks/check-client-info.sh` の `source "${SCRIPT_DIR}/lib/emit.sh"`（現 12 行）の直後に追加:

```bash
source "${SCRIPT_DIR}/lib/frontmatter.sh"
```

`:37`:

```bash
MODE=$(grep -m1 "^mode:" "$STATUS_FILE" | sed "s/^mode:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
```

を `MODE=$(frontmatter_value "$STATUS_FILE" "mode")` に。

- [ ] **Step 6: 全テストで挙動不変を確認**

Run: `python3 -m unittest discover tests 2>&1 | grep -E "^(Ran|OK|FAILED)"`
Expected: `OK`（全緑・挙動不変）。

- [ ] **Step 7: Commit**

```bash
git add hooks/check-gate.sh hooks/check-control-plane.sh hooks/check-task-completed.sh hooks/check-task-created.sh hooks/check-client-info.sh
git commit -m "$(cat <<'EOF'
refactor(hooks): inline scalar/gate reads use frontmatter_value/gate_value (M3)

check-gate/control-plane/task-completed/task-created/client-info の場当たり
grep|sed を単一所有者へ。control-plane/task-completed/client-info に
frontmatter.sh source 追加（全 profile 配布済み）。挙動不変。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: post-status-audit.sh の scalar×7 ＋ gate 読取を rewire

**Files:**
- Modify: `hooks/post-status-audit.sh:70,71,100,101,118,119,164`（scalar×7）
- Modify: `hooks/post-status-audit.sh:79-83,89,90,123-126,129,136`（gate readers＝grill 致命2）

> grill 致命2: post-status-audit は独自の gate-reader を**2つ**持つ — `extract_gate`（line 79-83、両対応 fallback）と `extract_gate_from_status`（line 123-126、STATUS 専用）。robust `gate_value`（Task1）はこの両方の真の drop-in。両定義を削除し全呼出を `gate_value` へ。これが M3「gate 一本化」の本丸。既存の改ざん検知テストがガード。

- [ ] **Step 1: snapshot/STATUS の scalar 読取を frontmatter_value へ**

（post-status-audit.sh は frontmatter.sh を source 済み。`$SNAPSHOT_FILE` は bare ファイルだが whole-file grep の frontmatter_value で読める。）

各行を以下に置換する（key と対象ファイル変数に注意）:

| 行 | 旧 | 新 |
|---|---|---|
| 70 | `_AEGIS_SNAP_PHASE_CHECK=$(grep -m1 '^phase:' "$SNAPSHOT_FILE" \| sed ...)` | `_AEGIS_SNAP_PHASE_CHECK=$(frontmatter_value "$SNAPSHOT_FILE" "phase")` |
| 71 | `_AEGIS_SNAP_MODE_CHECK=$(grep -m1 '^mode:' "$SNAPSHOT_FILE" \| sed ...)` | `_AEGIS_SNAP_MODE_CHECK=$(frontmatter_value "$SNAPSHOT_FILE" "mode")` |
| 100 | `OLD_PHASE=$(grep -m1 "^phase:" "$SNAPSHOT_FILE" \| sed ...)` | `OLD_PHASE=$(frontmatter_value "$SNAPSHOT_FILE" "phase")` |
| 101 | `NEW_PHASE=$(grep -m1 "^phase:" "$STATUS_FILE" \| sed ...)` | `NEW_PHASE=$(frontmatter_value "$STATUS_FILE" "phase")` |
| 118 | `OLD_MODE=$(grep -m1 "^mode:" "$SNAPSHOT_FILE" \| sed ...)` | `OLD_MODE=$(frontmatter_value "$SNAPSHOT_FILE" "mode")` |
| 119 | `NEW_MODE=$(grep -m1 "^mode:" "$STATUS_FILE" \| sed ...)` | `NEW_MODE=$(frontmatter_value "$STATUS_FILE" "mode")` |
| 164 | `TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" \| sed ...)` | `TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")` |

各置換は、対応する行の完全一致で Edit する（旧の完全形は `git show HEAD:hooks/post-status-audit.sh` で確認可）。

- [ ] **Step 1b: gate-reader 2関数を gate_value へ統一（grill 致命2）**

`extract_gate` 定義（line 79-83）を削除し、呼出を置換:
- line 89 `OLD=$(extract_gate "$SNAPSHOT_FILE" "$gate")` → `OLD=$(gate_value "$SNAPSHOT_FILE" "$gate")`
- line 90 `NEW=$(extract_gate "$STATUS_FILE" "$gate")` → `NEW=$(gate_value "$STATUS_FILE" "$gate")`

`extract_gate_from_status` 定義（line 123-126）を削除し、呼出を置換:
- line 129 `BOUNDARY_GATE=$(extract_gate_from_status "client_ready_for_dev")` → `BOUNDARY_GATE=$(gate_value "$STATUS_FILE" "client_ready_for_dev")`
- line 136 `BOUNDARY_GATE=$(extract_gate_from_status "dev_ready_for_client")` → `BOUNDARY_GATE=$(gate_value "$STATUS_FILE" "dev_ready_for_client")`

注: `extract_gate` の `frontmatter_section || raw_section` fallback ＋ unanchored grep を、`gate_value` の同 fallback ＋ 2スペース anchor が置換。実 gate_approvals データ（2スペース indent）で同結果＝挙動不変。tamper 比較ループの OLD/NEW は同値性が保たれる。

- [ ] **Step 2: post-status-audit テストと snapshot 系で挙動不変を確認**

Run: `python3 -m unittest tests.test_hook_output_schema tests.test_snapshot_atomic tests.test_snapshot_consumer_policy -v 2>&1 | tail -6`
Expected: OK（改ざん検知・snapshot 比較が全緑）。

- [ ] **Step 3: Commit**

```bash
git add hooks/post-status-audit.sh
git commit -m "$(cat <<'EOF'
refactor(post-status-audit): scalar reads use frontmatter_value (M3)

snapshot/STATUS の phase/mode/task_type 読取7箇所を単一所有者へ。
whole-file grep 関数なので bare snapshot でも挙動不変。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: example ミラー同期 + drift

**Files:**
- Mirror: `examples/minimal-project/hooks/lib/frontmatter.sh` ＋編集した全 hook

- [ ] **Step 1: 編集ファイルを example へ byte-identical コピー**

```bash
for f in lib/frontmatter.sh session-start.sh pre-compact.sh check-gate.sh check-control-plane.sh check-task-completed.sh check-task-created.sh check-client-info.sh post-status-audit.sh; do
  cp "hooks/$f" "examples/minimal-project/hooks/$f"
done
```

- [ ] **Step 2: byte 一致を確認**

```bash
for f in lib/frontmatter.sh session-start.sh pre-compact.sh check-gate.sh check-control-plane.sh check-task-completed.sh check-task-created.sh check-client-info.sh post-status-audit.sh; do
  diff -q "hooks/$f" "examples/minimal-project/hooks/$f" || echo "DRIFT: $f"
done; echo "done"
```
Expected: `done`（`DRIFT:` 出力なし）。

- [ ] **Step 3: mirror identity / drift テスト**

Run: `python3 -m unittest tests.test_mirror_identity -v 2>&1 | tail -4 && python3 scripts/check_reference_drift.py 2>&1 | tail -2`
Expected: mirror identity OK、`PASS: no reference drift detected`。

- [ ] **Step 4: Commit**

```bash
git add examples/minimal-project/hooks
git commit -m "$(cat <<'EOF'
chore(example): mirror M3 frontmatter parser unification (byte-identical)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: framework_version を 1.7.1 へ（4箇所同期）

**Files:**
- Modify: `scripts/check_framework_contract.py`（`FRAMEWORK_VERSION = "1.7.0"`）
- Modify: `templates/STATUS.template.md`（`framework_version: "1.7.0"`）
- Modify: `examples/minimal-project/docs/STATUS.md`（`framework_version: "1.7.0"`）
- Modify: `docs/STATUS.md`（`framework_version: "1.7.0"`）

- [ ] **Step 1: 4箇所を 1.7.1 に更新**

各ファイルの `1.7.0` → `1.7.1`（`FRAMEWORK_VERSION = "1.7.1"` / `framework_version: "1.7.1"`）。

- [ ] **Step 2: contract 全 profile で版数同期を確認**

Run: `python3 scripts/check_framework_contract.py --profile=full && python3 scripts/check_framework_contract.py --profile=standard --root=. && python3 scripts/check_framework_contract.py --profile=minimal --root=.`
Expected: 3 profile すべて PASS。

- [ ] **Step 3: Commit**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md examples/minimal-project/docs/STATUS.md docs/STATUS.md
git commit -m "$(cat <<'EOF'
chore: bump framework_version to 1.7.1 (M3 STATUS parser unification)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 全体検証ゲート + STATUS 更新

- [ ] **Step 1: 全テスト**

Run: `python3 -m unittest discover tests > /tmp/m3_tests.log 2>&1; echo "EXIT=$?"; grep -E "^(Ran|OK|FAILED)" /tmp/m3_tests.log`
Expected: `EXIT=0`、`OK`（新規テスト分増・失敗 0）。

- [ ] **Step 2: contract / drift / smoke / PoC**

Run:
```bash
for p in minimal standard; do python3 scripts/check_framework_contract.py --profile=$p --root=. || echo "FAIL:$p"; done
python3 scripts/check_framework_contract.py --profile=full || echo "FAIL:full"
python3 scripts/check_reference_drift.py 2>&1 | tail -1
python3 scripts/eval_scaffold_smoke.py 2>&1 | tail -3
bash tests/poc/v162-redteam-rerun.sh 2>&1 | tail -1
bash tests/poc/v163-redteam.sh 2>&1 | tail -1
```
Expected: 全 PASS、`FAIL:` 出力なし、PoC 18/18・5/5。

- [ ] **Step 3: docs/STATUS.md を v1.7.1 着地で更新**

`iteration` を 26 に、`next_action`/`session_history`（最新3件維持）を M3 着地内容へ更新。`framework_version` は Task 6 で 1.7.1 済み。

- [ ] **Step 4: 最終コミット**

```bash
git add docs/STATUS.md
git commit -m "$(cat <<'EOF'
chore(STATUS): record v1.7.1 M3 STATUS parser unification landing

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review メモ

- **Spec coverage:** 設計 §1(API)=Task1 / §2(置換マッピング)=Task2,3,4 / §3(挙動保存)=Task1 equivalence＋各 rewire の全テスト緑 / §4(エッジ)=Task1 単体（bare snapshot/空文字/absent） / §5(テスト)=Task1 / §6(版数・mirror)=Task5,6 / §7(検証)=Task7。session-start ループ据え置き（§2※）=触れない。
- **Type consistency:** 関数名 `frontmatter_value`/`gate_value`、引数順 `<file> <key>`/`<file> <gate>`、rc 0+空の契約を全タスク一貫。版数 old `1.7.0` → new `1.7.1` 一貫。
- **No placeholders:** 各 step に実コード/実コマンド/期待出力。post-status-audit の旧完全形は `git show HEAD:` で取得する指示（行内容は grep 済みで既知）。
- **grill-plan 重点:** ①frontmatter_value の whole-file grep が snapshot の bare ファイルで現行と byte 一致する点（equivalence テストは `---` 付き STATUS のみ→ bare snapshot の equivalence も足すか要検討）②control-plane/task-completed への `aegis_require_lib frontmatter.sh` 追加が fail-closed 挙動を変えないか（lib 欠落時 deny は既存ポリシーと一致だが、frontmatter.sh は値読取用＝deny 判断に不要なので require が過剰か要検討）③gate_value の anchor 厳密化（`"  gate:"`）が check-gate の無 anchor 形と実 STATUS で同結果か。
