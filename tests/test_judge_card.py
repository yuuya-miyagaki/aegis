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


if __name__ == "__main__":
    unittest.main()
