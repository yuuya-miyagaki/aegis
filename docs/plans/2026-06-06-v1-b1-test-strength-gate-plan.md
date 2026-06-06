# B1 テスト強度ゲート（mutation drill）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** qa ゲート承認時にハーネスがミューテーション・ドリルを実走し、各変更ハンクに仕込んだ mutant をテストが全て捕まえない限り承認を拒否する。結果は非エンジニア向けに平易な日本語へ翻訳する。

**Architecture:** 承認時実走（案A）。`scripts/check_status.py` の `pre_approve_gate("qa")` が、qa agent が記録した入力仕様（`.drill`）を読んでドリルランナー（`scripts/run-test-strength-drill.py`）を subprocess 起動。runner は baseline 安定確認 → 各 mutant をバイト退避付きで適用しテスト実行 → 機械 verdict をレポートに書き exit 0/1。verdict は承認の瞬間に計算されるため偽造・staleness 不能（指紋/ハッシュ不要）。

**Tech Stack:** Python 3（標準ライブラリ unittest / subprocess / tempfile）、git diff（変更行抽出）、aegis 既存の gate 機構（`pre_approve_gate` / `GATE_REF_MAPPING` / `evidence_integrity_violations`）。

---

## grill-plan 反映（2026-06-06・実装はこの修正版を正とする）

下記の致命1〜5は実装で必ず適用する。以降の Task コードブロックのうち該当箇所は本節の修正版で上書きされる（buggy 版より本節が優先）。

- **致命1 — untracked 新規ファイルが drill 不能**: `added_lines_by_file` を `git diff HEAD`（tracked）＋`git ls-files --others --exclude-standard`（untracked 新規＝全行 added）に拡張。「新モジュール追加」タスクを drillable に。
- **派生（致命1の副作用）— ハーネス成果物の自爆**: untracked 取り込みで `docs/qa-reports/*`（`.drill`/`.md`）が「変更ハンク」と誤認され網羅フロアで必ず block。→ `added_lines_by_file` で `docs/qa-reports/` 配下を除外（`DRILL_ARTIFACT_PREFIX`）。
- **致命2 — restore 検証失敗でバックアップを消すのに「ここにある」と嘘**: restore-verification-failure 経路では `backup_path.unlink()` を**呼ばない**（concurrent と同じく温存し、メッセージの位置に実在させる）。
- **致命3 — 承認時に任意の LLM 製シェルを破壊ガード迂回で実行**: `run_test` を `shell=True` → **`shlex.split()`＋`shell=False`**（シェルメタ解釈なし＝チェーン/リダイレクト/インジェクション面を除去）。さらに `run_drill` が実行前に `test command` を**標準出力に明示**（承認時にユーザーへ可視化）。許可リストは将来強化。
- **致命4 — `splitlines()` が git の行番号とずれ別行を破壊**: `_replace_line`/`_current_line` は **`text.split("\n")`**（`\n` のみ＝git と一致）で行を取り、`"\n".join` で byte 厳密復元。
- **致命5 — 非冪等な実テストを flaky 誤判定**: コードは fail-closed のまま（手堅さ維持）。skill（Task11）と `§12` に「`test_command` は冪等に（2回クリーンに走る形）」を明記。
- **要検討の安価分も反映**: `parse_spec` に mutant 上限 `MAX_MUTANTS`（暴走承認の防止）／Task9 に「`--pre-approve-gate qa` の呼び出し元は update-gate.sh の approve のみ」を grep 確認する step／skill に「コード変更後は `.drill` 再生成」「`update-gate.sh qa na` の理由構文を実装で確認」。

> 実装は `scripts/run-test-strength-drill.py` と `tests/test_test_strength_drill.py` を本節準拠で作る。aegis 哲学「Actual behavior: code, tests, and command output」に従い、最終的な正は**コードとテスト緑**。

---

## 実装上の決定事項（spec からの精緻化・plan レビューで要確認）

1. **runner は Python（spec の "shell" を精緻化）**: `scripts/run-test-strength-drill.py`。理由 — macOS（darwin）に `timeout(1)` が標準で無い／バイト厳密 save-restore・行厳密一致・任意内容の mutation 書込が Python で圧倒的に安全。対象プロジェクトの言語には依存しない（テキスト置換＋subprocess 実行のみ）点は spec の "言語非依存" を満たす。
2. **qa=approved は「合格ドリル」を必須化（手堅い enforcement）**: `pre_approve_gate("qa")` は `.drill` 入力が存在しなければ block（「テスト対象コードが無いなら qa=n/a を、有るならドリル仕様を」）。非コードタスクは既存 `qa=n/a`（pre_na_gate 経路・ドリル免除）に流す。これにより「ドリルを書かず素通り」の沈黙故障を塞ぐ。代償＝qa=approved の意味が変わるため、qa を直接 approve する既存テスト・example を「ドリル提供 or n/a」に更新する（Phase 4 で対応）。
   - **より弱い代替**（採らない）: `.drill` 不在なら advisory 警告のみで通す。既存破壊ゼロだが opt-out 穴が残る。手堅さ優先で不採用。
3. **成果物/入力ファイルは固定名**（v1 簡素化）: 入力 `docs/qa-reports/test-strength.drill`、レポート `docs/qa-reports/test-strength.md`。iteration ごとに上書き（履歴は STATUS.md `session_history`）。`current_refs.qa` はレポートを指す。
4. **diff ベース**: `git diff --unified=0 HEAD`（working tree vs HEAD＝未コミット変更全部）。追加行（`+`）のみ mutant 対象。

---

## ファイル構成

| ファイル | 役割 | 新規/改修 |
|---|---|---|
| `scripts/run-test-strength-drill.py` | ドリルランナー本体（diff 解析・反ガミング・baseline・mutant 適用/退避/復元・集計・レポート） | 新規 |
| `examples/minimal-project/scripts/run-test-strength-drill.py` | 上の byte 同一ミラー | 新規 |
| `scripts/check_status.py` | `pre_approve_gate` に `qa` ブランチ（runner を起動） | 改修 |
| `examples/minimal-project/scripts/check_status.py` | ミラー | 改修 |
| `scripts/check_reference_drift.py` | `MIRROR_FILES` に runner を登録 | 改修 |
| `examples/minimal-project/scripts/check_reference_drift.py` | ミラー（check_reference_drift は MIRROR 対象外だが root↔example 同一運用） | 改修 |
| `.claude/skills/qa-verification/SKILL.md` | qa agent にドリル手順（mutant 選定・`.drill` 記録・プレビュー・翻訳） | 改修＋ミラー |
| `templates/profiles/full.json` | runner を recommended に登録 | 改修 |
| `tests/test_test_strength_drill.py` | runner 単体テスト | 新規 |
| `tests/test_check_status.py` | `pre_approve_gate("qa")` 結合テスト | 改修 |
| `docs/architecture-overview.md` | ドリル成果物の記述 | 改修 |

> **ミラー注意**: `MIRROR_DIRS`/`MIRROR_FILES` に載るものは root と `examples/minimal-project/` で **byte 同一**必須。runner・check_status.py・skill を編集したら必ず example 側へ `cp` する（`check_reference_drift.py --check mirror identity` が検知）。

---

## Phase 1: ドリルランナーの純粋ロジック（diff 解析・反ガミング）

この Phase は副作用の無い純関数だけを TDD で作る。ファイル書込や subprocess はまだ。

### Task 1: runner スケルトンと spec パーサ

**Files:**
- Create: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_test_strength_drill.py
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run-test-strength-drill.py"

def _load():
    spec = importlib.util.spec_from_file_location("drill", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

drill = _load()


class TestParseSpec(unittest.TestCase):
    def test_valid_spec_parses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test-strength.drill"
            p.write_text(json.dumps({
                "test_command": "true",
                "timeout_seconds": 30,
                "mutants": [
                    {"file": "src/a.py", "line": 3,
                     "original": "    return a >= b", "mutated": "    return a > b"}
                ],
            }), encoding="utf-8")
            spec = drill.parse_spec(p)
            self.assertEqual(spec["test_command"], "true")
            self.assertEqual(len(spec["mutants"]), 1)

    def test_missing_file_raises_drillerror(self):
        with self.assertRaises(drill.DrillError):
            drill.parse_spec(Path("/nonexistent/x.drill"))

    def test_malformed_json_raises_drillerror(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.drill"
            p.write_text("{not json", encoding="utf-8")
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(p)

    def test_missing_required_key_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.drill"
            p.write_text(json.dumps({"mutants": []}), encoding="utf-8")
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(p)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill -v`
Expected: FAIL（`scripts/run-test-strength-drill.py` が無い／`parse_spec` 未定義）

- [ ] **Step 3: 最小実装**

```python
#!/usr/bin/env python3
"""Test-strength drill runner (B1). Runs at qa-gate approval time.

Reads a .drill input spec (mutants + scoped test command), applies each
mutant with byte-exact save/restore, runs the test command, and emits a
machine verdict. Exit 0 = PASS (all mutants caught), 1 = FAIL/inconclusive.
Verdict is computed live so it cannot be forged or go stale.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_SPEC_KEYS = ("test_command", "timeout_seconds", "mutants")


class DrillError(Exception):
    """Any condition that makes the drill inconclusive => fail-closed."""


def parse_spec(path: Path) -> dict:
    if not path.is_file():
        raise DrillError(f"drill spec not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise DrillError(f"drill spec is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise DrillError("drill spec must be a JSON object")
    for key in REQUIRED_SPEC_KEYS:
        if key not in data:
            raise DrillError(f"drill spec missing required key: {key}")
    if not isinstance(data["mutants"], list) or not data["mutants"]:
        raise DrillError("drill spec 'mutants' must be a non-empty list")
    for m in data["mutants"]:
        for k in ("file", "line", "original", "mutated"):
            if k not in m:
                raise DrillError(f"mutant missing key '{k}': {m}")
    return data
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill -v`
Expected: PASS（4 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): add test-strength drill runner skeleton + spec parser"
```

### Task 2: git diff から追加行を抽出

**Files:**
- Modify: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
import os
import subprocess as sp

class TestAddedLines(unittest.TestCase):
    def _git(self, root, *args):
        sp.run(["git", "-C", str(root), *args], check=True,
               capture_output=True, text=True)

    def test_added_lines_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git(root, "init", "-q")
            self._git(root, "config", "user.email", "t@t")
            self._git(root, "config", "user.name", "t")
            f = root / "src"
            f.mkdir()
            (f / "a.py").write_text("x = 1\n", encoding="utf-8")
            self._git(root, "add", "-A")
            self._git(root, "commit", "-qm", "init")
            # add two new lines (3 and 4 in new file)
            (f / "a.py").write_text("x = 1\ny = 2\nz = 3\n", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertIn("src/a.py", added)
            self.assertEqual(added["src/a.py"], {2, 3})

    def test_no_changes_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git(root, "init", "-q")
            self._git(root, "config", "user.email", "t@t")
            self._git(root, "config", "user.name", "t")
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            self._git(root, "add", "-A")
            self._git(root, "commit", "-qm", "init")
            self.assertEqual(drill.added_lines_by_file(root, "HEAD"), {})
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestAddedLines -v`
Expected: FAIL（`added_lines_by_file` 未定義）

- [ ] **Step 3: 最小実装**（runner に追記）

```python
def added_lines_by_file(root: Path, ref: str = "HEAD") -> dict[str, set[int]]:
    """Map each changed file (new path) to the set of ADDED (+) line numbers
    in the working tree vs `ref`. Uses --unified=0 so every shown '+' line is
    a real addition (no context lines)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "diff", "--unified=0", ref],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError) as exc:
        raise DrillError(f"git diff failed: {exc}")

    result: dict[str, set[int]] = {}
    cur_file: str | None = None
    new_lineno: int | None = None
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            cur_file = path[2:] if path.startswith("b/") else (
                None if path == "/dev/null" else path)
            new_lineno = None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            new_lineno = int(m.group(1)) if m else None
        elif line.startswith("+") and not line.startswith("+++"):
            if cur_file is not None and new_lineno is not None:
                result.setdefault(cur_file, set()).add(new_lineno)
                new_lineno += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass  # deletions do not advance new-file line number
    return result
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestAddedLines -v`
Expected: PASS（2 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): extract added (+) lines from git diff for anti-gaming"
```

### Task 3: 反ガミング検証（追加行限定＋網羅フロア）

**Files:**
- Modify: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestAntiGaming(unittest.TestCase):
    def test_mutant_outside_added_lines_rejected(self):
        added = {"src/a.py": {3, 4}}
        mutants = [{"file": "src/a.py", "line": 9,
                    "original": "x", "mutated": "y"}]
        v = drill.anti_gaming_violations(added, mutants)
        self.assertTrue(any("not an added" in m for m in v))

    def test_uncovered_hunk_rejected(self):
        # two contiguous runs: {3,4} and {7}. mutant only covers first run.
        added = {"src/a.py": {3, 4, 7}}
        mutants = [{"file": "src/a.py", "line": 3,
                    "original": "x", "mutated": "y"}]
        v = drill.anti_gaming_violations(added, mutants)
        self.assertTrue(any("coverage floor" in m for m in v))

    def test_all_runs_covered_passes(self):
        added = {"src/a.py": {3, 4, 7}}
        mutants = [
            {"file": "src/a.py", "line": 3, "original": "x", "mutated": "y"},
            {"file": "src/a.py", "line": 7, "original": "p", "mutated": "q"},
        ]
        self.assertEqual(drill.anti_gaming_violations(added, mutants), [])
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestAntiGaming -v`
Expected: FAIL（`anti_gaming_violations` 未定義）

- [ ] **Step 3: 最小実装**

```python
def _contiguous_runs(sorted_lines: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for n in sorted_lines:
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return runs


def anti_gaming_violations(
    added_by_file: dict[str, set[int]],
    mutants: list[dict],
) -> list[str]:
    """(a) each mutant must sit on an added (+) line; (b) every contiguous
    run of added lines must contain >=1 mutant (per-hunk coverage floor)."""
    violations: list[str] = []
    mutant_lines: dict[str, set[int]] = {}
    for m in mutants:
        mutant_lines.setdefault(m["file"], set()).add(int(m["line"]))

    for m in mutants:
        f, ln = m["file"], int(m["line"])
        if ln not in added_by_file.get(f, set()):
            violations.append(
                f"{f}:{ln} is not an added (+) line in the diff "
                f"(anti-gaming: mutants must sit on changed code)")

    for f, lines in added_by_file.items():
        for run in _contiguous_runs(sorted(lines)):
            if not (mutant_lines.get(f, set()) & set(run)):
                violations.append(
                    f"{f}: added lines {run[0]}-{run[-1]} have no mutant "
                    f"(coverage floor: every changed hunk needs one)")
    return violations
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestAntiGaming -v`
Expected: PASS（3 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): anti-gaming — added-line check + per-hunk coverage floor"
```

---

---

## Phase 2: 副作用つきドリル実行（baseline・mutant 適用・退避/復元/並行ガード・集計）

### Task 4: テストコマンド実行ラッパ（timeout 付き）

**Files:**
- Modify: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestRunTest(unittest.TestCase):
    def test_green_returns_passed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("true", Path(d), 10), "passed")

    def test_red_returns_failed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("false", Path(d), 10), "failed")

    def test_timeout_returns_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("sleep 5", Path(d), 1), "timeout")

    def test_missing_command_returns_error(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                drill.run_test("definitely-not-a-cmd-xyz", Path(d), 10), "error")
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestRunTest -v`
Expected: FAIL（`run_test` 未定義）

- [ ] **Step 3: 最小実装**

```python
def run_test(command: str, cwd: Path, timeout_seconds: int) -> str:
    """Run the scoped test command. Returns one of:
    'passed' (exit 0), 'failed' (non-zero), 'timeout', 'error' (could not run).
    Python's subprocess timeout is used (portable; macOS has no timeout(1))."""
    try:
        proc = subprocess.run(
            command, shell=True, cwd=str(cwd),
            capture_output=True, timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    except OSError:
        return "error"
    return "passed" if proc.returncode == 0 else "failed"
```

> 注: `shell=True` は qa agent が記録した信頼済みコマンドのみに使う（入力仕様は harness 内で生成・人間がレビュー）。外部入力ではない。

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestRunTest -v`
Expected: PASS（4 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): scoped test runner with portable timeout"
```

### Task 5: baseline 安定確認（2回緑）

**Files:**
- Modify: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestBaseline(unittest.TestCase):
    def test_both_green_is_green(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.check_baseline("true", Path(d), 10), "green")

    def test_red_is_red(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.check_baseline("false", Path(d), 10), "red")

    def test_flaky_is_flaky(self):
        # a command that passes once then fails: use a marker file
        with tempfile.TemporaryDirectory() as d:
            cmd = ("f=.flag; if [ -e $f ]; then exit 1; "
                   "else touch $f; exit 0; fi")
            self.assertEqual(drill.check_baseline(cmd, Path(d), 10), "flaky")
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestBaseline -v`
Expected: FAIL（`check_baseline` 未定義）

- [ ] **Step 3: 最小実装**

```python
def check_baseline(command: str, cwd: Path, timeout_seconds: int) -> str:
    """Run the test command twice on the UNMODIFIED code. Returns:
    'green' (both passed), 'red' (a run failed), 'flaky' (passed then failed
    or vice versa), 'inconclusive' (timeout/error). A non-green baseline makes
    the whole drill fail-closed (cannot distinguish mutant-caught from broken)."""
    first = run_test(command, cwd, timeout_seconds)
    if first in ("timeout", "error"):
        return "inconclusive"
    second = run_test(command, cwd, timeout_seconds)
    if second in ("timeout", "error"):
        return "inconclusive"
    if first == "passed" and second == "passed":
        return "green"
    if first == "failed" and second == "failed":
        return "red"
    return "flaky"
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestBaseline -v`
Expected: PASS（3 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): baseline stability check (2x green) — flaky guard"
```

### Task 6: mutant 適用＋バイト退避/復元/並行ガード（安全の核心）

**Files:**
- Modify: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestApplyMutant(unittest.TestCase):
    def _mk(self, d, body="def f(a, b):\n    return a >= b\n"):
        root = Path(d)
        (root / "src").mkdir()
        (root / "src" / "m.py").write_text(body, encoding="utf-8")
        return root

    def test_caught_when_test_detects_mutant(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            mutant = {"file": "src/m.py", "line": 2,
                      "original": "    return a >= b",
                      "mutated": "    return a > b"}
            # test command that is red iff line 2 contains '>' without '='
            cmd = "grep -q 'return a >= b' src/m.py"  # green on original
            result = drill.apply_mutant_and_test(root, mutant, cmd, 10)
            self.assertEqual(result, "caught")
            # file fully restored byte-for-byte
            self.assertEqual((root / "src" / "m.py").read_text(),
                             "def f(a, b):\n    return a >= b\n")

    def test_survived_when_test_blind(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            mutant = {"file": "src/m.py", "line": 2,
                      "original": "    return a >= b",
                      "mutated": "    return a > b"}
            result = drill.apply_mutant_and_test(root, mutant, "true", 10)
            self.assertEqual(result, "survived")
            self.assertEqual((root / "src" / "m.py").read_text(),
                             "def f(a, b):\n    return a >= b\n")

    def test_line_mismatch_aborts_without_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            mutant = {"file": "src/m.py", "line": 2,
                      "original": "    return a <= b",  # wrong original
                      "mutated": "    return a < b"}
            with self.assertRaises(drill.DrillError):
                drill.apply_mutant_and_test(root, mutant, "true", 10)
            self.assertEqual((root / "src" / "m.py").read_text(),
                             "def f(a, b):\n    return a >= b\n")

    def test_concurrent_edit_preserved_not_clobbered(self):
        # Simulate a third party rewriting the file DURING the test run.
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            mutant = {"file": "src/m.py", "line": 2,
                      "original": "    return a >= b",
                      "mutated": "    return a > b"}
            sentinel = "USER EDIT DURING DRILL\n"
            cmd = f"printf '%s' '{sentinel}' > src/m.py"  # overwrites file
            with self.assertRaises(drill.ConcurrentEditError):
                drill.apply_mutant_and_test(root, mutant, cmd, 10)
            # the third-party edit is preserved, NOT overwritten by restore
            self.assertEqual((root / "src" / "m.py").read_text(), sentinel)
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestApplyMutant -v`
Expected: FAIL（`apply_mutant_and_test` / `ConcurrentEditError` 未定義）

- [ ] **Step 3: 最小実装**

```python
class ConcurrentEditError(DrillError):
    """A third party modified the target file mid-drill; we refuse to
    overwrite their work (the core 'never destroy uncommitted work' promise)."""


def _replace_line(data: bytes, line_no: int, new_line: str) -> bytes:
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    if line_no < 1 or line_no > len(lines):
        raise DrillError(f"line {line_no} out of range (1..{len(lines)})")
    orig = lines[line_no - 1]
    newline = "\n" if orig.endswith("\n") else ""
    lines[line_no - 1] = new_line + newline
    return "".join(lines).encode("utf-8")


def _current_line(data: bytes, line_no: int) -> str:
    lines = data.decode("utf-8").splitlines()
    if line_no < 1 or line_no > len(lines):
        raise DrillError(f"line {line_no} out of range (1..{len(lines)})")
    return lines[line_no - 1]


def apply_mutant_and_test(root: Path, mutant: dict, command: str,
                          timeout_seconds: int) -> str:
    """Apply ONE mutant with byte-exact save/restore, run the test, restore.
    Returns 'caught' (test went red), 'survived' (test stayed green).
    Raises DrillError on any inconclusive/abort condition (fail-closed).
    Restore happens in finally; if a third party changed the file mid-run we
    do NOT overwrite (ConcurrentEditError)."""
    target = root / mutant["file"]
    if not target.is_file():
        raise DrillError(f"mutant target not found: {target}")
    original_bytes = target.read_bytes()

    # verify the target line is exactly what the LLM claimed (no line drift)
    if _current_line(original_bytes, int(mutant["line"])) != mutant["original"]:
        raise DrillError(
            f"line {mutant['line']} of {mutant['file']} does not match "
            f"'original'; refusing to mutate (line drift)")

    backup = tempfile.NamedTemporaryFile(delete=False)
    backup.write(original_bytes)
    backup.close()
    backup_path = Path(backup.name)

    mutant_bytes: bytes | None = None
    try:
        mutant_bytes = _replace_line(
            original_bytes, int(mutant["line"]), mutant["mutated"])
        target.write_bytes(mutant_bytes)
        outcome = run_test(command, root, timeout_seconds)
        if outcome == "failed":
            return "caught"
        if outcome == "passed":
            return "survived"
        raise DrillError(f"test command was inconclusive ({outcome})")
    finally:
        current = target.read_bytes() if target.is_file() else b""
        if mutant_bytes is not None and current == mutant_bytes:
            target.write_bytes(backup_path.read_bytes())
            if target.read_bytes() != original_bytes:
                backup_path.unlink(missing_ok=True)
                raise DrillError(
                    f"restore verification failed for {target}; "
                    f"backup at {backup_path}")
            backup_path.unlink(missing_ok=True)
        elif current == original_bytes:
            backup_path.unlink(missing_ok=True)  # already clean
        else:
            # third party (editor/watcher/other session) changed the file
            raise ConcurrentEditError(
                f"{target} was modified during the drill; refusing to "
                f"overwrite. Original bytes preserved at {backup_path}")
```

> **安全の要点**: `finally` で必ず復元を試みる。復元前に「現バイト == 自分が書いた mutant」を確認し、第三者が触っていたら `ConcurrentEditError` を投げてユーザーの編集を温存（バックアップ位置を提示）。`test_line_mismatch_aborts_without_write` のように書込前に弾くケースでは `mutant_bytes is None` のまま finally に入り、`current == original_bytes` 分岐で何もしない。

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestApplyMutant -v`
Expected: PASS（4 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): mutant apply with byte-exact save/restore + concurrent-edit guard"
```

### Task 7: 集計とレポート生成

**Files:**
- Modify: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestReport(unittest.TestCase):
    def test_pass_report_shape(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.md"
            drill.write_report(out, verdict="PASS", total=2, caught=2,
                               baseline="green", survived=[])
            text = out.read_text()
            self.assertIn("verdict: PASS", text)
            self.assertIn("mutants_total: 2", text)
            self.assertIn("mutants_caught: 2", text)
            self.assertIn("survived: []", text)

    def test_fail_report_lists_survivors(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.md"
            drill.write_report(out, verdict="FAIL", total=2, caught=1,
                               baseline="green", survived=["src/a.py:3"])
            text = out.read_text()
            self.assertIn("verdict: FAIL", text)
            self.assertIn("src/a.py:3", text)
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestReport -v`
Expected: FAIL（`write_report` 未定義）

- [ ] **Step 3: 最小実装**

```python
def write_report(report_path: Path, *, verdict: str, total: int, caught: int,
                 baseline: str, survived: list[str]) -> None:
    """Write the machine block (harness-authored, not LLM prose). The qa agent
    appends a plain-Japanese explanation block below this when presenting."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    survived_repr = "[]" if not survived else (
        "[" + ", ".join(survived) + "]")
    report_path.write_text(
        "# テスト強度ドリル結果（機械ブロック・ハーネス生成）\n\n"
        "```\n"
        f"verdict: {verdict}\n"
        f"mutants_total: {total}\n"
        f"mutants_caught: {caught}\n"
        f"baseline: {baseline}\n"
        f"survived: {survived_repr}\n"
        "```\n",
        encoding="utf-8",
    )
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestReport -v`
Expected: PASS（2 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): machine-block report generation"
```

### Task 8: main 統合（オーケストレーション＋exit code）

**Files:**
- Modify: `scripts/run-test-strength-drill.py`
- Test: `tests/test_test_strength_drill.py`

- [ ] **Step 1: 失敗するテストを書く**（subprocess で end-to-end）

```python
class TestMainEndToEnd(unittest.TestCase):
    def _git_init(self, root):
        for args in (["init", "-q"], ["config", "user.email", "t@t"],
                     ["config", "user.name", "t"]):
            sp.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)

    def _run(self, root, spec_path, report_path):
        return sp.run(
            ["python3", str(SCRIPT), "--root", str(root),
             "--spec", str(spec_path), "--report", str(report_path)],
            capture_output=True, text=True)

    def test_pass_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git_init(root)
            (root / "src").mkdir()
            (root / "src" / "m.py").write_text("a = 1\n", encoding="utf-8")
            sp.run(["git", "-C", str(root), "add", "-A"], check=True,
                   capture_output=True)
            sp.run(["git", "-C", str(root), "commit", "-qm", "i"], check=True,
                   capture_output=True)
            # add line 2 (a changed hunk)
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "grep -q 'b = 2' src/m.py",
                "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("verdict: PASS", report.read_text())

    def test_survived_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git_init(root)
            (root / "src").mkdir()
            (root / "src" / "m.py").write_text("a = 1\n", encoding="utf-8")
            sp.run(["git", "-C", str(root), "add", "-A"], check=True,
                   capture_output=True)
            sp.run(["git", "-C", str(root), "commit", "-qm", "i"], check=True,
                   capture_output=True)
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "true",  # blind test => survives
                "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 1)
            self.assertIn("verdict: FAIL", report.read_text())

    def test_missing_spec_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git_init(root)
            res = self._run(root, root / "nope.drill", root / "r.md")
            self.assertEqual(res.returncode, 1)
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_test_strength_drill.TestMainEndToEnd -v`
Expected: FAIL（`main` / argparse 未実装）

- [ ] **Step 3: 最小実装**

```python
def run_drill(root: Path, spec_path: Path, report_path: Path) -> int:
    """Orchestrate. Returns 0 (PASS) or 1 (FAIL/inconclusive). Never raises:
    every DrillError becomes a fail-closed verdict + non-zero exit."""
    try:
        spec = parse_spec(spec_path)
        added = added_lines_by_file(root, "HEAD")
        ag = anti_gaming_violations(added, spec["mutants"])
        if ag:
            print("DRILL BLOCKED (anti-gaming):")
            for v in ag:
                print(f"  - {v}")
            write_report(report_path, verdict="FAIL", total=len(spec["mutants"]),
                         caught=0, baseline="n/a", survived=[])
            return 1

        cmd, timeout = spec["test_command"], int(spec["timeout_seconds"])
        base = check_baseline(cmd, root, timeout)
        if base != "green":
            print(f"DRILL BLOCKED (baseline {base}): tests must be green and "
                  f"stable before drilling.")
            write_report(report_path, verdict="FAIL", total=len(spec["mutants"]),
                         caught=0, baseline=base, survived=[])
            return 1

        survived: list[str] = []
        caught = 0
        for m in spec["mutants"]:
            outcome = apply_mutant_and_test(root, m, cmd, timeout)
            if outcome == "caught":
                caught += 1
            else:
                survived.append(f"{m['file']}:{m['line']}")

        verdict = "PASS" if not survived else "FAIL"
        write_report(report_path, verdict=verdict, total=len(spec["mutants"]),
                     caught=caught, baseline="green", survived=survived)
        if survived:
            print("DRILL FAIL — these mutants survived (tests have a hole):")
            for s in survived:
                print(f"  - {s}")
            return 1
        print("DRILL PASS — all mutants caught.")
        return 0
    except ConcurrentEditError as exc:
        print(f"DRILL ABORTED (concurrent edit): {exc}")
        return 1
    except DrillError as exc:
        print(f"DRILL BLOCKED (fail-closed): {exc}")
        try:
            write_report(report_path, verdict="FAIL", total=0, caught=0,
                         baseline="inconclusive", survived=[])
        except OSError:
            pass
        return 1


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Test-strength drill runner (B1)")
    p.add_argument("--root", default=".")
    p.add_argument("--spec", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args(argv)
    return run_drill(Path(args.root).resolve(), Path(args.spec), Path(args.report))


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_test_strength_drill -v`
Expected: PASS（全 Task 1-8 のテスト）

- [ ] **Step 5: example へミラー＋コミット**

```bash
cp scripts/run-test-strength-drill.py examples/minimal-project/scripts/run-test-strength-drill.py
git add scripts/run-test-strength-drill.py examples/minimal-project/scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "feat(b1): drill runner main orchestration + example mirror"
```

---

---

## Phase 3: ゲート結合（`pre_approve_gate("qa")` が承認時にドリルを実走）

### Task 9: qa ブランチを `pre_approve_gate` に追加

**Files:**
- Modify: `scripts/check_status.py`（`pre_approve_gate` 末尾の `return 0` 直前・現状 line 857-858 付近 / `run_qa_drill` ヘルパを近傍に追加）
- Test: `tests/test_check_status.py`

既存 `pre_approve_gate` は qa を mode-transition でないゲートとして扱い、phase-order → prereq → strict チェックを通過して末尾 `return 0` に到達する（Explore 確認済み）。その**直前**にドリル実走を差し込む。既存チェックを温存し、ドリルを最終関門にする。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_check_status.py に追記
import json as _json
import subprocess as _sp

class TestQaDrillGate(unittest.TestCase):
    def _project(self, d, *, with_drill, blind=False):
        """Build a temp project: git repo + committed file + uncommitted
        change + STATUS.md (phase=qa, review approved) + optional .drill."""
        root = Path(d)
        for a in (["init", "-q"], ["config", "user.email", "t@t"],
                  ["config", "user.name", "t"]):
            _sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)
        src = root / "src"; src.mkdir()
        (src / "m.py").write_text("a = 1\n", encoding="utf-8")
        _sp.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
        _sp.run(["git", "-C", str(root), "commit", "-qm", "i"], check=True,
                capture_output=True)
        (src / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")  # changed hunk
        docs = root / "docs"; docs.mkdir(exist_ok=True)
        (docs / "STATUS.md").write_text(make_status_md(
            phase="qa", task_type="feature", task_size="M",
            approvals={"brainstorm": "approved", "plan": "approved",
                       "review": "approved", "qa": "pending"},
            refs={"plan": "docs/p.md", "review": "docs/r.md"},
        ), encoding="utf-8")
        # the gate only needs the drill spec to be present + runnable; we do not
        # rely on the referenced plan/review files existing (advisory only).
        qa_reports = docs / "qa-reports"; qa_reports.mkdir(parents=True, exist_ok=True)
        if with_drill:
            cmd = "true" if blind else "grep -q 'b = 2' src/m.py"
            (qa_reports / "test-strength.drill").write_text(_json.dumps({
                "test_command": cmd, "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
        # the drill runner must be importable from scripts/ next to check_status.py
        return root

    def test_qa_with_passing_drill_allows(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._project(d, with_drill=True)
            rc, out = run_check(str(root), "--pre-approve-gate", "qa")
            self.assertEqual(rc, 0, f"expected allow, got: {out}")

    def test_qa_without_drill_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._project(d, with_drill=False)
            rc, out = run_check(str(root), "--pre-approve-gate", "qa")
            self.assertEqual(rc, 1)
            self.assertIn("drill", out.lower())

    def test_qa_with_surviving_mutant_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._project(d, with_drill=True, blind=True)
            rc, out = run_check(str(root), "--pre-approve-gate", "qa")
            self.assertEqual(rc, 1)
```

> **重要（run_check のコピー）**: `run_check` は `scripts/check_status.py` を直接 `--root <temp>` で起動するが、`run_qa_drill` は runner を `check_status.py` と同じディレクトリから探す。temp プロジェクトには runner が無いので、`run_qa_drill` は **runner の絶対パスを `check_status.py` の隣**（実リポジトリの `scripts/`）から解決する実装にする（temp root にコピー不要）。下の実装はそれを満たす。

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_check_status.TestQaDrillGate -v`
Expected: FAIL（qa ブランチ未実装＝ドリル無視で allow されるか、helper 未定義）

- [ ] **Step 3: 最小実装**（`scripts/check_status.py`）

`pre_approve_gate` 末尾の `return 0`（line 858 付近）の直前に挿入:

```python
    if gate_name == "qa":
        drill_rc = run_qa_drill(root)
        if drill_rc != 0:
            return 1

    # Gate-ref consistency already checked above (before mode-transition gates).
    return 0
```

`pre_approve_gate` の定義より上（モジュール関数として）に追加:

```python
def run_qa_drill(root: Path) -> int:
    """qa 承認時にテスト強度ドリルを実走する（案A）。
    spec が無ければ block（テスト対象コードが無いなら qa=n/a を使う）。
    Returns 0 if drill passes (or n/a path), 1 to block approval."""
    spec_path = root / "docs" / "qa-reports" / "test-strength.drill"
    report_path = root / "docs" / "qa-reports" / "test-strength.md"
    if not spec_path.is_file():
        print("ERROR: qa を approve するにはテスト強度ドリルが必要です。")
        print("       テスト対象コードが無いタスクは qa=n/a（理由付き）にしてください。")
        print(f"       ドリル仕様が見つかりません: {spec_path}")
        return 1
    runner = Path(__file__).resolve().parent / "run-test-strength-drill.py"
    if not runner.is_file():
        print(f"ERROR: ドリルランナーが見つかりません: {runner}")
        return 1
    try:
        proc = subprocess.run(
            ["python3", str(runner), "--root", str(root),
             "--spec", str(spec_path), "--report", str(report_path)],
            capture_output=True, text=True,
        )
    except OSError as exc:
        print(f"ERROR: ドリル起動に失敗: {exc}")
        return 1
    # surface the runner's plain output so update-gate.sh echoes it to the user
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    return 0 if proc.returncode == 0 else 1
```

`check_status.py` 冒頭の import に `subprocess` が無ければ追加（既存確認: あれば不要）。

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_check_status.TestQaDrillGate -v`
Expected: PASS（3 tests）。もし prereq チェックで弾かれ allow テストが rc=1 になる場合は、`make_status_md` の approvals/phase を調整（review/plan/brainstorm を approved、phase=qa）して qa ブランチ到達を確保。

- [ ] **Step 5: example へミラー＋コミット**

```bash
cp scripts/check_status.py examples/minimal-project/scripts/check_status.py
git add scripts/check_status.py examples/minimal-project/scripts/check_status.py tests/test_check_status.py
git commit -m "feat(b1): pre_approve_gate runs test-strength drill at qa approval (Approach A)"
```

---

---

## Phase 4: 登録・既存資産の整合・統合検証

### Task 10: runner を mirror identity に登録

**Files:**
- Modify: `scripts/check_reference_drift.py`（`MIRROR_FILES`）
- Test: `tests/test_mirror_identity.py`（既存が `MIRROR_FILES` を走査するので自動カバー。明示テストを1本足す）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_mirror_identity.py に追記
def test_drill_runner_registered_in_mirror_files(self):
    from check_reference_drift import MIRROR_FILES
    from pathlib import Path as _P
    self.assertIn(_P("scripts") / "run-test-strength-drill.py", MIRROR_FILES)
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_mirror_identity -v`
Expected: FAIL（未登録）

- [ ] **Step 3: 最小実装**（`scripts/check_reference_drift.py`）

```python
MIRROR_FILES = [
    Path("scripts") / "check_status.py",
    Path("scripts") / "update-gate.sh",
    Path("scripts") / "run-test-strength-drill.py",  # B1 drill runner
]
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_mirror_identity -v`
Expected: PASS。続けて drift 全体も green を確認:
Run: `python3 scripts/check_reference_drift.py`
Expected: mirror identity チェックが root↔example で一致（Task 8/9 で cp 済みのため）

- [ ] **Step 5: example へミラー＋コミット**

```bash
cp scripts/check_reference_drift.py examples/minimal-project/scripts/check_reference_drift.py
git add scripts/check_reference_drift.py examples/minimal-project/scripts/check_reference_drift.py tests/test_mirror_identity.py
git commit -m "feat(b1): register drill runner in mirror identity check"
```

### Task 11: qa-verification skill にドリル手順を追記

**Files:**
- Modify: `.claude/skills/qa-verification/SKILL.md`（`## Plan 事前チェックリスト` の後・`## QA レポート出力` の前に挿入）
- Mirror: `examples/minimal-project/.claude/skills/qa-verification/SKILL.md`

- [ ] **Step 1: 節を追記**（テスト不要のドキュメント作業。挿入する本文）

````markdown
## テスト強度ドリル（mutation drill）

qa ゲート承認の前に必ず実施する。承認時にハーネス（`pre_approve_gate`）が
同じドリルを再実走し、合格しなければ承認を**拒否**する（偽造・古い結果は通らない）。

### 手順

1. **変更コードを読む**: `git diff HEAD` で今回のタスクの追加行（`+`）を把握する。
2. **mutant を選定**: 各「変更ハンク（連続した追加行のかたまり）」に**最低1個**、
   「テストが守ると主張する振る舞い」を壊す mutant を選ぶ（比較反転・境界±1・
   条件否定・早期 return 等）。mutant は必ず**追加行**の上に置く（文脈行は不可）。
3. **入力仕様を書く**: `docs/qa-reports/test-strength.drill` に JSON で記録する。

   ```json
   {
     "test_command": "<関連テストだけを走らせる最小コマンド>",
     "timeout_seconds": 60,
     "mutants": [
       {"file": "src/discount.py", "line": 12,
        "original": "    if total >= 100:", "mutated": "    if total > 100:"}
     ]
   }
   ```

   - `original` は対象行の**現在の中身と完全一致**させる（行ズレ防止）。
   - `test_command` は**フルスイートでなく関連テストにスコープ**する（承認のたび
     実走するため。重い場合の対処は下記）。
4. **プレビュー実走**: ユーザーに見せる前にローカルで実走して結果を確認する。

   ```bash
   python3 scripts/run-test-strength-drill.py --root . \
     --spec docs/qa-reports/test-strength.drill \
     --report docs/qa-reports/test-strength.md
   ```
5. **平易な日本語へ翻訳**してユーザーに提示する（合否はハーネスが決定済み。
   あなたは説明するだけで合否を動かさない）:
   - 合格✅例:「『割引計算』にわざとバグ（`>=`→`>`）を入れたらテスト〇〇が
     気づいて赤くなりました。このテストは意味があります。」
   - 不合格⚠️例:「バグを入れてもテストは緑のまま＝この部分は取りこぼします。
     **やること: 100 円ちょうどのケースのテストを追加してください。**」
6. **ref を記録**: `current_refs.qa` を `docs/qa-reports/test-strength.md` にする。
7. ドリル実行中は対象ファイルを開く watch テストや自動保存エディタを止める
   （ハーネスは並行編集を検知すると安全のため承認を中止する）。

### このドリルを省略してよい場合（qa=n/a）

- 非コード変更のみ（ドキュメント・設定・文言）。
- テストを伴わない/伴えないタスク。
- 単一行 mutant を作れない変更のみ（コード削除・複数行のみ）。

これらは `update-gate.sh qa na "<理由>"` で qa=n/a にする（ドリル免除）。

### 重くて承認が通らないとき

- `test_command` を関連テスト1ファイル等に絞る。
- mutant 数を各ハンク1個に抑える。
- それでも非現実的なら qa=n/a を理由付きで申告する。
````

- [ ] **Step 2: ミラー＋コミット**

```bash
cp .claude/skills/qa-verification/SKILL.md examples/minimal-project/.claude/skills/qa-verification/SKILL.md
git add .claude/skills/qa-verification/SKILL.md examples/minimal-project/.claude/skills/qa-verification/SKILL.md
git commit -m "docs(b1): qa-verification skill — mutation drill procedure"
```

- [ ] **Step 3: markdownlint 確認**（ネスト fence の警告に注意）

Run: `npx markdownlint-cli2 ".claude/skills/qa-verification/SKILL.md" 2>/dev/null || true`
Expected: 重大な警告なし（あれば fence のネストを解消）

### Task 12: full プロファイルに runner を登録

**Files:**
- Modify: `templates/profiles/full.json`（`recommended` 配列に追加）
- Test: contract チェックで検証

- [ ] **Step 1: 追記**（`templates/profiles/full.json` の `recommended` に追加）

```json
    "scripts/run-test-strength-drill.py"
```

- [ ] **Step 2: contract 検証**

Run: `python3 scripts/check_framework_contract.py --profile=full`
Expected: PASS（新スクリプトが存在し登録と一致）

- [ ] **Step 3: コミット**

```bash
git add templates/profiles/full.json
git commit -m "feat(b1): register drill runner in full profile"
```

### Task 13: qa を直接 approve する既存テスト・example を「ドリル or n/a」に更新

**Files:**
- Modify: qa=approved を `pre_approve_gate("qa")` 経由で通す既存テスト（grep で特定）
- Modify: `examples/minimal-project/docs/STATUS.md`（もし qa=approved を含むなら）

> **背景**: 決定事項2により `pre_approve_gate("qa")` はドリル必須になった。`update-gate.sh qa approve` や `pre_approve_gate("qa")` を呼ぶ既存テスト/スモークは、ドリル仕様を用意するか qa=n/a に変える必要がある。**`--check-deploy-ready` 等、approval 値を読むだけのテストは影響しない**（再 approve しないため）。

- [ ] **Step 1: 影響範囲を特定**

Run: `grep -rn "pre-approve-gate qa\|pre_approve_gate(\"qa\"\|update-gate.sh qa approve" tests/ examples/ bin/ scripts/ docs/ 2>/dev/null`
Expected: ドリルを伴わず qa を approve している箇所の一覧

- [ ] **Step 2: 各箇所を修正**
  - テスト内で qa を approve する目的が「後続フェーズの前提を作る」だけなら、`make_status_md(approvals={"qa": "approved"}, refs={"qa": "..."})` のように**値を直接セット**する形に保つ（`pre_approve_gate("qa")` を呼ばないなら影響なし）。
  - 実際に `pre_approve_gate("qa")` の allow を確認している既存テストがあれば、Task 9 の `_project` 同様にドリル仕様を与えるヘルパへ寄せる。
  - example のスモークが qa を approve するなら、`examples/minimal-project/docs/qa-reports/test-strength.drill` を同梱するか、example のタスクを qa=n/a に設定する。

- [ ] **Step 3: 回帰確認＋コミット**

Run: `python3 -m unittest discover -s tests -v`
Expected: 全 green

```bash
git add -A
git commit -m "test(b1): adapt existing qa-approval paths to require drill or n/a"
```

### Task 14: architecture-overview にドリル成果物を反映

**Files:**
- Modify: `docs/architecture-overview.md`

- [ ] **Step 1: 追記**（qa フェーズ／成果物の節に1段落）

> qa ゲートは承認時に `scripts/run-test-strength-drill.py` を実走し、変更コードに
> 仕込んだ mutant をテストが全て捕まえない限り承認を拒否する。入力は
> `docs/qa-reports/test-strength.drill`、機械生成レポートは
> `docs/qa-reports/test-strength.md`（`current_refs.qa`）。

- [ ] **Step 2: コミット**

```bash
git add docs/architecture-overview.md
git commit -m "docs(b1): document test-strength drill artifact in architecture overview"
```

### Task 15: 統合検証（全 green を証拠化）

- [ ] **Step 1: 全テスト**

Run: `python3 -m unittest discover -s tests -v`
Expected: 既存 213 + B1 追加分が全 PASS

- [ ] **Step 2: contract / drift / status strict**

Run:
```bash
python3 scripts/check_framework_contract.py --profile=full
python3 scripts/check_framework_contract.py --profile=standard
python3 scripts/check_reference_drift.py
python3 scripts/check_status.py --root . --strict
```
Expected: 全 PASS（特に mirror identity が root↔example 一致）

- [ ] **Step 3: eval tiers（あれば）**

Run: `bash scripts/run-evals.sh 2>/dev/null || ls scripts | grep -i eval`
Expected: 既存 eval 体系があれば tier 0-3 green（無ければスキップ理由を記録）

- [ ] **Step 4: 実 scaffold スモーク**

Run: 一時ディレクトリへ `full` で scaffold → 生成物に `scripts/run-test-strength-drill.py` が含まれることを確認 → ダミー変更＋`.drill` で承認パス（PASS）と survived（block）を1往復。
Expected: PASS で承認可・survived で blocked

- [ ] **Step 5: 証拠を残してコミット**

```bash
git add -A
git commit -m "test(b1): full integration verification green (tests/contract/drift/scaffold)"
```

---

## Self-Review（プラン執筆者によるチェック・実施済み）

- **spec カバレッジ**: §6.1 runner=Task1-8 / §6.3 入力仕様=Task1,9,11 / §6.4 ゲート結合=Task9 / §7.1 反ガミング=Task3 / §7.4 安全(byte/並行/baseline/timeout)=Task4-6 / §6.2 レポート=Task7 / §10 結合点=Task9-14 / §11 要否=Task9(n/a),11 / §12 限界=skill とレポート文言。**未カバーなし**。
- **プレースホルダ**: TBD/TODO なし。各コードステップは実行可能な実体を記載。
- **型/名称整合**: `parse_spec`/`added_lines_by_file`/`anti_gaming_violations`/`run_test`/`check_baseline`/`apply_mutant_and_test`/`write_report`/`run_drill`/`main`（runner）と `run_qa_drill`（check_status）の呼称は全 Task で一致。`ConcurrentEditError ⊂ DrillError`。`.drill`/`.md` パスは Task9・11 で一致（`docs/qa-reports/test-strength.{drill,md}`）。
- **既知の留意（実装中に確認）**: (1) `pre_approve_gate("qa")` の prereq/strict チェックを Task9 のテスト STATUS が満たすか（満たさなければ approvals/phase を調整）。(2) Task13 の影響範囲は grep 結果で確定（現状未知数）。(3) `splitlines(keepends=True)` は CRLF/末尾改行無しファイルでも原バイトを保つが、最終行に改行が無い mutant 行の置換時は `_replace_line` の newline 判定で担保。

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-06-06-v1-b1-test-strength-gate-plan.md`. Two execution options:

1. **Subagent-Driven（推奨）** — タスクごとに新鮮な subagent を割り当て、タスク間で2段レビュー、速い反復。`superpowers:subagent-driven-development` を使用。
2. **Inline Execution** — 本セッションで `superpowers:executing-plans` によりチェックポイント付きバッチ実行。

どちらで進めますか。
