#!/usr/bin/env python3
"""update-gate.sh の approve --ref 原子化と SIGPIPE 耐性（iter68・full-review 1-3）。

罠a: 旧実装は状態書込み（sed）より前に judge カード等を stdout へ流すため、
pipe 早期クローズで SIGPIPE 死＝gate 未承認のまま出力だけ欠ける。
罠b/c: gate 値と current_refs が別書込みのため、どちらの順でも
contract（pending+ref / approved+空）が赤くなる窓が開く。
本テストは「--ref 同時書込み」「書込みが承認主張出力に先行」を契約として固定する。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# phase=plan / brainstorm approved → plan gate が prereq を満たし、
# JUDGE_GATES にも qa drill にも該当しない＝pre-approve が無出力で決定的。
STATUS_PLAN_PHASE = """---
framework: aegis
framework_version: "0.12.0"
project_name: test
mode: Dev
phase: plan
task_type: feature
task_size: L
last_updated: "2026-01-01"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: null
  plan: null
  spec: null
  review: null
  qa: null
  security: null
  deploy: null
  translation: null
next_action: "fixture body (sed range closes at this top-level key, like production)"
---
"""

# na 検証用（pre_na_gate は bugfix/hotfix のみ na 許可）。plan gate に
# pending+ref を先置き＝降格後は advisory なので fixture として合法。
STATUS_BUGFIX_NA = STATUS_PLAN_PHASE.replace(
    "task_type: feature", "task_type: bugfix").replace(
    "  plan: null", '  plan: "docs/plans/plan.md"', 1)


class TestUpdateGateRefAtomic(unittest.TestCase):
    def _scaffold(self, d: Path, status: str = STATUS_PLAN_PHASE) -> Path:
        docs = d / "docs"
        (docs / "plans").mkdir(parents=True)
        (docs / "STATUS.md").write_text(status, encoding="utf-8")
        (docs / "plans" / "plan.md").write_text("# plan\n", encoding="utf-8")
        scripts = d / "scripts"
        scripts.mkdir()
        shutil.copy2(ROOT / "scripts" / "update-gate.sh",
                     scripts / "update-gate.sh")
        (scripts / "check_status.py").symlink_to(
            ROOT / "scripts" / "check_status.py")
        shutil.copytree(ROOT / "hooks" / "lib", d / "hooks" / "lib")
        return d

    def _run(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(root / "scripts" / "update-gate.sh"), *args],
            capture_output=True, text=True, check=False, timeout=60)

    def _status(self, root: Path) -> str:
        return (root / "docs" / "STATUS.md").read_text(encoding="utf-8")

    # --- 原子化（罠 b/c） ---

    def test_approve_ref_sets_gate_and_ref_together(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r = self._run(root, "plan", "approve", "--ref", "docs/plans/plan.md")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            status = self._status(root)
            self.assertIn("  plan: approved", status)
            self.assertIn('  plan: "docs/plans/plan.md"', status)

    def test_approve_ref_leaves_contract_green_immediately(self):
        """approve --ref 直後に evidence 整合が成立（窓なしの観測的証明）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r = self._run(root, "plan", "approve", "--ref", "docs/plans/plan.md")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            chk = subprocess.run(
                ["python3", str(root / "scripts" / "check_status.py"),
                 "--root", str(root), "--check-completion-evidence"],
                capture_output=True, text=True, check=False, timeout=60)
            self.assertEqual(chk.returncode, 0, f"{chk.stdout}\n{chk.stderr}")
            self.assertNotIn("EVIDENCE:", chk.stdout)

    # --- --ref 検証系（すべて状態不変で exit 1） ---

    def _assert_rejected_no_write(self, root: Path, *args: str) -> None:
        before = self._status(root)
        r = self._run(root, *args)
        self.assertNotEqual(r.returncode, 0,
                            f"must reject: {args}\n{r.stdout}\n{r.stderr}")
        self.assertEqual(before, self._status(root),
                         f"STATUS must be untouched: {args}")

    def test_ref_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", "docs/plans/nope.md")

    def test_ref_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            abs_path = str(root / "docs" / "plans" / "plan.md")
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", abs_path)

    def test_ref_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", "docs/plans/../plans/plan.md")

    def test_ref_unlisted_chars_rejected(self):
        """YAML/sed 安全性は文字 allowlist（[A-Za-z0-9._/-]）で担保する。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            weird = 'docs/plans/we"ird.md'
            (Path(d) / "docs" / "plans" / 'we"ird.md').write_text("x")
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", weird)

    def test_ref_on_gate_without_ref_key_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "brainstorm", "approve", "--ref", "docs/plans/plan.md")

    def test_ref_with_reset_and_na_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "brainstorm", "reset", "--ref", "docs/plans/plan.md")
            self._assert_rejected_no_write(
                root, "plan", "na", "--ref", "docs/plans/plan.md")

    def test_unknown_flag_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "plan", "approve", "--bogus")

    def test_ref_empty_string_rejected(self):
        """--ref "" は「--ref 未指定」に化けさせず明示エラー（review テスト強度
        指摘: allowlist は空文字に非マッチで素通りし、approved+空 ref の遅延
        FAIL に化ける）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(root, "plan", "approve", "--ref", "")

    def test_already_approved_ref_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            status = STATUS_PLAN_PHASE.replace("  plan: pending",
                                               "  plan: approved", 1)
            root = self._scaffold(Path(d), status)
            r = self._run(root, "plan", "approve", "--ref", "docs/plans/plan.md")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            self.assertIn("  plan: null", self._status(root),
                          "already-approved は ref を書き換えない")

    # --- na の ref null 化（writer 衛生の対称性） ---

    def test_na_nulls_ref(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d), STATUS_BUGFIX_NA)
            r = self._run(root, "plan", "na")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            status = self._status(root)
            self.assertIn("  plan: n/a", status)
            self.assertNotIn("docs/plans/plan.md", status,
                             "na は current_refs.plan を null 化する")

    # --- 部分失敗の封鎖（grill-plan 致命2） ---

    def test_ref_key_line_missing_rejected_before_write(self):
        """current_refs に対象 key 行が無い破損 STATUS では、sed が静かに
        素通りして gate だけ approved になる部分失敗を書込み前に拒否する。"""
        with tempfile.TemporaryDirectory() as d:
            broken = STATUS_PLAN_PHASE.replace("  plan: null\n", "", 1)
            root = self._scaffold(Path(d), broken)
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", "docs/plans/plan.md")

    # --- SIGPIPE 耐性（罠 a） ---

    def test_closed_stdout_pipe_still_approves(self):
        """読み手のいない pipe に stdout を繋いでも状態変更は完遂する。
        旧実装は書込み前の echo/cat が SIGPIPE 死 → gate pending のまま＝RED。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r_fd, w_fd = os.pipe()
            os.close(r_fd)  # 読み手なし → write は即 SIGPIPE/EPIPE
            try:
                r = subprocess.run(
                    ["bash", str(root / "scripts" / "update-gate.sh"),
                     "plan", "approve", "--ref", "docs/plans/plan.md"],
                    stdout=w_fd, stderr=subprocess.PIPE, text=True,
                    check=False, timeout=60)
            finally:
                os.close(w_fd)
            self.assertEqual(r.returncode, 0,
                             f"closed pipe must not abort state change: "
                             f"stderr={r.stderr}")
            status = self._status(root)
            self.assertIn("  plan: approved", status)
            self.assertIn('  plan: "docs/plans/plan.md"', status)

    # --- --ref × --ack 併用（judge gate 合流点・grill-plan 要検討3） ---

    def test_ref_with_ack_on_judge_gate(self):
        """review（JUDGE_GATES）で git なし→🟡 degrade→--ack 承認と --ref を
        併用: flag parser・ACK 後置追記・card push 移設が全部乗る経路。"""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            docs = root / "docs"
            (docs / "qa-reports").mkdir(parents=True)
            status = STATUS_PLAN_PHASE.replace(
                "phase: plan", "phase: review").replace(
                "  plan: pending", "  plan: approved", 1)
            (docs / "STATUS.md").write_text(status, encoding="utf-8")
            (docs / "qa-reports" / "review.md").write_text("# review\n",
                                                           encoding="utf-8")
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(ROOT / "scripts" / "update-gate.sh",
                         scripts / "update-gate.sh")
            for name in ("check_status.py", "build-judge-card.py",
                         "run-test-strength-drill.py", "record-test-result.py"):
                (scripts / name).symlink_to(ROOT / "scripts" / name)
            shutil.copytree(ROOT / "hooks" / "lib", root / "hooks" / "lib")
            r = subprocess.run(
                ["bash", str(scripts / "update-gate.sh"), "review", "approve",
                 "--ref", "docs/qa-reports/review.md", "--ack", "テスト確認済み"],
                capture_output=True, text=True, check=False, timeout=120)
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            status_after = (docs / "STATUS.md").read_text(encoding="utf-8")
            self.assertIn("  review: approved", status_after)
            self.assertIn('  review: "docs/qa-reports/review.md"', status_after)
            card = docs / "qa-reports" / "judge-review.md"
            self.assertTrue(card.is_file())
            self.assertIn("## ACK", card.read_text(encoding="utf-8"),
                          "ACK は書込み成立後にカードへ追記される")

    # --- 構造ピン（順序退行の静的ガード） ---

    def test_write_precedes_success_output_structure(self):
        """状態書込み（mv）が承認主張出力（[${ACTION_TAG}] 行・JUDGE CARD push）
        より前にあること。SIGPIPE trap の存在もピンする。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertIn("trap '' PIPE", text)
        write_idx = text.index('mv "$TMP" "$STATUS_FILE"')
        self.assertLess(write_idx, text.index("JUDGE CARD"),
                        "judge card push must come after the state write")
        self.assertLess(write_idx, text.index('[${ACTION_TAG}] ${GATE_NAME}:'),
                        "success report must come after the state write")

    def test_no_early_exit_pipe_consumers_structure(self):
        """F-1 回帰ピン: 早期終了する pipe 消費者（grep -q / grep -m1）は
        frontmatter_section の producer printf と EPIPE レースし、trap '' PIPE
        下で pipefail 誤判定＝正当な approve の偽拒否になる（実測 58/3000）。
        全量 drain か変数キャプチャ＋case 判定を使うこと。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertNotIn("| grep -q", text,
                         "早期終了 grep -q の再導入は F-1 レースの回帰")
        self.assertNotIn("| grep -m1", text,
                         "早期終了 grep -m1 の再導入は F-1 レースの回帰")

    def test_single_write_structure(self):
        """変異(a) 静的ピン: 書込みは単一 sed 呼び出し＋単一 mv。2回の別書込みに
        分割すると並行 reader が中間状態（gate だけ approved）を観測できる —
        動的テストでは検出不能なクラスのため構造でピンする。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertEqual(text.count('sed "${SED_ARGS[@]}"'), 1,
                         "STATUS 書込みは単一の sed 呼び出しであること")
        self.assertEqual(text.count('mv "$TMP" "$STATUS_FILE"'), 1,
                         "STATUS 書込みは単一の mv であること")


if __name__ == "__main__":
    unittest.main()
