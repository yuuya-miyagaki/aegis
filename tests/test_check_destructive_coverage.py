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


def test_tree_revert_commands_ask():
    """iter61 (full-review 2026-07-06 R1): the iter60 incident command class —
    a verification subagent reverting the parent's uncommitted work — must ask.
    Pathspec checkout is caught only in forms a branch name cannot take
    (glob / trailing slash / multi-arg / ` -- `); see the plan's matrix."""
    for cmd in (
        "git checkout docs/*",                        # the iter60 incident command
        "git checkout *",                             # leading glob (2nd-review M-1)
        "git checkout *.md",
        "git checkout ?foo.md",
        "git checkout docs/",                         # trailing slash: not a valid ref
        "git checkout HEAD docs/STATUS.md",           # multi-arg = pathspec form
        "git checkout HEAD 2026-notes.md",            # multi-arg, digit-leading file
        "git checkout HEAD -- docs/STATUS.md",        # canonical file-restore form
        "git checkout main -- docs/*",
        "git restore docs/STATUS.md",                 # restore = always a file discard
        "git -C /path/to/repo checkout docs/*",       # -C prefix (subagent idiom)
        "git stash",
        "git stash push -m wip",
        "git stash -u",                               # flag-form bare stash
        "git stash --all && pytest",
        "git stash && python3 -m pytest -q",
        "(git stash)",
        "git stash > /dev/null 2>&1",
        "git stash drop",
        "git stash clear",
        "git checkout -f main",                       # force = silent discard (grill M-1)
        "git checkout --force main",
        "git checkout -q -f main",                    # force behind another flag (2nd-review sec Minor-3)
        "git checkout --quiet --force main",
        "git stash 2>/dev/null",                      # fd-redirect stash (2nd-review sec Major-1)
        "git stash 1>/dev/null 2>&1",
        "git restore --source=HEAD docs/STATUS.md",   # flagged restore (grill M-2)
        "git restore --worktree docs/STATUS.md",
        "git restore -W docs/STATUS.md",
    ):
        out = _run(cmd)
        assert '"permissionDecision":"ask"' in out, f"should ask: {cmd} -> {out}"


def test_tree_revert_benign_allow():
    """iter61 guard: high-frequency benign git forms must never ask —
    single-branch checkout (with or without redirects), branch creation,
    non-destructive stash subcommands, index-only restore."""
    for cmd in (
        "git checkout main",
        "git checkout feature/foo",
        "git checkout v1.2.3",
        "git checkout main 2>/dev/null || git checkout -b main",
        "git checkout main > build.log 2>&1",
        "git checkout -b feature/x",
        "git checkout --track origin/x",
        "git checkout -",
        "git checkout main && make",
        "git stash list",
        "git stash show -p",
        "git stash pop && pytest",
        "git stash pop 2>/dev/null",   # fd redirect on a non-destructive subcommand
        "git stash list 2>/dev/null",
        "git restore --staged file.txt",
        "git checkout -q main",        # non-force flag must not trip the -f form
    ):
        out = _run(cmd)
        assert out.strip() == "{}", f"should allow: {cmd} -> {out}"
