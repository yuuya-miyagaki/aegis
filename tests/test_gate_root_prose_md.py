#!/usr/bin/env python3
"""iter55 P2: repo 直下の *.md（DOGFOOD-LOG.md 等のメタ文書）は Client モード・
plan 承認前でも編集可（ゲートはコードを守る・散文は対象外）。

ドッグフード ゲート戦闘2・4: 観測ログ DOGFOOD-LOG.md が Client 全期間＋Dev の plan
承認前に書けず、スクラッチパッドへのバッファ運用を強いられた。CLAUDE.md（control
検査で deny 済み）・サブディレクトリの .md・コードファイルは従来どおり。
Harness は tests/test_check_gate_root_external.py と同型。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_TMPL = (
    "---\nframework: aegis\nmode: {mode}\nphase: {phase}\n"
    "task_type: {task_type}\ngate_approvals:\n  plan: {plan}\n---\n"
)


def _scratch_root(mode: str = "Dev", task_type: str = "feature",
                  plan: str = "pending", phase: str = "implement"):
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        STATUS_TMPL.format(mode=mode, task_type=task_type, plan=plan, phase=phase),
        encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-gate.sh", hooks_dir / "check-gate.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, file_path: str) -> str:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-gate.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


class TestRootProseMdAllowed(unittest.TestCase):
    def test_client_mode_root_md_allowed(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            root = Path(name)
            out = _hook(root, f"{root}/DOGFOOD-LOG.md")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_plan_pending_root_md_allowed(self):
        with _scratch_root(mode="Dev", plan="pending", phase="brainstorm") as name:
            root = Path(name)
            out = _hook(root, f"{root}/NOTES.md")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")

    def test_relative_root_md_allowed(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            out = _hook(Path(name), "DOGFOOD-LOG.md")
        self.assertTrue(_allowed(out), f"got: {out[:200]!r}")


class TestGuardsUnchanged(unittest.TestCase):
    def test_client_mode_code_still_denied(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            root = Path(name)
            out = _hook(root, f"{root}/src/app.ts")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_client_mode_claude_md_still_denied(self):
        with _scratch_root(mode="Client", phase="discovery") as name:
            root = Path(name)
            out = _hook(root, f"{root}/CLAUDE.md")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_subdir_md_still_gated(self):
        with _scratch_root(mode="Dev", plan="pending") as name:
            root = Path(name)
            out = _hook(root, f"{root}/notes/inner.md")
        self.assertTrue(_denied(out), f"got: {out[:200]!r}")

    def test_symlink_md_to_control_file_not_prose_allowed(self):
        """盲検2次(security): prose carve-out は symlink を解決しない。repo 直下の
        `*.md` が制御ファイルへの symlink だと Client/plan 承認前でも allow され、
        iter55 前（plan-gate で deny）からの防御多層の後退になる。symlink は
        prose fast-path に載せず gate に落とす（＝Client/plan-pending で deny 復帰）。"""
        with _scratch_root(mode="Client", phase="discovery") as name:
            root = Path(name)
            # 実 repo の lib を破壊しないよう、target は制御プレーンの scripts/ 名を
            # scratch 内に実ファイルとして作りそこへ張る（symlink 経由の write は
            # 貫通するため、既存 symlink（emit.sh 等）を target にしてはならない）。
            (root / "scripts").mkdir(exist_ok=True)
            control_target = root / "scripts" / "update-gate.sh"
            control_target.write_text("x", encoding="utf-8")
            link = root / "notes.md"
            link.symlink_to(control_target)
            out = _hook(root, str(link))
        self.assertTrue(_denied(out),
                        f"symlink prose must not take the allow fast-path: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()
