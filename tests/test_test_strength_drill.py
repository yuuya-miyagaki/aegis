"""Unit tests for the B1 test-strength drill runner.

Test commands are deliberately shell-free (single binaries / helper scripts)
because the runner executes them with shell=False (grill fix: no shell vector).
"""
import importlib.util
import json
import subprocess as sp
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


def _git(root, *args):
    sp.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _git_init(root):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")


def _write_probe_test(root: Path, needle: str, target: str) -> str:
    """grep -q ダミーの実ランナー置換（iter71: baseline は positive proof 必須）。
    必ず git add/commit の後に呼ぶ（untracked＝coverage floor 非対象を保つ）。"""
    (root / "t_probe.py").write_text(
        "import unittest, pathlib\n"
        "class T(unittest.TestCase):\n"
        "    def test_probe(self):\n"
        f"        self.assertIn({needle!r}, "
        f"pathlib.Path({target!r}).read_text())\n", encoding="utf-8")
    return "python3 -m unittest t_probe"


class TestParseSpec(unittest.TestCase):
    def _write(self, d, **over):
        base = {
            "test_command": "true", "timeout_seconds": 30,
            "mutants": [{"file": "src/a.py", "line": 3,
                         "original": "    return a >= b",
                         "mutated": "    return a > b"}],
        }
        base.update(over)
        p = Path(d) / "x.drill"
        p.write_text(json.dumps(base), encoding="utf-8")
        return p

    def test_valid_spec_parses(self):
        with tempfile.TemporaryDirectory() as d:
            spec = drill.parse_spec(self._write(d))
            self.assertEqual(spec["test_command"], "true")
            self.assertEqual(len(spec["mutants"]), 1)

    def test_missing_file_raises(self):
        with self.assertRaises(drill.DrillError):
            drill.parse_spec(Path("/nonexistent/x.drill"))

    def test_malformed_json_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.drill"
            p.write_text("{not json", encoding="utf-8")
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(p)

    def test_missing_key_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.drill"
            p.write_text(json.dumps({"mutants": []}), encoding="utf-8")
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(p)

    def test_too_many_mutants_raises(self):
        with tempfile.TemporaryDirectory() as d:
            many = [{"file": "a", "line": 1, "original": "x", "mutated": "y"}
                    for _ in range(drill.MAX_MUTANTS + 1)]
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(self._write(d, mutants=many))

    def test_non_int_timeout_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(self._write(d, timeout_seconds="abc"))

    def test_non_int_mutant_line_raises(self):
        with tempfile.TemporaryDirectory() as d:
            bad = [{"file": "a", "line": "two", "original": "x", "mutated": "y"}]
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(self._write(d, mutants=bad))

    def test_empty_test_command_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(drill.DrillError):
                drill.parse_spec(self._write(d, test_command="   "))

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


class TestAddedLines(unittest.TestCase):
    def test_tracked_added_lines(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "init")
            (root / "src" / "a.py").write_text("x = 1\ny = 2\nz = 3\n", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertEqual(added.get("src/a.py"), {2, 3})

    def test_untracked_new_file_all_lines_added(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "init")
            (root / "src").mkdir()
            (root / "src" / "new.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertEqual(added.get("src/new.py"), {1, 2})

    def test_drill_artifacts_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "init")
            qa = root / "docs" / "qa-reports"
            qa.mkdir(parents=True)
            (qa / "test-strength.drill").write_text("{}", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertNotIn("docs/qa-reports/test-strength.drill", added)

    def test_docs_hunks_excluded_from_added_lines(self):
        # B1 恒久修正: docs/ 配下の簿記ファイルは mutant 対象に入らない。
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "init")
            docs = root / "docs"
            docs.mkdir()
            (docs / "STATUS.md").write_text("phase: implement\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "x.py").write_text("a = 1\n", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertNotIn("docs/STATUS.md", added)
            self.assertIn("src/x.py", added)

    def test_no_changes_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "init")
            self.assertEqual(drill.added_lines_by_file(root, "HEAD"), {})


class TestAntiGaming(unittest.TestCase):
    def test_mutant_outside_added_rejected(self):
        v = drill.anti_gaming_violations(
            {"src/a.py": {3, 4}},
            [{"file": "src/a.py", "line": 9, "original": "x", "mutated": "y"}])
        self.assertTrue(any("not an added" in m for m in v))

    def test_uncovered_hunk_rejected(self):
        v = drill.anti_gaming_violations(
            {"src/a.py": {3, 4, 7}},
            [{"file": "src/a.py", "line": 3, "original": "x", "mutated": "y"}])
        self.assertTrue(any("coverage floor" in m for m in v))

    def test_all_runs_covered(self):
        v = drill.anti_gaming_violations({"src/a.py": {3, 4, 7}}, [
            {"file": "src/a.py", "line": 3, "original": "x", "mutated": "y"},
            {"file": "src/a.py", "line": 7, "original": "p", "mutated": "q"}])
        self.assertEqual(v, [])


class TestRunTest(unittest.TestCase):
    def test_green(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("true", Path(d), 10), "passed")

    def test_red(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("false", Path(d), 10), "failed")

    def test_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("sleep 5", Path(d), 1), "timeout")

    def test_missing_cmd(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("definitely-not-a-cmd-xyz", Path(d), 10), "error")

    def test_bad_quoting_is_error(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.run_test("echo 'unterminated", Path(d), 10), "error")


class TestBaseline(unittest.TestCase):
    def _flaky_cmd(self, root):
        # helper script: passes the first time, fails the second (flag file)
        (root / "flaky.py").write_text(
            "import os, sys\n"
            "f = 'flag'\n"
            "sys.exit(1 if os.path.exists(f) else (open(f, 'w').close() or 0))\n",
            encoding="utf-8")
        return "python3 flaky.py"

    def test_green_without_marker_is_no_test_proof(self):
        # D2 (iter71): `true` passes twice but runs ZERO tests. Post-iter71 the
        # baseline requires a positive marker proof, so a non-runner green is
        # reported as "no-test-proof" (BLOCKED), not "green". RED until Task 3.
        with tempfile.TemporaryDirectory() as d:
            status, _ = drill.check_baseline("true", Path(d), 10)
            self.assertEqual(status, "no-test-proof")

    def test_real_runner_green(self):
        # D3 (both-green): a real unittest runner that actually runs a test and
        # passes twice yields a green baseline — the positive-proof path. This
        # stays green under the current exit-code baseline too.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "t_ok.py").write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n", encoding="utf-8")
            status, _ = drill.check_baseline(
                "python3 -m unittest t_ok", root, 30)
            self.assertEqual(status, "green")

    def test_red_surfaces_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "fail.py").write_text(
                "import sys\nprint('boom-marker')\nsys.exit(1)\n", encoding="utf-8")
            status, output = drill.check_baseline("python3 fail.py", root, 10)
            self.assertEqual(status, "red")
            self.assertIn("boom-marker", output)

    def test_flaky(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            status, _ = drill.check_baseline(self._flaky_cmd(root), root, 10)
            self.assertEqual(status, "flaky")


class TestApplyMutant(unittest.TestCase):
    def _mk(self, d):
        root = Path(d)
        (root / "src").mkdir()
        (root / "src" / "m.py").write_text(
            "def f(a, b):\n    return a >= b\n", encoding="utf-8")
        return root

    def test_caught(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            m = {"file": "src/m.py", "line": 2,
                 "original": "    return a >= b", "mutated": "    return a > b"}
            r = drill.apply_mutant_and_test(root, m, "grep -q 'return a >= b' src/m.py", 10)
            self.assertEqual(r, "caught")
            self.assertEqual((root / "src" / "m.py").read_text(),
                             "def f(a, b):\n    return a >= b\n")

    def test_survived(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            m = {"file": "src/m.py", "line": 2,
                 "original": "    return a >= b", "mutated": "    return a > b"}
            r = drill.apply_mutant_and_test(root, m, "true", 10)
            self.assertEqual(r, "survived")
            self.assertEqual((root / "src" / "m.py").read_text(),
                             "def f(a, b):\n    return a >= b\n")

    def test_line_mismatch_aborts_without_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            m = {"file": "src/m.py", "line": 2,
                 "original": "    return a <= b", "mutated": "    return a < b"}
            with self.assertRaises(drill.DrillError):
                drill.apply_mutant_and_test(root, m, "true", 10)
            self.assertEqual((root / "src" / "m.py").read_text(),
                             "def f(a, b):\n    return a >= b\n")

    def test_concurrent_edit_preserved_not_clobbered(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._mk(d)
            sentinel = "USER EDIT DURING DRILL\n"
            (root / "evil.txt").write_text(sentinel, encoding="utf-8")
            m = {"file": "src/m.py", "line": 2,
                 "original": "    return a >= b", "mutated": "    return a > b"}
            with self.assertRaises(drill.ConcurrentEditError):
                drill.apply_mutant_and_test(root, m, "cp evil.txt src/m.py", 10)
            self.assertEqual((root / "src" / "m.py").read_text(), sentinel)


class TestReport(unittest.TestCase):
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


class TestMainEndToEnd(unittest.TestCase):
    def _run(self, root, spec_path, report_path):
        return sp.run(
            ["python3", str(SCRIPT), "--root", str(root),
             "--spec", str(spec_path), "--report", str(report_path)],
            capture_output=True, text=True)

    def _commit_seed(self, root):
        (root / "src").mkdir()
        (root / "src" / "m.py").write_text("a = 1\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "i")

    def test_pass_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            cmd = _write_probe_test(root, "b = 2", "src/m.py")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": cmd,
                "timeout_seconds": 30,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("verdict: PASS", report.read_text())

    def test_new_untracked_file_pass_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "i")
            (root / "src").mkdir()
            (root / "src" / "n.py").write_text("v = 7\n", encoding="utf-8")  # untracked
            cmd = _write_probe_test(root, "v = 7", "src/n.py")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": cmd,
                "timeout_seconds": 30,
                "mutants": [{"file": "src/n.py", "line": 1,
                             "original": "v = 7", "mutated": "v = 8"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("verdict: PASS", report.read_text())

    def test_docs_tracked_changes_excluded_from_coverage_floor(self):
        # B1 恒久修正: docs/ の tracked 簿記ハンクは coverage floor に
        # 「mutant を要求するハンク」として現れない（framework 混在 diff 対策）。
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "m.py").write_text("a = 1\n", encoding="utf-8")
            docs = root / "docs"
            docs.mkdir()
            (docs / "LEARNINGS.md").write_text("# L\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "i")
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            (docs / "LEARNINGS.md").write_text("# L\n- note\n", encoding="utf-8")
            cmd = _write_probe_test(root, "b = 2", "src/m.py")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": cmd,
                "timeout_seconds": 30,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0,
                             f"docs hunk must not demand a mutant: {res.stdout}{res.stderr}")
            self.assertIn("verdict: PASS", report.read_text())

    def test_survived_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            # blind runner: a real test that passes but never touches src/m.py,
            # so the baseline is green (positive proof) yet the mutant survives
            # => FAIL. (Was "true", which post-iter71 is baseline no-test-proof
            # and would BLOCK before reaching the survive check — masking the
            # "surviving mutant => FAIL" invariant.)
            (root / "t_blind.py").write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    def test_blind(self):\n"
                "        self.assertTrue(True)\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "python3 -m unittest t_blind",  # blind => survives
                "timeout_seconds": 30,
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
            _git_init(root)
            res = self._run(root, root / "nope.drill", root / "r.md")
            self.assertEqual(res.returncode, 1)

    def test_no_commit_repo_pass_exit0(self):
        # git init but NO commit yet (no HEAD): must fall back to empty-tree diff
        # and still drill the new code, not crash.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "m.py").write_text("v = 7\n", encoding="utf-8")
            _git(root, "add", "-A")  # staged, but never committed
            # probe written AFTER `git add -A` so it stays untracked: with no
            # HEAD the diff is against the empty tree, so a staged/tracked probe
            # would itself become a coverage-floor target and BLOCK the drill.
            cmd = _write_probe_test(root, "v = 7", "src/m.py")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": cmd,
                "timeout_seconds": 30,
                "mutants": [{"file": "src/m.py", "line": 1,
                             "original": "v = 7", "mutated": "v = 8"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("verdict: PASS", report.read_text())

    def test_not_a_git_repo_blocks_with_guidance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)  # NOT a git repo
            (root / "m.py").write_text("v = 7\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                # baseline 到達前に not-a-git-repo で BLOCK するため移行不要（iter71）
                "test_command": "true", "timeout_seconds": 10,
                "mutants": [{"file": "m.py", "line": 1,
                             "original": "v = 7", "mutated": "v = 8"}],
            }), encoding="utf-8")
            res = self._run(root, spec, root / "r.md")
            self.assertEqual(res.returncode, 1)
            self.assertIn("git", res.stdout + res.stderr)

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

    def test_collectonly_alias_forge_blocked_e2e(self):
        # grill-code (2026-07-14): the R4 forge reconstructed via the no-dash
        # alias `--collectonly` (missed by the pre-iter69 denylist) PLUS an
        # import-crash mutant (syntactically valid, so it slips past
        # syntax_check_mutants). Both drill layers must still block it — the
        # NO_RUN denylist now enumerates the alias.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            (root / "src" / "m.py").write_text("a = 1\n\nb = 2\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "python3 -m pytest --collectonly -q",
                "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "", "mutated": "raise Exception()"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 1)
            self.assertIn("no-run フラグ", res.stdout)
            self.assertIn("verdict: FAIL", report.read_text())

    def test_setup_plan_alias_forge_blocked_e2e(self):
        # Same forge class via `--setup-plan` (runs fixtures, never test bodies).
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            (root / "src" / "m.py").write_text("a = 1\n\nb = 2\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "python3 -m pytest --setup-plan -q",
                "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "", "mutated": "raise Exception()"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 1)
            self.assertIn("no-run フラグ", res.stdout)

    def test_quoted_collectonly_forge_blocked_e2e(self):
        # blind-2nd F-1 [Critical]: the R4 forge reconstructed by QUOTING the
        # no-run flag (`"--collect-only"`), which is clean against the raw-string
        # regex but becomes a bare flag at shlex-exec time. The drill now
        # shlex-normalizes before the NO_RUN check, so it must still block.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            (root / "src" / "m.py").write_text("a = 1\n_ = 1\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": 'python3 -m pytest "--collect-only" -q',
                "timeout_seconds": 10,
                "mutants": [{"file": "src/m.py", "line": 2,
                             "original": "_ = 1", "mutated": "raise Exception()"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 1)
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
            cmd = _write_probe_test(root, "b = 2", "src/m.py")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": cmd,
                "timeout_seconds": 30,
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
            cmd = _write_probe_test(root, "b = 2", "src/m.py")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": cmd,
                "timeout_seconds": 30,
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
            cmd = _write_probe_test(root, "b = 2", "src/m.py")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": cmd,
                "timeout_seconds": 30,
                "mutants": [{"file": "src/m.py", "line": 5,
                             "original": "b = 2", "mutated": "b = 3"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0,
                             f"comment-only hunk must not demand a mutant: "
                             f"{res.stdout}{res.stderr}")
            self.assertIn("verdict: PASS", report.read_text())

    def test_import_probe_baseline_blocked_no_test_proof(self):
        # D1 (iter71): a non-runner import probe (`python3 -c "import m"`) exits
        # 0 and, against the current exit-code baseline, the mutant `b = 1/0`
        # makes the import crash -> "caught" -> PASS (the forge). Post-iter71 the
        # baseline demands a positive marker; the probe runs zero tests so the
        # baseline is "no-test-proof" -> BLOCKED (rc1) before any mutant runs.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "m.py").write_text("a = 1\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "i")
            (root / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")  # 行2=added
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": 'python3 -c "import m"',
                "timeout_seconds": 10,
                "mutants": [{"file": "m.py", "line": 2,
                             "original": "b = 2", "mutated": "b = 1/0"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
            self.assertIn("no-test-proof", res.stdout)
            self.assertIn("baseline: no-test-proof", report.read_text())


class TestVendorExclusion(unittest.TestCase):
    def test_vendor_excluded_segments(self):
        # OBS-023: vendor/build 出力が drill スコープを汚染しない
        for rel in [
            "node_modules/.bin/esbuild",
            "packages/app/node_modules/x/index.js",
            "dist/main.js",
            ".venv/lib/python3.12/site-packages/x.py",
            # 境界ピン: ディレクトリ segment 一致なら深さ問わず除外
            # （grill-plan B 🟡-1 / v160-security.md 残余リスク 1）
            "src/dist/gen.js",
        ]:
            self.assertTrue(drill.vendor_excluded(rel), rel)
        for rel in ["src/app.py", "src/dist.py", "distribution/x.py"]:
            self.assertFalse(drill.vendor_excluded(rel), rel)

    def test_added_lines_exclude_vendor_under_empty_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("a = 1\n", encoding="utf-8")
            nm = root / "node_modules" / "pkg"
            nm.mkdir(parents=True)
            (nm / "index.js").write_text("x\n", encoding="utf-8")
            _git(root, "add", "-A")
            added = drill.added_lines_by_file(root, drill.EMPTY_TREE)
            self.assertIn("src/app.py", added)
            self.assertNotIn("node_modules/pkg/index.js", added)

    def test_undecodable_tracked_diff_does_not_crash(self):
        # NUL なし不正 UTF-8: git はテキスト扱いで +行に生バイトを乗せる
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "blob.bin").write_bytes(b"\xcf\xfa\xed\xfe" * 64 + b"\n")
            (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            _git(root, "add", "-A")
            added = drill.added_lines_by_file(root, drill.EMPTY_TREE)  # 例外なく返る
            self.assertIn("src/app.py", added)


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

    def test_quoted_flag_rejected_via_shlex_norm(self):
        # blind-2nd (2026-07-14): 生文字列では境界不成立で通り抜ける引用済み
        # フラグ（"--collect-only"）を、実行系と同じ shlex 正規化で拒否する。
        with tempfile.TemporaryDirectory() as d:
            lib = self._lib(d, "AEGIS_TEST_NO_RUN_FLAG_REGEX='collect-only'\n")
            for cmd in ('pytest "--collect-only" -q', "pytest '--collect-only' -q"):
                with self.assertRaises(drill.DrillError, msg=cmd):
                    drill.check_no_run_command(cmd, patterns_lib=lib)

    def test_real_patterns_rejects_quoted_collect_only(self):
        with self.assertRaises(drill.DrillError):
            drill.check_no_run_command('python3 -m pytest "--collect-only" -q')

    def test_real_patterns_rejects_fixtures_per_test(self):
        # blind-2nd F-2: --fixtures-per-test はテスト本体を走らせない no-run
        with self.assertRaises(drill.DrillError):
            drill.check_no_run_command("python3 -m pytest --fixtures-per-test -q")

    def test_unparseable_quoting_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            lib = self._lib(d, "AEGIS_TEST_NO_RUN_FLAG_REGEX='collect-only'\n")
            with self.assertRaises(drill.DrillError):
                drill.check_no_run_command('pytest "unterminated', patterns_lib=lib)


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


if __name__ == "__main__":
    unittest.main()
