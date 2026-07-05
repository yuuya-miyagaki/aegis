import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import platform_manifest as pm


def test_required_constants_are_frozensets():
    for name in (
        "ALLOWED_MODELS", "FORBIDDEN_MODELS", "EFFORT_LEVELS",
        "OPUS_ONLY_EFFORTS", "KNOWN_HOOK_EVENTS",
        "TOOL_MATCHING_EVENTS", "KNOWN_TOOL_NAMES",
    ):
        assert isinstance(getattr(pm, name), frozenset), name


def test_allowed_and_forbidden_models_are_disjoint():
    assert pm.ALLOWED_MODELS & pm.FORBIDDEN_MODELS == frozenset()


def test_opus_only_efforts_subset_of_effort_levels():
    assert pm.OPUS_ONLY_EFFORTS <= pm.EFFORT_LEVELS


def test_tool_matching_events_subset_of_known_events():
    assert pm.TOOL_MATCHING_EVENTS <= pm.KNOWN_HOOK_EVENTS


def test_verification_dates_parse_as_iso():
    assert set(pm.PLATFORM_VERIFIED) == {
        "models", "hook_events", "tool_names", "hook_output_schema",
        "posttoolfailure_stderr",
    }
    for iso in pm.PLATFORM_VERIFIED.values():
        date.fromisoformat(iso)  # raises if malformed


def test_stale_keys_flags_old_dates_only():
    # 全キーが当日なら stale 無し
    today = date.fromisoformat(pm.PLATFORM_VERIFIED["models"])
    assert pm.stale_keys(today=today) == []
    # 最新検証日 + STALENESS_DAYS + 1 日後は全キー stale
    base = max(date.fromisoformat(v) for v in pm.PLATFORM_VERIFIED.values())
    future = base + timedelta(days=pm.STALENESS_DAYS + 1)
    assert sorted(pm.stale_keys(today=future)) == sorted(pm.PLATFORM_VERIFIED)
