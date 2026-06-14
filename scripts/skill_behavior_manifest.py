#!/usr/bin/env python3
"""Single source of truth for skill behavior invariants (the skill behavior contract).

Each judgment / dialogue skill — the ones whose adherence is NOT enforced by a hook —
declares the load-bearing instruction tokens it must always contain. A skill edit that
drops a core instruction is caught deterministically by
check_reference_drift.check_skill_behavior_contract (a regression guard).

This is the deterministic (layer-1) half of the skill pressure test. The opt-in
adversarial drill (layer-2) lives in extensions/skill-pressure-drill/ and actually runs
an agent against the skill; it is manual and not in CI.

Scope: only skills whose adherence cannot be hook-enforced. Hard gates are already
guaranteed by PaC hooks, so testing those would just duplicate the hook. Tokens are
short, stable core phrases: reword surrounding prose freely as long as the core phrase
survives; deleting the core phrase is exactly the regression we want to catch.

Root-only, non-mirrored (scripts/ is not a MIRROR_DIR). Consumed by import in
check_reference_drift.py; the check is framework-root guarded so it stays inert for
installed projects.

Limitation: this catches *accidental* removal of a core instruction. A determined edit
that deletes the instruction AND its manifest token in the same commit passes; layer 1
is a conscious-acknowledgment ratchet (a regression speed-bump), not a wall.
"""

from __future__ import annotations

# skill dir name -> load-bearing invariant tokens (substring match against SKILL.md body)
SKILL_INVARIANTS: dict[str, list[str]] = {
    "aegis-brainstorm": [
        "設計が承認されるまで",
        "「シンプルすぎる」は例外にならない",
    ],
    "tdd": [
        "テストなしのプロダクションコードは禁止",
        "RED-GREEN-REFACTOR",
    ],
    "bug-diagnosis": [
        "仮説を1つ立てる",
        "再現確認",
    ],
    "aegis-review-gate": [
        "evidence なき PASS 判定を出さない",
        "diff を読まずに",
    ],
    "aegis-security-gate": [
        "スキャンなき PASS を出さない",
        "「内部用だから安全」で省略しない",
    ],
    "qa-verification": [
        "エビデンスなき PASS を出さない",
        "テストを実行せずに「前回と同じ」で省略しない",
    ],
    "subagent-dev": [
        "タスクごとにフレッシュなサブエージェント",
        "段階レビュー",
    ],
}
