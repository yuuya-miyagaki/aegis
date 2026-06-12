#!/usr/bin/env python3
"""P1-C② (OBS-019): judge ゲート承認時、update-gate.sh はカード全文を
stdout に push する（pull 専用カードは client に届かないことが行動レビューで実証済み）。"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_CONTENT = """---
framework: aegis
framework_version: "1.6.0"
project_name: test
mode: Dev
phase: review
task_type: feature
task_size: M
last_updated: "2026-06-12"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: null
  plan: null
  spec: null
  review: docs/qa-reports/review.md
  qa: null
  security: null
  deploy: null
  translation: null
---
"""


class TestJudgeCardPush(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        docs = d / "docs"
        (docs / "qa-reports").mkdir(parents=True)
        (docs / "STATUS.md").write_text(STATUS_CONTENT, encoding="utf-8")
        (docs / "qa-reports" / "review.md").write_text("# review\n", encoding="utf-8")
        scripts = d / "scripts"
        scripts.mkdir()
        shutil.copy2(ROOT / "scripts" / "update-gate.sh", scripts / "update-gate.sh")
        for name in ("check_status.py", "build-judge-card.py",
                     "run-test-strength-drill.py", "record-test-result.py"):
            (scripts / name).symlink_to(ROOT / "scripts" / name)
        shutil.copytree(ROOT / "hooks" / "lib", d / "hooks" / "lib")
        return d

    def test_approve_pushes_card_to_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp))
            # git なし → drill 系は build() の catch-all で 🟡 degrade → --ack 経路
            r = subprocess.run(
                ["bash", str(root / "scripts" / "update-gate.sh"),
                 "review", "approve", "--ack", "テスト確認済み"],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
            self.assertIn("JUDGE CARD", r.stdout)
            card = root / "docs" / "qa-reports" / "judge-review.md"
            self.assertTrue(card.is_file())
            # カード本文（ヘッダ行）が stdout に含まれる = 全文 push
            first_line = card.read_text(encoding="utf-8").splitlines()[0]
            self.assertIn(first_line, r.stdout)
            self.assertIn("review: approved",
                          (root / "docs" / "STATUS.md").read_text(encoding="utf-8")
                          .replace("  review: approved", "review: approved"))


if __name__ == "__main__":
    unittest.main()
