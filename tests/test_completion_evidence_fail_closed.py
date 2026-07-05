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


def test_qa_ref_claims_report_is_accepted(tmp_path):
    """iter56 ②(b): qa ref が claims 付き QA レポート（test-strength.md ではない）を
    指しても evidence 検査が受理することを回帰固定（skill 新規約の受け皿）。"""
    (tmp_path / "docs" / "qa-reports").mkdir(parents=True)
    (tmp_path / "docs" / "qa-reports" / "iter1-qa.md").write_text(
        "# QA\n```claims\nverdict: approve\n```\n", encoding="utf-8")
    (tmp_path / "docs" / "qa-reports" / "iter1-review.md").write_text(
        "# review\n", encoding="utf-8")
    (tmp_path / "docs" / "STATUS.md").write_text(
        '---\nframework: aegis\nframework_version: "1.16.0"\n'
        'project_name: "t"\nmode: Dev\nphase: qa\n'
        'task_type: feature\ntask_size: M\niteration: 1\n'
        'ui_surface: false\nlast_updated: "2026-07-05T00:00:00Z"\n'
        'gate_approvals:\n  client_ready_for_dev: n/a\n  brainstorm: approved\n'
        '  plan: pending\n  review: approved\n  qa: approved\n'
        '  security: pending\n  deploy: pending\n'
        '  dev_ready_for_client: pending\n'
        'current_refs:\n  requirements: []\n  plan: null\n  spec: null\n'
        '  review: docs/qa-reports/iter1-review.md\n'
        '  qa: docs/qa-reports/iter1-qa.md\n  security: null\n'
        '  deploy: null\n  translation: null\n'
        'external_evidence: []\nfailure_tracking: null\n'
        'next_action: "t"\nblockers: []\nsession_history: []\n---\n\n## Summary\n\nt\n',
        encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout
