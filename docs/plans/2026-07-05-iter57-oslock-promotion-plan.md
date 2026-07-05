# iter57 主 moat 交代 実装計画（OS-lock 昇格・check-control-plane 退役）

> **実行規約:** aegis の state machine（implement→review→qa→security→deploy→ship→docs）に従いインライン実行する。
> 各 Task は RED→GREEN→commit の bite-sized 構成。チェックボックスで進捗管理。
> 設計正本: `docs/specs/2026-07-05-iter57-oslock-promotion-design.md`

**Goal:** 安定 control-plane の主 moat を静的解析（check-control-plane.sh 979行）から OS-lock（cp-lock・chmod）へ交代し、静的層は lock が守れない残余領域だけに縮退する。

**Architecture:** ①cp-lock に全数検証 `aegis_cp_verify` を追加し session-start で fail-visible 化 ②残余ミニフック `check-runtime-state.sh` 新設（runtime-state ガード＋unlock 形 deny・manifest allowlist/read-only 迂回を移植）③EACCES 説明 advisory `explain-oslock-eacces.sh` 新設 ④配線・contract・profile を交換して check-control-plane.sh を退役、難読化形テストは「lock 下実走→EACCES」カタログに置換。

**Tech Stack:** pure-bash（bash 3.2 安全・BSD/GNU find 両対応は `-perm -u+w` 形のみ使用）・pytest。

---

## File Structure（責務マップ）

- `hooks/lib/cp-lock.sh` 改修 — `aegis_cp_verify`（期待状態と実状態の全数照合）を追加
- `hooks/session-start.sh` 改修 — apply 後の verify・不一致の強警告（是正手順つき）
- `hooks/check-runtime-state.sh` 新規 — 残余静的ガード（PreToolUse Bash・fail-closed）
- `hooks/explain-oslock-eacces.sh` 新規 — EACCES 説明（PostToolUse Bash・純 advisory・fail-open）
- `hooks/check-control-plane.sh` 削除（Task 9）
- `templates/hooks.template.json`・`templates/profiles/*.json`・`bin/setup.sh`・
  `scripts/check_framework_contract.py`・`scripts/eval_scaffold_smoke.py`・`hooks/lib/scripts-manifest.tsv`（コメント）— 配線交換
- `docs/security-followups.md`・`README.md`・`docs/architecture-overview.md` — 台帳・サポート表明
- tests/ — 置換マッピング（Task 9 の表）どおり

## 移植ブロック集（PORT-n・出典は現行 `hooks/check-control-plane.sh`・**verbatim コピー**）

タスク本文から ID で参照する。コピー時に改変しない（改変が必要な箇所はタスク側に diff で明示）。

- **PORT-1** 安全フォールバック: `AEGIS_SAFETY_FALLBACK_BEGIN`〜`END` ブロック（:24-39）。
  `test_safety_fallback_identity.py` がバイト同一性を検査するため一字も変えない。
- **PORT-2** CASE_FOLD/CASE_I プローブ（:98-105）と `${CASE_I[@]+"${CASE_I[@]}"}` splice イディオム。
- **PORT-3** コマンド抽出（python3 優先＋埋め込みクォート時の fail-closed・改行→`;` 正規化）（:743-757）。
- **PORT-4** `CHAIN_OPS='[;&|>]|\$\(|`'`＋`strip_safe_stderr_redirects()`（:807-821）。
- **PORT-5** `manifest_script_in()`（:839-853）＋`is_allowlisted()`（:857-864）＋
  `SCRIPTS_MANIFEST` パス定義行（`grep -n 'SCRIPTS_MANIFEST=' hooks/check-control-plane.sh` で取得）。
- **PORT-6** read-only 迂回一式: `READ_ONLY_STARTS`・`WRITE_INDICATORS`・単体形(a)＋パイプ形(b)（:914-960）。
- **PORT-7** `is_bare_git_stage()` 関数一式（`grep -n 'is_bare_git_stage' hooks/check-control-plane.sh` で
  定義位置と依存ヘルパを特定して丸ごと）＋STATUS staging の ask 文言（:965-968）。

---

### Task 1: `aegis_cp_verify`（cp-lock 全数照合）＋ symlink 除外（grill 致命2）

**Files:** Modify `hooks/lib/cp-lock.sh` ／ Test Create `tests/test_cp_lock_verify.py`

> **grill 致命2 反映:** (a) symlink の mode は常に 0777 に見え verify が恒久偽陽性を出す。
> (b) 既存 `aegis_cp_lock` の `find -exec chmod` は symlink を**追従して CP 外の実ファイルを chmod する**
> （iter55「symlink 貫通」自己被弾と同クラス）。→ lock/unlock/verify の find **全てに `! -type l` を追加**。
> テスト追加: hooks/ 内に外部向き symlink を置き、lock 後も外部ターゲットが writable のままであること・
> verify が symlink を違反として報告しないこと。
> テスト実装注意（grill 要検討5）: assert 失敗時にも unlock が走るよう、`tests/test_cp_lock_lib.py` の
> 既存 finalizer fixture パターンを踏襲する（tmp read-only 残骸 flake の防止）。

- [ ] **Step 1-1: 失敗するテストを書く**

```python
"""aegis_cp_verify: 期待 lock 状態と実 FS 状態の全数照合（iter57 主 moat 昇格）。
sentinel 1点プローブ（[ -w hooks ]）が誤読する half-locked を可視化する。"""
import os
import subprocess
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "cp-lock.sh"

pytestmark = pytest.mark.skipif(os.geteuid() == 0, reason="root は a-w を無視")


def _mkcp(tmp_path):
    for d in ("hooks/lib", "scripts", "templates", ".claude/rules"):
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "hooks/lib/emit.sh").write_text("x\n")
    (tmp_path / "scripts/a.py").write_text("x\n")
    (tmp_path / "CLAUDE.md").write_text("x\n")
    return tmp_path


def _sh(script, cwd):
    return subprocess.run(["bash", "-c", script], cwd=cwd,
                          capture_output=True, text=True)


def test_verify_ok_when_fully_locked(tmp_path):
    root = _mkcp(tmp_path)
    r = _sh(f'source "{LIB}"; aegis_cp_lock "{root}"; aegis_cp_verify "{root}" feature', root)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == ""
    _sh(f'source "{LIB}"; aegis_cp_unlock "{root}"', root)  # tmp cleanup 可能に


def test_verify_detects_half_locked_nested_file(tmp_path):
    root = _mkcp(tmp_path)
    _sh(f'source "{LIB}"; aegis_cp_lock "{root}"', root)
    # 事故シミュレーション: ネスト深部 1 ファイルだけ writable に戻る
    # （sentinel の hooks/ dir 自体は locked のままなので旧プローブでは不可視）
    (root / "hooks/lib/emit.sh").chmod(0o644)
    r = _sh(f'source "{LIB}"; aegis_cp_verify "{root}" feature', root)
    assert r.returncode == 1
    assert "hooks/lib/emit.sh" in r.stdout
    _sh(f'source "{LIB}"; aegis_cp_unlock "{root}"', root)


def test_verify_detects_locked_remnant_in_framework_mode(tmp_path):
    root = _mkcp(tmp_path)
    _sh(f'source "{LIB}"; aegis_cp_lock "{root}"', root)
    _sh(f'source "{LIB}"; aegis_cp_unlock "{root}"', root)
    (root / "scripts/a.py").chmod(0o444)  # unlock 期待なのに 1 本だけ read-only
    r = _sh(f'source "{LIB}"; aegis_cp_verify "{root}" framework', root)
    assert r.returncode == 1
    assert "scripts/a.py" in r.stdout


def test_verify_empty_root_fails_loud(tmp_path):
    r = _sh(f'source "{LIB}"; aegis_cp_verify "" feature', tmp_path)
    assert r.returncode == 1
```

- [ ] **Step 1-2: RED 確認** — Run: `python3 -m pytest -q -p no:cacheprovider tests/test_cp_lock_verify.py`
      Expected: FAIL（`aegis_cp_verify: command not found` 系）
- [ ] **Step 1-3: 実装** — `hooks/lib/cp-lock.sh` 末尾（`aegis_cp_apply` の後）に追加:

```bash
# aegis_cp_verify <root> <task_type> — full-enumeration check that the ACTUAL
# FS state matches the EXPECTED lock state for task_type. Prints each
# mismatching path (one per line) to stdout; rc 0 = consistent, 1 = mismatch
# (or bad args). iter57: the sentinel probe in aegis_cp_apply is a cheap
# 1-point read used to SKIP redundant chmod; verify is the promoted moat's
# fail-visible net — it walks every path (find -perm -u+w is POSIX; works on
# BSD/macOS and GNU find alike; -writable is GNU-only so NOT used).
aegis_cp_verify() {
  local root="$1" task_type="$2" p bad rc=0
  [ -n "$root" ] || return 1
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ "$task_type" = "framework" ]; then
      bad=$(find "$p" ! -type l ! -perm -u+w 2>/dev/null)
    else
      bad=$(find "$p" ! -type l -perm -u+w 2>/dev/null)
    fi
    if [ -n "$bad" ]; then
      printf '%s\n' "$bad"
      rc=1
    fi
  done < <(aegis_cp_paths "$root")
  return "$rc"
}
```

- [ ] **Step 1-4: GREEN 確認** — 同コマンドで PASS
- [ ] **Step 1-5: commit** — `git add hooks/lib/cp-lock.sh tests/test_cp_lock_verify.py && git commit -m "feat(iter57): aegis_cp_verify — OS-lock 実状態の全数照合（half-locked 可視化・BSD/GNU find 両対応）"`

### Task 2: session-start の verify 配線（fail-visible 化）

**Files:** Modify `hooks/session-start.sh:271-275` ／ Test Modify `tests/test_session_start_cp_lock.py`

- [ ] **Step 2-1: 失敗するテストを追加**（既存 fixture 流用。half-locked を作って session-start 出力に強警告＋是正手順が入ることを検査）

```python
def test_session_start_warns_on_verify_mismatch(aegis_fixture_project):
    root = aegis_fixture_project  # 既存 fixture: STATUS.md task_type=feature
    subprocess.run(["bash", "-c",
        f'source "{root}/hooks/lib/cp-lock.sh"; aegis_cp_lock "{root}"'], check=True)
    (root / "hooks" / "lib" / "emit.sh").chmod(0o644)  # half-locked
    out = run_session_start(root)  # 既存ヘルパ
    assert "OS-lock 状態が期待と不一致" in out
    assert "aegis_cp_apply" in out  # 是正手順の案内
    subprocess.run(["bash", "-c",
        f'source "{root}/hooks/lib/cp-lock.sh"; aegis_cp_unlock "{root}"'], check=True)


def test_session_start_no_verify_warning_when_consistent(aegis_fixture_project):
    root = aegis_fixture_project
    out = run_session_start(root)
    assert "OS-lock 状態が期待と不一致" not in out
```

（`run_session_start`/fixture 名は既存テスト内の実名に合わせる — `tests/test_session_start_cp_lock.py` 冒頭を読んで一致させること）

- [ ] **Step 2-2: RED 確認**
- [ ] **Step 2-3: 実装** — `session-start.sh` の `aegis_cp_apply` 呼出しブロック（:271-275）を置換。
  **grill 要検討3 反映:** verify 警告の前に `case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*)` 分岐を置き、
  該当時は verify をスキップして「[WARNING] 本 OS（Windows ネイティブ）は公式サポート外・OS-lock 保護なし」
  の 1 行のみ emit（chmod no-op による全件不一致スパムの防止）:

```bash
if command -v aegis_cp_apply >/dev/null 2>&1; then
  aegis_cp_apply "$ROOT" "$TASK_TYPE" || CONTEXT="${CONTEXT} | [WARNING] control-plane lock/unlock 一部失敗（OS-lock=主 moat 未適用の可能性。残余ガード check-runtime-state と check-gate は有効）"
  # iter57: OS-lock は主 moat — apply 後に全数照合し、不一致は fail-visible にする。
  if command -v aegis_cp_verify >/dev/null 2>&1; then
    VERIFY_BAD=$(aegis_cp_verify "$ROOT" "$TASK_TYPE" 2>/dev/null | head -3 | tr '\n' ' ' || true)
    if [ -n "$VERIFY_BAD" ]; then
      CONTEXT="${CONTEXT} | [WARNING] OS-lock 状態が期待と不一致（主 moat・要是正）: ${VERIFY_BAD}— 是正: bash -c 'source hooks/lib/cp-lock.sh; aegis_cp_apply \"\$(pwd)\" ${TASK_TYPE}' を再実行"
    fi
  fi
else
  CONTEXT="${CONTEXT} | [WARNING] cp-lock.sh 利用不可（主 moat=OS-lock が無効。残余ガードのみ）"
fi
```

- [ ] **Step 2-4: GREEN 確認** — `python3 -m pytest -q -p no:cacheprovider tests/test_session_start_cp_lock.py tests/test_session_start_injection.py`
- [ ] **Step 2-5: commit** — `fix(iter57): session-start が verify 全数照合で OS-lock 不一致を強警告（主 moat の fail-visible 化）`

### Task 3: `check-runtime-state.sh` — 骨格＋runtime-state deny

**Files:** Create `hooks/check-runtime-state.sh` ／ Test Create `tests/test_runtime_state_hook.py`

- [ ] **Step 3-1: 失敗するテストを書く**（fixture は `tests/test_scripts_manifest_hook.py` の hook 実行ヘルパ流用: hook を copy した tmp プロジェクトに STATUS.md を置き、stdin に PreToolUse JSON を与える）

```python
def _hook_json(cmd):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd},
                       "transcript_path": "/Users/x/.claude/projects/t.jsonl"})

# deny: runtime-state への書込み形
#   echo x >> docs/STATUS.md ／ sed -i 's/pending/approved/' docs/STATUS.md
#   echo '{}' > .claude/settings.json ／ printf x > .claude/.gate-snapshot
# allow: 非該当 echo hi ／ ls src/
# allow: task_type=framework は全許可（現行踏襲）
# deny(fail-closed): 抽出不能入力（embedded escaped quote）で raw input に STATUS.md
# case-fold FS のみ: DOCS/STATUS.MD 形も deny（AEGIS_CASE_FOLD_FORCE=1 で強制発火・
#   test_case_insensitive_fs.py の既存イディオム流用）
```

各ケースを個別 test 関数で書く（`'"permissionDecision":"deny"' in out` / `"allow"` を assert）。

- [ ] **Step 3-2: RED 確認** — hook 不在で全 FAIL
- [ ] **Step 3-3: 実装** — `hooks/check-runtime-state.sh` 新規（実行属性 755）:

```bash
#!/usr/bin/env bash
# PreToolUse hook for Bash: residual static guard after the iter57 moat
# handover. The PRIMARY moat for the stable control-plane (hooks/ scripts/
# templates/ CLAUDE.md .claude/{rules,skills,commands,agents}) is the OS lock
# (hooks/lib/cp-lock.sh — syscall-enforced, form-independent). This hook keeps
# ONLY what the lock cannot cover:
#   (1) runtime-state writes — docs/STATUS.md and .claude/ non-locked parts
#       (settings*.json, .gate-snapshot, evidence-log …) stay writable for the
#       harness/framework, so Bash writes must still be gated statically.
#       Allowlist = hooks/lib/scripts-manifest.tsv class allow|ask (single
#       owner, iter55). manifest unreadable = deny (fail-closed).
#   (2) unlock forms — chmod/chflags/chattr aimed at the locked CP would let
#       an "EACCES self-repair" turn a caught accident into an uncaught one
#       (rev.2 撤回理由②). Denied with a policy message.
# Everything else that used to live in check-control-plane.sh (obfuscation
# token analysis, glob/quote-split/interpreter resolution) is retired: those
# forms now hit EACCES at the syscall regardless of shape.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# <PORT-1 安全フォールバック（バイト同一）>
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
STATUS_FILE="${ROOT}/docs/STATUS.md"
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/frontmatter.sh"
INPUT=$(cat)
[ -f "$STATUS_FILE" ] || { emit_allow; exit 0; }
# <PORT-2 CASE_FOLD/CASE_I>
# 残余ガードの対象トークン:
RUNTIME_STATE='docs/STATUS\.md|(^|[^A-Za-z0-9_./-])STATUS\.md|\.claude/|\.claude([^A-Za-z0-9_/]|$)'
LOCKED_CP='(^|[^A-Za-z0-9_./-])(\./)*(hooks|scripts|templates)(/|$|[[:space:]])|CLAUDE\.md'
UNLOCK_TOOLS='(^|[^A-Za-z0-9_])(chmod|chflags|chattr)([[:space:]]|$)'
# <PORT-3 コマンド抽出＋改行正規化>
_mentions_runtime_state() { printf '%s' "$1" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE"; }
_unlock_form_on_cp() {
  printf '%s' "$1" | grep -qE "$UNLOCK_TOOLS" || return 1
  printf '%s' "$1" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$LOCKED_CP|\.claude/(rules|skills|commands|agents)/"
}
if [ -n "$CMD" ]; then
  if ! _mentions_runtime_state "$CMD" && ! _unlock_form_on_cp "$CMD"; then
    emit_allow; exit 0
  fi
else
  # 抽出失敗 — raw input で判定継続（fail-closed）。transcript_path は
  # ~/.claude/projects/ を含むため RUNTIME_STATE の `.claude/` に必ず当たる →
  # 抽出失敗時は常に deny 経路に入る（現行 check-control-plane と同じ性質）。
  if ! printf '%s' "$INPUT" | grep ${CASE_I[@]+"${CASE_I[@]}"} -qE "$RUNTIME_STATE|$LOCKED_CP"; then
    emit_allow; exit 0
  fi
fi
TASK_TYPE=$(frontmatter_value "$STATUS_FILE" "task_type")
if [ "$TASK_TYPE" = "framework" ]; then emit_allow; exit 0; fi
if [ -n "$CMD" ] && _unlock_form_on_cp "$CMD"; then
  emit_deny "[integrity] chmod/chflags/chattr で control-plane（hooks/ scripts/ templates/ CLAUDE.md .claude/rules 等）の書込み保護を変更しようとしています。これは aegis の OS-lock（主 moat）です。EACCES が出た場合も解錠せず、framework の変更なら scripts/update-task.sh --type framework で task_type を切り替えてください。"
  exit 0
fi
# grill 致命4: EACCES 後の最自然な自己修復 `chmod -R u+w .` は CP token を含まず
# 旧 hook でも素通りだった。主 moat 一本化後は「唯一の moat を最頻事故形が無効化
# できる」に格上がりするため、再帰 chmod × ルート/glob ターゲットは ASK に落とす
# （deny にしないのは user プロジェクト自身の正当な一括 chmod がありうるため）。
_recursive_chmod_broad() {
  printf '%s' "$1" | grep -qE '(^|[^A-Za-z0-9_])chmod[[:space:]][^;|&]*-R' || return 1
  printf '%s' "$1" | grep -qE '[[:space:]](\.{1,2}/?|/|\*)([[:space:]]|$)'
}
if [ -n "$CMD" ] && _recursive_chmod_broad "$CMD"; then
  emit_ask "[integrity] 再帰 chmod（-R）がリポジトリ全体（. / .. / * 等）に及びます。control-plane の OS-lock（主 moat）も解錠されるため確認してください。EACCES への対処なら chmod ではなく task_type=framework への切替（scripts/update-task.sh）が正です。"
  exit 0
fi
# <PORT-4 CHAIN_OPS + strip_safe_stderr_redirects → CMD_SAFE>
# <PORT-5 SCRIPTS_MANIFEST + manifest_script_in + is_allowlisted>
if [ -n "$CMD_SAFE" ] && is_allowlisted "$CMD_SAFE"; then emit_allow; exit 0; fi
# <PORT-6 read-only 迂回 (a)(b)（CHECK_CMD="$CMD_SAFE"）>
# <PORT-7 is_bare_git_stage → emit_ask（STATUS staging）>
if [ -n "$CMD_SAFE" ] && manifest_script_in "$CMD_SAFE"; then
  emit_deny "[integrity] このコマンドは許可済みスクリプト（scripts-manifest）を含みますが、チェーン/リダイレクト演算子（; && || | > \$() \`）付きの複合コマンドでは実行できません。スクリプトを単体コマンドとして実行してください。"
  exit 0
fi
emit_deny "[integrity] runtime-state（docs/STATUS.md・.claude/ 設定類）へ書込みうる Bash コマンドは project work（task_type=${TASK_TYPE}）中はブロックされます。ゲート値は scripts/update-gate.sh、task_type/task_size は scripts/update-task.sh を単体で実行してください。読取りは cat/grep 等の単体コマンドなら許可されます。"
exit 0
```

（`<PORT-n>` 部は移植ブロック集を verbatim 展開。`aegis_require_lib` の実名は check-control-plane.sh:43-48 の
lib 読込み実装をそのまま流用 — 実装時に同型に揃える）

- [ ] **Step 3-4: GREEN 確認** — `python3 -m pytest -q -p no:cacheprovider tests/test_runtime_state_hook.py`
- [ ] **Step 3-5: commit** — `feat(iter57): check-runtime-state.sh — 残余静的ガード骨格（runtime-state deny・framework allow・抽出失敗 fail-closed・case-fold）`

### Task 4: allowlist＋read-only＋git-stage 迂回（PORT-4〜7 展開）

**Files:** Modify `hooks/check-runtime-state.sh` ／ Test Modify `tests/test_runtime_state_hook.py`

- [ ] **Step 4-1: 失敗するテストを追加** — allow: `bash scripts/update-gate.sh review approve`・
  `python3 scripts/check_status.py`・`cat docs/STATUS.md`・`grep -n phase docs/STATUS.md | head -3`・
  `ls templates/ 2>/dev/null`（stderr strip）／deny: `bash scripts/update-gate.sh x && rm -rf y`（専用文言）・
  manifest 欠落時の `python3 scripts/check_status.py`（fail-closed）／ask: `git add docs/STATUS.md`
- [ ] **Step 4-2: RED → Step 4-3: PORT-4〜7 を展開実装 → Step 4-4: GREEN**
- [ ] **Step 4-5: commit** — `feat(iter57): check-runtime-state — manifest allowlist・read-only/パイプ迂回・git-stage ask・チェーン専用文言（check-control-plane から移植）`

### Task 5: EACCES 説明 advisory

**Files:** Create `hooks/explain-oslock-eacces.sh` ／ Test Create `tests/test_explain_oslock_eacces.py`

- [ ] **Step 5-0（grill 致命1・着手前必須）: PostToolUse envelope の実証** —
  synthetic JSON テストは自作自演で green になるため、**実セッションで tool_response（stderr テキスト）が
  envelope に実在するかを先に確認**する: 一時 capture hook（`INPUT=$(cat); printf '%s\n' "$INPUT" >> .claude/.posttool-probe.log`）
  を scratch プロジェクトの PostToolUse Bash に登録 → EACCES で失敗するコマンドを実行 → log の JSON に
  stderr 相当が含まれるか確認。結果を `scripts/platform_manifest.py` の PLATFORM_VERIFIED 系コメントに
  検証日付きで記録。**不在だった場合の分岐**: advisory は廃案にし、同内容の説明を
  check-runtime-state の unlock-deny 文言と README 移行ノートに寄せる（設計書の該当節も更新）。
- [ ] **Step 5-1: 失敗するテストを書く** — PostToolUse JSON（`tool_response` に
  `"Permission denied"`＋`hooks/lib/emit.sh`）→ stdout に `additionalContext`＋`OS-lock`；
  EACCES のみ（CP なし）→ 出力なし rc0；CP のみ（EACCES なし）→ 出力なし rc0；
  壊れた JSON → 出力なし rc0（純 advisory・fail-open）；
  `.claude/projects/`（transcript_path）だけでは CP 判定にしない（誤発火防止）
- [ ] **Step 5-2: RED → Step 5-3: 実装**:

```bash
#!/usr/bin/env bash
# PostToolUse (Bash) ADVISORY: when a command failed with EACCES/Permission
# denied on a locked control-plane path, explain that this is the aegis
# OS-lock — BEFORE the agent tries `chmod +w` self-repair (rev.2 撤回理由②の
# 恒久対策). Pure advisory: never blocks, all failures fail-open (exit 0).
# Deliberately reads the RAW input; no JSON parsing dependency. transcript_path
# always contains ~/.claude/projects/, so `.claude/` alone must NOT count as a
# CP hit — only the locked dirs' explicit forms below.
set -u
INPUT=$(cat 2>/dev/null || true)
[ -n "$INPUT" ] || exit 0
printf '%s' "$INPUT" | grep -qiE 'permission denied|EACCES' || exit 0
printf '%s' "$INPUT" | grep -qE '(hooks|scripts|templates)/|CLAUDE\.md|\.claude/(rules|skills|commands|agents)/' || exit 0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/emit.sh" 2>/dev/null || exit 0
emit_context PostToolUse "[oslock] 直前の Permission denied は aegis の OS-lock（主 moat）による保護の可能性があります。chmod/chflags での解錠は行わないでください。framework ファイルの変更が正当な作業なら scripts/update-task.sh --type framework で task_type を切り替え、セッションを再開すると自動で unlock されます。"
exit 0
```

- [ ] **Step 5-4: GREEN → Step 5-5: commit** — `feat(iter57): explain-oslock-eacces — EACCES 時に OS-lock を説明し chmod 自己修復を抑止（純 advisory）`

### Task 6: 配線・登録の交換

**Files:** Modify `templates/hooks.template.json:58`・`templates/profiles/{minimal,standard,full}.json`・
`scripts/check_framework_contract.py:39,154`・`bin/setup.sh`（copy_hooks 末尾）・
`hooks/lib/scripts-manifest.tsv`（ヘッダコメント:2）・`scripts/eval_scaffold_smoke.py:162-179`
Test Modify: `tests/test_profile_moat_registration.py`・`tests/test_hook_required_coverage.py`・
`tests/test_safety_fallback_identity.py`・`tests/test_hook_output_schema.py`・`tests/test_full_profile_runnable_scripts.py`

- [ ] **Step 6-1: 失敗するテストを先に更新** — 各登録検査の期待値を
  `check-control-plane.sh` → `check-runtime-state.sh`（＋advisory は PostToolUse 登録のみ・
  safety-identity 対象は check-runtime-state のみ、explain-oslock-eacces は advisory につき対象外と明記）
- [ ] **Step 6-2: RED 確認（登録系テストが新期待で FAIL）**
- [ ] **Step 6-3: 実装**
  - hooks.template.json: Bash PreToolUse 先頭 entry の command を
    `bash "${CLAUDE_PROJECT_DIR:-.}"/hooks/check-runtime-state.sh` に変更。
    PostToolUse の `Bash` matcher グループ（post-bash.sh / post-bash-observe.sh が居る箇所）へ
    `{"type":"command","command":"bash \"${CLAUDE_PROJECT_DIR:-.}\"/hooks/explain-oslock-eacces.sh"}` を追加
  - profiles: `hooks_include`・`recommended`・`required_hook_scripts` の
    check-control-plane 行を check-runtime-state に置換し、explain-oslock-eacces.sh を
    check-control-plane が載っていた profile と同じ集合へ追加（minimal は現状の掲載有無に従う —
    実装時に `grep -n control-plane templates/profiles/minimal.json` で確認）
  - contract: `CORE_ENFORCEMENT_HOOKS` と `REQUIRED_HOOK_FILES` を交換（advisory も REQUIRED に追加 —
    配布欠落の silent 化防止。F6 教訓）
  - setup.sh `copy_hooks()` 末尾に退役 hook の prune を追加:

```bash
  # iter57: retired hooks — remove stale copies on upgrade so an old install
  # does not keep a wired-out moat file around (confusing half-state).
  rm -f "$target_dir/hooks/check-control-plane.sh"
```

  - scripts-manifest.tsv ヘッダの消費者名を check-runtime-state.sh に更新
  - **grill 致命3: 本リポ自身の生きた配線を更新** — hook 登録は install 先では settings、
    **本リポでは `.claude/settings.local.json`**（rev.2 grill#2 の記録）。
    `grep -n "check-control-plane" .claude/settings.json .claude/settings.local.json` で登録元を特定し、
    check-runtime-state＋explain-oslock-eacces へ書き換える（これを怠ると Task 8 の削除後、
    ユーザーの全 aegis セッションで PreToolUse が存在しないファイルを叩く）
  - eval_scaffold_smoke.py: check-control-plane 発火検証（:162-179）を
    「check-runtime-state が STATUS write を deny」＋「installed tree で cp-lock apply→verify rc0」に置換
- [ ] **Step 6-4: GREEN 確認** — `python3 -m pytest -q -p no:cacheprovider tests/test_profile_moat_registration.py tests/test_hook_required_coverage.py tests/test_safety_fallback_identity.py tests/test_hook_output_schema.py tests/test_full_profile_runnable_scripts.py && python3 scripts/check_framework_contract.py`
- [ ] **Step 6-5: commit** — `feat(iter57): 配線交換 — template/profiles/contract/setup prune/scaffold smoke を check-runtime-state＋advisory へ（退役 hook の install 残骸も除去）`

### Task 7: 事故カタログの lock 下 EACCES 回帰（置換の中核）

**Files:** Modify `tests/test_cp_lock_sf_catalog.py`（拡張）

- [ ] **Step 7-1: 追加ケースを書く**（既存カタログの fixture/ヘルパを流用。各形: lock 済み scratch CP に
  実行 → 失敗 rc≠0 かつ対象ファイル内容不変を assert）
  - grill 由来: `(cd sub && cp x ../hooks/emit.sh)`・`echo x > hooks/e.sh # HOOKS/ 大文字`（case-fold FS のみ）・
    `cp x hooks*/emit.sh`（glob）・`python3 -c "open('hooks/emit.sh','w').write('x')"`（既存にあれば重複不要）・
    `find hooks -name '*.sh' -exec sh -c 'echo x > {}' \;`
  - 新規ファイル作成の物理阻止: `touch hooks/evil.sh` → 失敗（dir a-w が創作も塞ぐ）
  - rename/move: `mv hooks hooks_bak` → 失敗（root は非 lock だが hooks dir 自体の rename は
    dir エントリ変更 = 親 dir write。root が writable なので **成功しうる** — 実測して成功するなら
    accepted residual（rev.2 既定）をコメントで明記し、テストは「hooks/ 内のファイルは INTACT」のみ assert）
- [ ] **Step 7-2: 実行して全 PASS を確認**（このタスクは既存機構の実証追加なので RED は不要 —
  代わりに **lock を外した対照実行**で「unlock なら書けてしまう」ことを 1 ケース確認し、
  テストが実際に挙動を弁別していることを示す）
- [ ] **Step 7-3: commit** — `test(iter57): 事故カタログ拡張 — grill 由来バイパス形＋新規作成/リネームを lock 下実走で回帰固定（旧難読化テスト群の置換受け皿）`

### Task 8: 退役実行（削除＋テスト置換マッピング）

**Files:** Delete `hooks/check-control-plane.sh` ＋ 下表のテスト整理

| 旧テスト | 処置 | 受け皿 |
|---|---|---|
| test_control_plane_token_split.py | 削除 | Task 7 カタログ（quote-split/backslash 形） |
| test_control_plane_var_expansion.py | 削除 | Task 7 カタログ（$(pwd)/$VAR 形は EACCES） |
| test_control_plane_messages.py | 削除 | test_runtime_state_hook（deny 文言 assert） |
| test_control_plane_allowlist.py | 書換 | check-runtime-state 対象に同ケース移植 |
| test_scripts_manifest_hook.py | 書換 | 対象 hook を check-runtime-state に変更（fail-closed 検査は不変） |
| test_control_plane_chmod_unlock.py | 分割 | 静的 deny → test_runtime_state_hook（Task 3/4 済）・layer-2 統合 → test_cp_relock_integration に unique 分を移送 |
| test_case_insensitive_fs.py | 部分削除 | check-secrets/check-gate 分は存置・CP 分は Task 7 case-fold ケース |
| test_safe_stderr_redirect.py | 部分書換 | check-secrets 分は存置・CP allowlist 分は test_runtime_state_hook |
| test_cp_lock_contract.py | 書換 | parity 対象を check-runtime-state の LOCKED_CP dirs へ（drift ガード継続） |
| test_patterns_parity.py | 書換 | CONTROL_PLANE 参照を新 hook の RUNTIME_STATE/LOCKED_CP に |
| test_check_status.py | 微修正 | コメント/文言中の hook 名参照のみ |

- [ ] **Step 8-1: 上表の「書換」を先に完了**（各書換は RED→GREEN で個別確認）
- [ ] **Step 8-2: `git rm hooks/check-control-plane.sh` ＋「削除」行のテストを `git rm`**
- [ ] **Step 8-3: 参照掃除**（`.claude/settings*.json` を必ず含める・grill 致命3） — Run: `grep -rn "check-control-plane" --exclude-dir=.git --exclude-dir=docs . ; grep -rln "check-control-plane" docs/`
      Expected: コード/テスト/テンプレ側 0 件。docs 側は Task 9 で更新する台帳・設計書のみ
- [ ] **Step 8-4: full suite green** — Run: `python3 -m pytest -q` Expected: 全 PASS
- [ ] **Step 8-5: commit** — `refactor(iter57)!: check-control-plane.sh（979行）退役 — 主 moat を OS-lock に交代（テストは 1対1 置換マッピングどおり移送）`

### Task 9: ドキュメント・台帳更新

**Files:** Modify `docs/security-followups.md`・`README.md`・`docs/architecture-overview.md`・`CLAUDE.md`（該当記述があれば）

- [ ] **Step 9-1:** security-followups.md — 冒頭 canonical 節の layer-1/layer-2 記述を「主 moat=OS-lock／残余静的ガード=check-runtime-state」へ改訂。SF-001〜005 の各項へ状態追記: 「iter57 で主 moat が syscall 層へ交代。事故スコープでは形非依存に構造閉鎖（Task 7 カタログが回帰固定）。敵対残存（os.chmod 解錠）は従来どおり脅威モデル外。Windows ネイティブは保護なし（公式サポート外）」
- [ ] **Step 9-2:** README — サポート OS 表明（macOS/Linux/WSL・Windows は OS-lock 無効）＋移行ノート（setup.sh 再実行で配線交換・旧 hook file は prune・framework 更新は task_type=framework・エディタからも read-only に見える）
- [ ] **Step 9-3:** `grep -rn "check-control-plane\|層1\|layer-1" README.md CLAUDE.md .claude/rules/ docs/architecture-overview.md` で残存記述を洗い、新構成へ更新
- [ ] **Step 9-4:** `python3 scripts/context_budget.py check`（budget 超過なし）・`python3 scripts/check_reference_drift.py`
- [ ] **Step 9-5: commit** — `docs(iter57): 台帳・README・アーキ記述を主 moat 交代後の構成へ（SF-001〜005 状態追記・Windows サポート表明）`

---

## 実装後（plan 外・state machine 準拠）

review（grill-code＋盲検2次）→ qa（B1 drill・per-task コミット済なら SKIP 代替実証）→
security（moat 交代の実バイパス試行・盲検2次）→ deploy（install 契約検証）→
ship（**v1.18.0 bump** — version 同期テストは iter56 で single-owner 鏡写し化済みのため
contract/template の 2 箇所のみ）→ docs（LEARNINGS 蒸留）→ push 手前停止。

## Self-Review チェック済み事項

- spec カバレッジ: 設計書の全コンポーネント（verify/session-start/残余フック/advisory/退役/台帳）に対応 Task あり
- 退役の空白確認: STATUS.md への Bash 書込みガードは Task 3 が退役前に GREEN になる順序（Task 8 は Task 3-7 完了後）＝保護の空白期間なし
- 型/名前整合: `aegis_cp_verify(root, task_type)`・`check-runtime-state.sh`・`explain-oslock-eacces.sh` で全 Task 一貫
