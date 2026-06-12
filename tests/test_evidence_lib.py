#!/usr/bin/env python3
"""evidence.sh — evidence-log 追記/ローテーションの契約テスト。

記録は fail-open（常に rc=0・本体を止めない）。スキーマ:
{"v":1,"ts":...,"src":"observed","cmd":...,"status":"ok|fail",
 "payload_sha":...,"fp":...}
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "evidence.sh"
LOG_REL = ".claude/evidence-log.jsonl"


def run_append(root: Path, status: str, payload: str,
               env_extra: dict | None = None) -> int:
    import os
    env = os.environ.copy()
    env.update(env_extra or {})
    script = (f'source "{LIB}"; '
              f'append_evidence "{root}" {status} "$(cat)"')
    proc = subprocess.run(["bash", "-c", script], input=payload,
                          capture_output=True, text=True, timeout=60, env=env)
    return proc.returncode


def run_rotate(root: Path, env_extra: dict | None = None) -> int:
    import os
    env = os.environ.copy()
    env.update(env_extra or {})
    script = f'source "{LIB}"; rotate_evidence_log "{root}"'
    proc = subprocess.run(["bash", "-c", script],
                          capture_output=True, text=True, timeout=60, env=env)
    return proc.returncode


def make_repo(d: Path) -> None:
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "init"], check=True)


def payload_for(cmd: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})


class TestAppendEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def read_lines(self):
        return [json.loads(line) for line in
                self.log.read_text(encoding="utf-8").splitlines() if line]

    def test_append_ok_writes_valid_json_line(self):
        rc = run_append(self.root, "ok", payload_for("python3 -m unittest"))
        self.assertEqual(rc, 0)
        rows = self.read_lines()
        self.assertEqual(len(rows), 1)
        d = rows[0]
        self.assertEqual(d["v"], 1)
        self.assertEqual(d["src"], "observed")
        self.assertEqual(d["status"], "ok")
        self.assertEqual(d["cmd"], "python3 -m unittest")
        self.assertRegex(d["payload_sha"], r"^[0-9a-f]{64}$")
        self.assertRegex(d["fp"], r"^[0-9a-f]{64}$")
        self.assertIn("T", d["ts"])

    def test_append_fail_status(self):
        run_append(self.root, "fail", payload_for("pytest"))
        self.assertEqual(self.read_lines()[0]["status"], "fail")

    def test_cmd_with_quotes_and_newlines_stays_valid_json(self):
        cmd = 'echo "a\nb"\tc\\d'
        run_append(self.root, "ok", payload_for(cmd))
        rows = self.read_lines()  # json.loads が通ること自体が検証
        self.assertEqual(len(rows), 1)

    def test_cmd_truncated_to_500(self):
        run_append(self.root, "ok", payload_for("x" * 1000))
        self.assertEqual(len(self.read_lines()[0]["cmd"]), 500)

    def test_broken_payload_still_rc0_and_appends(self):
        rc = run_append(self.root, "ok", "not-json{{{")
        self.assertEqual(rc, 0)
        rows = self.read_lines()
        self.assertEqual(rows[0]["cmd"], "")  # コマンド抽出不能でも記録は残る

    def test_append_is_appending(self):
        run_append(self.root, "ok", payload_for("a"))
        run_append(self.root, "fail", payload_for("b"))
        self.assertEqual([r["cmd"] for r in self.read_lines()], ["a", "b"])


class TestRotate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def test_rotate_creates_empty_file_when_absent(self):
        rc = run_rotate(self.root)
        self.assertEqual(rc, 0)
        self.assertTrue(self.log.is_file())
        self.assertEqual(self.log.read_text(encoding="utf-8"), "")

    def test_rotate_keeps_small_file(self):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_text('{"v":1}\n')
        run_rotate(self.root)
        self.assertEqual(self.log.read_text(encoding="utf-8"), '{"v":1}\n')
        self.assertFalse((self.root / (LOG_REL + ".1")).exists())

    def test_rotate_moves_oversized_to_dot1(self):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_text('{"v":1}\n' * 10)
        run_rotate(self.root, {"AEGIS_EVIDENCE_MAX_BYTES": "10"})
        self.assertTrue((self.root / (LOG_REL + ".1")).is_file())
        self.assertEqual(self.log.read_text(encoding="utf-8"), "")


class TestSessionStartRotates(unittest.TestCase):
    def test_session_start_touches_evidence_log(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_repo(root)
            (root / "docs").mkdir()
            (root / "docs" / "STATUS.md").write_text(
                "---\nmode: Dev\nphase: plan\nnext_action: x\n---\n")
            (root / "hooks").mkdir()
            (root / "hooks" / "lib").mkdir()
            for f in ("emit.sh", "frontmatter.sh", "extract-input.sh",
                      "fingerprint.sh", "evidence.sh", "patterns.sh",
                      "phase-skills.sh"):
                (root / "hooks" / "lib" / f).write_bytes(
                    (ROOT / "hooks" / "lib" / f).read_bytes())
            (root / "hooks" / "session-start.sh").write_bytes(
                (ROOT / "hooks" / "session-start.sh").read_bytes())
            proc = subprocess.run(
                ["bash", str(root / "hooks" / "session-start.sh")],
                input="{}", capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0)
            self.assertTrue((root / LOG_REL).is_file())


if __name__ == "__main__":
    unittest.main()
