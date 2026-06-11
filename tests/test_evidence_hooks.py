#!/usr/bin/env python3
"""E1 観測 hook の実発火テスト（post-bash-observe.sh / post-bash.sh 失敗側）。"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_REL = ".claude/evidence-log.jsonl"


def _load_judge():
    spec = importlib.util.spec_from_file_location(
        "judge_e2e", ROOT / "scripts" / "build-judge-card.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


judge = _load_judge()


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


class TestPostBashQuoteMask(unittest.TestCase):
    """post-bash.sh（grep 消費者）のクォートマスク（T1 v1.5.2）:
    クォート内ランナー言及の失敗では ReAct ヒントを出さず（emit_allow {}）、
    実ランナー失敗では従来どおり出す。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_quoted_mention_failure_emits_no_react_hint(self):
        rc, out = fire("post-bash.sh",
                       bash_payload('grep -E "(unittest|pytest)" missing.txt'),
                       self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), {})

    def test_real_runner_failure_still_emits_react_hint(self):
        rc, out = fire("post-bash.sh", bash_payload("pytest tests/"), self.root)
        self.assertEqual(rc, 0)
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ReAct", ctx)


class TestObserveToJudgeEndToEnd(unittest.TestCase):
    """grill-code 🟡1: 「観測した ok が green になる」主契約の結合固定。

    evidence.sh が記録する fp（書き手）と judge.current_fingerprint（読み手）
    の一致を、ログ手書き注入ではなく hook 実発火→判定で検証する。fire() の
    cwd は framework root・記録対象は tmp repo なので、書き手が誤った root
    （$PWD 等）の fp を書く変異はここで落ちる。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        shutil.copytree(ROOT / "hooks" / "lib", self.root / "hooks" / "lib")

    def tearDown(self):
        self.tmp.cleanup()

    def test_observed_ok_certifies_green(self):
        rc, _ = fire("post-bash-observe.sh",
                     bash_payload("python3 -m unittest discover -s tests"),
                     self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_observed_failure_certifies_red(self):
        rc, _ = fire("post-bash.sh",
                     bash_payload("python3 -m unittest discover -s tests"),
                     self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_code_change_after_observation_is_unverified(self):
        fire("post-bash-observe.sh", bash_payload("pytest"), self.root)
        (self.root / "app.py").write_text("print(1)\n", encoding="utf-8")
        self.assertEqual(judge.read_test_result(self.root), "unverified")


if __name__ == "__main__":
    unittest.main()
