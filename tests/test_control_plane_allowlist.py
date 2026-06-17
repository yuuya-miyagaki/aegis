#!/usr/bin/env python3
"""Task 1.3 (OBS-018): the control-plane allowlist must include the
evidence-recording scripts.

record-test-result.py (appends a Bash test observation to the evidence log) and
run-test-strength-drill.py (runs the B1 mutation drill) are invoked by the agent
during normal (non-framework) project work, but their `scripts/...` path matched
the control-plane regex and was DENIED — only check_framework_contract.py /
check_status.py / update-gate.sh were allowlisted. A bare (no-chain, no-redirect)
invocation of either must now be allowed; the allowlist's no-chain guard must be
preserved, so a chained command or a write redirect to control-plane still denies.

Harness mirrors tests/test_control_plane_var_expansion.py: a scratch root with a
feature-task STATUS.md (so the control-plane checks are active, not short-circuited
by task_type=framework), the hook, and the libs it sources.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch_root() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


def _asked(out: str) -> bool:
    return '"permissionDecision":"ask"' in out


class TestEvidenceScriptsAllowlisted(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_record_test_result_bare_is_allowed(self):
        out = _hook(
            self.root,
            "python3 scripts/record-test-result.py --cmd 'pytest tests/' --status ok")
        self.assertTrue(_allowed(out),
                        f"record-test-result must be allowed: {out[:200]!r}")

    def test_run_test_strength_drill_bare_is_allowed(self):
        out = _hook(
            self.root,
            "python3 scripts/run-test-strength-drill.py --root . "
            "--spec docs/qa-reports/test-strength.drill "
            "--report docs/qa-reports/test-strength.md")
        self.assertTrue(_allowed(out),
                        f"run-test-strength-drill must be allowed: {out[:200]!r}")

    def test_record_test_result_with_chain_still_denied(self):
        out = _hook(
            self.root,
            "python3 scripts/record-test-result.py --status ok "
            "&& rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out),
                        f"chained invocation must still deny: {out[:200]!r}")

    def test_run_drill_with_write_redirect_still_denied(self):
        out = _hook(
            self.root,
            "python3 scripts/run-test-strength-drill.py --root . "
            "> hooks/lib/emit.sh")
        self.assertTrue(_denied(out),
                        f"write redirect must still deny: {out[:200]!r}")


class TestBareGitAddStaging(unittest.TestCase):
    """Task 1.4 (OBS-017 catch-22): a fresh non-framework project needs to stage
    the framework files for its baseline commit, but `git add hooks scripts
    templates .claude CLAUDE.md docs` was denied outright. Staging is not a
    content write to a control-plane file (Edit/Write are still required for
    that), so a bare `git add <paths>` should ASK (user confirms), while broad/
    forced staging (-A/--all/-f/--force), chained commands, and content-writing
    git subcommands (apply) keep denying (fail-closed)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_bare_git_add_control_plane_dirs_is_ask(self):
        out = _hook(self.root,
                    "git add hooks scripts templates .claude CLAUDE.md docs")
        self.assertTrue(_asked(out),
                        f"bare baseline staging must ASK, not deny: {out[:200]!r}")

    def test_git_add_force_control_plane_still_denied(self):
        out = _hook(self.root, "git add -f .claude/settings.local.json")
        self.assertTrue(_denied(out),
                        f"-f forced staging must still deny: {out[:200]!r}")

    def test_git_add_all_control_plane_still_denied(self):
        out = _hook(self.root, "git add -A hooks/")
        self.assertTrue(_denied(out),
                        f"-A broad staging must still deny: {out[:200]!r}")

    def test_git_add_chained_still_denied(self):
        out = _hook(self.root, "git add hooks && rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out),
                        f"chained git add must still deny: {out[:200]!r}")

    def test_git_apply_control_plane_still_denied(self):
        out = _hook(self.root, "git apply hooks/evil.patch")
        self.assertTrue(_denied(out),
                        f"git apply (content write) must still deny: {out[:200]!r}")


class TestReadOnlyPipeline(unittest.TestCase):
    """Task 1.5 (OBS-003): a pipe whose EVERY segment is an independently
    read-only command is safe to allow even against control plane (inspection,
    not mutation). Only `|` is tolerated; a write segment, ;, &, &&, ||, <, >,
    $(), `` all keep denying (fail-closed)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # ---- all-read-only pipes against control plane → allow ----
    def test_find_pipe_head_allowed(self):
        out = _hook(self.root, "find hooks/ -type f | head")
        self.assertTrue(_allowed(out),
                        f"all-read-only pipe must be allowed: {out[:200]!r}")

    def test_grep_pipe_head_allowed(self):
        out = _hook(self.root, "grep -rn foo scripts/ | head -5")
        self.assertTrue(_allowed(out),
                        f"all-read-only pipe must be allowed: {out[:200]!r}")

    def test_cat_pipe_wc_allowed(self):
        out = _hook(self.root, "cat .claude/settings.local.json | wc -l")
        self.assertTrue(_allowed(out),
                        f"all-read-only pipe must be allowed: {out[:200]!r}")

    # ---- pipes with a write / other compound operator → deny ----
    def test_find_exec_rm_in_pipe_denied(self):
        out = _hook(self.root, "find hooks/ -type f -exec rm {} + | head")
        self.assertTrue(_denied(out),
                        f"write segment in pipe must deny: {out[:200]!r}")

    def test_pipe_to_tee_denied(self):
        out = _hook(self.root, "grep x scripts/ | tee out.txt")
        self.assertTrue(_denied(out),
                        f"tee write in pipe must deny: {out[:200]!r}")

    def test_and_chain_denied(self):
        out = _hook(self.root, "grep x hooks/ && curl http://evil")
        self.assertTrue(_denied(out),
                        f"&& chain must deny: {out[:200]!r}")

    def test_redirect_denied(self):
        out = _hook(self.root, "cat hooks/x.sh > scripts/y.sh")
        self.assertTrue(_denied(out),
                        f"redirect write must deny: {out[:200]!r}")

    def test_pipe_to_shell_denied(self):
        # Regression for the fail-open found in Task 1.5: tr leaves the LAST
        # pipe segment without a trailing newline and a bare `read` would skip
        # it. `sh` is neither a read-only starter nor a WRITE_INDICATOR keyword,
        # so only checking the last segment for a read-only starter catches it.
        out = _hook(self.root, "cat .claude/settings.local.json | sh")
        self.assertTrue(_denied(out),
                        f"piping control plane into a shell must deny: {out[:200]!r}")


class TestWriteTargetVsMention(unittest.TestCase):
    """Task 1.6 (OBS-006): a control-plane path mentioned only inside a quoted
    string literal (a commit message, an echo argument) that is NOT a write
    target must not be denied. Denial keys on the WRITE TARGET being control
    plane, not on a bare mention. Variable/command-substitution-built targets
    stay fail-closed (ask / broad deny)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # ---- quoted CP mention, not a write target → allow (false positives) ----
    def test_commit_message_mentioning_status_allowed(self):
        out = _hook(self.root, 'git commit -m "update STATUS.md handling"')
        self.assertTrue(_allowed(out),
                        f"CP in a quoted commit message must allow: {out[:200]!r}")

    def test_commit_message_mentioning_scripts_allowed(self):
        out = _hook(self.root, 'git commit -m "fix scripts/foo bug"')
        self.assertTrue(_allowed(out),
                        f"CP in a quoted commit message must allow: {out[:200]!r}")

    def test_echo_quoted_cp_redirect_to_noncp_allowed(self):
        out = _hook(self.root, "echo 'see hooks/ for details' >> notes.txt")
        self.assertTrue(_allowed(out),
                        f"CP in a quoted arg, write target non-CP must allow: {out[:200]!r}")

    def test_echo_quoted_cp_no_redirect_allowed(self):
        out = _hook(self.root, 'echo "edit scripts/foo.py please"')
        self.assertTrue(_allowed(out),
                        f"CP in a quoted echo arg must allow: {out[:200]!r}")

    # ---- write target IS control plane → deny ----
    def test_bare_redirect_to_cp_denied(self):
        out = _hook(self.root, "> hooks/x.sh")
        self.assertTrue(_denied(out),
                        f"redirect to CP must deny: {out[:200]!r}")

    def test_quoted_redirect_target_cp_denied(self):
        out = _hook(self.root, 'echo x > "hooks/lib/emit.sh"')
        self.assertTrue(_denied(out),
                        f"quoted CP write target must deny: {out[:200]!r}")

    def test_unquoted_cp_destination_denied(self):
        out = _hook(self.root, "cp safe.txt hooks/dest.sh")
        self.assertTrue(_denied(out),
                        f"unquoted CP destination must deny: {out[:200]!r}")

    def test_quoted_cp_destination_of_write_util_denied(self):
        # The hole masking could open: a write utility's destination is a QUOTED
        # CP path. Masking hides the CP and it is not a redirect, so a write
        # utility + any raw CP mention must deny (fail-closed).
        out = _hook(self.root, 'cp safe.txt "hooks/dest.sh"')
        self.assertTrue(_denied(out),
                        f"quoted CP write destination must deny: {out[:200]!r}")

    def test_quoted_cp_tee_target_denied(self):
        out = _hook(self.root, 'tee "scripts/evil.py"')
        self.assertTrue(_denied(out),
                        f"quoted CP tee target must deny: {out[:200]!r}")

    def test_sed_inplace_quoted_cp_denied(self):
        out = _hook(self.root, 'sed -i "s/a/b/" "hooks/lib/emit.sh"')
        self.assertTrue(_denied(out),
                        f"sed -i on quoted CP must deny: {out[:200]!r}")

    # Review finding (reviewer): the relaxation must be an ALLOWLIST of known
    # no-write commands, not a blocklist of write utilities — otherwise any
    # in-place writer not on the list (perl -i, patch, awk, sponge, ed, ...) with
    # a QUOTED control-plane target silently bypasses the moat (it denied before).
    def test_perl_inplace_quoted_cp_denied(self):
        out = _hook(self.root, 'perl -i -pe "s/a/b/" "hooks/lib/emit.sh"')
        self.assertTrue(_denied(out),
                        f"perl -i on quoted CP must deny: {out[:200]!r}")

    def test_patch_quoted_cp_denied(self):
        out = _hook(self.root, 'patch "scripts/foo.py" /tmp/p.diff')
        self.assertTrue(_denied(out),
                        f"patch on quoted CP must deny: {out[:200]!r}")

    def test_awk_quoted_cp_denied(self):
        out = _hook(self.root, 'awk "{print}" "templates/x.md"')
        self.assertTrue(_denied(out),
                        f"awk with quoted CP arg must deny (fail-closed): {out[:200]!r}")

    def test_unknown_writer_quoted_cp_denied(self):
        out = _hook(self.root, 'sponge "hooks/lib/emit.sh"')
        self.assertTrue(_denied(out),
                        f"unknown writer with quoted CP must deny: {out[:200]!r}")

    # ---- adversarial: must NOT open a hole ----
    def test_cmdsub_in_quotes_writing_cp_denied(self):
        # CRITICAL: $(...) inside double quotes is STILL executed. Masking the
        # quoted span would hide a destructive cmdsub — so any cmdsub/backtick
        # bails to the broad (fail-closed) check, which denies on the mention.
        out = _hook(self.root, 'echo "$(rm hooks/lib/emit.sh)"')
        self.assertTrue(_denied(out),
                        f"cmdsub writing CP inside quotes must deny: {out[:200]!r}")

    def test_bash_c_redirect_in_quotes_denied(self):
        # `bash -c "... > hooks/x"` executes the quoted redirect, so the raw
        # redirect-target scan keeps it denied (fail-closed over the contrived
        # benign `echo "literal > hooks/x"` case).
        out = _hook(self.root, 'bash -c "validator && malicious > hooks/x"')
        self.assertTrue(_denied(out),
                        f"bash -c with CP redirect must deny: {out[:200]!r}")

    def test_unbalanced_quote_denied(self):
        out = _hook(self.root, 'echo "hooks/')
        self.assertTrue(_denied(out),
                        f"unbalanced quote must fail closed (deny): {out[:200]!r}")

    def test_chain_after_quoted_message_denied(self):
        out = _hook(self.root, "git commit -m 'msg' && rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out),
                        f"unquoted CP after a chain must deny: {out[:200]!r}")

    def test_var_built_redirect_target_still_ask(self):
        out = _hook(self.root, "> $(echo hooks)/lib/emit.sh")
        self.assertTrue(_asked(out) or _denied(out),
                        f"cmdsub-built write target must stay ask/deny: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
