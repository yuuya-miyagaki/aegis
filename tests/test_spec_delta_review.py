#!/usr/bin/env python3
"""P2 (v1.9.0): spec delta review.

client_ready_for_dev GATE-APPROVE requires a plain-language CHANGES.md on the
2nd+ iteration so a non-engineer reviews what changed before re-approving
Client->Dev. iteration <= 1 or absent = not required (fail-open). Enforced at
the gate only (NOT the task-completion symmetric check) so later pure-Dev
iterations are not forced to produce a delta.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_STATUS = ROOT / "scripts" / "check_status.py"

SIX_ARTIFACTS = [
    ("docs/requirements/PRD.md", "prd-context"),
    ("docs/requirements/SCOPE.md", "scope-in-out"),
    ("docs/requirements/NFR.md", "nfr"),
    ("docs/requirements/ACCEPTANCE.md", "acceptance-criteria"),
    ("docs/handover/TO-DEV.md", "handover-to-dev"),
    ("docs/translation/mapping.md", "translation-mapping"),
]


def _filled(sentinel: str) -> str:
    body = ("# Document\n\nSufficient meaningful text exists to clear the "
            "minimum-bytes check. This sample passes 200 bytes and embeds "
            "the machine-readable sentinel comment the harness greps.\n\n")
    return body + f"<!-- aegis-required-section: {sentinel} -->\n"


def _status_md(iteration, gate="pending") -> str:
    iter_line = f"iteration: {iteration}\n" if iteration is not None else ""
    return (
        '---\nframework: aegis\nframework_version: "1.9.0"\n'
        'project_name: "test"\nmode: Client\nphase: handover\n'
        'task_type: feature\ntask_size: M\n' + iter_line +
        'ui_surface: false\nlast_updated: "2026-06-14T00:00:00Z"\n'
        'gate_approvals:\n'
        f'  client_ready_for_dev: {gate}\n  brainstorm: pending\n'
        '  plan: pending\n  review: pending\n  qa: pending\n'
        '  security: pending\n  deploy: pending\n'
        '  dev_ready_for_client: pending\n'
        'current_refs:\n  requirements: []\n  plan: null\n  spec: null\n'
        '  review: null\n  qa: null\n  security: null\n  deploy: null\n'
        '  translation: null\n'
        'external_evidence: []\nfailure_tracking: null\n'
        'next_action: "test"\nblockers: []\nsession_history: []\n---\n\n'
        '## Summary\n\ntest\n')


def _make_project(tmp: Path, iteration, changes, gate="pending") -> None:
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "STATUS.md").write_text(
        _status_md(iteration, gate), encoding="utf-8")
    for rel, sentinel in SIX_ARTIFACTS:
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(_filled(sentinel), encoding="utf-8")
    if changes is not None:
        cp = tmp / "docs" / "handover" / "CHANGES.md"
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(changes, encoding="utf-8")


def _pre_approve(tmp: Path) -> tuple[int, str]:
    r = subprocess.run(
        ["python3", str(CHECK_STATUS), "--root", str(tmp),
         "--pre-approve-gate", "client_ready_for_dev"],
        capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


VALVE = (
    "# 変更サマリ\n\n## 今回は要件変更なし\n\n"
    "- [x] 今回の反復では要件を変更していない（理由: バグ修正のみ）\n\n"
    "## この反復で変える理由\n\n該当なし\n\n"
    "## 追加（新しく作るもの）\n\n該当なし\n\n"
    "## 変更（やり方が変わるもの）\n\n該当なし\n\n"
    "## 削除・取りやめ\n\n該当なし\n\n"
    "## 受入条件・スコープへの影響\n\n影響なし\n\n"
    "<!-- aegis-required-section: spec-delta -->\n")


class TestFirstIterationDoesNotRequireDelta(unittest.TestCase):
    def test_iteration_1_approves_without_changes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 1, changes=None)
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"iteration 1 must approve w/o CHANGES.md. out=\n{out}")

    def test_iteration_absent_approves_without_changes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, None, changes=None)
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"absent iteration must approve (fail-open). out=\n{out}")


class TestLaterIterationRequiresDelta(unittest.TestCase):
    def test_iteration_2_without_changes_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=None)
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"iteration 2 must DENY w/o CHANGES.md. out=\n{out}")
            self.assertIn("docs/handover/CHANGES.md", out)

    def test_iteration_2_short_changes_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2,
                changes="<!-- aegis-required-section: spec-delta -->\n")
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"<200 byte CHANGES.md must DENY. out=\n{out}")

    def test_iteration_2_no_sentinel_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes="x" * 1024)
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"missing sentinel must DENY. out=\n{out}")

    def test_iteration_2_filled_changes_approves(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=_filled("spec-delta"))
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"properly filled CHANGES.md must APPROVE. out=\n{out}")

    def test_iteration_2_no_change_valve_approves(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=VALVE)
            rc, out = _pre_approve(p)
            self.assertEqual(rc, 0,
                f"no-change valve must APPROVE. out=\n{out}")

    def test_iteration_with_trailing_space_strips_and_requires(self):
        # iteration "2 " (trailing space): strip => digit => required.
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "docs").mkdir(parents=True, exist_ok=True)
            (p / "docs" / "STATUS.md").write_text(
                _status_md("2 "), encoding="utf-8")
            for rel, sentinel in SIX_ARTIFACTS:
                (p / rel).parent.mkdir(parents=True, exist_ok=True)
                (p / rel).write_text(_filled(sentinel), encoding="utf-8")
            rc, out = _pre_approve(p)
            self.assertNotEqual(rc, 0,
                f"iteration '2 ' must strip->require CHANGES. out=\n{out}")


class TestTemplateCarriesSentinel(unittest.TestCase):
    def test_changes_template_has_sentinel(self):
        p = ROOT / "templates" / "CHANGES.template.md"
        self.assertTrue(p.exists(),
                        "templates/CHANGES.template.md missing")
        text = p.read_text(encoding="utf-8")
        self.assertIn("<!-- aegis-required-section: spec-delta -->", text)


class TestCompletionPathDoesNotRequireDelta(unittest.TestCase):
    """C1: the task-completion symmetric check (client_ready_for_dev approved)
    must NOT demand CHANGES.md even at iteration>1 — only the 6 artifacts."""

    def test_completion_evidence_iteration2_approved_no_changes_ok(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_project(p, 2, changes=None, gate="approved")
            r = subprocess.run(
                ["python3", str(CHECK_STATUS), "--root", str(p),
                 "--check-completion-evidence"],
                capture_output=True, text=True)
            combined = r.stdout + r.stderr
            self.assertNotIn("CHANGES.md", combined,
                f"completion check must not demand CHANGES.md. out=\n{combined}")


UPDATE_GATE = ROOT / "scripts" / "update-gate.sh"


def _run_gate(root: Path, action: str) -> tuple[int, str]:
    # update-gate.sh resolves root via SCRIPT_DIR/..; symlink read-only trees.
    # .claude must be a REAL dir (not a symlink) so the gate snapshot/lock do
    # not leak into the framework repo's live .claude (order-dependent flake).
    for d in ("scripts", "hooks", "templates"):
        if not (root / d).exists():
            (root / d).symlink_to(ROOT / d)
    (root / ".claude").mkdir(exist_ok=True)
    r = subprocess.run(
        ["bash", str(root / "scripts" / "update-gate.sh"),
         "client_ready_for_dev", action, "--ack", "test"],
        capture_output=True, text=True, cwd=str(root))
    return r.returncode, r.stdout + r.stderr


class TestReEntryResetWorkflow(unittest.TestCase):
    """C2: sticky-approved gate short-circuits; after reset the gate-time
    spec-delta check fires. Exercises the real update-gate.sh path."""

    def test_sticky_approved_then_reset_enforces_delta(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            # iteration 2, gate already approved (post first-cycle), no CHANGES.
            _make_project(p, 2, changes=None, gate="approved")

            # 1) approve while already approved => short-circuit, no check.
            rc, out = _run_gate(p, "approve")
            self.assertEqual(rc, 0,
                f"already-approved approve must short-circuit. out=\n{out}")

            # 2) reset => pending.
            rc, out = _run_gate(p, "reset")
            self.assertEqual(rc, 0, f"reset must succeed. out=\n{out}")

            # 3) approve now runs the check; iteration>1 + no CHANGES => DENY.
            rc, out = _run_gate(p, "approve")
            self.assertNotEqual(rc, 0,
                f"post-reset approve must DENY w/o CHANGES. out=\n{out}")
            self.assertIn("docs/handover/CHANGES.md", out)

            # 4) add CHANGES => approve succeeds.
            (p / "docs" / "handover" / "CHANGES.md").write_text(
                _filled("spec-delta"), encoding="utf-8")
            rc, out = _run_gate(p, "approve")
            self.assertEqual(rc, 0,
                f"approve with filled CHANGES must succeed. out=\n{out}")


if __name__ == "__main__":
    unittest.main()
