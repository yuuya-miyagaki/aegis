"""iter41 D2: the Task completion-enforcement hooks (check-task-created.sh =
plan-gate hard stop; check-task-completed.sh = completion-evidence) must be
wired into the standard profile, the framework's own active settings, and
enforced by the contract. The dogfood settings.local.json had drifted from the
template and never registered them, so 'completion requires evidence' was not
mechanically enforced even here."""
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

TASK_HOOKS = ("check-task-created.sh", "check-task-completed.sh")


def _json(rel):
    return json.loads((ROOT / rel).read_text())


def test_standard_profile_includes_task_hooks():
    std = _json("templates/profiles/standard.json")
    # hooks_include uses bare script names; required_hook_scripts uses the
    # "hooks/" prefix (matches the data model in standard.json).
    for h in TASK_HOOKS:
        assert h in std["hooks_include"], f"standard hooks_include missing {h}"
        assert f"hooks/{h}" in std["required_hook_scripts"], (
            f"standard required_hook_scripts missing hooks/{h}"
        )


def test_template_registers_task_hooks():
    """The tracked hooks.template.json (what setup.sh filters to generate
    settings) must register the Task hooks — this is the reproducible source of
    truth, independent of any per-machine settings.local.json."""
    tmpl = _json("templates/hooks.template.json")
    assert "TaskCreated" in tmpl["hooks"]
    assert "TaskCompleted" in tmpl["hooks"]


def test_active_settings_register_task_hooks():
    """Dogfood consistency: the live settings (if present) must register the
    Task hooks. settings.local.json is gitignored, so skip on a fresh clone
    where it hasn't been generated yet."""
    p = ROOT / ".claude" / "settings.local.json"
    if not p.exists():
        pytest.skip("settings.local.json not present (fresh clone) — see template test")
    s = json.loads(p.read_text())
    cmds = []
    for entries in s.get("hooks", {}).values():
        for e in entries:
            for hk in e.get("hooks", []):
                cmds.append(hk.get("command", ""))
    for h in TASK_HOOKS:
        assert any(h in c for c in cmds), f"active settings missing {h}"


def _load_contract():
    spec = importlib.util.spec_from_file_location(
        "cfc", ROOT / "scripts" / "check_framework_contract.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_contract_core_hook_check_behaviour(tmp_path):
    """Behavioural, not just constant-presence: the check FAILs when a CORE hook
    is unregistered and passes for the real framework settings."""
    cfc = _load_contract()
    assert cfc.check_active_settings_core_hooks(ROOT) == []
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text(
        '{"hooks":{"PreToolUse":[{"hooks":[{"command":"bash hooks/check-gate.sh"}]}]}}'
    )
    fails = cfc.check_active_settings_core_hooks(tmp_path)
    assert any("check-task-completed.sh" in f for f in fails), fails
