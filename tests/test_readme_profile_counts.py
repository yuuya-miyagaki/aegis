#!/usr/bin/env python3
"""iteration 34 D1（外部レビュー E5）: README の profile 件数が profiles JSON と
一致することを機械的に固定し、再 stale を防ぐ。

README は従来 minimal「4 core files」/ standard「15 required + 8 recommended」と
書いていたが、実際は minimal required=8 / standard required=18・recommended=8。
"""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _count(profile: str, key: str) -> int:
    data = json.loads(
        (ROOT / "templates" / "profiles" / f"{profile}.json").read_text(encoding="utf-8")
    )
    return len(data.get(key, []))


class TestReadmeProfileCounts(unittest.TestCase):

    def test_minimal_required_count_matches(self):
        expected = _count("minimal", "required")
        m = re.search(r"minimal[^\d(]*\((\d+)\s*required", README)
        self.assertIsNotNone(
            m, "README に `minimal` (<n> required) の記述が見つからない")
        self.assertEqual(
            int(m.group(1)), expected,
            f"README の minimal required 件数 {m.group(1)} が "
            f"minimal.json の {expected} と不一致")

    def test_standard_counts_match(self):
        exp_req = _count("standard", "required")
        exp_rec = _count("standard", "recommended")
        m = re.search(
            r"standard[^\d(]*\((\d+)\s*required\s*\+\s*(\d+)\s*recommended", README)
        self.assertIsNotNone(
            m, "README に `standard` (<r> required + <c> recommended) の記述が無い")
        self.assertEqual(
            int(m.group(1)), exp_req,
            f"README standard required {m.group(1)} != JSON {exp_req}")
        self.assertEqual(
            int(m.group(2)), exp_rec,
            f"README standard recommended {m.group(2)} != JSON {exp_rec}")


if __name__ == "__main__":
    unittest.main()
