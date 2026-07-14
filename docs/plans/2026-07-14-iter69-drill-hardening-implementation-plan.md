# B1 drill 強化（NO_RUN 拒否＋mutant 構文検証＋コメントラン floor 除外＋since baseline）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: `subagent-dev`（フレッシュ subagent per task・2段階レビュー）。Steps は checkbox（`- [ ]`）で追跡。

**Goal:** B1 drill の no-run PASS フォージ（R4）を封じ、コメント/docstring 孤立ハンク（罠 l）と committed-diff-empty（罠 f）による sanctioned skip 強制を解消する。

**Architecture:** 全変更を `scripts/run-test-strength-drill.py` に閉じる。(1) NO_RUN 拒否＝patterns.sh の `AEGIS_TEST_NO_RUN_FLAG_REGEX` を bash+grep subprocess で single-source 消費（evidence.sh と同一エンジン）、(2) mutant 構文検証＝適用前 pre-pass（.py→`compile()` builtin／.sh→`bash -n` stdin）、(3) coverage floor からコメント/空行/py docstring のみの連続ランを除外、(4) `.drill` spec の optional key `since` で diff baseline ref を指定（ancestor 検証＋report `since:` 行）。承認時経路（check_status.py::run_qa_drill 固定 argv）・judge（verdict のみ regex 抽出）・patterns.sh は無改修。

**参照設計:** docs/specs/2026-07-14-iter69-drill-hardening-design.md（brainstorm record: 同日 -brainstorm-record.md）

**Tech Stack:** python3 標準ライブラリのみ（ast/py builtin compile 追加）・bash/grep/git（既存前提）・unittest（tests/）

**モデル方針:** implementer subagent は `model:"opus"`（書く=opus）。レビュー/判定は親（fable）。

## Global Constraints

- 新機能に fail-open 分岐を作らない。唯一の緩和（floor 除外）は計算失敗時「除外しない＝厳格化」へ劣化。
- 新例外型を作らない（全て既存 `DrillError` に集約）。
- patterns.sh の regex は**変更しない**（single source。消費のみ）。
- `check_status.py`・`update-gate.sh`・`build-judge-card.py` は**変更しない**。
- 既存テスト（40件）は挙動不変で GREEN 維持（ピン更新は TestReport の 2 件のみ）。
- 各タスクの最後に per-task commit（コミットメッセージは各 Task の Step 参照）。

## 事前確認済みの事実（実装者向けコンテキスト）

1. **NO_RUN regex の正本**: `hooks/lib/patterns.sh:179` — `AEGIS_TEST_NO_RUN_FLAG_REGEX='(^|[[:space:]])(-{1,2}(version|help|collect-only|co|dry-run|no-run|fixtures|markers|listTests|list-tests|listFiles|listAllFiles)|-h)($|[[:space:]])'`。`[[:space:]]` POSIX クラスを含むため **Python `re` に直接食わせると文字集合として誤解釈され silent mis-match**。消費は bash+grep 経由のみ（evidence.sh:127-131 と同一エンジン）。
2. **patterns.sh の解決はスクリプト位置相対**: drill の `--root` は scratch clone/temp repo を指しうる（既存 E2E テストは全て patterns.sh の無い temp repo）。`Path(__file__).resolve().parent.parent / "hooks" / "lib" / "patterns.sh"` で framework install の正本を引く（update-task.sh の ROOT 解決と同型・install レイアウトは scripts/ と hooks/ が兄弟）。
3. **承認時経路は固定 argv**: `check_status.py:run_qa_drill` は runner を `--root/--spec/--report` のみで起動（`check_status.py:946-951`）。CLI flag は承認時に届かない → `since` は spec key。
4. **judge は report から `verdict:` のみ regex 抽出**（`build-judge-card.py:477` `re.search(r"verdict:\s*(\w+)", ...)`）→ `since:` 行の追加は安全。`verdict: SKIP` ブロック（check_status.py 生成）は不変。
5. **コメント行 mutant は必ず survived→FAIL**（コメントは挙動を持たない）→ floor 除外は「充足不可能な要求の削除」であり偽造面積を増やさない。混在ラン（コード行を含む）は `set(run) <= exempt` を満たさず floor 維持。
6. **既存 E2E の test_command は NO_RUN 非該当**（`grep -q ...`／`true`）— 実 regex 消費でも既存 E2E は GREEN 維持。
7. 既存ヘルパー再利用: `_contiguous_runs`（floor のラン分解）・`_replace_line` 相当のロジック（構文検証の mutant 全文構成は `text.split("\n")` コピーで行う）・`DrillError` catch → `DRILL BLOCKED (fail-closed)` 経路。
8. `.claude/skills/qa-verification/SKILL.md` はコンテキスト予算管理下 → 追記後 `python3 scripts/context_budget.py` で確認。
9. **report 内容をピンする他テストは無い**（grill-plan 裏取り済・2026-07-14）: `tests/test_check_status.py::TestQaDrillGate` は実 drill を承認時経路（`--pre-approve-gate qa`）で走らせるが、検証は rc と stdout キーワード（ドリル/スキップ）のみ・test_command は `true`/`grep -q ...` で NO_RUN 非該当＝本変更で非退行。report 機械ブロックのピンは `tests/test_test_strength_drill.py::TestReport` の 2 件だけ（Task 1 で更新）。
10. 本開発シェルに `pytest` 単体コマンドは無い（`python3 -m pytest` を使う）。E2E の collect-only テストは実装後は NO_RUN 拒否が実行前に発火するため pytest 実体に依存しない（実装前の挙動差は Step 1-2 のメッセージ照合コメント参照）。

## File Structure

- Modify: `scripts/run-test-strength-drill.py` — 新規関数 4 群＋`parse_spec`/`anti_gaming_violations`/`write_report`/`run_drill` 拡張
- Modify: `tests/test_test_strength_drill.py` — 新規テストクラス 5＋E2E 4＋ピン更新 2
- Modify: `.claude/skills/qa-verification/SKILL.md` — since key・NO_RUN 拒否・floor 除外の利用者向け記述

---

### Task 1: RED — 失敗するテストを先に書く

**Files:**
- Modify: `tests/test_test_strength_drill.py`

**Interfaces:**
- Produces: 後続タスクが GREEN 化する対象。関数名は `drill.check_no_run_command(cmd, patterns_lib=None)` / `drill.resolve_since_ref(root, since)` / `drill.syntax_check_mutants(root, mutants)` / `drill.non_coverable_lines(root, rel)` / `drill.anti_gaming_violations(added, mutants, coverage_files=None, exempt_lines=None)` / `drill.write_report(..., since="n/a")`。

- [ ] **Step 1-1: 新規テストクラス 5 つをファイル末尾（`if __name__` の前）に追加**

```python
class TestNoRunCommand(unittest.TestCase):
    """R4: no-run コマンド（--collect-only 等）の拒否。single source は
    patterns.sh（スクリプト位置相対）。patterns_lib 引数は fixture 注入口。
    実装は `grep -qE -e "$REGEX"`（`-e` で dash 始まり regex のオプション
    誤解釈を機構的に排除・マッチ意味論は evidence.sh:128 と同一）。"""

    def _lib(self, d, content):
        p = Path(d) / "patterns.sh"
        p.write_text(content, encoding="utf-8")
        return p

    def test_collect_only_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            lib = self._lib(d, "AEGIS_TEST_NO_RUN_FLAG_REGEX='collect-only'\n")
            with self.assertRaises(drill.DrillError):
                drill.check_no_run_command("pytest --collect-only -q",
                                           patterns_lib=lib)

    def test_clean_command_passes(self):
        with tempfile.TemporaryDirectory() as d:
            lib = self._lib(d, "AEGIS_TEST_NO_RUN_FLAG_REGEX='collect-only'\n")
            drill.check_no_run_command("pytest tests/ -q", patterns_lib=lib)

    def test_missing_lib_fail_closed(self):
        with self.assertRaises(drill.DrillError):
            drill.check_no_run_command(
                "pytest -q", patterns_lib=Path("/nonexistent/patterns.sh"))

    def test_unset_regex_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            lib = self._lib(d, "# regex not defined here\n")
            with self.assertRaises(drill.DrillError):
                drill.check_no_run_command("pytest -q", patterns_lib=lib)

    def test_real_patterns_rejects_collect_only(self):
        # single-source 消費の実証: 実 patterns.sh で R4 のフォージコマンドを拒否
        with self.assertRaises(drill.DrillError):
            drill.check_no_run_command("pytest --collect-only -q")

    def test_real_patterns_accepts_normal_pytest(self):
        drill.check_no_run_command("python3 -m pytest tests/test_x.py -q")


class TestSinceRef(unittest.TestCase):
    def _two_commits(self, root):
        _git_init(root)
        (root / "a.txt").write_text("1\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "c1")
        first = sp.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                       capture_output=True, text=True, check=True).stdout.strip()
        (root / "a.txt").write_text("1\n2\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "c2")
        return first

    def test_valid_ancestor_resolves_to_full_sha(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first = self._two_commits(root)
            self.assertEqual(drill.resolve_since_ref(root, first), first)

    def test_unknown_ref_raises(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._two_commits(root)
            with self.assertRaises(drill.DrillError):
                drill.resolve_since_ref(root, "no-such-ref-xyz")

    def test_non_ancestor_raises(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first = self._two_commits(root)
            _git(root, "checkout", "-q", "-b", "side", first)
            (root / "b.txt").write_text("side\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "side-commit")
            side = sp.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
            _git(root, "checkout", "-q", "-")
            with self.assertRaises(drill.DrillError):
                drill.resolve_since_ref(root, side)


class TestSyntaxCheckMutants(unittest.TestCase):
    def _mut(self, file, line, original, mutated):
        return {"file": file, "line": line,
                "original": original, "mutated": mutated}

    def test_python_syntax_broken_mutant_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("def f():\n    return 1\n",
                                       encoding="utf-8")
            with self.assertRaises(drill.DrillError):
                drill.syntax_check_mutants(
                    root, [self._mut("a.py", 2, "    return 1", "    return (")])

    def test_python_semantic_mutant_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("def f():\n    return 1\n",
                                       encoding="utf-8")
            drill.syntax_check_mutants(
                root, [self._mut("a.py", 2, "    return 1", "    return 2")])

    def test_bash_syntax_broken_mutant_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "x.sh").write_text("if true; then\n  echo hi\nfi\n",
                                       encoding="utf-8")
            with self.assertRaises(drill.DrillError):
                drill.syntax_check_mutants(
                    root, [self._mut("x.sh", 3, "fi", "f (")])

    def test_unknown_extension_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "n.txt").write_text("hello\n", encoding="utf-8")
            drill.syntax_check_mutants(
                root, [self._mut("n.txt", 1, "hello", "((broken((")])

    def test_unparseable_original_skipped(self):
        # 元ファイルが parse 不能 → 帰責不能として skip（baseline red が受ける）
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "bad.py").write_text("def (\n", encoding="utf-8")
            drill.syntax_check_mutants(
                root, [self._mut("bad.py", 1, "def (", "also broken (")])


class TestNonCoverableLines(unittest.TestCase):
    def test_blank_and_hash_comment_lines(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("x = 1\n\n# note\n  # indented\n",
                                       encoding="utf-8")
            got = drill.non_coverable_lines(root, "a.py")
            self.assertNotIn(1, got)
            self.assertTrue({2, 3, 4}.issubset(got))

    def test_js_line_comments(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.js").write_text("// c\nlet x = 1\n", encoding="utf-8")
            got = drill.non_coverable_lines(root, "a.js")
            self.assertIn(1, got)
            self.assertNotIn(2, got)

    def test_python_docstring_lines(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "m.py").write_text(
                '"""module doc\nsecond line\n"""\nx = 1\n', encoding="utf-8")
            got = drill.non_coverable_lines(root, "m.py")
            self.assertTrue({1, 2, 3}.issubset(got))
            self.assertNotIn(4, got)

    def test_parse_failure_no_docstring_exemption(self):
        # AST parse 失敗 → docstring 除外なし（厳格側劣化）。# 行は除外のまま。
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "b.py").write_text('def (\n"""not a docstring"""\n# c\n',
                                       encoding="utf-8")
            got = drill.non_coverable_lines(root, "b.py")
            self.assertNotIn(2, got)
            self.assertIn(3, got)

    def test_unreadable_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                drill.non_coverable_lines(Path(d), "missing.py"), set())

    def test_shebang_counts_as_comment(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "s.sh").write_text("#!/bin/bash\necho hi\n",
                                       encoding="utf-8")
            got = drill.non_coverable_lines(root, "s.sh")
            self.assertIn(1, got)
            self.assertNotIn(2, got)

    def test_crlf_lines_handled(self):
        # CRLF: strip() が \r を除去するため判定は LF と同一
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "w.py").write_text("x = 1\r\n\r\n# note\r\n",
                                       encoding="utf-8")
            got = drill.non_coverable_lines(root, "w.py")
            self.assertNotIn(1, got)
            self.assertTrue({2, 3}.issubset(got))


class TestFloorExemption(unittest.TestCase):
    def test_comment_only_run_exempted(self):
        added = {"src/a.py": {2, 3}}
        got = drill.anti_gaming_violations(
            added, [], exempt_lines={"src/a.py": {2, 3}})
        self.assertEqual(got, [])

    def test_mixed_run_keeps_floor(self):
        added = {"src/a.py": {2, 3}}
        got = drill.anti_gaming_violations(
            added, [], exempt_lines={"src/a.py": {2}})
        self.assertEqual(len(got), 1)
        self.assertIn("coverage floor", got[0])

    def test_none_exempt_is_previous_behavior(self):
        added = {"src/a.py": {2, 3}}
        got = drill.anti_gaming_violations(added, [], exempt_lines=None)
        self.assertEqual(len(got), 1)
```

- [ ] **Step 1-2: E2E テスト 4 件を `TestMainEndToEnd` 内に追加**

```python
    def test_collect_only_command_blocked_e2e(self):
        # R4 フォージ再現: no-run コマンドは実 patterns.sh 消費で BLOCKED
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "pytest --collect-only -q",
                "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 1)
            self.assertIn("DRILL BLOCKED", res.stdout)
            # 経路特定: baseline red/inconclusive でも rc=1+BLOCKED には到達する
            # ため、NO_RUN 拒否のメッセージ自体を要求する（RED の証明力を担保。
            # 実装前は pytest 不在環境でも inconclusive 経由で偶然 PASS しうる）
            self.assertIn("no-run フラグ", res.stdout)
            self.assertIn("verdict: FAIL", report.read_text())

    def test_since_mode_committed_change_pass(self):
        # 罠 f: per-task コミット済みで diff HEAD 空でも、since=反復基点で drill 成立
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            base = sp.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "task work")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "grep -q 'b = 2' src/m.py",
                "timeout_seconds": 10,
                "since": base,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            text = report.read_text()
            self.assertIn("verdict: PASS", text)
            self.assertIn(f"since: {base}", text)

    def test_since_non_ancestor_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            _git(root, "checkout", "-q", "-b", "side")
            (root / "side.txt").write_text("s\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "side")
            side = sp.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
            _git(root, "checkout", "-q", "-")
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "grep -q 'b = 2' src/m.py",
                "timeout_seconds": 10,
                "since": side,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 1)
            self.assertIn("DRILL BLOCKED", res.stdout)

    def test_comment_only_hunk_no_mutant_required_e2e(self):
        # 罠 l: 純コメントの孤立ハンクは floor を要求されない
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "m.py").write_text("a = 1\nmid = 0\nz = 9\n",
                                               encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "i")
            (root / "src" / "m.py").write_text(
                "a = 1\n# isolated note\nmid = 0\nz = 9\nb = 2\n",
                encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "grep -q 'b = 2' src/m.py",
                "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 5,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0,
                             f"comment-only hunk must not demand a mutant: "
                             f"{res.stdout}{res.stderr}")
            self.assertIn("verdict: PASS", report.read_text())
```

- [ ] **Step 1-3: parse_spec の since 検証テストを `TestParseSpec` に追加**

```python
    def test_since_optional_and_validated(self):
        with tempfile.TemporaryDirectory() as d:
            spec = drill.parse_spec(self._write(d, since="abc123"))
            self.assertEqual(spec["since"], "abc123")

    def test_since_empty_string_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(self._write(d, since="   "))

    def test_since_non_string_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(self._write(d, since=123))
```

- [ ] **Step 1-4: TestReport の 2 ピンを since 行込みへ更新**

```python
    def test_pass_report_shape(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.md"
            drill.write_report(out, verdict="PASS", total=2, caught=2,
                               baseline="green", survived=[], since="HEAD")
            text = out.read_text()
            self.assertIn("verdict: PASS", text)
            self.assertIn("mutants_total: 2", text)
            self.assertIn("survived: []", text)
            self.assertIn("since: HEAD", text)

    def test_fail_report_lists_survivors(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.md"
            drill.write_report(out, verdict="FAIL", total=2, caught=1,
                               baseline="green", survived=["src/a.py:3"])
            text = out.read_text()
            self.assertIn("verdict: FAIL", text)
            self.assertIn("src/a.py:3", text)
            self.assertIn("since: n/a", text)  # 省略時デフォルト
```

- [ ] **Step 1-5: RED を確認**

Run: `python3 -m pytest tests/test_test_strength_drill.py -q`
Expected: 新規/更新 33 件中 **32 FAIL・1 PASS**。PASS するのは `test_since_optional_and_validated` のみ（現 parse_spec は未知キーを素通しするため実装前から通る＝後方互換のピン。意図的に残す）。FAIL の内訳: 新規関数群の `AttributeError`／`write_report` の `TypeError`（since キーワード）または `since: n/a` 不在／since 検証・NO_RUN メッセージ・floor 除外・E2E の未実装挙動。既存 40 件は PASS 維持（TestReport の旧版 2 件は更新済みのため FAIL 側に計上）。

- [ ] **Step 1-6: Commit**

```bash
git add tests/test_test_strength_drill.py
git commit -m "test(iter69): RED — drill 強化4点（NO_RUN 拒否/since/構文検証/floor 除外）の失敗テストを先置き"
```

---

### Task 2: GREEN(1/4) — NO_RUN 拒否

**Files:**
- Modify: `scripts/run-test-strength-drill.py`

**Interfaces:**
- Produces: `check_no_run_command(cmd: str, patterns_lib: Path | None = None) -> None`（違反・検査不能は DrillError）。`FRAMEWORK_ROOT`／`PATTERNS_LIB` モジュール定数。
- Consumes: Task 1 のテスト。

- [ ] **Step 2-1: モジュール定数と関数を追加**（`EMPTY_TREE` 定義の直後あたり）

```python
# R4 (full-review 2026-07-06): evidence.sh は no-run コマンド（--collect-only /
# --dry-run 等）を AEGIS_TEST_NO_RUN_FLAG_REGEX で拒否するが、drill 側が未消費
# だった — collect-only ＋構文破壊 mutant で「1件もテストを実行しない DRILL
# PASS」が成立していた。同じ regex を同じエンジン（bash grep -E）で消費する:
# regex は [[:space:]] POSIX クラスを含み、python re に直接食わせると文字集合
# として誤解釈され silent mis-match になる。
# patterns.sh は --root でなく本スクリプト位置相対で解決する: --root は
# patterns.sh を持たない scratch clone / temp repo を指しうる（root 相対だと
# 全 drill block か fail-open の二択になる）。framework install では scripts/
# と hooks/ が兄弟（update-task.sh の ROOT 解決と同型）。
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_LIB = FRAMEWORK_ROOT / "hooks" / "lib" / "patterns.sh"


def check_no_run_command(cmd: str, patterns_lib: Path | None = None) -> None:
    """Reject a test_command matching AEGIS_TEST_NO_RUN_FLAG_REGEX (single
    source: patterns.sh). Any condition that prevents the check — missing
    patterns.sh, unset regex, grep/subprocess failure — is fail-closed."""
    lib = Path(patterns_lib) if patterns_lib is not None else PATTERNS_LIB
    if not lib.is_file():
        raise DrillError(
            f"patterns.sh not found: {lib} — NO_RUN 検査を実行できないため "
            f"fail-closed（framework install が壊れています）")
    # grep -e: dash 始まり regex がオプションと誤解釈される余地を機構的に排除
    # （マッチ意味論は evidence.sh:128 の grep -qE と同一）
    script = ('source "$1" >/dev/null 2>&1 || exit 3; '
              '[ -n "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] || exit 3; '
              'printf %s "$2" | grep -qE -e "$AEGIS_TEST_NO_RUN_FLAG_REGEX"')
    try:
        proc = subprocess.run(
            ["bash", "-c", script, "_", str(lib), cmd],
            capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DrillError(f"NO_RUN 検査の実行に失敗（fail-closed）: {exc}")
    if proc.returncode == 0:
        raise DrillError(
            "test_command が no-run フラグ（--collect-only / --dry-run / "
            "--version 等）を含みます — テストを1件も実行しないコマンドは"
            "テスト強度を証明しません")
    if proc.returncode != 1:
        raise DrillError(
            f"NO_RUN regex を patterns.sh から読み込めません "
            f"(rc={proc.returncode}) — fail-closed")
```

- [ ] **Step 2-2: run_drill へ配線**（`cmd`/`timeout` 取得直後・transparency print の前）

```python
        cmd = spec["test_command"]
        timeout = int(spec["timeout_seconds"])
        check_no_run_command(cmd)
        # transparency: surface what will actually be executed at approval time
        print(f"test command (executed at approval): {cmd}")
```

- [ ] **Step 2-3: 対象テスト GREEN を確認**

Run: `python3 -m pytest tests/test_test_strength_drill.py -q -k "NoRun or collect_only"`
Expected: TestNoRunCommand 6 件＋test_collect_only_command_blocked_e2e が PASS。

- [ ] **Step 2-4: 既存 E2E の非退行を確認**

Run: `python3 -m pytest tests/test_test_strength_drill.py -q -k "TestMainEndToEnd"`
Expected: 既存 E2E は PASS 維持（since/コメント系の新規のみ FAIL 残）。

- [ ] **Step 2-5: Commit**

```bash
git add scripts/run-test-strength-drill.py
git commit -m "feat(iter69): drill が NO_RUN regex を single-source 消費 — no-run コマンドの偽 PASS を封鎖（R4）"
```

---

### Task 3: GREEN(2/4) — mutant 構文検証

**Files:**
- Modify: `scripts/run-test-strength-drill.py`

**Interfaces:**
- Produces: `syntax_check_mutants(root: Path, mutants: list[dict]) -> None`（構文破壊 mutant を全件列挙して DrillError）。内部ヘルパー `_parses(rel, text) -> bool | None`。
- Consumes: Task 1 のテスト。

- [ ] **Step 3-1: 関数を追加**（`check_no_run_command` の直後）

```python
_SYNTAX_CHECKED_SUFFIXES = (".py", ".sh", ".bash")


def _parses(rel: str, text: str) -> bool | None:
    """Parse verdict for the file type: True/False, or None when no checker
    exists for this extension (unknown types are not judged)."""
    suffix = Path(rel).suffix
    if suffix == ".py":
        try:
            compile(text, rel, "exec")
            return True
        except (SyntaxError, ValueError):
            return False
    if suffix in (".sh", ".bash"):
        try:
            proc = subprocess.run(["bash", "-n"], input=text.encode("utf-8"),
                                  capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return proc.returncode == 0
    return None


def syntax_check_mutants(root: Path, mutants: list[dict]) -> None:
    """R4 併発: 構文破壊 mutant は「テストが assert で捕まえた」ことを証明しない
    （import/収集エラーでも red になる）。適用前 pre-pass で mutant 適用後の全文
    が構文検査（.py→compile() builtin／.sh→bash -n）を通ることを要求する。
    元ファイルが parse 不能なファイルは帰責不能として skip（baseline red が別途
    受け止める）。ファイル不在・行範囲外・original 不一致も skip — それらは
    apply_mutant の既存エラー経路が正本（メッセージを二重化しない）。"""
    broken: list[str] = []
    originals: dict[str, str | None] = {}
    for m in mutants:
        rel = m["file"]
        if Path(rel).suffix not in _SYNTAX_CHECKED_SUFFIXES:
            continue
        if rel not in originals:
            try:
                text = (root / rel).read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                originals[rel] = None
            else:
                originals[rel] = text if _parses(rel, text) else None
        text = originals[rel]
        if text is None:
            continue
        line_no = int(m["line"])
        parts = text.split("\n")
        if line_no < 1 or line_no > len(parts):
            continue
        if parts[line_no - 1] != m["original"]:
            continue
        mutated = parts.copy()
        mutated[line_no - 1] = m["mutated"]
        if _parses(rel, "\n".join(mutated)) is False:
            broken.append(f"{rel}:{line_no}")
    if broken:
        raise DrillError(
            "構文破壊 mutant は assert の強さを証明しません（parse エラーでも"
            "テストは red になるため）。意味を変え構文を保つ mutant に"
            "書き換えてください: " + ", ".join(broken))
```

- [ ] **Step 3-2: run_drill へ配線**（反ガミング判定ブロックの直後・baseline の前）

```python
        syntax_check_mutants(root, spec["mutants"])

        base, base_output = check_baseline(cmd, root, timeout)
```

- [ ] **Step 3-3: 対象テスト GREEN＋既存非退行を確認**

Run: `python3 -m pytest tests/test_test_strength_drill.py -q -k "SyntaxCheck or TestApplyMutant or TestMainEndToEnd"`
Expected: TestSyntaxCheckMutants 5 件 PASS。既存 PASS 維持（since/コメント系のみ FAIL 残）。
※ 既存 E2E の mutant（`b = 2`→`b = 3` 等）は構文保存のため素通り。

- [ ] **Step 3-4: Commit**

```bash
git add scripts/run-test-strength-drill.py
git commit -m "feat(iter69): mutant 構文検証 pre-pass — 構文破壊 mutant を spec エラー化（R4 併発）"
```

---

### Task 4: GREEN(3/4) — コメント/docstring ラン floor 除外

**Files:**
- Modify: `scripts/run-test-strength-drill.py`

**Interfaces:**
- Produces: `non_coverable_lines(root: Path, rel: str) -> set[int]`／`_docstring_lines(text: str) -> set[int]`／`LINE_COMMENT_TOKENS`。`anti_gaming_violations(..., exempt_lines: dict[str, set[int]] | None = None)`（None=従来挙動）。
- Consumes: Task 1 のテスト。既存 `_contiguous_runs`。

- [ ] **Step 4-1: `import ast` を追加**（既存 import 群の先頭・アルファベット順で `import json` の前）

```python
import ast
```

- [ ] **Step 4-2: 除外行計算の関数群を追加**（`_contiguous_runs` の直後）

```python
# 罠 l (full-review R6 / LEARNINGS:136): コメント/空行/docstring だけの連続ラン
# には behavior-catching mutant を置けない（そこに置いた mutant は必ず
# survived→FAIL）。floor がそれを要求すると sanctioned skip 強制になるため
# 除外する。除外は「充足不可能な要求の削除」のみ: コード行を含む混在ランは
# subset 判定を満たさず floor 維持＝偽造面積は増えない。
# 実需（LEARNINGS の実痛点）は py/sh。js 系トークンは配布先ユーザープロジェクト
# （feature/refactor タスク）向けの安価な拡張。
LINE_COMMENT_TOKENS = {
    ".py": "#", ".sh": "#", ".bash": "#",
    ".js": "//", ".ts": "//", ".jsx": "//", ".tsx": "//",
    ".mjs": "//", ".cjs": "//",
}


def _docstring_lines(text: str) -> set[int]:
    """Module/class/function docstring line ranges via AST. A file that does
    not parse yields the empty set — no exemption (stricter = safe)."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                    and body[0].end_lineno is not None):
                lines.update(range(body[0].lineno, body[0].end_lineno + 1))
    return lines


def non_coverable_lines(root: Path, rel: str) -> set[int]:
    """Lines of the on-disk file that cannot host a catchable mutant: blank
    lines, line comments (by extension; shebang included), and python
    docstrings. Read/decode failures degrade to 'no exemption'."""
    try:
        text = (root / rel).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    token = LINE_COMMENT_TOKENS.get(Path(rel).suffix)
    exempt: set[int] = set()
    for i, raw in enumerate(text.split("\n"), 1):
        stripped = raw.strip()
        if not stripped or (token and stripped.startswith(token)):
            exempt.add(i)
    if Path(rel).suffix == ".py":
        exempt |= _docstring_lines(text)
    return exempt
```

- [ ] **Step 4-3: `anti_gaming_violations` に `exempt_lines` を追加**（floor ループのみ変更・検査 (a) は不変）

```python
def anti_gaming_violations(
    added_by_file: dict[str, set[int]],
    mutants: list[dict],
    coverage_files: set[str] | None = None,
    exempt_lines: dict[str, set[int]] | None = None,
) -> list[str]:
```

floor ループ（`for f, lines in added_by_file.items():` 内）:

```python
    for f, lines in added_by_file.items():
        if coverage_files is not None and f not in coverage_files:
            continue  # untouched untracked/noise file: do not force coverage
        exempt = (exempt_lines or {}).get(f, set())
        for run in _contiguous_runs(sorted(lines)):
            if set(run) <= exempt:
                continue  # comment/blank/docstring-only run: no catchable mutant
            if not (mutant_lines.get(f, set()) & set(run)):
                violations.append(
                    f"{f}: added lines {run[0]}-{run[-1]} have no mutant "
                    f"(coverage floor: every changed hunk needs one)")
    return violations
```

docstring の `(b)` 説明文にも一文追記: `Runs made solely of blank/comment/docstring lines (see exempt_lines) are exempt — they cannot host a catchable mutant.`

- [ ] **Step 4-4: run_drill へ配線**（`coverage_files` 計算の直後・`ag = ...` を置換）

```python
        coverage_files = tracked | (mutant_files & set(added))
        # 罠 l: コメント/空行/docstring だけのランは floor 免除（透明化のため
        # 免除ランを承認ログに明示する）
        exempt = {f: non_coverable_lines(root, f) for f in coverage_files}
        for f in sorted(coverage_files & set(added)):
            for run in _contiguous_runs(sorted(added[f])):
                if set(run) <= exempt.get(f, set()):
                    print(f"coverage floor exempt (comment/blank/docstring "
                          f"only): {f}:{run[0]}-{run[-1]}")
        ag = anti_gaming_violations(added, spec["mutants"],
                                    coverage_files=coverage_files,
                                    exempt_lines=exempt)
```

- [ ] **Step 4-5: 対象テスト GREEN＋既存非退行を確認**

Run: `python3 -m pytest tests/test_test_strength_drill.py -q -k "NonCoverable or FloorExemption or TestAntiGaming or comment_only"`
Expected: 新規 9 件＋test_comment_only_hunk_no_mutant_required_e2e PASS。TestAntiGaming 既存 3 件 PASS 維持。

- [ ] **Step 4-6: Commit**

```bash
git add scripts/run-test-strength-drill.py
git commit -m "feat(iter69): coverage floor からコメント/空行/docstring のみのランを除外 — 不可能要求の削除（罠 l）"
```

---

### Task 5: GREEN(4/4) — since baseline モード＋report `since:` 行

**Files:**
- Modify: `scripts/run-test-strength-drill.py`

**Interfaces:**
- Produces: `.drill` spec optional key `since`／`resolve_since_ref(root: Path, since: str) -> str`（フル sha 返却）／`write_report(..., since: str = "n/a")`（機械ブロック `since:` 行）。
- Consumes: Task 1 のテスト。既存 `resolve_diff_ref`。

- [ ] **Step 5-1: parse_spec に since 検証を追加**（timeout 検証の直後）

```python
    # 罠 f (full-review R6 / LEARNINGS:76): per-task コミット運用では diff HEAD
    # が空になり drill 不成立。optional 'since' で反復基点 ref への diff に
    # 切り替える（committed-this-iteration を追加扱い）。CLI flag でなく spec
    # key なのは、承認時経路 (check_status.py::run_qa_drill) が固定 argv で
    # runner を起動するため — spec なら preview と承認が自動一致し、基点 ref
    # が監査可能な証拠ファイルに残る。
    if "since" in data:
        if not isinstance(data["since"], str) or not data["since"].strip():
            raise DrillError("'since' must be a non-empty string when present")
```

- [ ] **Step 5-2: resolve_since_ref を追加**（`resolve_diff_ref` の直後）

```python
def resolve_since_ref(root: Path, since: str) -> str:
    """Validate the spec's 'since' baseline and return its full sha. The ref
    must resolve to a commit AND be an ancestor of HEAD: a non-ancestor ref
    would define a diff no reviewer can audit from the report alone.
    Fail-closed on any git failure."""
    try:
        rp = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "-q",
             f"{since}^{{commit}}"],
            capture_output=True, text=True)
    except OSError as exc:
        raise DrillError(f"git rev-parse failed: {exc}")
    sha = rp.stdout.strip()
    if rp.returncode != 0 or not sha:
        raise DrillError(f"spec 'since' が commit に解決できません: {since}")
    try:
        anc = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor",
             sha, "HEAD"],
            capture_output=True, text=True)
    except OSError as exc:
        raise DrillError(f"git merge-base failed: {exc}")
    if anc.returncode != 0:
        raise DrillError(
            f"spec 'since' は HEAD の祖先ではありません: {since} — "
            f"監査不能な diff 基点は拒否します")
    return sha
```

- [ ] **Step 5-3: write_report に since 行を追加**

```python
def write_report(report_path: Path, *, verdict: str, total: int, caught: int,
                 baseline: str, survived: list[str], since: str = "n/a") -> None:
```

本文の `baseline` 行の直後に:

```python
        f"baseline: {baseline}\n"
        f"since: {since}\n"
        f"survived: {survived_repr}\n"
```

- [ ] **Step 5-4: run_drill の ref 決定と write_report 4 箇所を配線**

関数冒頭（try の前）に `since_label = "n/a"` を置き、ref 決定を置換:

```python
def run_drill(root: Path, spec_path: Path, report_path: Path) -> int:
    """Orchestrate. Returns 0 (PASS) or 1 (FAIL/inconclusive). Never raises:
    every DrillError becomes a fail-closed verdict + non-zero exit."""
    since_label = "n/a"
    try:
        ...
        if "since" in spec:
            ref = resolve_since_ref(root, spec["since"].strip())
        else:
            ref = resolve_diff_ref(root)  # 'HEAD', or empty-tree when no commits
        since_label = ref
        # transparency: the report records which baseline defined "added lines"
        print(f"diff baseline (since): {since_label}")
        tracked_map = _tracked_added_lines(root, ref)
        ...
```

write_report の全 4 呼び出し（反ガミング FAIL／baseline FAIL／最終／DrillError catch）に `since=since_label` を追加。例（最終）:

```python
        write_report(report_path, verdict=verdict, total=len(spec["mutants"]),
                     caught=caught, baseline="green", survived=survived,
                     since=since_label)
```

DrillError catch 内:

```python
            write_report(report_path, verdict="FAIL", total=0, caught=0,
                         baseline="inconclusive", survived=[],
                         since=since_label)
```

- [ ] **Step 5-5: 全テスト GREEN を確認**

Run: `python3 -m pytest tests/test_test_strength_drill.py tests/test_drill_quotepath.py -q`
Expected: 全件 PASS（新規＋既存＋ピン更新）。

- [ ] **Step 5-6: full suite**

Run: `python3 -m pytest tests/ -q`
Expected: 全件 PASS（既知 flaky: test_update_gate_lock は回帰外）。

- [ ] **Step 5-7: Commit**

```bash
git add scripts/run-test-strength-drill.py
git commit -m "feat(iter69): .drill spec key 'since' — 反復基点 diff モード（ancestor 検証＋report since: 行で透明化・罠 f）"
```

---

### Task 6: guidance 同期（qa-verification SKILL.md）＋full suite

**Files:**
- Modify: `.claude/skills/qa-verification/SKILL.md`

**Interfaces:**
- Consumes: Task 2-5 の実装済み挙動。

- [ ] **Step 6-1: spec 例へ since を追記**（`.drill` JSON 例のセクション・「シェル機能は使えない」の箇条書きに続けて）

```markdown
   - `test_command` に no-run フラグ（`--collect-only` / `--dry-run` /
     `--version` 等）は使えない（patterns.sh の NO_RUN regex で承認時に拒否）。
   - mutant は**構文を保って意味を変える**こと（構文破壊 mutant は
     `.py`→compile / `.sh`→`bash -n` の事前検査で spec エラーになる）。
   - タスク単位でコミット済みの反復は、optional key `"since": "<反復基点の
     コミット sha>"` を足すと基点以降の committed 変更が drill 対象になる
     （基点は HEAD の祖先必須・report の `since:` 行に記録される）。
   - コメント/空行/docstring だけの変更ハンクは coverage floor から自動除外
     される（mutant 配置不要・承認ログに除外ランが明示される）。
```

- [ ] **Step 6-2: skip 宣言セクションの誘導を更新** — 「テスト対象コードが無いタスク（スキップ宣言）」セクションの導入文（「mutant を作れないタスク…」の段落）の直前に、次の段落をこのまま挿入する:

```markdown
> **コミット済みで diff が空になっただけのタスクは skip でなく `"since"` を使う**
> （反復基点のコミット sha を指定）。skip は「テスト対象コード自体が無い」
> 場合（ドキュメント・設定・文言のみの変更）に限る。
```

- [ ] **Step 6-3: コンテキスト予算を確認**

Run: `python3 scripts/context_budget.py`
Expected: PASS（超過時は追記を圧縮して再実行）。

- [ ] **Step 6-4: full suite＋contract**

Run: `python3 -m pytest tests/ -q && python3 scripts/check_framework_contract.py`
Expected: 全件 PASS・contract aligned。

- [ ] **Step 6-5: Commit**

```bash
git add .claude/skills/qa-verification/SKILL.md
git commit -m "docs(iter69): qa-verification skill に since/NO_RUN 拒否/構文検証/floor 除外の利用手順を同期"
```

---

## 受入条件（サマリ）

1. `pytest --collect-only -q` を test_command に持つ spec は実 patterns.sh 消費で DRILL BLOCKED（R4 封鎖・E2E 実証）。
2. 構文破壊 mutant（py/sh）は baseline 実行前に spec エラーとして全件列挙 BLOCKED。構文保存 mutant・未知拡張子・parse 不能な元ファイルは素通り。
3. コメント/空行/py docstring **のみ**の連続ランは floor 免除（混在ランは維持・免除ランは承認ログに明示）。`exempt_lines=None` は従来挙動。
4. spec key `since` で反復基点 diff が成立（committed 変更が追加扱い・非 ancestor / 不明 ref は BLOCKED・report に `since:` 行）。省略時の挙動は完全不変。
5. 全 pre-check は fail-closed（新 fail-open 分岐ゼロ・新例外型ゼロ）。
6. full suite GREEN・contract aligned・qa-verification SKILL.md 同期・context budget PASS。
