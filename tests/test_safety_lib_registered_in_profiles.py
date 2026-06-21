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

# 複数 hook が source する必須 lib。fail-closed 依存があるため 3 profile の
# required と契約で配布を固定する（safety.sh は v1.6.2、frontmatter.sh は
# M3/v1.7.1 で session-start に加え control-plane/task-completed も hard-depend）。
REQUIRED_LIBS = [
    "hooks/lib/safety.sh",
    "hooks/lib/secrets-patterns.sh",
    "hooks/lib/phase-skills.sh",
    "hooks/lib/frontmatter.sh",
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
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "proj"
            # B1: standard profile を使う。`--profile=full --root` は
            # check_framework_contract が *常に* ERROR にするため、safety.sh の
            # 有無に関係なく rc!=0 になり「偽の安心」だった（テストが別理由で通る）。
            # standard は safety.sh を required に含むので、削除で「missing required
            # file」として *safety.sh を理由に* 正しく FAIL する。
            r = subprocess.run(
                [str(ROOT / "bin" / "setup.sh"),
                 "--profile=standard", f"--target={target}"],
                capture_output=True, text=True,
            )
            self.assertEqual(
                r.returncode, 0, f"setup failed: {r.stdout}\n{r.stderr}"
            )

            def _contract():
                return subprocess.run(
                    ["python3", str(ROOT / "scripts" / "check_framework_contract.py"),
                     "--profile=standard", "--root", str(target)],
                    capture_output=True, text=True,
                )

            # 因果の固定: safety.sh があるうちは PASS。
            r_intact = _contract()
            self.assertEqual(
                r_intact.returncode, 0,
                f"健全な standard install は PASS すべき: "
                f"{r_intact.stdout}\n{r_intact.stderr}"
            )

            # safety.sh を消すと FAIL（しかも safety.sh を理由に）。
            (target / "hooks" / "lib" / "safety.sh").unlink()
            r_removed = _contract()
            self.assertNotEqual(
                r_removed.returncode, 0,
                f"safety.sh 削除後は FAIL すべき: stdout={r_removed.stdout!r}"
            )
            self.assertIn(
                "safety.sh", r_removed.stdout,
                f"FAIL は safety.sh を理由にすべき（別理由の偽 FAIL ではない）: "
                f"{r_removed.stdout!r}"
            )


if __name__ == "__main__":
    unittest.main()
