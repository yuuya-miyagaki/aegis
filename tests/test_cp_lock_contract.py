import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cp_lock_in_required_hook_files():
    text = (ROOT / "scripts" / "check_framework_contract.py").read_text()
    assert 'hooks/lib/cp-lock.sh' in text, \
        "cp-lock.sh must be registered in REQUIRED_HOOK_FILES"


def test_version_is_1_15_0_and_synced():
    contract = (ROOT / "scripts" / "check_framework_contract.py").read_text()
    assert 'FRAMEWORK_VERSION = "1.15.0"' in contract
    tpl = (ROOT / "templates" / "STATUS.template.md").read_text()
    assert 'framework_version: "1.15.0"' in tpl


def test_framework_contract_passes():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_framework_contract.py")],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, f"contract failed:\n{r.stdout}\n{r.stderr}"
