"""iter42 G1: check-destructive must ask on catastrophic commands the review
found slipping through (dd of=, recursive chmod, mkfs, shred, truncating a
system path via redirect) — while leaving benign idioms (chmod 644, append,
>/dev/null) alone. These are emit_ask (confirm), not deny: accident-prevention."""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-destructive.sh"


def _run(cmd):
    payload = json.dumps({"tool_input": {"command": cmd}})
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, capture_output=True, text=True
    ).stdout


def test_dangerous_commands_ask():
    for cmd in (
        "dd if=/dev/zero of=/dev/sda",
        "chmod -R 777 /",
        "chmod -Rf 777 /srv",   # combined flag R then f
        "chmod -fR 777 /srv",   # combined flag f then R
        "mkfs.ext4 /dev/sdb1",
        "shred -u secret.txt",
        "echo x > /etc/hosts",
    ):
        out = _run(cmd)
        assert '"permissionDecision":"ask"' in out, f"should ask: {cmd} -> {out}"


def test_benign_commands_allow():
    for cmd in (
        "echo hello",
        "chmod 644 file.txt",
        "chmod -v u+x run.sh",         # no recursive flag
        "echo x >> app.log",           # append, not truncate
        "make build >/dev/null 2>&1",  # /dev/null must NOT trip truncate
        "python3 app.py 2>/etc/app.log",  # fd redirect (2>) must NOT trip truncate
        "cat /etc/hosts",              # read, not truncate
    ):
        out = _run(cmd)
        assert out.strip() == "{}", f"should allow: {cmd} -> {out}"
