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


# --- Task 3: check_reference_drift consumes manifest event/tool atoms ---

def _write_template(tmp_path, hooks: dict) -> Path:
    root = tmp_path
    (root / "templates").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "hooks.template.json").write_text(
        json.dumps({"hooks": hooks}), encoding="utf-8"
    )
    return root


def test_drift_clean_template_passes(tmp_path):
    root = _write_template(tmp_path, {
        "PreToolUse": [{"matcher": "Edit|Write|NotebookEdit", "hooks": []}],
        "PostToolUse": [{"matcher": "Bash", "hooks": []}],
    })
    failures, warnings = crd.check_platform_manifest(root)
    assert failures == []
    assert warnings == []  # staleness は別関数なので壁時計に依存しない


def test_drift_unknown_event_fails(tmp_path):
    root = _write_template(tmp_path, {
        "PreToolUseX": [{"matcher": "Bash", "hooks": []}],
    })
    failures, _ = crd.check_platform_manifest(root)
    assert any("PreToolUseX" in f and "KNOWN_HOOK_EVENTS" in f for f in failures)


def test_drift_unknown_tool_warns(tmp_path):
    root = _write_template(tmp_path, {
        "PreToolUse": [{"matcher": "Bash|FrobnicateTool", "hooks": []}],
    })
    failures, warnings = crd.check_platform_manifest(root)
    assert failures == []
    assert any("FrobnicateTool" in w for w in warnings)


def test_drift_ignores_session_source_matchers(tmp_path):
    # SessionStart の matcher は tool ではない＝WARN を出さない
    root = _write_template(tmp_path, {
        "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": []}],
    })
    failures, warnings = crd.check_platform_manifest(root)
    assert failures == []
    assert warnings == []


def test_staleness_skipped_when_not_framework_root(tmp_path):
    # platform_manifest.py を含まない root（例: install 先 scaffold）では staleness を
    # 発火させない＝二重発火を防ぐ。
    failures, warnings = crd.check_platform_staleness(tmp_path)
    assert failures == []
    assert warnings == []


def test_drift_malformed_matcher_does_not_crash(tmp_path):
    # drift checker は不正 template を「報告」すべきで crash してはならない:
    # matcher が null / 非 dict 要素 / hooks が非 dict のいずれでも例外を出さない。
    root = _write_template(tmp_path, {
        "PreToolUse": [{"matcher": None, "hooks": []}, "not-a-dict"],
    })
    failures, warnings = crd.check_platform_manifest(root)  # 例外が出ないこと
    assert isinstance(failures, list) and isinstance(warnings, list)

    bad = tmp_path / "bad"
    (bad / "templates").mkdir(parents=True)
    (bad / "templates" / "hooks.template.json").write_text(
        json.dumps({"hooks": []}), encoding="utf-8")
    failures, warnings = crd.check_platform_manifest(bad)  # hooks が list でも crash しない
    assert isinstance(failures, list) and isinstance(warnings, list)
