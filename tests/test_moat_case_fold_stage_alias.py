# iter77 Task1 (RED): moat case-fold / stage-alias pins.
#
# 旧実装（未修正 hooks）の実測ギャップを pin する:
#   - check-destructive.sh: 生経路（rm 特例 :128 / CMD_REGEX ループ :144 / fallback :60-77）
#     が case-sensitive で、非難読化の大文字コマンド（RM -rf / GIT RESET --HARD /
#     CHMOD -R / > /ETC/...）を silent allow する。NORM 経路の grep -i は
#     NORM!=CMD（難読化実在）のときしか走らないため、平文大文字は素通り。
#     macOS 等 case-insensitive FS では /bin/rm が RM で実行される＝実バイパス。
#   - check-secrets.sh: _STAGE_BROAD_RE (:169) が verb `add` のみで、`git stage -A` /
#     `git stage .`（stage は add の完全 alias）の broad staging が repo 内の実 .env
#     ごと素通りする。大文字 `GIT STAGE -A` も同様。難読化形 git${IFS}stage -A も
#     NORM 経路の同 regex を通るため素通り。
#
# 期待値は修正後の仕様（新実装）。旧実装での実測（2026-07-26・HEAD=ad04973）:
#   赤11: D-1 D-2 D-3 D-4a D-4b D-6 D-7 S-1 S-2 S-3 S-5（すべて allow だった）
#   緑4:  D-5 (allow) / S-4 (allow) / S-6 (deny) / S-7 (deny)
import json, subprocess, os, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _verdict(out):
    out = out.strip()
    if out == "{}":
        return "allow"
    if '"permissionDecision":"deny"' in out or '"permissionDecision": "deny"' in out:
        return "deny"
    if '"permissionDecision":"ask"' in out or '"permissionDecision": "ask"' in out:
        return "ask"
    return "other:" + out[:60]


def _run(hook, cmd):
    p = subprocess.run(["bash", os.path.join(ROOT, "hooks", hook)],
                       input=json.dumps({"tool_input": {"command": cmd}}).encode(),
                       capture_output=True, cwd=ROOT)
    return _verdict(p.stdout.decode("utf-8", "replace"))


def _run_raw(hook, raw_payload):
    """hook に生 stdin（不整形 JSON 可）を渡し (verdict, 出力全文) を返す。"""
    p = subprocess.run(["bash", os.path.join(ROOT, "hooks", hook)],
                       input=raw_payload.encode(), capture_output=True, cwd=ROOT)
    out = p.stdout.decode("utf-8", "replace")
    return _verdict(out), out


def _run_in_repo(hook, cmd, files=None, staged=None):
    """一時 git repo で hook を実行。files={name:content} 作成、staged=[names] を git add 済みに。"""
    d = tempfile.mkdtemp()
    try:
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
        subprocess.run(["git", "init", "-q"], cwd=d, env=env)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=d, env=env)
        subprocess.run(["git", "config", "user.name", "t"], cwd=d, env=env)
        for name, content in (files or {}).items():
            with open(os.path.join(d, name), "w") as f:
                f.write(content)
        for name in (staged or []):
            subprocess.run(["git", "add", name], cwd=d, env=env)
        p = subprocess.run(["bash", os.path.join(ROOT, "hooks", hook)],
                           input=json.dumps({"tool_input": {"command": cmd}}).encode(),
                           capture_output=True, cwd=d, env=env)
        out = p.stdout.decode("utf-8", "replace")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return _verdict(out)


ENV_FILE = {".env": "SECRET=x\n"}

# === D 系: check-destructive.sh の case-fold ===

# --- D-1/D-2: 平文大文字 RM -rf（case-insensitive FS では実 rm）→ ASK ---
def test_d1_uppercase_rm_recursive_asks():
    assert _run("check-destructive.sh", "RM -rf /tmp/x") == "ask"


def test_d2_uppercase_rm_uppercase_flag_asks():
    assert _run("check-destructive.sh", "RM -RF /tmp/x") == "ask"


# --- D-3: システムパスへの redirect の大文字パス変種 → ASK ---
def test_d3_redirect_uppercase_etc_asks():
    assert _run("check-destructive.sh", "echo x > /ETC/passwd") == "ask"


# --- D-4: CMD_REGEX 生経路の大文字コマンド（git / chmod 代表2種）→ ASK ---
def test_d4a_uppercase_git_reset_hard_asks():
    assert _run("check-destructive.sh", "GIT RESET --HARD") == "ask"


def test_d4b_uppercase_chmod_recursive_asks():
    assert _run("check-destructive.sh", "CHMOD -R 777 /tmp/x") == "ask"


# --- D-5 対照: 小文字の safe-artifact 削除は従来どおり allow（case-fold が
#     safe-targets 例外を壊さないことの回帰 pin）---
def test_d5_lowercase_rm_safe_artifact_still_allows():
    assert _run("check-destructive.sh", "rm -rf node_modules") == "allow"


# --- D-6: 大文字 RM は safe-artifact 対象でも ASK（sed の rm strip が RM に効かず
#     SAFE_TARGETS 例外に入らない・大文字化という難読化自体が確認対象）---
def test_d6_uppercase_rm_safe_artifact_asks():
    assert _run("check-destructive.sh", "RM -rf node_modules") == "ask"


# --- D-6b (grill-code 追加): 混在ケース。全大文字 pin（D-1）では「-i を RM|rm の
#     手動 alternation に置換する」treadmill 型 mutant を検知できない（D-1 は緑のまま
#     混在ケースだけ silent allow に戻る）。-i の case-insensitive 性そのものを固定する。---
def test_d6b_mixed_case_rm_recursive_asks():
    assert _run("check-destructive.sh", "Rm -rF /tmp/x") == "ask"


# --- D-7: fallback 経路（CMD 抽出不能）の case-fold ---
# 誘発方法: 閉じクォート欠落の truncated JSON。grep fast-path は閉じ `"` 必須で
# 不一致、python3 は json.loads 失敗 → CMD 空 → :60 fallback へ。
_TRUNC_LOWER = '{"tool_input":{"command":"rm -rf /tmp/x'
_TRUNC_UPPER = '{"tool_input":{"command":"RM -rf /tmp/x'


def test_d7_control_fallback_reachable_lowercase_asks():
    """fixture 実証（緑対照）: truncated JSON で fallback 経路に到達し、小文字 rm は
    fallback の「解析に失敗」ask が出る。この対照が D-7 本 pin の経路到達を保証する。"""
    v, out = _run_raw("check-destructive.sh", _TRUNC_LOWER)
    assert v == "ask"
    assert "解析に失敗" in out


def test_d7_fallback_uppercase_rm_asks():
    """本 pin: 同じ truncated 形で大文字 RM のみ silent allow になってはならない。"""
    v, _ = _run_raw("check-destructive.sh", _TRUNC_UPPER)
    assert v == "ask"


# --- D-7b (review テスト強度 mutation (d) 検知者不在の封鎖): fallback の
#     CMD_REGEX ループ（:67-68）の -i を pin する。D-7 は rm 特例 grep（:71）しか
#     踏まないため、:68 の -i 除去 mutant は D-7b なしでは 18/18 green のまま通る
#     （mutation 実走で検知者不在を実証・2026-07-26）。---
_TRUNC_GIT_UPPER = '{"tool_input":{"command":"GIT RESET --HARD'


def test_d7b_fallback_uppercase_cmd_regex_family_asks():
    v, _ = _run_raw("check-destructive.sh", _TRUNC_GIT_UPPER)
    assert v == "ask"


# === S 系: check-secrets.sh の stage alias / case-fold ===
# broad-stage 検出は repo 走査で secret の実在を確認して初めて deny になるため、
# 実 .env 入り tmp repo を CWD にして起動する。

# --- S-1/S-2: `git stage` は `git add` の完全 alias — broad staging は deny ---
def test_s1_git_stage_dash_A_with_real_env_denies():
    assert _run_in_repo("check-secrets.sh", "git stage -A", files=ENV_FILE) == "deny"


def test_s2_git_stage_dot_with_real_env_denies():
    assert _run_in_repo("check-secrets.sh", "git stage .", files=ENV_FILE) == "deny"


# --- S-3: 難読化形の stage alias broad staging（NORM 経路）→ ASK ---
def test_s3_ifs_git_stage_dash_A_with_real_env_asks():
    assert _run_in_repo("check-secrets.sh", "git${IFS}stage -A", files=ENV_FILE) == "ask"


# --- S-4 対照: stage を前方一致で誤爆しない（stagearea は alias ではない）---
def test_s4_git_stagearea_not_falsely_blocked():
    assert _run_in_repo("check-secrets.sh", "git stagearea xyz", files=ENV_FILE) == "allow"


# --- S-5: 大文字 GIT STAGE -A（case-insensitive FS では実 git）→ deny ---
def test_s5_uppercase_git_stage_dash_A_with_real_env_denies():
    assert _run_in_repo("check-secrets.sh", "GIT STAGE -A", files=ENV_FILE) == "deny"


# --- S-5b (grill-code 追加): 大文字×難読化の合成。CMD_LC（case fold）と NORM_LC
#     （${IFS} 畳み込み後 fold）の二重経路が同時に機能することを固定する。---
def test_s5b_uppercase_ifs_git_stage_dash_A_with_real_env_asks():
    assert _run_in_repo("check-secrets.sh", "GIT${IFS}STAGE -A", files=ENV_FILE) == "ask"


# --- S-6 対照: 生 `git add -A` の broad-stage deny は不変（回帰 pin）---
def test_s6_git_add_dash_A_with_real_env_still_denies():
    assert _run_in_repo("check-secrets.sh", "git add -A", files=ENV_FILE) == "deny"


# --- S-7 対照: 明示 `git stage .env` は従来から deny（S-3/v1.6.1 既対応・実 .env で実証）---
def test_s7_git_stage_explicit_env_still_denies():
    assert _run_in_repo("check-secrets.sh", "git stage .env", files=ENV_FILE) == "deny"
