#!/usr/bin/env python3
"""AEGIS_TEST_RUNNER_REGEX — bash(grep -E)/python(re) パリティ契約。

パターンは両エンジンで同一判定でなければならない（分類は patterns.sh が
単一ソース、消費者は post-bash.sh=grep -E と build-judge-card.py=re の2系統）。
共有フィクスチャで両エンジンの判定一致と期待値を検証する。
禁止構文: [[:space:]] / \\b（エンジン間で挙動が割れるため）。
照合前パイプライン: 改行→';' ＋ クォート span→Q 置換（DQ→SQ 順、T1 v1.5.2）。
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "hooks" / "lib" / "patterns.sh"

# (command, is_test_runner) — 消費者は照合前に改行を ';' に正規化する
# （post-bash.sh: tr '\n' ';' ／ build-judge-card.py: cmd.replace("\n", ";")）。
# 本テストも同じ正規化を適用してから両エンジンで照合する。
FIXTURES = [
    ("python3 -m unittest discover -s tests", True),
    ("python -m unittest tests.test_x -v", True),
    ("pytest tests/ -v", True),
    ("python3 -m pytest -x", True),
    ("python -m pytest", True),
    ("npx vitest run", True),
    ("bunx vitest run", True),
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
    ("cd app && vitest", True),
    ("CI=1 pytest -x", True),
    ("FOO=bar BAZ=qux jest", True),
    ("uv run pytest", True),
    ("poetry run pytest tests/", True),
    ("echo build done\nvitest run", True),   # 正規化後の ';' 境界で一致
    ("(pytest)", True),                       # サブシェル先頭
    ("cd app && (vitest run)", True),         # 区切り直後のサブシェル
    # v1.5.1 grill-code 🟡-1: '(' はコマンド位置直後のみ。クォート内グループ
    # 正規表現（grep -E "(pytest|...)" は不一致時 rc=1）が false-RED にならない
    ('grep -E "(pytest|unittest)" log.txt', False),
    ('grep "(vitest" src/a.ts', False),
    # v1.5.1 で意図的に反転（コマンド位置アンカー）: 引数・echo 言及は分類しない
    ("echo pytest", False),
    ("grep vitest package.json", False),
    ("cat jest.config.js", False),
    ("echo done\ngrep pytest log.txt", False),
    # 受容済みの取りこぼし（fail-closed 方向）: ラッパー形は分類されない
    ("time pytest", False),
    ('bash -c "pytest"', False),
    ("git status", False),
    ("ls -la", False),
    ("npm run build", False),
    ("go build ./...", False),
    ("python3 scripts/check_status.py", False),
    ("cargo build", False),
    ("attest something", False),
    ("protest --loud", False),
    # --- T1 v1.5.2: クォートマスク（"…"/'…' → Q 置換）---
    # false-RED 根治（v1.5.1 ではクォート内 |runner / ; runner が一致していた）
    ('grep -E "(unittest|pytest)" missing.txt', False),
    ('grep "foo; pytest" missing.txt', False),
    ('grep "a\\" ; pytest" log.txt', False),   # escaped-quote: \\. が \" を吸収
    # 不変ピン（マスク後も先頭ランナーは残る／クォート起動は従来どおり不一致）
    ('pytest "tests/foo bar"', True),
    ('npx "vitest"', False),
    ('echo ""; pytest', True),
    # 反転 fixture（grill A 🔴-1）: Q「置換」を「削除」に revert すると
    # ' pytest' に縮退して True 化＝green 偽装。この行が RED で封鎖する。
    ('"echo" pytest', False),
    # 受容残余（grill A 🟡-2）: 混在クォート横断は unverified=fail-closed 方向
    ("echo 'a\"b'; pytest \"x\"", False),
]


def normalize_py(cmd: str, strips: list[re.Pattern]) -> str:
    """消費者（build-judge-card.py）と同一の正規化: 改行→';'、
    クォート span→Q 置換（DQ→SQ の順は fixtures でピン留めする規約）。"""
    s = cmd.replace("\n", ";")
    for p in strips:
        s = p.sub("Q", s)
    return s


def normalize_sed(cmd: str, strips: list[str]) -> str:
    """消費者（post-bash.sh）と同一の tr+sed パイプラインを実走する。"""
    script = ('printf %s "$1" | tr "\\n" ";" '
              '| sed -E "s/$2/Q/g" | sed -E "s/$3/Q/g"')
    r = subprocess.run(["bash", "-c", script, "_", cmd, strips[0], strips[1]],
                       capture_output=True, text=True, timeout=10, check=True)
    return r.stdout


def bash_strip_patterns() -> list[str]:
    out = subprocess.run(
        ["bash", "-c",
         'source "$1"; printf "%s\\n%s\\n" '
         '"$AEGIS_TR_STRIP_DQ" "$AEGIS_TR_STRIP_SQ"',
         "_", str(PATTERNS)],
        capture_output=True, text=True, timeout=10, check=True)
    return [l for l in out.stdout.splitlines() if l.strip()]


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
        cls.strips_raw = bash_strip_patterns()
        cls.strips = [re.compile(p) for p in cls.strips_raw]

    def test_patterns_exist(self):
        self.assertGreaterEqual(len(self.patterns), 5)

    def test_strip_patterns_exist_and_sed_safe(self):
        # DQ→SQ の 2 本。'/' を含まない＝sed s/// デリミタ安全（T1 v1.5.2）。
        self.assertEqual(len(self.strips_raw), 2)
        for p in self.strips_raw:
            self.assertNotIn("/", p)

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
            s = normalize_py(cmd, self.strips)
            got = any(c.search(s) for c in compiled)
            self.assertEqual(got, expected, f"python re: {cmd!r} -> {s!r}")

    def test_fixtures_grep(self):
        for cmd, expected in FIXTURES:
            s = normalize_sed(cmd, self.strips_raw)
            got = grep_match(s, self.patterns)
            self.assertEqual(got, expected, f"grep -E: {cmd!r} -> {s!r}")

    def test_mask_engines_agree(self):
        # sed -E と python re のマスク結果バイト一致（12+ 形、grill 実測の恒久化）。
        for cmd, _ in FIXTURES:
            self.assertEqual(normalize_py(cmd, self.strips),
                             normalize_sed(cmd, self.strips_raw),
                             f"mask parity: {cmd!r}")


class TestMaskScopeBoundary(unittest.TestCase):
    """マスクは分類専用 — deny 系 hook に波及していないこと（fail-open 防止）。"""

    def test_deny_hooks_do_not_reference_strip_patterns(self):
        for h in ("check-destructive.sh", "check-control-plane.sh",
                  "check-secrets.sh"):
            text = (ROOT / "hooks" / h).read_text(encoding="utf-8")
            self.assertNotIn("AEGIS_TR_STRIP", text, h)


if __name__ == "__main__":
    unittest.main()
