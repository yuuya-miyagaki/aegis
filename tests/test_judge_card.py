import importlib.util
import json
import subprocess as sp
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build-judge-card.py"

def _load():
    spec = importlib.util.spec_from_file_location("judge", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

judge = _load()


class TestReadClaims(unittest.TestCase):
    def test_parses_fenced_claims_block(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "review.md"
            p.write_text(
                "# review\n\n```claims\n"
                "tests_pass: true\nno_stubs: true\nverdict: approve\n```\n",
                encoding="utf-8")
            claims = judge.read_claims(p)
            self.assertEqual(claims["tests_pass"], True)
            self.assertEqual(claims["verdict"], "approve")

    def test_missing_block_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "review.md"
            p.write_text("# review\n\nno claims here\n", encoding="utf-8")
            self.assertIsNone(judge.read_claims(p))

    def test_missing_file_returns_none(self):
        self.assertIsNone(judge.read_claims(Path("/nonexistent/x.md")))


class TestFingerprint(unittest.TestCase):
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def _repo(self, d):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-qm", "i")
        return root

    def test_fingerprint_changes_with_code(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo(d)
            (root / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            fp1 = judge.code_fingerprint(root)
            (root / "a.py").write_text("x = 1\ny = 3\n", encoding="utf-8")
            fp2 = judge.code_fingerprint(root)
            self.assertNotEqual(fp1, fp2)

    def test_fingerprint_stable_when_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo(d)
            (root / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            self.assertEqual(judge.code_fingerprint(root), judge.code_fingerprint(root))


class TestTier1(unittest.TestCase):
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def _repo_with_change(self, d, body):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-qm", "i")
        (root / "m.py").write_text(body, encoding="utf-8")  # untracked change
        return root

    def test_scan_stubs_detects_todo_in_changed(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    pass  # stub\n")
            hits = judge.scan_stubs(root)
            self.assertTrue(hits)

    def test_scan_stubs_clean(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            self.assertEqual(judge.scan_stubs(root), [])

    def test_read_test_result_fresh_green(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            fp = judge.code_fingerprint(root)
            qa = root / "docs" / "qa-reports"
            qa.mkdir(parents=True)
            (qa / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": fp}),
                encoding="utf-8")
            self.assertEqual(judge.read_test_result(root), "green")

    def test_read_test_result_stale_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            qa = root / "docs" / "qa-reports"
            qa.mkdir(parents=True)
            (qa / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": "STALE"}),
                encoding="utf-8")
            self.assertEqual(judge.read_test_result(root), "unverified")

    def test_read_test_result_absent_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            self.assertEqual(judge.read_test_result(root), "unverified")


class TestResolveReport(unittest.TestCase):
    def _status(self, root, review_ref):
        docs = root / "docs"; docs.mkdir(exist_ok=True)
        (docs / "STATUS.md").write_text(
            "---\ncurrent_refs:\n"
            f"  review: {review_ref}\n  qa: null\n---\n", encoding="utf-8")

    def test_resolves_review_ref(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._status(root, "docs/qa-reports/review.md")
            self.assertEqual(judge.resolve_gate_report(root, "review"),
                             root / "docs/qa-reports/review.md")

    def test_null_ref_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._status(root, "null")
            self.assertIsNone(judge.resolve_gate_report(root, "review"))


class TestVerdict(unittest.TestCase):
    def _facts(self, **over):
        f = {"tests": "green", "stubs": [], "secrets": [],
             "b1_verdict": None, "deps": "clean"}
        f.update(over)
        return f

    def test_clean_all_green(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(), {"verdict": "approve"})
        self.assertEqual(v.overall, 0)

    def test_stub_blocks_even_without_claim(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(stubs=["m.py:2"]), None)
        self.assertEqual(v.overall, 1)
        self.assertTrue(v.red)

    def test_claim_tests_pass_but_red_blocks(self):
        v = judge.compute_verdict("review", {"tests_pass": True, "verdict": "approve"},
                                  self._facts(tests="red"), None)
        self.assertEqual(v.overall, 1)

    def test_tests_unverified_is_yellow(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(tests="unverified"), {"verdict": "approve"})
        self.assertEqual(v.overall, 2)

    def test_second_opinion_divergence_is_yellow(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(), {"verdict": "reject"})
        self.assertEqual(v.overall, 2)

    def test_second_opinion_missing_is_yellow_for_review(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(), None)
        self.assertEqual(v.overall, 2)

    def test_claims_absent_is_yellow_not_red(self):
        v = judge.compute_verdict("review", None, self._facts(), None)
        self.assertEqual(v.overall, 2)

    def test_deps_vuln_is_yellow_never_red(self):
        # deps audits are flaky/env-sensitive: a vuln advises but never blocks,
        # even when a claim asserts deps_clean.
        v = judge.compute_verdict("security", {"deps_clean": True, "verdict": "approve"},
                                  self._facts(deps="vuln"), {"verdict": "approve"})
        self.assertEqual(v.overall, 2)


class TestMain(unittest.TestCase):
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def _project(self, d, *, body, claims_block, review_ref="docs/qa-reports/review.md",
                 test_result=None):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
        self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
        (root / "m.py").write_text(body, encoding="utf-8")
        docs = root / "docs"; (docs / "qa-reports").mkdir(parents=True)
        (docs / "STATUS.md").write_text(
            "---\ncurrent_refs:\n"
            f"  review: {review_ref}\n  qa: null\n---\n", encoding="utf-8")
        if review_ref != "null":
            (root / review_ref).write_text("# review\n\n" + claims_block, encoding="utf-8")
        if test_result is not None:
            (docs / "qa-reports" / "test-result.json").write_text(
                json.dumps(test_result), encoding="utf-8")
        return root

    def _run(self, root, gate="review"):
        out = root / "docs" / "qa-reports" / f"judge-{gate}.md"
        return sp.run(["python3", str(SCRIPT), "--gate", gate, "--root", str(root),
                       "--report-out", str(out)], capture_output=True, text=True), out

    def test_block_on_stub_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._project(
                d, body="def f():\n    pass  # stub\n",
                claims_block="```claims\nno_stubs: true\nverdict: approve\n```\n")
            res, out = self._run(root)
            self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
            self.assertIn("🔴", out.read_text())

    def test_yellow_on_missing_second_opinion_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            fp_body = "def f():\n    return 1\n"
            root = self._project(
                d, body=fp_body,
                claims_block="```claims\nno_stubs: true\ntests_pass: true\nverdict: approve\n```\n")
            # add a fresh green test-result so tests aren't unverified
            fp = judge.code_fingerprint(root)
            (root / "docs" / "qa-reports" / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": fp}), encoding="utf-8")
            res, out = self._run(root)
            self.assertEqual(res.returncode, 2, res.stdout + res.stderr)

    def test_green_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            body = "def f():\n    return 1\n"
            root = self._project(
                d, body=body,
                claims_block=("```claims\nno_stubs: true\ntests_pass: true\nverdict: approve\n"
                              "second_opinion:\n  verdict: approve\n```\n"))
            fp = judge.code_fingerprint(root)
            (root / "docs" / "qa-reports" / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": fp}), encoding="utf-8")
            res, out = self._run(root)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("🟢", out.read_text())


class TestRecorder(unittest.TestCase):
    REC = Path(__file__).resolve().parent.parent / "scripts" / "record-test-result.py"

    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def test_records_green(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git(root, "init", "-q"); self._git(root, "config", "user.email", "t@t")
            self._git(root, "config", "user.name", "t")
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
            (root / "a.py").write_text("x=1\ny=2\n", encoding="utf-8")
            sp.run(["python3", str(self.REC), "--root", str(root), "true"],
                   check=True, capture_output=True)
            data = json.loads((root / "docs/qa-reports/test-result.json").read_text())
            self.assertEqual(data["status"], "green")
            self.assertEqual(data["code_fingerprint"], judge.code_fingerprint(root))

    def test_records_red_on_failing_command(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git(root, "init", "-q"); self._git(root, "config", "user.email", "t@t")
            self._git(root, "config", "user.name", "t")
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
            (root / "a.py").write_text("x=1\ny=2\n", encoding="utf-8")
            sp.run(["python3", str(self.REC), "--root", str(root), "false"],
                   check=True, capture_output=True)
            data = json.loads((root / "docs/qa-reports/test-result.json").read_text())
            self.assertEqual(data["status"], "red")


class TestAuditDeps(unittest.TestCase):
    def test_no_manifest_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(judge.audit_deps(Path(d)), "unverified")

    def test_python_without_requirements_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "main.py").write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(judge.audit_deps(Path(d)), "unverified")

    def test_node_without_lockfile_is_unverified(self):
        # package.json but no lockfile must NOT fabricate 'vuln' from an npm error.
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "package.json").write_text("{}", encoding="utf-8")
            self.assertEqual(judge.audit_deps(Path(d)), "unverified")


if __name__ == "__main__":
    unittest.main()
