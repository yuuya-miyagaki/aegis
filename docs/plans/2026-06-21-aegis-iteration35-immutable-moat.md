# Immutable Moat (layer-2 OS lock) Implementation Plan — iteration 35

> **For agentic workers:** REQUIRED SUB-SKILL: framework subagent-dev（`.claude/skills/subagent-dev/SKILL.md`）。
> タスクごとにフレッシュなサブエージェント＋2段階レビュー。各タスクは TDD（RED→GREEN→commit）。
> Steps は checkbox（`- [ ]`）で進捗管理。

**Goal:** control-plane への誤書込み防御を OS/FS レベルの write-lock（layer-2）で多層化する。`hooks/lib/cp-lock.sh` を新設し session-start で task_type 連動 lock/unlock を行う。既存の静的 moat（layer-1）は存置。

**Architecture:** `chmod -R a-w`（owner も含め write 剥奪・read+exec 維持）で安定 CP パスを物理的に書込み不可にする。lock 状態は STATUS の `task_type` から session-start で決定（project 系=LOCKED / framework=UNLOCKED）。lock は「層」であり失敗は warn（fail-closed ではない）。layer-1（check-control-plane[Bash]＋check-gate[Edit|Write]）が常時存在するため lock 失敗でも moat は残る。

**Tech Stack:** bash 3.2（macOS 既定）・pure-bash（外部依存ゼロ）・pytest（subprocess で hook/lib を実走）・POSIX `chmod`。

**設計の正直な価値の射程（grill 反映・2026-06-21）:** 普通のコマンド形による「事故」は既に layer-1 が Bash も Edit/Write も deny 済。**layer-2 は敵対 SF-004 を閉じない**——`chmod`/`chflags` は所有権で判定されるため、owner（エージェント）は a-w 下でも `os.chmod(constructed_path,0o644)` で解錠でき、敵対者は SF-004 と同じ interpreter channel で解錠してから書ける（layer-1 は構築形を取りこぼす＝原理的限界はそのまま）。SF-004 は「事故」では起きない。**よって layer-2 の正直な価値は次の1点に尽きる**: layer-1 は 889 行・SF-001〜005 の 5 件のバイパス実績がある脆い層であり、その**未発見バイパスクラスに対する「事故ケース限定」の独立 syscall バックストップ（保険）**。敵対 sandbox ではない。穴埋めでも SF-004 閉鎖でもなく、**事故ケースの多層保険**として lean に実装する。

## Global Constraints

- **bash 3.2 互換**: 外側 hook スコープは `[ ]`、関数内は `[[ ]]` 可。`readarray`/連想配列 禁止。process substitution `< <(...)` は可。BSD/GNU 両対応の `chmod`/`find`。
- **pure-bash・外部依存ゼロ**（cp-lock.sh は python3/jq 非依存）。
- **lock 失敗は非致命（warn）**: session-start は `set -euo pipefail`。lock 呼び出しは必ず `if` で rc を消費し、script を abort させない。
- **fail-closed しない**: cp-lock.sh の source は `|| true`＋`command -v` ガード（欠損で session が落ちない・layer-1 は維持）。
- **退役なし**: `check-control-plane.sh`・`hooks/lib/` は一切削除しない。
- **SemVer**: 追加のみ後方互換 → **MINOR 1.12.1 → 1.13.0**。
- **設計**: `docs/specs/2026-06-21-immutable-moat-design.md`（rev.2）。安定 CP セットの単一所有は `aegis_cp_paths`。
- **lock 対象パス（root 相対）**: `hooks` `scripts` `templates` `CLAUDE.md` `.claude/rules` `.claude/skills` `.claude/commands` `.claude/agents`（存在するもののみ）。
- **settings は両方 lock しない（grill#2 反映）**: `.claude/settings.json`・`.claude/settings.local.json` とも layer-2 lock 対象外。理由: (1) Claude Code ハーネス自身が permission grant（"常に許可"）や hook 更新を settings（特に settings.local.json）へ書く＝lock すると EACCES でサイレント破損、(2) 本リポは hook 登録が settings.local.json にあり settings.json は不在＝lock しても無意味、(3) settings は layer-1（check-gate が Edit、check-control-plane が Bash 書込みを deny・check-skill-gate も settings.json 改変 skill を gate）で既に保護済。
- **その他の除外（lock しない）**: `docs/`（STATUS 含む）・`.claude/.gate-snapshot`・`.claude/evidence-log.jsonl*`・`.claude/.audit-skip.log`・`.claude/.task-event-debug.log`・`.claude/.aegis-install-version`・repo root 自身（downstream のユーザープロジェクト root を縛らない）。

---

### Task 0: `hooks/lib/cp-lock.sh` — CP OS-lock lib（安定 CP セットの単一所有）

**Files:**
- Create: `hooks/lib/cp-lock.sh`
- Test: `tests/test_cp_lock_lib.py`

**Interfaces:**
- Produces:
  - `aegis_cp_paths <root>` → 存在する lock 対象パスを 1 行 1 件で stdout 出力。
  - `aegis_cp_lock <root>` → 各パスに `chmod -R a-w`。全成功で rc 0、一部失敗で rc 1。
  - `aegis_cp_unlock <root>` → 各パスに `chmod -R u+w`。全成功で rc 0、一部失敗で rc 1。
- Consumes: なし（純粋ユーティリティ）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_cp_lock_lib.py`

```python
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "cp-lock.sh"

WINDOWS = sys.platform.startswith("win")
# root bypasses the write permission bit, so a-w does not block root writes.
# CI often runs as root — skip the moat assertions there (they are meaningless).
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    WINDOWS or ROOTUSER,
    reason="chmod write-bit is a no-op on native Windows / bypassed by root")


def _make_scratch() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    # CP files (must become read-only when locked)
    (p / "hooks" / "lib").mkdir(parents=True)
    (p / "hooks" / "check-x.sh").write_text("echo hi\n")
    (p / "hooks" / "lib" / "util.sh").write_text("echo lib\n")
    (p / "scripts").mkdir()
    (p / "scripts" / "tool.py").write_text("print(1)\n")
    (p / "CLAUDE.md").write_text("# rules\n")
    (p / ".claude" / "skills").mkdir(parents=True)
    (p / ".claude" / "skills" / "s.md").write_text("skill\n")
    (p / ".claude" / "settings.json").write_text("{}\n")
    # runtime-state (must stay writable)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text("---\n---\n")
    (p / ".claude" / ".gate-snapshot").write_text("phase: x\n")
    (p / ".claude" / "settings.local.json").write_text("{}\n")
    return tmp


def _bash(snippet: str, root: str):
    return subprocess.run(
        ["bash", "-c", f'source "{LIB}"; {snippet}'],
        capture_output=True, text=True, cwd=root,
    )


def _can_write(path: Path) -> bool:
    # Try to append via a fresh shell so the test process umask/ownership
    # doesn't mask the chmod result; return True iff the write syscall succeeds.
    r = subprocess.run(["bash", "-c", f'printf x >> "{path}"'],
                       capture_output=True, text=True)
    return r.returncode == 0


@NO_FS_LOCK
class TestCpLock:
    def test_paths_lists_only_existing(self):
        tmp = _make_scratch()
        try:
            out = _bash('aegis_cp_paths "$PWD"', tmp.name).stdout
            listed = {line.split("/")[-1] for line in out.split() if line}
            assert "hooks" in listed and "scripts" in listed
            assert "CLAUDE.md" in listed
            # settings (json AND local) / docs / .gate-snapshot must NOT be listed
            assert "settings.json" not in out and "settings.local.json" not in out
            assert "/docs" not in out and ".gate-snapshot" not in out
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_lock_blocks_all_write_forms(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            # echo redirect, cp, rm, python3 open(w) — all must fail under lock
            cp_file = p / "hooks" / "lib" / "util.sh"
            assert not _can_write(cp_file), "locked CP file must reject append"
            assert subprocess.run(
                ["bash", "-c", f'cp /etc/hostname "{cp_file}"'],
                capture_output=True).returncode != 0
            assert subprocess.run(
                ["bash", "-c", f'rm "{cp_file}"'],
                capture_output=True).returncode != 0
            assert subprocess.run(
                ["python3", "-c", f"open('{cp_file}','w').write('x')"],
                capture_output=True).returncode != 0
            # creating a NEW file inside a locked dir must also fail
            assert subprocess.run(
                ["bash", "-c", f'printf x > "{p / "hooks" / "evil.sh"}"'],
                capture_output=True).returncode != 0
            assert cp_file.read_text() == "echo lib\n", "file content INTACT"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_runtime_state_stays_writable_under_lock(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            assert _bash('aegis_cp_lock "$PWD"', tmp.name).returncode == 0
            assert _can_write(p / "docs" / "STATUS.md")
            assert _can_write(p / ".claude" / ".gate-snapshot")
            assert _can_write(p / ".claude" / "settings.json")
            assert _can_write(p / ".claude" / "settings.local.json")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_unlock_restores_writability(self):
        tmp = _make_scratch()
        p = Path(tmp.name)
        try:
            _bash('aegis_cp_lock "$PWD"', tmp.name)
            assert not _can_write(p / "hooks" / "lib" / "util.sh")
            assert _bash('aegis_cp_unlock "$PWD"', tmp.name).returncode == 0
            assert _can_write(p / "hooks" / "lib" / "util.sh")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()

    def test_lock_is_idempotent(self):
        tmp = _make_scratch()
        try:
            assert _bash('aegis_cp_lock "$PWD"; aegis_cp_lock "$PWD"',
                         tmp.name).returncode == 0
            assert _bash('aegis_cp_unlock "$PWD"; aegis_cp_unlock "$PWD"',
                         tmp.name).returncode == 0
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name])
            tmp.cleanup()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_cp_lock_lib.py -v`
Expected: FAIL（`hooks/lib/cp-lock.sh` が存在せず source 失敗）

- [ ] **Step 3: 最小実装** — `hooks/lib/cp-lock.sh`

```bash
#!/usr/bin/env bash
# hooks/lib/cp-lock.sh — layer-2 OS/FS write-lock for the stable control-plane.
# Sourced by session-start.sh. pure-bash, bash 3.2 safe, idempotent.
#   lock   = chmod -R a-w  (removes write for all; read+exec preserved)
#   unlock = chmod -R u+w  (restores owner write)
# Failure is NON-fatal: the caller warns and continues (OS lock is a defense
# layer, not a fail-closed gate — layer-1 static moat is always present).
# Owner of the stable CP path set (single source of truth for the chmod target).
# NOTE: this is the FS-path enumeration for layer-2; it is intentionally NOT
# unified with check-control-plane.sh's CONTROL_PLANE regex (different domain:
# command-token matching vs filesystem paths).

# aegis_cp_paths <root> — print existing lock-target paths, one per line.
aegis_cp_paths() {
  local root="$1" p
  # NOTE: .claude/settings*.json は意図的に対象外（Claude Code ハーネスが
  # permission grant / config を settings へ書くため lock すると破損する。
  # settings は layer-1 で保護済）。
  for p in \
    "hooks" \
    "scripts" \
    "templates" \
    "CLAUDE.md" \
    ".claude/rules" \
    ".claude/skills" \
    ".claude/commands" \
    ".claude/agents"; do
    [ -e "${root}/${p}" ] && printf '%s\n' "${root}/${p}"
  done
}

# aegis_cp_lock <root> — make the stable CP read-only. rc 0 all-ok, 1 on any failure.
aegis_cp_lock() {
  local root="$1" rc=0 p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    chmod -R a-w "$p" 2>/dev/null || rc=1
  done < <(aegis_cp_paths "$root")
  return "$rc"
}

# aegis_cp_unlock <root> — restore owner write on the stable CP. rc 0/1 as above.
aegis_cp_unlock() {
  local root="$1" rc=0 p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    chmod -R u+w "$p" 2>/dev/null || rc=1
  done < <(aegis_cp_paths "$root")
  return "$rc"
}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_cp_lock_lib.py -v`
Expected: PASS（全 5 テスト・macOS/Linux）

- [ ] **Step 5: コミット**

```bash
git add hooks/lib/cp-lock.sh tests/test_cp_lock_lib.py
git commit -F - <<'EOF'
feat(moat): add cp-lock.sh layer-2 OS write-lock for control-plane

chmod -R a-w / u+w で安定 CP を task_type 連動で施錠/解錠する pure-bash lib。
aegis_cp_paths が lock 対象 FS パスの単一所有。runtime-state は除外。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 1: session-start.sh で task_type 連動 lock/unlock

**Files:**
- Modify: `hooks/session-start.sh`（lib source は行 9-12 付近に追記、lock 呼び出しは末尾 `emit_context SessionStart "$CONTEXT"` の直前）
- Test: `tests/test_session_start_cp_lock.py`

**Interfaces:**
- Consumes: `aegis_cp_lock` / `aegis_cp_unlock`（Task 0）、`ROOT`（session-start 行 6）、`TASK_TYPE`（session-start 行 41）。
- Produces: なし（副作用＝FS lock 状態 ＋ 失敗時の CONTEXT warn）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_session_start_cp_lock.py`

```python
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = sys.platform.startswith("win")
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    WINDOWS or ROOTUSER, reason="chmod no-op on Windows / bypassed by root")
LIBS = ("emit.sh", "frontmatter.sh", "phase-skills.sh", "sanitize.sh",
        "evidence.sh", "extract-input.sh", "fingerprint.sh", "patterns.sh",
        "cp-lock.sh")  # evidence.sh の推移的依存も含める


def _install(task_type: str) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        f"task_type: {task_type}\n---\n")
    (p / "hooks" / "lib").mkdir(parents=True)
    (p / "hooks" / "session-start.sh").write_bytes(
        (ROOT / "hooks" / "session-start.sh").read_bytes())
    for lib in LIBS:
        (p / "hooks" / "lib" / lib).write_bytes(
            (ROOT / "hooks" / "lib" / lib).read_bytes())
    (p / "scripts").mkdir()
    (p / "scripts" / "tool.py").write_text("print(1)\n")
    (p / "CLAUDE.md").write_text("# rules\n")
    return tmp


def _run_session_start(root: str):
    return subprocess.run(
        ["bash", str(Path(root) / "hooks" / "session-start.sh")],
        input="{}", capture_output=True, text=True, cwd=root)


def _writable(path: Path) -> bool:
    return subprocess.run(["bash", "-c", f'printf x >> "{path}"'],
                          capture_output=True).returncode == 0


@NO_FS_LOCK
class TestSessionStartLock:
    def test_feature_locks_control_plane(self):
        tmp = _install("feature")
        p = Path(tmp.name)
        try:
            r = _run_session_start(tmp.name)
            assert r.returncode == 0
            assert not _writable(p / "hooks" / "lib" / "frontmatter.sh"), \
                "feature session must lock CP"
            assert not _writable(p / "CLAUDE.md")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_framework_unlocks_control_plane(self):
        tmp = _install("framework")
        p = Path(tmp.name)
        try:
            # pre-lock to prove session-start actively unlocks
            subprocess.run(["chmod", "-R", "a-w", str(p / "hooks")])
            r = _run_session_start(tmp.name)
            assert r.returncode == 0
            assert _writable(p / "hooks" / "lib" / "frontmatter.sh"), \
                "framework session must unlock CP"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_missing_lib_does_not_crash(self):
        tmp = _install("feature")
        p = Path(tmp.name)
        try:
            (p / "hooks" / "lib" / "cp-lock.sh").unlink()
            r = _run_session_start(tmp.name)
            assert r.returncode == 0, "missing cp-lock must not fail session-start"
            assert "layer-1" in r.stdout or "cp-lock" in r.stdout, \
                "should warn that layer-2 was skipped"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_session_start_cp_lock.py -v`
Expected: FAIL（session-start がまだ lock を呼ばない＝feature でも writable のまま）

- [ ] **Step 3: session-start.sh を改修**

3a. lib source 追加（既存 `source "${SCRIPT_DIR}/lib/sanitize.sh"`（行 12）の直後に追記）:

```bash
# layer-2 CP OS-lock lib. Sourced safely: a missing/broken lib must NOT
# fail-close the session (the static moat / layer-1 is always present).
# NOTE: a bare `source missing.sh || true` does NOT survive `set -e` — sourcing
# a nonexistent file is fatal and bypasses `||`. Guard with -f so the missing
# lib path is simply skipped (the command -v check below then emits the warn).
if [ -f "${SCRIPT_DIR}/lib/cp-lock.sh" ]; then
  source "${SCRIPT_DIR}/lib/cp-lock.sh" 2>/dev/null || true
fi
```

3b. lock 呼び出し（末尾 `emit_context SessionStart "$CONTEXT"` の直前に挿入）:

```bash
# layer-2: OS/FS write-lock of the stable control-plane, keyed on task_type.
# Lock failure is non-fatal — warn into CONTEXT; layer-1 static moat stays active.
if command -v aegis_cp_lock >/dev/null 2>&1 && command -v aegis_cp_unlock >/dev/null 2>&1; then
  if [ "$TASK_TYPE" = "framework" ]; then
    aegis_cp_unlock "$ROOT" || CONTEXT="${CONTEXT} | [WARNING] control-plane unlock 一部失敗（framework 編集が EACCES になる場合あり・該当ファイルを手動 chmod u+w）"
  else
    aegis_cp_lock "$ROOT" || CONTEXT="${CONTEXT} | [WARNING] control-plane lock 一部失敗（layer-2 未適用・layer-1 静的 moat は有効）"
  fi
else
  CONTEXT="${CONTEXT} | [WARNING] cp-lock.sh 利用不可（layer-2 OS lock skip・layer-1 静的 moat は有効）"
fi
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_session_start_cp_lock.py -v`
Expected: PASS（3 テスト）

- [ ] **Step 5: 回帰確認＋コミット**

Run: `python3 -m pytest tests/test_session_start*.py -v`（既存 session-start テストが緑のまま）

```bash
git add hooks/session-start.sh tests/test_session_start_cp_lock.py
git commit -F - <<'EOF'
feat(moat): wire cp-lock into session-start (task_type-keyed lock/unlock)

project 系 task_type は CP を chmod a-w で施錠、framework は解錠。
cp-lock 欠損・lock 失敗は warn のみで session を落とさない（layer-1 維持）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 2: layer-1 chmod-unlock / rename 回帰テスト（新規ロジック無し）

> **意図**: 設計の前提「`chmod +w`/`chflags nouchg`/`chattr -i`/`mv hooks` が CP 対象なら
> project モードで layer-1 が deny」を実測で固定し、将来のリファクタで退行しないようにする。
> production code は変更しない。

**Files:**
- Test: `tests/test_control_plane_chmod_unlock.py`

**Interfaces:**
- Consumes: `hooks/check-control-plane.sh`（既存・無改修）。

- [ ] **Step 1: 回帰テストを書く** — `tests/test_control_plane_chmod_unlock.py`

```python
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
```

- [ ] **Step 2: テスト実行（基本 GREEN 期待・既存挙動の固定）**

Run: `python3 -m pytest tests/test_control_plane_chmod_unlock.py -v`
Expected: PASS（既存挙動を確認）。万一いずれか FAIL なら、それは layer-1 の実ギャップ＝
設計前提の反証なので**停止して報告**（推測で production を変えない）。

- [ ] **Step 3: コミット**

```bash
git add tests/test_control_plane_chmod_unlock.py
git commit -F - <<'EOF'
test(moat): pin layer-1 deny for chmod-unlock / rename of control-plane

設計が layer-2 の前提とする「CP 対象 chmod +w/chflags/chattr/mv は project
モードで layer-1 deny」を回帰テストで固定（production 無改修）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 3: SF-001〜005 カタログを lock 下で実走（defense-in-depth 証拠）

> **意図**: 「**lock がアクティブな間は、layer-1 を素通りする形（quote-split / SF-004 interpreter
> 含む）でも syscall が形非依存に CP 書込みを阻止する**」ことを実証する。これは layer-2 の
> defense-in-depth（layer-1 が漏らした事故が lock に当たって止まる）証拠。
> **注意（grill#1）**: これは「SF-004 を脅威として閉じた」証明では**ない**——敵対者は同じ
> interpreter で `os.chmod` 解錠してから書けるため lock を回避できる。本テストが示すのは
> あくまで「lock 状態を前提とした事故ケースの形非依存阻止」であり、`security-followups.md`
> には「敵対 SF-004 は layer-2 でも閉じない・事故ケースは多層保険で軽減」と記す。

**Files:**
- Test: `tests/test_cp_lock_sf_catalog.py`

**Interfaces:**
- Consumes: `aegis_cp_lock`（Task 0）。

- [ ] **Step 1: テストを書く** — `tests/test_cp_lock_sf_catalog.py`

```python
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "cp-lock.sh"
WINDOWS = sys.platform.startswith("win")
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    WINDOWS or ROOTUSER, reason="chmod no-op on Windows / bypassed by root")


def _scratch():
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "hooks" / "lib").mkdir(parents=True)
    (p / "hooks" / "lib" / "emit.sh").write_text("echo orig\n")
    return tmp


def _lock(root: str):
    subprocess.run(["bash", "-c", f'source "{LIB}"; aegis_cp_lock "{root}"'],
                   check=True, cwd=root)


@NO_FS_LOCK
class TestSfCatalogUnderLock:
    """Each SF form, run as a real shell command under an active lock, must
    fail to mutate the CP file — the OS enforces this form-independently."""

    def _assert_blocked(self, root: Path, shell_cmd: str):
        target = root / "hooks" / "lib" / "emit.sh"
        before = target.read_text()
        subprocess.run(["bash", "-c", shell_cmd], capture_output=True, cwd=str(root))
        assert target.read_text() == before, f"CP mutated by: {shell_cmd!r}"

    def test_sf_catalog_all_blocked_under_lock(self):
        tmp = _scratch()
        root = Path(tmp.name)
        try:
            _lock(tmp.name)
            forms = [
                'echo evil > "hoo""ks/lib/emit.sh"',          # SF-001 quote-split
                'echo evil > hooks\\/lib/emit.sh',             # SF-001 backslash
                'cp /etc/hostname hooks/lib/emit.sh',          # plain
                'rm -f hooks/lib/emit.sh',                     # delete (dir write)
                "python3 -c \"open('hook'+chr(115)+'/lib/emit.sh','w').write('x')\"",  # SF-004
                "perl -e \"open(F,'>','hook'.'s'.'/lib/emit.sh'); print F 'x'\"",      # SF-004
            ]
            for f in forms:
                self._assert_blocked(root, f)
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()
```

- [ ] **Step 2: テスト実行**

Run: `python3 -m pytest tests/test_cp_lock_sf_catalog.py -v`
Expected: PASS（lock 下で SF-001/004 含む全形が CP を変更できない）

- [ ] **Step 3: コミット**

```bash
git add tests/test_cp_lock_sf_catalog.py
git commit -F - <<'EOF'
test(moat): prove forms are syscall-blocked while the lock is active

quote-split/backslash/SF-004 interpreter 構築まで含め、lock がアクティブな間は
全形が CP を変更できないことを実走で実証（事故ケースの defense-in-depth 証拠。
敵対 SF-004 の閉鎖ではない＝os.chmod 解錠は別途残る）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 4: contract 登録・version bump・docs・SF disposition 更新

**Files:**
- Modify: `scripts/check_framework_contract.py`（`REQUIRED_HOOK_FILES` に cp-lock 追加・`FRAMEWORK_VERSION` を 1.13.0）
- Modify: `templates/STATUS.template.md`（行 3 `framework_version: "1.13.0"`）
- Modify: `docs/STATUS.md`（live `framework_version: "1.13.0"`）
- Modify: `README.md`（layer-2 のアップグレード注記）・`docs/architecture-overview.md`（hook 表に layer-2 一文）
- Modify: `docs/security-followups.md`（SF-001〜005 の disposition 更新・テスト緑後）
- Test: `tests/test_cp_lock_contract.py`

**Interfaces:**
- Consumes: Task 0 の `hooks/lib/cp-lock.sh` が存在すること。

- [ ] **Step 1: contract 登録テストを書く** — `tests/test_cp_lock_contract.py`

```python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cp_lock_in_required_hook_files():
    text = (ROOT / "scripts" / "check_framework_contract.py").read_text()
    assert 'hooks/lib/cp-lock.sh' in text, \
        "cp-lock.sh must be registered in REQUIRED_HOOK_FILES"


def test_version_is_1_13_0_and_synced():
    contract = (ROOT / "scripts" / "check_framework_contract.py").read_text()
    assert 'FRAMEWORK_VERSION = "1.13.0"' in contract
    tpl = (ROOT / "templates" / "STATUS.template.md").read_text()
    assert 'framework_version: "1.13.0"' in tpl


def test_framework_contract_passes():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_framework_contract.py")],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, f"contract failed:\n{r.stdout}\n{r.stderr}"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_cp_lock_contract.py -v`
Expected: FAIL（cp-lock 未登録・版未 bump）

- [ ] **Step 3a: `scripts/check_framework_contract.py` を編集**

行 24 を変更:
```python
FRAMEWORK_VERSION = "1.13.0"
```

`REQUIRED_HOOK_FILES`（行 131 以降のリスト）に追記（`hooks/lib/safety.sh` 等の lib 群と並べる）:
```python
    ROOT / "hooks/lib/cp-lock.sh",
```

- [ ] **Step 3b: 版の同期**

`templates/STATUS.template.md` 行 3:
```
framework_version: "1.13.0"
```

`docs/STATUS.md` のトップ frontmatter `framework_version`（gate/phase/mode 以外＝Edit 可）:
```
framework_version: "1.13.0"
```

残存する旧版文字列を掃討:
Run: `grep -rn '1\.12\.1' --include='*.py' --include='*.md' --include='*.json' . | grep -v session_history | grep -v docs/plans | grep -v CHANGELOG`
→ ヒットした「現在版を指す」箇所のみ 1.13.0 へ（履歴・過去記録は据置）。

- [ ] **Step 3c: README / architecture-overview に layer-2 注記**

`README.md` の guarantee セクション（"guarantee applies to the path/gate surface..." 付近）に1段落:
```markdown
**Upgrade note (1.13.0):** A second, defense-in-depth layer
(`hooks/lib/cp-lock.sh`) OS-locks the framework control-plane (`chmod -R a-w`)
during non-framework work, keyed on `task_type` at session start. It is additive
and backward-compatible, and is insurance against an undiscovered bypass in the
static hook layer for the *accidental* case — it is not a sandbox (an agent that
runs `chmod +w` / `os.chmod` first can still write).
- The lock **persists on disk** between Claude sessions: while `task_type` is a
  project type, `hooks/`, `scripts/`, `CLAUDE.md`, `.claude/{rules,skills,commands,agents}`
  are read-only in your editor too. They unlock automatically in a `task_type:
  framework` session, or manually via `chmod -R u+w <path>`.
- **Updating the framework** (e.g. `git pull` that rewrites vendored hooks) must
  be done in a `task_type: framework` session, otherwise the write hits EACCES.
- On native Windows `chmod` is a no-op, so layer-1 (the static hooks) remains the
  protection there. Both `.claude/settings.json` and `.claude/settings.local.json`
  are **excluded** from the lock (Claude Code writes permission grants there);
  they stay protected by layer-1.
```

`docs/architecture-overview.md` の hook 表近傍に1行:
```
- layer-2: cp-lock.sh が session-start で task_type 連動の OS write-lock を適用（POSIX/macOS）。
```
**かつ**、`docs/architecture-overview.md` 内の `hooks/lib/*.sh` 件数表記（`lib/ 10` 等）を
**11 に更新**する（cp-lock.sh 追加分）。`test_arch_overview_currency.py` がディスク実数
（`hooks/lib/*.sh` の本数）と一致を要求するため。他にも lib 本数に依存する currency テストが
あれば全て更新（フル suite で確認）。

- [ ] **Step 4: テストが通ることを確認＋フル検証**

Run: `python3 -m pytest tests/test_cp_lock_contract.py -v`
Expected: PASS

Run（全体回帰）: `python3 -m pytest -q`
Expected: 全 PASS（既存 + 新規 4 ファイル）

Run（contract 全 profile）: `python3 scripts/check_framework_contract.py`
Expected: `PASS`

- [ ] **Step 5: `docs/security-followups.md` の disposition 更新（テスト緑後）**

SF-001/002/003/004/005 各項目に追記（**CLOSED へは移さない**・状態行を更新）:
```
- **状態（2026-06-21 更新）**: iteration 35 で layer-2 OS lock を defense-in-depth として
  追加。lock がアクティブな間（POSIX/macOS の project モード）は本形の**事故**書込みが
  syscall で EACCES（test_cp_lock_sf_catalog.py で実証）＝多層保険で軽減。ただし**敵対者は
  `os.chmod` で解錠してから書けるため本項目は CLOSED にしない**（特に SF-004 は静的・OS
  どちらでも敵対閉鎖は原理的に不可）。Windows ネイティブは layer-2 no-op＝layer-1 のみ。
  対応コミット: <Task0-Task4 のレンジ>。
```
「防御の多層化」提言セクション末尾に「案A は iteration 35 で layer-2（事故ケース多層保険）として実装。敵対 sandbox ではない旨を明記」を1行追記。

- [ ] **Step 6: コミット**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md docs/STATUS.md README.md docs/architecture-overview.md docs/security-followups.md tests/test_cp_lock_contract.py
git commit -F - <<'EOF'
chore(moat): register cp-lock in contract, bump 1.13.0, docs + SF disposition

REQUIRED_HOOK_FILES に cp-lock.sh を追加、版を MINOR bump（layer-2 は追加のみ
後方互換）。README/architecture に layer-2 注記（on-disk 永続・framework 更新は
framework mode の注意込み）、security-followups の SF-001..005 を「事故ケース多層
保険・敵対閉鎖ではない」disposition へ更新（CLOSED にはしない）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

## 残課題 / 意図的スコープ外（grill-plan で再検討）

- **lifecycle re-lock（mid-session task_type 反転）**: MVP は default-LOCK＋session-start
  （startup/resume/clear/compact で発火）で吸収。`post-status-audit.sh` への phase 遷移
  re-lock は、毎遷移で `chmod -R` のコストと複雑度に見合わないため**繰延**。残余＝
  「framework session 中に iteration rollover で task_type=feature へ反転し、かつ次の
  session-start が無いまま CP を触る」窓のみ（次 session-start で再 lock）。grill-plan 判断点。
- **macOS `chflags uchg` 硬化**: **採用しない**（grill#1）。uchg は owner-chmod を防ぐが、敵対者は
  `os.chflags(path,0)` を同じ interpreter channel で実行して解錠でき、事故には chmod a-w で十分。
  硬化にならない上に macOS 分岐の複雑度だけ増えるため不採用。
- **rename/move gap**: root を lock しない方針（downstream のユーザー root を縛らない）。
  `mv hooks`/`cp x hooks` は layer-1 deny（Task 2 で固定）＝accepted residual。
- **`chmod -R` の session-start レイテンシ**: `.claude/skills` 等を含む chmod -R が毎
  session-start で走る。実測でボトルネックなら lock 済みマーカーで skip する最適化を検討（YAGNI 監視）。
  reviewer-performance 計測: ローカル SSD で 120 ファイル lock ≈5ms＝許容。**follow-up（要対応・別 iteration）**:
  **NFS/SMB/FUSE などネットワークマウント**では各 chmod が往復になり 200-2000ms/session 増の可能性
  （リモートコンテナ利用が増加中）。`stat -f %T` 等でネットワーク FS を検出したら layer-2 を skip
  する 1 行ガードを将来追加（非ブロッカー）。

## Self-Review（spec 照合・grill 反映後）

- 設計 §目的/価値の射程（事故ケース多層保険・敵対 SF-004 は閉じない）→ Task 0/1（layer-2 実装）＋ Task 3（lock アクティブ時の形非依存阻止＝defense-in-depth 証拠）。
- 設計 §スコープ「chmod-unlock guard は回帰テスト」→ Task 2。
- 設計 §安定 CP セット（settings は両方除外・root 非 lock）→ Task 0 `aegis_cp_paths`＋テスト。
- 設計 §プラットフォーム（Windows no-op・skip／root skip）→ 全テストの `NO_FS_LOCK`（WINDOWS or ROOTUSER）＋session-start warn。
- 設計 §SemVer MINOR 1.13.0 → Task 4。
- 設計 §SF 対応（CLOSED にしない・多層保険）→ Task 3（実証）＋ Task 4 Step 5（記録更新）。
- 設計 §決定事項「単一所有＝cp-lock.sh・platform_manifest 非搭載」→ Task 0（`aegis_cp_paths`）。
- on-disk 永続・framework 更新は framework mode → Task 4 README 注記。
- 未カバーで意図的繰延/不採用: lifecycle re-lock（繰延）・chflags uchg（不採用）（上記「残課題」に明示）。

## grill-plan 反映ログ（2026-06-21）

- **致命#1（SF-004 closure 撤回）**: owner が `os.chmod` で解錠できるため敵対 SF-004 は layer-2 でも閉じない。justification を「事故ケースの独立 syscall 保険」へ書換え（Global Constraints / Task 3 / Task 4 Step 5）。chflags uchg は不採用へ。
- **致命#2（settings lock 回避）**: Claude Code が permission grant を settings（特に .local）へ書く＋本リポは hook 登録が settings.local.json。両 settings を layer-2 除外し layer-1 に委ねる（Global Constraints / Task 0 `aegis_cp_paths`＋テスト）。
- **致命#3（root skip）**: root は a-w を無視。全 lock テストに `NO_FS_LOCK`（WINDOWS or geteuid==0）。
- **要検討#1/#2**: on-disk 永続 read-only・`git pull` は framework mode を README に明記（Task 4 Step 3c）。
