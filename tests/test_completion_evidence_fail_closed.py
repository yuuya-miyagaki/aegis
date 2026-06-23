"""iter41 I2: --check-completion-evidence must fail-closed (exit 1) when
STATUS.md is absent or has no YAML frontmatter, symmetric with
validate_status_file. Previously it returned exit 0 (PASS) — an adversary could
delete/corrupt STATUS.md to make the TaskCompleted evidence check pass."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run(root):
    return subprocess.run(
        ["python3", str(ROOT / "scripts/check_status.py"),
         "--root", str(root), "--check-completion-evidence"],
        capture_output=True, text=True,
    )


def test_absent_status_is_violation(tmp_path):
    r = _run(tmp_path)  # no docs/STATUS.md
    assert r.returncode == 1, r.stdout
    assert "EVIDENCE" in r.stdout


def test_frontmatter_none_is_violation(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "STATUS.md").write_text("no frontmatter here\n")
    r = _run(tmp_path)
    assert r.returncode == 1, r.stdout
    assert "EVIDENCE" in r.stdout
