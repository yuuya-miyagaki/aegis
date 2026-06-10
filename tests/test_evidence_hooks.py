#!/usr/bin/env python3
"""E1 観測 hook の実発火テスト（post-bash-observe.sh / post-bash.sh 失敗側）。"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_REL = ".claude/evidence-log.jsonl"


def fire(script: str, payload: dict, root: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["AEGIS_ROOT_OVERRIDE"] = str(root)
    proc = subprocess.run(
        ["bash", str(ROOT / "hooks" / script)],
        input=json.dumps(payload), capture_output=True, text=True,
        timeout=60, env=env)
    return proc.returncode, proc.stdout


def make_repo(d: Path) -> None:
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "init"], check=True)


def bash_payload(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd},
            "tool_response": {"exitCode": 0}}


class TestPostBashObserve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def test_records_ok_and_allows(self):
        rc, out = fire("post-bash-observe.sh",
                       bash_payload("python3 -m unittest"), self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), {})  # emit_allow
        row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["cmd"], "python3 -m unittest")

    def test_raw_garbage_input_still_allows_rc0(self):
        env = os.environ.copy()
        env["AEGIS_ROOT_OVERRIDE"] = str(self.root)
        proc = subprocess.run(
            ["bash", str(ROOT / "hooks" / "post-bash-observe.sh")],
            input="garbage not json", capture_output=True, text=True,
            timeout=60, env=env)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout), {})


class TestPostBashFailureRecords(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_hook_records_fail_status(self):
        rc, _ = fire("post-bash.sh", bash_payload("pytest tests/"), self.root)
        self.assertEqual(rc, 0)
        row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["cmd"], "pytest tests/")


if __name__ == "__main__":
    unittest.main()
