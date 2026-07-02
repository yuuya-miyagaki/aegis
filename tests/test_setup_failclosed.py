"""iter54 C-2/C-3: bin/setup.sh の fail-open install 封鎖と --force データ損失防止。

C-2（2026-07-02 グリル再現）: 壊れた profile JSON／パス中の `'` があっても
「Setup complete.」rc0 で終わるのに CLAUDE.md/settings/hooks が未 install
＝moat ゼロの fail-open。修正 = profile JSON の冒頭検証（fail-closed）＋
python へのパス引き渡しを argv 経由に統一＋全 parse_json_array 呼び出しの rc 検査。

C-3: `--force` がユーザー所有ファイル（docs/STATUS.md 等の運用状態）を
無バックアップ上書き＝データ損失。修正 = 差分がある場合のみ上書き前に
.bak.<ts> 退避（D3 哲学の copy_file への適用。copy 自体・COPY 出力・
INSTALLED_PATHS 追加は現状維持）。
"""
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run_setup(framework_root, target, profile="minimal", force=False,
               check=False):
    cmd = ["bash", str(pathlib.Path(framework_root) / "bin" / "setup.sh"),
           f"--profile={profile}", f"--target={target}"]
    if force:
        cmd.append("--force")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def _fake_framework(tmp_path):
    """profile を改変可能な最小 framework コピー（実 repo は書き換えない）。"""
    fw = tmp_path / "framework"
    for rel in ("bin", "templates/profiles", "scripts", "hooks/lib", "docs"):
        (fw / rel).mkdir(parents=True)
    shutil.copy2(ROOT / "bin" / "setup.sh", fw / "bin" / "setup.sh")
    shutil.copy2(ROOT / "templates" / "hooks.template.json",
                 fw / "templates" / "hooks.template.json")
    for t in ("CLAUDE.template.md", "STATUS.template.md", "LEARNINGS.template.md"):
        shutil.copy2(ROOT / "templates" / t, fw / "templates" / t)
    shutil.copy2(ROOT / "scripts" / "check_framework_contract.py",
                 fw / "scripts" / "check_framework_contract.py")
    shutil.copy2(ROOT / "scripts" / "check_status.py",
                 fw / "scripts" / "check_status.py")
    for lib in (ROOT / "hooks" / "lib").glob("*.sh"):
        shutil.copy2(lib, fw / "hooks" / "lib" / lib.name)
    shutil.copy2(ROOT / "hooks" / "session-start.sh",
                 fw / "hooks" / "session-start.sh")
    shutil.copy2(ROOT / "templates" / "profiles" / "minimal.json",
                 fw / "templates" / "profiles" / "minimal.json")
    return fw


# ---------------------------------------------------------------------------
# C-2: 壊れ profile JSON → fail-closed（rc≠0・Setup complete. を出さない）
# ---------------------------------------------------------------------------
def test_broken_profile_json_fails_closed(tmp_path):
    fw = _fake_framework(tmp_path)
    profile = fw / "templates" / "profiles" / "minimal.json"
    profile.write_text('{"name": "minimal", "required": [broken', encoding="utf-8")
    target = tmp_path / "proj"
    r = _run_setup(fw, target)
    assert r.returncode != 0, (
        f"broken profile JSON must abort setup (fail-closed): "
        f"rc={r.returncode} out={r.stdout[-300:]!r}")
    assert "Setup complete." not in r.stdout
    assert not (target / "CLAUDE.md").exists()


def test_broken_profile_json_reports_reason(tmp_path):
    fw = _fake_framework(tmp_path)
    profile = fw / "templates" / "profiles" / "minimal.json"
    profile.write_text('{oops}', encoding="utf-8")
    r = _run_setup(fw, tmp_path / "proj")
    combined = (r.stdout + r.stderr).lower()
    assert "profile" in combined and ("json" in combined or "parse" in combined), (
        f"error must name the broken profile JSON: {combined[-300:]!r}")


# ---------------------------------------------------------------------------
# C-2: パス中の `'` → install 完遂（fail-open せず、壊れもしない）
# ---------------------------------------------------------------------------
def test_single_quote_in_target_path_installs_fully(tmp_path):
    target = tmp_path / "it's here" / "proj"
    r = _run_setup(ROOT, target, profile="minimal")
    assert r.returncode == 0, f"setup must succeed: {r.stderr[-300:]!r}"
    assert (target / "CLAUDE.md").is_file(), "CLAUDE.md must be installed"
    assert (target / "docs" / "STATUS.md").is_file(), "STATUS.md must be installed"
    assert (target / "hooks" / "session-start.sh").is_file(), (
        "hooks_include hooks must be installed")
    settings = target / ".claude" / "settings.local.json"
    assert settings.is_file(), "settings.local.json must be generated"
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert "hooks" in data, "generated settings must contain hooks wiring"


def test_single_quote_in_framework_path_installs_fully(tmp_path):
    """framework 側パスの `'` は parse_json_array の python -c 文字列を壊し、
    全ループが黙って空回り＝「Setup complete.」rc0 で 0 ファイル install の
    fail-open だった（C-2 の主再現経路）。argv 化＋rc 検査で install 完遂になる。"""
    quoted_parent = tmp_path / "it's fw"
    quoted_parent.mkdir()
    fw = _fake_framework(quoted_parent)
    target = tmp_path / "proj"
    r = _run_setup(fw, target, profile="minimal")
    assert r.returncode == 0, f"setup must succeed: {r.stderr[-300:]!r}"
    assert (target / "CLAUDE.md").is_file(), (
        f"CLAUDE.md must be installed (fail-open closed): out={r.stdout[-300:]!r}")
    assert (target / "docs" / "STATUS.md").is_file()
    assert (target / "hooks" / "session-start.sh").is_file()
    assert (target / ".claude" / "settings.local.json").is_file()


def test_single_quote_in_target_full_profile_hooks_complete(tmp_path):
    target = tmp_path / "o'brien"
    r = _run_setup(ROOT, target, profile="full")
    assert r.returncode == 0, f"setup must succeed: {r.stderr[-300:]!r}"
    profile = json.loads(
        (ROOT / "templates" / "profiles" / "full.json").read_text(encoding="utf-8"))
    for hook in profile["hooks_include"]:
        assert (target / "hooks" / hook).is_file(), f"missing hook: {hook}"


# ---------------------------------------------------------------------------
# C-3: --force はユーザー所有ファイルを .bak 退避してから上書き
# ---------------------------------------------------------------------------
def test_force_backs_up_user_status(tmp_path):
    target = tmp_path / "proj"
    _run_setup(ROOT, target, profile="minimal", check=True)
    status = target / "docs" / "STATUS.md"
    user_content = "---\nphase: implement\n---\nUSER OPERATIONAL STATE\n"
    status.write_text(user_content, encoding="utf-8")
    r = _run_setup(ROOT, target, profile="minimal", force=True, check=True)
    baks = list((target / "docs").glob("STATUS.md.bak.*"))
    assert baks, (
        f"--force must back up the user STATUS.md before overwrite: "
        f"out={r.stdout[-300:]!r}")
    assert baks[0].read_text(encoding="utf-8") == user_content, (
        ".bak must preserve the pre-overwrite user content")
    assert status.read_text(encoding="utf-8") != user_content, (
        "--force must still perform the overwrite")


def test_force_backs_up_user_claude_md(tmp_path):
    target = tmp_path / "proj"
    _run_setup(ROOT, target, profile="minimal", check=True)
    claude = target / "CLAUDE.md"
    claude.write_text("# my customized operating contract\n", encoding="utf-8")
    _run_setup(ROOT, target, profile="minimal", force=True, check=True)
    baks = list(target.glob("CLAUDE.md.bak.*"))
    assert baks, "--force must back up the user CLAUDE.md before overwrite"
    assert baks[0].read_text(encoding="utf-8") == "# my customized operating contract\n"


def test_force_identical_user_file_makes_no_bak(tmp_path):
    """FORCE＋同一内容は .bak を作らない（D3: 差分時のみ退避・churn ゼロ）。"""
    target = tmp_path / "proj"
    _run_setup(ROOT, target, profile="minimal", check=True)
    _run_setup(ROOT, target, profile="minimal", force=True, check=True)
    assert not list(target.glob("CLAUDE.md.bak.*"))
    assert not list((target / "docs").glob("STATUS.md.bak.*"))


def test_no_force_still_skips_existing_user_file(tmp_path):
    """--force なしの skip-if-exists は非退行（ユーザーファイルは触らない）。"""
    target = tmp_path / "proj"
    _run_setup(ROOT, target, profile="minimal", check=True)
    status = target / "docs" / "STATUS.md"
    status.write_text("USER EDIT\n", encoding="utf-8")
    _run_setup(ROOT, target, profile="minimal", check=True)
    assert status.read_text(encoding="utf-8") == "USER EDIT\n"
    assert not list((target / "docs").glob("STATUS.md.bak.*"))
