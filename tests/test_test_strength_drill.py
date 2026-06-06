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

    def test_green(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.check_baseline("true", Path(d), 10), "green")

    def test_red(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(drill.check_baseline("false", Path(d), 10), "red")

    def test_flaky(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(drill.check_baseline(self._flaky_cmd(root), root, 10), "flaky")


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
                               baseline="green", survived=[])
            text = out.read_text()
            self.assertIn("verdict: PASS", text)
            self.assertIn("mutants_total: 2", text)
            self.assertIn("survived: []", text)

    def test_fail_report_lists_survivors(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.md"
            drill.write_report(out, verdict="FAIL", total=2, caught=1,
                               baseline="green", survived=["src/a.py:3"])
            text = out.read_text()
            self.assertIn("verdict: FAIL", text)
            self.assertIn("src/a.py:3", text)


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

    def test_new_untracked_file_pass_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "i")
            (root / "src").mkdir()
            (root / "src" / "n.py").write_text("v = 7\n", encoding="utf-8")  # untracked
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "grep -q 'v = 7' src/n.py",
                "timeout_seconds": 10,
                "mutants": [{"file": "src/n.py", "line": 1,
                             "original": "v = 7", "mutated": "v = 8"}],
            }), encoding="utf-8")
            report = root / "r.md"
            res = self._run(root, spec, report)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("verdict: PASS", report.read_text())

    def test_survived_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            self._commit_seed(root)
            (root / "src" / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            spec = root / "s.drill"
            spec.write_text(json.dumps({
                "test_command": "true",  # blind => survives
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
            _git_init(root)
            res = self._run(root, root / "nope.drill", root / "r.md")
            self.assertEqual(res.returncode, 1)


if __name__ == "__main__":
    unittest.main()
