#!/usr/bin/env python3
"""K-5 (v1.6.2) grill 致命 2: safety.sh / secrets-patterns.sh / phase-skills.sh
が profile required と framework_contract REQUIRED の両方に登録されている
契約。

第6回 Phase A REDTEAM-05 (S-1): 既存の secrets-patterns.sh / phase-skills.sh
は profile required に登録されておらず、install 先で削除しても contract が
PASS する＝F6 同型の 2 例目。新規 safety.sh も同じ落とし穴に嵌まる前に、
profile / contract の双方で必須化する。
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# K-5 で必須化する 3 つの lib（safety.sh は v1.6.2 新規）
REQUIRED_LIBS = [
    "hooks/lib/safety.sh",
    "hooks/lib/secrets-patterns.sh",
    "hooks/lib/phase-skills.sh",
]

PROFILES = ["minimal", "standard", "full"]


class TestProfileRequiredHasSafetyLibs(unittest.TestCase):

    def test_all_profiles_require_safety_libs(self):
        """3 profile すべてが REQUIRED_LIBS を required に含む"""
        for prof in PROFILES:
            path = ROOT / "templates" / "profiles" / f"{prof}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            required = set(data.get("required", []))
            for lib in REQUIRED_LIBS:
                self.assertIn(
                    lib, required,
                    f"{prof}.json: {lib} missing from required"
                )


class TestFrameworkContractHasSafetyLibs(unittest.TestCase):

    def test_check_framework_contract_lists_safety_libs(self):
        """scripts/check_framework_contract.py REQUIRED_HOOK_FILES に登録
        （Path オブジェクトのリストなので relative path で比較）"""
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import check_framework_contract as c
        finally:
            sys.path.pop(0)
        required_rel = {
            str(p.relative_to(ROOT)) for p in c.REQUIRED_HOOK_FILES
        }
        for lib in REQUIRED_LIBS:
            self.assertIn(
                lib, required_rel,
                f"check_framework_contract REQUIRED_HOOK_FILES missing {lib}"
            )


class TestRemovingSafetyLibFailsContract(unittest.TestCase):
    """install 先で safety.sh を消すと contract / scaffold smoke が FAIL"""

    def test_contract_fails_when_safety_lib_removed(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "proj"
            # Run setup
            r = subprocess.run(
                [str(ROOT / "bin" / "setup.sh"),
                 "--profile=full", f"--target={target}"],
                capture_output=True, text=True,
            )
            self.assertEqual(
                r.returncode, 0, f"setup failed: {r.stdout}\n{r.stderr}"
            )
            # Remove safety.sh
            (target / "hooks" / "lib" / "safety.sh").unlink()
            # Contract check must fail
            r = subprocess.run(
                ["python3", str(ROOT / "scripts" / "check_framework_contract.py"),
                 "--profile=full", "--root", str(target)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(
                r.returncode, 0,
                f"contract should fail without safety.sh: stdout={r.stdout!r}"
            )


if __name__ == "__main__":
    unittest.main()
