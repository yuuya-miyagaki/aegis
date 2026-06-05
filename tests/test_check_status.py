#!/usr/bin/env python3
"""Fixture-based integration tests for check_status.py routing matrix.

Tests --check-deploy-ready and --check-phase-transition via subprocess CLI,
covering task_type × task_size × phase combinations.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_STATUS = ROOT / "scripts" / "check_status.py"

# Default gate approvals (all pending).
DEFAULT_APPROVALS = {
    "client_ready_for_dev": "approved",
    "brainstorm": "approved",
    "plan": "approved",
    "review": "pending",
    "qa": "pending",
    "security": "pending",
    "deploy": "pending",
    "dev_ready_for_client": "pending",
}


def make_status_md(
    *,
    mode: str = "Dev",
    phase: str = "implement",
    task_type: str = "feature",
    task_size: str = "L",
    approvals: dict[str, str] | None = None,
    refs: dict[str, str] | None = None,
) -> str:
    """Generate a minimal STATUS.md frontmatter for testing."""
    gates = dict(DEFAULT_APPROVALS)
    if approvals:
        gates.update(approvals)
    gate_lines = "\n".join(f"  {k}: {v}" for k, v in gates.items())

    default_refs = {
        "requirements": "null",
        "plan": "null",
        "spec": "null",
        "review": "null",
        "qa": "null",
        "security": "null",
        "deploy": "null",
        "translation": "null",
    }
    if refs:
        default_refs.update(refs)
    ref_lines = "\n".join(f"  {k}: {v}" for k, v in default_refs.items())

    return (
        f"---\n"
        f"framework: aegis\n"
        f'framework_version: "0.12.0"\n'
        f"project_name: test\n"
        f"mode: {mode}\n"
        f"phase: {phase}\n"
        f"task_type: {task_type}\n"
        f"task_size: {task_size}\n"
        f'last_updated: "2026-01-01"\n'
        f"gate_approvals:\n"
        f"{gate_lines}\n"
        f"current_refs:\n"
        f"{ref_lines}\n"
        f"next_action: test\n"
        f"blockers: []\n"
        f"session_history: []\n"
        f"---\n"
    )


def run_check(tmp_root: str, *args: str) -> tuple[int, str]:
    """Run check_status.py with given args against a temp project root."""
    result = subprocess.run(
        ["python3", str(CHECK_STATUS), "--root", tmp_root, *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


class TempProject:
    """Context manager that creates a temp project with STATUS.md."""

    def __init__(self, status_content: str):
        self._content = status_content
        self._tmpdir: tempfile.TemporaryDirectory | None = None

    def __enter__(self) -> str:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = self._tmpdir.name
        docs = Path(root) / "docs"
        docs.mkdir()
        (docs / "STATUS.md").write_text(self._content, encoding="utf-8")
        return root

    def __exit__(self, *args):
        if self._tmpdir:
            self._tmpdir.cleanup()


# =============================================================================
# --check-deploy-ready tests
# =============================================================================


class TestCheckDeployReady(unittest.TestCase):
    """Test deploy readiness check across task_type × task_size matrix."""

    def test_feature_L_all_approved_allows(self):
        """feature/L with review+qa+security approved → allow."""
        content = make_status_md(
            task_type="feature", task_size="L",
            approvals={"review": "approved", "qa": "approved", "security": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 0, f"Expected allow, got: {out}")

    def test_feature_L_review_pending_denies(self):
        """feature/L with review=pending → deny."""
        content = make_status_md(
            task_type="feature", task_size="L",
            approvals={"review": "pending", "qa": "approved", "security": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 1, f"Expected deny, got: {out}")
            self.assertIn("review", out, f"Deny reason should mention 'review': {out}")

    def test_feature_L_qa_pending_denies(self):
        """feature/L with qa=pending → deny."""
        content = make_status_md(
            task_type="feature", task_size="L",
            approvals={"review": "approved", "qa": "pending", "security": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 1, f"Expected deny, got: {out}")
            self.assertIn("qa", out, f"Deny reason should mention 'qa': {out}")

    def test_feature_S_allows_without_deploy_gates(self):
        """feature/S — deploy phase not in SIZE_ALLOWED_PHASES["S"] → allow."""
        content = make_status_md(
            task_type="feature", task_size="S",
            approvals={},  # all default (pending)
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 0, f"Expected allow (S skips deploy), got: {out}")

    def test_feature_M_allows_without_deploy_gates(self):
        """feature/M — deploy phase not in SIZE_ALLOWED_PHASES["M"] → allow."""
        content = make_status_md(
            task_type="feature", task_size="M",
            approvals={},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 0, f"Expected allow (M skips deploy), got: {out}")

    def test_bugfix_M_review_approved_allows(self):
        """bugfix/M — review is the only required gate → allow when approved."""
        content = make_status_md(
            task_type="bugfix", task_size="M",
            approvals={"review": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 0, f"Expected allow, got: {out}")

    def test_feature_L_review_na_denies_strict(self):
        """feature/L with review=n/a → deny (strict enforcement)."""
        content = make_status_md(
            task_type="feature", task_size="L",
            approvals={"review": "n/a", "qa": "approved", "security": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 1, f"Expected deny (strict), got: {out}")
            self.assertIn("n/a", out, f"Strict deny should mention 'n/a': {out}")

    def test_refactor_L_all_approved_allows(self):
        """refactor/L with all gates approved → allow."""
        content = make_status_md(
            task_type="refactor", task_size="L",
            approvals={"review": "approved", "qa": "approved", "security": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 0, f"Expected allow, got: {out}")

    def test_hotfix_S_allows_even_pending(self):
        """hotfix/S — S size skips deploy → allow regardless of gates."""
        content = make_status_md(
            task_type="hotfix", task_size="S",
            approvals={},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-deploy-ready")
            self.assertEqual(rc, 0, f"Expected allow, got: {out}")


# =============================================================================
# --check-phase-transition tests
# =============================================================================


class TestCheckPhaseTransition(unittest.TestCase):
    """Test phase transition validation across task_size matrix."""

    def test_implement_to_review_gates_met_allows(self):
        """implement→review with brainstorm+plan approved → allow."""
        content = make_status_md(
            phase="review", task_size="L",
            approvals={"brainstorm": "approved", "plan": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "implement", "review")
            self.assertEqual(rc, 0, f"Expected allow, got: {out}")

    def test_implement_to_deploy_skips_denies(self):
        """implement→deploy without review/qa/security → deny."""
        content = make_status_md(
            phase="deploy", task_size="L",
            approvals={},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "implement", "deploy")
            self.assertEqual(rc, 1, f"Expected deny, got: {out}")
            self.assertIn("review", out, f"Deny should mention missing 'review' gate: {out}")

    def test_review_to_qa_review_approved_allows(self):
        """review→qa with review approved → allow."""
        content = make_status_md(
            phase="qa", task_size="L",
            approvals={"review": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "review", "qa")
            self.assertEqual(rc, 0, f"Expected allow, got: {out}")

    def test_review_to_qa_review_pending_denies(self):
        """review→qa with review=pending → deny."""
        content = make_status_md(
            phase="qa", task_size="L",
            approvals={"review": "pending"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "review", "qa")
            self.assertEqual(rc, 1, f"Expected deny, got: {out}")

    def test_brainstorm_to_implement_S_plan_skipped_allows(self):
        """brainstorm→implement for S size (plan phase skipped) → allow."""
        content = make_status_md(
            phase="implement", task_size="S",
            approvals={"brainstorm": "approved", "plan": "n/a"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "brainstorm", "implement")
            self.assertEqual(rc, 0, f"Expected allow (S skips plan), got: {out}")

    def test_brainstorm_to_implement_L_plan_pending_denies(self):
        """brainstorm→implement for L size with plan=pending → deny."""
        content = make_status_md(
            phase="implement", task_size="L",
            approvals={"brainstorm": "approved", "plan": "pending"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "brainstorm", "implement")
            self.assertEqual(rc, 1, f"Expected deny, got: {out}")

    def test_client_phase_transition_always_allows(self):
        """Client phase transitions are not validated → allow."""
        content = make_status_md(phase="onboard", task_size="L")
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "onboard", "discovery")
            self.assertEqual(rc, 0, f"Expected allow (Client phases), got: {out}")

    def test_qa_to_security_qa_approved_allows(self):
        """qa→security with qa approved → allow."""
        content = make_status_md(
            phase="security", task_size="L",
            approvals={"review": "approved", "qa": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "qa", "security")
            self.assertEqual(rc, 0, f"Expected allow, got: {out}")

    def test_implement_to_security_skip_denies(self):
        """implement→security with review+qa approved → deny (phase skip)."""
        content = make_status_md(
            phase="security", task_size="L",
            approvals={"review": "approved", "qa": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "implement", "security")
            self.assertEqual(rc, 1, f"Expected deny (phase skip), got: {out}")
            self.assertIn("skip", out.lower())

    def test_review_to_ship_S_skips_qa_security_deploy_allows(self):
        """review→ship for S size (qa/security/deploy skipped) → allow."""
        content = make_status_md(
            phase="ship", task_size="S",
            approvals={"review": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "review", "ship")
            self.assertEqual(rc, 0, f"Expected allow (S skips qa/security/deploy), got: {out}")

    def test_backward_transition_always_allows(self):
        """review→implement (backward/rework) → always allow."""
        content = make_status_md(phase="implement", task_size="L")
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-phase-transition", "review", "implement")
            self.assertEqual(rc, 0, f"Expected allow (backward), got: {out}")


# =============================================================================
# Hook-level integration tests (shell scripts → deny JSON)
# =============================================================================


class TempProjectWithHooks(TempProject):
    """Extended temp project that copies hook scripts so ROOT resolves to temp dir.

    Hooks compute ROOT from their own filesystem location (SCRIPT_DIR/..),
    so we must place hook files inside the temp project for correct resolution.
    """

    def __enter__(self) -> str:
        root = super().__enter__()
        root_path = Path(root)

        # Symlink scripts/ so check_status.py is importable.
        (root_path / "scripts").symlink_to(ROOT / "scripts")

        # Copy hook files into temp project so ROOT resolves correctly.
        hooks_dir = root_path / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "extract-input.sh").symlink_to(
            ROOT / "hooks" / "lib" / "extract-input.sh"
        )
        (lib_dir / "emit.sh").symlink_to(
            ROOT / "hooks" / "lib" / "emit.sh"
        )
        # Copy each hook script (not symlink — so dirname resolves to temp).
        import shutil
        for hook_name in [
            "check-deploy-gate.sh",
            "check-deploy-mcp-gate.sh",
            "post-status-audit.sh",
        ]:
            src = ROOT / "hooks" / hook_name
            if src.exists():
                shutil.copy2(src, hooks_dir / hook_name)
        return root


def run_hook(hook_name: str, tmp_root: str, stdin_json: str) -> tuple[int, str]:
    """Run a hook shell script (by name) from the temp project's hooks/ dir."""
    hook_path = str(Path(tmp_root) / "hooks" / hook_name)
    result = subprocess.run(
        ["bash", hook_path],
        input=stdin_json,
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": tmp_root},
        cwd=tmp_root,
    )
    return result.returncode, result.stdout.strip()


class TestDeployGateHookDenyJSON(unittest.TestCase):
    """Verify check-deploy-gate.sh emits proper deny JSON (not silent exit)."""

    HOOK_NAME = "check-deploy-gate.sh"
    # Minimal PreToolUse Bash input with a deploy command.
    DEPLOY_INPUT = '{"tool_name":"Bash","tool_input":{"command":"vercel deploy --prod"}}'
    # Read-only command that contains 'deploy' as argument (should NOT trigger).
    READONLY_INPUT = '{"tool_name":"Bash","tool_input":{"command":"rg deploy docs/"}}'

    def test_deny_emits_json(self):
        """When gates not met, hook must emit permissionDecision:deny JSON."""
        content = make_status_md(
            task_type="feature", task_size="L", phase="deploy",
            approvals={"review": "pending"},
        )
        with TempProjectWithHooks(content) as root:
            rc, out = run_hook(self.HOOK_NAME, root, self.DEPLOY_INPUT)
            self.assertEqual(rc, 0, f"Hook should exit 0 even on deny, got rc={rc}")
            self.assertIn('"permissionDecision":"deny"', out,
                          f"Expected deny JSON, got: {out}")
            self.assertIn("[deploy-gate]", out, f"Deny message should include tag: {out}")

    def test_allow_emits_empty_json(self):
        """When all gates met, hook must emit empty JSON."""
        content = make_status_md(
            task_type="feature", task_size="L", phase="deploy",
            approvals={"review": "approved", "qa": "approved", "security": "approved"},
        )
        with TempProjectWithHooks(content) as root:
            rc, out = run_hook(self.HOOK_NAME, root, self.DEPLOY_INPUT)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}")

    def test_readonly_deploy_word_not_triggered(self):
        """Read-only command containing 'deploy' should not trigger the hook."""
        content = make_status_md(
            task_type="feature", task_size="L", phase="deploy",
            approvals={"review": "pending"},
        )
        with TempProjectWithHooks(content) as root:
            rc, out = run_hook(self.HOOK_NAME, root, self.READONLY_INPUT)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}")


# =============================================================================
# MCP deploy gate hook tests
# =============================================================================


class TestMCPDeployGateHook(unittest.TestCase):
    """Verify check-deploy-mcp-gate.sh emits proper deny/allow JSON for MCP deploy tools."""

    HOOK_NAME = "check-deploy-mcp-gate.sh"
    # Vercel deploy MCP tool input.
    VERCEL_DEPLOY_INPUT = '{"tool_name":"mcp__claude_ai_Vercel__deploy_to_vercel","tool_input":{"project_id":"xxx"}}'

    def test_mcp_vercel_deploy_deny_json(self):
        """MCP Vercel deploy with gates not met → deny JSON."""
        content = make_status_md(
            task_type="feature", task_size="L", phase="deploy",
            approvals={"review": "pending"},
        )
        with TempProjectWithHooks(content) as root:
            rc, out = run_hook(self.HOOK_NAME, root, self.VERCEL_DEPLOY_INPUT)
            self.assertEqual(rc, 0, f"Hook should exit 0 even on deny, got rc={rc}")
            self.assertIn('"permissionDecision":"deny"', out,
                          f"Expected deny JSON, got: {out}")
            self.assertIn("[deploy-gate-mcp]", out, f"Deny message should include MCP tag: {out}")

    def test_mcp_vercel_deploy_allow_json(self):
        """MCP Vercel deploy with all gates met → empty JSON (allow)."""
        content = make_status_md(
            task_type="feature", task_size="L", phase="deploy",
            approvals={"review": "approved", "qa": "approved", "security": "approved"},
        )
        with TempProjectWithHooks(content) as root:
            rc, out = run_hook(self.HOOK_NAME, root, self.VERCEL_DEPLOY_INPUT)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}")

    def test_mcp_deploy_small_task_allows(self):
        """MCP deploy with task_size=S → allow (deploy phase skipped)."""
        content = make_status_md(
            task_type="feature", task_size="S", phase="review",
            approvals={},
        )
        with TempProjectWithHooks(content) as root:
            rc, out = run_hook(self.HOOK_NAME, root, self.VERCEL_DEPLOY_INPUT)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}")

    def test_matcher_covers_deploy_tools(self):
        """Matcher regex must match known deploy MCP tool names."""
        import re
        matcher = re.compile(r"mcp__.*__deploy.*")
        deploy_tools = [
            "mcp__claude_ai_Vercel__deploy_to_vercel",
            "mcp__claude_ai_Vercel__deploy_preview",
            "mcp__firebase__deploy_hosting",
        ]
        for tool in deploy_tools:
            self.assertRegex(tool, matcher, f"Matcher should cover: {tool}")

    def test_matcher_excludes_non_deploy(self):
        """Matcher regex must NOT match non-deploy MCP tool names."""
        import re
        matcher = re.compile(r"mcp__.*__deploy.*")
        non_deploy_tools = [
            "mcp__github__push_files",
            "mcp__github__get_file_contents",
            "mcp__github__create_pull_request",
            "mcp__claude_ai_Vercel__list_deployments",
            "mcp__claude_ai_Vercel__get_deployment",
            "mcp__memory__create_entities",
        ]
        for tool in non_deploy_tools:
            self.assertNotRegex(tool, matcher, f"Matcher should NOT cover: {tool}")

    def test_matcher_valid_js_regex(self):
        """All matchers in hooks.template.json must be valid JS RegExp and match
        identically in both Python re and JS RegExp for known tool names.

        This narrows (but does not close) the gap between unit-test regex
        validation and Claude Code runtime behaviour, which evaluates matchers
        as JS RegExp.
        """
        import json
        import shutil
        node = shutil.which("node")
        if node is None:
            self.skipTest("node not available — JS regex cross-check skipped")
        template_path = ROOT / "templates" / "hooks.template.json"
        with open(template_path, encoding="utf-8") as f:
            template = json.load(f)
        # Collect all matchers from the template.
        matchers: list[str] = []
        for _event, entries in template.get("hooks", {}).items():
            for entry in entries:
                m = entry.get("matcher")
                if m:
                    matchers.append(m)
        self.assertTrue(len(matchers) > 0, "No matchers found in template")
        # Cross-check: deploy matcher against known tool names via Node.js.
        # v0.13.0 Phase 0b: matcher was narrowed from the broad regex
        # `mcp__.*__deploy.*` (which also caught get_deployment*/list_deployments)
        # to the literal `mcp__claude_ai_Vercel__deploy_to_vercel`. Other MCP
        # deploy tools (Firebase, etc.) are intentionally NOT covered yet; they
        # will be added as explicit matchers in a later phase when added to the
        # supported MCP set.
        deploy_matcher = "mcp__claude_ai_Vercel__deploy_to_vercel"
        self.assertIn(deploy_matcher, matchers)
        test_cases = [
            ("mcp__claude_ai_Vercel__deploy_to_vercel", True),
            ("mcp__firebase__deploy_hosting", False),  # excluded since Phase 0b narrowing
            ("mcp__github__push_files", False),
            ("mcp__claude_ai_Vercel__list_deployments", False),
        ]
        js_code_parts = [f"const m = new RegExp({json.dumps(deploy_matcher)});"]
        for tool_name, expected in test_cases:
            js_code_parts.append(
                f"if (m.test({json.dumps(tool_name)}) !== {str(expected).lower()}) "
                f"{{ process.stderr.write('JS mismatch: {tool_name}\\n'); process.exit(1); }}"
            )
        js_code = "\n".join(js_code_parts)
        result = subprocess.run(
            [node, "-e", js_code], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"JS regex cross-check failed: {result.stderr.strip()}")


# =============================================================================
# --pre-approve-gate ref check tests
# =============================================================================


class TestPreApproveGateRefCheck(unittest.TestCase):
    """Verify gate-ref consistency check emits DEPRECATION WARNING."""

    def test_plan_gate_ref_empty_warns(self):
        """Approving 'plan' with empty ref → DEPRECATION WARNING, return 0."""
        content = make_status_md(
            phase="plan", task_size="L",
            approvals={"brainstorm": "approved"},
            refs={"plan": "null"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "plan")
            self.assertEqual(rc, 0, f"Should still allow (deprecation), got: {out}")
            self.assertIn("DEPRECATION WARNING", out,
                          f"Should show deprecation warning: {out}")
            self.assertIn("v0.13.0", out,
                          f"Should mention target version: {out}")

    def test_plan_gate_ref_set_no_warning(self):
        """Approving 'plan' with ref set → no warning."""
        content = make_status_md(
            phase="plan", task_size="L",
            approvals={"brainstorm": "approved"},
            refs={"plan": "docs/plans/my-plan.md"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "plan")
            self.assertEqual(rc, 0)
            self.assertNotIn("DEPRECATION WARNING", out)

    def test_review_gate_ref_empty_warns(self):
        """Approving 'review' with empty ref → DEPRECATION WARNING."""
        content = make_status_md(
            phase="review", task_size="L",
            approvals={"brainstorm": "approved", "plan": "approved"},
            refs={"review": "null"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "review")
            self.assertEqual(rc, 0)
            self.assertIn("DEPRECATION WARNING", out,
                          f"review ref empty should warn: {out}")

    def test_deploy_gate_ref_empty_warns(self):
        """Approving 'deploy' with empty ref → DEPRECATION WARNING."""
        content = make_status_md(
            phase="deploy", task_size="L",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "review": "approved", "qa": "approved", "security": "approved",
            },
            refs={"deploy": "null"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "deploy")
            self.assertEqual(rc, 0)
            self.assertIn("DEPRECATION WARNING", out,
                          f"deploy ref empty should warn: {out}")

    def test_brainstorm_gate_no_ref_check(self):
        """Approving 'brainstorm' (no ref mapping) → no warning."""
        content = make_status_md(
            phase="brainstorm", task_size="L",
            approvals={},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "brainstorm")
            self.assertEqual(rc, 0)
            self.assertNotIn("DEPRECATION WARNING", out)

    def test_existing_status_no_ref_migration(self):
        """Existing STATUS.md with all refs null → can still approve gates (migration path)."""
        content = make_status_md(
            phase="review", task_size="L",
            approvals={"brainstorm": "approved", "plan": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "review")
            # Must succeed (return 0) — this is the migration guarantee.
            self.assertEqual(rc, 0, f"Migration path broken: {out}")


# =============================================================================
# --check-status-health tests
# =============================================================================


class TestStatusHealth(unittest.TestCase):
    """Verify STATUS.md health check warnings."""

    def test_fresh_status_no_warnings(self):
        """Recently updated STATUS.md → no warnings."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        content = make_status_md(phase="implement")
        # Replace the fixed date with now.
        content = content.replace('"2026-01-01"', f'"{now}"')
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-status-health")
            self.assertEqual(rc, 0)
            self.assertNotIn("HEALTH:", out)

    def test_stale_last_updated_warns(self):
        """last_updated 8 days ago → staleness warning."""
        content = make_status_md(phase="implement")
        # Default last_updated is "2026-01-01" which is very old.
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-status-health")
            self.assertEqual(rc, 0)
            self.assertIn("HEALTH:", out, f"Should have health warning: {out}")
            self.assertIn("last_updated", out, f"Warning should mention staleness: {out}")

    def test_boundary_7_days_no_warning(self):
        """Exactly 7 days old → no staleness warning (boundary)."""
        from datetime import datetime, timezone, timedelta
        boundary = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        content = make_status_md(phase="implement")
        content = content.replace('"2026-01-01"', f'"{boundary}"')
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-status-health")
            self.assertEqual(rc, 0)
            # 7 days is the boundary — should NOT warn.
            self.assertNotIn("last_updated", out)

    def test_max_evidence_warns(self):
        """3 external_evidence entries → archive warning."""
        content = make_status_md(phase="implement")
        # Insert external_evidence with 3 dict entries before the closing ---.
        evidence = (
            "external_evidence:\n"
            '  - type: "ev-1"\n'
            '    scope: "scope-1"\n'
            '  - type: "ev-2"\n'
            '    scope: "scope-2"\n'
            '  - type: "ev-3"\n'
            '    scope: "scope-3"\n'
        )
        content = content.replace("session_history: []\n", f"session_history: []\n{evidence}")
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-status-health")
            self.assertEqual(rc, 0)
            self.assertIn("HEALTH:", out, f"Should have health warning: {out}")
            self.assertIn("external_evidence", out,
                          f"Warning should mention evidence archival: {out}")

    def test_docs_phase_no_staleness_warn(self):
        """phase=docs with stale date → no staleness warning (exempt)."""
        content = make_status_md(phase="docs")
        # Default "2026-01-01" is very old but docs phase is exempt.
        with TempProject(content) as root:
            rc, out = run_check(root, "--check-status-health")
            self.assertEqual(rc, 0)
            self.assertNotIn("last_updated", out)


class TestPhaseSkipHookDenyJSON(unittest.TestCase):
    """Verify post-status-audit.sh emits proper deny JSON for phase skips."""

    HOOK_NAME = "post-status-audit.sh"

    def _make_snapshot(self, root: str, phase: str, gates: dict[str, str]) -> None:
        """Create .claude/.gate-snapshot with phase and gate data."""
        snapshot_dir = Path(root) / ".claude"
        snapshot_dir.mkdir(exist_ok=True)
        gate_lines = "\n".join(f"  {k}: {v}" for k, v in gates.items())
        snapshot = f"gate_approvals:\n{gate_lines}\nphase: {phase}\n"
        (snapshot_dir / ".gate-snapshot").write_text(snapshot, encoding="utf-8")

    def test_phase_skip_deny_emits_json(self):
        """implement→security skip must emit deny JSON, not silent exit."""
        # Gates in STATUS.md must MATCH snapshot gates to avoid gate-tamper
        # firing before the phase transition check.
        status_approvals = {"review": "approved", "qa": "approved"}
        content = make_status_md(
            phase="security", task_size="L",
            approvals=status_approvals,
        )
        with TempProjectWithHooks(content) as root:
            # Snapshot: same gates as STATUS.md, but phase=implement (old phase).
            self._make_snapshot(root, "implement", {
                "client_ready_for_dev": "approved",
                "brainstorm": "approved",
                "plan": "approved",
                "review": "approved",
                "qa": "approved",
                "security": "pending",
                "deploy": "pending",
                "dev_ready_for_client": "pending",
            })
            # PostToolUse input for an Edit on STATUS.md.
            stdin = '{"tool_name":"Edit","tool_input":{"file_path":"docs/STATUS.md"}}'
            rc, out = run_hook(self.HOOK_NAME, root, stdin)
            self.assertEqual(rc, 0, f"Hook should exit 0 even on deny, got rc={rc}")
            self.assertIn('"decision":"block"', out,
                          f"Expected block JSON for phase skip, got: {out}")
            self.assertIn("[phase-skip]", out,
                          f"Deny message should include phase-skip tag: {out}")


# =============================================================================
# Profile hooks_include coverage tests
# =============================================================================


class TestProfileHooksInclude(unittest.TestCase):
    """Verify profiles include deploy gate hooks so scaffolded projects are protected."""

    PROFILES_DIR = ROOT / "templates" / "profiles"

    def _load_hooks_include(self, profile_name: str) -> list[str]:
        import json
        profile_path = self.PROFILES_DIR / f"{profile_name}.json"
        with open(profile_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("hooks_include", [])

    def test_full_profile_includes_deploy_gate(self):
        """full.json hooks_include must contain check-deploy-gate.sh."""
        hooks = self._load_hooks_include("full")
        self.assertIn("check-deploy-gate.sh", hooks)

    def test_full_profile_includes_mcp_deploy_gate(self):
        """full.json hooks_include must contain check-deploy-mcp-gate.sh."""
        hooks = self._load_hooks_include("full")
        self.assertIn("check-deploy-mcp-gate.sh", hooks)

    def test_deploy_hooks_in_template_have_profile_coverage(self):
        """Every deploy-gate hook in hooks.template.json must appear in full profile."""
        import json
        template_path = ROOT / "templates" / "hooks.template.json"
        with open(template_path, encoding="utf-8") as f:
            template = json.load(f)
        hooks = self._load_hooks_include("full")
        deploy_scripts = []
        # hooks.template.json: {"hooks": {"PreToolUse": [{matcher, hooks: [{command}]}]}}
        for _event, entries in template.get("hooks", {}).items():
            for entry in entries:
                for hook_def in entry.get("hooks", []):
                    cmd = hook_def.get("command", "")
                    if "deploy" in cmd:
                        script = cmd.split("hooks/")[-1] if "hooks/" in cmd else None
                        if script:
                            deploy_scripts.append(script)
        self.assertTrue(len(deploy_scripts) > 0, "No deploy hooks found in template")
        for script in deploy_scripts:
            self.assertIn(script, hooks,
                          f"Deploy hook {script} missing from full profile hooks_include")


# =============================================================================
# P2d: update-gate.sh action tests (approve / na / reset)
# =============================================================================


class TestUpdateGateActions(unittest.TestCase):
    """Test update-gate.sh approve/na/reset actions."""

    UPDATE_GATE = ROOT / "scripts" / "update-gate.sh"

    def _run_gate(self, root: str, gate: str, action: str = "approve") -> tuple[int, str]:
        """Run update-gate.sh from the temp project's scripts/ dir."""
        local_script = Path(root) / "scripts" / "update-gate.sh"
        result = subprocess.run(
            ["bash", str(local_script), gate, action],
            capture_output=True, text=True,
            cwd=root,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        return result.returncode, (result.stdout + result.stderr).strip()

    def _setup_project(self, root: str, content: str) -> None:
        """Write STATUS.md and set up scripts dir in temp root.

        Copies update-gate.sh (so ROOT resolves to temp dir via dirname)
        and symlinks check_status.py (so pre-approve/pre-na checks work).
        """
        import shutil
        docs = Path(root) / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "STATUS.md").write_text(content, encoding="utf-8")
        # Copy update-gate.sh so ROOT resolves to temp dir.
        scripts_dir = Path(root) / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        shutil.copy2(self.UPDATE_GATE, scripts_dir / "update-gate.sh")
        # Symlink check_status.py so it's available in the same dir.
        (scripts_dir / "check_status.py").symlink_to(
            ROOT / "scripts" / "check_status.py"
        )

    def test_default_action_is_approve(self):
        """No action arg → defaults to approve (backward compat)."""
        content = make_status_md(
            phase="brainstorm",
            approvals={"brainstorm": "pending", "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "brainstorm")
            self.assertEqual(rc, 0, f"Default approve should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: approved", status,
                          f"Gate should be approved in STATUS.md")

    def test_na_action_sets_gate_to_na(self):
        """na action on pending brainstorm gate → set to n/a (bugfix flow)."""
        content = make_status_md(
            phase="brainstorm",
            task_type="bugfix",
            approvals={"brainstorm": "pending", "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "brainstorm", "na")
            self.assertEqual(rc, 0, f"na action should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: n/a", status,
                          f"Gate should be n/a in STATUS.md")

    def test_na_action_blocks_for_already_approved(self):
        """na action on approved gate → error (cannot downgrade)."""
        content = make_status_md(
            phase="brainstorm",
            approvals={"brainstorm": "approved", "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "brainstorm", "na")
            self.assertNotEqual(rc, 0, f"na on approved should fail: {out}")
            self.assertIn("approved", out, f"Error should mention current value: {out}")

    def test_reset_action_sets_gate_to_pending(self):
        """reset action on n/a gate → set back to pending."""
        content = make_status_md(
            phase="brainstorm",
            approvals={"brainstorm": "n/a", "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "brainstorm", "reset")
            self.assertEqual(rc, 0, f"reset action should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: pending", status,
                          f"Gate should be reset to pending in STATUS.md")

    def test_reset_action_blocks_for_pending(self):
        """reset action on already-pending gate → error (no-op)."""
        content = make_status_md(
            phase="brainstorm",
            approvals={"brainstorm": "pending", "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "brainstorm", "reset")
            self.assertNotEqual(rc, 0, f"reset on pending should fail: {out}")

    def test_na_blocked_for_non_brainstorm_plan(self):
        """na action on review gate → error (only brainstorm/plan allow n/a)."""
        content = make_status_md(
            phase="review",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "review": "pending", "client_ready_for_dev": "approved",
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "review", "na")
            self.assertNotEqual(rc, 0, f"na on review should fail: {out}")
            self.assertIn("n/a", out, f"Error should explain n/a restriction: {out}")

    def test_reset_clears_corresponding_ref(self):
        """reset on plan gate must also null current_refs.plan."""
        content = make_status_md(
            phase="implement",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "client_ready_for_dev": "approved",
            },
            refs={"plan": "docs/plans/my-plan.md"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            # Create the ref file so the validator doesn't complain
            plan_dir = Path(tmp) / "docs" / "plans"
            plan_dir.mkdir(parents=True, exist_ok=True)
            (plan_dir / "my-plan.md").write_text("plan", encoding="utf-8")
            rc, out = self._run_gate(tmp, "plan", "reset")
            self.assertEqual(rc, 0, f"reset should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("plan: pending", status,
                          "Gate should be reset to pending")
            # current_refs.plan should be nulled
            import re
            ref_match = re.search(
                r"current_refs:.*?(?=\n[a-z]|\Z)",
                status, re.DOTALL,
            )
            self.assertIsNotNone(ref_match, "current_refs section should exist")
            ref_section = ref_match.group()
            # The plan ref within current_refs must be null
            plan_ref = re.search(r"plan:\s*(\S+)", ref_section)
            self.assertIsNotNone(plan_ref, "plan ref should exist in current_refs")
            self.assertEqual(plan_ref.group(1), "null",
                             f"current_refs.plan should be null after reset, got: {plan_ref.group(1)}")

    def test_reset_clears_translation_for_client_ready_for_dev(self):
        """reset on client_ready_for_dev must null current_refs.translation."""
        content = make_status_md(
            phase="implement",
            approvals={
                "client_ready_for_dev": "approved",
                "brainstorm": "approved", "plan": "approved",
            },
            refs={"translation": "docs/translation/mapping.md"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            trans_dir = Path(tmp) / "docs" / "translation"
            trans_dir.mkdir(parents=True, exist_ok=True)
            (trans_dir / "mapping.md").write_text("mapping", encoding="utf-8")
            rc, out = self._run_gate(tmp, "client_ready_for_dev", "reset")
            self.assertEqual(rc, 0, f"reset should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("client_ready_for_dev: pending", status)
            import re
            ref_match = re.search(
                r"current_refs:.*?(?=\n[a-z]|\Z)",
                status, re.DOTALL,
            )
            ref_section = ref_match.group()
            trans_ref = re.search(r"translation:\s*(\S+)", ref_section)
            self.assertIsNotNone(trans_ref)
            self.assertEqual(trans_ref.group(1), "null",
                             f"current_refs.translation should be null after reset, got: {trans_ref.group(1)}")

    def test_reset_no_ref_gate_only_changes_gate(self):
        """reset on brainstorm (no ref mapping) only changes gate value."""
        content = make_status_md(
            phase="brainstorm",
            approvals={
                "brainstorm": "n/a",
                "client_ready_for_dev": "approved",
            },
            refs={"plan": "docs/plans/keep-this.md"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            plan_dir = Path(tmp) / "docs" / "plans"
            plan_dir.mkdir(parents=True, exist_ok=True)
            (plan_dir / "keep-this.md").write_text("plan", encoding="utf-8")
            rc, out = self._run_gate(tmp, "brainstorm", "reset")
            self.assertEqual(rc, 0, f"reset should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: pending", status)
            # plan ref should be untouched
            import re
            ref_match = re.search(
                r"current_refs:.*?(?=\n[a-z]|\Z)",
                status, re.DOTALL,
            )
            ref_section = ref_match.group()
            plan_ref = re.search(r"plan:\s*(\S+)", ref_section)
            self.assertIsNotNone(plan_ref)
            self.assertEqual(plan_ref.group(1), "docs/plans/keep-this.md",
                             f"Plan ref should be untouched: {plan_ref.group(1)}")

    def test_na_blocked_for_feature_task_type(self):
        """na on brainstorm for feature task → error (feature requires brainstorm)."""
        content = make_status_md(
            phase="brainstorm",
            task_type="feature",
            approvals={"brainstorm": "pending", "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "brainstorm", "na")
            self.assertNotEqual(rc, 0, f"na on feature brainstorm should fail: {out}")
            self.assertIn("feature", out.lower(),
                          f"Error should mention task_type: {out}")

    def test_na_allowed_for_bugfix_task_type(self):
        """na on brainstorm for bugfix task → allowed."""
        content = make_status_md(
            phase="brainstorm",
            task_type="bugfix",
            approvals={"brainstorm": "pending", "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "brainstorm", "na")
            self.assertEqual(rc, 0, f"na on bugfix brainstorm should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: n/a", status)

    def test_na_allowed_for_hotfix_task_type(self):
        """na on plan for hotfix task → allowed."""
        content = make_status_md(
            phase="brainstorm",
            task_type="hotfix",
            approvals={"brainstorm": "n/a", "plan": "pending",
                        "client_ready_for_dev": "approved"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_project(tmp, content)
            rc, out = self._run_gate(tmp, "plan", "na")
            self.assertEqual(rc, 0, f"na on hotfix plan should succeed: {out}")
            status = (Path(tmp) / "docs" / "STATUS.md").read_text()
            self.assertIn("plan: n/a", status)


# =============================================================================
# P2d: post-status-audit.sh all gate change detection
# =============================================================================


class TestPostStatusAuditAllGateChanges(unittest.TestCase):
    """Verify post-status-audit.sh detects ALL gate value changes, not just →approved."""

    HOOK_NAME = "post-status-audit.sh"

    def _make_snapshot(self, root: str, phase: str, gates: dict[str, str],
                       mode: str = "Dev") -> None:
        """Create .claude/.gate-snapshot with phase, mode, and gate data."""
        snapshot_dir = Path(root) / ".claude"
        snapshot_dir.mkdir(exist_ok=True)
        gate_lines = "\n".join(f"  {k}: {v}" for k, v in gates.items())
        snapshot = f"gate_approvals:\n{gate_lines}\nphase: {phase}\nmode: {mode}\n"
        (snapshot_dir / ".gate-snapshot").write_text(snapshot, encoding="utf-8")

    def test_pending_to_na_via_direct_edit_denied(self):
        """Direct edit pending→n/a must be denied (bypass attempt)."""
        status_approvals = {
            "client_ready_for_dev": "approved",
            "brainstorm": "n/a",  # changed from pending
            "plan": "approved",
            "review": "pending", "qa": "pending",
            "security": "pending", "deploy": "pending",
            "dev_ready_for_client": "pending",
        }
        content = make_status_md(phase="implement", approvals=status_approvals)
        with TempProjectWithHooks(content) as root:
            self._make_snapshot(root, "implement", {
                "client_ready_for_dev": "approved",
                "brainstorm": "pending",  # was pending
                "plan": "approved",
                "review": "pending", "qa": "pending",
                "security": "pending", "deploy": "pending",
                "dev_ready_for_client": "pending",
            })
            stdin = '{"tool_name":"Edit","tool_input":{"file_path":"docs/STATUS.md"}}'
            rc, out = run_hook(self.HOOK_NAME, root, stdin)
            self.assertEqual(rc, 0)
            self.assertIn('"decision":"block"', out,
                          f"pending→n/a direct edit should be blocked: {out}")
            self.assertIn("gate-tamper", out,
                          f"Deny message should include gate-tamper tag: {out}")

    def test_approved_to_pending_via_direct_edit_denied(self):
        """Direct edit approved→pending must be denied (reset bypass)."""
        status_approvals = {
            "client_ready_for_dev": "approved",
            "brainstorm": "approved",
            "plan": "pending",  # changed from approved
            "review": "pending", "qa": "pending",
            "security": "pending", "deploy": "pending",
            "dev_ready_for_client": "pending",
        }
        content = make_status_md(phase="implement", approvals=status_approvals)
        with TempProjectWithHooks(content) as root:
            self._make_snapshot(root, "implement", {
                "client_ready_for_dev": "approved",
                "brainstorm": "approved",
                "plan": "approved",  # was approved
                "review": "pending", "qa": "pending",
                "security": "pending", "deploy": "pending",
                "dev_ready_for_client": "pending",
            })
            stdin = '{"tool_name":"Edit","tool_input":{"file_path":"docs/STATUS.md"}}'
            rc, out = run_hook(self.HOOK_NAME, root, stdin)
            self.assertEqual(rc, 0)
            self.assertIn('"decision":"block"', out,
                          f"approved→pending direct edit should be blocked: {out}")

    def test_no_change_passes(self):
        """Same gates in snapshot and STATUS.md → allow."""
        gates = {
            "client_ready_for_dev": "approved",
            "brainstorm": "approved",
            "plan": "approved",
            "review": "pending", "qa": "pending",
            "security": "pending", "deploy": "pending",
            "dev_ready_for_client": "pending",
        }
        content = make_status_md(phase="implement", approvals=gates)
        with TempProjectWithHooks(content) as root:
            self._make_snapshot(root, "implement", gates)
            stdin = '{"tool_name":"Edit","tool_input":{"file_path":"docs/STATUS.md"}}'
            rc, out = run_hook(self.HOOK_NAME, root, stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}", f"No change should pass: {out}")


# =============================================================================
# P1: Client/Dev boundary gate enforcement
# =============================================================================


class TestModeTransitionEnforcement(unittest.TestCase):
    """Verify Client↔Dev boundary checks in check_phase_transition."""

    def test_handover_to_brainstorm_requires_client_ready_for_dev(self):
        """handover→brainstorm without client_ready_for_dev → deny."""
        content = make_status_md(
            mode="Dev", phase="brainstorm",
            approvals={"client_ready_for_dev": "pending"},
        )
        with TempProject(content) as root:
            rc, out = run_check(
                root, "--check-phase-transition", "handover", "brainstorm",
            )
            self.assertNotEqual(rc, 0, f"Should deny without client_ready_for_dev: {out}")
            self.assertIn("client_ready_for_dev", out,
                          f"Error should mention missing gate: {out}")

    def test_handover_to_brainstorm_with_gate_approved_allows(self):
        """handover→brainstorm with client_ready_for_dev approved → allow."""
        content = make_status_md(
            mode="Dev", phase="brainstorm",
            approvals={"client_ready_for_dev": "approved"},
        )
        with TempProject(content) as root:
            rc, out = run_check(
                root, "--check-phase-transition", "handover", "brainstorm",
            )
            self.assertEqual(rc, 0, f"Should allow with client_ready_for_dev: {out}")

    def test_dev_ready_for_client_validates_review_gate(self):
        """dev_ready_for_client pre-approve requires review gate approved."""
        content = make_status_md(
            phase="ship", task_type="feature", task_size="L",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "review": "pending",  # NOT approved
                "qa": "approved", "security": "approved",
            },
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "dev_ready_for_client")
            self.assertNotEqual(rc, 0, f"Should deny without review: {out}")
            self.assertIn("review", out, f"Error should mention review: {out}")

    def test_dev_ready_for_client_all_approved_allows(self):
        """dev_ready_for_client with review approved → allow."""
        content = make_status_md(
            phase="ship", task_type="feature", task_size="L",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "review": "approved", "qa": "approved", "security": "approved",
            },
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "dev_ready_for_client")
            self.assertEqual(rc, 0, f"Should allow with review approved: {out}")


class TestModeChangeAudit(unittest.TestCase):
    """Verify post-status-audit.sh detects unauthorized mode changes."""

    HOOK_NAME = "post-status-audit.sh"

    def _make_snapshot(self, root: str, phase: str, gates: dict[str, str],
                       mode: str = "Dev") -> None:
        """Create .claude/.gate-snapshot with phase, mode, and gate data."""
        snapshot_dir = Path(root) / ".claude"
        snapshot_dir.mkdir(exist_ok=True)
        gate_lines = "\n".join(f"  {k}: {v}" for k, v in gates.items())
        snapshot = f"gate_approvals:\n{gate_lines}\nphase: {phase}\nmode: {mode}\n"
        (snapshot_dir / ".gate-snapshot").write_text(snapshot, encoding="utf-8")

    def test_mode_change_without_gate_denied(self):
        """Direct mode change Client→Dev (same phase) without gate → deny.

        This tests the defense-in-depth mode-tamper check: mode changes
        but phase stays the same, bypassing the phase transition check.
        """
        gates = {
            "client_ready_for_dev": "pending",
            "brainstorm": "pending", "plan": "pending",
            "review": "pending", "qa": "pending",
            "security": "pending", "deploy": "pending",
            "dev_ready_for_client": "pending",
        }
        # Mode changed Client→Dev but phase stays at handover.
        content = make_status_md(mode="Dev", phase="handover", approvals=gates)
        with TempProjectWithHooks(content) as root:
            self._make_snapshot(root, "handover", gates, mode="Client")
            stdin = '{"tool_name":"Edit","tool_input":{"file_path":"docs/STATUS.md"}}'
            rc, out = run_hook(self.HOOK_NAME, root, stdin)
            self.assertEqual(rc, 0)
            self.assertIn('"decision":"block"', out,
                          f"Mode change without gate should be blocked: {out}")
            self.assertIn("mode-tamper", out,
                          f"Deny message should include mode-tamper tag: {out}")

    def test_mode_change_with_gate_approved_passes(self):
        """Mode change Client→Dev (same phase) with gate approved → allow."""
        gates = {
            "client_ready_for_dev": "approved",
            "brainstorm": "pending", "plan": "pending",
            "review": "pending", "qa": "pending",
            "security": "pending", "deploy": "pending",
            "dev_ready_for_client": "pending",
        }
        content = make_status_md(mode="Dev", phase="handover", approvals=gates)
        with TempProjectWithHooks(content) as root:
            self._make_snapshot(root, "handover", gates, mode="Client")
            stdin = '{"tool_name":"Edit","tool_input":{"file_path":"docs/STATUS.md"}}'
            rc, out = run_hook(self.HOOK_NAME, root, stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}", f"Mode change with gate should pass: {out}")


# =============================================================================
# P2a: translation ref contract
# =============================================================================


class TestTranslationRefContract(unittest.TestCase):
    """Verify translation ref is checked in file existence validation and gate-ref mapping."""

    def test_translation_ref_missing_file_fails(self):
        """translation ref pointing to non-existent file → FAIL."""
        content = make_status_md(
            phase="implement",
            refs={"translation": "docs/translation/mapping.md"},
        )
        with TempProject(content) as root:
            rc, out = run_check(root)
            self.assertNotEqual(rc, 0, f"Should fail on missing translation file: {out}")
            self.assertIn("translation", out,
                          f"Failure should mention translation ref: {out}")

    def test_translation_ref_exists_passes(self):
        """translation ref with existing file → no failure from ref check."""
        content = make_status_md(
            phase="implement",
            refs={"translation": "docs/translation/mapping.md"},
        )
        with TempProject(content) as root:
            # Create the referenced file.
            trans_dir = Path(root) / "docs" / "translation"
            trans_dir.mkdir(parents=True)
            (trans_dir / "mapping.md").write_text("# Mapping\n")
            rc, out = run_check(root)
            # Should not fail on translation ref (may fail on other things).
            self.assertNotIn("translation", out,
                             f"Should not complain about existing translation file: {out}")

    def test_client_ready_for_dev_warns_on_empty_translation(self):
        """Approving client_ready_for_dev with empty translation ref → DEPRECATION WARNING."""
        content = make_status_md(
            mode="Client", phase="handover",
            approvals={"client_ready_for_dev": "pending"},
            refs={"translation": "null"},
        )
        with TempProject(content) as root:
            # Create translation/mapping.md so the existing file check passes.
            trans_dir = Path(root) / "docs" / "translation"
            trans_dir.mkdir(parents=True)
            (trans_dir / "mapping.md").write_text("# Mapping\n")
            rc, out = run_check(root, "--pre-approve-gate", "client_ready_for_dev")
            self.assertEqual(rc, 0, f"Should still allow (deprecation): {out}")
            self.assertIn("DEPRECATION WARNING", out,
                          f"Should warn about empty translation ref: {out}")


# =============================================================================
# P2c: secrets hook recursive search
# =============================================================================


class TestSecretsHookMonorepo(unittest.TestCase):
    """Verify check-secrets.sh detects .env files in subdirectories."""

    HOOK_SRC = ROOT / "hooks" / "check-secrets.sh"

    def _setup_git_project(self) -> tuple[tempfile.TemporaryDirectory, str]:
        """Create a temp git project with hooks and lib."""
        import shutil
        tmpdir = tempfile.TemporaryDirectory()
        root = tmpdir.name
        root_path = Path(root)

        # Init git repo so git rev-parse works.
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=root, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "test"],
            cwd=root, capture_output=True,
        )

        # Copy hook and lib.
        hooks_dir = root_path / "hooks"
        hooks_dir.mkdir()
        shutil.copy2(self.HOOK_SRC, hooks_dir / "check-secrets.sh")
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "extract-input.sh").symlink_to(
            ROOT / "hooks" / "lib" / "extract-input.sh"
        )
        (lib_dir / "emit.sh").symlink_to(
            ROOT / "hooks" / "lib" / "emit.sh"
        )
        return tmpdir, root

    def _run_hook(self, root: str, cmd: str) -> tuple[int, str]:
        """Run check-secrets.sh with a Bash command input."""
        hook_path = Path(root) / "hooks" / "check-secrets.sh"
        stdin = f'{{"tool_name":"Bash","tool_input":{{"command":"{cmd}"}}}}'
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": root},
            cwd=root,
        )
        return result.returncode, result.stdout.strip()

    def test_subdirectory_env_detected_on_git_add_all(self):
        """git add -A with .env in subdirectory → deny."""
        tmpdir, root = self._setup_git_project()
        try:
            # Create .env in a subdirectory (monorepo pattern).
            api_dir = Path(root) / "services" / "api"
            api_dir.mkdir(parents=True)
            (api_dir / ".env").write_text("SECRET_KEY=xxx\n")
            rc, out = self._run_hook(root, "git add -A")
            self.assertEqual(rc, 0)
            self.assertIn('"permissionDecision":"deny"', out,
                          f"Subdirectory .env should be detected: {out}")
        finally:
            tmpdir.cleanup()

    def test_safe_variants_excluded(self):
        """git add -A with only .env.example in subdirectory → allow."""
        tmpdir, root = self._setup_git_project()
        try:
            api_dir = Path(root) / "services" / "api"
            api_dir.mkdir(parents=True)
            (api_dir / ".env.example").write_text("SECRET_KEY=\n")
            rc, out = self._run_hook(root, "git add -A")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}", f"Safe .env.example should be allowed: {out}")
        finally:
            tmpdir.cleanup()

    def test_node_modules_excluded(self):
        """git add -A with .env inside node_modules → allow (ignored)."""
        tmpdir, root = self._setup_git_project()
        try:
            nm_dir = Path(root) / "node_modules" / "some-pkg"
            nm_dir.mkdir(parents=True)
            (nm_dir / ".env").write_text("INTERNAL=val\n")
            rc, out = self._run_hook(root, "git add -A")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}", f"node_modules .env should be ignored: {out}")
        finally:
            tmpdir.cleanup()


# =============================================================================
# P2b: templates integrity protection
# =============================================================================


class TestTemplateProtection(unittest.TestCase):
    """Verify check-gate.sh blocks template edits during project work."""

    def _setup_hooks_project(self, task_type: str = "feature") -> tuple[
        tempfile.TemporaryDirectory, str
    ]:
        """Create a temp project with check-gate.sh and STATUS.md."""
        import shutil
        tmpdir = tempfile.TemporaryDirectory()
        root = tmpdir.name
        root_path = Path(root)

        # Create STATUS.md.
        content = make_status_md(
            phase="implement", task_type=task_type,
            approvals={"brainstorm": "approved", "plan": "approved"},
        )
        docs = root_path / "docs"
        docs.mkdir()
        (docs / "STATUS.md").write_text(content, encoding="utf-8")

        # Copy hook and lib.
        hooks_dir = root_path / "hooks"
        hooks_dir.mkdir()
        shutil.copy2(ROOT / "hooks" / "check-gate.sh", hooks_dir / "check-gate.sh")
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "extract-input.sh").symlink_to(
            ROOT / "hooks" / "lib" / "extract-input.sh"
        )
        (lib_dir / "emit.sh").symlink_to(
            ROOT / "hooks" / "lib" / "emit.sh"
        )
        return tmpdir, root

    def _run_hook(self, root: str, file_path: str) -> tuple[int, str]:
        """Run check-gate.sh with an Edit targeting file_path."""
        hook_path = Path(root) / "hooks" / "check-gate.sh"
        stdin = f'{{"tool_name":"Edit","tool_input":{{"file_path":"{file_path}"}}}}'
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            cwd=root,
        )
        return result.returncode, result.stdout.strip()

    def test_template_edit_blocked_during_project_work(self):
        """Edit to templates/ during feature work → deny."""
        tmpdir, root = self._setup_hooks_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, "templates/hooks.template.json")
            self.assertEqual(rc, 0)
            self.assertIn('"permissionDecision":"deny"', out,
                          f"Template edit should be blocked: {out}")
            self.assertIn("integrity", out,
                          f"Deny should mention integrity: {out}")
        finally:
            tmpdir.cleanup()

    def test_template_edit_allowed_for_framework_task(self):
        """Edit to templates/ during framework work → allow."""
        tmpdir, root = self._setup_hooks_project(task_type="framework")
        try:
            rc, out = self._run_hook(root, "templates/hooks.template.json")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}", f"Framework task should allow template edit: {out}")
        finally:
            tmpdir.cleanup()


# =============================================================================
# P1: check-control-plane.sh allowlist redirect bypass
# =============================================================================


class TestControlPlaneAllowlistBypass(unittest.TestCase):
    """Verify check-control-plane.sh blocks allowlisted commands with redirect."""

    HOOK_SRC = ROOT / "hooks" / "check-control-plane.sh"

    def _setup_project(self, task_type: str = "feature") -> tuple[
        tempfile.TemporaryDirectory, str
    ]:
        """Create temp project with check-control-plane.sh and STATUS.md."""
        import shutil
        tmpdir = tempfile.TemporaryDirectory()
        root = tmpdir.name
        root_path = Path(root)

        content = make_status_md(
            phase="implement", task_type=task_type,
            approvals={"brainstorm": "approved", "plan": "approved",
                        "client_ready_for_dev": "approved"},
        )
        docs = root_path / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "STATUS.md").write_text(content, encoding="utf-8")

        hooks_dir = root_path / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        shutil.copy2(self.HOOK_SRC, hooks_dir / "check-control-plane.sh")
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "extract-input.sh").symlink_to(
            ROOT / "hooks" / "lib" / "extract-input.sh"
        )
        (lib_dir / "emit.sh").symlink_to(
            ROOT / "hooks" / "lib" / "emit.sh"
        )
        return tmpdir, root

    def _run_hook(self, root: str, cmd: str) -> tuple[int, str]:
        """Run check-control-plane.sh with a Bash command input."""
        import json
        stdin = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": cmd},
        })
        hook_path = Path(root) / "hooks" / "check-control-plane.sh"
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": root},
            cwd=root,
        )
        return result.returncode, result.stdout.strip()

    def test_allowlisted_script_with_redirect_denied(self):
        """Allowlisted script + > redirect → deny (write bypass attempt)."""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(
                root,
                "python3 scripts/check_status.py --root . > /tmp/pwn.txt",
            )
            self.assertEqual(rc, 0)
            self.assertIn('"permissionDecision":"deny"', out,
                          f"Allowlisted script + redirect should be denied: {out}")
        finally:
            tmpdir.cleanup()

    def test_allowlisted_script_with_append_redirect_denied(self):
        """Allowlisted script + >> redirect → deny."""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(
                root,
                "python3 scripts/check_status.py --root . >> /tmp/pwn.txt",
            )
            self.assertEqual(rc, 0)
            self.assertIn('"permissionDecision":"deny"', out,
                          f"Allowlisted script + >> should be denied: {out}")
        finally:
            tmpdir.cleanup()

    def test_allowlisted_script_plain_allowed(self):
        """Allowlisted script without redirect → allow."""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(
                root,
                "python3 scripts/check_status.py --root .",
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, "{}",
                             f"Plain allowlisted script should be allowed: {out}")
        finally:
            tmpdir.cleanup()

    def test_non_allowlisted_command_with_control_plane_denied(self):
        """Non-allowlisted command referencing control plane → deny."""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(
                root,
                "python3 -c 'open(\"docs/STATUS.md\").read()'",
            )
            self.assertEqual(rc, 0)
            self.assertIn('"permissionDecision":"deny"', out,
                          f"Non-allowlisted control plane command should be denied: {out}")
        finally:
            tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
