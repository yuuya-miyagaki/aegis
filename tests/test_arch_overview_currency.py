#!/usr/bin/env python3
"""C-5 / C-6: docs/architecture-overview.md must stay aligned with the
actual hook / lib / skill counts and the user-invocable skill list.

Full review axis D, findings C-5 and C-6:
  - Arch overview claims 18 skills with 15 `user-invocable: true` rows;
    reality is 1 `true` (session-recovery) + 17 `false`.
  - Arch overview claims `16 のランタイムフック` / `lib/ 3` / `11 チェック`;
    reality is 17 main hooks, 7 lib hooks, 12 drift checks.

Strategy (v1.6.1): pin the COUNTS that have the widest drift impact and
the user-invocable BOOLEAN table that lies in load-bearing prose. The
fully automated `generate_arch_inventory.py` is deferred to v1.7 (T2).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "architecture-overview.md"


def _arch_text() -> str:
    return ARCH.read_text(encoding="utf-8")


class TestArchOverviewCounts(unittest.TestCase):
    """The integer counts the doc claims must equal the implementation."""

    def test_main_hooks_count_matches_disk(self):
        actual = len(list((ROOT / "hooks").glob("*.sh")))
        text = _arch_text()
        # Match prose forms: "16 のランタイムフック", "全 16 フック",
        # "メイン16", "全 17 フック" etc. Capture the number near "フック".
        for pat in (r"(\d+)\s*のランタイムフック",
                    r"全\s*(\d+)\s*フック",
                    r"メイン\s*(\d+)"):
            for m in re.finditer(pat, text):
                self.assertEqual(
                    int(m.group(1)), actual,
                    f"arch-overview claims {m.group(1)} hooks at "
                    f"pattern {pat!r}; on disk hooks/*.sh = {actual}")

    def test_lib_hooks_count_matches_disk(self):
        actual = len(list((ROOT / "hooks" / "lib").glob("*.sh")))
        text = _arch_text()
        # "lib/ 3" form: "lib/ N:" or "lib/ N "
        for m in re.finditer(r"lib/\s*(\d+)\s*[:：]", text):
            self.assertEqual(
                int(m.group(1)), actual,
                f"arch-overview claims lib/ {m.group(1)}; on disk "
                f"hooks/lib/*.sh = {actual}")

    def test_drift_checks_count_matches_implementation(self):
        # Import ALL_CHECKS via source-grep (avoids module import cost).
        src = (ROOT / "scripts" / "check_reference_drift.py").read_text(
            encoding="utf-8")
        block = re.search(r"ALL_CHECKS = \[(.*?)\]", src, re.S)
        self.assertIsNotNone(block, "ALL_CHECKS literal not found")
        actual = block.group(1).count("(\"")
        text = _arch_text()
        for m in re.finditer(r"(\d+)\s*チェック", text):
            # "N チェック" appears in a different context (e.g. lint),
            # so we only assert on the drift line, which contains "drift".
            # Find the surrounding line.
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            line = text[line_start:line_end]
            if "drift" in line.lower() or "check_reference_drift" in line:
                self.assertEqual(
                    int(m.group(1)), actual,
                    f"arch-overview claims {m.group(1)} drift checks "
                    f"in line {line!r}; ALL_CHECKS = {actual}")


class TestArchOverviewSkillUserInvocableTable(unittest.TestCase):
    """The user-invocable table for skills must match the SKILL.md
    frontmatter on disk. Drift in this table mis-documents the load-
    bearing P1-A invariant that user-invocable=false skills have only
    the phase-skills.sh path-form starter."""

    def _disk_user_invocable_map(self) -> dict[str, bool]:
        m = {}
        for sk_md in (ROOT / ".claude" / "skills").glob("*/SKILL.md"):
            name = sk_md.parent.name
            text = sk_md.read_text(encoding="utf-8")
            frontmatter = re.match(r"^---\n(.*?)\n---", text, re.S)
            if not frontmatter:
                continue
            for line in frontmatter.group(1).splitlines():
                if line.startswith("user-invocable:"):
                    v = line.split(":", 1)[1].strip().lower()
                    m[name] = (v == "true")
                    break
        return m

    def _arch_user_invocable_table(self) -> dict[str, bool]:
        text = _arch_text()
        # Locate the table — look for a line that has both "user-invocable"
        # in the header and a markdown table border below.
        m = re.search(
            r"^\|\s*スキル\s*\|.*?user-invocable.*?\n\|[\-\s|]+\n(.*?)\n\n",
            text, re.M | re.S)
        self.assertIsNotNone(m,
                             "user-invocable table not located in arch-overview")
        rows = m.group(1).splitlines()
        out: dict[str, bool] = {}
        for r in rows:
            cells = [c.strip() for c in r.split("|")[1:-1]]
            if len(cells) < 3:
                continue
            name = cells[0]
            val = cells[2].lower()
            if val in ("true", "false"):
                out[name] = (val == "true")
        return out

    def test_disk_and_arch_user_invocable_match(self):
        disk = self._disk_user_invocable_map()
        arch = self._arch_user_invocable_table()
        # The two maps must agree on every name present in both.
        disagreements = []
        for name in sorted(set(disk) & set(arch)):
            if disk[name] != arch[name]:
                disagreements.append(
                    f"{name}: disk={disk[name]!r} vs arch={arch[name]!r}")
        self.assertEqual(
            disagreements, [],
            f"user-invocable drift between SKILL.md and arch-overview: "
            f"{disagreements}")

    def test_arch_table_skill_set_matches_disk(self):
        """Every skill on disk must appear in the table (and vice versa).
        Aliases are allowed in arch-overview to ease reading, so we just
        confirm the cardinalities and exact-match sets are equal."""
        disk = set(self._disk_user_invocable_map().keys())
        arch = set(self._arch_user_invocable_table().keys())
        missing_in_arch = disk - arch
        extra_in_arch = arch - disk
        self.assertEqual(
            (missing_in_arch, extra_in_arch), (set(), set()),
            f"arch-overview skill table out of sync: "
            f"missing={missing_in_arch}, extra={extra_in_arch}")


if __name__ == "__main__":
    unittest.main()
