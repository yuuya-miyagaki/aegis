"""iter41 D4: when an existing .claude/settings.local.json cannot be parsed as
JSON (e.g. a non-engineer pasted a // comment), setup.sh must warn loudly and
point at the .bak instead of silently dropping the user's permissions/env."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_broken_existing_settings_emits_warning(tmp_path):
    target = tmp_path / "proj"
    (target / ".claude").mkdir(parents=True)
    # Invalid JSON (JSONC-style comment a non-engineer might paste).
    (target / ".claude" / "settings.local.json").write_text(
        '{\n  // my note\n  "permissions": {"allow": ["Bash(ls)"]}\n}\n'
    )
    r = subprocess.run(
        ["bash", str(ROOT / "bin/setup.sh"),
         "--profile=standard", f"--target={target}"],
        capture_output=True, text=True,
    )
    combined = r.stdout + r.stderr
    assert "WARNING" in combined and "could not be parsed" in combined, combined
    # a backup of the unparseable file exists so perms can be recovered:
    assert list((target / ".claude").glob("settings.local.json.bak.*"))
