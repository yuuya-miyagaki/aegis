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
    # --- T2 v1.5.2: 入れ子サブシェル（unverified 縮小、green 偽装には使えない）---
    ("((pytest))", True),
    ("( (vitest run))", True),
    # 閉じ忘れクォート＝マスク不能な不正形はアンカーが受け皿（defense-in-depth）
    ('grep "(pytest x', False),
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


EVIDENCE_LIB = ROOT / "hooks" / "lib" / "evidence.sh"


def run_is_test_runner_cmd(cmd: str) -> bool:
    """evidence.sh の is_test_runner_cmd 実関数（hot-path recorder が使う・単一
    sed -e -e ＋単一 grep -e -e 実装）を呼ぶ。raw cmd（改行含む）を stdin で渡し、
    関数内部の正規化（tr+sed マスク）ごと検証する。"""
    script = 'source "%s"; is_test_runner_cmd "$(cat)"' % EVIDENCE_LIB
    r = subprocess.run(["bash", "-c", script], input=cmd,
                       capture_output=True, text=True, timeout=30, check=True)
    return r.stdout.strip() == "true"


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

    def test_fixtures_is_test_runner_cmd(self):
        """M4: evidence.sh の is_test_runner_cmd 実関数（hot-path recorder が使う・
        単一 sed -e -e ＋単一 grep -e -e 実装）を canonical FIXTURES 全件で判定し、
        reader/旧2連パイプ実装と同一分類であることを直接ピン。「単一 sed は2連
        パイプと byte 等価」の主張を、緑偽装防止の肝（'"echo" pytest'→False・
        エスケープ quote・入れ子サブシェル）を含む全形で実証する。万一どこかで
        分岐すれば fail-closed だが false-yellow（UX 劣化）として即検出する。"""
        for cmd, expected in FIXTURES:
            self.assertEqual(run_is_test_runner_cmd(cmd), expected,
                             f"is_test_runner_cmd: {cmd!r}")


def bash_array(name: str) -> list[str]:
    out = subprocess.run(
        ["bash", "-c",
         'source "$1"; printf "%s\\n" "${' + name + '[@]}"',
         "_", str(PATTERNS)],
        capture_output=True, text=True, timeout=10, check=True)
    return [l for l in out.stdout.splitlines() if l.strip()]


class TestMarkerZeroRunParity(unittest.TestCase):
    """iter71 review F-2 (仕様/敵対角度): AEGIS_TEST_PASS_MARKER_REGEX と
    AEGIS_TEST_ZERO_RUN_REGEX も grep -E ∩ python-re parity 契約下に置く。
    iter71 で bracket 内の `\\t` をリテラル TAB へ修正した（BSD grep -E は `\\t`
    を展開しない・[[:space:]] は parity 違反）ため、TAB/space 両表現で両エンジンの
    判定が一致することをピンする。従来 parity テストは RUNNER_REGEX のみ対象だった。"""

    @classmethod
    def setUpClass(cls):
        cls.markers = bash_array("AEGIS_TEST_PASS_MARKER_REGEX")
        cls.zeroruns = bash_array("AEGIS_TEST_ZERO_RUN_REGEX")

    def _both_engines(self, patterns, text):
        py = any(re.compile(p).search(text) for p in patterns)
        gr = grep_match(text, patterns)
        return py, gr

    def test_arrays_nonempty(self):
        self.assertGreaterEqual(len(self.markers), 3)
        self.assertGreaterEqual(len(self.zeroruns), 3)

    def test_no_engine_splitting_syntax(self):
        for p in self.markers + self.zeroruns:
            self.assertNotIn("[[:", p, f"POSIX class in {p}")
            self.assertNotIn("\\b", p, f"\\b in {p}")

    def test_python_re_compiles(self):
        for p in self.markers + self.zeroruns:
            re.compile(p)

    def test_marker_tab_space_parity(self):
        # TAB と space 両表現で go/jest/vitest STRONG marker がマッチし、grep -E と
        # python re が同一判定であること。
        fixtures = [
            ("ok  \texample.com/pkg\t0.123s", True),   # go TAB 区切り
            ("ok  example.com/pkg  0.123s", True),      # go space 区切り
            ("Tests:\t3 passed, 3 total", True),        # jest TAB
            ("Tests:       3 passed, 3 total", True),   # jest space
            ("Test Files\t1 passed", True),             # vitest TAB
            ("Tests:       2 skipped, 3 passed, 5 total", True),  # jest skipped 混在（iter72 緩和）
            (" Test Files  1 passed (1)", True),        # vitest インデント（iter72 緩和）
            ("nothing to see here", False),
        ]
        for text, expected in fixtures:
            py, gr = self._both_engines(self.markers, text)
            self.assertEqual(py, gr, f"engine split (marker): {text!r} py={py} grep={gr}")
            self.assertEqual(py, expected, f"marker expected {expected}: {text!r}")

    def test_zerorun_tab_space_parity(self):
        fixtures = [
            ("Tests:\t0 passed, 0 total", True),        # jest zero TAB
            ("Tests:       0 passed, 0 total", True),   # jest zero space
            ("Test Files\t0 passed", True),             # vitest zero TAB
            ("Tests:       5 passed, 5 total", False),  # 非 zero は不一致
        ]
        for text, expected in fixtures:
            py, gr = self._both_engines(self.zeroruns, text)
            self.assertEqual(py, gr, f"engine split (zerorun): {text!r} py={py} grep={gr}")
            self.assertEqual(py, expected, f"zerorun expected {expected}: {text!r}")


class TestCountFamilyParity(unittest.TestCase):
    """iter72 (SF-014 count proof): AEGIS_TEST_COUNT_FAMILIES の DETECT/EXEC/
    MINUS も grep -E ∩ python-re parity 契約下に置く（5 フィールド `|||` 形式・
    共通部分集合・fixture 両エンジン一致）。"""

    @classmethod
    def setUpClass(cls):
        cls.entries = bash_array("AEGIS_TEST_COUNT_FAMILIES")

    def test_entry_format_five_fields(self):
        self.assertGreaterEqual(len(self.entries), 6)
        for e in self.entries:
            parts = e.split("|||")
            self.assertEqual(len(parts), 5, f"NAME|||DETECT|||EXEC|||MODE|||MINUS: {e!r}")
            name, detect, exec_pat, mode, _minus = parts
            self.assertTrue(name, e)
            self.assertTrue(detect, e)
            self.assertTrue(exec_pat, e)
            self.assertIn(mode, ("sum", "lines"), e)

    def test_regexes_common_subset_and_compile(self):
        for e in self.entries:
            _n, detect, exec_pat, _m, minus = e.split("|||")
            pats = [detect, exec_pat] + ([minus] if minus else [])
            for p in pats:
                self.assertNotIn("[[:", p, f"POSIX class in {p}")
                self.assertNotIn("\\b", p, f"\\b in {p}")
                re.compile(p)

    def test_detect_fixture_parity(self):
        # (text, family-that-must-detect-or-None, expected)
        fixtures = [
            ("Ran 2 tests in 0.000s", "unittest", True),
            ("=========== 3 passed in 0.42s ===========", "pytest", True),
            ("Tests:       2 skipped, 3 passed, 5 total", "jest", True),
            ("      Tests  2 passed (2)", "vitest", True),
            ("test result: ok. 0 passed; 0 failed; 3 ignored", "cargo", True),
            ("--- SKIP: TestA (0.00s)", "go-verbose", True),
            # iter72 review 強度F-1: literal-TAB 形も DETECT が両エンジン一致すること
            ("Tests:\t1 failed, 2 passed, 3 total", "jest", True),   # jest TAB 区切り
            ("\tTests  2 passed (2)", "vitest", True),               # vitest TAB インデント
            ("      Tests  3 skipped (3)", "vitest", True),          # vitest all-skip 行も DETECT
            ("ok  \texample.com/pkg\t0.012s", None, False),  # 素の go は族なし
        ]
        by_name = {e.split("|||")[0]: e.split("|||")[1] for e in self.entries}
        for text, fam, expected in fixtures:
            for name, detect in by_name.items():
                py = re.compile(detect).search(text) is not None
                gr = grep_match(text, [detect])
                self.assertEqual(py, gr, f"engine split ({name}): {text!r}")
                if fam is not None and name == fam:
                    self.assertEqual(py, expected, f"{name} detect: {text!r}")
                if fam is None:
                    self.assertFalse(py, f"{name} must NOT detect: {text!r}")

    def test_exec_minus_fixture_parity(self):
        # 強度F-4: EXEC/MINUS も grep -E と python re で同一挙動であることを
        # fixture で pin（従来は DETECT のみ両エンジン照合だった）。
        by_name = {e.split("|||")[0]: e.split("|||") for e in self.entries}
        # (family, field_index, text, expected_match)  field: 2=EXEC, 4=MINUS
        fixtures = [
            ("unittest", 2, "Ran 5 tests in 0.01s", True),
            ("cargo", 2, "test result: ok. 5 passed; 0 failed", True),
            ("cargo", 2, "test result: ok. 0 passed; 0 failed; 3 ignored", True),
            ("unittest", 4, "OK (skipped=2)", True),
            ("unittest", 4, "config: skipped=10", False),
            ("unittest", 4, "unskipped=3", False),
        ]
        for fam, idx, text, expected in fixtures:
            pat = by_name[fam][idx]
            py = re.compile(pat).search(text) is not None
            gr = grep_match(text, [pat])
            self.assertEqual(py, gr, f"engine split ({fam}[{idx}]): {text!r} py={py} grep={gr}")
            self.assertEqual(py, expected, f"{fam}[{idx}] expected {expected}: {text!r}")


class TestDequoteNormalize(unittest.TestCase):
    """iter75 SF-017: aegis_dequote_normalize — quote/backslash/${IFS} を畳んで
    deny 系 hook が生 regex 判定できるよう正規化する共有 helper（純 bash・parser なし）。
    r""m / g""it a""dd .e""nv / r\\m / rm${IFS}-rf / git${IFS}add .env の難読化を捕捉し、
    非難読化コマンドは不変。brace 展開（SF-019 残余）は畳まないことを pin する。"""

    def test_dequote_normalize(self):
        def norm(s):
            script = 'source hooks/lib/patterns.sh; printf %s "$(aegis_dequote_normalize "$1")"'
            return subprocess.run(["bash", "-c", script, "_", s], cwd=ROOT,
                                  capture_output=True, text=True).stdout
        self.assertEqual(norm('r""m -rf /x'), 'rm -rf /x')
        self.assertEqual(norm('g""it a""dd .e""nv'), 'git add .env')
        self.assertEqual(norm('r\\m -rf'), 'rm -rf')
        self.assertEqual(norm('rm${IFS}-rf /x'), 'rm -rf /x')          # ${IFS} → 空白（grill 致命1）
        self.assertEqual(norm('git${IFS}add .env'), 'git add .env')    # secret bypass 綴り
        self.assertEqual(norm('rm -rf /x'), 'rm -rf /x')               # 非難読化は不変
        # iter75 fix-forward F2: backslash-newline（行継続）と残改行の畳み込み
        self.assertEqual(norm('git add \\\n.env'), 'git add .env')     # 行継続 → 実コマンド再構成
        self.assertEqual(norm('rm \\\n-rf'), 'rm -rf')
        self.assertEqual(norm('gi\\\nt add'), 'git add')               # 語中の行継続
        self.assertEqual(norm('a\nb'), 'a b')                          # 裸の改行 → 空白
        # 残余（SF-019・iter75 では畳まない＝不変を pin）:
        self.assertEqual(norm('r{,}m -rf'), 'r{,}m -rf')               # brace 展開は非対応（構造化 argv 待ち）


class TestMaskScopeBoundary(unittest.TestCase):
    """マスクは分類専用 — deny 系 hook に波及していないこと（fail-open 防止）。"""

    def test_deny_hooks_do_not_reference_strip_patterns(self):
        for h in ("check-destructive.sh", "check-runtime-state.sh",
                  "check-secrets.sh"):
            text = (ROOT / "hooks" / h).read_text(encoding="utf-8")
            self.assertNotIn("AEGIS_TR_STRIP", text, h)


if __name__ == "__main__":
    unittest.main()
