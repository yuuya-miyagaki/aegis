"""iter42 G3: deploy detection is single-sourced in patterns.sh
(AEGIS_DEPLOY_REGEX), so check-deploy-gate and check-cron-gate share it and no
longer drift. After single-sourcing, cron-gate also inherits the destructive
patterns (incl. G1's chmod -R) instead of its narrower inline list."""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run(hook, payload, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(
        ["bash", str(ROOT / "hooks" / hook)],
        input=json.dumps(payload), capture_output=True, text=True, env=e,
    ).stdout


def test_patterns_defines_deploy_regex():
    assert "AEGIS_DEPLOY_REGEX" in (ROOT / "hooks/lib/patterns.sh").read_text()


def _status(tmp_path):
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "STATUS.md").write_text(
        "---\nmode: Dev\nphase: deploy\ntask_type: feature\ntask_size: L\n"
        "gate_approvals:\n  deploy: pending\n---\n"
    )


def test_deploy_gate_engages_on_vercel(tmp_path):
    _status(tmp_path)
    out = _run("check-deploy-gate.sh", {"tool_input": {"command": "vercel deploy --prod"}},
               env={"AEGIS_ROOT_OVERRIDE": str(tmp_path)})
    assert '"permissionDecision"' in out, out  # deny or ask, not bare allow


def test_deploy_gate_allows_readonly(tmp_path):
    _status(tmp_path)
    out = _run("check-deploy-gate.sh", {"tool_input": {"command": "rg deploy src/"}},
               env={"AEGIS_ROOT_OVERRIDE": str(tmp_path)})
    assert out.strip() == "{}", out


def test_cron_gate_inherits_new_destructive_pattern():
    # chmod -R is a G1 pattern; after single-source it must reach cron-gate.
    out = _run("check-cron-gate.sh", {"tool_input": {"prompt": "nightly job: chmod -R 777 /srv"}})
    assert '"permissionDecision":"ask"' in out, out


def test_cron_gate_asks_on_deploy():
    out = _run("check-cron-gate.sh", {"tool_input": {"prompt": "weekly: run vercel deploy"}})
    assert '"permissionDecision":"ask"' in out, out


def test_cron_gate_allows_benign():
    out = _run("check-cron-gate.sh", {"tool_input": {"prompt": "nightly: echo healthcheck && curl status"}})
    assert out.strip() == "{}", out
