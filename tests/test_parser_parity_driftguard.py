#!/usr/bin/env python3
"""iter66: bash↔python frontmatter 読取意味論の parity drift-guard。

契約 = 「frontmatter 内の最初の値」。fixture ごとに bash 読点と python 読点の
返値一致をアサートする。どちらかが将来 drift したらここが赤になる。
bare/unterminated は bash 側のみの挙動ピン（python は STATUS frontmatter 専用）。
"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "frontmatter.sh"
_spec = importlib.util.spec_from_file_location(
    "check_status", ROOT / "scripts" / "check_status.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


def bash_value(path: Path, key: str) -> str:
    r = subprocess.run(
        ["bash", "-c", f"source '{LIB}' && frontmatter_value '{path}' '{key}'"],
        capture_output=True, text=True, check=False)
    return r.stdout.strip()


def bash_gate(path: Path, gate: str) -> str:
    r = subprocess.run(
        ["bash", "-c", f"source '{LIB}' && gate_value '{path}' '{gate}'"],
        capture_output=True, text=True, check=False)
    return r.stdout.strip()


def py_value(text: str, key: str) -> str:
    fm = cs.extract_frontmatter(text)
    if fm is None:
        return ""
    v = cs.extract_scalar_value(fm, key)
    return "" if v is None else v


def py_gate(text: str, gate: str) -> str:
    fm = cs.extract_frontmatter(text)
    if fm is None:
        return ""
    return cs.extract_approval_map(fm).get(gate, "")


class TestParserParity(unittest.TestCase):
    def _file(self, d: str, text: str) -> Path:
        p = Path(d) / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def assert_parity(self, text: str, key: str, expected: str):
        with tempfile.TemporaryDirectory() as d:
            p = self._file(d, text)
            b, py = bash_value(p, key), py_value(text, key)
            self.assertEqual(b, py, f"bash={b!r} python={py!r} for {key}")
            self.assertEqual(b, expected)

    def assert_gate_parity(self, text: str, gate: str, expected: str):
        with tempfile.TemporaryDirectory() as d:
            p = self._file(d, text)
            b, py = bash_gate(p, gate), py_gate(text, gate)
            self.assertEqual(b, py, f"bash={b!r} python={py!r} for {gate}")
            self.assertEqual(b, expected)

    def test_a_duplicate_key_in_frontmatter(self):
        self.assert_parity(
            "---\ntask_size: M\ntask_size: S\n---\nbody\n", "task_size", "M")

    def test_a_duplicate_gate_key(self):
        self.assert_gate_parity(
            "---\ngate_approvals:\n  review: approved\n  review: pending\n"
            "---\nbody\n", "review", "approved")

    def test_b_quoted_and_unquoted_mixed(self):
        # F-1 の再発防止ピン
        self.assert_parity(
            '---\ntask_size: M\ntask_size: "S"\n---\nbody\n', "task_size", "M")

    def test_c_body_spoof_line(self):
        self.assert_parity(
            "---\ntask_size: M\n---\nbody\ntask_size: S\n", "task_size", "M")
        self.assert_parity(
            "---\nmode: Dev\n---\nbody\ntask_size: S\n", "task_size", "")

    def test_d_gate_section_missing_body_block_ignored(self):
        # F-2 の再発防止ピン
        self.assert_gate_parity(
            "---\nmode: Dev\n---\nbody\ngate_approvals:\n  review: approved\n",
            "review", "")

    def test_e_bare_snapshot_bash_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("task_type: framework\n", encoding="utf-8")
            self.assertEqual(bash_value(p, "task_type"), "framework")

    def test_f_unterminated_frontmatter_both_absent(self):
        text = "---\ntask_size: S\nno close\n"
        with tempfile.TemporaryDirectory() as d:
            p = self._file(d, text)
            self.assertEqual(bash_value(p, "task_size"), "")
            self.assertEqual(py_value(text, "task_size"), "")


if __name__ == "__main__":
    unittest.main()
