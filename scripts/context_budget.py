#!/usr/bin/env python3
"""Deterministic context-budget check + tighten-only ratchet (roadmap P1).

Single owner of: target enumeration, budget registry I/O, word counting,
the check (FAIL on over-budget), and the ratchet (tighten / seed).
check_framework_contract.py imports check(). Unit = words (len(text.split())).
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_WORDS = 1500
DEFAULT_RULE_WORDS = 500


def word_count(text: str) -> int:
    return len(text.split())


# Budget-exclude markers: content whose growth is governed by ANOTHER invariant
# (e.g. the routing roster, drift-pinned to .claude/agents/) is wrapped in these
# and excluded from the word count, so the budget measures bloat-prone free prose
# only. An unmatched start (no matching end) matches nothing = counts everything
# (fail-graceful, never hides bloat). Do NOT nest markers: the non-greedy match
# runs first-start..first-end, so a nested pair is NOT strip-safe.
_EXCLUDE_RE = re.compile(
    r"<!--\s*aegis:budget-exclude-start\s*-->.*?<!--\s*aegis:budget-exclude-end\s*-->",
    re.DOTALL,
)


def _strip_excluded(text: str) -> str:
    return _EXCLUDE_RE.sub("", text)


def _budget_word_count(text: str) -> int:
    return word_count(_strip_excluded(text))


def registry_path(root: Path) -> Path:
    return Path(root) / "scripts" / "context-budgets.json"


def load_budgets(root: Path) -> dict:
    p = registry_path(root)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_budgets(root: Path, data: dict) -> None:
    registry_path(root).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def iter_targets(root: Path) -> list[Path]:
    root = Path(root)
    targets = sorted((root / ".claude" / "skills").glob("*/SKILL.md"))
    targets += sorted((root / ".claude" / "rules").glob("*.md"))
    return targets


def _kind(rel: str) -> str:
    return "rule" if "/rules/" in rel.replace("\\", "/") else "skill"


def budget_for(rel: str, data: dict) -> int:
    explicit = data.get("budgets", {}).get(rel)
    if explicit is not None:
        return explicit
    if _kind(rel) == "rule":
        return data.get("default_rule_words", DEFAULT_RULE_WORDS)
    return data.get("default_skill_words", DEFAULT_SKILL_WORDS)


def check(root: Path = ROOT) -> list[str]:
    root = Path(root)
    # Fail-graceful on a corrupt registry: report it as a contract failure
    # rather than crashing the whole contract run (matches how the framework
    # hardens against malformed manifests/templates).
    try:
        data = load_budgets(root)
    except json.JSONDecodeError as e:
        return [f"scripts/context-budgets.json is invalid JSON: {e}"]
    failures: list[str] = []
    for p in iter_targets(root):
        rel = str(p.relative_to(root))
        count = _budget_word_count(p.read_text(encoding="utf-8"))
        budget = budget_for(rel, data)
        if count > budget:
            failures.append(f"{rel} is too large: {count} words > {budget}")
    return failures


def tighten(root: Path = ROOT) -> list[tuple[str, int]]:
    """Lower budgets to current word count (never raise). New files get an
    explicit entry at their current count. Returns changed (rel, new)."""
    root = Path(root)
    data = load_budgets(root)
    budgets = data.setdefault("budgets", {})
    changed: list[tuple[str, int]] = []
    for p in iter_targets(root):
        rel = str(p.relative_to(root))
        count = _budget_word_count(p.read_text(encoding="utf-8"))
        if rel not in budgets or count < budgets[rel]:
            budgets[rel] = count
            changed.append((rel, count))
    save_budgets(root, data)
    return changed


def seed(root: Path = ROOT, headroom: float = 1.1) -> list[tuple[str, int]]:
    """Populate budgets for targets that lack an explicit entry, at
    ceil(current * headroom). Existing entries and defaults untouched if set."""
    root = Path(root)
    data = load_budgets(root)
    budgets = data.setdefault("budgets", {})
    data.setdefault("default_skill_words", DEFAULT_SKILL_WORDS)
    data.setdefault("default_rule_words", DEFAULT_RULE_WORDS)
    added: list[tuple[str, int]] = []
    for p in iter_targets(root):
        rel = str(p.relative_to(root))
        if rel in budgets:
            continue
        count = _budget_word_count(p.read_text(encoding="utf-8"))
        # round() first: float math like 50 * 1.1 == 55.00000000000001 would
        # otherwise ceil to 56. We want the intended +10%, not float noise.
        budgets[rel] = math.ceil(round(count * headroom, 6))
        added.append((rel, budgets[rel]))
    save_budgets(root, data)
    return added


def main(argv: list[str]) -> int:
    if "--tighten" in argv:
        for rel, new in tighten():
            print(f"tightened {rel} -> {new}")
        return 0
    if "--seed" in argv:
        for rel, new in seed():
            print(f"seeded {rel} -> {new}")
        return 0
    failures = check()
    for f in failures:
        print(f"FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
