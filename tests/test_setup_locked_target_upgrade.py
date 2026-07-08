"""iter63 R3: a locked install (cp-lock chmod a-w) must not kill the documented
upgrade path (re-run bin/setup.sh). setup.sh self-heals: it unlocks via the
framework's own cp-lock lib, gated on an aegis-install marker AND an actual
lock finding, so a random read-only --target dir is never touched. Opt-out
AEGIS_SETUP_SELFHEAL=off fails closed with an attributed error.
Repro insight (2026-07-07): an IDENTICAL re-install never fails (copy_file_force
cmp -s short-circuits before cp) — the regression only shows on a DIFFERING
framework file, so every locked-upgrade test stales a hook first."""
import os
import pathlib
import stat
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
# chmod a-w does not bind root (repo convention: test_cp_lock_lib.py etc.) —
# every test that relies on lock semantics must skip as root.
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0


def _run(target, profile="standard", env_extra=None, check=False):
    env = dict(os.environ)
    env.pop("AEGIS_SETUP_SELFHEAL", None)  # shell leakage must not flip tests
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(ROOT / "bin/setup.sh"),
         f"--profile={profile}", f"--target={target}"],
        capture_output=True, text=True, env=env, check=check)


def _lock(target):
    subprocess.run(
        ["bash", "-c",
         f'source "{ROOT}/hooks/lib/cp-lock.sh" && aegis_cp_lock "{target}"'],
        check=True, capture_output=True, text=True)


def _unlock_all(path):
    # teardown: pytest's tmp cleanup must never fight a-w dirs left by a
    # failing assertion mid-test.
    subprocess.run(["chmod", "-R", "u+w", str(path)], capture_output=True)


@pytest.mark.skipif(ROOTUSER, reason="chmod a-w does not bind root")
def test_locked_upgrade_self_heals(tmp_path):
    target = tmp_path / "proj"
    try:
        _run(str(target), check=True)
        hook = target / "hooks" / "check-gate.sh"
        hook.write_text("#!/usr/bin/env bash\n# STALE\nexit 0\n")
        _lock(str(target))
        r = _run(str(target))
        assert r.returncode == 0, r.stderr
        assert "OS-locked" in r.stdout            # NOTE printed
        assert "next session start" in r.stdout   # re-lock deferral pinned
        assert hook.read_text() == (ROOT / "hooks" / "check-gate.sh").read_text()
        assert list((target / "hooks").glob("check-gate.sh.bak.*"))
        assert os.access(str(target / "hooks"), os.W_OK)  # left unlocked by design
    finally:
        _unlock_all(tmp_path)


def test_fresh_install_prints_no_unlock_note(tmp_path):
    target = tmp_path / "proj"
    r = _run(str(target))
    assert r.returncode == 0, r.stderr
    assert "OS-locked" not in r.stdout


def test_aegis_install_unlocked_stays_silent(tmp_path):
    # Pins the SECOND leg of the AND gate (marker present but zero verify
    # findings → no unlock, no NOTE). Doubles as a distribution-source canary:
    # a read-only file in the FRAMEWORK working copy ships read-only and turns
    # every fresh install into a false "OS-locked" heal (review iter63 Minor-2).
    target = tmp_path / "proj"
    _run(str(target), check=True)
    r = _run(str(target))  # marker exists, nothing locked
    assert r.returncode == 0, r.stderr
    assert "OS-locked" not in r.stdout


@pytest.mark.skipif(ROOTUSER, reason="chmod a-w does not bind root")
def test_selfheal_off_fails_closed_with_attribution(tmp_path):
    target = tmp_path / "proj"
    try:
        _run(str(target), check=True)
        hook = target / "hooks" / "check-gate.sh"
        hook.write_text("#!/usr/bin/env bash\n# STALE\nexit 0\n")
        _lock(str(target))
        r = _run(str(target), env_extra={"AEGIS_SETUP_SELFHEAL": "off"})
        assert r.returncode != 0
        assert "cp-lock" in r.stderr
        assert "AEGIS_SETUP_SELFHEAL" in r.stderr
        # the ATTRIBUTION line itself, not just the remedy lines (B1 drill
        # iter63: a mutant dropping the $why line survived on remedy tokens
        # alone — the remedy block also mentions cp-lock.sh)
        assert "is not writable" in r.stderr
        assert not os.access(str(target / "hooks"), os.W_OK)  # lock untouched
    finally:
        _unlock_all(tmp_path)


@pytest.mark.skipif(ROOTUSER, reason="chmod a-w does not bind root")
def test_non_aegis_readonly_target_is_not_unlocked(tmp_path):
    target = tmp_path / "proj"
    hooks = target / "hooks"
    hooks.mkdir(parents=True)
    hooks.chmod(0o555)  # user-made read-only dir; NO aegis markers exist
    try:
        r = _run(str(target))
        assert r.returncode != 0
        assert "cp-lock" in r.stderr              # remedy is still explained
        assert "is not writable" in r.stderr      # attribution line pinned (B1)
        mode = stat.S_IMODE(hooks.stat().st_mode)
        assert mode == 0o555                      # perms untouched (no unlock)
    finally:
        _unlock_all(tmp_path)
