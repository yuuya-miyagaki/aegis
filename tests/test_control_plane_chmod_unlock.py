import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _scratch():
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n")
    (p / "hooks" / "lib").mkdir(parents=True)
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 p / "hooks" / "check-control-plane.sh")
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        shutil.copy2(ROOT / "hooks" / "lib" / lib, p / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    return subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root)).stdout


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


class TestChmodUnlockGuard:
    def setup_method(self):
        self.tmp = _scratch()
        self.root = Path(self.tmp.name)

    def teardown_method(self):
        self.tmp.cleanup()

    def test_chmod_unlock_forms_on_cp_denied(self):
        for cmd in (
            "chmod +w hooks/lib/emit.sh",
            "chmod u+w hooks/lib/emit.sh",
            "chmod -R u+w hooks",
            "chmod a+w scripts/x.py",
            "chflags nouchg hooks/lib/emit.sh",
            "chattr -i hooks/lib/emit.sh",
        ):
            assert _denied(_hook(self.root, cmd)), f"must deny: {cmd!r}"

    def test_rename_move_of_cp_denied(self):
        for cmd in ("mv hooks hooks_bak", "cp safe.txt hooks", "mv scripts s2"):
            assert _denied(_hook(self.root, cmd)), f"must deny: {cmd!r}"

    def test_non_cp_chmod_allowed(self):
        assert _allowed(_hook(self.root, "chmod 755 src/app.py"))
        assert _allowed(_hook(self.root, "chmod +x build/run.sh"))
