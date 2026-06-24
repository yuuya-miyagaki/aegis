"""iter42 G2: check-secrets' commit check runs `git diff --cached` in the hook
CWD. With `git -C <repo> commit` (CWD != repo) the staged-diff scan saw nothing
and let a staged .env through. Honor -C / --git-dir so the TARGET repo is scanned.
The greedy -C extraction must also ignore a -C inside the commit message."""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-secrets.sh"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _mkrepo(path):
    path.mkdir()
    _git(path, "init")
    _git(path, "config", "user.email", "t@t")
    _git(path, "config", "user.name", "t")
    (path / ".env").write_text("SECRET=x\n")
    _git(path, "add", "--", ".env")
    return path


def _run(cmd, cwd):
    return subprocess.run(
        ["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True, text=True, cwd=str(cwd),
    ).stdout


def test_git_C_commit_with_staged_env_is_denied(tmp_path):
    repo = _mkrepo(tmp_path / "repo")
    # hook CWD is tmp_path (NOT repo); command targets repo via -C.
    out = _run(f"git -C {repo} commit -m x", cwd=tmp_path)
    assert '"permissionDecision":"deny"' in out, out


def test_git_C_with_dash_C_in_message_still_denied(tmp_path):
    repo = _mkrepo(tmp_path / "repo2")
    out = _run(f'git -C {repo} commit -m "fix -C handling"', cwd=tmp_path)
    assert '"permissionDecision":"deny"' in out, out


def test_plain_commit_in_cwd_still_denied(tmp_path):
    repo = _mkrepo(tmp_path / "repo3")
    out = _run("git commit -m x", cwd=repo)  # CWD == repo (current behavior)
    assert '"permissionDecision":"deny"' in out, out


def test_git_dir_equals_form_denied(tmp_path):
    repo = _mkrepo(tmp_path / "repo4")
    out = _run(f"git --git-dir={repo}/.git --work-tree={repo} commit -m x", cwd=tmp_path)
    assert '"permissionDecision":"deny"' in out, out


def test_git_dir_space_form_denied(tmp_path):
    repo = _mkrepo(tmp_path / "repo5")
    out = _run(f"git --git-dir {repo}/.git --work-tree {repo} commit -m x", cwd=tmp_path)
    assert '"permissionDecision":"deny"' in out, out


def test_quoted_dash_C_path_denied(tmp_path):
    # surrounding quotes (no inner space) must be stripped so the right repo is scanned
    repo = _mkrepo(tmp_path / "repo6")
    out = _run(f'git -C "{repo}" commit -m x', cwd=tmp_path)
    assert '"permissionDecision":"deny"' in out, out
