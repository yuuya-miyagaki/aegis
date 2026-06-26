#!/usr/bin/env python3
"""K-12 (v1.6.2 / JNY-07): profile recommended と checker / mapping の対称性。

第6回 Phase C5 JNY-07 (非エンジニア E2E 阻害の核):
  - full profile は BRAINSTORM-RECORD / SPEC / TRANSLATION-MAPPING /
    RUNBOOK / MANUAL / UAT-RESULTS の 6 件のみテンプレを配布
  - check_status.py CLIENT_GATE_ARTIFACTS は PRD / SCOPE / NFR /
    ACCEPTANCE / HANDOVER-TO-DEV / translation の sentinel を要求
  → ファイル名空間が完全に非対称で、非エンジニアは「テンプレが無いのに
    テンプレ通り埋めろ」で詰む。

K-12 対策: ARTIFACT_TO_TEMPLATE という明示マッピング dict を単一所有
（scripts/_artifact_template_map.py）。本テストは：
  1. checker が要求する全 artifact が mapping に登録されている
  2. mapping の全 template が full profile recommended に含まれている
  3. mapping の全 template が disk に実在する
  4. deny メッセージにテンプレ場所が含まれている
の 4 契約で恒久封鎖する。
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    from _artifact_template_map import ARTIFACT_TO_TEMPLATE
finally:
    sys.path.pop(0)


PROFILE_FULL = ROOT / "templates" / "profiles" / "full.json"


def _client_gate_artifacts() -> list[tuple[str, str]]:
    """check_status.py の CLIENT_GATE_ARTIFACTS を読み込む"""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import check_status
    finally:
        sys.path.pop(0)
    return list(check_status.CLIENT_GATE_ARTIFACTS)


class TestArtifactMappingCoverage(unittest.TestCase):
    """ARTIFACT_TO_TEMPLATE が必須 artifact を網羅する"""

    def test_mapping_covers_all_client_gate_artifacts(self):
        for path, _sentinel in _client_gate_artifacts():
            self.assertIn(
                path, ARTIFACT_TO_TEMPLATE,
                f"{path} required by client_ready_for_dev but not in "
                f"ARTIFACT_TO_TEMPLATE — add it to "
                f"scripts/_artifact_template_map.py"
            )


class TestFullProfileShipsAllTemplates(unittest.TestCase):
    """full profile recommended が ARTIFACT_TO_TEMPLATE の全 template を含む"""

    def test_full_profile_has_all_mapped_templates(self):
        profile = json.loads(PROFILE_FULL.read_text(encoding="utf-8"))
        distributed = set(profile.get("recommended", []))
        for artifact, template in ARTIFACT_TO_TEMPLATE.items():
            self.assertIn(
                template, distributed,
                f"{template} (for {artifact}) required by mapping but "
                f"not in full profile recommended — non-engineer cannot "
                f"find the template (JNY-07)"
            )


class TestMappedTemplatesExist(unittest.TestCase):
    """mapping の全 template path が disk に実在する"""

    def test_all_template_paths_exist(self):
        for artifact, template in ARTIFACT_TO_TEMPLATE.items():
            path = ROOT / template
            self.assertTrue(
                path.exists(),
                f"{template} (for {artifact}) listed in mapping but not "
                f"on disk — typo or missing template file"
            )


class TestDenyMessageIncludesTemplatePath(unittest.TestCase):
    """check_status の deny メッセージにテンプレ場所が含まれる"""

    def test_deny_message_mentions_pertinent_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "proj"
            project.mkdir()
            (project / "docs").mkdir()
            # Minimal STATUS.md so check_status doesn't crash on missing file
            (project / "docs" / "STATUS.md").write_text(
                "---\nframework: aegis\nmode: Client\nphase: handover\n"
                "task_type: feature\niteration: 1\n"
                "gate_approvals:\n"
                "  client_ready_for_dev: pending\n"
                "  brainstorm: pending\n  plan: pending\n  review: pending\n"
                "  qa: pending\n  security: pending\n  deploy: pending\n"
                "  dev_ready_for_client: pending\n"
                "current_refs:\n  requirements: null\n"
                "blockers: []\nfailure_tracking: null\n"
                'last_updated: "2026-06-13T00:00:00Z"\n---\n',
                encoding="utf-8"
            )
            r = subprocess.run(
                ["python3", str(ROOT / "scripts" / "check_status.py"),
                 "--root", str(project),
                 "--pre-approve-gate", "client_ready_for_dev"],
                capture_output=True, text=True,
            )
            combined = r.stdout + r.stderr
            # 必須 artifact に紐づく代表的なテンプレ名が deny に出ること
            self.assertIn(
                "templates/PRD.template.md", combined,
                f"deny must mention PRD template: {combined[:400]}"
            )
            self.assertIn(
                "templates/HANDOVER-TO-DEV.template.md", combined,
                f"deny must mention HANDOVER-TO-DEV template: {combined[:400]}"
            )


class TestFullInstallSurfacesTemplateHints(unittest.TestCase):
    """iter48 (JNY-07 e2e): full install が _artifact_template_map.py を同梱し、
    client-gate deny に実際にテンプレ位置ヒントが出る（install で空 degrade しない）
    ことを固定する。回帰: map を full.json から外すと deny ヒントが消えて本テストが RED。"""

    _STATUS = (
        "---\nframework: aegis\nmode: Client\nphase: handover\n"
        "task_type: feature\niteration: 1\n"
        "gate_approvals:\n"
        "  client_ready_for_dev: pending\n"
        "  brainstorm: pending\n  plan: pending\n  review: pending\n"
        "  qa: pending\n  security: pending\n  deploy: pending\n"
        "  dev_ready_for_client: pending\n"
        "current_refs:\n  requirements: null\n"
        "blockers: []\nfailure_tracking: null\n"
        'last_updated: "2026-06-26T00:00:00Z"\n---\n'
    )

    def test_full_install_deny_includes_template_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "proj"
            subprocess.run(
                ["bash", str(ROOT / "bin" / "setup.sh"),
                 "--profile=full", f"--target={target}"],
                check=True, capture_output=True, text=True,
            )
            # the JNY-07 data dependency must be shipped by the full profile
            self.assertTrue(
                (target / "scripts" / "_artifact_template_map.py").exists(),
                "full install must ship scripts/_artifact_template_map.py (JNY-07 data dep)")
            (target / "docs").mkdir(parents=True, exist_ok=True)
            (target / "docs" / "STATUS.md").write_text(self._STATUS, encoding="utf-8")
            # run the INSTALL's own check_status so import resolution proves
            # self-containment (sys.path[0] = the install's scripts/ dir).
            r = subprocess.run(
                ["python3", str(target / "scripts" / "check_status.py"),
                 "--root", str(target),
                 "--pre-approve-gate", "client_ready_for_dev"],
                capture_output=True, text=True,
            )
            combined = r.stdout + r.stderr
            self.assertIn(
                "templates/PRD.template.md", combined,
                f"full install client-gate deny must surface the PRD template hint "
                f"(JNY-07 must not degrade to empty in the field): {combined[:400]}")


if __name__ == "__main__":
    unittest.main()
