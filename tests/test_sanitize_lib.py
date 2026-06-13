#!/usr/bin/env python3
"""Unit tests for hooks/lib/sanitize.sh::aegis_sanitize_field.

Neutralizes untrusted project free text (STATUS.md blockers/next_action,
LEARNINGS.md) before it is injected into a hook's additionalContext.

Run: python3 -m unittest tests.test_sanitize_lib -v
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAN = ROOT / "hooks" / "lib" / "sanitize.sh"


def san(value: str, maxlen: int | None = None) -> str:
    call = 'aegis_sanitize_field "$1"' + (f" {maxlen}" if maxlen else "")
    script = f'source "{SAN}"\n{call}\n'
    r = subprocess.run(["bash", "-c", script, "_", value],
                       capture_output=True, text=True)
    return r.stdout


class TestSanitize(unittest.TestCase):
    def test_strips_brackets_and_tags(self):
        self.assertEqual(san("<script>[end]ok"), "scriptendok")

    def test_collapses_newlines_and_tabs(self):
        self.assertEqual(san("a\nb\tc"), "a b c")

    def test_strips_control_bytes(self):
        out = subprocess.run(
            ["bash", "-c",
             f'source "{SAN}"; v="$(printf \'a\\001b\')"; aegis_sanitize_field "$v"'],
            capture_output=True, text=True).stdout
        self.assertNotIn("\x01", out)
        self.assertEqual(out, "a b")

    def test_truncates_to_maxlen_ascii(self):
        out = san("x" * 500, 50)
        self.assertTrue(out.startswith("x" * 50))
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(len(out.replace("…", "").encode()), 50)

    def test_truncates_multibyte_safely(self):
        """致命1: 日本語(3B/字)を byte-cap しても char を割らず valid UTF-8。"""
        jp = "あ" * 100  # 300 bytes
        out = subprocess.run(
            ["bash", "-c", f'source "{SAN}"; aegis_sanitize_field "$1" 50', "_", jp],
            capture_output=True).stdout  # bytes
        decoded = out.decode("utf-8")  # 不正 UTF-8 ならここで例外=テスト失敗
        body = decoded.rstrip("…")
        self.assertTrue(body and jp.startswith(body))   # 入力の prefix（割れ無し）
        self.assertLessEqual(len(out), 50 + len("…".encode()))  # byte 予算内

    def test_squeezes_and_trims(self):
        self.assertEqual(san("   a    b   "), "a b")

    def test_short_value_unchanged(self):
        self.assertEqual(san("short text", 200), "short text")

    def test_empty_value(self):
        self.assertEqual(san("", 200), "")


if __name__ == "__main__":
    unittest.main()
