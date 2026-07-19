# iter75 SF-017 MOAT-BYPASS 修正 実装計画

> **For agentic workers:** TDD 厳守（RED→GREEN）。各タスクは per-task commit。実装は opus dispatch（session=fable）。CP コード（check-runtime-state.sh・SF-001 資産）は**触らない**。設計正本＝`docs/specs/2026-07-20-iter75-moat-quote-split-design.md`。

**Goal:** `check-destructive.sh`／`check-secrets.sh` の空クォート トークン分割バイパス（`g""it a""dd .e""nv` → secret DENY が silent ALLOW）を、共有正規化 helper で閉じる。

**Architecture:** `patterns.sh` に純 bash の `aegis_dequote_normalize`（クォート/バックスラッシュ除去）を新設。両フックは既存の生 CMD 判定を保存したまま、生で miss かつ正規化形（`NORM != CMD`＝難読化実在）で一致した場合に **ASK** を追加発火。

**Tech Stack:** POSIX shell（bash 3.2 互換）、pytest（subprocess でフック実走）、grep（BSD/GNU 両対応・既存 `LC_ALL=C`）。

---

## File Structure
- `hooks/lib/patterns.sh` — `aegis_dequote_normalize` helper 追加（単一ソース）。
- `hooks/check-destructive.sh` — 既存 raw 判定の後に正規化 re-check（WARN セット）。
- `hooks/check-secrets.sh` — 既存 raw 判定の後に正規化 re-check（emit_ask）。
- `tests/test_moat_quote_split.py` — 新規（RED→回帰 pin）。
- `tests/test_patterns_parity.py` — 正規化 helper の parity/単体を追記。

---

### Task 1: RED — 現状バイパスを実証し、期待挙動を assert

**Files:**
- Create: `tests/test_moat_quote_split.py`

- [ ] **Step 1: 失敗テストを書く**

```python
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
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest tests/test_moat_quote_split.py -v`
Expected: **6 FAIL**（現状は全て `allow` が返る＝バイパス実証。grill_verify で実測済み）。

- [ ] **Step 3: commit（RED を証跡化）**

```bash
git add tests/test_moat_quote_split.py
git commit -F - <<'EOF'
test(iter75): RED — SF-017 quote-split バイパスを実証（現状 allow）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 2: 共有 helper `aegis_dequote_normalize` を patterns.sh に追加

**Files:**
- Modify: `hooks/lib/patterns.sh`（ファイル末尾付近・他の関数定義の近く）
- Test: `tests/test_patterns_parity.py`

- [ ] **Step 1: 単体テストを書く**

`tests/test_patterns_parity.py` に追記:

```python
def test_dequote_normalize():
    import subprocess, os
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    def norm(s):
        script = 'source hooks/lib/patterns.sh; printf %s "$(aegis_dequote_normalize "$1")"'
        return subprocess.run(["bash","-c",script,"_",s], cwd=ROOT,
                              capture_output=True, text=True).stdout
    assert norm('r""m -rf /x') == 'rm -rf /x'
    assert norm('g""it a""dd .e""nv') == 'git add .env'
    assert norm('r\\m -rf') == 'rm -rf'
    assert norm('rm${IFS}-rf /x') == 'rm -rf /x'          # ${IFS} → 空白（grill 致命1）
    assert norm('git${IFS}add .env') == 'git add .env'    # secret bypass 綴り
    assert norm('rm -rf /x') == 'rm -rf /x'               # 非難読化は不変
    # 残余（SF-019・iter75 では畳まない＝不変を pin）:
    assert norm('r{,}m -rf') == 'r{,}m -rf'               # brace 展開は非対応（構造化 argv 待ち）
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest tests/test_patterns_parity.py::test_dequote_normalize -v`
Expected: FAIL（`aegis_dequote_normalize: command not found`）。

- [ ] **Step 3: helper を実装**

`hooks/lib/patterns.sh` に追加:

```sh
# --- iter75 SF-017: quote/backslash/${IFS} 正規化（純 bash・parser なし） ---
# _obfuscated_unlock_on_cp（check-runtime-state.sh）と同一手法の拡張。呼び出し側は
# LC_ALL=C を export 済み前提。brace/param-default/cmdsub は解決しない（SF-019 残余・
# 構造化 argv 待ち）。
aegis_dequote_normalize() {
  local c=$1
  c=${c//\\/}              # バックスラッシュ除去
  c=${c//\"/}              # 二重クォート除去
  c=${c//\'/}              # 単一クォート除去
  c=${c//'${IFS}'/ }       # ${IFS} → 空白（grill 致命1: git${IFS}add .env を捕捉）
  c=${c//'$IFS'/ }         # $IFS  → 空白
  printf '%s' "$c"
}
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m pytest tests/test_patterns_parity.py::test_dequote_normalize -v`
Expected: PASS。

- [ ] **Step 5: commit**

```bash
git add hooks/lib/patterns.sh tests/test_patterns_parity.py
git commit -F - <<'EOF'
feat(iter75): patterns.sh に aegis_dequote_normalize を追加（共有正規化 helper）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 3: check-destructive.sh で正規化 re-check（destructive RED を GREEN 化）

**Files:**
- Modify: `hooks/check-destructive.sh:140` の直後（RAW pattern チェックの後・`if [ -n "$WARN" ]` の前）

- [ ] **Step 1: 実装を追加**

`hooks/check-destructive.sh` の line 140（RAW command patterns ループ終わり）と line 142（`if [ -n "$WARN" ]`）の間に挿入:

```sh
# iter75 SF-017: 生 CMD で miss したとき、quote/backslash 難読化を正規化して再判定。
# 正規化で command が変わった（難読化実在）かつ破壊パターンに一致 → ASK。
# 安全形除外（build artifact）は再適用しない（難読化自体が確認対象）。
if [ -z "$WARN" ]; then
  NORM=$(aegis_dequote_normalize "$CMD")
  if [ "$NORM" != "$CMD" ]; then
    NORM_LOWER=$(printf '%s' "$NORM" | tr '[:upper:]' '[:lower:]')
    if printf '%s' "$NORM" | grep -qE 'rm\s+(-[a-zA-Z]*[rR]|--recursive)' 2>/dev/null; then
      WARN="難読化された破壊的コマンド（連結クォート/バックスラッシュ）の可能性: 再帰削除。意図を確認してください。"
    fi
    if [ -z "$WARN" ]; then
      for i in "${!AEGIS_DESTRUCTIVE_LOWER_REGEX[@]}"; do
        if printf '%s' "$NORM_LOWER" | grep -qE "${AEGIS_DESTRUCTIVE_LOWER_REGEX[$i]}" 2>/dev/null; then
          WARN="難読化された破壊的コマンドの可能性: ${AEGIS_DESTRUCTIVE_LOWER_WARN[$i]}"; break
        fi
      done
    fi
    if [ -z "$WARN" ]; then
      for i in "${!AEGIS_DESTRUCTIVE_CMD_REGEX[@]}"; do
        if printf '%s' "$NORM" | grep -qE "${AEGIS_DESTRUCTIVE_CMD_REGEX[$i]}" 2>/dev/null; then
          WARN="難読化された破壊的コマンドの可能性: ${AEGIS_DESTRUCTIVE_CMD_WARN[$i]}"; break
        fi
      done
    fi
  fi
fi
```

- [ ] **Step 2: destructive RED が GREEN になるか確認**

Run: `python3 -m pytest tests/test_moat_quote_split.py -k destructive -v`
Expected: 2 PASS（`r""m`・`r\m` が ASK）。

- [ ] **Step 3: 平文の回帰を確認（誤変化なし）**

Run: `python3 -m pytest tests/test_check_destructive_coverage.py -v`
Expected: 全 PASS（平文 `rm -rf`=ASK・safe artifact=allow 不変）。

- [ ] **Step 4: commit**

```bash
git add hooks/check-destructive.sh
git commit -F - <<'EOF'
fix(iter75): check-destructive で quote-split 難読化を正規化 re-check→ASK（SF-017）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 4: check-secrets.sh — staging 検出を単一ソース化し正規化 re-check → ASK

> grill 致命2（regex 再掲 drift）＋致命3（挿入位置の到達性）を反映。

**Files:**
- Modify: `hooks/check-secrets.sh`（Check0 line 146・Check1 line 162 の inline regex を変数化＋末尾に正規化ブロック）

- [ ] **Step 1: staging 検出 regex を変数へ単一ソース化（挙動保存リファクタ）**

`CMD_LC=` 定義（line 143）の直後に、Check0/Check1 の regex を変数化:

```sh
# iter75 SF-017: staging 検出 regex を単一ソース化（raw deny と正規化 ask が同一検出器）。
_STAGE_HIGHRISK_RE="git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}([[:space:]]+(--[A-Za-z][-A-Za-z0-9]*[[:space:]]+)*)?.*(${AEGIS_HIGH_RISK_RE})"
_STAGE_ENV_RE="git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}([[:space:]]+(--[A-Za-z][-A-Za-z0-9]*[[:space:]]+)*)?.*\.env"
```

そして既存 Check0（line 146）を `grep -qE "$_STAGE_HIGHRISK_RE"` に、Check1（line 162）を `grep -qE "$_STAGE_ENV_RE"` に**置換**（regex 本体は不変＝挙動保存）。

- [ ] **Step 2: 置換が挙動保存であることを確認**

Run: `python3 -m pytest tests/test_secrets_pattern_consumer.py tests/test_secrets_broad_dot_token.py tests/test_secrets_quoted_var_and_cmdsub.py -v`
Expected: 全 PASS（平文 `git add .env`=DENY・`.env.example`=allow 不変）。

- [ ] **Step 3: 到達性を実測（難読化 staging が正規化ブロックまで届くか）**

Run:
```bash
printf '%s' '{"tool_input":{"command":"g\"\"it a\"\"dd .e\"\"nv"}}' | bash hooks/check-secrets.sh; echo " rc=$?"
```
Expected: 現状は `{}`（allow・まだ未実装）。**early allow に食われず末尾まで到達している**ことを、フックに一時 `>&2 echo REACHED` を挟むか、実装後に ASK になることで確認する（Step 5 で GREEN 化＝到達を含意）。

- [ ] **Step 4: 正規化 re-check を最終 `emit_allow` の直前に挿入**

（`SAFE_ENV_SUFFIXES`・上記変数は既にスコープ内。読み取り難読化 `c""at .e""nv` は staging regex（`git…add…`）に非一致ゆえ末尾配置でも誤爆しない。）

```sh
# iter75 SF-017: 生 CMD で全 deny を通過したとき、quote/backslash/${IFS} 難読化を
# 正規化し、同じ staging 検出器（単一ソース）を再適用。難読化実在かつ一致 → ASK
# （DENY でなく: command 位置非解釈ゆえ commit -m 内 .env 言及と区別不能・
# _obfuscated_unlock_on_cp 一貫）。
NORM=$(aegis_dequote_normalize "$CMD")
if [ "$NORM" != "$CMD" ]; then
  NORM_LC=$(printf '%s' "$NORM" | tr '[:upper:]' '[:lower:]')
  NORM_STRIPPED=$(printf '%s' "$NORM_LC" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")
  if printf '%s' "$NORM_LC" | grep -qE "$_STAGE_HIGHRISK_RE" 2>/dev/null \
     || printf '%s' "$NORM_STRIPPED" | grep -qE "$_STAGE_ENV_RE" 2>/dev/null; then
    emit_ask "[secrets] 難読化された形（連結クォート/バックスラッシュ/\${IFS}）で認証ファイル (.env / 鍵 / credentials 等) を git に staging しようとしている可能性があります。意図を確認してください。生の形（例: git add .env）は拒否されます。"
    exit 0
  fi
fi
```

- [ ] **Step 5: secrets RED が GREEN になるか確認**

Run: `python3 -m pytest tests/test_moat_quote_split.py -k secrets -v`
Expected: PASS（`g""it a""dd .e""nv`・`git add .e""nv`・`git${IFS}add .env` が ASK）。

- [ ] **Step 6: commit**

```bash
git add hooks/check-secrets.sh
git commit -F - <<'EOF'
fix(iter75): check-secrets staging 検出を単一ソース化＋正規化 re-check→ASK（SF-017）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 5: 回帰 pin（誤検知・誤 DENY を固定）

**Files:**
- Modify: `tests/test_moat_quote_split.py`

- [ ] **Step 1: 回帰テストを追記**

```python
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
```

- [ ] **Step 2: 全て GREEN を確認**

Run: `python3 -m pytest tests/test_moat_quote_split.py -v`
Expected: 全 PASS（RED 6 件＋回帰 6 件＋残余 pin 2 件）。

- [ ] **Step 3: commit**

```bash
git add tests/test_moat_quote_split.py
git commit -F - <<'EOF'
test(iter75): SF-017 回帰 pin（平文評決不変・安全形除外・正常クォート非誤爆）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 6: フルスイート green＋記録

- [ ] **Step 1: フルスイート実行**

Run: `python3 -m pytest -q 2>&1 | tail -5`
Expected: 全 PASS（既知 flaky `test_update_gate_lock` を除く）。既存件数から +10 前後増。

- [ ] **Step 2: contract/drift/status_doctor**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/status_doctor.py --root .`
Expected: 両 PASS。

- [ ] **Step 3: バイパス封鎖の最終実証（親再現の再走）**

Run:
```bash
printf '%s' '{"tool_input":{"command":"g\"\"it a\"\"dd .e\"\"nv"}}' | bash hooks/check-secrets.sh
```
Expected: `ask` 出力（旧は `{}`=allow）。

- [ ] **Step 4: docs 記録**

`docs/specs/2026-07-20-iter75-moat-quote-split-design.md` に「実装済み・commit 範囲」を追記。SF-017 状態を更新用にメモ（docs フェーズで security-followups.md を CLOSED-in-review 候補へ）。

---

### Task 7: SF-019 起票（残余＝brace/param/cmdsub の原理的天井）

**Files:**
- Modify: `docs/security-followups.md`（OPEN セクション・`## CLOSED` の直前）

- [ ] **Step 1: SF-019 を追記**

grill_verify で実証した残余を durable 記録:
- タイトル: `SF-019: check-destructive/secrets の brace/param-default/cmdsub トークン分割は文字列正規化で塞げない（残余・構造化 argv 待ち）`
- 種別: SF-017 と同クラス（静的 matcher がシェルのトークン化を再現しない）の**未畳み込み綴り**。iter75 は quote/BS/`${IFS}` を閉じたが、`{r,x}m`/`r{,}m`・`${x:-rm}`・`$(...)`/backtick は残存。
- 重大度: **Medium（残余・記録のみ）**。理由: brace は実行時に重複トークン（`rm rm -rf`）を生む綴りもあり到達は非自明・cmdsub/param は SF-004 隣接（runtime 構築＝静的解析の原理限界・実証済み）。secret-staging の主要綴り（quote/BS/`${IFS}`）は iter75 で閉鎖。
- 再現: `r{,}m -rf`/`g{,}it add .env` → ALLOW（grill_verify・現行 HEAD）。
- 修正方向: **ロードマップ iter77 の構造化 argv（実行イベント/argv 判定）**で根治。または SF-001 の control-plane リゾルバ（brace/param 対応済み）を destructive/secrets へ移植（重い・North Star 非整合ぎみ）。**「raw shell text を真実の代理にするな」の系**。
- 状態: **OPEN（accepted residual・iter77 系で根治予定）**。iter75 の残余 pin（test_residual_*）が将来対応時に flip して revisit を強制。

- [ ] **Step 2: commit**

```bash
git add docs/security-followups.md
git commit -F - <<'EOF'
docs(iter75): SF-019 起票 — brace/param/cmdsub トークン分割の残余（構造化 argv 待ち）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Self-Review
- **Spec coverage**: 設計 §コンポーネント分解（helper・destructive・secrets）→ Task2/3/4。§判定表 → Task1/5。§テスト戦略 → Task1/2/5。✅
- **Placeholder scan**: 全ステップに実コード・実コマンド・期待出力あり。✅
- **Type consistency**: helper 名 `aegis_dequote_normalize` を Task2 定義・Task3/4 で一貫使用。変数 `NORM`/`NORM_LC`/`NORM_STRIPPED` 一貫。✅
- **grill-plan 反映済み（2026-07-20・全指摘）**:
  - 致命1（`${IFS}`/`$IFS` 未対応＝`git${IFS}add .env` が修正後も ALLOW）→ Task2 helper に `${IFS}`/`$IFS` 畳み込み追加・Task1/5 に RED/pin。**実証**: grill_verify で現状 ALLOW を確認。
  - 致命2（check-secrets 正規化 grep の regex 再掲 drift）→ Task4 Step1 で staging 検出を `_STAGE_HIGHRISK_RE`/`_STAGE_ENV_RE` に単一ソース化し raw/正規化が同一検出器。
  - 致命3（挿入位置の到達性未保証）→ Task4 Step3 に到達性実測ステップ。読み取り難読化は staging regex 非一致ゆえ末尾配置で誤爆しないことも明記。
  - 要検討2（brace/param/cmdsub 残余）→ Task7 で SF-019 起票・Task5 に残余 pin（現状 allow を固定）。
- **残る受容（明記）**: (a) destructive の正規化も commit-message 誤 ASK を稀に生む（`git commit -m "dr""op table"`）＝ASK 非ブロックゆえ許容。(b) `rm -rf "$DIR"` は生一致で WARN→正規化 skip（二重発火なし・Task5 で pin）。(c) safe-artifact 除外は難読化形に非適用（難読化自体が確認対象）＝過剰 ASK でなく設計意図。
