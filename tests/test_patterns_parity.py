#!/usr/bin/env python3
"""AEGIS_TEST_RUNNER_REGEX — bash(grep -E)/python(re) パリティ契約。

パターンは両エンジンで同一判定でなければならない（分類は patterns.sh が
単一ソース、消費者は post-bash.sh=grep -E と build-judge-card.py=re の2系統）。
共有フィクスチャで両エンジンの判定一致と期待値を検証する。
禁止構文: [[:space:]] / \\b（エンジン間で挙動が割れるため）。
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "hooks" / "lib" / "patterns.sh"

# (command, is_test_runner)
FIXTURES = [
    ("python3 -m unittest discover -s tests", True),
    ("python -m unittest tests.test_x -v", True),
    ("pytest tests/ -v", True),
    ("npx vitest run", True),
    ("vitest", True),
    ("npx jest --ci", True),
    ("cargo test --all", True),
    ("go test ./...", True),
    ("npm test", True),
    ("npm run test", True),
    ("npm run test:unit", True),
    ("pnpm test", True),
    ("bun test", True),
    ("yarn test", True),
    ("echo pytest", True),   # 文字列一致は許容（記録側は全実行を保存済み）
    ("git status", False),
    ("ls -la", False),
    ("npm run build", False),
    ("go build ./...", False),
    ("python3 scripts/check_status.py", False),
    ("cargo build", False),
    ("attest something", False),
    ("protest --loud", False),
]


def bash_patterns() -> list[str]:
    out = subprocess.run(
        ["bash", "-c",
         'source "$1"; printf "%s\\n" "${AEGIS_TEST_RUNNER_REGEX[@]}"',
         "_", str(PATTERNS)],
        capture_output=True, text=True, timeout=10, check=True)
    return [l for l in out.stdout.splitlines() if l.strip()]


def grep_match(cmd: str, patterns: list[str]) -> bool:
    for p in patterns:
        r = subprocess.run(["grep", "-Eq", p],
                           input=cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return True
    return False


class TestTestRunnerParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = bash_patterns()

    def test_patterns_exist(self):
        self.assertGreaterEqual(len(self.patterns), 5)

    def test_no_engine_splitting_syntax(self):
        for p in self.patterns:
            self.assertNotIn("[[:", p, f"POSIX class in {p}")
            self.assertNotIn("\\b", p, f"\\b in {p}")

    def test_python_re_compiles(self):
        for p in self.patterns:
            re.compile(p)

    def test_fixtures_python(self):
        compiled = [re.compile(p) for p in self.patterns]
        for cmd, expected in FIXTURES:
            got = any(c.search(cmd) for c in compiled)
            self.assertEqual(got, expected, f"python re: {cmd!r}")

    def test_fixtures_grep(self):
        for cmd, expected in FIXTURES:
            got = grep_match(cmd, self.patterns)
            self.assertEqual(got, expected, f"grep -E: {cmd!r}")


if __name__ == "__main__":
    unittest.main()
