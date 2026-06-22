# moat lifecycle re-lock — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** セッション中に task_type が framework↔非 framework に変わったとき、layer-2 immutable moat の CP lock 状態を自動で再施錠/解錠する。

**Architecture:** lock 判定を `cp-lock.sh::aegis_cp_apply` 1関数に集約（desired 判定→sentinel 安価プローブ→不一致時のみ chmod -R）。`session-start.sh` のインライン判定を同関数に置換し、`post-status-audit.sh`（STATUS 編集で発火）からも呼んでセッション中の再施錠点を作る。post-status-audit を lock トリガ化すると iter36 Bug A（os.chmod の symlink 追従）が再発しうるため、post-status-audit を起動するテスト scaffold の symlink→copy 化を先行する。

**Tech Stack:** bash 3.2（pure-bash・外部依存なし）、Python unittest/pytest。正典設計: `docs/plans/2026-06-22-iter37-moat-relock-design.md`。

**スコープ（ユーザー承認）:** (a) セッション中 task_type 切替の再施錠のみ。(b) クラッシュ窓 default-lock 硬化・PreToolUse 毎ツール再 lock・settings.json lock は **対象外（YAGNI）**。

**実装順の要点:** Task 3（テスト分離ハードニング）を Task 4（post-status-audit を lock トリガ化）より**前**に行う。さもないと Task 4 着地後に既存 `test_phase_skill_injection`（task_type=feature・TemporaryDirectory・check_status.py symlink）が leak する。

---

### Task 1: `aegis_cp_apply` 共有関数（cp-lock.sh）

**Files:**
- Modify: `hooks/lib/cp-lock.sh`（`aegis_cp_unlock` 定義の直後に追記）
- Test: `tests/test_cp_lock_lib.py`

- [ ] **Step 1: 失敗するテストを追記**（`TestCpLock` クラス内、`test_lock_is_idempotent` の後）

```python
    def test_apply_framework_unlocks(self):
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            _bash('aegis_cp_lock "$PWD"', tmp.name)  # start locked
            assert not _can_write(p / "hooks" / "lib" / "util.sh")
            assert _bash('aegis_cp_apply "$PWD" framework', tmp.name).returncode == 0
            assert _can_write(p / "hooks" / "lib" / "util.sh"), "framework => unlock"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_apply_nonframework_locks(self):
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            assert _can_write(p / "hooks" / "lib" / "util.sh")  # fresh = unlocked
            assert _bash('aegis_cp_apply "$PWD" feature', tmp.name).returncode == 0
            assert not _can_write(p / "hooks" / "lib" / "util.sh"), "feature => lock"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_apply_empty_task_type_locks(self):
        # default-lock: 空/未知の task_type は安全側=lock
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            assert _bash('aegis_cp_apply "$PWD" ""', tmp.name).returncode == 0
            assert not _can_write(p / "hooks" / "lib" / "util.sh")
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()

    def test_apply_idempotent_keeps_state(self):
        tmp = _make_scratch(); p = Path(tmp.name)
        try:
            _bash('aegis_cp_lock "$PWD"', tmp.name)  # locked
            assert _bash('aegis_cp_apply "$PWD" feature', tmp.name).returncode == 0
            assert not _can_write(p / "hooks" / "lib" / "util.sh"), "already locked => stays locked"
            _bash('aegis_cp_unlock "$PWD"', tmp.name)  # unlocked
            assert _bash('aegis_cp_apply "$PWD" framework; aegis_cp_apply "$PWD" framework',
                         tmp.name).returncode == 0
            assert _can_write(p / "hooks" / "lib" / "util.sh"), "already unlocked => stays unlocked"
        finally:
            subprocess.run(["chmod", "-R", "u+w", tmp.name]); tmp.cleanup()
```

そして platform-independent（`NO_FS_LOCK` の外、`test_empty_root_is_rejected` の隣）に:

```python
def test_apply_empty_root_is_rejected():
    assert _bash('aegis_cp_apply "" feature', ".").returncode == 1
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest tests/test_cp_lock_lib.py -k apply -v`
Expected: FAIL（`aegis_cp_apply: command not found` 由来で rc≠0 / アサート失敗）

- [ ] **Step 3: 実装**（`hooks/lib/cp-lock.sh`、`aegis_cp_unlock` の閉じ括弧の直後に追記）

```bash
# aegis_cp_apply <root> <task_type> — re-establish the correct CP lock state for the
# CURRENT task_type. framework => unlock; anything else (incl. empty/unknown =>
# default-lock) => lock. Idempotent: a cheap sentinel probe ([ -w <root>/hooks ])
# decides whether a flip is needed so a no-op call avoids a redundant chmod -R.
# rc mirrors the underlying lock/unlock (0 ok / 1 chmod failure); a no-op returns 0.
aegis_cp_apply() {
  local root="$1" task_type="$2" sentinel
  [ -n "$root" ] || return 1
  sentinel="${root}/hooks"
  if [ "$task_type" = "framework" ]; then
    # desired = unlock. Already writable (unlocked) => no-op.
    if [ -e "$sentinel" ] && [ -w "$sentinel" ]; then
      return 0
    fi
    aegis_cp_unlock "$root"
  else
    # desired = lock (default-lock). Already non-writable (locked) => no-op.
    if [ -e "$sentinel" ] && [ ! -w "$sentinel" ]; then
      return 0
    fi
    aegis_cp_lock "$root"
  fi
}
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m pytest tests/test_cp_lock_lib.py -v`
Expected: PASS（全件）

- [ ] **Step 5: commit**

```bash
git add hooks/lib/cp-lock.sh tests/test_cp_lock_lib.py
git commit -F - <<'EOF'
feat(moat): add aegis_cp_apply — idempotent lock state from task_type

cp-lock.sh に共有関数 aegis_cp_apply を新設（desired= framework?unlock:lock、
sentinel [ -w <root>/hooks ] で現状を安価プローブし不一致時のみ chmod -R）。
空/未知 task_type は default-lock。session-start / post-status-audit から共有。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 2: session-start.sh をインライン判定から `aegis_cp_apply` に置換（挙動保存）

**Files:**
- Modify: `hooks/session-start.sh:270-280`
- Test: `tests/test_session_start_injection.py`（lock 状態の挙動保存テストを追加）

- [ ] **Step 1: 失敗するテストを追記**（`tests/test_session_start_injection.py`、`_scaffold` は既に copy 化済み）

```python
    def test_nonframework_locks_control_plane(self):
        import subprocess as sp
        status = STATUS.replace("task_type: feature", "task_type: feature")  # feature = 非 framework
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), status)
            try:
                self._run(root)
                # CP（hooks）は session-start 後に read-only
                w = sp.run(["bash", "-c", f'printf x >> "{root}/hooks/session-start.sh"'],
                           capture_output=True)
                assert w.returncode != 0, "非 framework は CP を lock するべき"
            finally:
                sp.run(["chmod", "-R", "u+w", str(root)])

    def test_framework_unlocks_control_plane(self):
        import subprocess as sp
        status = STATUS.replace("task_type: feature", "task_type: framework")
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), status)
            try:
                sp.run(["chmod", "-R", "a-w", f"{root}/hooks"])  # pre-lock
                self._run(root)
                w = sp.run(["bash", "-c", f'printf x >> "{root}/hooks/session-start.sh"'],
                           capture_output=True)
                assert w.returncode == 0, "framework は CP を unlock するべき"
            finally:
                sp.run(["chmod", "-R", "u+w", str(root)])
```

注: root/Windows では chmod write-bit が no-op。これらは現状の `test_session_start_injection.py` の他テスト同様にローカル（非 root）で意味を持つ。CI が root の場合は別途 skip マーカーを付与（`os.geteuid()==0` ガード）。実装時に test_cp_lock_lib の `ROOTUSER` 判定を流用して `@pytest.mark.skipif` を付ける。

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest tests/test_session_start_injection.py -k control_plane -v`
Expected: 現状のインライン実装でも PASS する可能性が高い（挙動保存テスト）。**この Task は挙動保存リファクタなので RED は「リファクタ後も GREEN のまま」を保証するためのもの**。先にテストを足し GREEN を確認 → Step 3 でリファクタ → 再 GREEN（不変）を確認する。

- [ ] **Step 3: session-start.sh をリファクタ**

`hooks/session-start.sh:270-280` の現行ブロック:

```bash
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

を次に置換（判定は不変＝framework→unlock / 他→lock。共有関数に一本化）:

```bash
if command -v aegis_cp_apply >/dev/null 2>&1; then
  aegis_cp_apply "$ROOT" "$TASK_TYPE" || CONTEXT="${CONTEXT} | [WARNING] control-plane lock/unlock 一部失敗（layer-2 未適用・layer-1 静的 moat は有効。framework 編集が EACCES なら該当ファイルを手動 chmod u+w）"
else
  CONTEXT="${CONTEXT} | [WARNING] cp-lock.sh 利用不可（layer-2 OS lock skip・layer-1 静的 moat は有効）"
fi
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m pytest tests/test_session_start_injection.py tests/test_phase_skills_lib.py -v`
Expected: PASS（挙動保存・既存 injection テストも不変）

- [ ] **Step 5: commit**

```bash
git add hooks/session-start.sh tests/test_session_start_injection.py
git commit -F - <<'EOF'
refactor(moat): session-start uses aegis_cp_apply (behavior-preserving)

lock 判定を共有関数に一本化（framework→unlock / 他→lock は不変）。
session-start と post-status-audit のロジック重複＝ドリフトを構造的に排除。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 3: post-status-audit を起動するテストの分離ハードニング（symlink→copy・先行必須）

**目的:** Task 4 で post-status-audit が lock トリガになる前に、これを起動するテスト scaffold が実リポファイルを symlink していないことを保証する（iter36 Bug A の再発防止）。

**Files:**
- Modify: `tests/test_phase_skill_injection.py:61`（known leak: task_type=feature・TemporaryDirectory・check_status.py symlink）
- Audit/Modify: 下記 triage で判明した他の post-status-audit 起動テスト

- [ ] **Step 1: triage — repo を破壊しうるテストを列挙（grill-plan で精緻化済み）**

**前提（重要）**: cp_apply は post-status-audit の `source ${SCRIPT_DIR}/lib/cp-lock.sh` が成功して初めて定義される。よって **scratch に cp-lock.sh が存在するときだけ lock が発火する**＝scratch が **full hooks/ を copytree** したテストのみが対象。`hooks/lib` を**選択的に symlink** する scaffold（例 `test_check_status.py::TempProjectWithHooks`・`test_failure_policy.py:210`）は cp-lock.sh を含まない → cp_apply 未定義 → **lock しない＝安全**（grill 初版で TempProjectWithHooks を危険視したが、cp-lock.sh 不在のため非該当と確認）。

**repo 破壊の 4 条件（AND）**:
1. scratch が **full `hooks/` を copytree**（cp-lock.sh が存在 → cp_apply が発火しうる）
2. かつ `symlink_to(ROOT/...)` で**実リポファイル**（scripts/check_status.py 等）を scratch に張る
3. かつ post-status-audit（または session-start）を **task_type≠framework（空含む）** で起動 → scratch を lock
4. かつ cleanup が `with tempfile.TemporaryDirectory()`（resetperms=os.chmod が symlink を辿る。`mkdtemp + rmtree(ignore_errors=True)` は辿らない＝安全）

Run（再検証用）:
```bash
for f in $(grep -rln "copytree.*hooks\b\|copytree(ROOT / \"hooks\")" tests/); do
  echo "=== $f ==="; grep -n "symlink_to(ROOT\|symlink_to(HOOKS\|session-start\|post-status-audit\|task_type\|TemporaryDirectory" "$f"
done
```

**確定該当（修正必須）**: `tests/test_phase_skill_injection.py`（full hooks copytree:59・check_status.py symlink:61・post-status-audit:68・task_type=feature:19・TemporaryDirectory）。**これが唯一の repo 破壊ケース。**
**非該当（確認済み・修正不要）**: `TempProjectWithHooks`（cp-lock.sh 不在）／`test_failure_policy.py:210`（hooks/lib 選択 symlink・cp-lock.sh 不在）／`test_hook_output_schema.py:1429/1508`（deploy-gate・post-status-audit 非起動）／`test_session_start_injection.py`・`test_phase_skills_lib.py`（iter36 で copy2 済み）。

- [ ] **Step 2: 失敗する回帰ガードを追加**（`tests/test_phase_skill_injection.py`、`TestPhaseTransitionInjection` 内）

```python
    def test_scaffold_check_status_is_regular_file_not_symlink(self):
        # Regression: post-status-audit が lock トリガになった後、scratch に symlink した
        # 実 check_status.py を cleanup の resetperms(os.chmod) が辿って実ファイルを破壊する
        # （iter36 Bug A）。_scaffold は copy しなければならない。
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp))
            cs = root / "scripts" / "check_status.py"
            self.assertTrue(cs.is_file(), "scaffold must provide check_status.py")
            self.assertFalse(cs.is_symlink(), "must copy, not symlink, the real check_status.py")
```

- [ ] **Step 3: RED 確認**

Run: `python3 -m pytest tests/test_phase_skill_injection.py -k not_symlink -v`
Expected: FAIL（現状 symlink なので `is_symlink()` True → `assertFalse` 失敗）

- [ ] **Step 4: symlink→copy 化**（`tests/test_phase_skill_injection.py:61`）

現行:
```python
        (d / "scripts" / "check_status.py").symlink_to(ROOT / "scripts" / "check_status.py")
```
を:
```python
        # COPY (not symlink): Task 4 以降 post-status-audit が scratch を lock するため、
        # cleanup の resetperms(os.chmod) が symlink を辿って実 check_status.py を破壊する
        # （iter36 Bug A）。copy なら cleanup の chmod はコピーに当たり実ファイル不変。
        shutil.copy2(ROOT / "scripts" / "check_status.py",
                     d / "scripts" / "check_status.py")
```
triage で他に該当が出たら同様に copy 化＋同型の回帰ガードを追加する。

- [ ] **Step 5: GREEN 確認**

Run: `python3 -m pytest tests/test_phase_skill_injection.py -v`
Expected: PASS

- [ ] **Step 6: commit**

```bash
git add tests/test_phase_skill_injection.py
git commit -F - <<'EOF'
test(moat): copy (not symlink) real check_status.py in post-status-audit scaffolds

Task 4 で post-status-audit を lock トリガ化する前段。symlink + scratch lock +
TemporaryDirectory cleanup(resetperms=os.chmod が symlink 追従) で実ファイルが
破壊される iter36 Bug A の再発を防ぐ。回帰ガード追加。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 4: post-status-audit.sh からセッション中再施錠を発火（TDD）

**Files:**
- Modify: `hooks/post-status-audit.sh`（source 追加＋STATUS 存在確認直後に cp_apply）
- Test: `tests/test_cp_relock_integration.py`（新規）

- [ ] **Step 1: 失敗する統合テストを新規作成**（`tests/test_cp_relock_integration.py`）

```python
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0
NO_FS_LOCK = pytest.mark.skipif(
    sys.platform.startswith("win") or ROOTUSER,
    reason="chmod write-bit is a no-op on native Windows / bypassed by root")

STATUS_TMPL = """---
framework: aegis
mode: Dev
phase: implement
task_type: {tt}
gate_approvals:
  plan: approved
---
"""


def _scaffold(d: Path, task_type: str) -> Path:
    (d / "docs").mkdir()
    (d / "docs" / "STATUS.md").write_text(STATUS_TMPL.format(tt=task_type), encoding="utf-8")
    (d / ".claude").mkdir()
    shutil.copytree(ROOT / "hooks", d / "hooks")
    (d / "scripts").mkdir()
    # COPY (not symlink) — never symlink real repo files into a lockable scratch.
    shutil.copy2(ROOT / "scripts" / "check_status.py", d / "scripts" / "check_status.py")
    return d


def _run_audit(root: Path) -> None:
    import json
    payload = json.dumps({"tool_name": "Edit",
                          "tool_input": {"file_path": str(root / "docs" / "STATUS.md")}})
    subprocess.run(["bash", str(root / "hooks" / "post-status-audit.sh")],
                   input=payload, capture_output=True, text=True, timeout=60,
                   env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)})


def _can_write(p: Path) -> bool:
    return subprocess.run(["bash", "-c", f'printf x >> "{p}"'],
                          capture_output=True).returncode == 0


@NO_FS_LOCK
def test_status_edit_to_nonframework_relocks():
    with tempfile.TemporaryDirectory() as tmp:
        root = _scaffold(Path(tmp), "feature")
        try:
            subprocess.run(["chmod", "-R", "u+w", f"{root}/hooks"])  # start unlocked
            assert _can_write(root / "hooks" / "session-start.sh")
            _run_audit(root)
            assert not _can_write(root / "hooks" / "session-start.sh"), \
                "非 framework への STATUS 編集で post-status-audit が再 lock するべき"
        finally:
            subprocess.run(["chmod", "-R", "u+w", str(root)])


@NO_FS_LOCK
def test_status_edit_to_framework_unlocks():
    with tempfile.TemporaryDirectory() as tmp:
        root = _scaffold(Path(tmp), "framework")
        try:
            subprocess.run(["chmod", "-R", "a-w", f"{root}/hooks"])  # start locked
            assert not _can_write(root / "hooks" / "session-start.sh")
            _run_audit(root)
            assert _can_write(root / "hooks" / "session-start.sh"), \
                "framework への STATUS 編集で post-status-audit が unlock するべき"
        finally:
            subprocess.run(["chmod", "-R", "u+w", str(root)])
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m pytest tests/test_cp_relock_integration.py -v`
Expected: FAIL（post-status-audit はまだ cp_apply を呼ばないので lock 状態が変わらない）

- [ ] **Step 3: post-status-audit.sh を実装**

(3a) source ブロック（`hooks/post-status-audit.sh:29` の `source ".../phase-skills.sh"` の直後）に追加:
```bash
# layer-2 cp-lock lib (optional — absent in minimal scaffolds).
[ -r "${SCRIPT_DIR}/lib/cp-lock.sh" ] && source "${SCRIPT_DIR}/lib/cp-lock.sh" 2>/dev/null || true
```

(3b) STATUS 存在確認（`if [ ! -f "$STATUS_FILE" ]; then emit_allow; exit 0; fi` の閉じ `fi`、現 `:55`）の**直後**に挿入:
```bash
# layer-2 lifecycle re-lock: a mid-session task_type change (framework <-> other)
# must re-establish the correct CP lock state. chmod side-effect only — never
# emits and never alters the audit decision below; || true keeps it non-fatal
# under set -e. Runs on every STATUS edit where STATUS is readable (incl. the
# snapshot-missing / tamper exit paths below — re-lock is independent of them).
if command -v aegis_cp_apply >/dev/null 2>&1; then
  _AEGIS_TT=$(frontmatter_value "$STATUS_FILE" "task_type" || true)
  aegis_cp_apply "$ROOT" "$_AEGIS_TT" || true
fi
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m pytest tests/test_cp_relock_integration.py tests/test_phase_skill_injection.py -v`
Expected: PASS（再施錠が効く・既存 post-status-audit テストも copy 化済みで leak しない）

- [ ] **Step 5: 既存 post-status-audit テスト群の不変確認（lock+cleanup を新たに経由する full-hooks テスト含む）**

Run: `python3 -m pytest tests/test_check_status.py tests/test_hook_output_schema.py tests/test_snapshot_atomic.py tests/test_snapshot_consumer_policy.py tests/test_safety_lib_missing.py -v`
Expected: PASS（gate-tamper 監査・phase-skills injection・snapshot ポリシーは不変。cp_apply は emit に非干渉）。

注（grill-plan）: `test_snapshot_atomic.py`・`test_snapshot_consumer_policy.py`・`test_safety_lib_missing.py` は **full hooks copytree＋task_type=feature** だが**実リポを symlink しない**＝repo 破壊なし。ただし Task 4 以降は post-status-audit が scratch を lock するため、これらは初めて lock+cleanup 経路を通る。cp-lock は STATUS.md / .gate-snapshot を除外（runtime-state は writable 維持）なので assertion は不変のはずだが、(1) これらが GREEN を保つこと、(2) TemporaryDirectory cleanup が locked scratch を resetperms で正常削除し locked litter を残さないこと、を本 Step で確認する。万一 FAIL するなら、当該テストの cleanup を `finally: chmod -R u+w` で明示 unlock してから cleanup する（test_cp_lock_lib のパターン）。

- [ ] **Step 6: commit**

```bash
git add hooks/post-status-audit.sh tests/test_cp_relock_integration.py
git commit -F - <<'EOF'
feat(moat): re-lock control-plane on mid-session task_type change

post-status-audit.sh が STATUS 編集時に aegis_cp_apply を呼び、framework↔非
framework の切替で CP lock 状態を再確立。emit には非干渉（chmod 副作用のみ・
|| true で非致命）。session-start 単独だった lock ライフサイクルの穴を閉じる。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 5: framework_version バンプ＋契約整合

**Files:**
- Modify: framework_version の単一 owner（実装時に特定）＋同期参照
- Test: `scripts/check_framework_contract.py`（既存・実行のみ）

- [ ] **Step 1: version owner を特定**

Run:
```bash
grep -rn "1\.13\.0" scripts/ hooks/ README.md docs/STATUS.md
```
owner（定数定義箇所）と参照（同期先）を区別する。Summary 記載どおり version owner は一本化済み＝owner を 1 箇所変更し、契約テストで同期を検証する。

- [ ] **Step 2: minor バンプ 1.13.0 → 1.14.0**

moat に新しい保護トリガ（セッション中再施錠）を追加する behavioral change＝minor バンプ。owner を `1.14.0` に更新し、参照側（STATUS.md `framework_version` 等）が owner 参照型でなく直書きなら同時更新する。

- [ ] **Step 3: 契約整合の確認**

Run: `python3 scripts/check_framework_contract.py`
Expected: `PASS: aegis contract is aligned`

注: バンプの要否は判断事項。grill-plan / review で過剰なら patch 据置に差し戻し可。iter35（moat 新設）が 1.13.0 だったため、その lifecycle 拡張は minor が一貫。

- [ ] **Step 4: commit**

```bash
git add -A
git commit -F - <<'EOF'
chore(moat): bump framework_version 1.13.0 -> 1.14.0 (re-lock lifecycle)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

### Task 6: フルスイート緑＋分離不変条件＋クローズアウト

**Files:**
- Modify: `docs/LEARNINGS.md`、`docs/STATUS.md`

- [ ] **Step 1: フルスイート＋ mode 不変条件＋ git バックストップ（grill-plan #2）**

Run:
```bash
echo "pre: $(stat -f '%Sp' scripts/check_status.py)"; \
python3 -m pytest tests/ -q 2>&1 | tail -4; \
echo "post: $(stat -f '%Sp' scripts/check_status.py)"; \
echo "=== git backstop (tracked-file mode flip catch-all) ==="; git status --porcelain
```
Expected:
- 全件 PASS（1 skip 許容）
- pre/post とも `-rw-r--r--`（check_status.py 644 維持）
- **`git status --porcelain` が空**（コミット済み状態なら）。これが triage 漏れの**真のバックストップ**: leak は実ファイルを 0o700 化＝**exec ビットを立てる**ため、git は tracked file の mode flip（100644→100755）を検出する。check_status.py 単体 stat では捕えられない scripts/ dir や hooks/lib/*.sh への波及も、git は mode 変化として表面化させる（このタイミングで未コミットがある場合は `git diff --summary` で `mode change` 行が無いことを確認）。
- **いずれか崩れたら** iteration FAIL 扱い → triage（Task 3 Step 1）に戻り、漏れた full-hooks×symlink テストを copy 化する。

- [ ] **Step 2: 契約＋ status_doctor**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/status_doctor.py --root .`
Expected: 両方 PASS

- [ ] **Step 3: LEARNINGS 追記**

`docs/LEARNINGS.md` のフレームワーク改善カテゴリに（confidence 付き）:
```markdown
- [confidence:8] moat の lock ライフサイクルは「lock を決める単一関数（aegis_cp_apply）＋複数の発火点（session-start＋post-status-audit）」に分けると、判定ドリフトなく再施錠点を増やせる。発火点を増やすときは、その hook を起動する全テスト scaffold が実リポを symlink していないか（lock×TemporaryDirectory cleanup で iter36 Bug A 再発）を必ず再監査する。
```

- [ ] **Step 4: STATUS 更新（gate は update-gate.sh 経由・直接編集禁止）**

`docs/STATUS.md` の `phase` を `review` に進め（review ゲート承認直前）、`next_action`・`last_updated` を更新。session_history は review ゲート承認/コミット時に追記（max 3＝必要なら古い 1 件を `docs/evidence-archive.md` へ退避）。

- [ ] **Step 5: commit（テスト緑記録は record-test-result 経由）**

```bash
python3 scripts/record-test-result.py --root . "python3 -m pytest tests/ -q"
git add docs/LEARNINGS.md docs/STATUS.md
git commit -F - <<'EOF'
docs(moat): iteration 37 closeout — re-lock lifecycle LEARNINGS + STATUS

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
```

---

## ゲート（実装後）

- **grill-code**（実装後・必須）→ 指摘を全消し。
- **review**（必須・judge 🟢＋盲検第2意見）/ **qa**（必須）/ **security**（必須・moat 変更につき正規実施＝lock 中 CP への実走・再施錠の adversarial 確認）。M のため **deploy skip**。
- ref は承認直前に設定（pending+ref で STATUS 検証テスト赤化）。
- push は yuuya-miyagaki。

## Self-Review（plan 内チェック）

- **spec coverage**: design の ①共有関数=Task1 / ②session-start 置換=Task2 / ③重大エッジ(test 分離)=Task3 / ④post-status-audit 発火=Task4 / テスト=各 Task / 規模・ゲート=末尾。網羅。
- **placeholder**: triage（Task3 Step1・Task5 Step1）はコマンドと判定基準を明示＝investigation task として具体。
- **type consistency**: `aegis_cp_apply <root> <task_type>` のシグネチャは Task1 定義と Task2/4 呼び出しで一致。sentinel=`<root>/hooks`（Task1 実装と整合）。
