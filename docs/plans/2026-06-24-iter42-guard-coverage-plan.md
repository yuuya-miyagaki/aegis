# iter42 Guard Coverage (G1-G3) Implementation Plan

> TDD task-by-task. **commit 順序**: judge は working tree vs HEAD を diff するので per-task commit しない。実装+test を全部済ませ、Task V で gate→単一 commit（iter41 で確立）。framework_version は 1.14.0 据置。

**Goal:** 事故防止 guard の取りこぼし（G1 破壊パターン・G2 secrets git -C・G3 deploy/cron single-source）を埋める。

**参照設計:** `docs/specs/2026-06-24-iter42-guard-coverage-design.md`

**Tech Stack:** bash 3.2-safe / grep -E / python3 stdlib / pytest（subprocess で hook 実起動）

**作業前提:** task_type=framework（moat 解錠）。out-of-scope: git-push-deploy / var-indirection / generic truncate / I3。

---

## Task G1: 破壊コマンドパターンを patterns.sh に追加

**Files:**
- Modify: `hooks/lib/patterns.sh`（`AEGIS_DESTRUCTIVE_CMD_REGEX` + `AEGIS_DESTRUCTIVE_CMD_WARN`）
- Test: `tests/test_check_destructive_coverage.py`（新規）

- [ ] **Step 1: failing test**

```python
# tests/test_check_destructive_coverage.py
import json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-destructive.sh"

def _run(cmd):
    payload = json.dumps({"tool_input": {"command": cmd}})
    return subprocess.run(["bash", str(HOOK)], input=payload,
                          capture_output=True, text=True).stdout

def test_dangerous_commands_ask():
    for cmd in (
        "dd if=/dev/zero of=/dev/sda",
        "chmod -R 777 /",
        "chmod -Rf 777 /srv",         # combined flag (R then f)
        "chmod -fR 777 /srv",         # combined flag (f then R)
        "mkfs.ext4 /dev/sdb1",
        "shred -u secret.txt",
        "echo x > /etc/hosts",
    ):
        out = _run(cmd)
        assert '"permissionDecision":"ask"' in out, f"should ask: {cmd} -> {out}"

def test_benign_commands_allow():
    for cmd in (
        "echo hello",
        "chmod 644 file.txt",
        "chmod -v u+x run.sh",        # no recursive flag
        "echo x >> app.log",          # append, not truncate
        "make build >/dev/null 2>&1", # /dev/null redirect must NOT trip truncate
        "cat /etc/hosts",             # read, not truncate
    ):
        out = _run(cmd)
        assert out.strip() == "{}", f"should allow: {cmd} -> {out}"

```

- [ ] **Step 2: run → FAIL** (`python3 -m pytest tests/test_check_destructive_coverage.py -q`): dangerous cmds currently allow.

- [ ] **Step 3: implement** — `hooks/lib/patterns.sh`、`AEGIS_DESTRUCTIVE_CMD_REGEX` 配列末尾（`'find\s+.+\s+-delete'` の後）に追加し、`AEGIS_DESTRUCTIVE_CMD_WARN` に**同順**で対応 WARN を追加:

```bash
  'find\s+.+\s+-delete'
  '(^|[^[:alnum:]_])dd\s+.*\bof='
  '(^|[^[:alnum:]_])chmod\s+(-[a-zA-Z]*R[a-zA-Z]*\b|--recursive\b)'
  '(^|[^[:alnum:]_])mkfs(\.|[[:space:]]|$)'
  '(^|[^[:alnum:]_])shred([[:space:]]|$)'
  '(^|[^>])>\s*/(etc|usr|bin|sbin|boot|sys|lib)(/|[[:space:]]|$)'
)
```

> grill 致命修正: (1) truncate 一覧から `dev` を除外（`>/dev/null` 誤検知回避・生デバイス truncate は dd of= で概ね捕捉）。(2) chmod は `R` を含む dash-cluster（`-R`/`-fR`/`-Rf`）または `--recursive` を捕捉し `chmod 644`/`chmod -v` を非該当に。

WARN（同順・末尾）:

```bash
  "Destructive: find -delete bulk-deletes matching files."
  "Destructive: dd writes directly to a device/file (overwrites raw blocks)."
  "Destructive: recursive chmod (-R) changes permissions across a whole tree."
  "Destructive: mkfs formats a filesystem (destroys all data on it)."
  "Destructive: shred securely wipes files (unrecoverable)."
  "Destructive: redirect truncates a system path."
)
```

> chmod 正規表現は `chmod -R` / `chmod -fR` / `chmod -Rf` を捕捉し `chmod 644` を捕捉しないこと。truncate は単一 `>` のみ（`>>` append と `2>` を非該当に）。実装後に test の benign 群（`chmod 644`, `>> log`）で固定。実装時に regex を実測調整。

- [ ] **Step 4: run → PASS**（新規 test ＋ 既存 check-destructive 関連テスト）。

- [ ] **Step 5: commit しない**（Task V）。

---

## Task G3: deploy/destructive を patterns.sh に single-source 化

**Files:**
- Modify: `hooks/lib/patterns.sh`（`AEGIS_DEPLOY_REGEX` 追加）
- Modify: `hooks/check-deploy-gate.sh`（DEPLOY_RE → patterns.sh 参照・挙動保存）
- Modify: `hooks/check-cron-gate.sh`（inline DANGER_RE → patterns.sh import）
- Test: `tests/test_gate_pattern_single_source.py`（新規）

- [ ] **Step 1: failing tests**

```python
# tests/test_gate_pattern_single_source.py
import json, pathlib, subprocess, tempfile, os
ROOT = pathlib.Path(__file__).resolve().parents[1]

def _run(hook, payload, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(["bash", str(ROOT / "hooks" / hook)],
                          input=json.dumps(payload), capture_output=True, text=True, env=e).stdout

def test_patterns_defines_deploy_regex():
    assert "AEGIS_DEPLOY_REGEX" in (ROOT / "hooks/lib/patterns.sh").read_text()

def test_deploy_gate_still_asks_or_denies_on_vercel(tmp_path):
    # minimal STATUS so deploy-gate engages (deploy not approved -> deny/ask)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "STATUS.md").write_text(
        "---\nmode: Dev\nphase: deploy\ntask_type: feature\ntask_size: L\n"
        "gate_approvals:\n  deploy: pending\n---\n")
    out = _run("check-deploy-gate.sh", {"tool_input": {"command": "vercel deploy --prod"}},
               env={"AEGIS_ROOT_OVERRIDE": str(tmp_path)})
    assert '"permissionDecision"' in out  # engaged (deny or ask), not bare allow {}

def test_deploy_gate_allows_readonly(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "STATUS.md").write_text(
        "---\nmode: Dev\nphase: deploy\ntask_type: feature\ntask_size: L\n"
        "gate_approvals:\n  deploy: pending\n---\n")
    out = _run("check-deploy-gate.sh", {"tool_input": {"command": "rg deploy src/"}},
               env={"AEGIS_ROOT_OVERRIDE": str(tmp_path)})
    assert out.strip() == "{}"

def test_cron_gate_asks_on_new_destructive():
    # G1 pattern (chmod -R) must propagate to cron after single-source
    out = _run("check-cron-gate.sh", {"tool_input": {"prompt": "nightly: chmod -R 777 /srv"}})
    assert '"permissionDecision":"ask"' in out

def test_cron_gate_allows_benign():
    out = _run("check-cron-gate.sh", {"tool_input": {"prompt": "nightly: echo healthcheck"}})
    assert out.strip() == "{}"
```

- [ ] **Step 2: run → FAIL** (AEGIS_DEPLOY_REGEX absent; cron doesn't catch chmod -R).

- [ ] **Step 3a: patterns.sh** — `AEGIS_DESTRUCTIVE_*` ブロックの後に、check-deploy-gate.sh:62 の DEPLOY_RE を**逐語**移設:

```bash
# Deploy-command detection (single source for check-deploy-gate + check-cron-gate).
AEGIS_DEPLOY_REGEX='(^|[[:space:];&|])(vercel +deploy|vercel( +--[A-Za-z][A-Za-z0-9-]*(=[^[:space:];&|]*)?)*[[:space:]]*($|[;&|>])|firebase +deploy|netlify +deploy|(npm|pnpm|yarn|bun) +(run +)?deploy|flyctl +deploy|railway +deploy|gcloud +app +deploy|wrangler +(deploy|publish))'
```

- [ ] **Step 3b: check-deploy-gate.sh** — `aegis_require_lib "${SCRIPT_DIR}/lib/patterns.sh"` を lib ロード群に追加し、inline `DEPLOY_RE='...'` 定義を削除、`grep -qEi "$DEPLOY_RE"` を `grep -qEi "$AEGIS_DEPLOY_REGEX"` に変更。

- [ ] **Step 3c: check-cron-gate.sh** — `aegis_require_lib "${SCRIPT_DIR}/lib/patterns.sh"` を追加（emit.sh の後）。inline `DANGER_RE='...'` ブロックを削除し、判定を:

```bash
PROMPT_LOWER=$(printf '%s' "$PROMPT" | tr '[:upper:]' '[:lower:]')
_danger=""
# deploy
printf '%s' "$PROMPT" | grep -qEi "$AEGIS_DEPLOY_REGEX" 2>/dev/null && _danger=1
# destructive (lower-cased: SQL)
if [ -z "$_danger" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_LOWER_REGEX[@]}"; do
    printf '%s' "$PROMPT_LOWER" | grep -qE "${AEGIS_DESTRUCTIVE_LOWER_REGEX[$i]}" 2>/dev/null && { _danger=1; break; }
  done
fi
# destructive (raw: git/dd/chmod -R/...) + rm -r
if [ -z "$_danger" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_CMD_REGEX[@]}"; do
    printf '%s' "$PROMPT" | grep -qE "${AEGIS_DESTRUCTIVE_CMD_REGEX[$i]}" 2>/dev/null && { _danger=1; break; }
  done
fi
if [ -z "$_danger" ]; then
  printf '%s' "$PROMPT" | grep -qE 'rm\s+(-[a-zA-Z]*[rR]|--recursive)' 2>/dev/null && _danger=1
fi
if [ -n "$_danger" ]; then
  PREVIEW=$(printf '%s' "$PROMPT" | head -c 200 | tr '\000-\037\177' ' ')
  REASON=$(printf '[cron-gate] スケジュール対象 prompt にデプロイ/破壊的コマンドが含まれています。承認の前に内容を確認してください。preview: %s' "$PREVIEW")
  emit_ask "$REASON"
  exit 0
fi
emit_allow
exit 0
```

> 注: cron-gate は emit.sh のみ source していたので patterns.sh 追加が必要。patterns.sh は配列定義のみ（副作用なし）。

- [ ] **Step 4: run → PASS**（新規 test ＋ 既存 deploy/cron テスト＋`bash -n`）。挙動保存確認: 既存の deploy-gate/cron-gate テストが緑のまま。

- [ ] **Step 5: commit しない**（Task V）。

---

## Task G2: check-secrets が git -C/--git-dir を尊重

**Files:**
- Modify: `hooks/check-secrets.sh`（commit 検査の git diff --cached）
- Test: `tests/test_check_secrets_git_dir.py`（新規）

- [ ] **Step 1: failing test**

```python
# tests/test_check_secrets_git_dir.py
import json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "check-secrets.sh"

def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)

def _run(cmd, cwd):
    return subprocess.run(["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}),
                          capture_output=True, text=True, cwd=str(cwd)).stdout

def test_git_C_commit_with_staged_env_is_denied(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir()
    _git(repo, "init"); _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
    (repo / ".env").write_text("SECRET=x\n")
    _git(repo, "add", "--", ".env")  # staged (hook not firing on this test add)
    # Hook CWD is tmp_path (NOT repo); command targets repo via -C.
    out = _run(f"git -C {repo} commit -m x", cwd=tmp_path)
    assert '"permissionDecision":"deny"' in out, out

def test_plain_commit_in_cwd_still_denied(tmp_path):
    repo = tmp_path / "repo2"; repo.mkdir()
    _git(repo, "init"); _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
    (repo / ".env").write_text("SECRET=x\n")
    _git(repo, "add", "--", ".env")
    out = _run("git commit -m x", cwd=repo)  # CWD == repo (current behavior)
    assert '"permissionDecision":"deny"' in out, out
```

- [ ] **Step 2: run → FAIL** (git -C case: hook scans CWD, finds nothing → allow).

- [ ] **Step 3: implement** — `check-secrets.sh`、commit 検査ブロック（`if printf '%s' "$CMD" | grep -qE "git[[:space:]]+${GIT_PRE_OPTS}commit"` 内）の手前で git ディレクトリ引数を抽出:

```bash
# G2 (iter42): honor -C <path> / --git-dir=<path> so `git -C repo commit` scans
# the TARGET repo's staged diff, not the hook CWD (which scanned nothing).
# grill 致命: git options precede the subcommand, so scope extraction to the
# pre-`commit` prefix — otherwise a `-C` inside the commit message (git -C r
# commit -m "fix -C") is grabbed by the greedy match.
_aegis_git_dir_args() {
  local cmd="${1%% commit*}"  # part before the ` commit` SUBCOMMAND (space-delimited;
                              # a bare "commit" could be a substring of the -C path)
  local path=""
  # --git-dir=PATH
  path=$(printf '%s' "$cmd" | sed -nE 's/.*--git-dir=([^[:space:]]+).*/\1/p' | head -1)
  if [ -n "$path" ]; then printf -- '--git-dir\n%s\n' "$path"; return; fi
  # -C PATH  (first occurrence in the option prefix)
  path=$(printf '%s' "$cmd" | sed -nE 's/.*[[:space:]]-C[[:space:]]+([^[:space:]]+).*/\1/p' | head -1)
  if [ -n "$path" ]; then printf -- '-C\n%s\n' "$path"; fi
}
```

そして commit 検査内の 2 つの `git diff --cached --name-only` を:

```bash
GIT_DIR_ARGS=()
while IFS= read -r _a; do [ -n "$_a" ] && GIT_DIR_ARGS+=("$_a"); done < <(_aegis_git_dir_args "$CMD")
... git "${GIT_DIR_ARGS[@]+"${GIT_DIR_ARGS[@]}"}" diff --cached --name-only ...
```

（bash 3.2 安全: 空配列展開は `${arr[@]+"${arr[@]}"}`。抽出失敗時は空＝CWD で実行＝現挙動。）

- [ ] **Step 4: run → PASS**（新規 test ＋ 既存 check-secrets テスト）。

- [ ] **Step 5: commit しない**（Task V）。

---

## Task V: 全体検証 + gate + 単一 commit（version 1.14.0 据置）

**実装順:** G1 → G3 → G2（G3 は G1 の patterns に依存）。全て実装+test まで（commit しない）。

- [ ] **Step 1: grill-code**（diff 全体・全指摘を潰す）。
- [ ] **Step 2:** `python3 -m pytest -q`（既存 + 新規 green）／`check_framework_contract.py`（full PASS・1.14.0）／`status_doctor.py` PASS／`bash -n hooks/lib/patterns.sh hooks/check-destructive.sh hooks/check-deploy-gate.sh hooks/check-cron-gate.sh hooks/check-secrets.sh`。
- [ ] **Step 3:** standard 配布の擬似検証（一時 target に setup → contract --profile=standard PASS）。
- [ ] **Step 4: record-test-result**（全コード編集後に1回・green bind）。LEARNINGS 更新。
- [ ] **Step 5: gate**（working tree 未 commit）: review→qa→security→deploy→ship。盲検2次（reviewer + security）。current_refs は承認直前設定・gate コマンドは tail（head 禁止）。qa は guard hook の挙動テストがあるので drill 可否を判断（混在 diff なら skip-drill + RED-first TDD）。
- [ ] **Step 6: 単一 commit + push**（push は yuuya-miyagaki）。STATUS next_action を iter43 アンカー（I3 authorized-path 設計）に更新。

---

## Self-Review

- **Spec coverage:** G1（patterns）/G2（secrets git -C）/G3（deploy single-source + cron import）各々 Task。out-of-scope 明記。✓
- **Placeholder scan:** 全 step に実コード。regex の最終調整は実装時 test 固定と明記（chmod/truncate の境界）。
- **Type consistency:** `AEGIS_DEPLOY_REGEX`・`AEGIS_DESTRUCTIVE_CMD_REGEX`・`_aegis_git_dir_args`・`GIT_DIR_ARGS` を全 task で一貫。
- **未確定（grill-plan で詰める）:** (a) chmod/truncate regex の誤検知境界（`>>`/`2>`/`chmod 644`）。(b) DEPLOY_RE 逐語移設の byte 等価。(c) cron-gate の patterns.sh import が他の発火経路（python3 不在 fail-closed）を壊さないか。
