"""iter51: ship a curated permissions.allow so the framework's safe read-only /
record-only commands stop prompting, while state-mutating (update-gate.sh /
update-task.sh) and dangerous commands keep prompting. Verifies:
  - the template carries the allow set (and excludes mutators/dangerous),
  - the entries actually prefix the real invocation strings (grill #2 proxy),
  - every profile ships it (filtered branch must carry permissions, grill B1),
  - re-install unions with user allow and preserves user deny/env (grill B2),
  - the moat holds: deny-hooks stay registered, gate scripts are not auto-allowed.
"""
import json
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "hooks.template.json"

# Representative real invocations the framework runs that SHOULD be auto-allowed.
SHOULD_MATCH = [
    "python3 scripts/status_doctor.py --root .",
    "python3 scripts/check_framework_contract.py --root .",
    "python3 scripts/check_status.py --root .",
    "python3 scripts/retro_report.py --root .",
    "python3 -m pytest -q",
    "pytest tests/test_x.py",
    "git status",
    "git diff HEAD",
    "git log --oneline -5",
]
# Commands that MUST keep prompting — no allow entry may match these.
# record-test-result.py / run-test-strength-drill.py are command-EXEC gadgets
# (record-test-result executes its CLI arg via drill._execute) — auto-allowing
# them would be a permission-bypass, so they must NOT match any allow entry.
SHOULD_NOT_MATCH = [
    "bash scripts/update-gate.sh review approve",
    "bash scripts/update-task.sh --size M",
    "python3 scripts/record-test-result.py rm -rf /",
    "python3 scripts/run-test-strength-drill.py",
    "git push origin main",
    "rm -rf build",
]


def _template_allow():
    d = json.loads(TEMPLATE.read_text())
    return d.get("permissions", {}).get("allow", [])


def _matches(entry, cmd):
    """Claude Code Bash rule semantics (verified against permissions.md):
    Bash(PREFIX:*) / Bash(PREFIX *) = word-boundary prefix match;
    Bash(EXACT) = exact match. True iff `cmd` is auto-allowed by `entry`."""
    if not (entry.startswith("Bash(") and entry.endswith(")")):
        return False
    inner = entry[len("Bash("):-1]
    for suffix in (":*", " *"):
        if inner.endswith(suffix):
            prefix = inner[: -len(suffix)]
            return cmd == prefix or cmd.startswith(prefix + " ")
    return cmd == inner


def _install(target, profile="standard"):
    return subprocess.run(
        ["bash", str(ROOT / "bin/setup.sh"),
         f"--profile={profile}", f"--target={target}"],
        check=True, capture_output=True, text=True,
    )


def _installed(target):
    return json.loads((target / ".claude" / "settings.local.json").read_text())


# --- Task 1: template carries the allow set; excludes mutators/dangerous ---

def test_template_has_allow_set():
    allow = _template_allow()
    required = [
        "Bash(python3 scripts/status_doctor.py:*)",
        "Bash(python3 scripts/check_framework_contract.py:*)",
        "Bash(python3 -m pytest:*)",
        "Bash(pytest:*)",
        "Bash(git status:*)",
    ]
    for r in required:
        assert r in allow, f"template allow missing {r}: {allow}"


def test_template_allow_excludes_mutators_and_dangerous():
    allow = _template_allow()
    for cmd in SHOULD_NOT_MATCH:
        assert not any(_matches(e, cmd) for e in allow), \
            f"{cmd!r} must NOT be auto-allowed; allow={allow}"
    joined = " ".join(allow)
    assert "update-gate.sh" not in joined
    assert "update-task.sh" not in joined
    # command-exec gadgets must never be auto-allowed (grill-code 🔴/🟡):
    assert "record-test-result.py" not in joined
    assert "run-test-strength-drill.py" not in joined


def test_allowed_scripts_do_not_invoke_command_executor():
    """No allow-listed framework script may call the drill command executor
    (drill._execute) — that turns the entry into an arbitrary-command gadget
    (the reason record-test-result.py is excluded). Locks the safe call graph so
    a future refactor that wires _execute into an allow-listed reader is caught
    (review Finding 1: JSON can't hold a warning comment, so guard it as a test)."""
    import re as _re
    for entry in _template_allow():
        m = _re.match(r"^Bash\(python3 (scripts/[\w./-]+\.py)", entry)
        if not m:
            continue
        script = ROOT / m.group(1)
        if not script.is_file():
            continue
        assert "._execute(" not in script.read_text(), \
            f"allow-listed {m.group(1)} calls drill._execute = arbitrary-command gadget"


# --- Task 1 proxy (grill #2): entries actually prefix real invocations ---

def test_allow_entries_match_real_invocations():
    allow = _template_allow()
    for cmd in SHOULD_MATCH:
        assert any(_matches(e, cmd) for e in allow), \
            f"no allow entry matches real invocation: {cmd!r}"


# --- Task 2: every profile ships the allow set (filtered must carry it) ---

@pytest.mark.parametrize("profile", ["minimal", "standard", "full"])
def test_install_ships_allow_all_profiles(tmp_path, profile):
    target = tmp_path / "proj"
    _install(str(target), profile)
    installed = _installed(target).get("permissions", {}).get("allow", [])
    for e in _template_allow():
        assert e in installed, f"profile {profile}: installed allow missing {e}"


# --- Task 3: re-install unions with user allow, preserves deny/env, idempotent ---

def test_reinstall_unions_user_allow_and_preserves(tmp_path):
    target = tmp_path / "proj"
    (target / ".claude").mkdir(parents=True)
    (target / ".claude" / "settings.local.json").write_text(json.dumps({
        "permissions": {"allow": ["Bash(npm test:*)"], "deny": ["Bash(rm:*)"]},
        "env": {"FOO": "bar"},
    }))
    _install(str(target))
    d = _installed(target)
    allow = d.get("permissions", {}).get("allow", [])
    assert "Bash(npm test:*)" in allow, "user-added allow dropped"
    for e in _template_allow():
        assert e in allow, f"framework allow missing after merge: {e}"
    assert d["permissions"].get("deny") == ["Bash(rm:*)"], "user deny not preserved"
    assert d.get("env", {}).get("FOO") == "bar", "user env not preserved"
    # idempotent: a second install must not duplicate or change the allow set.
    _install(str(target))
    allow2 = _installed(target)["permissions"]["allow"]
    assert len(allow2) == len(set(allow2)), f"duplicates after re-install: {allow2}"
    assert sorted(allow2) == sorted(allow), "allow set not stable across re-install"


# --- Task 4: moat — deny-hooks stay registered after install ---

def test_install_preserves_deny_hooks(tmp_path):
    target = tmp_path / "proj"
    _install(str(target), "full")
    pre = json.dumps(_installed(target).get("hooks", {}).get("PreToolUse", []))
    assert "check-destructive.sh" in pre, "destructive deny-hook missing"
    assert "check-control-plane.sh" in pre, "control-plane deny-hook missing"
