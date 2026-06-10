#!/usr/bin/env python3
"""hooks/lib/frontmatter.sh の単体テスト（P3-5）。"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "frontmatter.sh"


def run_fn(fn: str, *args: str) -> tuple[int, str]:
    quoted = " ".join(f"'{a}'" for a in args)
    r = subprocess.run(
        ["bash", "-c", f"source '{LIB}' && {fn} {quoted}"],
        capture_output=True, text=True, check=False)
    return r.returncode, r.stdout


class TestReadFrontmatter(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        p = tmp / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_basic_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\na: 1\nb: 2\n---\nbody\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(rc, 0)
            self.assertEqual(out, "a: 1\nb: 2\n")

    def test_body_dashes_not_included(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\na: 1\n---\nbody\n---\ntail\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(out, "a: 1\n")

    def test_no_frontmatter_rc1_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "plain text\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")

    def test_unterminated_frontmatter_rc1_no_partial_output(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\na: 1\nno close\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")

    def test_missing_file_rc1(self):
        rc, out = run_fn("read_frontmatter", "/nonexistent/x.md")
        self.assertEqual(rc, 1)


class TestFrontmatterSection(unittest.TestCase):
    def test_section_over_20_lines(self):
        # P3-5 の動機: gate_approvals 開始から 20 行を超えたキーも読めること。
        pad = "\n".join(f"  k{i:02d}: pending" for i in range(25))
        text = f"---\ngate_approvals:\n{pad}\n  plan: approved\nnext_key: x\n---\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text(text, encoding="utf-8")
            rc, out = run_fn("frontmatter_section", str(p), "gate_approvals")
            self.assertEqual(rc, 0)
            self.assertIn("  plan: approved", out)
            self.assertNotIn("next_key", out)

    def test_section_absent_rc1(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text("---\na: 1\n---\n", encoding="utf-8")
            rc, out = run_fn("frontmatter_section", str(p), "gate_approvals")
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
