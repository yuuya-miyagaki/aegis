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


class TestRawSection(unittest.TestCase):
    # .gate-snapshot は --- 区切りのない生ファイル。frontmatter_section では
    # 読めないため raw_section が必要（post-status-audit の改ざん検知が依存）。
    def test_bare_snapshot_file(self):
        text = "gate_approvals:\n  plan: approved\n  qa: pending\nphase: implement\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text(text, encoding="utf-8")
            rc, out = run_fn("raw_section", str(p), "gate_approvals")
            self.assertEqual(rc, 0)
            self.assertIn("  plan: approved", out)
            self.assertIn("  qa: pending", out)
            self.assertNotIn("phase:", out)

    def test_key_absent_rc1(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("phase: implement\n", encoding="utf-8")
            rc, out = run_fn("raw_section", str(p), "gate_approvals")
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")

    def test_missing_file_rc1(self):
        rc, out = run_fn("raw_section", "/nonexistent/x", "gate_approvals")
        self.assertEqual(rc, 1)

    def test_frontmattered_file_also_readable(self):
        # フォールバック連鎖で STATUS.md に使われても同じ節が取れること。
        text = "---\ngate_approvals:\n  plan: approved\nnext: x\n---\nbody\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text(text, encoding="utf-8")
            rc, out = run_fn("raw_section", str(p), "gate_approvals")
            self.assertEqual(rc, 0)
            self.assertIn("  plan: approved", out)
            self.assertNotIn("next:", out)


class TestFrontmatterValue(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        p = tmp / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_quoted_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), '---\nmode: "Dev"\nphase: implement\n---\n')
            rc, out = run_fn("frontmatter_value", str(p), "mode")
            self.assertEqual(out, "Dev\n")

    def test_unquoted_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\nphase: implement\n---\n")
            rc, out = run_fn("frontmatter_value", str(p), "phase")
            self.assertEqual(out, "implement\n")

    def test_empty_string_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), '---\nnext_action: ""\n---\n')
            rc, out = run_fn("frontmatter_value", str(p), "next_action")
            self.assertEqual(out, "\n")

    def test_value_with_spaces_and_colon(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), '---\nnext_action: "do X: then Y"\n---\n')
            rc, out = run_fn("frontmatter_value", str(p), "next_action")
            self.assertEqual(out, "do X: then Y\n")

    def test_absent_key_empty_rc0(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\nmode: Dev\n---\n")
            rc, out = run_fn("frontmatter_value", str(p), "nonexistent")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_bare_snapshot_value(self):
        # --- 無しの .gate-snapshot からも読める（post-status-audit 依存）
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("phase: implement\nmode: Dev\n", encoding="utf-8")
            rc, out = run_fn("frontmatter_value", str(p), "phase")
            self.assertEqual(out, "implement\n")

    def test_missing_file_empty_rc0(self):
        rc, out = run_fn("frontmatter_value", "/nonexistent/x.md", "mode")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")


class TestGateValue(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        p = tmp / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_gate_present(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan: approved\n  qa: pending\n---\n")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "approved\n")

    def test_gate_null(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan: null\n---\n")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "null\n")

    def test_gate_absent_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan: approved\n---\n")
            rc, out = run_fn("gate_value", str(p), "deploy")
            self.assertEqual(out, "")

    def test_gate_anchor_no_substring_match(self):
        # 2スペース anchor: "plan" が "plan_extra" を誤って拾わない
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\ngate_approvals:\n  plan_extra: approved\n  plan: pending\n---\n")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "pending\n")

    def test_gate_bare_snapshot(self):
        # grill 致命1: --- 無し .gate-snapshot からも読める（raw_section fallback）
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("gate_approvals:\n  plan: approved\n  qa: pending\nphase: implement\n",
                         encoding="utf-8")
            rc, out = run_fn("gate_value", str(p), "plan")
            self.assertEqual(out, "approved\n")


class TestValueEquivalenceWithLegacyPipeline(unittest.TestCase):
    """新関数が旧3段パイプと全キーで一致することを実証（挙動不変）。"""
    STATUS = ('---\nframework: aegis\nframework_version: "1.7.1"\n'
              'mode: Dev\nphase: implement\ntask_type: framework\n'
              'task_size: M\nnext_action: "do X: then Y"\nblockers: []\n'
              'gate_approvals:\n  plan: approved\n  qa: pending\n  deploy: null\n---\nbody\n')
    SNAPSHOT = ("gate_approvals:\n  plan: approved\n  qa: pending\n"
                "phase: implement\nmode: Dev\n")

    def _legacy_value(self, path: str, key: str) -> str:
        cmd = (f'grep -m1 "^{key}:" "{path}" | sed "s/^{key}:[[:space:]]*//" '
               f"| sed 's/^\"//;s/\"$//' || true")
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout

    def _legacy_gate(self, path: str, gate: str) -> str:
        cmd = (f'{{ source "{LIB}"; frontmatter_section "{path}" gate_approvals 2>/dev/null '
               f'|| raw_section "{path}" gate_approvals; }} | grep -m1 "{gate}:" '
               f"| sed \"s/.*{gate}:[[:space:]]*//\" | sed 's/^\"//;s/\"$//' || true")
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout

    def test_scalar_all_keys_match(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text(self.STATUS, encoding="utf-8")
            for key in ("mode", "phase", "task_type", "task_size",
                        "next_action", "framework_version", "missing"):
                _, new = run_fn("frontmatter_value", str(p), key)
                self.assertEqual(new, self._legacy_value(str(p), key),
                                 f"scalar divergence for {key!r}")

    def test_scalar_bare_snapshot_match(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text(self.SNAPSHOT, encoding="utf-8")
            for key in ("phase", "mode", "missing"):
                _, new = run_fn("frontmatter_value", str(p), key)
                self.assertEqual(new, self._legacy_value(str(p), key),
                                 f"bare-snapshot scalar divergence for {key!r}")

    def test_gate_match_status_and_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            st = Path(d) / "STATUS.md"
            st.write_text(self.STATUS, encoding="utf-8")
            snap = Path(d) / ".gate-snapshot"
            snap.write_text(self.SNAPSHOT, encoding="utf-8")
            for path in (st, snap):
                for gate in ("plan", "qa", "deploy", "client_ready_for_dev"):
                    _, new = run_fn("gate_value", str(path), gate)
                    self.assertEqual(new, self._legacy_gate(str(path), gate),
                                     f"gate divergence for {gate!r} in {path.name}")


class TestCallSitesUse20PlusLines(unittest.TestCase):
    def test_update_gate_lists_gates_beyond_20_lines(self):
        # P3-5 regression: a gate_approvals section longer than 20 lines must
        # still be fully listed by update-gate.sh (the old grep -A20 truncated).
        import shutil
        pad = "\n".join(f"  pad{i:02d}: pending" for i in range(22))
        text = ("---\nframework: aegis\ngate_approvals:\n" + pad +
                "\n  deploy: pending\nphase: plan\n---\n")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            (root / "scripts").mkdir()
            (root / "hooks" / "lib").mkdir(parents=True)
            (root / "docs" / "STATUS.md").write_text(text, encoding="utf-8")
            shutil.copy(ROOT / "scripts" / "update-gate.sh", root / "scripts")
            shutil.copy(ROOT / "scripts" / "check_status.py", root / "scripts")
            for lib in ("frontmatter.sh", "emit.sh", "extract-input.sh", "patterns.sh"):
                shutil.copy(ROOT / "hooks" / "lib" / lib, root / "hooks" / "lib")
            r = subprocess.run(["bash", str(root / "scripts" / "update-gate.sh")],
                               capture_output=True, text=True, check=False)
            self.assertIn("deploy: pending", r.stdout)


if __name__ == "__main__":
    unittest.main()
