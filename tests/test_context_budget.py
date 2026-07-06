#!/usr/bin/env python3
"""context_budget の単体テスト。"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import context_budget  # noqa: E402


def _mk(root: Path, rel: str, words: int) -> Path:
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(" ".join(["w"] * words) + "\n", encoding="utf-8")
    return p


def _registry(root: Path, data: dict) -> None:
    (Path(root) / "scripts").mkdir(parents=True, exist_ok=True)
    (Path(root) / "scripts" / "context-budgets.json").write_text(
        json.dumps(data), encoding="utf-8")


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_over_budget_fails(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 100)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(
            any("foo/SKILL.md" in f and "100 words > 50" in f for f in failures),
            failures)

    def test_within_budget_passes(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 40)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        self.assertEqual(context_budget.check(self.tmp), [])

    def test_default_guards_unlisted_skill(self):
        _mk(self.tmp, ".claude/skills/big/SKILL.md", 2000)
        _registry(self.tmp, {"default_skill_words": 1500, "budgets": {}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("big/SKILL.md" in f for f in failures), failures)

    def test_rule_default_guards(self):
        _mk(self.tmp, ".claude/rules/r.md", 2000)
        _registry(self.tmp, {"default_rule_words": 500, "budgets": {}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("rules/r.md" in f for f in failures), failures)

    def test_malformed_registry_reports_not_crashes(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 10)
        (self.tmp / "scripts").mkdir(parents=True, exist_ok=True)
        (self.tmp / "scripts" / "context-budgets.json").write_text(
            "{ not valid json", encoding="utf-8")
        failures = context_budget.check(self.tmp)  # must not raise
        self.assertTrue(any("invalid JSON" in f for f in failures), failures)


class TestRatchet(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-r-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _read(self):
        return json.loads(
            (self.tmp / "scripts" / "context-budgets.json").read_text())

    def test_tighten_lowers_to_current(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 30)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 100}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/foo/SKILL.md"], 30)

    def test_tighten_never_raises(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 80)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/foo/SKILL.md"], 50)

    def test_tighten_adds_new_file_at_current(self):
        _mk(self.tmp, ".claude/skills/new/SKILL.md", 42)
        _registry(self.tmp, {"budgets": {}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/new/SKILL.md"], 42)

    def test_seed_uses_headroom_and_skips_existing(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 100)
        _mk(self.tmp, ".claude/skills/bar/SKILL.md", 50)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 999}})
        context_budget.seed(self.tmp, headroom=1.1)
        data = self._read()
        self.assertEqual(data["budgets"][".claude/skills/foo/SKILL.md"], 999)
        self.assertEqual(data["budgets"][".claude/skills/bar/SKILL.md"], 55)
        self.assertIn("default_skill_words", data)


class TestBudgetExclude(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-x-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_excluded_region_not_counted(self):
        # prose 10語 ＋ 除外領域(マーカー3+100+3=106語) → 計数=10（除外なしなら116）
        body = ("w " * 10 + "\n<!-- aegis:budget-exclude-start -->\n"
                + "x " * 100 + "\n<!-- aegis:budget-exclude-end -->\n")
        p = Path(self.tmp) / ".claude" / "rules" / "r.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        _registry(self.tmp, {"budgets": {".claude/rules/r.md": 20}})
        self.assertEqual(context_budget.check(self.tmp), [])  # 10 ≤ 20

    def test_unmatched_marker_counts_everything(self):
        # start だけ（end 無し）→ strip せず全計数（fail-graceful・bloat を隠さない）
        body = ("w " * 10 + "\n<!-- aegis:budget-exclude-start -->\n" + "x " * 100 + "\n")
        p = Path(self.tmp) / ".claude" / "rules" / "r.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        _registry(self.tmp, {"budgets": {".claude/rules/r.md": 20}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("rules/r.md" in f for f in failures), failures)


class TestRoutingExcludeAntiAbuse(unittest.TestCase):
    """濫用ガード: routing.md の除外領域は drift 支配の roster のみ。任意 prose を
    包んで budget を回避できないことを固定（除外領域 ⊇ 全 agent 名 かつ ⊉ 対象 prose）。"""

    def test_excluded_is_drift_roster_not_prose(self):
        routing = (ROOT / ".claude" / "rules" / "routing.md").read_text(encoding="utf-8")
        regions = re.findall(
            r"<!--\s*aegis:budget-exclude-start\s*-->(.*?)<!--\s*aegis:budget-exclude-end\s*-->",
            routing, re.DOTALL)
        # 多領域濫用の封鎖: routing.md の除外は roster ただ1つのみ（2つ目のマーカー対で
        # prose を包む濫用を検知＝grill-plan 要検討2）。
        self.assertEqual(len(regions), 1,
                         f"routing.md の budget-exclude 領域は roster の1つのみであるべき（実際 {len(regions)} 個）")
        excluded = regions[0]
        # (a) drift 支配の全 agent（.claude/agents/*.md）が除外領域内（roster が除外対象）
        agent_stems = sorted(p.stem for p in (ROOT / ".claude" / "agents").glob("*.md"))
        self.assertTrue(agent_stems, "agents/ が空")
        for a in agent_stems:
            self.assertIn(f"`{a}`", excluded,
                          f"drift roster の `{a}` が除外領域外＝除外が roster と不一致")
        # (b) 除外領域は roster 行のみ＝各行が backtick agent 名を含む行 or 既知 scaffold 行。
        # review 盲検2次 note2: 「⊇ agent 名 ∧ ∌ 固定 sentinel」だけだと、sentinel を避けた自由
        # prose を roster 領域に混ぜて budget を隠す濫用が素通りする。各行が roster 行であることを
        # 強制し「除外領域 == roster」を真に担保する（agent 追加は行に backtick 名が入るので追従）。
        scaffold = "Each agent's own file defines its domain."
        for line in excluded.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            is_roster = line.startswith("Subagents:") or line == scaffold or any(
                f"`{a}`" in line for a in agent_stems)
            self.assertTrue(is_roster,
                            f"除外領域に roster でない行が混入＝budget 隠しの濫用: {line!r}")

    def test_only_routing_uses_exclude_markers(self):
        # allowlist トリップワイヤ（grill-code 🟡）: 除外マーカーを使ってよい budget-target は
        # routing.md のみ。除外機構は汎用（_strip_excluded は全 target に効く）だが濫用ガードは
        # routing.md 特化ゆえ、新規 excluder は無ガードで bloat 隠しの穴になる。ここで FAIL させ
        # 「専用の濫用ガードを付けてから allowlist を更新せよ」を機械強制する。iter_targets（skills/
        # rules）に実 _EXCLUDE_RE を当てる（CLAUDE.md 等の非 target・マーカー言及は対象外）。
        excluders = sorted(
            str(p.relative_to(ROOT)) for p in context_budget.iter_targets(ROOT)
            if context_budget._EXCLUDE_RE.search(p.read_text(encoding="utf-8")))
        self.assertEqual(
            excluders, [".claude/rules/routing.md"],
            "budget-exclude マーカーは routing.md のみ許可。新 excluder は専用濫用ガードを "
            f"追加してから allowlist を更新せよ: {excluders}")


class TestRealRepo(unittest.TestCase):
    def test_real_repo_check_is_green(self):
        # seed 済み（committed）registry で実リポの全 skill/rule が予算内であること。
        # 予算超過の skill 追加や registry 破損があれば、このテストが FAIL する。
        self.assertEqual(context_budget.check(ROOT), [])


if __name__ == "__main__":
    unittest.main()
