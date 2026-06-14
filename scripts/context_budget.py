#!/usr/bin/env python3
"""Deterministic context-budget check + tighten-only ratchet (roadmap P1).

Single owner of: target enumeration, budget registry I/O, word counting,
the check (FAIL on over-budget), and the ratchet (tighten / seed).
check_framework_contract.py imports check(). Unit = words (len(text.split())).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_WORDS = 1500
DEFAULT_RULE_WORDS = 500


def word_count(text: str) -> int:
    return len(text.split())


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
    data = load_budgets(root)
    failures: list[str] = []
    for p in iter_targets(root):
        rel = str(p.relative_to(root))
        count = word_count(p.read_text(encoding="utf-8"))
        budget = budget_for(rel, data)
        if count > budget:
            failures.append(f"{rel} is too large: {count} words > {budget}")
    return failures
