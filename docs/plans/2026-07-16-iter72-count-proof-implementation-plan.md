# iter72: marker count proof（SF-014 完結編）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `.claude/skills/subagent-dev/SKILL.md`（タスクごとにフレッシュな implementer サブエージェント・per-task commit・2段レビュー）。Steps は checkbox 追跡。

**Goal:** `aegis_marker_verdict` に Stage 5「count proof」を追加し、all-skip suite の偽 green（unittest／go `-v`）を封鎖しつつ、cargo（doc-tests 空）と jest（skipped 混在）の実証済み偽陰性を修正する。

**Architecture:** count 族データは `hooks/lib/patterns.sh`（単一ソース・parity 契約下）、算術は `hooks/lib/marker.sh` Stage 5（bash 3.2・grep -E のみ）。verdict インターフェース（stdin 全文→"true"/"false"・rc3）は不変＝3 消費者（evidence.sh／record／drill）は無改修。

**Tech Stack:** bash 3.2 / BSD・GNU grep -E / python3 unittest（既存構成のみ・新規依存なし）

**設計正本:** `docs/specs/2026-07-16-iter72-count-proof-design.md`（追補 1-4 含む）

**不変条件（全タスク共通の受入基準）:**
- Stage 5 は verdict を true→false 方向にのみ変える。意図的 false→true は「cargo zero-run 行削除」「jest STRONG 緩和」「vitest アンカー緩和」の 3 点のみ（いずれも設計追補で forge 価値不変を論証済み）。
- 既存 moat pin（M2-M11・TestWeakPairBoundary・pytest/cargo all-skip false pin・test_test_marker_zero_run.py・test_test_runner_realness.py）は**テスト本体を変更せずに** green を維持する（cargo all-ignored pin は機構が zero-run 行→Stage 5 に替わるが黒箱で不変）。
- 例外は TestSkipSuiteResidual の unittest 残余 pin（true→false へ**意図的に反転**＝本反復の目的そのもの）。

---

## Task 0（コーディネーター事前確認・dispatch なし）

- [ ] `git status` clean・`python3 -m unittest discover -s tests -q` が baseline green であることを確認（実測 passed 数を記録）
- [ ] 以降のタスクは同一ファイル群を触るため**直列実行**（並列 dispatch 禁止）

---

### Task 1: RED — テスト先行（意図的 pin 反転＋新規テスト）

**Files:**
- Modify: `tests/test_marker_lib.py`
- Modify: `tests/test_patterns_parity.py`

**実装させないこと（このタスクでは production コード禁止）:** `hooks/lib/*.sh`・`scripts/*.py` に触れない。

- [ ] **Step 1-1: test_marker_lib.py — import に `re` を追加**

先頭 import 群を:

```python
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
```

- [ ] **Step 1-2: TestSkipSuiteResidual を count-proof 後の契約に書き換える**

クラス全体（docstring 含む）を以下で**置換**する。pytest/cargo の 2 pin は入力・assert とも不変。unittest pin は false へ反転（目的）。go bare pin は残余として維持。go `-v` の 2 本と unittest 境界 1 本を追加:

```python
class TestSkipSuiteResidual(unittest.TestCase):
    """iter71 review F-A / iter72 count proof: an all-skip suite runs ZERO test
    bodies. iter72's Stage 5 (count proof: executed = passed+failed, skips
    excluded, >=1 required per detected count family) CLOSES the unittest and
    `go test -v` halves of the residual; the remaining split:

      - pytest (`N skipped in`), cargo (`0 passed`), jest (no `passed`
        segment): false. MOAT-PROTECTION pins (cargo now via the Stage 5 sum
        — the zero-run line-deny was removed to fix the empty-doc-tests
        false negative — but the pin below is black-box identical).
      - unittest all-skip: false since iter72 (Ran N - skipped=N = 0). CLOSED.
      - go -v all-skip: false since iter72 (`--- SKIP:` only -> 0 PASS/FAIL
        lines). CLOSED for the top-level all-`t.Skip()` form; a parent
        t.Run holder still prints `--- PASS:` (its body DID run) — design
        addendum 4.
      - bare `go test`: `ok pkg dur` carries no counts; an all-skip package
        is byte-identical to a real pass (iter71 verified). PRE-EXISTING
        residual, SF-014 bucket, contained by the B1 drill (an all-skip
        baseline kills no mutant -> DRILL FAIL). Permanent-fix candidate:
        execution attestation (iter73+ track)."""

    def test_pytest_all_skip_false_moat_pin(self):
        out = ("platform darwin -- Python 3.9.6, pytest-8.4.2\n"
               "rootdir: /tmp/x\ncollected 1 item\n\n"
               "t.py s  [100%]\n\n=========== 1 skipped in 0.01s ===========\n")
        rc, verdict = _verdict(out, "python3 -m pytest t.py", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_cargo_all_ignored_false_moat_pin(self):
        out = ("running 3 tests\n"
               "test result: ok. 0 passed; 0 failed; 3 ignored\n")
        rc, verdict = _verdict(out, "cargo test", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_unittest_all_skip_false_closed(self):
        # iter72 CLOSED: Ran(2) - skipped(2) = 0 bodies. Real output captured
        # 2026-07-16 (python3 -m unittest, two @unittest.skip tests, rc=0).
        out = ("ss\n" + "-" * 70 +
               "\nRan 2 tests in 0.000s\n\nOK (skipped=2)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_unittest_partial_skip_true_boundary(self):
        # Boundary pin: Ran(2) - skipped(1) = 1 executed -> true. Real output
        # captured 2026-07-16.
        out = ("s.\n" + "-" * 70 +
               "\nRan 2 tests in 0.000s\n\nOK (skipped=1)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_go_verbose_all_skip_false_closed(self):
        # iter72 CLOSED: -v output present but zero `--- PASS:`/`--- FAIL:`.
        out = ("=== RUN   TestA\n--- SKIP: TestA (0.00s)\n"
               "=== RUN   TestB\n--- SKIP: TestB (0.00s)\n"
               "PASS\nok  \texample.com/pkg\t0.012s\n")
        rc, verdict = _verdict(out, "go test -v ./...", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_go_verbose_pass_true(self):
        out = ("=== RUN   TestA\n--- PASS: TestA (0.00s)\n"
               "PASS\nok  \texample.com/pkg\t0.010s\n")
        rc, verdict = _verdict(out, "go test -v ./...", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_go_bare_all_skip_true_known_residual(self):
        # PRE-EXISTING residual (SF-014): bare `go test` emits `ok pkg dur`
        # with no counts; all-skip and real pass are byte-identical (iter71
        # verified). No count family detects -> Stage 1-4 verdict -> true.
        out = "ok  \texample.com/pkg\t0.012s\n"
        rc, verdict = _verdict(out, "go test ./...", "0")
        self.assertEqual((rc, verdict), (0, "true"))
```

- [ ] **Step 1-3: TestCountProof クラスを追加（TestWeakPairBoundary の後ろ）**

```python
class TestCountProof(unittest.TestCase):
    """iter72 Stage 5 (count proof) — false-negative fixes and the guard.

    The two `..._fixed` tests pin REAL-WORLD summary shapes that the pre-iter72
    verdict REJECTED (both empirically demonstrated on 2026-07-16, see the
    design addendum): cargo's empty doc-tests section tripped the zero-run
    line-deny; jest's `skipped,` segment broke the STRONG marker adjacency."""

    def test_cargo_empty_doctests_section_true_fixed(self):
        # Real-world shape: unit section 5 passed + EMPTY doc-tests section
        # (`running 0 tests` -> `0 passed`). Pre-iter72: false (zero-run
        # line-deny). Stage 5 sums across ALL `test result:` lines: 5 >= 1.
        out = ("running 5 tests\n"
               "test a ... ok\ntest b ... ok\ntest c ... ok\n"
               "test d ... ok\ntest e ... ok\n"
               "test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; "
               "0 filtered out; finished in 0.00s\n\n"
               "   Doc-tests mylib\n\nrunning 0 tests\n\n"
               "test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; "
               "0 filtered out; finished in 0.00s\n")
        rc, verdict = _verdict(out, "cargo test", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_jest_skipped_mixed_true_fixed(self):
        # Real jest segment order is failed, skipped, todo, passed, total —
        # any skipped test broke the old `(N failed,)? N passed` adjacency.
        out = ("Tests:       2 skipped, 3 passed, 5 total\n"
               "Snapshots:   0 total\nTime:        1.2 s\n")
        rc, verdict = _verdict(out, "npx jest", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_jest_all_skip_false(self):
        # All-skip jest prints NO `passed` segment -> no STRONG hit -> false
        # (unchanged behavior, now double-covered by the count stage).
        out = "Tests:       3 skipped, 3 total\n"
        rc, verdict = _verdict(out, "npx jest", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_vitest_indented_summary_true(self):
        # Real vitest indents its summary lines (design addendum 2); the
        # anchors now allow leading blanks.
        out = (" Test Files  1 passed (1)\n"
               "      Tests  2 passed (2)\n")
        rc, verdict = _verdict(out, "npx vitest run", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_unittest_failed_with_skips_true(self):
        # Red-run verdict (the verdict proves "tests ran", not "green"):
        # Ran(5) - skipped(2) = 3 bodies executed -> true.
        out = ("Ran 5 tests in 0.010s\n\nFAILED (failures=1, skipped=2)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_cargo_hybrid_echo_forge_true_known_residual(self):
        # ACCEPTED RESIDUAL pin (design addendum 3): an echoed pair PLUS a
        # real zero-run cargo line now reads true (the removed line-deny
        # caught it). Accepted because the attacker strictly dominates by
        # just NOT running cargo (pure echo was already true pre-iter72 —
        # cargo has no prologue/exit-code second axis). Echo-class residual
        # (b), contained by drill/human preview. This pin makes the deny-
        # surface change explicit; flipping it back requires reintroducing
        # the empty-doc-tests false negative — do NOT "fix" without reading
        # SF-014.
        out = ("running 3 tests\n"
               "test result: ok. 3 passed; 0 failed; 0 ignored\n"
               "running 0 tests\n"
               "test result: ok. 0 passed; 0 failed; 0 ignored\n")
        rc, verdict = _verdict(out, "cargo test", "0")
        self.assertEqual((rc, verdict), (0, "true"))

    def test_forged_huge_count_stays_false_path(self):
        # A forged astronomically large count must not crash the arithmetic
        # (bash overflow) out of the normal verdict path: digit tokens are
        # capped at 9 chars before summation. unittest family: Ran(huge->cap)
        # - skipped(huge->cap) = 0 -> false (all-skip shape preserved).
        out = ("Ran 99999999999999999999 tests in 0.000s\n\n"
               "OK (skipped=99999999999999999999)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "0")
        self.assertEqual((rc, verdict), (0, "false"))

    def test_rc3_when_count_families_missing(self):
        # The rc3 guard must cover the NEW array: a patterns.sh without
        # AEGIS_TEST_COUNT_FAMILIES (stale install) -> evaluation impossible.
        src = (ROOT / "hooks" / "lib" / "patterns.sh").read_text()
        kept, skip = [], False
        for ln in src.splitlines(keepends=True):
            if ln.startswith("AEGIS_TEST_COUNT_FAMILIES=("):
                skip = True
                continue
            if skip and ln.strip() == ")":
                skip = False
                continue
            if not skip:
                kept.append(ln)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "patterns.sh").write_text("".join(kept))
            shutil.copy(MARKER_LIB, Path(d) / "marker.sh")
            rc, _out = _verdict(
                PYTEST_REAL, "python3 -m pytest tests/", "0",
                lib=Path(d) / "marker.sh")
            self.assertEqual(rc, 3)
```

- [ ] **Step 1-4: test_patterns_parity.py — 既存 fixture の拡張**

`TestMarkerZeroRunParity.test_marker_tab_space_parity` の `fixtures` リストに 2 行追加（`("nothing to see here", False),` の**直前**に挿入）:

```python
            ("Tests:       2 skipped, 3 passed, 5 total", True),  # jest skipped 混在（iter72 緩和）
            (" Test Files  1 passed (1)", True),        # vitest インデント（iter72 緩和）
```

- [ ] **Step 1-5: test_patterns_parity.py — TestCountFamilyParity クラスを追加（TestMarkerZeroRunParity の後ろ）**

```python
class TestCountFamilyParity(unittest.TestCase):
    """iter72 (SF-014 count proof): AEGIS_TEST_COUNT_FAMILIES の DETECT/EXEC/
    MINUS も grep -E ∩ python-re parity 契約下に置く（5 フィールド `|||` 形式・
    共通部分集合・fixture 両エンジン一致）。"""

    @classmethod
    def setUpClass(cls):
        cls.entries = bash_array("AEGIS_TEST_COUNT_FAMILIES")

    def test_entry_format_five_fields(self):
        self.assertGreaterEqual(len(self.entries), 6)
        for e in self.entries:
            parts = e.split("|||")
            self.assertEqual(len(parts), 5, f"NAME|||DETECT|||EXEC|||MODE|||MINUS: {e!r}")
            name, detect, exec_pat, mode, _minus = parts
            self.assertTrue(name, e)
            self.assertTrue(detect, e)
            self.assertTrue(exec_pat, e)
            self.assertIn(mode, ("sum", "lines"), e)

    def test_regexes_common_subset_and_compile(self):
        for e in self.entries:
            _n, detect, exec_pat, _m, minus = e.split("|||")
            pats = [detect, exec_pat] + ([minus] if minus else [])
            for p in pats:
                self.assertNotIn("[[:", p, f"POSIX class in {p}")
                self.assertNotIn("\\b", p, f"\\b in {p}")
                re.compile(p)

    def test_detect_fixture_parity(self):
        # (text, family-that-must-detect-or-None, expected)
        fixtures = [
            ("Ran 2 tests in 0.000s", "unittest", True),
            ("=========== 3 passed in 0.42s ===========", "pytest", True),
            ("Tests:       2 skipped, 3 passed, 5 total", "jest", True),
            ("      Tests  2 passed (2)", "vitest", True),
            ("test result: ok. 0 passed; 0 failed; 3 ignored", "cargo", True),
            ("--- SKIP: TestA (0.00s)", "go-verbose", True),
            ("ok  \texample.com/pkg\t0.012s", None, False),  # 素の go は族なし
        ]
        by_name = {e.split("|||")[0]: e.split("|||")[1] for e in self.entries}
        for text, fam, expected in fixtures:
            for name, detect in by_name.items():
                py = re.compile(detect).search(text) is not None
                gr = grep_match(text, [detect])
                self.assertEqual(py, gr, f"engine split ({name}): {text!r}")
                if fam is not None and name == fam:
                    self.assertEqual(py, expected, f"{name} detect: {text!r}")
                if fam is None:
                    self.assertFalse(py, f"{name} must NOT detect: {text!r}")
```

- [ ] **Step 1-6: RED を実測**

Run: `python3 -m unittest tests.test_marker_lib tests.test_patterns_parity -v 2>&1 | tail -20`

Expected: **正確に 10 failed**（grill-plan Rev.2 で精密化）:
1. `test_unittest_all_skip_false_closed` — 現行は true（反転対象＝本反復の目的）
2. `test_go_verbose_all_skip_false_closed` — 現行は true（`--- SKIP` のみでも STRONG `ok pkg dur` が通る）
3. `test_cargo_empty_doctests_section_true_fixed` — 現行は false（zero-run 行 deny の偽陰性）
4. `test_jest_skipped_mixed_true_fixed` — 現行は false（STRONG 隣接要求の偽陰性）
5. `test_vitest_indented_summary_true` — 現行は false（行頭アンカー）
6. `test_forged_huge_count_stays_false_path` — 現行は true（pair 成立・zero-run 非該当・Stage 5 不在）
7. `test_cargo_hybrid_echo_forge_true_known_residual` — 現行は **false**（fixture が zero-run 行を含み現行 deny が命中。削除後に true 化＝deny 面変更の pin そのもの。pure-echo 形〔zero 行なし〕は現行でも true である点と混同しない）
8. `test_rc3_when_count_families_missing` — 現行は rc0/true（guard 未対応・除去ループは HEAD では no-op）
9. `test_entry_format_five_fields` — 配列未定義（len 0）
10. `test_marker_tab_space_parity` — 追加 fixture 2 件が expected True に対し両エンジン False（parity 自体は一致）

**注記**: `TestCountFamilyParity` の他 2 テスト（`test_regexes_common_subset_and_compile`／`test_detect_fixture_parity`）は空配列に対しループが回らず **vacuous PASS** する（RED に数えない）。**already-green の回帰 pin（PASS のまま）**: `test_unittest_partial_skip_true_boundary`／`test_go_verbose_pass_true`／`test_jest_all_skip_false`／`test_unittest_failed_with_skips_true`／`test_go_bare_all_skip_true_known_residual`。実測の failed/passed 数を commit message に記録し、期待 10 件と差異があれば原因を特定してから進む。

- [ ] **Step 1-7: Commit**

```bash
git add tests/test_marker_lib.py tests/test_patterns_parity.py
git commit -m "test(iter72): Task1 RED — count proof の失敗テスト先行（実測 X failed/Y passed・unittest all-skip 反転＋cargo/jest 偽陰性 fixture＋parity）"
```

---

### Task 2: GREEN — patterns.sh count 族データ＋marker.sh Stage 5

**Files:**
- Modify: `hooks/lib/patterns.sh`
- Modify: `hooks/lib/marker.sh`

- [ ] **Step 2-1: patterns.sh — jest STRONG marker の緩和**

`AEGIS_TEST_PASS_MARKER_REGEX` 内の:

```bash
  '(^|\n)Tests:[ 	]+([0-9]+ failed,[ 	]+)?[0-9]+ passed'
```

を以下に置換（コメントも更新。ブラケット内は**リテラル TAB**を維持）:

```bash
  # jest / vitest: "Tests:       5 passed, 5 total". iter72: real jest orders
  # segments failed, skipped, todo, passed — any skipped/todo test broke the
  # old `(N failed,)? N passed` adjacency (empirically a false negative for
  # every suite with a skipped test). `([0-9]+ [a-z]+,[ 	]+)*` accepts the
  # intermediate segments; forge value is unchanged (the strict form was
  # already echoable) and Stage 5 still requires passed+failed >= 1.
  '(^|\n)Tests:[ 	]+([0-9]+ [a-z]+,[ 	]+)*[0-9]+ passed'
```

- [ ] **Step 2-2: patterns.sh — vitest アンカーのインデント許容**

STRONG 内:

```bash
  '(^|\n)Test Files[ 	]+[0-9]+ passed'
```

を:

```bash
  # vitest: real output indents its summary (" Test Files  1 passed (1)") —
  # iter72 allows leading blanks (accept-side only; forge value unchanged).
  '(^|\n)[ 	]*Test Files[ 	]+[0-9]+ passed'
```

`AEGIS_TEST_ZERO_RUN_REGEX` 内:

```bash
  '(^|\n)Test Files[ 	]+0 passed'              # vitest
```

を:

```bash
  '(^|\n)[ 	]*Test Files[ 	]+0 passed'         # vitest（iter72: インデント許容）
```

- [ ] **Step 2-3: patterns.sh — cargo zero-run 行 deny の削除**

`AEGIS_TEST_ZERO_RUN_REGEX` から次の 1 行を**削除**:

```bash
  '(^|\n)test result: (ok|FAILED)\. 0 passed'   # cargo
```

配列の直前コメント（`# K-1 (v1.6.2): zero-run output signals...` ブロック）の末尾に追記:

```bash
# iter72: the cargo line-deny (`test result: ... 0 passed`) was REMOVED — an
# empty doc-tests section emits exactly that line on every real run of a
# doc-test-less crate (empirically: verdict false = false negative), while
# the attack it guarded (echoed pair + a REAL zero-run cargo alongside) is
# strictly dominated by pure echo with no cargo run at all (already true
# today; cargo has no prologue/exit-code second axis). The all-ignored case
# stays rejected by the Stage 5 count sum in marker.sh (moat pin unchanged:
# tests/test_marker_lib.py test_cargo_all_ignored_false_moat_pin).
```

- [ ] **Step 2-4: patterns.sh — AEGIS_TEST_COUNT_FAMILIES を追加**

`AEGIS_TEST_PROLOGUE_REGEX` ブロックの**直前**に挿入（`|||` 前後・ブラケット内の TAB はリテラル）:

```bash
# iter72 (SF-014 count proof): count-family data for marker.sh Stage 5. A
# STRONG/WEAK marker hit proves a summary LINE exists; the count stage
# additionally requires the summary's arithmetic to show >=1 test body
# actually executed (skips excluded). Entry format (`|||`-separated, the
# AEGIS_TEST_PASS_MARKER_PAIRS convention): NAME|||DETECT|||EXEC|||MODE|||MINUS
#   DETECT: family is present when any output line matches.
#   EXEC  : MODE=sum   -> sum every digit-run inside each EXEC match found on
#                         DETECT-matching lines (unittest MINUS scans the whole
#                         output — see the entry comment).
#           MODE=lines -> count EXEC-matching lines over the whole output.
#   MINUS : (sum only, may be empty) digit-run sum over the WHOLE output,
#           subtracted from the EXEC sum (floored at 0).
# Families NOT listed (bare `go test`: non-verbose output carries no counts)
# fall back to the Stage 1-4 verdict; that residual is pinned in
# tests/test_marker_lib.py and tracked in docs/security-followups.md SF-014.
# Extraction is heuristic text-mining over untrusted-ish output: mis-detection
# and over-subtraction fail CLOSED (false); over-addition needs attacker-
# controlled output = the echo residual (b), out of scope.
# CONSTRAINT (same as above): grep-E ∩ python-re common subset — no
# [[:space:]], no \b, literal TAB (0x09) inside brackets.
AEGIS_TEST_COUNT_FAMILIES=(
  # unittest: `Ran 5 tests in 0.010s` + `OK (skipped=2)` -> 5-2=3. MINUS scans
  # the WHOLE output because `skipped=K` lives on the OK/FAILED line, not the
  # `Ran` line.
  'unittest|||(^|\n)Ran [0-9]+ tests? in|||Ran [0-9]+ tests?|||sum|||skipped=[0-9]+'
  # pytest: `===== 2 failed, 3 passed in 1.20s =====` -> 2+3. (`3 skipped in`
  # has no passed/failed token -> 0.)
  'pytest|||={3,} .* in [0-9.]+s|||[0-9]+ (passed|failed)|||sum|||'
  # jest: `Tests:       1 failed, 2 skipped, 3 passed, 6 total` -> 1+3
  # (skipped/todo segments carry no passed|failed token).
  'jest|||(^|\n)Tests:[ 	]|||[0-9]+ (passed|failed)|||sum|||'
  # vitest: `      Tests  2 passed (2)` (indented) -> 2. Older outputs without
  # the Tests line fall back to Stage 1-4 (Test Files STRONG marker).
  'vitest|||(^|\n)[ 	]*Tests[ 	]+[0-9]+ passed|||[0-9]+ (passed|failed)|||sum|||'
  # cargo: sum across ALL `test result:` lines (unit + doc-tests sections) —
  # fixes the empty-doc-tests false negative; all-ignored sums to 0 -> false.
  'cargo|||(^|\n)test result: (ok|FAILED)\.|||[0-9]+ (passed|failed)|||sum|||'
  # go -v: count `--- PASS:`/`--- FAIL:` lines; an all-skip -v run has only
  # `--- SKIP:` -> 0 -> false. Bare `go test` emits no counts -> family not
  # detected -> Stage 1-4 verdict (known residual, see array comment).
  'go-verbose|||(^|\n)--- (PASS|FAIL|SKIP):|||(^|\n)--- (PASS|FAIL):|||lines|||'
)
```

- [ ] **Step 2-5: marker.sh — rc3 guard へ count 配列を追加**

ヘッダコメントの `# NOTE: the rc3 guard below requires ALL SIX pattern sources non-empty.` を `ALL SEVEN` に更新し、guard の連鎖:

```bash
  if [ -z "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_PAIRS[*]:-}" ] || \
     [ -z "${AEGIS_TEST_ZERO_RUN_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PROLOGUE_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_IS_PYTEST_REGEX:-}" ]; then
```

を:

```bash
  if [ -z "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_PAIRS[*]:-}" ] || \
     [ -z "${AEGIS_TEST_ZERO_RUN_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PROLOGUE_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_IS_PYTEST_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_COUNT_FAMILIES[*]:-}" ]; then
```

に置換。あわせてヘッダの Pipeline 説明に Stage 5 を追記（`(4) K-1 ...` ブロックの後）:

```bash
#   (5) iter72 (SF-014 count proof) — for each count-capable family whose
#       summary is DETECTed in the output (AEGIS_TEST_COUNT_FAMILIES), compute
#       executed = passed+failed (skips excluded) and require >=1 in at least
#       one detected family. No family detected (bare `go test`) keeps the
#       stage-1-4 verdict — the documented SF-014 residual.
```

- [ ] **Step 2-6: marker.sh — Stage 5 本体**

関数末尾の:

```bash
  printf 'true'
}
```

を以下に置換（`local` 宣言は既存関数スタイルに合わせる）:

```bash
  # Stage 5 (iter72 SF-014): count proof. Stages 2-4 prove a summary LINE
  # exists; they do not prove any test BODY ran (all-skip suites: unittest
  # counts skipped tests inside `Ran N`; go -v prints only `--- SKIP:`).
  # ANY rule: multiple families in one real run's output only occur under
  # attacker-controlled output (the echo residual (b), out of scope), while
  # an ALL rule would misreject a real run that happens to quote a nested
  # runner's output. Arithmetic errors fail CLOSED (true->false only).
  local entry rest fam_detect fam_exec fam_mode fam_minus lines n m num
  local family_detected=0 count_ok=0
  for entry in "${AEGIS_TEST_COUNT_FAMILIES[@]}"; do
    rest="${entry#*\|\|\|}"
    if [ "$rest" = "$entry" ]; then
      continue  # malformed (no ||| at all): the family cannot veto
    fi
    fam_detect="${rest%%\|\|\|*}"; rest="${rest#*\|\|\|}"
    fam_exec="${rest%%\|\|\|*}"; rest="${rest#*\|\|\|}"
    fam_mode="${rest%%\|\|\|*}"; fam_minus="${rest#*\|\|\|}"
    if [ "$fam_minus" = "$rest" ]; then
      fam_minus=""  # 4-field entry: no MINUS
    fi
    if [ -z "$fam_detect" ] || [ -z "$fam_exec" ] || [ -z "$fam_mode" ]; then
      continue
    fi
    lines="$(printf '%s' "$out" | grep -E "$fam_detect")" || continue
    family_detected=1
    if [ "$fam_mode" = "lines" ]; then
      n="$(printf '%s' "$out" | grep -cE "$fam_exec")" || true
    else
      n=0
      # digit tokens only after the final grep -oE '[0-9]+' — unquoted word
      # splitting is glob-safe; 10# blocks octal on zero-padded counts; the
      # 9-char cap keeps a FORGED astronomic count inside bash arithmetic
      # (overflow would crash out of the normal "false" path) — >=1
      # semantics only need magnitude, not precision.
      for num in $(printf '%s' "$lines" | grep -oE "$fam_exec" | grep -oE '[0-9]+' || true); do
        num="${num:0:9}"
        n=$((n + 10#$num))
      done
      if [ -n "$fam_minus" ]; then
        m=0
        for num in $(printf '%s' "$out" | grep -oE "$fam_minus" | grep -oE '[0-9]+' || true); do
          num="${num:0:9}"
          m=$((m + 10#$num))
        done
        n=$((n - m))
        if [ "$n" -lt 0 ]; then
          n=0
        fi
      fi
    fi
    if [ "$n" -ge 1 ]; then
      count_ok=1
      break
    fi
  done
  if [ "$family_detected" -eq 1 ] && [ "$count_ok" -eq 0 ]; then
    printf 'false'
    return 0
  fi
  printf 'true'
}
```

（注意: `fam_mode` 抽出行の直後の `fam_minus="${rest#*\|\|\|}"` は、`rest` に `|||` が残らない 4 フィールド entry で `rest` がそのまま返る——直後の `[ "$fam_minus" = "$rest" ]` 比較は**この場合を空 MINUS に正規化する**ためのもの。5 フィールド正規形は parity テストが pin する。）

- [ ] **Step 2-7: 対象テストが green になることを確認**

Run: `python3 -m unittest tests.test_marker_lib tests.test_patterns_parity -v 2>&1 | tail -8`
Expected: PASS（0 failed）

- [ ] **Step 2-8: full suite 確認**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -5`
Expected: Task 0 の baseline から**新規 fail ゼロ**（既知 flaky=test_update_gate_lock のみ許容・再走で green を確認）

- [ ] **Step 2-9: Commit**

```bash
git add hooks/lib/patterns.sh hooks/lib/marker.sh
git commit -m "feat(iter72): Task2 — marker Stage 5 count proof（unittest all-skip/go -v 封鎖・cargo/jest/vitest 偽陰性修正・rc3 guard 拡張）"
```

---

### Task 3: record-test-result.py — docstring/拒否メッセージの契約同期（動作不変）

**Files:**
- Modify: `scripts/record-test-result.py`

- [ ] **Step 3-1: docstring の Residual 段落を更新**

`Residual (intentionally NOT closed): ...` から `...audit_deps positive-proof track (iter72).` までの段落を以下で置換:

```python
Residual (intentionally NOT closed): the marker is an OUTPUT-based proof, so
two classes remain, both in the SF-014 bucket:
  (a) arbitrary-script output — e.g. an `npm test` script that echoes
      marker-shaped lines; counts can be echoed too, so no output parsing
      distinguishes it.
  (b) bare `go test` all-skip — non-verbose go output (`ok pkg dur`) carries
      no per-test counts; an all-skip package is byte-identical to a real
      pass. (unittest all-skip and `go test -v` all-skip ARE closed since
      iter72: marker.sh Stage 5 requires executed = passed+failed with skips
      excluded >= 1 per detected count family — AEGIS_TEST_COUNT_FAMILIES.)
We do NOT chase either by enumeration (a denylist regression = reproducing
SF-014). Contained by defence-in-depth: fingerprint / judge / human preview /
drill (a skip/echo baseline kills no mutant -> the drill FAILs). The permanent
fix candidate for both is execution attestation (the audit_deps
positive-proof track, iter73+).
```

また冒頭の `Zero-run forgery — CLOSED (SF-014 iter71):` 段落の末尾（`A red run keeps recording as-is ...` の文の後）に 1 文追加:

```python
Since iter72 the verdict additionally COUNTS executed tests (skips excluded),
closing the unittest / `go test -v` all-skip forgery classes.
```

- [ ] **Step 3-2: 拒否メッセージへ skip 起因の説明を追記**

`_reject(` の green 不成立メッセージは隣接文字列リテラルの連結で構成されており、直前リテラルが「…束縛）は」で終わって「記録しません。」へ係る。**行の途中挿入は文を壊す**ため、リテラル行

```python
                "記録しません。pytest は `-q` を外して実行してください（marker "
```

を次の 1 行に**置換**する（「記録しません。」の直後に skip 文を差し込む形・インデント維持）:

```python
                "記録しません。全テストが skip のスイート（実行 0 件）も不成立"
                "です。pytest は `-q` を外して実行してください（marker "
```

（メッセージ文字列を pin する既存テストは無いことを 2026-07-16 に grep で確認済み。変更後 `python3 -m unittest discover -s tests -p "test_record*" -v 2>&1 | tail -3` で record 系テストが green のこと。）

- [ ] **Step 3-3: 動作不変の確認（実行系スモーク）**

Run: `python3 scripts/record-test-result.py --root . "python3 -m unittest tests.test_marker_lib" && tail -1 .claude/evidence-log.jsonl | python3 -c "import json,sys; e=json.load(sys.stdin); print(e['status'], e.get('marker'))"`
Expected: `recorded: green` / `ok True`

- [ ] **Step 3-4: Commit**

```bash
git add scripts/record-test-result.py
git commit -m "docs(iter72): Task3 — record docstring/メッセージを count proof 契約に同期（unittest/go -v all-skip CLOSED・go 素出力/echo 残余）"
```

---

### Task 4: docs 層同期 — SF-014 追記＋qa-verification SKILL

**Files:**
- Modify: `docs/security-followups.md`
- Modify: `.claude/skills/qa-verification/SKILL.md`

- [ ] **Step 4-1: SF-014 に iter72 適用の追記**

`### SF-014: ...` セクションの iter71 bullet（`- **iter71 で record/drill に positive proof を適用...`）の**直後**に追加:

```markdown
- **iter72 で count proof を適用（残余 (a) の主形 CLOSED・偽陰性 2 件修正）**: `aegis_marker_verdict` に Stage 5（count proof）を追加＝count 族サマリ検出時に executed（passed+failed・skip 除外）≧1 を要求（`AEGIS_TEST_COUNT_FAMILIES`・unittest: `Ran N`−Σ`skipped=K`／pytest・jest・vitest・cargo: Σ(passed+failed)／go `-v`: `--- PASS|FAIL` 行数）。これで **(a) all-skip の unittest（`Ran N ... OK (skipped=N)`）と go `-v`（`--- SKIP:` のみ）は CLOSED**（残るは素の `go test`＝非 verbose 出力に count が存在せず all-skip と実 run が byte 同形〔iter71 実測〕・`-v` 強制は全 go ユーザーの UX 退行のため見送り・drill subsume で contained）。**(b) echo-marker は count でも原理的に閉じない**（数字ごと偽装可能・出力ベース proof の床）＝(a)-go 素出力とともに恒久策候補は execution attestation（iter73+ audit_deps positive proof と同トラック）。**併せて修正した pre-existing 偽陰性 2 件（いずれも 2026-07-16 実証）**: (i) cargo の zero-run 行 deny が doc-tests 空セクション（`running 0 tests`→`test result: ok. 0 passed`＝doc-test を持たない全 crate の実出力）を誤拒否→行 deny を削除し Stage 5 の合計算術に委譲（all-ignored は Σ=0 で引き続き false・moat pin 黒箱不変。削除で開くのは「echo pair＋実 zero-run cargo 併走」形のみだが、実 run を省いた pure echo が現行でも true のため攻撃価値は strictly dominated＝設計追補 3）。(ii) jest の実サマリ順序（failed, skipped, todo, passed）で skipped 混在時に STRONG marker の隣接要求が破れ実 run を誤拒否→中間セグメント許容へ緩和（厳格形は echo 可能だったため forge 価値不変）。vitest はサマリ行のインデント疑義に対しアンカー緩和（受理側のみ）。
```

- [ ] **Step 4-2: qa-verification SKILL の marker 記述を count 契約へ同期**

`.claude/skills/qa-verification/SKILL.md` を編集（**行番号でなくアンカー文で位置決めする**——行はドリフトする）:

1. 「green（exit 0）に marker verdict を必須化」を含む段落（`従来どおり記録。受理 green には additive な ...` の文の後）に追記:

```markdown
> iter72 以降は marker のマッチに加えて **executed 実数（passed+failed・skip 除外）≧1** を要求
> （all-skip suite の green 記録は不成立）。cargo は doc-tests 空セクションがあっても受理（偽陰性修正済み）。
```

2. 「`DRILL BLOCKED (baseline no-test-proof)`」を含む drill 側説明文の直後に 1 句追記:

```markdown
     all-skip の baseline（unittest 全 @skip／go -v 全 t.Skip）も iter72 以降は no-test-proof で BLOCKED。
```

- [ ] **Step 4-3: budget/整合確認**

Run: `python3 scripts/context_budget.py --root . 2>&1 | tail -3 && python3 scripts/check_framework_contract.py --root . 2>&1 | tail -3`
Expected: いずれも PASS（budget 超過なし）

- [ ] **Step 4-4: Commit**

```bash
git add docs/security-followups.md .claude/skills/qa-verification/SKILL.md
git commit -m "docs(iter72): Task4 — SF-014 に count proof 適用を追記＋qa-verification SKILL 同期"
```

---

## grill-plan 反映記録（Rev.2・2026-07-16）

- 致命 1: RED 期待を「正確に 10 failed」へ精密化（vacuous-pass 2 件と already-green pin 5 件を明示）→ Step 1-6 反映
- 致命 2: cargo deny 削除で受理される hybrid forge の residual pin テスト追加（`test_cargo_hybrid_echo_forge_true_known_residual`・HEAD では false→削除後 true＝deny 面変更の pin）→ Step 1-3 反映
- 致命 3: 偽装巨大数の bash 算術オーバーフロー→桁 9 文字 cap＋pin テスト（`test_forged_huge_count_stays_false_path`）→ Step 1-3／2-6 反映
- 追加修正: record メッセージの挿入位置が前行「…）は」と連結して文が壊れる→行置換方式へ（Step 3-2）／SKILL 編集を行番号→アンカー文指定へ（Step 4-2）
- 要検討（記録のみ）: evidence.sh window の巨大 cargo clip は現行と同値（false→false・退行なし）／vitest all-skip ファイルの Test Files 計上は未実証（qa で npx 試行）／新 marker.sh×旧 patterns.sh 混載は rc3 全停止だが同 dir 一括配布で構造回避（iter71 と同判断）／shellcheck 全体ゲートなし確認済み（SC2046 はコメントで意図明示）

## Self-Review（記録）

- Spec coverage: 設計 §推奨アプローチ→Task2、§単調性→Task1 不変条件＋pin、§ランナー別表→Task1 テスト網、追補 1（jest）→Step 2-1、追補 2（vitest）→Step 2-2、追補 3（cargo）→Step 2-3、追補 4（go 親）→Task1 docstring、record 文書→Task3、SF-014/SKILL→Task4。ギャップなし。
- Placeholder scan: TBD/TODO なし。全コードブロック実体。
- Type consistency: `AEGIS_TEST_COUNT_FAMILIES` の 5 フィールド形式（Task1 parity test ↔ Task2 データ ↔ Step 2-6 パーサ）一致。`_verdict` ヘルパ・`MARKER_LIB`・`ROOT` は test_marker_lib.py 既存定義を使用。
