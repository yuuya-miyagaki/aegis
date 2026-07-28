#!/usr/bin/env python3
"""pytest attestation plugin (iter78). Writes structured execution events to
$AEGIS_ATTEST_EVENT_PATH as JSONL. FAITHFUL RECORDING ONLY — no counting, no
verdict; aggregation lives in scripts/attest-test-run.py so there is exactly
one decision point. No-op without the env var (safe to import anywhere).
Internal failures are swallowed: a dead plugin must not break the test run;
missing events fail CLOSED at the attestor (rc2, no green)."""
import json
import os

_PATH = os.environ.get("AEGIS_ATTEST_EVENT_PATH")


def _emit(obj):
    if not _PATH:
        return
    try:
        with open(_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


def pytest_collectreport(report):
    try:
        if report.failed:
            _emit({"e": "collect_error", "nodeid": str(getattr(report, "nodeid", ""))})
    except Exception:
        pass


def pytest_runtest_logreport(report):
    try:
        _emit({"e": "test", "nodeid": str(report.nodeid), "when": str(report.when),
               "outcome": str(report.outcome),
               "wasxfail": hasattr(report, "wasxfail")})
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    try:
        _emit({"e": "sessionfinish", "exitstatus": int(exitstatus)})
    except Exception:
        pass
