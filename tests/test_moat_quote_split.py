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
