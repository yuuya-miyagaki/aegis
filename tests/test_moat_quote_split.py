import json, subprocess, os, tempfile, shutil
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _run(hook, cmd):
    p = subprocess.run(["bash", os.path.join(ROOT, "hooks", hook)],
                       input=json.dumps({"tool_input": {"command": cmd}}).encode(),
                       capture_output=True, cwd=ROOT)
    out = p.stdout.decode("utf-8", "replace")
    if out.strip() == "{}":
        return "allow"
    if '"permissionDecision":"deny"' in out or '"permissionDecision": "deny"' in out:
        return "deny"
    if '"permissionDecision":"ask"' in out or '"permissionDecision": "ask"' in out:
        return "ask"
    return "other:" + out.strip()[:40]

def _run_msg(hook, cmd):
    """hook の JSON 出力から reason 文字列を返す（無ければ ''）。"""
    p = subprocess.run(["bash", os.path.join(ROOT, "hooks", hook)],
                       input=json.dumps({"tool_input": {"command": cmd}}).encode(),
                       capture_output=True, cwd=ROOT)
    out = p.stdout.decode("utf-8", "replace").strip()
    if not out or out == "{}":
        return ""
    try:
        obj = json.loads(out)
    except Exception:
        return out
    # hookSpecificOutput.permissionDecisionReason を優先、なければ全体を文字列化
    hso = obj.get("hookSpecificOutput", {})
    return hso.get("permissionDecisionReason", "") or json.dumps(obj, ensure_ascii=False)

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
    if out.strip() == "{}":
        return "allow"
    if '"permissionDecision":"deny"' in out or '"permissionDecision": "deny"' in out:
        return "deny"
    if '"permissionDecision":"ask"' in out or '"permissionDecision": "ask"' in out:
        return "ask"
    return "other:" + out.strip()[:60]

# --- destructive: 空クォート/バックスラッシュ/${IFS} 分割は ASK になるべき ---
def test_destructive_empty_quote_split_asks():
    assert _run("check-destructive.sh", 'r""m -rf /tmp/aegis-victim') == "ask"

def test_destructive_backslash_split_asks():
    assert _run("check-destructive.sh", 'r\\m -rf /tmp/aegis-victim') == "ask"

def test_destructive_ifs_split_asks():
    assert _run("check-destructive.sh", 'rm${IFS}-rf /tmp/aegis-victim') == "ask"

# --- secrets: 難読化した git add .env は ASK になるべき（生形は DENY 維持）---
def test_secrets_empty_quote_split_asks():
    assert _run("check-secrets.sh", 'g""it a""dd .e""nv') == "ask"

def test_secrets_dotenv_split_asks():
    assert _run("check-secrets.sh", 'git add .e""nv') == "ask"

def test_secrets_ifs_split_asks():
    assert _run("check-secrets.sh", 'git${IFS}add .env') == "ask"

# --- 平文は従来評決を維持 ---
def test_plain_rm_rf_still_asks():
    assert _run("check-destructive.sh", 'rm -rf /tmp/x') == "ask"
def test_plain_git_add_env_still_denies():
    assert _run("check-secrets.sh", 'git add .env') == "deny"

# --- 変数展開クォート（生で一致）は従来経路のまま（誤 ASK 二重化しない）---
def test_rm_rf_quoted_var_asks_via_raw():
    # 生経路一致（rm -rf が生で再帰削除 regex にマッチ）。正規化経路の
    # 「難読化された」プレフィクスが付かないことで生経路を通ったことを pin。
    # 評決 ask だけでは正規化経路へフォールスルーしても flip しない（mutant で実証）ため
    # メッセージ本文でも生経路を検証する。
    assert _run("check-destructive.sh", 'rm -rf "$DIR"') == "ask"
    assert "難読化された" not in _run_msg("check-destructive.sh", 'rm -rf "$DIR"')

# --- 対照: 難読化形は「難読化された」プレフィクスを含む（pin を両側から締める）---
def test_obfuscated_rm_has_obfuscation_prefix():
    assert "難読化された" in _run_msg("check-destructive.sh", 'r""m -rf /tmp/x')

# --- 安全形の難読化は allow（.env.example は除外維持）---
def test_obfuscated_safe_env_allows():
    assert _run("check-secrets.sh", 'g""it a""dd .e""nv.example') == "allow"

# --- 正常なクォート使用を誤爆しない ---
def test_normal_quoted_commit_msg_not_denied():
    # コミットメッセージに STATUS.md を含んでも secrets は無関係→allow
    assert _run("check-secrets.sh", 'git commit -m "fix STATUS.md handling"') == "allow"
def test_normal_quoted_path_not_falsely_asked():
    assert _run("check-destructive.sh", 'cp "my file.txt" dest/') == "allow"

# --- 残余（SF-019・iter75 では未対応＝現状 allow を明示 pin）---
# brace/param-default/cmdsub は静的文字列畳み込みでは塞げない（構造化 argv 待ち）。
# 現状 allow を固定し、将来対応時にこの pin が flip して revisit を強制する。
def test_residual_brace_split_still_allows_SF019():
    assert _run("check-destructive.sh", 'r{,}m -rf /tmp/x') == "allow"
def test_residual_secrets_brace_split_still_allows_SF019():
    assert _run("check-secrets.sh", 'g{,}it add .env') == "allow"

# === fix-forward RED（iter75 review reject 対応）===

# --- F1: broad-stage/commit 難読化（実 .env が repo 存在/staged のとき ASK）---
ENV_FILE = {".env": "SECRET=x\n"}

def test_ff_broad_stage_ifs_split_asks():
    assert _run_in_repo("check-secrets.sh", 'git${IFS}add -A', files=ENV_FILE) == "ask"

def test_ff_broad_stage_quote_split_asks():
    assert _run_in_repo("check-secrets.sh", 'g""it a""dd -A', files=ENV_FILE) == "ask"

def test_ff_commit_ifs_split_asks():
    assert _run_in_repo("check-secrets.sh", 'git${IFS}commit', files=ENV_FILE, staged=[".env"]) == "ask"

# --- F1 対照（生形は従来 deny）---
def test_ff_broad_stage_raw_still_denies():
    assert _run_in_repo("check-secrets.sh", 'git add -A', files=ENV_FILE) == "deny"

# --- F1 誤検知回帰 pin（.env 非staged の正当 commit は allow）---
def test_ff_commit_quoted_msg_not_falsely_asked():
    assert _run_in_repo("check-secrets.sh", 'git commit -m "fix bug"', files=ENV_FILE) == "allow"

# --- F1 .env 不在 repo では難読化 broad も allow（スキャン空）---
def test_ff_broad_stage_no_env_allows():
    assert _run_in_repo("check-secrets.sh", 'git${IFS}add -A', files={"README.md": "x"}) == "allow"

# --- F2: backslash-newline 行継続（明示 .env / destructive ゆえ既存 _run で可）---
def test_ff_backslash_newline_staging_asks():
    assert _run("check-secrets.sh", 'git add \\\n.env') == "ask"

def test_ff_backslash_newline_rm_asks():
    assert _run("check-destructive.sh", 'rm \\\n-rf /tmp/x') == "ask"

# --- F3: 難読化大文字（destructive）---
def test_ff_uppercase_quote_split_asks():
    assert _run("check-destructive.sh", 'R""M -RF /tmp/x') == "ask"

def test_ff_uppercase_ifs_split_asks():
    assert _run("check-destructive.sh", 'RM${IFS}-rf /tmp/x') == "ask"

# --- FF7: 非rm 大文字難読化が CMD_REGEX ループ（:161）で ASK になるべき ---
# review 再走で盲検2次＋reviewer-testing が摘発: :161 の CMD_REGEX ループは $NORM
# （大文字のまま）で照合しており、chmod/find/dd/shred/mkfs/git 系の大文字難読化が
# ASK を silent 回避していた。正規化経路の全 grep を grep -i on NORM に統一して封鎖。
# NORM_LOWER 化では chmod の -R リテラル（regex 内 R）が壊れ捕捉不可のため grep -i を採用。
@pytest.mark.parametrize("cmd", [
    'C""HMOD -R 777 /tmp/x',
    'CHMOD${IFS}-R 777 /tmp/x',
    'F""IND /tmp/x -delete',
    'FIND${IFS}/tmp/x -delete',
    'D""D if=/dev/zero of=/tmp/x',
    'S""HRED /tmp/x',
    'M""KFS.EXT4 /dev/x',
    'G""IT BRANCH -D foo',
    'GIT${IFS}RESET --HARD',
    'GIT${IFS}PUSH origin main --FORCE',
    # FF8（review-testing F1 補強）: CMD_REGEX の残りカテゴリも大文字難読化で pin。
    # 実装は grep -i ループで配列全体に効く（共通コードパス）ため即 GREEN の回帰 pin。
    'GIT${IFS}FILTER-BRANCH --all',
    'G""IT UPDATE-REF -D refs/heads/x',
    'GIT${IFS}REFLOG EXPIRE --EXPIRE=NOW --ALL',
    'G""IT STASH DROP',
    'GIT${IFS}CLEAN -FD',
    'NPX${IFS}RIMRAF /tmp/x',
    'echo x >${IFS}/ETC/passwd',
])
def test_ff_uppercase_nonrm_destructive_asks(cmd):
    assert _run("check-destructive.sh", cmd) == "ask"

# F-2（reviewer-testing 指摘）: 語中継続の統合層 pin（backslash-newline 行の検知力）
def test_ff_backslash_newline_midword_rm_asks():
    # gi<改行>t でなく r<改行>m -rf（rm の語中継続）→ 実行時 rm -rf
    assert _run("check-destructive.sh", 'r\\\nm -rf /tmp/x') == "ask"

# === FF9（iter75 security reject 対応・道A）===
# security 1次(opus)/盲検2次(fable) の2実バグ。bash（実行シェル）で runtime 実証:
#   - IFS-family（$IFS/${IFS}/${IFS:0:1}/${IFS: -1}/${IFS/x/y}/${IFS#} 等）は
#     unquoted 展開ゆえ IFS 値（空白）で word-split → 実 rm -rf / git add .env。
#   - `rm -rf${IFS}/x` は SAFE_TARGETS early-exit（flag 密着 ${IFS} を単一 flag
#     トークン扱い）が NORM 再判定より前で swallow → silent 再帰削除。
# fix: (A) aegis_dequote_normalize に ${IFS...} family を非貪欲畳み込み（patterns.sh）。
#      (B) check-destructive の SAFE_TARGETS early-exit を NORM!=CMD（難読化実在）時 skip。

# --- SEC-1: IFS param-expansion family — destructive（obfuscated rm → ASK）---
@pytest.mark.parametrize("cmd", [
    'rm${IFS:0:1}-rf /tmp/x',
    'rm${IFS: -1}-rf /tmp/x',
    'rm${IFS/x/y}-rf /tmp/x',
    'rm${IFS#}-rf /tmp/x',
    'rm${IFS:-z}-rf /tmp/x',   # :- は IFS set/non-null ゆえ空白展開（実バイパス）
])
def test_ff9_ifs_family_destructive_asks(cmd):
    assert _run("check-destructive.sh", cmd) == "ask"

# --- SEC-1: IFS param-expansion family — secrets（obfuscated git add .env → ASK）---
@pytest.mark.parametrize("cmd", [
    'git${IFS:0:1}add .env',
    'git${IFS: -1}add .env',
    'git${IFS/x/y}add .env',
    'git${IFS#}add .env',
])
def test_ff9_ifs_family_secrets_asks(cmd):
    assert _run("check-secrets.sh", cmd) == "ask"

# --- SEC-1 chain: broad-stage / commit（repo に実 .env・IFS family）→ ASK ---
def test_ff9_ifs_family_broad_stage_asks():
    assert _run_in_repo("check-secrets.sh", 'git${IFS:0:1}add -A', files=ENV_FILE) == "ask"

def test_ff9_ifs_family_commit_asks():
    assert _run_in_repo("check-secrets.sh", 'git${IFS:0:1}commit', files=ENV_FILE, staged=[".env"]) == "ask"

# --- Finding 1: SAFE_TARGETS early-exit が flag 密着 ${IFS} を swallow → ASK にすべき ---
@pytest.mark.parametrize("cmd", [
    'rm -rf${IFS}/x',          # security Finding 1 の実証形（literal ${IFS}）
    'rm -rf${IFS:0:1}/x',      # 同 family の param-expansion 変種
])
def test_ff9_flag_adjacent_ifs_rm_asks(cmd):
    assert _run("check-destructive.sh", cmd) == "ask"

# --- Finding 1 非回帰: 難読化なしの安全形削除は従来どおり allow（early-exit skip は
#     NORM!=CMD のときのみ・平文 safe-artifact は NORM==CMD ゆえ影響しない）---
@pytest.mark.parametrize("cmd", [
    'rm -rf build',
    'rm -rf node_modules dist',
    'rm -rf ./dist',
])
def test_ff9_plain_safe_artifact_still_allows(cmd):
    assert _run("check-destructive.sh", cmd) == "allow"

# --- Finding 1 対照: 難読化された safe-artifact 削除は artifact-only とみなさず ASK ---
def test_ff9_obfuscated_safe_artifact_asks():
    # `rm -rf${IFS}build` は実行時 `rm -rf build`（safe）だが難読化自体が確認対象。
    assert _run("check-destructive.sh", 'rm -rf${IFS}build') == "ask"

# --- 残余（proven-non-exploitable・runtime 実証済み）: ANSI-C クォート $'\\x20' は
#     literal-in-word space ゆえ word-split せず → `rm -rf`（空白入り単一語）= command
#     not found（実行不能）。畳まない設計を pin（現状 allow 固定・将来 flip で revisit）。
#     bash 実証: `rm$'\\x20'-rf /tmp/x` → "command not found: rm -rf"。---
@pytest.mark.parametrize("cmd", [
    "rm$'\\x20'-rf /tmp/x",
    "rm$'\\t'-rf /tmp/x",
])
def test_ff9_residual_ansic_quote_nonexploitable_allows(cmd):
    assert _run("check-destructive.sh", cmd) == "allow"

# --- grill-code G9: 多数 ${IFS} でも正しく ASK（no-cap / no-MISS の scale pin）。
#     畳み込みは単一 sed で O(n)（bash の ${c//…} 全置換や1個ずつ loop は多数一致で
#     O(n²)＝秒オーダー→hook timeout=fail-open）。将来 cap を入れて多数時に silent
#     allow へ後退したらこの pin が flip して revisit を強制する。---
def test_ff9_many_ifs_scale_still_asks():
    assert _run("check-destructive.sh", "rm" + "${IFS}" * 1000 + "-rf /tmp/x") == "ask"

# --- 残余（構造化 argv・SF-019）: iter75 security 再走で 1次(opus)/盲検2次(fable) が
#     摘発した「静的文字列正規化では健全に塞げない」クラス。道C で SF-017 の主張を
#     「非空 ${IFS} 展開＋Finding 1」に正確化し、以下は SF-019（iter77 構造化 argv 待ち）
#     の accepted residual として現状 allow を pin する。将来の argv 判定で flip→revisit。
#     全て意図的難読化を要し事故経路で発生しない（脅威モデル外）。
#
#   F-SEC-B: ゼロ幅 IFS 展開（${IFS:0:0} 等）は runtime で空展開＝隣接連結（glue）だが
#     sed は一律空白へ畳む＝過分割。mixed split/glue は fold-to-space/fold-to-empty の
#     どちらの純形でも非マッチ＝2ⁿ 展開列挙が必要（bash runtime で実削除を実証）。
@pytest.mark.parametrize("cmd", [
    'rm${IFS}-${IFS:0:0}rf${IFS}/tmp/x',   # 全区切りが IFS の mixed split/glue（純2形とも非マッチ）
    'rm -${IFS:0:0}rf${IFS}/tmp/x',        # literal space + glue-IFS + split-IFS
])
def test_ff9_residual_zerowidth_ifs_mixed_allows_SF019(cmd):
    assert _run("check-destructive.sh", cmd) == "allow"

#   F-SEC-C1: param-default ネスト（${Q:-${IFS}}）＝単一パス sed が inner } で早期終端。
def test_ff9_residual_param_default_ifs_allows_SF019():
    assert _run("check-destructive.sh", 'rm${Q:-${IFS}}-rf /tmp/x') == "allow"
    assert _run_in_repo("check-secrets.sh", 'git${Q:-${IFS}}add .env', files=ENV_FILE) == "allow"

#   F-SEC-C2: 変数間接（${!x}）＝${IFS...} リテラルでなく静的射程外。
def test_ff9_residual_indirect_ifs_allows_SF019():
    assert _run("check-destructive.sh", 'x=IFS; rm${!x}-rf /tmp/x') == "allow"
