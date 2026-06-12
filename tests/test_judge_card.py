import importlib.util
import json
import shutil
import subprocess as sp
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = ROOT_DIR / "scripts" / "build-judge-card.py"
RECORDER = ROOT_DIR / "scripts" / "record-test-result.py"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

judge = _load("judge", SCRIPT)
record = _load("record_mod", RECORDER)


def _ev_line(cmd: str, status: str, fp: str,
             marker_verified: bool = True) -> str:
    """Build a synthetic OBSERVED evidence entry.

    C-2 (v1.6.1) requires `marker_verified:true` for an observed entry
    to count as green; existing fixtures simulate a real test run, so
    we default to True. Tests that explicitly need a forgery / migration
    case pass marker_verified=False.
    """
    return json.dumps({"v": 1, "ts": "2026-06-10T00:00:00Z", "src": "observed",
                       "cmd": cmd, "status": status,
                       "payload_sha": "0" * 64, "fp": fp,
                       "marker_verified": marker_verified}) + "\n"


def _copy_lib(root: Path) -> None:
    """E1 fixture: read_test_result/current_fingerprint delegate to
    hooks/lib/{fingerprint,patterns}.sh, so the project root needs them."""
    shutil.copytree(ROOT_DIR / "hooks" / "lib", root / "hooks" / "lib")


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


class TestCurrentFingerprint(unittest.TestCase):
    """Delegation contract: current_fingerprint() shells out to
    hooks/lib/fingerprint.sh (single owner — behavior tests live in
    tests/test_fingerprint_lib.py). Here we test only the python boundary."""

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
        _copy_lib(root)
        return root

    def test_missing_lib_returns_nolib(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(judge.current_fingerprint(Path(d)), "nolib")

    def test_returns_hex64_and_is_stable(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo(d)
            fp1 = judge.current_fingerprint(root)
            self.assertRegex(fp1, r"^[0-9a-f]{64}$")
            self.assertEqual(fp1, judge.current_fingerprint(root))

    def test_changes_with_code(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo(d)
            fp1 = judge.current_fingerprint(root)
            (root / "a.py").write_text("x = 1\ny = 3\n", encoding="utf-8")
            fp2 = judge.current_fingerprint(root)
            self.assertNotEqual(fp1, fp2)


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


class TestReadTestResultFromEvidence(unittest.TestCase):
    """E1: the judge's test verdict comes from the OBSERVED evidence log
    (.claude/evidence-log.jsonl), never from a self-reported file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        sp.run(["git", "-C", str(self.root), "init", "-q"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                "-c", "user.name=t", "commit", "-q", "--allow-empty",
                "-m", "init"], check=True, capture_output=True)
        _copy_lib(self.root)
        (self.root / ".claude").mkdir()
        self.log = self.root / ".claude" / "evidence-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_log_is_unverified(self):
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_ok_with_matching_fp_is_green(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("python3 -m unittest", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_fail_with_matching_fp_is_red(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("pytest", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_stale_fp_is_unverified(self):
        self.log.write_text(_ev_line("pytest", "ok", "f" * 64))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_newest_stale_does_not_fall_back_to_older_fresh(self):
        # grill-code 🟢: 最新エントリが decide する。最新が stale fp なら
        # それより古い「現 fp 一致の ok」へ遡って green 化してはならない
        # （遡ると、コード変更後に古い記録で承認できてしまう）。
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("pytest", "ok", fp) + _ev_line("pytest", "ok", "f" * 64))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_non_test_commands_ignored(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("git status", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_latest_matching_entry_wins(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("pytest", "ok", fp) + _ev_line("pytest", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_broken_lines_skipped(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text("{{{broken\n" + _ev_line("pytest", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_rotated_dot1_is_scanned(self):
        fp = judge.current_fingerprint(self.root)
        (self.root / ".claude" / "evidence-log.jsonl.1").write_text(
            _ev_line("pytest", "ok", fp))
        self.log.write_text("")
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_manual_src_counts(self):
        fp = judge.current_fingerprint(self.root)
        row = json.loads(_ev_line("python3 -m unittest", "ok", fp))
        row["src"] = "manual"
        self.log.write_text(json.dumps(row) + "\n")
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_oversize_current_fp_is_unverified(self):
        # AEGIS_FP_MAX_FILES=0 相当は作れないため、巨大変更を作るより
        # current_fingerprint が hex64 以外を返す経路を直接検証する:
        # hooks/lib/fingerprint.sh を削除 → "nolib" → unverified。
        shutil.rmtree(self.root / "hooks")
        fpval = judge.current_fingerprint(self.root)
        self.assertEqual(fpval, "nolib")
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_multiline_command_classified(self):
        """改行入りコマンドは ';' 正規化後に分類される（grep/re パリティ、T1 v1.5.1）。"""
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("echo build done\nvitest run", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_mention_in_args_not_classified(self):
        """引数位置のランナー名言及（grep vitest package.json）は分類されず、
        その失敗が直前の実テスト green を覆さない（false-RED 解消の e2e）。"""
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("vitest run", "ok", fp)
            + _ev_line("grep vitest package.json", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_quoted_runner_mention_failure_does_not_red(self):
        """クォート内ランナー言及の失敗（grep -E "(unittest|pytest)" f, rc≠0）は
        分類されず、直前の実 green を覆さない（T1 v1.5.2 false-RED 根治 e2e）。"""
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("vitest run", "ok", fp)
            + _ev_line('grep -E "(unittest|pytest)" missing.txt', "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_mask_is_substitution_not_deletion(self):
        """grill-code v1.5.2 J1: マスクは「Q 置換」であり「削除」ではないことを
        production 消費者（read_test_result）で直接ピン留めする。
        '"echo" pytest' (ok) は Q 置換なら 'Q pytest' → 非分類 → unverified。
        削除実装に変異すると ' pytest' → コマンド位置一致 → green 偽装が成立し、
        このテストが RED になる（mutation killer）。"""
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line('"echo" pytest', "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_missing_strip_patterns_is_unverified(self):
        """patterns.sh に STRIP 変数が無い（破損・旧版）場合、判定は
        fail-closed（unverified）に倒れる。"""
        lib = self.root / "hooks" / "lib" / "patterns.sh"
        text = lib.read_text(encoding="utf-8")
        lib.write_text(text.replace("AEGIS_TR_STRIP_DQ", "X_DQ")
                           .replace("AEGIS_TR_STRIP_SQ", "X_SQ"),
                       encoding="utf-8")
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("pytest", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")


class TestStubPrecision(unittest.TestCase):
    """Regression: stub scan must not hard-block legitimate code (#grill-code)."""

    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def _repo_with_change(self, d, body, name="m.py"):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-qm", "i")
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return root

    def test_lowercase_todo_identifiers_are_clean(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(
                d, "todos = []\nitems = todoStore.all()\ntodo = 1\n")
            self.assertEqual(judge.scan_stubs(root), [],
                             "lowercase identifiers must not be flagged as stubs")

    def test_html_placeholder_attr_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(
                d, '<input placeholder="お名前">\n', name="form.html")
            self.assertEqual(judge.scan_stubs(root), [],
                             "HTML placeholder attribute must not be flagged")

    def test_uppercase_marker_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "x = 1  # TODO: finish\n")
            self.assertTrue(judge.scan_stubs(root))

    def test_docs_changes_are_not_scanned_for_stubs(self):
        # A TODO in a changed doc must not hard-block a gate (docs aren't code).
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "# TODO: write this\n",
                                          name="docs/notes.md")
            self.assertEqual(judge.scan_stubs(root), [])


class TestSecretScanScope(unittest.TestCase):
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def test_secret_on_added_line_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git(root, "init", "-q"); self._git(root, "config", "user.email", "t@t")
            self._git(root, "config", "user.name", "t")
            (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
            self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
            (root / "cfg.py").write_text('api_key = "abcd1234efgh"\n', encoding="utf-8")
            self.assertTrue(judge.scan_secrets(root))

    def test_preexisting_secret_on_unchanged_line_not_flagged(self):
        # A secret on a committed (unchanged) line must NOT block a change that
        # only touches an unrelated line of the same file.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git(root, "init", "-q"); self._git(root, "config", "user.email", "t@t")
            self._git(root, "config", "user.name", "t")
            (root / "cfg.py").write_text('api_key = "abcd1234efgh"\n', encoding="utf-8")
            self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
            (root / "cfg.py").write_text(
                'api_key = "abcd1234efgh"\nunrelated = 1\n', encoding="utf-8")
            self.assertEqual(judge.scan_secrets(root), [],
                             "pre-existing secret on an unchanged line must not block")


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

    def _project(self, d, *, body, claims_block, review_ref="docs/qa-reports/review.md"):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
        self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
        (root / "m.py").write_text(body, encoding="utf-8")
        _copy_lib(root)
        (root / ".claude").mkdir()
        docs = root / "docs"; (docs / "qa-reports").mkdir(parents=True)
        (docs / "STATUS.md").write_text(
            "---\ncurrent_refs:\n"
            f"  review: {review_ref}\n  qa: null\n---\n", encoding="utf-8")
        if review_ref != "null":
            (root / review_ref).write_text("# review\n\n" + claims_block, encoding="utf-8")
        return root

    def _inject_green_evidence(self, root):
        """Observed green run bound to the CURRENT worktree fingerprint —
        must be done after every file of the fixture is in place."""
        fp = judge.current_fingerprint(root)
        (root / ".claude" / "evidence-log.jsonl").write_text(
            _ev_line("python3 -m unittest", "ok", fp), encoding="utf-8")

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
            # add fresh observed green evidence so tests aren't unverified
            self._inject_green_evidence(root)
            res, out = self._run(root)
            self.assertEqual(res.returncode, 2, res.stdout + res.stderr)

    def test_green_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            body = "def f():\n    return 1\n"
            root = self._project(
                d, body=body,
                claims_block=("```claims\nno_stubs: true\ntests_pass: true\nverdict: approve\n"
                              "second_opinion:\n  verdict: approve\n```\n"))
            self._inject_green_evidence(root)
            res, out = self._run(root)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("🟢", out.read_text())

    def test_internal_error_is_yellow_not_hard_block(self):
        # A judge that cannot run (e.g. non-git project) must yield ack-able 🟡
        # (rc 2), not a non-ack-able 🔴 (rc 1) that bricks every gate.
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "judge.md"
            res = sp.run(["python3", str(SCRIPT), "--gate", "review", "--root", str(d),
                          "--report-out", str(out)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 2, res.stdout + res.stderr)


class TestRecordTestResultManual(unittest.TestCase):
    """E1: record-test-result.py is the MANUAL fallback writer — it executes
    the test command itself (trusted runner) and appends src:"manual" to the
    evidence log. It must no longer write test-result.json (self-report)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        sp.run(["git", "-C", str(self.root), "init", "-q"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "config", "user.email", "t@t"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "config", "user.name", "t"],
               check=True, capture_output=True)
        (self.root / "a.py").write_text("x=1\n", encoding="utf-8")
        sp.run(["git", "-C", str(self.root), "add", "-A"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "commit", "-qm", "i"],
               check=True, capture_output=True)
        _copy_lib(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_passing_command_appends_manual_ok(self):
        rc = record.main(["--root", str(self.root), "true"])
        self.assertEqual(rc, 0)
        row = json.loads((self.root / ".claude" / "evidence-log.jsonl")
                         .read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(row["src"], "manual")
        self.assertEqual(row["status"], "ok")
        self.assertRegex(row["fp"], r"^[0-9a-f]{64}$")

    def test_failing_command_appends_manual_fail(self):
        record.main(["--root", str(self.root), "false"])
        row = json.loads((self.root / ".claude" / "evidence-log.jsonl")
                         .read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(row["status"], "fail")

    def test_no_test_result_json_written(self):
        record.main(["--root", str(self.root), "true"])
        self.assertFalse(
            (self.root / "docs" / "qa-reports" / "test-result.json").exists())


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


class TestBinaryScanResilience(unittest.TestCase):
    """OBS-023: バイナリ混入 index で judge ビルダーがクラッシュしない。"""

    def _scaffold_repo(self, root: Path) -> None:
        sp.run(["git", "init", "-q"], cwd=str(root), check=True)
        _copy_lib(root)
        (root / "docs" / "qa-reports").mkdir(parents=True)
        (root / "docs" / "STATUS.md").write_text(
            "---\nframework: aegis\nmode: Dev\nphase: review\n"
            "task_type: feature\ntask_size: M\n"
            "gate_approvals:\n  review: pending\n"
            "current_refs:\n  review: null\n---\n", encoding="utf-8")

    def test_scan_skips_undecodable_changed_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._scaffold_repo(root)
            (root / "src").mkdir()
            # NUL なし不正 UTF-8 → drill は追加行として返し、read_text が strict だと落ちる
            (root / "src" / "blob.bin").write_bytes(b"\xcf\xfa\xed\xfe" * 64 + b"\n")
            sp.run(["git", "add", "-A"], cwd=str(root), check=True)
            self.assertEqual(judge.scan_stubs(root), [])    # 例外なく skip
            self.assertEqual(judge.scan_secrets(root), [])

    def test_obs023_cli_repro_no_traceback(self):
        # 再現コマンド: python3 scripts/build-judge-card.py --gate review --root .
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._scaffold_repo(root)
            nm = root / "node_modules" / ".bin"
            nm.mkdir(parents=True)
            (nm / "esbuild").write_bytes(b"\xcf\xfa\xed\xfe" * 256 + b"\n")
            (root / "src").mkdir()
            (root / "src" / "blob.bin").write_bytes(b"\xcf\xfa\xed\xfe" * 64 + b"\n")
            sp.run(["git", "add", "-A"], cwd=str(root), check=True)
            r = sp.run(["python3", str(SCRIPT), "--gate", "review", "--root", str(root)],
                       capture_output=True, text=True, timeout=120)
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn(r.returncode, (0, 1, 2))
            self.assertTrue((root / "docs" / "qa-reports" / "judge-review.md").is_file())


if __name__ == "__main__":
    unittest.main()
