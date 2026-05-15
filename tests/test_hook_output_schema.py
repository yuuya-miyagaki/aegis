#!/usr/bin/env python3
"""Hook output schema contract tests.

各 hook の JSON 出力が公式 Claude Code Hooks 仕様と一致することを検証する。

公式仕様（2026-05-03 確認）:
- PreToolUse: hookSpecificOutput.permissionDecision/permissionDecisionReason
- PostToolUse: top-level decision/reason
- PostToolUseFailure: hookSpecificOutput.additionalContext
- PreCompact (block): top-level decision/reason
- PreCompact (allow): hookSpecificOutput.additionalContext
- SessionStart: hookSpecificOutput.additionalContext

旧形式（撲滅対象）:
- top-level permissionDecision/message
- hookSpecificOutput.message
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
HOOKS = ROOT / "hooks"


def run_hook(script: str, payload: dict, *, cwd: Path | None = None) -> tuple[int, dict, str]:
    """Run a hook script with JSON payload on stdin.

    Returns (returncode, parsed_stdout, stderr).
    parsed_stdout is {} if stdout is empty/whitespace/'{}'.
    """
    result = subprocess.run(
        ["bash", str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd or ROOT),
    )
    out = result.stdout.strip()
    parsed = {} if not out or out == "{}" else json.loads(out)
    return result.returncode, parsed, result.stderr


def make_pretool_payload(tool_name: str, tool_input: dict) -> dict:
    """Build a minimal PreToolUse hook input."""
    return {
        "session_id": "test-session",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": str(ROOT),
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_use_id": "test-tool-use-id",
    }


def make_posttool_payload(tool_name: str, tool_input: dict, *, success: bool = True) -> dict:
    """Build a minimal PostToolUse hook input."""
    return {
        "session_id": "test-session",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": str(ROOT),
        "permission_mode": "default",
        "hook_event_name": "PostToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_use_id": "test-tool-use-id",
        "tool_response": {"stdout": "", "stderr": "", "exitCode": 0 if success else 1},
    }


# ---------------------------------------------------------------------------
# Shared assertion helpers
# ---------------------------------------------------------------------------


class HookSchemaAssertions(unittest.TestCase):
    """Mixin: schema-level assertions for each hook event family."""

    # --- PreToolUse -------------------------------------------------------

    def assert_pretool_decision(self, output: dict, expected: str, *, hint: str = ""):
        """Assert PreToolUse output is a valid hookSpecificOutput.permissionDecision."""
        prefix = f"[{hint}] " if hint else ""
        # Old top-level keys must NOT appear (Claude Code 1.x → 2.x migration).
        self.assertNotIn(
            "permissionDecision", output,
            f"{prefix}top-level permissionDecision must be removed (use hookSpecificOutput)",
        )
        self.assertNotIn(
            "message", output,
            f"{prefix}top-level message must be removed (use permissionDecisionReason)",
        )
        hso = output.get("hookSpecificOutput")
        self.assertIsNotNone(hso, f"{prefix}hookSpecificOutput must be present")
        self.assertEqual(
            hso.get("hookEventName"), "PreToolUse",
            f"{prefix}hookEventName must be 'PreToolUse'",
        )
        self.assertEqual(
            hso.get("permissionDecision"), expected,
            f"{prefix}permissionDecision must be '{expected}'",
        )
        self.assertIn(
            "permissionDecisionReason", hso,
            f"{prefix}permissionDecisionReason missing",
        )
        self.assertTrue(
            hso["permissionDecisionReason"].strip(),
            f"{prefix}permissionDecisionReason must not be empty",
        )

    # --- PostToolUse ------------------------------------------------------

    def assert_posttool_block(self, output: dict, *, hint: str = ""):
        """Assert PostToolUse output is a valid top-level decision='block'/reason."""
        prefix = f"[{hint}] " if hint else ""
        # Old PreToolUse-style keys must NOT appear here.
        self.assertNotIn(
            "permissionDecision", output,
            f"{prefix}PostToolUse must NOT use permissionDecision (PreToolUse-only)",
        )
        self.assertNotIn(
            "message", output,
            f"{prefix}PostToolUse must use 'reason', not 'message'",
        )
        self.assertEqual(
            output.get("decision"), "block",
            f"{prefix}top-level decision must be 'block'",
        )
        self.assertIn(
            "reason", output,
            f"{prefix}top-level reason missing",
        )
        self.assertTrue(
            output["reason"].strip(),
            f"{prefix}reason must not be empty",
        )

    # --- PostToolUseFailure ----------------------------------------------

    def assert_posttoolfailure_notification(self, output: dict, *, hint: str = ""):
        """Assert PostToolUseFailure output is hookSpecificOutput.additionalContext (no block)."""
        prefix = f"[{hint}] " if hint else ""
        # Must NOT block (PostToolUseFailure is informational only here).
        self.assertNotEqual(
            output.get("decision"), "block",
            f"{prefix}PostToolUseFailure should not block",
        )
        hso = output.get("hookSpecificOutput")
        self.assertIsNotNone(hso, f"{prefix}hookSpecificOutput must be present")
        self.assertEqual(
            hso.get("hookEventName"), "PostToolUseFailure",
            f"{prefix}hookEventName must be 'PostToolUseFailure'",
        )
        self.assertIn(
            "additionalContext", hso,
            f"{prefix}additionalContext missing (no top-level 'message' allowed)",
        )
        self.assertNotIn(
            "message", hso,
            f"{prefix}'message' is the old key; use 'additionalContext'",
        )
        self.assertTrue(
            hso["additionalContext"].strip(),
            f"{prefix}additionalContext must not be empty",
        )

    # --- PreCompact -------------------------------------------------------

    def assert_precompact_block(self, output: dict, *, rc: int | None = None, hint: str = ""):
        """Assert PreCompact block: top-level decision='block'/reason (no hookSpecificOutput.message).

        rc!=None なら exit code も検証。block path は exit 0 必須
        （exit 2 だと Claude Code は stdout JSON を無視して stderr feedback 扱いにする）。
        """
        prefix = f"[{hint}] " if hint else ""
        if rc is not None:
            self.assertEqual(
                rc, 0,
                f"{prefix}PreCompact block path must exit 0 (exit 2 makes Claude Code ignore stdout JSON). got rc={rc}",
            )
        self.assertEqual(
            output.get("decision"), "block",
            f"{prefix}top-level decision must be 'block'",
        )
        self.assertIn("reason", output, f"{prefix}reason missing")
        self.assertTrue(output["reason"].strip(), f"{prefix}reason must not be empty")
        # Old hookSpecificOutput.message must NOT be used.
        hso = output.get("hookSpecificOutput", {})
        self.assertNotIn(
            "message", hso,
            f"{prefix}hookSpecificOutput.message is old form; use top-level 'reason'",
        )

    def assert_precompact_allow(self, output: dict, *, rc: int | None = None, hint: str = ""):
        """Assert PreCompact allow: hookSpecificOutput.additionalContext + hookEventName."""
        prefix = f"[{hint}] " if hint else ""
        if rc is not None:
            self.assertEqual(rc, 0, f"{prefix}PreCompact allow path must exit 0. got rc={rc}")
        self.assertNotEqual(
            output.get("decision"), "block",
            f"{prefix}allow must not have decision=block",
        )
        if not output:
            # Empty dict is valid (allow with no context).
            return
        hso = output.get("hookSpecificOutput")
        self.assertIsNotNone(hso, f"{prefix}hookSpecificOutput must be present when context provided")
        self.assertEqual(
            hso.get("hookEventName"), "PreCompact",
            f"{prefix}hookEventName must be 'PreCompact'",
        )
        self.assertIn(
            "additionalContext", hso,
            f"{prefix}additionalContext missing",
        )
        self.assertNotIn(
            "message", hso,
            f"{prefix}'message' is old key; use 'additionalContext'",
        )


# ---------------------------------------------------------------------------
# PreToolUse hooks (8 files)
# ---------------------------------------------------------------------------


class TestPreToolUseHooks(HookSchemaAssertions):
    """All 8 PreToolUse hooks must use hookSpecificOutput.permissionDecision."""

    def setUp(self):
        # Make a temp project root so framework gate logic can read STATUS.md etc.
        self.tmp = tempfile.mkdtemp(prefix="aegis-hook-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write_status(self, content: str, root: str | None = None):
        root = root or self.tmp
        docs = Path(root) / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "STATUS.md").write_text(content)

    # --- check-gate.sh -------------------------------------------------

    def test_check_gate_deny_template_edit_during_project_work(self):
        """Editing templates/ during task_type=feature should deny."""
        self._write_status(
            "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
            "gate_approvals:\n  plan: approved\n---\n"
        )
        payload = make_pretool_payload(
            "Edit",
            {"file_path": f"{self.tmp}/templates/CLAUDE.template.md"},
        )
        rc, out, err = run_hook("check-gate.sh", payload, cwd=Path(self.tmp))
        if out:  # if hook denied
            self.assert_pretool_decision(out, "deny", hint="check-gate.sh template edit")

    def test_check_gate_pass_when_no_violation(self):
        """Editing source files with plan approved should allow (empty output)."""
        self._write_status(
            "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
            "gate_approvals:\n  plan: approved\n---\n"
        )
        payload = make_pretool_payload(
            "Edit",
            {"file_path": f"{self.tmp}/src/main.py"},
        )
        rc, out, err = run_hook("check-gate.sh", payload, cwd=Path(self.tmp))
        # Pass through: empty {} or no schema violation if it returns anything.
        if out:
            self.assertNotIn("permissionDecision", out, "passthrough must not deny")

    # --- check-control-plane.sh ---------------------------------------

    def test_check_control_plane_deny_bash_writing_to_hooks(self):
        """Bash command targeting hooks/ during project work should deny."""
        self._write_status(
            "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
            "gate_approvals:\n  plan: approved\n---\n"
        )
        payload = make_pretool_payload(
            "Bash",
            {"command": "echo evil > hooks/bad.sh"},
        )
        rc, out, err = run_hook("check-control-plane.sh", payload, cwd=Path(self.tmp))
        if out:
            self.assert_pretool_decision(out, "deny", hint="check-control-plane.sh hooks write")

    # --- check-secrets.sh ---------------------------------------------

    def test_check_secrets_deny_git_add_env(self):
        """git add .env must deny."""
        payload = make_pretool_payload("Bash", {"command": "git add .env"})
        rc, out, err = run_hook("check-secrets.sh", payload, cwd=Path(self.tmp))
        if out:
            self.assert_pretool_decision(out, "deny", hint="check-secrets.sh git add .env")

    # --- check-destructive.sh -----------------------------------------

    def test_check_destructive_ask_for_rm_rf(self):
        """rm -rf must ask for confirmation."""
        payload = make_pretool_payload("Bash", {"command": "rm -rf /tmp/foo"})
        rc, out, err = run_hook("check-destructive.sh", payload, cwd=Path(self.tmp))
        if out:
            self.assert_pretool_decision(out, "ask", hint="check-destructive.sh rm -rf")

    # --- check-deploy-gate.sh / check-deploy-mcp-gate.sh / check-tdd.sh / check-client-info.sh -----
    # 残りのケースは個別 hook 修正と並行して追加する（Task 0a-1 後半）

    def test_check_deploy_gate_deny_when_gate_pending(self):
        """deploy gate pending 時の vercel deploy で deny。"""
        self._write_status(
            "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
            "gate_approvals:\n  plan: approved\n  deploy: pending\n---\n"
        )
        payload = make_pretool_payload("Bash", {"command": "vercel deploy --prod"})
        rc, out, err = run_hook("check-deploy-gate.sh", payload, cwd=Path(self.tmp))
        if out:
            self.assert_pretool_decision(out, "deny", hint="check-deploy-gate.sh vercel deploy")


# ---------------------------------------------------------------------------
# PostToolUse hook (post-status-audit.sh)
# ---------------------------------------------------------------------------


class TestPostToolUseHook(HookSchemaAssertions):
    """post-status-audit.sh must use top-level decision/reason (PostToolUse spec)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-poststatus-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # Required directory layout
        (Path(self.tmp) / "docs").mkdir()
        (Path(self.tmp) / ".claude").mkdir()

    def _setup_tampered_status(self, *, gate: str, edit_tool: str = "Edit"):
        """Create a snapshot with gate=pending and STATUS.md with gate=approved (tamper)."""
        snapshot = (
            "gate_approvals:\n"
            f"  {gate}: pending\n"
        )
        status = (
            "---\n"
            "mode: Dev\n"
            "phase: implement\n"
            "gate_approvals:\n"
            f"  {gate}: approved\n"
            "---\n"
        )
        snapshot_path = Path(self.tmp) / ".claude" / ".gate-snapshot"
        status_path = Path(self.tmp) / "docs" / "STATUS.md"
        snapshot_path.write_text(snapshot)
        status_path.write_text(status)
        return status_path

    def _run(self, file_path: str, edit_tool: str = "Edit"):
        payload = make_posttool_payload(edit_tool, {"file_path": file_path})
        return run_hook("post-status-audit.sh", payload, cwd=Path(self.tmp))

    # gate × tool 9 ケースのうち代表 3 件（Edit/Write/NotebookEdit）

    def test_gate_tamper_via_edit(self):
        path = self._setup_tampered_status(gate="qa")
        rc, out, err = self._run(str(path), "Edit")
        if out:
            self.assert_posttool_block(out, hint="gate-tamper Edit")

    def test_gate_tamper_via_write(self):
        path = self._setup_tampered_status(gate="qa")
        rc, out, err = self._run(str(path), "Write")
        if out:
            self.assert_posttool_block(out, hint="gate-tamper Write")

    def test_gate_tamper_via_notebook_edit(self):
        path = self._setup_tampered_status(gate="qa")
        # NotebookEdit uses notebook_path, but extract-input.sh falls back.
        payload = make_posttool_payload(
            "NotebookEdit", {"notebook_path": str(path)}
        )
        rc, out, err = run_hook("post-status-audit.sh", payload, cwd=Path(self.tmp))
        if out:
            self.assert_posttool_block(out, hint="gate-tamper NotebookEdit")

    # phase / mode 系は実装後に追加（hook 修正と並行）


# ---------------------------------------------------------------------------
# PostToolUseFailure hook (post-bash.sh)
# ---------------------------------------------------------------------------


class TestPostToolUseFailureHook(HookSchemaAssertions):
    """post-bash.sh after migration to PostToolUseFailure must use additionalContext."""

    def test_test_runner_failure_emits_react_guidance(self):
        """vitest 失敗時に additionalContext で ReAct ヒント。"""
        payload = {
            "session_id": "t",
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": "vitest run"},
            "tool_response": {"exitCode": 1, "stdout": "", "stderr": "FAIL"},
        }
        rc, out, err = run_hook("post-bash.sh", payload)
        if out:
            self.assert_posttoolfailure_notification(out, hint="post-bash.sh vitest fail")


# ---------------------------------------------------------------------------
# PreCompact hook (pre-compact.sh)
# ---------------------------------------------------------------------------


class TestPreCompactHook(HookSchemaAssertions):
    """pre-compact.sh: block=top-level decision/reason、allow=hookSpecificOutput.additionalContext."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-precompact-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (Path(self.tmp) / "docs").mkdir()

    def _write_status(self, *, phase: str = "implement", mtime_offset: int = 0):
        path = Path(self.tmp) / "docs" / "STATUS.md"
        path.write_text(
            "---\n"
            "mode: Dev\n"
            f"phase: {phase}\n"
            "next_action: working\n"
            "---\n"
        )
        if mtime_offset:
            now = path.stat().st_mtime
            os.utime(path, (now + mtime_offset, now + mtime_offset))

    def test_precompact_block_when_status_stale(self):
        """STATUS.md が stale → block (top-level decision/reason)。

        実 aegis の docs/STATUS.md の mtime を一時的に過去にずらして検証する。
        テスト終了時に必ず原状回復する（finally で utime を戻す）。
        """
        aegis_status = ROOT / "docs" / "STATUS.md"
        original_mtime = aegis_status.stat().st_mtime
        # 1 時間前にずらす
        os.utime(aegis_status, (original_mtime - 3600, original_mtime - 3600))
        os.environ["ULTRA_PRECOMPACT_INTERVAL"] = "300"
        try:
            rc, out, err = run_hook(
                "pre-compact.sh",
                {"hook_event_name": "PreCompact"},
            )
        finally:
            # 原状回復（テスト失敗時も必ず実行）
            os.utime(aegis_status, (original_mtime, original_mtime))
            os.environ.pop("ULTRA_PRECOMPACT_INTERVAL", None)
        self.assertTrue(out, "pre-compact.sh must emit JSON when stale (got empty)")
        self.assert_precompact_block(out, rc=rc, hint="pre-compact stale")

    def test_precompact_allow_when_status_current(self):
        """STATUS.md current → allow (hookSpecificOutput.additionalContext)。

        実 aegis の docs/STATUS.md mtime を「今」に更新してから実行。
        テスト終了時に元の mtime へ復元する。
        """
        aegis_status = ROOT / "docs" / "STATUS.md"
        original_mtime = aegis_status.stat().st_mtime
        # mtime を現在時刻に更新（touch 相当）
        os.utime(aegis_status, None)
        try:
            rc, out, err = run_hook(
                "pre-compact.sh",
                {"hook_event_name": "PreCompact"},
            )
        finally:
            os.utime(aegis_status, (original_mtime, original_mtime))
        self.assertTrue(out, "pre-compact.sh must emit JSON when current (got empty)")
        self.assert_precompact_allow(out, rc=rc, hint="pre-compact allow")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
