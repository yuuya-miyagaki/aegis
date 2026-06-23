"""iter41 I1: post-status-audit.sh is a PostToolUse blocker. When its safety
libs cannot be sourced it previously died under set -e with empty stdout, which
the Claude Code spec reads as allow = fail-open (the gate/mode tamper detector
silently skipped). It must instead emit a PostToolUse {"decision":"block"} and
exit 0 (fail-closed). The byte-identical PreToolUse fallback (12 deny hooks) is
the wrong schema here, so post-status-audit gets its own POSTTOOL fallback and
is NOT part of that identity set."""
import json
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "post-status-audit.sh"


def test_fail_closed_when_safety_lib_missing(tmp_path):
    hooks = tmp_path / "hooks"
    (hooks / "lib").mkdir(parents=True)
    shutil.copy(HOOK, hooks / "post-status-audit.sh")  # copy hook, NO libs
    payload = json.dumps(
        {"tool_input": {"file_path": str(tmp_path / "docs/STATUS.md")}}
    )
    r = subprocess.run(
        ["bash", str(hooks / "post-status-audit.sh")],
        input=payload, capture_output=True, text=True,
    )
    assert '"decision":"block"' in r.stdout, (r.stdout, r.stderr)
    assert r.returncode == 0  # explicit block, not a crash/fail-open


def test_posttool_fallback_emits_block_schema():
    text = HOOK.read_text()
    assert "AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN" in text
    assert "AEGIS_SAFETY_FALLBACK_POSTTOOL_END" in text
    m = re.search(r"POSTTOOL_BEGIN(.*?)POSTTOOL_END", text, re.DOTALL)
    block = m.group(1)
    assert '"decision":"block"' in block
    assert "permissionDecision" not in block  # not the PreToolUse schema


def test_post_status_audit_not_in_pretool_identity_set():
    t = (ROOT / "tests" / "test_safety_fallback_identity.py").read_text()
    assert "post-status-audit.sh" not in t
