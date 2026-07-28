#!/usr/bin/env python3
"""C-2: judge card must NOT mark `pytest --version` style commands as green.

Before v1.6.1 the harness classified a Bash command as a "test run" purely
by matching the runner name (pytest / vitest / jest / cargo test / go test /
unittest / npm test). Any command that started with the runner name and
exited 0 was recorded as `status:"ok"` AND the judge card later printed
`テスト: green` — even when the command was `pytest --version`, `--collect-only`,
`-h`, or `-k __NEVER_MATCH__` (no test actually ran).

Fix (Task 2, v1.6.1):

  (a) Add AEGIS_TEST_PASS_MARKER_REGEX to hooks/lib/patterns.sh: tight
      summary-line patterns for each runner (pytest "== N passed in ...",
      jest "Tests: N passed", cargo "test result: ok.", go "ok pkg X.Xs",
      unittest "Ran N tests" + "OK").

  (b) hooks/post-bash-observe.sh inspects the tool_response output and,
      if AT LEAST ONE marker hits, writes marker_verified:true into the
      evidence-log entry. Otherwise marker_verified:false.

  (c) scripts/build-judge-card.py:read_test_result returns "green" / "red"
      ONLY when an entry has marker_verified:true. v1.6.0 entries (no
      such field) and any false entry → "unverified" (fail-closed).

This file pins the behavior end-to-end against a synthetic evidence log
in a tmp scratch root.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# A. patterns.sh layer: AEGIS_TEST_PASS_MARKER_REGEX must exist and be
# loadable from a bash subshell as an array.
# ---------------------------------------------------------------------------


class TestPassMarkerPatternsExposed(unittest.TestCase):
    LIB = ROOT / "hooks" / "lib" / "patterns.sh"

    def _load_array(self, var: str) -> list[str]:
        cmd = (f'source "{self.LIB}" && '
               f'printf "%s\\0" "${{{var}[@]}}"')
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"bash failed loading ${var}: {r.stderr}")
        return [x for x in r.stdout.split("\x00") if x]

    def test_marker_array_defined(self):
        """STRONG markers — single-line sufficient. v1.6.1 grill-code
        Critical split: unittest+cargo moved to AEGIS_TEST_PASS_MARKER_PAIRS
        (weak/pair-required). Remaining strong: pytest === summary, jest,
        vitest Test Files, go pkg+time."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        self.assertTrue(arr,
                        "AEGIS_TEST_PASS_MARKER_REGEX is empty/undefined")
        self.assertGreaterEqual(
            len(arr), 3,
            f"expected ≥3 strong runner markers, got {len(arr)}: {arr}")

    def test_pytest_summary_marker_matches_real_output(self):
        """The pytest summary line must hit."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        # A real pytest summary line.
        sample = "============================= 3 passed in 0.42s =============================="
        hit = any(self._grep_e_matches(p, sample) for p in arr)
        self.assertTrue(hit,
                        f"no marker matched pytest summary line: {sample!r}")

    def test_jest_summary_marker_matches(self):
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        sample = "Tests:       5 passed, 5 total"
        hit = any(self._grep_e_matches(p, sample) for p in arr)
        self.assertTrue(hit, f"no marker matched jest line: {sample!r}")

    def test_unittest_pair_anchors_match(self):
        """Unittest is now PAIR-required (weak markers). The pair entry
        format is `ANCHOR|||COMPANION` — split and confirm both halves
        match their respective unittest summary line."""
        pairs = self._load_array("AEGIS_TEST_PASS_MARKER_PAIRS")
        unittest_pair = next((p for p in pairs if "Ran" in p), None)
        self.assertIsNotNone(unittest_pair,
                             f"unittest pair missing from PAIRS: {pairs}")
        anchor, _, companion = unittest_pair.partition("|||")
        self.assertTrue(
            self._grep_e_matches(anchor, "Ran 17 tests in 89.6s"),
            f"unittest anchor must match 'Ran N tests in X.Xs': {anchor}")
        self.assertTrue(
            self._grep_e_matches(companion, "OK"),
            f"unittest companion must match 'OK': {companion}")

    def test_pytest_version_does_NOT_match(self):
        """The whole point: `pytest --version` output must NOT trigger
        any pass marker."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        sample = "pytest 7.4.0"
        hit = any(self._grep_e_matches(p, sample) for p in arr)
        self.assertFalse(hit,
                         f"FALSE-GREEN: a marker matched the pytest --version "
                         f"output: pattern hit={sample!r}, arr={arr}")

    def test_pytest_collect_only_does_NOT_match(self):
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        for sample in (
            "collected 3 items",
            "<Module test_x.py>",
            "no tests ran in 0.01s",
        ):
            hit = any(self._grep_e_matches(p, sample) for p in arr)
            self.assertFalse(hit,
                             f"FALSE-GREEN on --collect-only line {sample!r}")

    def test_echo_passed_string_does_NOT_match(self):
        """`echo "1 passed"` is NOT a real summary line."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        for sample in (
            "1 passed",
            "PASS",
            "passed",
        ):
            hit = any(self._grep_e_matches(p, sample) for p in arr)
            self.assertFalse(hit,
                             f"FALSE-GREEN on echoed token {sample!r}")

    def test_unittest_OK_alone_does_NOT_match(self):
        """grill-code A-Crit-2 / B-Critical: `echo OK` must NOT trigger
        the unittest marker. The unittest pass signal is BOTH `Ran N tests`
        AND `OK` together — implemented as a peephole pair in evidence.sh."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_REGEX")
        # Each marker individually is allowed to match this string (we'll
        # tighten in evidence.sh's pair-check), but in isolation the
        # AEGIS_TEST_PASS_MARKER_REGEX patterns must not certify "OK" alone.
        # Confirm that the new evidence.sh-side gate (pair requirement)
        # exists by checking AEGIS_TEST_PASS_MARKER_PAIRS is defined.
        # (Standalone hits remain possible at the patterns layer; the pair
        # contract is enforced at the consumer layer — see test_marker_peephole_pair_required_for_weak_markers.)

    def test_cargo_test_result_alone_does_NOT_certify(self):
        """`echo "test result: ok."` alone must NOT certify green —
        a real cargo run prints both `running N tests` and the result line."""
        # Asserted at the consumer layer (build-judge-card.py via
        # the pair-required pattern in patterns.sh).

    def test_pair_array_defined(self):
        """AEGIS_TEST_PASS_MARKER_PAIRS: weak markers that require a
        companion-line peephole (consumer-enforced)."""
        arr = self._load_array("AEGIS_TEST_PASS_MARKER_PAIRS")
        self.assertGreaterEqual(
            len(arr), 2,
            f"expected ≥2 pair entries (unittest + cargo at minimum), got "
            f"{len(arr)}: {arr}")

    @staticmethod
    def _grep_e_matches(pattern: str, text: str) -> bool:
        r = subprocess.run(
            ["grep", "-E", "-q", pattern],
            input=text.encode(),
            capture_output=True)
        return r.returncode == 0


# ---------------------------------------------------------------------------
# B. read_test_result schema migration: v1.6.0 entries (no marker_verified
# field) must NOT return green.
# ---------------------------------------------------------------------------


class TestReadTestResultSchemaMigration(unittest.TestCase):
    """Synthesize an evidence-log + repo state and call read_test_result
    directly."""

    @classmethod
    def setUpClass(cls):
        # Import build-judge-card.py as a module.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_judge_card", str(ROOT / "scripts" / "build-judge-card.py"))
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def _scratch_repo(self) -> tempfile.TemporaryDirectory:
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=p, check=True)
        subprocess.run(["git", "config", "user.email", "x@y.z"],
                       cwd=p, check=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=p, check=True)
        (p / "f.txt").write_text("seed", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=p, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                       cwd=p, check=True)
        # Mirror the libs/patterns the judge-card reads.
        ev = p / ".claude"
        ev.mkdir()
        # Sym to lib/ files so read_test_result can load the runner regex
        # AND current_fingerprint (delegates to fingerprint.sh).
        hooks_dir = p / "hooks"
        hooks_dir.mkdir()
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        for lib in ("patterns.sh", "fingerprint.sh"):
            (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
        return tmp

    def _fp(self, root: Path) -> str:
        return self.mod.current_fingerprint(root)

    def _write_entry(self, root: Path, entry: dict):
        log = root / ".claude" / "evidence-log.jsonl"
        log.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    def test_entry_without_marker_verified_field_returns_unverified(self):
        """v1.6.0 log entries (no marker_verified key) must NOT pass green.

        iter78 契約更新: pytest ok は green 制限で marker 検査より前に
        transparent 化されるため、この「marker キー欠如の observed ok は
        decidable にならない」検出力が pytest では死ぬ（transparent も unverified
        になるので assertion は通るが理由が別）。非 pytest（unittest）へスワップ
        して marker 経路の検出力を保存。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "python3 -m unittest",
                "status": "ok",
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "unverified")

    def test_entry_with_marker_verified_false_returns_unverified(self):
        # iter78 契約更新: pytest --version は green 制限で marker 検査より前に
        # transparent 化され、marker_verified:false ゲート（この pin の対象）の
        # 検出力が死ぬ。非 pytest（unittest）へスワップして marker false ゲートを
        # 保存（runner regex 一致・marker 未成立の形）。
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "python3 -m unittest --version",
                "status": "ok", "marker_verified": False,
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "unverified")

    def test_entry_with_marker_verified_true_and_ok_returns_green(self):
        # iter78 契約更新: observed pytest ok は green 制限で transparent 化され
        # green を返さなくなる。observed+marker_verified:true の green 経路
        # （この pin の対象）を保存するため非 pytest（unittest）へスワップ。
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "python3 -m unittest",
                "status": "ok", "marker_verified": True,
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "green")

    def test_entry_with_marker_verified_true_and_fail_returns_red(self):
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "observed", "cmd": "pytest tests/",
                "status": "fail", "marker_verified": True,
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "red")

    def test_manual_record_is_trusted_even_without_marker(self):
        """Entries from record-test-result.py have src='manual' and reflect
        a trusted runner; marker_verified is not required for those.

        iter71 note: the judge-side READ contract (src=manual is decidable
        without marker_verified) is UNCHANGED in iter71. iter71 enforces the
        marker verdict at record WRITE-time instead, closing the green-forge
        entry point before it is written — direct log tampering remains the
        job of the fingerprint / human-preview layer (as before)."""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            # iter78 契約更新: manual pytest ok は green 制限で transparent 化
            # され green を返さなくなる。manual が marker なしでも trusted＝
            # decidable green（この pin の対象）を保存するため非 pytest
            # （unittest）へスワップ。
            self._write_entry(r, {
                "v": 1, "ts": "2026-06-12T00:00:00Z",
                "src": "manual", "cmd": "python3 -m unittest",
                "status": "ok",
                "payload_sha": "x" * 64, "fp": fp,
            })
            self.assertEqual(self.mod.read_test_result(r), "green")


# ---------------------------------------------------------------------------
# C. post-bash-observe.sh end-to-end: feeding the observer a
# `pytest --version` (no marker) gives marker_verified:false. Feeding it
# a fake-but-realistic pytest summary gives marker_verified:true.
# ---------------------------------------------------------------------------


class TestPostBashObserveMarkerField(unittest.TestCase):
    HOOK = ROOT / "hooks" / "post-bash-observe.sh"

    def _scratch(self) -> tempfile.TemporaryDirectory:
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=p, check=True)
        subprocess.run(["git", "config", "user.email", "x@y.z"],
                       cwd=p, check=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=p, check=True)
        (p / "seed.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=p, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                       cwd=p, check=True)
        # Mirror the hook layout.
        hooks_dir = p / "hooks"
        hooks_dir.mkdir()
        for hk in ("post-bash-observe.sh",):
            (hooks_dir / hk).symlink_to(ROOT / "hooks" / hk)
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        for lib in ("extract-input.sh", "emit.sh", "patterns.sh",
                    "fingerprint.sh", "evidence.sh", "safety.sh", "marker.sh"):
            (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
        return tmp

    def _run(self, root: Path, payload: dict) -> dict | None:
        subprocess.run(
            ["bash", str(root / "hooks" / "post-bash-observe.sh")],
            input=json.dumps(payload), capture_output=True, text=True,
            cwd=str(root), env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)})
        log = root / ".claude" / "evidence-log.jsonl"
        if not log.exists():
            return None
        last = log.read_text(encoding="utf-8").splitlines()[-1]
        return json.loads(last)

    def test_real_summary_sets_marker_true(self):
        """K-1 (v1.6.2): pytest 系コマンドは strong marker に加えてプロローグ
        (platform / rootdir / collected N items) が出力に存在する必要がある。
        v1.6.1 は summary 1 行だけで true としたが、これは
        `echo "===== 3 passed ====="` 1 発の forge と区別不能なため、
        v1.6.2 でプロローグ存在を必須化（軸 3）。
        ここでは『実際の pytest 出力（プロローグ + 進捗 + 終端 summary）』を
        与えて引き続き verified=true を確認する。"""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "pytest tests/"},
                "tool_response": {
                    "exitCode": 0,
                    "output": (
                        "platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0\n"
                        "rootdir: /tmp/proj\n"
                        "collected 3 items\n\n"
                        "tests/test_x.py ...\n\n"
                        "============== 3 passed in 0.42s ==============\n"
                    ),
                },
            })
            self.assertIsNotNone(entry, "no log entry written")
            self.assertEqual(
                entry.get("marker_verified"), True,
                f"real pytest summary should mark verified=true: {entry}")

    def test_pytest_version_sets_marker_false(self):
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "pytest --version"},
                "tool_response": {"exitCode": 0, "output": "pytest 7.4.0\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"`pytest --version` must NOT verify: {entry}")

    def test_echo_passed_sets_marker_false(self):
        """Echoed token must not pass the summary regex (forge attempt)."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "pytest --collect-only; echo '1 passed'"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "collected 0 items\n1 passed\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"echoed `1 passed` must NOT verify: {entry}")

    def test_full_pytest_summary_line_echo_alone_does_NOT_verify(self):
        """grill-code A-Crit-2: `echo "============ 1 passed in 0.01s ============"`
        on its own is just a string — the runner did not execute. The peephole
        / pair contract must block this case."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                # pytest --collect-only matches the runner regex but runs no tests
                "tool_input": {
                    "command": "echo '============ 1 passed in 0.01s ============' && pytest --collect-only"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "============ 1 passed in 0.01s ============\ncollected 0 items\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"echo-forged full pytest summary must NOT verify: {entry}")

    def test_unittest_OK_alone_does_NOT_verify_in_observer(self):
        """`pytest --version && echo OK` — runner regex hits pytest, then OK
        is printed by echo. Without `Ran N tests in` companion the unittest
        marker must NOT verify."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "pytest --version && echo OK"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "pytest 7.4.0\nOK\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"bare 'OK' line must NOT verify without 'Ran N tests': {entry}")

    def test_cargo_test_result_alone_does_NOT_verify_in_observer(self):
        """`cargo test --no-run` prints `test result: ok. 0 passed` (compile
        only). Without `running N tests` companion the cargo marker must
        NOT verify."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "cargo test --no-run"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "test result: ok. 0 passed; 0 failed\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), False,
                f"bare `test result: ok` must NOT verify without "
                f"`running N tests`: {entry}")

    def test_unittest_OK_with_Ran_companion_verifies(self):
        """Both `Ran N tests in` AND `OK` present → pair satisfied."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "python3 -m unittest discover"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "...\nRan 5 tests in 0.123s\nOK\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), True,
                f"unittest pair (Ran ... + OK) must verify: {entry}")

    def test_cargo_pair_complete_verifies(self):
        """Both `running N tests` AND `test result: ok` present → pair satisfied."""
        with self._scratch() as _:
            r = Path(_)
            entry = self._run(r, {
                "tool_name": "Bash",
                "tool_input": {"command": "cargo test"},
                "tool_response": {
                    "exitCode": 0,
                    "output": "running 5 tests\n.....\n\n"
                              "test result: ok. 5 passed; 0 failed\n"},
            })
            self.assertIsNotNone(entry)
            self.assertEqual(
                entry.get("marker_verified"), True,
                f"cargo pair (running N tests + test result: ok) must "
                f"verify: {entry}")


# ---------------------------------------------------------------------------
# D. trust-scan (iter67): undecidable-ok エントリ〔observed かつ
# marker_verified≠true かつ status=ok〕は情報ゼロ＝透明として skip し、
# 走査は最新の decidable エントリ〔src='manual'、または observed かつ
# marker_verified=true〕まで遡って判定を下す。
#   - undecidable-fail〔status=fail〕は従来どおり終端 unverified。
#   - decidable の fp 不一致も従来どおり終端 unverified。
#   - undecidable-ok の透明化は fp 検査より前（stale な undecidable-ok も透明）。
# 現行 read_test_result は undecidable-ok で終端 unverified を返すため、
# 「透明化して古い decidable が勝つ」を期待する系列は RED になる。
# ---------------------------------------------------------------------------


class TestReadTestResultTrustScan(unittest.TestCase):
    """undecidable-ok 透明化の目標意味論を系列で固定する（実装は iter67 Task 2）。"""

    STALE = "a" * 64

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_judge_card", str(ROOT / "scripts" / "build-judge-card.py"))
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def _scratch_repo(self) -> tempfile.TemporaryDirectory:
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=p, check=True)
        subprocess.run(["git", "config", "user.email", "x@y.z"],
                       cwd=p, check=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=p, check=True)
        (p / "f.txt").write_text("seed", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=p, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                       cwd=p, check=True)
        ev = p / ".claude"
        ev.mkdir()
        hooks_dir = p / "hooks"
        hooks_dir.mkdir()
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        for lib in ("patterns.sh", "fingerprint.sh"):
            (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
        return tmp

    def _fp(self, root: Path) -> str:
        return self.mod.current_fingerprint(root)

    def _entry(self, src: str, status: str, fp: str,
               marker_verified="__absent__", cmd: str = "pytest tests/") -> dict:
        """基本形の evidence エントリを1件生成。marker_verified に
        '__absent__' を渡すとキー自体を持たない（v1.6.0 スキーマ相当）。"""
        d = {
            "v": 1, "ts": "2026-07-12T00:00:00Z",
            "src": src, "cmd": cmd, "status": status,
            "payload_sha": "x" * 64, "fp": fp,
        }
        if marker_verified != "__absent__":
            d["marker_verified"] = marker_verified
        return d

    def _write_entries(self, root: Path, entries: list, rotated_split=None):
        """entries は古→新。rotated_split=None なら全件を current ログへ。
        rotated_split=N なら先頭 N 件を .1（rotated）へ、残りを current へ。
        read 側は .1 → current の順で古→新として読む。"""
        cur = root / ".claude" / "evidence-log.jsonl"
        rot = root / ".claude" / "evidence-log.jsonl.1"
        if rotated_split is None:
            cur.write_text(
                "".join(json.dumps(e) + "\n" for e in entries),
                encoding="utf-8")
            return
        old, new = entries[:rotated_split], entries[rotated_split:]
        rot.write_text(
            "".join(json.dumps(e) + "\n" for e in old), encoding="utf-8")
        cur.write_text(
            "".join(json.dumps(e) + "\n" for e in new), encoding="utf-8")

    def test_trusted_green_survives_noise_ok_entry(self):
        """manual green の後ろに no-run な observed/ok/mv=False が積まれても、
        後者は透明で古い manual green が勝つ。

        iter78 契約更新: green を期待する trusted manual エントリの cmd を
        非 pytest（unittest）へスワップ（pytest だと green 制限で transparent 化
        され「trusted green が勝つ」検出力が死ぬ）。noise エントリは pytest ok
        のままでよい — pytest 制限で transparent 化されても「skip される」意味は
        同じ（noise の目的＝decidable green を覆さないこと）で保存される。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", fp, cmd="python3 -m unittest"),
                self._entry("observed", "ok", fp, marker_verified=False,
                            cmd="pytest --collect-only -q"),
            ])
            self.assertEqual(
                self.mod.read_test_result(r), "green",
                "undecidable-ok ノイズが未実装（終端 unverified）＝RED")

    def test_marker_verified_green_survives_noise_ok_entry(self):
        """marker_verified=true の green も後続 no-run ノイズを透過して勝つ。

        iter78 契約更新: green を期待する marker_verified:true エントリの cmd を
        非 pytest（unittest）へスワップ（pytest だと green 制限で transparent 化
        され検出力が死ぬ）。noise（mv=False）は pytest のままで透明維持。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("observed", "ok", fp, marker_verified=True,
                            cmd="python3 -m unittest"),
                self._entry("observed", "ok", fp, marker_verified=False),
            ])
            self.assertEqual(
                self.mod.read_test_result(r), "green",
                "undecidable-ok ノイズが未実装（終端 unverified）＝RED")

    def test_decidable_red_cannot_be_laundered_by_noise_ok_entry(self):
        """decidable red は後続の no-run ノイズで 🟡 に洗浄できない
        （red 洗浄経路の封鎖）。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("observed", "fail", fp, marker_verified=True),
                self._entry("observed", "ok", fp, marker_verified=False),
            ])
            self.assertEqual(
                self.mod.read_test_result(r), "red",
                "透明化が未実装だと red が noise ok で unverified に洗浄＝RED")

    def test_undecidable_fail_stays_terminal_unverified(self):
        """undecidable-fail〔observed/fail/mv≠true〕は透明化せず終端 unverified
        （fail 側の fail-closed は不変）。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", fp),
                self._entry("observed", "fail", fp, marker_verified=False),
            ])
            self.assertEqual(self.mod.read_test_result(r), "unverified")

    def test_transparency_does_not_resurrect_stale_green(self):
        """透明化は古い decidable を"復活"させるが、その decidable 自身が
        stale なら fp 不一致で終端 unverified（stale green を蘇生しない）。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", self.STALE),
                self._entry("observed", "ok", fp, marker_verified=False),
            ])
            self.assertEqual(self.mod.read_test_result(r), "unverified")

    def test_v160_ok_entry_is_transparent_in_sequence(self):
        """marker_verified キー自体を持たない v1.6.0 の observed/ok も
        undecidable-ok として透明（古い manual green が勝つ）。

        iter78 契約更新: green を期待する trusted manual エントリの cmd を
        非 pytest（unittest）へスワップ。v1.6.0 noise（marker キー欠如）は
        pytest のままで透明維持。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", fp, cmd="python3 -m unittest"),
                self._entry("observed", "ok", fp),  # marker_verified 欠如
            ])
            self.assertEqual(
                self.mod.read_test_result(r), "green",
                "キー欠如の undecidable-ok が終端扱い＝RED")

    def test_newest_decidable_red_still_wins(self):
        """最新が decidable red なら（透明化と無関係に）従来どおり red。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", fp),
                self._entry("observed", "fail", fp, marker_verified=True),
            ])
            self.assertEqual(self.mod.read_test_result(r), "red")

    def test_noise_only_log_stays_unverified(self):
        """undecidable-ok だけのログは decidable ゼロ＝unverified
        （透明化で全件消えても silent-green にしない）。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("observed", "ok", fp, marker_verified=False),
                self._entry("observed", "ok", fp, marker_verified=False),
            ])
            self.assertEqual(self.mod.read_test_result(r), "unverified")

    def test_transparency_spans_rotated_log(self):
        """透明化は rotated (.1) 境界をまたぐ：.1 側の古い manual green を
        current 側の undecidable-ok を透過して拾う。

        iter78 契約更新: green を期待する .1 側の trusted manual エントリの cmd を
        非 pytest（unittest）へスワップ。current 側 noise は pytest のまま透明維持。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", fp, cmd="python3 -m unittest"),  # -> .1
                self._entry("observed", "ok", fp, marker_verified=False),  # current
            ], rotated_split=1)
            self.assertEqual(
                self.mod.read_test_result(r), "green",
                "rotated 境界を越えた透明化が未実装＝RED")

    def test_transparency_precedes_fp_check(self):
        """undecidable-ok の透明化は fp 検査より前：最新 observed/ok が
        stale fp でも undecidable-ok として透明化され、古い manual green が勝つ。

        iter78 契約更新: green を期待する trusted manual エントリの cmd を
        非 pytest（unittest）へスワップ。stale noise は pytest のまま透明維持。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", fp, cmd="python3 -m unittest"),
                self._entry("observed", "ok", self.STALE, marker_verified=False),
            ])
            self.assertEqual(
                self.mod.read_test_result(r), "green",
                "stale な undecidable-ok が fp 検査で終端＝RED")

    def test_transparency_does_not_skip_undecidable_fail(self):
        """3段系列（green ← undecidable-fail ← undecidable-ok）: 透明化は
        undecidable-fail を飛び越えない＝noise-ok を skip した先の
        undecidable-fail が終端 unverified（review 1次 角度C の未ピン指摘を固定）。"""
        with self._scratch_repo() as _:
            r = Path(_)
            fp = self._fp(r)
            self._write_entries(r, [
                self._entry("manual", "ok", fp),
                self._entry("observed", "fail", fp, marker_verified=False),
                self._entry("observed", "ok", fp, marker_verified=False),
            ])
            self.assertEqual(self.mod.read_test_result(r), "unverified")


if __name__ == "__main__":
    unittest.main()
