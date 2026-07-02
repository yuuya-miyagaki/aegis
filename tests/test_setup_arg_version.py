#!/usr/bin/env python3
"""iter45 (full-review C2 / C3): bin/setup.sh の引数解析と version stamp。

C2: 引数パーサが `--profile=full`（= 形式）のみ受理し、`--profile full`
    （空白形式）は `*)` に落ちて "Unknown argument" で即死する。CLAUDE.md
    散文は空白形式を使うため doc/impl 不整合。→ パーサを while+shift 2 アーム化
    して両形式対応にする（--profile / --target とも）。

C3: FRAMEWORK_VERSION 取得の `python3 - <<'PY' ... PY` がクォート付き heredoc
    のため `$FRAMEWORK_ROOT` を展開せず python は常に FileNotFoundError → "unknown"。
    grep フォールバックが実値を救出するため機能影響は現状ゼロ＝dead first path。
    → heredoc を argv 渡しにして python 主経路を実際に機能させる（grep は存置）。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SH = ROOT / "bin" / "setup.sh"
MINIMAL_PROFILE = ROOT / "templates" / "profiles" / "minimal.json"
CONTRACT = ROOT / "scripts" / "check_framework_contract.py"


def _framework_version() -> str:
    import re
    m = re.search(r'FRAMEWORK_VERSION\s*=\s*"([^"]+)"', CONTRACT.read_text())
    assert m, "FRAMEWORK_VERSION constant missing"
    return m.group(1)


FRAMEWORK_VERSION = _framework_version()


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(SETUP_SH), *args], capture_output=True, text=True,
    )


class TestC2ArgParserBothForms(unittest.TestCase):
    """C2: --profile / --target を = 形式と空白形式の両方で受理する。"""

    def test_equals_form_still_works(self):
        """回帰: 既存の = 形式は引き続き成功する。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile=minimal", f"--target={proj}"])
            self.assertEqual(r.returncode, 0,
                             f"=-form regressed: {r.stdout[:200]} {r.stderr[:200]}")

    def test_space_form_profile_and_target(self):
        """C2 本丸: --profile minimal --target <dir>（両空白形式）が成功する。

        修正前は `--profile` が `*)` に落ちて "Unknown argument" で rc≠0。
        """
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile", "minimal", "--target", str(proj)])
            self.assertEqual(
                r.returncode, 0,
                f"space-form rejected: stdout={r.stdout[:200]} stderr={r.stderr[:200]}")
            self.assertTrue(
                (proj / ".claude" / ".aegis-install-version").exists(),
                "space-form install did not complete (no version stamp)")

    def test_mixed_form(self):
        """混在: --profile minimal --target=<dir> が成功する。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile", "minimal", f"--target={proj}"])
            self.assertEqual(
                r.returncode, 0,
                f"mixed-form rejected: stdout={r.stdout[:200]} stderr={r.stderr[:200]}")

    def test_profile_missing_value_fails_with_clear_message(self):
        """値欠落（--profile が最終引数）は決定的メッセージで fail-closed。

        修正前は "Unknown argument: --profile"（rc≠0 だがメッセージが別）。
        修正後は "--profile requires a value"。
        """
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run([f"--target={proj}", "--profile"])
            self.assertNotEqual(r.returncode, 0, "missing value must fail")
            self.assertIn(
                "requires a value", (r.stdout + r.stderr),
                f"expected deterministic 'requires a value': {r.stderr[:200]}")

    def test_unknown_arg_still_fails(self):
        """回帰: 不明引数は引き続き fail-closed。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile=minimal", f"--target={proj}", "--bogus"])
            self.assertNotEqual(r.returncode, 0, "unknown arg must fail")
            self.assertIn("Unknown argument", (r.stdout + r.stderr),
                          f"expected 'Unknown argument': {r.stderr[:200]}")

    def test_target_space_form_alone(self):
        """--target だけ空白形式（--profile は = 形式）でも成功する。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile=minimal", "--target", str(proj)])
            self.assertEqual(
                r.returncode, 0,
                f"target space-form rejected: {r.stdout[:200]} {r.stderr[:200]}")

    def test_force_flag_does_not_hang(self):
        """--force（値なしフラグ）が shift され無限ループしない（再 install も成功）。

        while+shift ループで --force アームの shift が欠けると `[ $# -gt 0 ]` が
        減らず無限ループ（ハング）する。timeout で「ハング＝TimeoutExpired＝失敗」
        として検知する（rc≠0 の静かな失敗ではなく）。
        """
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            _run(["--profile=minimal", f"--target={proj}"])  # first install
            r = subprocess.run(
                [str(SETUP_SH), "--profile=minimal", f"--target={proj}", "--force"],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(
                r.returncode, 0,
                f"--force re-install failed: {r.stdout[:200]} {r.stderr[:200]}")

    def test_help_exits_zero_with_usage(self):
        """-h/--help は rc 0 で Usage と空白形式ヒントを出す。"""
        r = subprocess.run([str(SETUP_SH), "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"--help should exit 0: {r.stderr[:200]}")
        out = r.stdout + r.stderr
        self.assertIn("Usage", out, "expected Usage text")
        # review F5: the space-form hint is part of C2's user-facing contract.
        self.assertIn("space form", out,
                      "expected --help to advertise the space form (C2)")

    def test_profile_consumes_flag_lookalike_then_fails_validation(self):
        """value-mistake（review F3 / maint M1）: --profile --force は --force を値に
        取り、profile allowlist 検証で fail-closed（getopt 慣行・spec の許容挙動）。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile", "--force", f"--target={proj}"])
            self.assertNotEqual(r.returncode, 0, "flag-lookalike value must fail")
            self.assertIn("Invalid profile", r.stdout + r.stderr,
                          f"expected allowlist rejection: {r.stderr[:200]}")

    def test_profile_explicit_empty_value_fails_closed(self):
        """review F2: --profile "" (明示空値) は fail-closed（is required）。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile", "", f"--target={proj}"])
            self.assertNotEqual(r.returncode, 0, "explicit empty profile must fail")


class TestC3VersionHeredoc(unittest.TestCase):
    """C3: version heredoc の dead first path を解消し python 主経路を機能させる。"""

    def _heredoc_bodies(self) -> list:
        """bin/setup.sh の全 <<'PY' ... PY ブロックの body（呼出行と終端 PY を除く）。

        iter54 C-2 で heredoc は 1→複数（profile 検証・parse_json_array・
        generate_settings も argv 経由の quoted heredoc に統一）。契約は
        「全 heredoc が argv でパスを受け、$VAR 展開に依存しない」に拡張。
        """
        lines = SETUP_SH.read_text().splitlines()
        starts = [i for i, l in enumerate(lines) if "<<'PY'" in l]
        self.assertGreaterEqual(len(starts), 1, "expected at least one <<'PY' heredoc")
        bodies = []
        for s in starts:
            ends = [i for i in range(s + 1, len(lines)) if lines[i].strip() == "PY"]
            self.assertTrue(ends, f"heredoc terminator 'PY' not found after line {s}")
            bodies.append("\n".join(lines[s + 1:ends[0]]))
        return bodies

    def test_heredoc_uses_argv_not_framework_root_var(self):
        """静的: 全 heredoc body は sys.argv を読み、$FRAMEWORK_ROOT 等の
        シェル変数参照を含まない。

        修正前は body に pathlib.Path("$FRAMEWORK_ROOT/...") があり（クォート
        heredoc 内で非展開＝dead path）、sys.argv は無い。iter54 C-2 で同じ
        不変条件を全 heredoc（profile 検証／parse_json_array／generate_settings）
        に適用（inline `python3 -c "...'$var'..."` は `'` 入りパスで壊れる）。
        """
        for i, body in enumerate(self._heredoc_bodies()):
            self.assertIn("sys.argv", body,
                          f"heredoc #{i} body must read paths from sys.argv")
            self.assertNotIn("$FRAMEWORK_ROOT", body,
                             f"heredoc #{i}: quoted body must not rely on "
                             f"$FRAMEWORK_ROOT (non-expanded = dead path)")
            self.assertNotIn("$TARGET", body,
                             f"heredoc #{i}: quoted body must not rely on $TARGET")

    def test_python_primary_path_resolves_version(self):
        """positive-control: python 主経路が実際に version を返すことの実証。

        仕掛け（fallback 実装への意図的結合・grill-plan 要検討1）: doctored な
        check_framework_contract.py の version 行に末尾コメントで2つ目のクォート
        文字列を置く。grep フォールバックの `sed -E 's/.*"([^"]+)".*/\\1/'` は
        greedy `.*` で **最後の** クォート群（誤値）を拾い、python の anchored
        `re.search(r'FRAMEWORK_VERSION\\s*=\\s*"([^"]+)"')` は **最初の**（正値）を
        拾う。両経路とも rc 0（grep は値を返すので abort しない）なので、RED の
        理由は「abort」ではなく純粋に「どちらの値が stamp に入ったか」になる。

        修正前: python dead → grep が誤値 "0.0.0-grepwrong"。
        修正後: python が正値 "9.9.9-real"。
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            fwroot = tmp_path / "fwroot"
            (fwroot / "bin").mkdir(parents=True)
            (fwroot / "templates" / "profiles").mkdir(parents=True)
            (fwroot / "scripts").mkdir(parents=True)
            shutil.copy(SETUP_SH, fwroot / "bin" / "setup.sh")
            (fwroot / "bin" / "setup.sh").chmod(0o755)
            shutil.copy(MINIMAL_PROFILE, fwroot / "templates" / "profiles" / "minimal.json")
            (fwroot / "scripts" / "check_framework_contract.py").write_text(
                '# fake contract for positive-control\n'
                'FRAMEWORK_VERSION = "9.9.9-real"  # historical default "0.0.0-grepwrong"\n'
            )
            contract = fwroot / "scripts" / "check_framework_contract.py"
            # Self-validate the discriminator is LIVE (review F1): the grep
            # fallback alone MUST extract the WRONG value from this fixture.
            # Without this, a future fixture edit could let grep also yield the
            # right value, and a green stamp would no longer prove python carried
            # the load (false green). This runs setup.sh's exact grep+sed (line
            # ~119) standalone.
            grep_pipeline = (
                r'''grep -E '^FRAMEWORK_VERSION\s*=' "$1" '''
                r'''| sed -E 's/.*"([^"]+)".*/\1/' | head -1'''
            )
            grep_only = subprocess.run(
                ["bash", "-c", grep_pipeline, "_", str(contract)],
                capture_output=True, text=True,
            )
            self.assertEqual(
                grep_only.stdout.strip(), "0.0.0-grepwrong",
                "discriminator not live: grep fallback would NOT have produced a "
                "wrong value, so a green stamp cannot prove python carried the load")
            proj = tmp_path / "proj"
            r = subprocess.run(
                [str(fwroot / "bin" / "setup.sh"),
                 "--profile=minimal", f"--target={proj}"],
                capture_output=True, text=True,
            )
            self.assertEqual(
                r.returncode, 0,
                f"fake-root setup aborted (RED reason must be value, not abort): "
                f"stdout={r.stdout[:300]} stderr={r.stderr[:300]}")
            stamp = proj / ".claude" / ".aegis-install-version"
            self.assertTrue(stamp.exists(), "version stamp missing")
            self.assertEqual(
                stamp.read_text().strip(), "9.9.9-real",
                "python primary path did not carry the load (grep fallback's "
                "wrong value leaked → heredoc still dead)")

    def test_real_install_stamps_actual_version(self):
        """回帰: 実 bin/setup.sh の install は実 version を stamp する。"""
        with tempfile.TemporaryDirectory() as tmp:
            proj = pathlib.Path(tmp) / "proj"
            r = _run(["--profile=minimal", f"--target={proj}"])
            self.assertEqual(r.returncode, 0, f"setup failed: {r.stderr[:200]}")
            stamp = proj / ".claude" / ".aegis-install-version"
            self.assertEqual(stamp.read_text().strip(), FRAMEWORK_VERSION)


if __name__ == "__main__":
    unittest.main()
