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
import re
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
    "git show HEAD",
    "python3 scripts/check_reference_drift.py --root .",
    "python3 scripts/learnings_search.py --query mutation",
    "python3 scripts/lint_names.py --root .",
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


# --- iter52: allow-list completeness guard (classification-map driven) ---
# Every scripts/ CLI entrypoint is classified by INTENT, not mechanism: several
# safe readers (check_status.py etc.) call subprocess.run on FIXED internal
# commands, so "uses subprocess" is NOT the criterion.
#   safe_auto_allow = pure reader / benign idempotent generator that never
#       executes an arg/stdin-controlled command and mutates no risky repo state
#       -> MUST be in permissions.allow.
#   must_prompt = mutates persistent state (STATUS/snapshot, evidence log) OR
#       executes an arg-controlled command (exec gadget) OR scaffolds/installs/
#       evals -> MUST NOT be auto-allowed.
#   not_cli = import-only module, never invoked as a Bash command.
# A new scripts/ entrypoint absent here trips test_every_script_is_classified,
# forcing an explicit allow/prompt decision (anti-drift; iter49/50 family).
SCRIPTS_DIR = ROOT / "scripts"

# iter55: SCRIPT_CLASS は hooks/lib/scripts-manifest.tsv（single owner）由来。
# allow → safe_auto_allow / ask・framework-only → must_prompt / import-only → not_cli。
# 分類の理由（exec ガジェット・状態変異・context_budget の --tighten/--seed 書込み等）は
# TSV ヘッダコメントに集約（旧: このファイルの手書き dict — 3重管理の最後の1枚だった）。
_CLASS_FROM_MANIFEST = {
    "allow": "safe_auto_allow",
    "ask": "must_prompt",
    "framework-only": "must_prompt",
    "import-only": "not_cli",
}


def _load_script_class():
    out = {}
    text = (ROOT / "hooks" / "lib" / "scripts-manifest.tsv").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entry, cls = line.split("\t")  # 厳格 split（strip しない — contract が清潔さを保証）
        out[pathlib.Path(entry).name] = _CLASS_FROM_MANIFEST[cls]
    return out


SCRIPT_CLASS = _load_script_class()

SAFE_GIT_READS = ["git status", "git log", "git diff", "git show"]
DESTRUCTIVE_GIT = ["git branch -D x", "git remote remove origin", "git checkout ."]


def _enumerated_scripts():
    return {p.name for p in SCRIPTS_DIR.glob("*.py")} | \
           {p.name for p in SCRIPTS_DIR.glob("*.sh")}


def _allow_targets_script(entry, name):
    # name-mention check — used by the NEGATIVE/orphan tests where we want to
    # catch ANY allow entry that references a must_prompt / not_cli script.
    return f"scripts/{name}" in entry


def _rep_invocation(name):
    # representative real invocation, so the POSITIVE membership test proves the
    # script is actually auto-allowed (a malformed entry lacking ':*' would
    # name-mention but NOT auto-allow '... <args>'). Runner follows the
    # extension convention (.sh via bash) so a future safe_auto_allow shell
    # script doesn't yield a false RED.
    runner = "bash" if name.endswith(".sh") else "python3"
    return f"{runner} scripts/{name} x"


def test_every_script_is_classified():
    enum = _enumerated_scripts()
    missing = enum - set(SCRIPT_CLASS)
    assert not missing, f"unclassified scripts/ entrypoints: {sorted(missing)}"
    stale = set(SCRIPT_CLASS) - enum
    assert not stale, f"SCRIPT_CLASS lists non-existent scripts: {sorted(stale)}"


def test_safe_auto_allow_scripts_are_allowed():
    allow = _template_allow()
    for name, cls in SCRIPT_CLASS.items():
        if cls == "safe_auto_allow":
            assert any(_matches(e, _rep_invocation(name)) for e in allow), \
                f"safe_auto_allow script not actually auto-allowed: {name}"


def test_non_safe_scripts_are_not_allowed():
    allow = _template_allow()
    for name, cls in SCRIPT_CLASS.items():
        if cls != "safe_auto_allow":
            assert not any(_allow_targets_script(e, name) for e in allow), \
                f"{cls} script must NOT be auto-allowed: {name}"


def test_safe_git_reads_allowed_destructive_excluded():
    allow = _template_allow()
    for cmd in SAFE_GIT_READS:
        assert any(_matches(e, cmd) for e in allow), f"safe git read not allowed: {cmd}"
    for cmd in DESTRUCTIVE_GIT:
        assert not any(_matches(e, cmd) for e in allow), f"destructive git auto-allowed: {cmd}"


def test_no_orphan_script_allow_entry():
    safe = {n for n, c in SCRIPT_CLASS.items() if c == "safe_auto_allow"}
    for entry in _template_allow():
        m = re.search(r"scripts/([\w.-]+)", entry)
        if m:
            assert m.group(1) in safe, \
                f"allow entry targets non-safe_auto_allow script: {entry}"


def test_script_class_consistent_with_should_lists():
    # single-source guard: the matcher-form lists SHOULD_MATCH / SHOULD_NOT_MATCH
    # and SCRIPT_CLASS must never disagree, so a future editor updating one
    # cannot silently diverge from the other.
    def _script(cmd):
        m = re.search(r"scripts/([\w.-]+)", cmd)
        return m.group(1) if m else None
    for cmd in SHOULD_MATCH:
        n = _script(cmd)
        if n:
            assert SCRIPT_CLASS.get(n) == "safe_auto_allow", \
                f"SHOULD_MATCH {cmd!r} but SCRIPT_CLASS[{n}]={SCRIPT_CLASS.get(n)}"
    for cmd in SHOULD_NOT_MATCH:
        n = _script(cmd)
        if n:
            assert SCRIPT_CLASS.get(n) == "must_prompt", \
                f"SHOULD_NOT_MATCH {cmd!r} but SCRIPT_CLASS[{n}]={SCRIPT_CLASS.get(n)}"


# --- iter55: scripts-manifest.tsv must ship with hooks/lib (F6-class install gap) ---

def test_install_ships_scripts_manifest(tmp_path):
    """setup.sh の lib 配布は *.sh glob だったため .tsv が配布されず、install 先で
    allowlist が fail-closed 全 deny になる（F6 同型の install 死角）。"""
    target = tmp_path / "proj"
    _install(str(target), "full")
    installed = target / "hooks" / "lib" / "scripts-manifest.tsv"
    assert installed.is_file(), "scripts-manifest.tsv not shipped to install target"
    src = (ROOT / "hooks" / "lib" / "scripts-manifest.tsv").read_text()
    assert installed.read_text() == src, "installed manifest differs from source"


def test_installed_hook_allows_manifest_script(tmp_path):
    """installed tree での hook 実発火（scaffold smoke の精神）: feature タスク下で
    class=allow スクリプトの素実行が通る。"""
    target = tmp_path / "proj"
    _install(str(target), "full")
    (target / "docs").mkdir(exist_ok=True)
    (target / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": "python3 scripts/retro_report.py"}})
    r = subprocess.run(
        ["bash", str(target / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(target))
    assert r.stdout.strip() == "{}", f"installed hook must allow: {r.stdout[:200]!r}"
