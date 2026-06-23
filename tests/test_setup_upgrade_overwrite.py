"""iter41 D3: re-install (upgrade) must overwrite framework-owned assets so
security fixes reach existing installs, while preserving user-owned files. A
.bak of any overwritten differing framework file is kept (recoverable); an
identical file produces no churn and no .bak."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _install(target, profile="standard"):
    return subprocess.run(
        ["bash", str(ROOT / "bin/setup.sh"),
         f"--profile={profile}", f"--target={target}"],
        check=True, capture_output=True, text=True,
    )


def test_upgrade_overwrites_framework_hook_but_preserves_user_docs(tmp_path):
    target = tmp_path / "proj"
    _install(str(target))
    # Simulate a STALE framework hook + a user-customized STATUS.
    hook = target / "hooks" / "check-gate.sh"
    hook.write_text("#!/usr/bin/env bash\n# STALE\nexit 0\n")
    status = target / "docs" / "STATUS.md"
    status.write_text("USER EDIT\n")
    _install(str(target))  # re-install = upgrade
    # framework-owned hook refreshed from source (no longer STALE):
    assert "# STALE" not in hook.read_text()
    assert hook.read_text() == (ROOT / "hooks" / "check-gate.sh").read_text()
    # a .bak of the overwritten hook exists:
    assert list((target / "hooks").glob("check-gate.sh.bak.*"))
    # user-owned doc preserved:
    assert status.read_text() == "USER EDIT\n"


def test_identical_framework_file_makes_no_bak(tmp_path):
    target = tmp_path / "proj"
    _install(str(target))
    _install(str(target))  # second install, nothing changed
    assert not list((target / "hooks").glob("check-gate.sh.bak.*"))
