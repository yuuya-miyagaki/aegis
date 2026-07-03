#!/usr/bin/env python3
"""iter55 P0: 実行可スクリプトの allowlist は hooks/lib/scripts-manifest.tsv が単一正本。

ドッグフード一周目（2026-07-03）でゲート戦闘 7 件中 6 件が allowlist 系だった。
settings permissions（8本）と hook のハードコード case（5本）が別管理でドリフトし、
skill が指示する status_doctor.py（/recover）・retro_report.py（/retro）・
build-judge-card.py（/gate）・update-task.sh（正規の task 変更手段）を hook が deny した。

本テストは manifest の class allow|ask 全 12 本の素の単体実行 ALLOW・framework-only の
DENY・manifest 欠落時の全 DENY（fail-closed）・チェーン/リダイレクト付き DENY 維持を pin する。
Harness は tests/test_control_plane_allowlist.py と同型。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch_root(include_manifest: bool = True) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    if include_manifest:
        (lib_dir / "scripts-manifest.tsv").symlink_to(
            ROOT / "hooks" / "lib" / "scripts-manifest.tsv")
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


# manifest の class allow|ask 全 12 本の代表実呼び出し形。
RUNNABLE = [
    "python3 scripts/check_status.py",
    "python3 scripts/check_framework_contract.py --profile=standard --root .",
    "python3 scripts/status_doctor.py",
    "python3 scripts/retro_report.py --root .",
    "python3 scripts/build-judge-card.py --gate review",
    "python3 scripts/check_reference_drift.py",
    "python3 scripts/learnings_search.py --query mutation",
    "python3 scripts/lint_names.py",
    "bash scripts/update-gate.sh review approve",
    "bash scripts/update-task.sh --size L",
    "python3 scripts/record-test-result.py --cmd 'pytest' --status ok",
    "python3 scripts/run-test-strength-drill.py --root .",
]

# framework-only: 対象プロジェクトでは deny のまま（framework repo は task_type=framework で素通り）
FRAMEWORK_ONLY = [
    "python3 scripts/context_budget.py check",
    "python3 scripts/run_eval.py",
    "python3 scripts/eval_scaffold_smoke.py",
    "python3 scripts/eval_scenario.py",
]


class TestManifestRunnable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_all_runnable_scripts_allowed_bare(self):
        for cmd in RUNNABLE:
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_allowed(out), f"{cmd!r} must be allowed: {out[:200]!r}")

    def test_framework_only_scripts_stay_denied(self):
        for cmd in FRAMEWORK_ONLY:
            with self.subTest(cmd=cmd):
                out = _hook(self.root, cmd)
                self.assertTrue(_denied(out), f"{cmd!r} must stay denied: {out[:200]!r}")

    def test_chained_runnable_still_denied(self):
        out = _hook(self.root,
                    "bash scripts/update-task.sh --size L && rm hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"chain must deny: {out[:200]!r}")

    def test_redirect_runnable_still_denied(self):
        out = _hook(self.root, "python3 scripts/retro_report.py > hooks/lib/emit.sh")
        self.assertTrue(_denied(out), f"redirect must deny: {out[:200]!r}")

    # grill-code 🔴: substring マッチは「スクリプトへの書込み」を実行と誤認した。
    # 実行形（interpreter+パス or パスで始まる）以外は deny を pin する。
    def test_write_to_allowlisted_script_denied(self):
        out = _hook(self.root, "cp evil scripts/update-gate.sh")
        self.assertTrue(_denied(out),
                        f"write TO an allowlisted script must deny: {out[:200]!r}")

    def test_mention_after_other_command_denied(self):
        out = _hook(self.root, "echo before scripts/check_status.py")
        self.assertTrue(_denied(out),
                        f"non-invocation mention must deny: {out[:200]!r}")

    def test_bare_script_path_invocation_allowed(self):
        out = _hook(self.root, "scripts/update-gate.sh review approve")
        self.assertTrue(_allowed(out), f"bare path invocation: {out[:200]!r}")

    def test_dot_slash_invocation_allowed(self):
        out = _hook(self.root, "./scripts/update-task.sh --size L")
        self.assertTrue(_allowed(out), f"./ invocation: {out[:200]!r}")


class TestManifestFailClosed(unittest.TestCase):
    def test_missing_manifest_denies_everything(self):
        """manifest 欠落 = 全 deny（旧ハードコード5本も含む）。fail-closed の核心 pin。"""
        with _scratch_root(include_manifest=False) as name:
            root = Path(name)
            for cmd in ("python3 scripts/check_status.py",
                        "bash scripts/update-gate.sh review approve"):
                with self.subTest(cmd=cmd):
                    out = _hook(root, cmd)
                    self.assertTrue(_denied(out),
                                    f"missing manifest must deny {cmd!r}: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
