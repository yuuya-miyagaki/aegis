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


def run_hook(
    script: str,
    payload: dict,
    *,
    cwd: Path | None = None,
    env: dict | None = None,
) -> tuple[int, dict, str]:
    """Run a hook script with JSON payload on stdin.

    Returns (returncode, parsed_stdout, stderr).
    parsed_stdout is {} if stdout is empty/whitespace/'{}'.

    The optional `env` dict is merged onto os.environ before invoking the hook
    (used by TaskCreated/TaskCompleted tests to set AEGIS_ROOT_OVERRIDE).
    """
    actual_env = os.environ.copy()
    if env:
        actual_env.update(env)
    result = subprocess.run(
        ["bash", str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd or ROOT),
        env=actual_env,
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

    def test_check_secrets_deny_git_add_uppercase_env(self):
        """git add .ENV must deny: on a case-insensitive FS it stages the real
        .env secret (A15/M5)."""
        payload = make_pretool_payload("Bash", {"command": "git add .ENV"})
        rc, out, err = run_hook("check-secrets.sh", payload, cwd=Path(self.tmp))
        self.assertNotEqual(out, {}, "git add .ENV must deny, not pass through")
        self.assert_pretool_decision(out, "deny", hint="check-secrets.sh git add .ENV")

    # --- check-destructive.sh -----------------------------------------

    def test_check_destructive_ask_for_rm_rf(self):
        """rm -rf must ask for confirmation."""
        payload = make_pretool_payload("Bash", {"command": "rm -rf /tmp/foo"})
        rc, out, err = run_hook("check-destructive.sh", payload, cwd=Path(self.tmp))
        if out:
            self.assert_pretool_decision(out, "ask", hint="check-destructive.sh rm -rf")

    # --- check-deploy-gate.sh / check-deploy-mcp-gate.sh / check-client-info.sh -----
    # 残りのケースは個別 hook 修正と並行して追加する。

    # --- check-tdd.sh -------------------------------------------------

    def test_check_tdd_asks_when_no_test_changes(self):
        """AEGIS_TDD_MODE unset (strict default): prod edit without tests -> ask."""
        payload = make_pretool_payload("Edit", {"file_path": "src/app.ts"})
        rc, out, err = run_hook("check-tdd.sh", payload, cwd=Path(self.tmp))
        # 非空を明示 assert（`if out:` ガードだと誤って allow を返しても空振りで PASS する）
        self.assertNotEqual(out, {}, "strict default must not allow ({})")
        self.assert_pretool_decision(out, "ask", hint="check-tdd strict default")

    def test_check_tdd_off_allows(self):
        """AEGIS_TDD_MODE=off: prod edit without tests -> allow (bypass)."""
        payload = make_pretool_payload("Edit", {"file_path": "src/app.ts"})
        rc, out, err = run_hook(
            "check-tdd.sh", payload, cwd=Path(self.tmp), env={"AEGIS_TDD_MODE": "off"}
        )
        self.assertEqual(out, {}, "off must emit allow ({})")

    def test_check_tdd_non_exact_off_keeps_strict(self):
        """Fail-safe: only the lowercase exact value 'off' bypasses; any other
        value (case variant, trailing space, typo) keeps the strict ask."""
        payload = make_pretool_payload("Edit", {"file_path": "src/app.ts"})
        for value in ("OFF", "Off", "off ", "strict", "1", "true"):
            with self.subTest(value=value):
                rc, out, err = run_hook(
                    "check-tdd.sh",
                    payload,
                    cwd=Path(self.tmp),
                    env={"AEGIS_TDD_MODE": value},
                )
                self.assertNotEqual(out, {}, f"{value!r} must not bypass ({{}})")
                self.assert_pretool_decision(out, "ask", hint="check-tdd fail-safe")

    def test_check_deploy_gate_deny_when_gate_pending(self):
        """deploy gate pending 時の vercel deploy で deny。"""
        self._write_status(
            "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
            "gate_approvals:\n  plan: approved\n  deploy: pending\n---\n"
        )
        payload = make_pretool_payload("Bash", {"command": "vercel deploy --prod"})
        # AEGIS_ROOT_OVERRIDE pins the hook to the scratch STATUS. Without it the
        # hook resolves ROOT to its own script-parent (the real repo) and reads the
        # real STATUS.md, so the decision tracked the real task_size (size=S → deploy
        # phase skipped → ASK, not deny). Assert non-vacuously: deny is required.
        rc, out, err = run_hook(
            "check-deploy-gate.sh",
            payload,
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": self.tmp},
        )
        self.assert_pretool_decision(out, "deny", hint="check-deploy-gate.sh vercel deploy")


# ---------------------------------------------------------------------------
# PostToolUse hook (post-status-audit.sh)
# ---------------------------------------------------------------------------


class TestDeployGateStderrSeparation(HookSchemaAssertions):
    """T2 (v1.5.1): check-deploy-gate は判定文面を stdout のみから作る。
    stderr は「RC≠0 かつ stdout 空」の deny 時だけ診断として併合する。
    check_status.py をスタブ化した一時 root + AEGIS_ROOT_OVERRIDE で発火する。"""

    STUB_DENY = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('STDERR_NOISE_MARKER\\n')\n"
        "sys.stdout.write('gate pending: deploy\\n')\n"
        "sys.exit(3)\n"
    )
    STUB_ASK = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('STDERR_NOISE_MARKER\\n')\n"
        "sys.stdout.write('ASK: size-skip deploy confirm\\n')\n"
        "sys.exit(2)\n"
    )
    STUB_SILENT_DENY = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('TRACEBACK_MARKER\\n')\n"
        "sys.exit(3)\n"
    )

    def _root_with_stub(self, stub: str) -> str:
        tmp = tempfile.mkdtemp(prefix="aegis-deploygate-t2-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (Path(tmp) / "docs").mkdir()
        (Path(tmp) / "docs" / "STATUS.md").write_text(
            "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
            "gate_approvals:\n  deploy: pending\n---\n", encoding="utf-8")
        (Path(tmp) / "scripts").mkdir()
        (Path(tmp) / "scripts" / "check_status.py").write_text(
            stub, encoding="utf-8")
        return tmp

    def _fire(self, tmp: str, env_extra: dict | None = None):
        payload = make_pretool_payload("Bash", {"command": "vercel deploy --prod"})
        env = {"AEGIS_ROOT_OVERRIDE": tmp}
        if env_extra:
            env.update(env_extra)
        return run_hook("check-deploy-gate.sh", payload, env=env)

    def test_deny_reason_excludes_stderr(self):
        tmp = self._root_with_stub(self.STUB_DENY)
        rc, out, err = self._fire(tmp)
        self.assert_pretool_decision(out, "deny", hint="T2 deny stdout-only")
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("gate pending: deploy", reason)
        self.assertNotIn("STDERR_NOISE_MARKER", reason)

    def test_ask_reason_excludes_stderr(self):
        tmp = self._root_with_stub(self.STUB_ASK)
        rc, out, err = self._fire(tmp)
        self.assert_pretool_decision(out, "ask", hint="T2 ask stdout-only")
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("size-skip deploy confirm", reason)
        self.assertNotIn("STDERR_NOISE_MARKER", reason)

    def test_empty_stdout_deny_merges_stderr_diagnostic(self):
        tmp = self._root_with_stub(self.STUB_SILENT_DENY)
        rc, out, err = self._fire(tmp)
        self.assert_pretool_decision(out, "deny", hint="T2 diagnostic merge")
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("TRACEBACK_MARKER", reason)

    def test_mktemp_failure_does_not_fail_open(self):
        """TMPDIR 不在で mktemp が死んでも判定経路は維持される（🔴-4）。"""
        tmp = self._root_with_stub(self.STUB_DENY)
        rc, out, err = self._fire(tmp, {"TMPDIR": "/nonexistent-aegis-tmp"})
        self.assert_pretool_decision(out, "deny", hint="T2 mktemp fail-closed")


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

    def test_multiline_test_command_emits_react_guidance(self):
        """改行入りテストコマンドも正規化後に分類される（T1 v1.5.1 回帰ガード。
        grep は行単位 ^ で正規化前も一致するため RED にはならない — judge 側と
        同一の正規化規約を hook にも固定するのが目的）。"""
        tmp = tempfile.mkdtemp(prefix="aegis-postbash-ml-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        payload = {
            "session_id": "t",
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": "echo build done\nvitest run"},
            "tool_response": {"exitCode": 1, "stdout": "", "stderr": "FAIL"},
        }
        rc, out, err = run_hook(
            "post-bash.sh", payload, env={"AEGIS_ROOT_OVERRIDE": tmp})
        self.assertNotEqual(out, {}, "multiline test command must emit ReAct hint")
        self.assert_posttoolfailure_notification(out, hint="post-bash.sh multiline")


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

    # --- P3-2: AEGIS_PRECOMPACT_INTERVAL 改名（旧 ULTRA_ は 1 リリース fallback） ---

    def _run_with_interval_env(self, age_seconds: int, env: dict):
        """repo STATUS.md の mtime を「現在−age_seconds」に設定し、interval
        環境変数つきで実発火する。mtime・環境変数とも必ず原状回復する。"""
        import time
        aegis_status = ROOT / "docs" / "STATUS.md"
        original_mtime = aegis_status.stat().st_mtime
        stale_at = time.time() - age_seconds
        os.utime(aegis_status, (stale_at, stale_at))
        saved = {k: os.environ.get(k) for k in
                 ("AEGIS_PRECOMPACT_INTERVAL", "ULTRA_PRECOMPACT_INTERVAL")}
        for k in saved:
            os.environ.pop(k, None)
        os.environ.update(env)
        try:
            return run_hook("pre-compact.sh", {"hook_event_name": "PreCompact"})
        finally:
            os.utime(aegis_status, (original_mtime, original_mtime))
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_precompact_aegis_env_name_blocks(self):
        """新名 AEGIS_=1 で 60 秒経過 → block（既定 300 なら allow になる差で検証）。"""
        rc, out, err = self._run_with_interval_env(
            60, {"AEGIS_PRECOMPACT_INTERVAL": "1"})
        self.assertTrue(out, "pre-compact.sh must emit JSON (got empty)")
        self.assert_precompact_block(out, rc=rc, hint="AEGIS_ interval=1")

    def test_precompact_legacy_ultra_env_still_blocks(self):
        """旧名 ULTRA_ のみでも fallback で効く（1 リリース互換）。"""
        rc, out, err = self._run_with_interval_env(
            60, {"ULTRA_PRECOMPACT_INTERVAL": "1"})
        self.assertTrue(out, "pre-compact.sh must emit JSON (got empty)")
        self.assert_precompact_block(out, rc=rc, hint="legacy ULTRA_ interval=1")

    def test_precompact_aegis_env_takes_precedence(self):
        """両方設定時は AEGIS_ 優先（AEGIS_=999999999 / ULTRA_=1 → allow）。"""
        rc, out, err = self._run_with_interval_env(
            3600, {"AEGIS_PRECOMPACT_INTERVAL": "999999999",
                   "ULTRA_PRECOMPACT_INTERVAL": "1"})
        self.assertTrue(out, "pre-compact.sh must emit JSON (got empty)")
        self.assert_precompact_allow(out, rc=rc, hint="AEGIS_ wins over ULTRA_")


# ---------------------------------------------------------------------------
# Skill PreToolUse hook (check-skill-gate.sh, v0.13.0 Phase 0b)
# ---------------------------------------------------------------------------


class TestSkillGateHook(HookSchemaAssertions):
    """check-skill-gate.sh: control-plane skills (update-config / keybindings-help /
    fewer-permission-prompts) must trigger ask. Other skills pass through."""

    def _payload(self, skill_name: str) -> dict:
        return make_pretool_payload("Skill", {"skill": skill_name})

    def test_update_config_asks(self):
        rc, out, err = run_hook("check-skill-gate.sh", self._payload("update-config"))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="check-skill-gate update-config")

    def test_keybindings_help_asks(self):
        rc, out, err = run_hook("check-skill-gate.sh", self._payload("keybindings-help"))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="check-skill-gate keybindings-help")

    def test_fewer_permission_prompts_asks(self):
        rc, out, err = run_hook("check-skill-gate.sh", self._payload("fewer-permission-prompts"))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="check-skill-gate fewer-permission-prompts")

    def test_non_control_plane_skill_passes_through(self):
        """A regular skill (e.g. brainstorming) must NOT trigger ask."""
        rc, out, err = run_hook("check-skill-gate.sh", self._payload("brainstorming"))
        self.assertEqual(rc, 0)
        # Pass-through: output is empty dict {} (no permissionDecision).
        self.assertEqual(
            out, {},
            f"non control-plane skill must pass through (empty output), got: {out}",
        )

    def test_missing_skill_name_passes_through(self):
        """Defensive default: if tool_input.skill is missing, allow."""
        payload = make_pretool_payload("Skill", {})
        rc, out, err = run_hook("check-skill-gate.sh", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out, {}, f"missing skill must pass through, got: {out}")


# ---------------------------------------------------------------------------
# CronCreate PreToolUse hook (check-cron-gate.sh, v0.13.0 Phase 0b)
# ---------------------------------------------------------------------------


class TestCronGateHook(HookSchemaAssertions):
    """check-cron-gate.sh: payloads containing deploy/destructive commands must
    trigger ask. Safe payloads pass through."""

    def _payload(self, prompt: str) -> dict:
        return make_pretool_payload("CronCreate", {"prompt": prompt})

    def test_vercel_deploy_in_prompt_asks(self):
        rc, out, err = run_hook("check-cron-gate.sh", self._payload("Run vercel deploy --prod every morning"))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="check-cron-gate vercel deploy")

    def test_rm_rf_in_prompt_asks(self):
        rc, out, err = run_hook("check-cron-gate.sh", self._payload("rm -rf /tmp/old-logs every week"))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="check-cron-gate rm -rf")

    def test_git_force_push_asks(self):
        rc, out, err = run_hook("check-cron-gate.sh", self._payload("git push origin main --force"))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="check-cron-gate git force-push")

    def test_control_char_prompt_emits_valid_json(self):
        """Regression (Round 3 P1): a cron prompt with a control char (\\u0001) plus
        a deploy keyword must still produce VALID ask JSON. The preview embedded in
        the reason must be sanitized to printable, or emit produces malformed JSON."""
        rc, out, err = run_hook("check-cron-gate.sh", self._payload("vercel deploy \u0001 prod"))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="cron-gate control-char prompt")

    def test_safe_prompt_passes_through(self):
        """A benign scheduled task should NOT trigger ask."""
        rc, out, err = run_hook("check-cron-gate.sh", self._payload("Generate a daily report from production logs"))
        self.assertEqual(rc, 0)
        self.assertEqual(out, {}, f"safe payload must pass through, got: {out}")

    def test_empty_prompt_passes_through(self):
        """If we cannot extract a prompt, allow (defensive default)."""
        rc, out, err = run_hook("check-cron-gate.sh", self._payload(""))
        self.assertEqual(rc, 0)
        self.assertEqual(out, {}, f"empty payload must pass through, got: {out}")


# ---------------------------------------------------------------------------
# TaskCreated event hook (check-task-created.sh, v0.13.0 Phase 0b)
# ---------------------------------------------------------------------------


class TestTaskCreatedHook(HookSchemaAssertions):
    """check-task-created.sh: hard stop via {"continue":false,"stopReason":"..."}
    when plan gate is pending during implement phase (Round 4-C 採用方針)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-task-created-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (Path(self.tmp) / "docs").mkdir()
        (Path(self.tmp) / ".claude").mkdir()

    def _write_status(self, *, phase: str, plan_gate: str):
        path = Path(self.tmp) / "docs" / "STATUS.md"
        path.write_text(
            "---\n"
            f"phase: {phase}\n"
            "mode: Dev\n"
            "gate_approvals:\n"
            f"  plan: {plan_gate}\n"
            "---\n"
        )

    def _payload(self, subject: str) -> dict:
        """Official Claude Code Hooks payload key for TaskCreated is task_subject
        (per Hooks reference). Use that as the primary test fixture."""
        return {"task_subject": subject}

    def test_hard_stop_when_plan_pending_in_implement_phase(self):
        self._write_status(phase="implement", plan_gate="pending")
        rc, out, err = run_hook(
            "check-task-created.sh",
            self._payload("Implement new feature foo"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0, "TaskCreated hard-stop emits via JSON, exit code 0")
        self.assertEqual(
            out.get("continue"), False,
            f"hard stop must use continue:false (NOT decision:block). got: {out}",
        )
        self.assertIn("stopReason", out)
        self.assertTrue(out["stopReason"].strip(), "stopReason must be non-empty")
        # PreToolUse-style decision must NOT be present.
        self.assertNotIn(
            "decision", out,
            "TaskCreated uses continue:false, not decision:block (Round 4-C)",
        )

    def test_control_char_subject_emits_valid_json(self):
        """Regression (Round 3 P1): task_subject with a control char (\\u0001) must
        still produce VALID hard-stop JSON. TaskCreated is a safety-boundary hard
        stop, so malformed JSON would fail open (Claude Code ignores unparseable
        output). The preview must be sanitized to printable before emit."""
        self._write_status(phase="implement", plan_gate="pending")
        # run_hook json.loads the stdout; if the hook emits invalid JSON this raises.
        rc, out, err = run_hook(
            "check-task-created.sh",
            self._payload("Implement \u0001 feature"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("continue"), False, f"must hard-stop with valid JSON, got: {out}")
        self.assertIn("stopReason", out)
        self.assertTrue(out["stopReason"].strip())

    def test_pass_through_when_plan_approved(self):
        self._write_status(phase="implement", plan_gate="approved")
        rc, out, err = run_hook(
            "check-task-created.sh",
            self._payload("Implement new feature foo"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, {}, f"plan approved must pass through, got: {out}")

    def test_pass_through_in_plan_phase(self):
        """phase=plan: TaskCreate for planning sub-work is legitimate."""
        self._write_status(phase="plan", plan_gate="pending")
        rc, out, err = run_hook(
            "check-task-created.sh",
            self._payload("Sketch plan for X"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, {}, f"plan phase must allow task creation, got: {out}")

    def test_unparseable_payload_dumps_and_passes(self):
        """fail-safe: parse failure dumps to .claude/.task-event-debug.log and passes."""
        self._write_status(phase="implement", plan_gate="pending")
        rc, out, err = run_hook(
            "check-task-created.sh",
            {"unknown_key": "value"},  # no subject/title/description
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, {})
        log = Path(self.tmp) / ".claude" / ".task-event-debug.log"
        self.assertTrue(log.exists(), "raw_input must be dumped on parse failure")


# ---------------------------------------------------------------------------
# TaskCompleted event hook (check-task-completed.sh, v0.13.0 Phase 0b)
# ---------------------------------------------------------------------------


class TestTaskCompletedHook(HookSchemaAssertions):
    """check-task-completed.sh: 差し戻し via exit 2 + stderr when STATUS.md
    next_action is empty (Round 4-C 採用方針)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-task-completed-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (Path(self.tmp) / "docs").mkdir()
        (Path(self.tmp) / ".claude").mkdir()
        # E1 liveness signal: session-start touches the (possibly empty) log on
        # every session, so its presence is the baseline for completion.
        (Path(self.tmp) / ".claude" / "evidence-log.jsonl").touch()

    def _write_status(self, *, next_action: str):
        path = Path(self.tmp) / "docs" / "STATUS.md"
        path.write_text(
            "---\n"
            "phase: implement\n"
            "mode: Dev\n"
            f"next_action: {next_action}\n"
            "---\n"
        )

    def _payload(self, subject: str) -> dict:
        """Official Claude Code Hooks payload key for TaskCompleted is task_subject
        (per Hooks reference). Use that as the primary test fixture."""
        return {"task_subject": subject}

    def test_push_back_when_next_action_empty(self):
        self._write_status(next_action="")
        rc, out, err = run_hook(
            "check-task-completed.sh",
            self._payload("Task foo done"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        # TaskCompleted: exit 2 + stderr for 差し戻し
        self.assertEqual(rc, 2, "TaskCompleted push-back must exit 2 (NOT continue:false)")
        self.assertEqual(out, {}, "stdout must be empty on push-back; stderr carries reason")
        self.assertIn("task-completed", err)
        self.assertIn("next_action", err)

    def test_pass_through_when_next_action_set(self):
        self._write_status(next_action="Move to qa phase")
        rc, out, err = run_hook(
            "check-task-completed.sh",
            self._payload("Task foo done"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, {}, f"valid completion must pass through, got: {out}")

    def test_push_back_when_next_action_null(self):
        """next_action: null is also treated as empty → push back."""
        self._write_status(next_action="null")
        rc, out, err = run_hook(
            "check-task-completed.sh",
            self._payload("Task done"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 2, "next_action: null must also trigger push-back")

    def test_unparseable_payload_dumps_and_passes(self):
        """fail-safe: parse failure dumps + passes through."""
        self._write_status(next_action="OK")
        rc, out, err = run_hook(
            "check-task-completed.sh",
            {"unknown_key": "value"},
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, {})
        log = Path(self.tmp) / ".claude" / ".task-event-debug.log"
        self.assertTrue(log.exists())

    def _write_status_full(self, *, next_action: str, approvals: dict, refs: dict):
        gate_lines = "\n".join(f"  {k}: {v}" for k, v in approvals.items())
        ref_lines = "\n".join(f"  {k}: {v}" for k, v in refs.items())
        path = Path(self.tmp) / "docs" / "STATUS.md"
        path.write_text(
            "---\n"
            "phase: implement\n"
            "mode: Dev\n"
            f"next_action: {next_action}\n"
            "gate_approvals:\n"
            f"{gate_lines}\n"
            "current_refs:\n"
            f"{ref_lines}\n"
            "---\n"
        )

    def test_push_back_when_evidence_missing(self):
        """qa approved but current_refs.qa null -> exit 2 with evidence reason."""
        self._write_status_full(
            next_action="Move to security phase",
            approvals={"qa": "approved", "review": "pending", "security": "pending",
                       "deploy": "pending", "plan": "pending"},
            refs={"qa": "null", "review": "null", "security": "null",
                  "deploy": "null", "plan": "null", "spec": "null", "translation": "null"},
        )
        rc, out, err = run_hook(
            "check-task-completed.sh", self._payload("QA done"),
            cwd=Path(self.tmp), env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 2, "evidence violation must push back via exit 2")
        self.assertEqual(out, {}, "stdout empty on push-back; stderr carries reason")
        self.assertIn("task-completed", err)
        self.assertIn("qa", err)

    def test_missing_evidence_log_pushes_back(self):
        """E1: no evidence log at all = observer layer never ran -> push back."""
        self._write_status(next_action="Move to qa phase")
        (Path(self.tmp) / ".claude" / "evidence-log.jsonl").unlink()
        rc, out, err = run_hook(
            "check-task-completed.sh",
            self._payload("Task foo done"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 2)
        self.assertEqual(out, {})
        self.assertIn("evidence-log", err)

    def test_empty_evidence_log_passes(self):
        """E1: an EMPTY log is fine (liveness, not activity) -> pass through."""
        self._write_status(next_action="Move to qa phase")
        rc, out, err = run_hook(
            "check-task-completed.sh",
            self._payload("Task foo done"),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, {})

    def test_pass_through_when_evidence_clean(self):
        """All coupled gates pending, refs null, next_action set -> pass through."""
        self._write_status_full(
            next_action="Move to qa phase",
            approvals={"qa": "pending", "review": "pending", "security": "pending",
                       "deploy": "pending", "plan": "pending"},
            refs={"qa": "null", "review": "null", "security": "null",
                  "deploy": "null", "plan": "null", "spec": "null", "translation": "null"},
        )
        rc, out, err = run_hook(
            "check-task-completed.sh", self._payload("Impl step done"),
            cwd=Path(self.tmp), env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(rc, 0, f"clean evidence must pass through, got rc={rc} err={err}")
        self.assertEqual(out, {})


# ---------------------------------------------------------------------------
# extract_exit_code dual-schema support (v0.13.0 Phase 0b)
# ---------------------------------------------------------------------------


class TestExtractExitCode(unittest.TestCase):
    """lib/extract-input.sh の extract_exit_code が tool_response.exitCode と
    tool_result.exit_code の両方を読めること。priority: tool_response > tool_result."""

    def _run(self, payload: dict) -> str:
        script = (
            f"source {HOOKS}/lib/extract-input.sh\n"
            "extract_exit_code \"$(cat)\"\n"
        )
        result = subprocess.run(
            ["bash", "-c", script],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_tool_response_exit_code_camel_case(self):
        """Primary key: tool_response.exitCode (camelCase, Claude Code 2.x suspected)."""
        self.assertEqual(self._run({"tool_response": {"exitCode": 42}}), "42")

    def test_tool_response_exit_code_snake_case(self):
        """Defensive: tool_response.exit_code (snake_case)."""
        self.assertEqual(self._run({"tool_response": {"exit_code": 7}}), "7")

    def test_tool_result_exit_code_legacy(self):
        """Legacy / aegis pre-v0.12.2 schema: tool_result.exit_code."""
        self.assertEqual(self._run({"tool_result": {"exit_code": 13}}), "13")

    def test_priority_tool_response_over_tool_result(self):
        """When both schemas present, tool_response wins (priority order)."""
        payload = {"tool_response": {"exitCode": 1}, "tool_result": {"exit_code": 99}}
        self.assertEqual(self._run(payload), "1")

    def test_default_zero_when_missing(self):
        """No exit code anywhere → default 0."""
        self.assertEqual(self._run({}), "0")

    def test_zero_exit_returned_correctly(self):
        """Exit 0 (success) is distinguished from missing (also defaults to 0)."""
        self.assertEqual(self._run({"tool_response": {"exitCode": 0}}), "0")


# ---------------------------------------------------------------------------
# check-destructive.sh extensions (v0.13.0 Phase 0b)
# ---------------------------------------------------------------------------


class TestCheckDestructiveExtensions(HookSchemaAssertions):
    """v0.13.0 Phase 0b 追加された ask パターン (history-rewriting / bulk-delete)。"""

    def _run(self, command: str):
        return run_hook("check-destructive.sh", make_pretool_payload("Bash", {"command": command}))

    def test_git_filter_branch_asks(self):
        rc, out, err = self._run("git filter-branch --tree-filter 'rm -rf bad' HEAD")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="git filter-branch")

    def test_git_update_ref_delete_asks(self):
        rc, out, err = self._run("git update-ref -d refs/heads/feature")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="git update-ref -d")

    def test_git_reflog_expire_now_asks(self):
        rc, out, err = self._run("git reflog expire --expire=now --all")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="git reflog expire --expire=now")

    def test_npx_rimraf_asks(self):
        rc, out, err = self._run("npx rimraf node_modules")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="npx rimraf")

    def test_find_delete_asks(self):
        rc, out, err = self._run("find /tmp/cache -name '*.log' -delete")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "ask", hint="find -delete")


# ---------------------------------------------------------------------------
# check-secrets.sh high-risk credential patterns (v0.13.0 Phase 0b)
# ---------------------------------------------------------------------------


class TestCheckSecretsHighRisk(HookSchemaAssertions):
    """v0.13.0 Phase 0b: PEM鍵/SSH鍵/credentials.json/service-account.json
    などの高リスク認証ファイルへの git add を deny。"""

    def _run(self, command: str):
        return run_hook("check-secrets.sh", make_pretool_payload("Bash", {"command": command}))

    def test_git_add_pem_denies(self):
        rc, out, err = self._run("git add server.pem")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add *.pem")

    def test_git_add_id_rsa_denies(self):
        rc, out, err = self._run("git add ~/.ssh/id_rsa")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add id_rsa")

    def test_git_add_id_ed25519_denies(self):
        # P2-4: 現代 ssh-keygen 既定の鍵種も検出する。
        rc, out, err = self._run("git add ~/.ssh/id_ed25519")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add id_ed25519")

    def test_git_add_id_ecdsa_pub_denies(self):
        rc, out, err = self._run("git add id_ecdsa.pub")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add id_ecdsa.pub")

    def test_git_add_credentials_json_denies(self):
        rc, out, err = self._run("git add my-credentials.json")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add credentials.json")

    def test_git_add_service_account_denies(self):
        rc, out, err = self._run("git add service-account-key.json")
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add service-account*.json")


# ---------------------------------------------------------------------------
# check-secrets.sh broad staging + commit (v0.13.0 Phase 0b NO-GO fix)
# ---------------------------------------------------------------------------


class TestCheckSecretsBroadStaging(HookSchemaAssertions):
    """v0.13.0 Phase 0b NO-GO fix: broad staging (git add . / git add -A) と
    git commit でも高リスク認証ファイル (PEM/SSH/credentials/service-account) を
    検知して deny する。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-secrets-broad-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # Initialize a minimal git repo so check-secrets.sh's git commands work.
        subprocess.run(["git", "init", "-q", self.tmp], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.tmp, "config", "user.email", "test@example.com"], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.tmp, "config", "user.name", "Test"], check=True, capture_output=True)

    def _payload(self, command: str) -> dict:
        return make_pretool_payload("Bash", {"command": command})

    def test_git_add_dot_with_pem_in_repo_denies(self):
        """git add . when *.pem exists → deny via find-based recursive scan."""
        (Path(self.tmp) / "server.pem").write_text("-----FAKE-----")
        rc, out, err = run_hook("check-secrets.sh", self._payload("git add ."), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add . with *.pem")

    def test_git_add_A_with_id_rsa_denies(self):
        (Path(self.tmp) / "id_rsa").write_text("-----PRIVATE KEY-----")
        rc, out, err = run_hook("check-secrets.sh", self._payload("git add -A"), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add -A with id_rsa")

    def test_git_add_dot_with_credentials_json_denies(self):
        (Path(self.tmp) / "my-credentials.json").write_text("{}")
        rc, out, err = run_hook("check-secrets.sh", self._payload("git add ."), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add . with credentials.json")

    def test_git_add_dot_with_service_account_denies(self):
        (Path(self.tmp) / "service-account-key.json").write_text("{}")
        rc, out, err = run_hook("check-secrets.sh", self._payload("git add ."), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add . with service-account*.json")

    def test_git_commit_with_pem_staged_denies(self):
        """git commit when *.pem is in cached diff → deny via cached scan."""
        pem = Path(self.tmp) / "key.pem"
        pem.write_text("-----FAKE-----")
        subprocess.run(["git", "-C", self.tmp, "add", "key.pem"], check=True, capture_output=True)
        rc, out, err = run_hook("check-secrets.sh", self._payload("git commit -m feat"), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git commit with staged *.pem")

    def test_git_commit_with_id_rsa_staged_denies(self):
        rsa = Path(self.tmp) / "id_rsa"
        rsa.write_text("-----PRIVATE-----")
        subprocess.run(["git", "-C", self.tmp, "add", "id_rsa"], check=True, capture_output=True)
        rc, out, err = run_hook("check-secrets.sh", self._payload("git commit -m feat"), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git commit with staged id_rsa")

    def test_git_add_dot_with_id_ed25519_denies(self):
        # P2-4: broad staging でも ed25519 鍵を検出する。
        (Path(self.tmp) / "id_ed25519").write_text("-----PRIVATE-----")
        rc, out, err = run_hook("check-secrets.sh", self._payload("git add ."), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git add . with id_ed25519")

    def test_git_commit_with_id_ecdsa_staged_denies(self):
        # P2-4: staged commit でも ecdsa 鍵を検出する。
        key = Path(self.tmp) / "id_ecdsa"
        key.write_text("-----PRIVATE-----")
        subprocess.run(["git", "-C", self.tmp, "add", "id_ecdsa"], check=True, capture_output=True)
        rc, out, err = run_hook("check-secrets.sh", self._payload("git commit -m feat"), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assert_pretool_decision(out, "deny", hint="git commit with staged id_ecdsa")

    def test_git_commit_clean_passes_through(self):
        """git commit without high-risk staged → empty {} pass-through."""
        (Path(self.tmp) / "README.md").write_text("hi")
        subprocess.run(["git", "-C", self.tmp, "add", "README.md"], check=True, capture_output=True)
        rc, out, err = run_hook("check-secrets.sh", self._payload("git commit -m feat"), cwd=Path(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(out, {}, f"clean commit must pass through, got: {out}")


# ---------------------------------------------------------------------------
# Audit fix-forward P1 (A1-A4): extraction fidelity, gate fail-closed,
# deploy word-boundary (2026-06-06 audit fix-forward; history in git log).
# ---------------------------------------------------------------------------


def _python3_broken_env(test) -> dict:
    """Return an env whose PATH shadows python3 with a stub that exits 127,
    simulating a missing/broken interpreter. Cleanup registered on `test`.

    grep/sed/bash still resolve from the rest of PATH; only python3 is shadowed,
    so the hook's python3-based extraction fails while the rest of the script runs.
    """
    shim_dir = tempfile.mkdtemp(prefix="aegis-no-python3-")
    test.addCleanup(shutil.rmtree, shim_dir, ignore_errors=True)
    stub = Path(shim_dir) / "python3"
    stub.write_text("#!/bin/sh\nexit 127\n")
    stub.chmod(0o755)
    return {"PATH": f"{shim_dir}:{os.environ.get('PATH', '')}"}


class TestExtractCommandFidelity(HookSchemaAssertions):
    """A3: extract_command must not truncate at an embedded escaped quote.
    A command with a quote BEFORE the dangerous token previously slipped the
    destructive/secrets checks (grep `"[^"]*"` stopped at the first \\")."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-extract-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_escaped_quote_does_not_truncate_destructive(self):
        # Embedded quote precedes `rm -rf`; truncation would hide it and allow.
        cmd = 'echo "done" && rm -rf /tmp/aegis-x'
        rc, out, err = run_hook(
            "check-destructive.sh",
            make_pretool_payload("Bash", {"command": cmd}),
            cwd=Path(self.tmp),
        )
        self.assertNotEqual(
            out, {},
            "escaped-quote command must still be inspected (not truncated to allow)",
        )
        self.assert_pretool_decision(out, "ask", hint="A3 escaped-quote destructive")

    def test_plain_command_still_inspected(self):
        # Control: no embedded quote, grep fast-path still works.
        rc, out, err = run_hook(
            "check-destructive.sh",
            make_pretool_payload("Bash", {"command": "rm -rf /tmp/aegis-y"}),
            cwd=Path(self.tmp),
        )
        self.assert_pretool_decision(out, "ask", hint="A3 plain destructive control")


class TestGateHookFailClosed(HookSchemaAssertions):
    """A1: gate hooks must NOT fail open when python3 is unavailable.
    skill-gate / cron-gate → fail-closed ask; task-created → still evaluates
    the (python3-free) plan-gate condition from STATUS.md and hard-stops."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-failclosed-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_skill_gate_fails_closed_without_python3(self):
        env = _python3_broken_env(self)
        rc, out, err = run_hook(
            "check-skill-gate.sh",
            make_pretool_payload("Skill", {"skill": "update-config"}),
            env=env,
        )
        self.assertNotEqual(out, {}, "python3 unavailable must NOT fail open (was allow {})")
        self.assert_pretool_decision(out, "ask", hint="A1 skill-gate no-python3")

    def test_cron_gate_fails_closed_without_python3(self):
        env = _python3_broken_env(self)
        rc, out, err = run_hook(
            "check-cron-gate.sh",
            make_pretool_payload("CronCreate", {"prompt": "Run vercel deploy --prod nightly"}),
            env=env,
        )
        self.assertNotEqual(out, {}, "python3 unavailable must NOT fail open (was allow {})")
        self.assert_pretool_decision(out, "ask", hint="A1 cron-gate no-python3")

    def test_task_created_hard_stops_without_python3(self):
        (Path(self.tmp) / "docs").mkdir()
        (Path(self.tmp) / ".claude").mkdir()
        (Path(self.tmp) / "docs" / "STATUS.md").write_text(
            "---\nphase: implement\nmode: Dev\ngate_approvals:\n  plan: pending\n---\n"
        )
        env = _python3_broken_env(self)
        env["AEGIS_ROOT_OVERRIDE"] = str(self.tmp)
        rc, out, err = run_hook(
            "check-task-created.sh",
            {"task_subject": "Implement feature foo"},
            cwd=Path(self.tmp),
            env=env,
        )
        self.assertEqual(
            out.get("continue"), False,
            f"python3 unavailable must still hard-stop in implement+plan-pending, got: {out}",
        )
        self.assertIn("stopReason", out)
        self.assertTrue(out["stopReason"].strip())


class TestDeployGateWordBoundary(HookSchemaAssertions):
    """A2: deploy gate must catch deploy commands behind a benign prefix
    (npx / env-assignment / sudo), not only at command start."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-deploy-wb-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (Path(self.tmp) / "docs").mkdir()
        (Path(self.tmp) / "docs" / "STATUS.md").write_text(
            "---\ntask_type: feature\nphase: deploy\nmode: Dev\ntask_size: L\n"
            "gate_approvals:\n  plan: approved\n  review: approved\n  qa: approved\n"
            "  security: approved\n  deploy: pending\n---\n"
        )

    def _expect_deny(self, command: str, hint: str):
        rc, out, err = run_hook(
            "check-deploy-gate.sh",
            make_pretool_payload("Bash", {"command": command}),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertNotEqual(out, {}, f"{hint}: deploy gate pending must deny, got allow {{}}")
        self.assert_pretool_decision(out, "deny", hint=hint)

    def test_bare_vercel_deploy_denies_control(self):
        self._expect_deny("vercel deploy --prod", "A2 control bare vercel deploy")

    def test_npx_prefix_denies(self):
        self._expect_deny("npx vercel deploy --prod", "A2 npx prefix")

    def test_env_assignment_prefix_denies(self):
        self._expect_deny("FOO=bar vercel deploy --prod", "A2 env-assignment prefix")

    def test_read_only_command_passes_through(self):
        # Negative control: referencing a checklist file is not a deploy.
        rc, out, err = run_hook(
            "check-deploy-gate.sh",
            make_pretool_payload("Bash", {"command": "cat docs/DEPLOY-CHECKLIST.template.md"}),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )
        self.assertEqual(out, {}, f"read-only command must pass through, got: {out}")


class TestDeployGateFlagForms(HookSchemaAssertions):
    """P2-2: flag-form vercel (`vercel --prod` = default deploy) と
    wrangler deploy|publish を捕捉。サブコマンド形 (`vercel env ...`) は allow。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-deploy-flag-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (Path(self.tmp) / "docs").mkdir()
        # 実 scripts を配線（無いと python3 が file-not-found RC=2 で deny に
        # 偶然倒れ、ゲートロジック自体を検査しないテストになる）。
        (Path(self.tmp) / "scripts").symlink_to(ROOT / "scripts")
        (Path(self.tmp) / "docs" / "STATUS.md").write_text(
            "---\ntask_type: feature\nphase: deploy\nmode: Dev\ntask_size: L\n"
            "gate_approvals:\n  plan: approved\n  review: approved\n  qa: approved\n"
            "  security: approved\n  deploy: pending\n---\n"
        )

    def _run(self, command: str):
        return run_hook(
            "check-deploy-gate.sh",
            make_pretool_payload("Bash", {"command": command}),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )

    def _expect_deny(self, command: str, hint: str):
        rc, out, err = self._run(command)
        self.assertNotEqual(out, {}, f"{hint}: must deny, got allow {{}}")
        self.assert_pretool_decision(out, "deny", hint=hint)

    def _expect_allow(self, command: str, hint: str):
        rc, out, err = self._run(command)
        self.assertEqual(out, {}, f"{hint}: must pass through, got: {out}")

    # --- deny: flag-form vercel ---

    def test_vercel_prod_denies(self):
        self._expect_deny("vercel --prod", "vercel --prod")

    def test_npx_vercel_prod_denies(self):
        self._expect_deny("npx vercel --prod", "npx vercel --prod")

    def test_vercel_prod_yes_denies(self):
        self._expect_deny("vercel --prod --yes", "vercel --prod --yes")

    def test_vercel_prod_chained_denies(self):
        self._expect_deny("vercel --prod && echo ok", "vercel --prod && chain")

    def test_vercel_prod_redirect_denies(self):
        # グリル穴3: リダイレクト終端でもバイパス不可。
        self._expect_deny("vercel --prod > deploy.log", "vercel --prod > redirect")

    def test_wrangler_deploy_denies(self):
        self._expect_deny("wrangler deploy", "wrangler deploy")

    def test_wrangler_publish_denies(self):
        self._expect_deny("wrangler publish", "wrangler publish")

    # --- allow: non-deploy forms ---

    def test_my_vercel_allowed(self):
        self._expect_allow("my-vercel --prod", "my-vercel prefix")

    def test_vercel_env_ls_allowed(self):
        self._expect_allow("vercel env ls", "vercel env ls")

    def test_vercel_env_pull_prod_allowed(self):
        # グリル穴3: サブコマンド後置 flag は deploy ではない。
        self._expect_allow("vercel env pull --prod", "vercel env pull --prod")

    def test_vercel_dev_allowed(self):
        self._expect_allow("vercel dev", "vercel dev")

    def test_rg_deploy_allowed(self):
        self._expect_allow("rg deploy", "rg deploy")

    def test_cat_checklist_allowed(self):
        self._expect_allow("cat templates/DEPLOY-CHECKLIST.template.md",
                           "cat checklist template")


class TestDeployGateSizeSkipAsk(HookSchemaAssertions):
    """P2-3 (観察4): size-skip (S/M) の deploy は無検査許可ではなく ask。
    RC=2 でも ASK: マーカーが無い出力は deny に倒す。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aegis-deploy-sizeskip-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (Path(self.tmp) / "docs").mkdir()
        (Path(self.tmp) / "scripts").symlink_to(ROOT / "scripts")

    def _write_status(self, task_size: str):
        (Path(self.tmp) / "docs" / "STATUS.md").write_text(
            f"---\ntask_type: feature\nphase: review\nmode: Dev\ntask_size: {task_size}\n"
            "gate_approvals:\n  plan: approved\n---\n"
        )

    def _run(self, command: str = "vercel deploy"):
        return run_hook(
            "check-deploy-gate.sh",
            make_pretool_payload("Bash", {"command": command}),
            cwd=Path(self.tmp),
            env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
        )

    def test_size_S_deploy_asks(self):
        self._write_status("S")
        rc, out, err = self._run()
        self.assertNotEqual(out, {}, "size-skip deploy must ask, got allow {}")
        self.assert_pretool_decision(out, "ask", hint="S size-skip → ask")

    def test_size_M_deploy_asks(self):
        self._write_status("M")
        rc, out, err = self._run()
        self.assertNotEqual(out, {}, "size-skip deploy must ask, got allow {}")
        self.assert_pretool_decision(out, "ask", hint="M size-skip → ask")

    def test_size_L_pending_still_denies(self):
        self._write_status("L")
        rc, out, err = self._run()
        self.assertNotEqual(out, {}, "L pending gates must deny, got allow {}")
        self.assert_pretool_decision(out, "deny", hint="L pending → deny unchanged")

    def test_rc2_without_ask_marker_denies(self):
        """ASK: マーカーの無い RC=2（interpreter 異常等）は deny に倒す。"""
        self._write_status("S")
        scripts = Path(self.tmp) / "scripts"
        scripts.unlink()
        scripts.mkdir()
        (scripts / "check_status.py").write_text(
            "import sys; print('boom'); sys.exit(2)\n", encoding="utf-8")
        rc, out, err = self._run()
        self.assertNotEqual(out, {}, "RC2 w/o marker must deny, got allow {}")
        self.assert_pretool_decision(out, "deny", hint="RC2 without ASK marker → deny")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
