#!/usr/bin/env python3
"""Operational health diagnostics for STATUS.md.

Complements check_status.py (schema validation) with runtime/operational
health checks that the schema validator does not cover.

Exits 1 on any FAIL, 0 on WARNING-only or clean.

Usage:
    python3 scripts/status_doctor.py [--root <project_root>]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Import extraction utilities from check_status.py (same directory).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_status import (
    extract_failure_tracking,
    extract_frontmatter,
    extract_scalar_value,
    extract_session_history,
    has_top_level_key,
    read_text,
)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

STALE_DAYS = 7
BLOCKER_STALE_DAYS = 3


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str | None) -> date | None:
    """Try to parse a date from YYYY-MM-DD or ISO 8601 timestamp."""
    if not value:
        return None
    try:
        # Normalize: strip quotes, take first 10 chars (handles YYYY-MM-DDTHH:MM:SSZ).
        cleaned = value.strip().strip('"')[:10]
        parts = cleaned.split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        pass
    return None


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def d1_last_updated_stale(
    frontmatter: str, today: date
) -> list[str]:
    """D1: last_updated が STALE_DAYS 日以上前 → WARNING"""
    warnings: list[str] = []
    last_updated = extract_scalar_value(frontmatter, "last_updated")
    d = _parse_date(last_updated)
    if d and (today - d) >= timedelta(days=STALE_DAYS):
        delta = (today - d).days
        warnings.append(
            f"last_updated is {delta} days old ({last_updated}) — "
            f"project may be stale (threshold: {STALE_DAYS} days)"
        )
    return warnings


def d2_blockers_stale(
    frontmatter: str, today: date
) -> list[str]:
    """D2: blockers が空でなく、last_updated が BLOCKER_STALE_DAYS 日以上前 → WARNING"""
    warnings: list[str] = []

    # Check blockers — we look for non-empty blockers in the frontmatter.
    # Blockers is a list: `blockers: []` means empty, otherwise has items.
    has_blockers = False
    in_block = False
    for line in frontmatter.splitlines():
        stripped = line.rstrip()
        if not in_block:
            if stripped.startswith("blockers:"):
                inline = stripped[len("blockers:"):].strip()
                if inline == "[]":
                    break
                if inline == "":
                    in_block = True
                    continue
                # Inline non-empty value.
                has_blockers = True
                break
            continue
        # Inside blockers block.
        if stripped.strip().startswith("- "):
            has_blockers = True
            break
        if stripped.strip() and not stripped.startswith(" "):
            break

    if not has_blockers:
        return warnings

    last_updated = extract_scalar_value(frontmatter, "last_updated")
    d = _parse_date(last_updated)
    if d and (today - d) >= timedelta(days=BLOCKER_STALE_DAYS):
        delta = (today - d).days
        warnings.append(
            f"blockers are present and last_updated is {delta} days old — "
            f"blockers may be unattended (threshold: {BLOCKER_STALE_DAYS} days)"
        )

    return warnings


def d3_failure_escalation(
    frontmatter: str, root: Path
) -> list[str]:
    """D3: failure_tracking.count >= 3 かつ second-opinion.md 未作成 → FAIL"""
    failures: list[str] = []

    if not has_top_level_key(frontmatter, "failure_tracking"):
        return failures

    ft = extract_failure_tracking(frontmatter)
    if ft is None:
        return failures

    count_str = ft.get("count", "0")
    try:
        count = int(count_str)
    except (ValueError, TypeError):
        return failures

    if count >= 3:
        second_opinion = root / "docs" / "second-opinion.md"
        if not second_opinion.exists():
            goal = ft.get("goal", "(unknown)")
            failures.append(
                f"failure_tracking.count={count} (goal: {goal}) but "
                f"docs/second-opinion.md does not exist — "
                f"CLAUDE.md requires writing second-opinion.md after 3 failures"
            )

    return failures


def d4_phase_stagnation(frontmatter: str) -> list[str]:
    """D4: session_history の全エントリが同一 phase → WARNING"""
    warnings: list[str] = []

    history = extract_session_history(frontmatter)
    if len(history) < 2:
        return warnings

    phases = {entry.get("phase") for entry in history if entry.get("phase")}
    if len(phases) == 1:
        phase = next(iter(phases))
        warnings.append(
            f"all {len(history)} session_history entries are in '{phase}' phase — "
            f"consider changing approach or escalating"
        )

    return warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_doctor_collect(root: Path) -> tuple[list[str], list[str]]:
    """Run all diagnostics and return (warnings, failures) lists.

    Returns ([], []) if STATUS.md is missing or has no frontmatter.
    """
    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        return [], []

    text = read_text(status_path)
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        return [], []

    today = date.today()
    all_warnings: list[str] = []
    all_failures: list[str] = []

    # D1
    all_warnings.extend(d1_last_updated_stale(frontmatter, today))
    # D2
    all_warnings.extend(d2_blockers_stale(frontmatter, today))
    # D3
    all_failures.extend(d3_failure_escalation(frontmatter, root))
    # D4
    all_warnings.extend(d4_phase_stagnation(frontmatter))

    return all_warnings, all_failures


def run_doctor(root: Path) -> int:
    """Run all diagnostics. Returns 0 on pass/warning-only, 1 on any FAIL."""
    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        print("ERROR: docs/STATUS.md not found")
        return 1

    text = read_text(status_path)
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        print("ERROR: docs/STATUS.md is missing YAML frontmatter")
        return 1

    all_warnings, all_failures = run_doctor_collect(root)

    for w in all_warnings:
        print(f"WARNING: {w}")
    for f in all_failures:
        print(f"FAIL: {f}")

    if all_failures:
        return 1

    if not all_warnings:
        print(f"PASS: status doctor found no issues: {status_path}")
    else:
        print(f"PASS (with {len(all_warnings)} warnings): {status_path}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="STATUS.md operational health diagnostics")
    parser.add_argument(
        "--root", default=".", help="Project root containing docs/STATUS.md"
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    return run_doctor(root)


if __name__ == "__main__":
    raise SystemExit(main())
