"""iter56 ①: broad-staging 検出の `\\.` がトークン境界非アンカーで、
.env.example / .gitignore 等の先頭ドットファイル名に前方一致していた
（M2 で2回再現）。broad-dot は「ディレクトリ全体を指すトークン」
（. / .. / ./ / ../ 直後が空白・行末・シェルデリミタ）のみに限定する。"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-secrets.sh"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _mkrepo(path):
    """repo に実 .env を置く: broad 判定が真なら deny になる状態を作る。"""
    path.mkdir()
    _git(path, "init")
    (path / ".env").write_text("SECRET=x\n")
    (path / ".env.example").write_text("SECRET=\n")
    (path / ".gitignore").write_text(".env\n")
    return path


def _run(cmd, cwd):
    return subprocess.run(
        ["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True, text=True, cwd=str(cwd),
    ).stdout


# --- 負例: 先頭ドットの個別ファイル add は broad ではない（修正の本体） ---

def test_add_env_example_is_not_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r1")
    out = _run("git add .env.example", cwd=repo)
    assert '"permissionDecision":"deny"' not in out, out


def test_add_gitignore_is_not_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r2")
    out = _run("git add .gitignore", cwd=repo)
    assert '"permissionDecision":"deny"' not in out, out


def test_add_dot_dir_path_is_not_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r3")
    (repo / ".github").mkdir()
    (repo / ".github" / "ci.yml").write_text("x\n")
    out = _run("git add .github/ci.yml", cwd=repo)
    assert '"permissionDecision":"deny"' not in out, out


# --- 正例: broad staging は引き続き deny（回帰ガード） ---

def test_add_bare_dot_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r4")
    out = _run("git add .", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dot_with_following_arg_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r5")
    out = _run("git add . foo.txt", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dot_slash_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r6")
    out = _run("git add ./", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dotdot_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r7")
    sub = repo / "sub"
    sub.mkdir()
    out = _run("git add ..", cwd=sub)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dash_a_still_broad(tmp_path):
    repo = _mkrepo(tmp_path / "r8")
    out = _run("git add -A", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dot_before_shell_delimiter_still_broad(tmp_path):
    """grill 致命1: `.` の直後がシェルデリミタでも broad（境界を空白/行末に
    限定すると `git add .&&git commit` がすり抜け＝moat 後退）。"""
    repo = _mkrepo(tmp_path / "r10")
    out = _run("git add .&&git commit -m x", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out
    out = _run("git add .;true", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


def test_add_dot_before_paren_or_redirect_still_broad(tmp_path):
    """grill-code 🔴: デリミタ列挙（;&|）は `)` `>` を漏らす。境界は
    「パス構成文字以外すべて」の否定クラスでなければならない。"""
    repo = _mkrepo(tmp_path / "r11")
    sub = repo / "sub"
    sub.mkdir()
    out = _run("(cd sub && git add .)", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out
    out = _run("git add .>out", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out


# --- 付随: 直接 .env deny 文言に safe variant 案内がある ---

def test_direct_env_deny_mentions_safe_variant(tmp_path):
    repo = _mkrepo(tmp_path / "r9")
    out = _run("git add .env", cwd=repo)
    assert '"permissionDecision":"deny"' in out, out
    assert ".env.example" in out, out
