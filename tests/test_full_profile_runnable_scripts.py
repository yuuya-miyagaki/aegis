"""iter56 ⑥: full install 先で manifest の実行可スクリプト（allow|ask）が
実在することを検証する。iter55 の install テストは「hook が allow する」ことのみ
検証し「ファイルが存在する」ことを検証していなかった（M2 実測: retro_report.py
が hook ALLOW なのに未配布で /retro が手動フォールバック化）。"""
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_framework_contract as cfc  # noqa: E402


class TestFullInstallRunnableScripts(unittest.TestCase):
    def test_full_install_contains_all_runnable_scripts(self):
        import json
        import tempfile
        full = json.loads(
            (ROOT / "templates" / "profiles" / "full.json").read_text(encoding="utf-8"))
        unshipped = set(full.get("intentional_unshipped", {}))
        with tempfile.TemporaryDirectory() as t:
            target = pathlib.Path(t) / "proj"
            target.mkdir()
            subprocess.run(
                ["bash", str(ROOT / "bin" / "setup.sh"),
                 "--profile=full", f"--target={target}"],
                check=True, capture_output=True, text=True)
            manifest = cfc.load_scripts_manifest(ROOT)
            missing = [e for e, c in sorted(manifest.items())
                       if c in ("allow", "ask") and e not in unshipped
                       and not (target / e).is_file()]
            self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
