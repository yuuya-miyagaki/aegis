import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cp_lock_in_required_hook_files():
    text = (ROOT / "scripts" / "check_framework_contract.py").read_text()
    assert 'hooks/lib/cp-lock.sh' in text, \
        "cp-lock.sh must be registered in REQUIRED_HOOK_FILES"


def test_status_template_version_mirrors_contract():
    """STATUS テンプレの framework_version は check_framework_contract の
    FRAMEWORK_VERSION（single owner）を鏡写しにする。iter56: 版数リテラルを
    ハードコードすると bump 毎に手更新が要り drift 源になるため、単一ソースから
    読んで一致のみを検査する（版そのものは contract 側が唯一の owner）。"""
    import re
    contract = (ROOT / "scripts" / "check_framework_contract.py").read_text()
    m = re.search(r'FRAMEWORK_VERSION\s*=\s*"([^"]+)"', contract)
    assert m, "FRAMEWORK_VERSION が check_framework_contract.py に無い"
    version = m.group(1)
    tpl = (ROOT / "templates" / "STATUS.template.md").read_text()
    assert f'framework_version: "{version}"' in tpl, \
        f"STATUS テンプレの version が contract ({version}) と不一致"


def test_framework_contract_passes():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_framework_contract.py")],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, f"contract failed:\n{r.stdout}\n{r.stderr}"
