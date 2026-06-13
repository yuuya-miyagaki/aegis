#!/usr/bin/env python3
"""C-3: client_ready_for_dev must NOT approve on 6 empty `touch`-created files.

The v1.6.0 P1-D pre-approval and TaskCompleted symmetric check verify
existence of the 6 handover artifacts (PRD/SCOPE/NFR/ACCEPTANCE/TO-DEV/
mapping.md), but NOT content. Full-review axis A finding C-3 reproduced:

    mkdir -p docs/{requirements,handover,translation}
    touch docs/requirements/{PRD,SCOPE,NFR,ACCEPTANCE}.md
    touch docs/handover/TO-DEV.md
    touch docs/translation/mapping.md
    bash scripts/update-gate.sh client_ready_for_dev approve --ack 'PoC'
    # → gate moves to approved

This restores the exact silent-fail path that v1.6.0 P1-D was meant to close.

Fix (Task 3, v1.6.1):

  Each of the 6 artifacts must satisfy (a) ≥200 bytes AND (b) contain a
  machine-readable sentinel HTML comment:

    PRD.md                   <!-- aegis-required-section: prd-context -->
    SCOPE.md                 <!-- aegis-required-section: scope-in-out -->
    NFR.md                   <!-- aegis-required-section: nfr -->
    ACCEPTANCE.md            <!-- aegis-required-section: acceptance-criteria -->
    handover/TO-DEV.md       <!-- aegis-required-section: handover-to-dev -->
    translation/mapping.md   <!-- aegis-required-section: translation-mapping -->

  The sentinel is embedded in the templates (at the tail) so a user filling
  out the template normally keeps it. Removing the sentinel = fail.

The check fires at gate-approve time (pre_approve_client_ready_for_dev)
AND at task-completion time (evidence-integrity check), preserving the
v1.6.0 P1-D bilateral symmetry.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATE_GATE = ROOT / "scripts" / "update-gate.sh"

# Reference: keep in sync with CLIENT_GATE_ARTIFACTS in check_status.py.
ARTIFACTS = [
    ("docs/requirements/PRD.md", "prd-context"),
    ("docs/requirements/SCOPE.md", "scope-in-out"),
    ("docs/requirements/NFR.md", "nfr"),
    ("docs/requirements/ACCEPTANCE.md", "acceptance-criteria"),
    ("docs/handover/TO-DEV.md", "handover-to-dev"),
    ("docs/translation/mapping.md", "translation-mapping"),
]

# How much real text counts as "the user filled it in".
MIN_BYTES = 200


def _make_status_md(p: Path):
    (p / "docs").mkdir(exist_ok=True)
    (p / "docs" / "STATUS.md").write_text(
        '---\n'
        'framework: aegis\n'
        'framework_version: "1.6.1"\n'
        'project_name: "test"\n'
        'mode: Client\n'
        'phase: handover\n'
        'task_type: feature\n'
        'task_size: M\n'
        'iteration: 1\n'
        'ui_surface: false\n'
        'last_updated: "2026-06-12T00:00:00Z"\n'
        'gate_approvals:\n'
        '  client_ready_for_dev: pending\n'
        '  brainstorm: pending\n'
        '  plan: pending\n'
        '  review: pending\n'
        '  qa: pending\n'
        '  security: pending\n'
        '  deploy: pending\n'
        '  dev_ready_for_client: pending\n'
        'current_refs:\n'
        '  requirements: []\n'
        '  plan: null\n'
        '  spec: null\n'
        '  review: null\n'
        '  qa: null\n'
        '  security: null\n'
        '  deploy: null\n'
        '  translation: null\n'
        'external_evidence: []\n'
        'client_context:\n'
        '  client_id: ""\n'
        '  context_loaded: false\n'
        'failure_tracking: null\n'
        'next_action: "test"\n'
        'blockers: []\n'
        'session_history: []\n'
        '---\n\n## Summary\n\ntest\n',
        encoding="utf-8")


def _filled_content(sentinel: str) -> str:
    body = ("# Document\n\n"
            "Sufficient meaningful text exists to clear the minimum-bytes "
            "check. This sample text passes 200 bytes and embeds the "
            "machine-readable sentinel comment that the harness greps.\n\n")
    return body + f"<!-- aegis-required-section: {sentinel} -->\n"


def _run_gate(root: Path) -> tuple[int, str]:
    # update-gate.sh resolves the project root via SCRIPT_DIR/..; symlink the
    # read-only trees so the script can find scripts/hooks/templates.
    # `.claude` must be a REAL local dir, NOT a symlink to the framework repo's
    # own `.claude`: update-gate.sh writes the gate snapshot and lock dir under
    # `${ROOT}/.claude`, and a symlink would leak those writes into the live
    # `.claude/.gate-snapshot`, corrupting the developer's real session state
    # and cross-contaminating other tests that read it (order-dependent flake).
    for d in ("scripts", "hooks", "templates"):
        if not (root / d).exists():
            (root / d).symlink_to(ROOT / d)
    (root / ".claude").mkdir(exist_ok=True)
    r = subprocess.run(
        ["bash", str(root / "scripts" / "update-gate.sh"),
         "client_ready_for_dev", "approve", "--ack", "test"],
        capture_output=True, text=True, cwd=str(root))
    return r.returncode, r.stdout + r.stderr


class TestTouchBypassBlocked(unittest.TestCase):
    """All-empty artifacts must be rejected."""

    def test_six_touched_empty_files_are_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_status_md(p)
            for rel, _sentinel in ARTIFACTS:
                (p / rel).parent.mkdir(parents=True, exist_ok=True)
                (p / rel).touch()
            rc, out = _run_gate(p)
            self.assertNotEqual(
                rc, 0,
                f"6 touch-created (0 bytes, no sentinel) artifacts must "
                f"DENY gate approve. got rc={rc}, out=\n{out}")

    def test_sentinel_present_but_under_200_bytes_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_status_md(p)
            for rel, sentinel in ARTIFACTS:
                (p / rel).parent.mkdir(parents=True, exist_ok=True)
                (p / rel).write_text(
                    f"<!-- aegis-required-section: {sentinel} -->\n",
                    encoding="utf-8")
            rc, out = _run_gate(p)
            self.assertNotEqual(
                rc, 0,
                f"sentinel-only (under 200 bytes) artifacts must DENY. "
                f"got rc={rc}, out=\n{out}")

    def test_filled_but_sentinel_removed_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_status_md(p)
            for rel, _sentinel in ARTIFACTS:
                (p / rel).parent.mkdir(parents=True, exist_ok=True)
                # 1 KiB of prose; no sentinel.
                (p / rel).write_text("x" * 1024, encoding="utf-8")
            rc, out = _run_gate(p)
            self.assertNotEqual(
                rc, 0,
                f"missing sentinel must DENY even with bulk text. "
                f"got rc={rc}, out=\n{out}")


class TestProperlyFilledArtifactsApprove(unittest.TestCase):
    def test_six_properly_filled_files_approve(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            _make_status_md(p)
            for rel, sentinel in ARTIFACTS:
                (p / rel).parent.mkdir(parents=True, exist_ok=True)
                (p / rel).write_text(_filled_content(sentinel),
                                     encoding="utf-8")
            rc, out = _run_gate(p)
            self.assertEqual(
                rc, 0,
                f"properly filled artifacts must APPROVE. "
                f"got rc={rc}, out=\n{out}")


class TestTemplatesContainSentinels(unittest.TestCase):
    """The templates themselves must carry the sentinel so a user copying
    a template (and filling it out) ends up with the sentinel present."""

    TEMPLATES = [
        ("templates/PRD.template.md", "prd-context"),
        ("templates/SCOPE.template.md", "scope-in-out"),
        ("templates/NFR.template.md", "nfr"),
        ("templates/ACCEPTANCE.template.md", "acceptance-criteria"),
        ("templates/HANDOVER-TO-DEV.template.md", "handover-to-dev"),
        ("templates/TRANSLATION-MAPPING.template.md", "translation-mapping"),
    ]

    def test_each_template_contains_sentinel(self):
        for rel, sentinel in self.TEMPLATES:
            with self.subTest(template=rel):
                p = ROOT / rel
                self.assertTrue(p.exists(),
                                f"template missing: {rel}")
                text = p.read_text(encoding="utf-8")
                marker = f"<!-- aegis-required-section: {sentinel} -->"
                self.assertIn(
                    marker, text,
                    f"{rel} is missing required sentinel {marker!r}")


if __name__ == "__main__":
    unittest.main()
