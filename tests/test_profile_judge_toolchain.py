"""iter41 D1: standard profile must ship the judge toolchain so review/qa/
security/deploy gates are approvable. build-judge-card.py importlib-loads
run-test-strength-drill.py (no fallback), and check_status.run_judge_card
returns 1 (fail-closed) when the builder is absent — so without these the
standard install cannot approve any judge gate."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _profile(name):
    return json.loads(
        (ROOT / "templates" / "profiles" / f"{name}.json").read_text()
    )


def test_standard_requires_gate_blocking_judge_scripts():
    """The two gate-blocking scripts must be `required` so the contract enforces
    them (recommended-missing is only a WARNING)."""
    req = set(_profile("standard").get("required", []))
    for needed in (
        "scripts/build-judge-card.py",
        "scripts/run-test-strength-drill.py",
    ):
        assert needed in req, f"standard required missing gate-critical: {needed}"


def test_standard_recommends_judge_support():
    """record-test-result.py (green records) and fingerprint.sh (nolib fallback)
    don't block card build, so recommended is sufficient."""
    files = set(_profile("standard").get("required", [])) | set(
        _profile("standard").get("recommended", [])
    )
    for needed in ("scripts/record-test-result.py", "hooks/lib/fingerprint.sh"):
        assert needed in files, f"standard profile missing judge support: {needed}"
