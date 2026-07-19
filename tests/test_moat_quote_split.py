import json, subprocess, os
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
    assert _run("check-destructive.sh", 'rm -rf "$DIR"') == "ask"

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
