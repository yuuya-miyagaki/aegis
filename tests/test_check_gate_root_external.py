#!/usr/bin/env python3
"""iter44 (C5): check-gate.sh must not apply the plan-gate — or the Client-mode
code lock — to ROOT-external absolute paths.

Background: during a 2026-06-24 review, an Edit to a global auto-memory file
(~/.claude/projects/.../memory/*.md — outside the project ROOT) was denied with
"[gate] Plan gate is pending". The plan gate (and the Client-mode deny) guard
THIS project's code; an absolute path outside ROOT is not project code, so it must
short-circuit to allow BEFORE the mode/plan-gate checks. Control-file / templates /
docs protections run first and stay intact.

Harness mirrors tests/test_control_plane_allowlist.py: a scratch ROOT containing
the hook plus the libs it sources, so the hook's ROOT (SCRIPT_DIR/..) resolves to
the scratch dir. emit_allow outputs exactly "{}" (hooks/lib/emit.sh), so allow is
asserted strictly (NOT via an `if out:` guard, which would let a deny pass).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_TMPL = (
    "---\nframework: aegis\nmode: {mode}\nphase: {phase}\n"
    "task_type: {task_type}\ngate_approvals:\n  plan: {plan}\n---\n"
)


def _scratch_root(mode: str = "Dev", task_type: str = "feature",
                  plan: str = "pending", phase: str = "implement"):
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        STATUS_TMPL.format(mode=mode, task_type=task_type, plan=plan, phase=phase),
        encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-gate.sh", hooks_dir / "check-gate.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, file_path: str, tool: str = "Edit") -> str:
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": file_path}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-gate.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


def _external_of(root: Path) -> str:
    """An absolute path that is a sibling of (never under) the scratch ROOT,
    mimicking a global auto-memory file outside the project."""
    return os.path.join(os.path.dirname(str(root)), "aegis-external-mem", "MEMORY.md")


class TestRootExternalAllow(unittest.TestCase):
    def test_a_dev_plan_pending_external_absolute_allows(self):
        """RED before fix: a ROOT-external absolute path (auto-memory) must allow,
        not be denied by a pending plan gate."""
        with _scratch_root(mode="Dev", plan="pending") as name:
            root = Path(name)
            out = _hook(root, _external_of(root))
        self.assertTrue(_allowed(out),
                        f"ROOT-external absolute path must allow ({{}}), got: {out!r}")

    def test_b_dev_plan_pending_internal_absolute_denies(self):
        """Regression: project code under ROOT stays plan-gated. Exercises both the
        logical ROOT and physical ROOT_REAL (macOS /var -> /private/var) arms."""
        with _scratch_root(mode="Dev", plan="pending") as name:
            root = Path(name)
            for base in {str(root), os.path.realpath(str(root))}:
                out = _hook(root, os.path.join(base, "src", "main.py"))
                self.assertTrue(
                    _denied(out),
                    f"internal path {base}/src/main.py must deny, got: {out!r}")

    def test_c_control_file_denies_during_project_work(self):
        """Regression: a hooks/ control file is denied under task_type=feature even
        when the plan gate is approved (control-file protection, not plan gate)."""
        with _scratch_root(mode="Dev", task_type="feature", plan="approved") as name:
            root = Path(name)
            out = _hook(root, os.path.join(str(root), "hooks", "x.sh"))
        self.assertTrue(_denied(out), f"control file must deny, got: {out!r}")

    def test_d_docs_allows(self):
        """Regression: the docs/ allowlist still allows."""
        with _scratch_root(mode="Dev", plan="pending") as name:
            root = Path(name)
            out = _hook(root, os.path.join(str(root), "docs", "foo.md"))
        self.assertTrue(_allowed(out), f"docs path must allow ({{}}), got: {out!r}")

    def test_e_client_mode_external_allows(self):
        """#1: external absolute paths are allowed even in Client mode (auto-memory
        is mode-independent). RED before fix (Client mode denied all non-allowlisted
        edits)."""
        with _scratch_root(mode="Client", plan="approved") as name:
            root = Path(name)
            out = _hook(root, _external_of(root))
        self.assertTrue(_allowed(out),
                        f"Client-mode external path must allow ({{}}), got: {out!r}")

    def test_f_client_mode_internal_denies(self):
        """#1 regression: the Client-mode code lock still denies ROOT-internal code."""
        with _scratch_root(mode="Client", plan="approved") as name:
            root = Path(name)
            out = _hook(root, os.path.join(str(root), "src", "x.py"))
        self.assertTrue(_denied(out),
                        f"Client-mode internal code must deny, got: {out!r}")

    def test_g_relative_path_stays_gated(self):
        """Defensive (grill-code): a relative target matches no case arm and stays
        plan-gated. Edit/Write always supply absolute paths, but this pins the
        invariant so a future change can't accidentally let relative project code
        escape the plan gate via the short-circuit."""
        with _scratch_root(mode="Dev", plan="pending") as name:
            root = Path(name)
            out = _hook(root, "src/app.ts")
        self.assertTrue(_denied(out),
                        f"relative project path must stay gated, got: {out!r}")

    def test_h_templates_denied_during_project_work(self):
        """Regression (grill-code): the short-circuit runs after the templates
        block, so a templates/ file stays framework-controlled (denied under
        task_type=feature)."""
        with _scratch_root(mode="Dev", task_type="feature", plan="approved") as name:
            root = Path(name)
            out = _hook(root, os.path.join(str(root), "templates", "X.template.md"))
        self.assertTrue(_denied(out), f"template file must deny, got: {out!r}")

    def test_i_internal_allowed_when_plan_approved(self):
        """Positive control (review note): an internal path IS allowed once the
        plan gate is approved. This proves the harness STATUS is actually parsed
        and the gate value round-trips — if a future schema rename broke gate
        parsing, plan would read empty and this would flip to deny, catching the
        drift (guards against silent false-greens in the _denied tests)."""
        with _scratch_root(mode="Dev", plan="approved") as name:
            root = Path(name)
            out = _hook(root, os.path.join(str(root), "src", "main.py"))
        self.assertTrue(_allowed(out),
                        f"internal path with plan approved must allow, got: {out!r}")

    def test_j_sibling_prefix_dir_is_external(self):
        """Edge (review note): a sibling dir whose name shares ROOT as a string
        prefix (e.g. /path/aegis-backup vs ROOT /path/aegis) is NOT internal — the
        '/' anchor in "$ROOT"/* prevents the false match, so it short-circuits to
        allow as a genuinely external path."""
        with _scratch_root(mode="Dev", plan="pending") as name:
            root = Path(name)
            sibling = str(root) + "-backup"
            out = _hook(root, os.path.join(sibling, "src", "main.py"))
        self.assertTrue(_allowed(out),
                        f"sibling-prefix dir must be external/allow, got: {out!r}")


if __name__ == "__main__":
    unittest.main()
