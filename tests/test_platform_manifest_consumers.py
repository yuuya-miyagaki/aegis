import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_framework_contract as cfc
import check_reference_drift as crd


# --- Task 2: check_framework_contract consumes manifest model/effort atoms ---

def test_policy_consistency_passes_on_real_policy():
    # 実ポリシー表はマニフェストに収まっている＝失敗ゼロ
    assert cfc.check_model_policy_manifest_consistency() == []


def test_policy_consistency_flags_forbidden_model(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"planner.md": ("haiku", "max")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("haiku" in f and "forbidden" in f for f in failures)


def test_policy_consistency_flags_unknown_model(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"planner.md": ("claude-opus-4-8", "max")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("not in ALLOWED_MODELS" in f for f in failures)


def test_policy_consistency_flags_unknown_effort(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"qa.md": ("opus", "ultra")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("not in EFFORT_LEVELS" in f for f in failures)


def test_policy_consistency_flags_opus_only_effort_on_nonopus(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"reviewer-testing.md": ("sonnet", "max")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("only allowed on opus" in f for f in failures)


def test_contract_imports_manifest_atoms():
    # マニフェスト原子を import 経由で使用していること（リテラル再定義の防止）
    from platform_manifest import OPUS_ONLY_EFFORTS
    assert cfc.OPUS_ONLY_EFFORTS is OPUS_ONLY_EFFORTS
