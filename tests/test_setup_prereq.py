#!/usr/bin/env python3
"""K-10 (v1.6.2 / DIST-03): setup.sh の prereq 検査契約。

第6回 Phase A DIST-03: 偽 python3 stub（exit 127）を PATH 先頭に置いて
setup.sh を走らせると `set -euo pipefail` 下でも process substitution
`while ... < <(parse_json_array ...)` が pipefail を伝播せず、empty
stdout でループ 0 回 → "Setup complete." EXIT=0 / 0 ファイル install。

K-10 対策: setup.sh 冒頭で python3 / bash の存在＋実行可能性を
検査し、不在/壊れていれば早期 abort。
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SH = ROOT / "bin" / "setup.sh"


class TestSetupPrereq(unittest.TestCase):

    def test_setup_fails_loudly_when_python3_broken(self):
        """python3 stub が exit 非 0 なら setup は明示エラーで abort"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            stub_dir = tmp_path / "bin"
            stub_dir.mkdir()
            stub = stub_dir / "python3"
            stub.write_text("#!/bin/sh\nexit 127\n")
            stub.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{stub_dir}:{env.get('PATH', '')}"
            r = subprocess.run(
                [str(SETUP_SH), "--profile=standard",
                 f"--target={tmp_path / 'proj'}"],
                env=env, capture_output=True, text=True,
            )
            self.assertNotEqual(
                r.returncode, 0,
                f"setup should fail with broken python3: "
                f"stdout={r.stdout[:200]} stderr={r.stderr[:200]}"
            )
            self.assertIn(
                "python3",
                (r.stdout + r.stderr).lower(),
                f"error message should mention python3: {r.stderr}"
            )

    def test_setup_succeeds_with_working_python3(self):
        """通常の python3 がいれば setup は成功 (回帰)"""
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                [str(SETUP_SH), "--profile=minimal",
                 f"--target={pathlib.Path(tmp) / 'proj'}"],
                capture_output=True, text=True,
            )
            self.assertEqual(
                r.returncode, 0,
                f"setup should succeed: stdout={r.stdout[:200]} "
                f"stderr={r.stderr[:200]}"
            )


if __name__ == "__main__":
    unittest.main()
