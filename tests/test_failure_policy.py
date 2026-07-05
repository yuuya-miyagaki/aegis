#!/usr/bin/env python3
"""docs/hook-failure-policy.md の宣言と hook 実挙動の突合（観察3）。

表が宣言の単一ソース。本テストは:
  1. 表が hooks/*.sh を過不足なく覆うこと
  2. python3 遮断環境での実 decision が表の宣言と一致すること
  3. 入力パース失敗時に誤 deny しないこと（allow / RC0）
を実発火で検証する。表の陳腐化＝テスト FAIL。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "hook-failure-policy.md"
HOOKS = ROOT / "hooks"

sys.path.insert(0, str(ROOT / "tests"))
from test_hook_output_schema import (  # noqa: E402
    _python3_broken_env,
    make_posttool_payload,
    make_pretool_payload,
    run_hook,
)

ROW_RE = re.compile(
    r"^\| (check-[a-z-]+\.sh|post-[a-z-]+\.sh|explain-[a-z-]+\.sh"
    r"|pre-compact\.sh|session-start\.sh) \|")

# pre-compact staleness must not interfere: pin the interval high under both
# the current and the post-T6 env var names.
FRESH_PRECOMPACT_ENV = {
    "ULTRA_PRECOMPACT_INTERVAL": "99999999",
    "AEGIS_PRECOMPACT_INTERVAL": "99999999",
}


def parse_policy_table() -> dict[str, dict[str, str]]:
    rows = {}
    for line in POLICY.read_text(encoding="utf-8").splitlines():
        if not ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows[cells[0]] = {"class": cells[1], "py_dep": cells[2],
                          "py_absent": cells[3], "parse_fail": cells[4]}
    return rows


def fire_raw(script: str, stdin: str, *, cwd: Path | None = None,
             env_extra: dict | None = None) -> tuple[int, str, str]:
    """Run a hook with a RAW (non-JSON) stdin string."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(["bash", str(HOOKS / script)], input=stdin,
                       capture_output=True, text=True, check=False,
                       cwd=str(cwd or ROOT), env=env)
    return r.returncode, r.stdout.strip(), r.stderr


def decision_of(rc: int, out: dict) -> str:
    """Normalize a hook result to a policy decision keyword."""
    if rc == 2:
        return "exit2"
    if not out:
        return "allow"
    hso = out.get("hookSpecificOutput", {})
    if "permissionDecision" in hso:
        return hso["permissionDecision"]  # deny / ask / allow
    if out.get("continue") is False:
        return "hard-stop"
    if out.get("decision") == "block":
        return "block"
    if "additionalContext" in hso:
        return "allow"
    return f"unknown:{out}"


def _write_status(root: Path, content: str) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "STATUS.md").write_text(content, encoding="utf-8")


FEATURE_STATUS = (
    "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
    "gate_approvals:\n  plan: approved\n---\n"
)
DEPLOY_PENDING_STATUS = (
    "---\ntask_type: feature\nphase: deploy\nmode: Dev\ntask_size: L\n"
    "gate_approvals:\n  plan: approved\n  review: approved\n  qa: approved\n"
    "  security: approved\n  deploy: pending\n---\n"
)
IMPLEMENT_PLAN_PENDING_STATUS = (
    "---\nphase: implement\nmode: Dev\ngate_approvals:\n  plan: pending\n---\n"
)
NEXT_ACTION_STATUS = (
    "---\nphase: implement\nmode: Dev\nnext_action: continue with T2\n---\n"
)


class TestPolicyTableCoverage(unittest.TestCase):
    def test_table_covers_all_hooks(self):
        declared = set(parse_policy_table())
        actual = {p.name for p in HOOKS.glob("*.sh")}
        self.assertEqual(
            declared, actual,
            "policy table out of sync with hooks/*.sh "
            f"(missing: {actual - declared}, stale: {declared - actual})")


class TestPython3AbsentBehavior(unittest.TestCase):
    """表の「python3 不在時」列と、python3 遮断下の実 decision の突合。"""

    def setUp(self):
        self.table = parse_policy_table()
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-policy-test-"))
        import shutil
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _scenarios(self):
        """hook → (payload, cwd, env_extra, expected_decision, declared_substr)."""
        t = self.tmp
        return [
            # check-gate.sh is verified by a dedicated method, not this loop: it
            # resolves ROOT as SCRIPT_DIR/.. (ignoring cwd/AEGIS_ROOT_OVERRIDE), so
            # firing the real hook here reads the LIVE repo STATUS and would pass
            # only by luck of the repo's plan-gate state (iter36 Bug-B class; this
            # surfaced in iter38 rollover when plan=pending made it deny→fail).
            # See test_python3_absent_check_gate_reads_scratch_status.
            ("check-tdd.sh",
             make_pretool_payload("Edit", {"file_path": f"{t}/src/main.py"}),
             t, {"AEGIS_TDD_MODE": "off"}, "allow", "通常判定"),
            ("check-client-info.sh",
             make_pretool_payload("Write", {"file_path": f"{t}/docs/notes.md",
                                            "content": "meeting notes"}),
             t, {}, "allow", "通常判定"),
            ("check-destructive.sh",
             make_pretool_payload("Bash", {"command": "rm -rf /tmp/x"}),
             t, {}, "ask", "通常判定"),
            ("check-secrets.sh",
             make_pretool_payload("Bash", {"command": "git add .env"}),
             t, {}, "deny", "通常判定"),
            ("check-deploy-gate.sh",
             make_pretool_payload("Bash", {"command": "vercel deploy --prod"}),
             t, {"AEGIS_ROOT_OVERRIDE": str(t)}, "deny", "deny"),
            ("check-deploy-mcp-gate.sh",
             make_pretool_payload("mcp__claude_ai_Vercel__deploy_to_vercel", {}),
             ROOT, {}, "deny", "deny"),
            ("check-skill-gate.sh",
             make_pretool_payload("Skill", {"skill": "update-config"}),
             ROOT, {}, "ask", "ask"),
            ("check-cron-gate.sh",
             make_pretool_payload("CronCreate",
                                  {"prompt": "Run vercel deploy --prod nightly"}),
             ROOT, {}, "ask", "ask"),
            ("check-task-created.sh",
             {"task_subject": "Implement feature foo"},
             t, {"AEGIS_ROOT_OVERRIDE": str(t)}, "hard-stop", "hard stop"),
            ("check-task-completed.sh",
             {"task_subject": "Task foo done"},
             t, {"AEGIS_ROOT_OVERRIDE": str(t)}, "exit2", "exit 2"),
        ]

    def test_python3_absent_behavior(self):
        _write_status(self.tmp, FEATURE_STATUS)
        broken = _python3_broken_env(self)
        for hook, payload, cwd, env_extra, expect, declared_substr in self._scenarios():
            with self.subTest(hook=hook):
                row = self.table.get(hook)
                self.assertIsNotNone(row, f"{hook} missing from policy table")
                self.assertIn(
                    declared_substr, row["py_absent"],
                    f"{hook}: table declares '{row['py_absent']}' but test "
                    f"expects a '{declared_substr}' policy — update table or test")
                # Per-hook fixture STATUS (overwrites the shared feature STATUS).
                if hook == "check-deploy-gate.sh":
                    _write_status(self.tmp, DEPLOY_PENDING_STATUS)
                elif hook == "check-task-created.sh":
                    _write_status(self.tmp, IMPLEMENT_PLAN_PENDING_STATUS)
                elif hook == "check-task-completed.sh":
                    _write_status(self.tmp, NEXT_ACTION_STATUS)
                else:
                    _write_status(self.tmp, FEATURE_STATUS)
                env = dict(broken)
                env.update(env_extra)
                rc, out, err = run_hook(hook, payload, cwd=cwd, env=env)
                self.assertEqual(
                    decision_of(rc, out), expect,
                    f"{hook}: declared '{row['py_absent']}', got rc={rc} out={out} "
                    f"stderr={err[:200]}")

    def test_python3_absent_control_plane_raw_fallback_denies(self):
        """check-runtime-state（iter57 で check-control-plane から交代）: ROOT は
        SCRIPT_DIR 解決のため hook を一時 root へコピーし lib を symlink して発火する。
        `\\"` 含み入力で bash fast-path も外れ、raw fallback が runtime-state /
        locked-CP 言及を捕捉して deny（fail-closed）になること。"""
        import shutil
        row = self.table["check-runtime-state.sh"]
        self.assertIn("deny", row["py_absent"])
        _write_status(self.tmp, FEATURE_STATUS)
        hooks_dir = self.tmp / "hooks"
        lib_dir = hooks_dir / "lib"
        lib_dir.mkdir(parents=True)
        shutil.copy2(HOOKS / "check-runtime-state.sh", hooks_dir)
        for lib in ("extract-input.sh", "emit.sh", "frontmatter.sh", "safety.sh"):
            (lib_dir / lib).symlink_to(HOOKS / "lib" / lib)
        broken = _python3_broken_env(self)
        env = os.environ.copy()
        env.update(broken)
        payload = make_pretool_payload(
            "Bash", {"command": 'echo "x" >> docs/STATUS.md'})
        r = subprocess.run(
            ["bash", str(hooks_dir / "check-runtime-state.sh")],
            input=json.dumps(payload), capture_output=True, text=True,
            check=False, cwd=str(self.tmp), env=env)
        out = json.loads(r.stdout) if r.stdout.strip() else {}
        self.assertEqual(
            decision_of(r.returncode, out), "deny",
            f"raw fallback must fail closed, got rc={r.returncode} "
            f"out={r.stdout[:160]} stderr={r.stderr[:160]}")

    def test_python3_absent_check_gate_reads_scratch_status(self):
        """check-gate.sh resolves ROOT as SCRIPT_DIR/.. (it honors neither cwd nor
        AEGIS_ROOT_OVERRIDE), so firing the real hook with cwd=scratch still reads
        the LIVE repo STATUS — the _scenarios() loop only passed by luck of the
        repo's plan-gate state (iter36 Bug-B class; iter38 rollover's plan=pending
        exposed it as a deny→fail). Fire a temp-root COPY (libs copied, not
        symlinked — os.chmod follows symlinks, iter36 Bug A) so ROOT=scratch, and
        assert the py-absent fallback tracks the SCRATCH plan gate at BOTH poles
        (approved→allow '通常判定' / pending→deny) — proving live-STATUS independence."""
        import shutil
        row = self.table["check-gate.sh"]
        self.assertIn("通常判定", row["py_absent"])
        hooks_dir = self.tmp / "hooks"
        (hooks_dir / "lib").mkdir(parents=True)
        shutil.copy2(HOOKS / "check-gate.sh", hooks_dir)
        for lib in ("safety.sh", "extract-input.sh", "emit.sh", "frontmatter.sh"):
            shutil.copy2(HOOKS / "lib" / lib, hooks_dir / "lib")
        env = os.environ.copy()
        env.update(_python3_broken_env(self))
        payload = make_pretool_payload("Edit", {"file_path": f"{self.tmp}/src/main.py"})

        def _decide():
            r = subprocess.run(
                ["bash", str(hooks_dir / "check-gate.sh")],
                input=json.dumps(payload), capture_output=True, text=True,
                check=False, cwd=str(self.tmp), env=env)
            out = json.loads(r.stdout) if r.stdout.strip() else {}
            return decision_of(r.returncode, out), r

        # scratch plan=approved -> allow (faithful to the table's '通常判定').
        _write_status(self.tmp, FEATURE_STATUS)
        decision, r = _decide()
        self.assertEqual(decision, "allow",
                         f"plan=approved scratch must allow, got rc={r.returncode} "
                         f"out={r.stdout[:160]} stderr={r.stderr[:160]}")
        # scratch plan=pending -> deny: the verdict tracks the SCRATCH STATUS, which
        # only holds if the hook reads scratch and not the live repo STATUS.
        _write_status(self.tmp, IMPLEMENT_PLAN_PENDING_STATUS)
        decision, r = _decide()
        self.assertEqual(decision, "deny",
                         f"plan=pending scratch must deny (proves scratch is read), "
                         f"got rc={r.returncode} out={r.stdout[:160]} "
                         f"stderr={r.stderr[:160]}")

    def test_python3_absent_advisory_hooks_do_not_crash(self):
        """advisory hooks: python3 遮断でも RC0（セッションを止めない）。"""
        broken = _python3_broken_env(self)
        # E1 observer hooks write the evidence log; isolate via
        # AEGIS_ROOT_OVERRIDE so the framework repo's own .claude/ is not
        # polluted by test firings.
        ev_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(ev_tmp.cleanup)
        ev_root = {"AEGIS_ROOT_OVERRIDE": ev_tmp.name}
        # post-status-audit resolves its root via CLAUDE_PROJECT_DIR (NOT
        # AEGIS_ROOT_OVERRIDE). Point it at an isolated project whose STATUS.md
        # and .gate-snapshot are in sync, so the audit reaches emit_allow on its
        # own merits — never reading the live repo snapshot, which other tests
        # transiently mutate (the source of an order-dependent flake). Matching
        # phase/mode also keeps us off the python3 transition path, which would
        # (correctly) fail-closed under the broken-python3 env.
        audit_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(audit_tmp.cleanup)
        audit_root = Path(audit_tmp.name)
        (audit_root / "docs").mkdir()
        (audit_root / ".claude").mkdir()
        _synced_gates = (
            "gate_approvals:\n"
            "  client_ready_for_dev: n/a\n"
            "  brainstorm: approved\n"
            "  plan: approved\n"
        )
        (audit_root / "docs" / "STATUS.md").write_text(
            "---\nmode: Dev\nphase: implement\n" + _synced_gates + "---\n",
            encoding="utf-8")
        (audit_root / ".claude" / ".gate-snapshot").write_text(
            _synced_gates + "phase: implement\nmode: Dev\n", encoding="utf-8")
        audit_env = {"CLAUDE_PROJECT_DIR": str(audit_root)}
        cases = [
            ("post-bash.sh",
             json.dumps(make_posttool_payload("Bash", {"command": "ls"})),
             ev_root),
            ("post-bash-observe.sh",
             json.dumps(make_posttool_payload("Bash", {"command": "ls"})),
             ev_root),
            ("post-status-audit.sh",
             json.dumps(make_posttool_payload(
                 "Edit", {"file_path": str(audit_root / "docs" / "STATUS.md")})),
             audit_env),
            ("pre-compact.sh", "{}", FRESH_PRECOMPACT_ENV),
            ("session-start.sh",
             json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
             {}),
        ]
        for hook, stdin, env_extra in cases:
            with self.subTest(hook=hook):
                row = parse_policy_table()[hook]
                self.assertEqual(row["class"], "advisory")
                env = dict(broken)
                env.update(env_extra)
                rc, out, err = fire_raw(hook, stdin, env_extra=env)
                self.assertEqual(
                    rc, 0,
                    f"{hook}: advisory hook must not crash without python3 "
                    f"(rc={rc}, stderr={err[:200]})")
                self.assertNotIn('"decision":"block"', out.replace(" ", ""),
                                 f"{hook}: advisory must not block, got {out[:120]}")


class TestParseFailureAllows(unittest.TestCase):
    """入力パース失敗（非 JSON stdin）は誤 deny しない。"""

    RAW = "not-json{{{"

    def setUp(self):
        self.table = parse_policy_table()
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-policy-parse-"))
        import shutil
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        _write_status(self.tmp, FEATURE_STATUS)

    def test_parse_failure_allows(self):
        # ※2: check-deploy-mcp-gate は stdin 不参照のため対象外。
        # ※1: control-plane は raw fallback — RAW に control plane 言及なし → allow。
        hooks = [h for h, row in self.table.items()
                 if row["parse_fail"].startswith("allow")
                 or h == "check-runtime-state.sh"]
        self.assertGreaterEqual(len(hooks), 14)
        for hook in hooks:
            with self.subTest(hook=hook):
                env_extra: dict = {"AEGIS_ROOT_OVERRIDE": str(self.tmp)}
                env_extra.update(FRESH_PRECOMPACT_ENV)
                rc, out, err = fire_raw(hook, self.RAW, cwd=self.tmp,
                                        env_extra=env_extra)
                self.assertEqual(rc, 0, f"{hook}: rc={rc} stderr={err[:200]}")
                if out and out != "{}":
                    data = json.loads(out)
                    self.assertEqual(
                        decision_of(rc, data), "allow",
                        f"{hook}: parse failure must allow, got {out[:160]}")


if __name__ == "__main__":
    unittest.main()
