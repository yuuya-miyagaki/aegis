#!/usr/bin/env python3
"""iter43 Task 6: snapshot.sh が framework contract の必須 lib に登録され、
install で配布されることの契約（F6 life-support）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_framework_contract as c  # noqa: E402


def test_snapshot_lib_is_required():
    assert any("snapshot.sh" in str(p) for p in c.REQUIRED_HOOK_FILES), (
        "hooks/lib/snapshot.sh must be in REQUIRED_HOOK_FILES (F6 life-support)"
    )


def test_snapshot_lib_exists_on_disk():
    assert (ROOT / "hooks" / "lib" / "snapshot.sh").exists()
