# 実装計画 — iter63: setup.sh self-heal unlock（R3・v1.24.0）

> 設計正本: docs/specs/2026-07-07-iter63-setup-self-heal-design.md
> 動機正本: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R3・§4 Phase 0-3
> 実再現ログ: locked＋stale hook → `bash bin/setup.sh` = rc=1・`cp: …/hooks/check-gate.sh: Permission denied`（2026-07-07 本セッション）。
> **重要な再現知見**: 同一内容の再 install は `copy_file_force` の `cmp -s` で cp 前に
> no-op になるため死なない。故障は「配布物に差分がある実 upgrade」でのみ顕在化。
> 回帰テストは必ず **stale 化 → lock → 再実行** の順。

## タスク分解（TDD: Task 1 が RED → Task 2/3 で GREEN）

### Task 1: 回帰テスト新設（RED 先行）

新規 `tests/test_setup_locked_target_upgrade.py`。4 テスト中 3 が現状 RED、
T2 のみ既存挙動の回帰ピン（現状 green）。

```python
"""iter63 R3: a locked install (cp-lock chmod a-w) must not kill the documented
upgrade path (re-run bin/setup.sh). setup.sh self-heals: it unlocks via the
framework's own cp-lock lib, gated on an aegis-install marker AND an actual
lock finding, so a random read-only --target dir is never touched. Opt-out
AEGIS_SETUP_SELFHEAL=off fails closed with an attributed error.
Repro insight: an IDENTICAL re-install never fails (copy_file_force cmp -s
short-circuits before cp) — the regression only shows on a DIFFERING framework
file, so every locked-upgrade test stales a hook first."""
import os
import pathlib
import stat
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
# chmod a-w does not bind root (repo convention: test_cp_lock_lib.py etc.) —
# every test that relies on lock semantics must skip as root.
ROOTUSER = hasattr(os, "geteuid") and os.geteuid() == 0


def _run(target, profile="standard", env_extra=None, check=False):
    env = dict(os.environ)
    env.pop("AEGIS_SETUP_SELFHEAL", None)  # shell leakage must not flip tests
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(ROOT / "bin/setup.sh"),
         f"--profile={profile}", f"--target={target}"],
        capture_output=True, text=True, env=env, check=check)


def _lock(target):
    subprocess.run(
        ["bash", "-c",
         f'source "{ROOT}/hooks/lib/cp-lock.sh" && aegis_cp_lock "{target}"'],
        check=True, capture_output=True, text=True)


def _unlock_all(path):
    # teardown: pytest's tmp cleanup must never fight a-w dirs left by a
    # failing assertion mid-test.
    subprocess.run(["chmod", "-R", "u+w", str(path)], capture_output=True)


@pytest.mark.skipif(ROOTUSER, reason="chmod a-w does not bind root")
def test_locked_upgrade_self_heals(tmp_path):
    target = tmp_path / "proj"
    try:
        _run(str(target), check=True)
        hook = target / "hooks" / "check-gate.sh"
        hook.write_text("#!/usr/bin/env bash\n# STALE\nexit 0\n")
        _lock(str(target))
        r = _run(str(target))
        assert r.returncode == 0, r.stderr
        assert "OS-locked" in r.stdout            # NOTE printed
        assert "next session start" in r.stdout   # re-lock deferral pinned
        assert hook.read_text() == (ROOT / "hooks" / "check-gate.sh").read_text()
        assert list((target / "hooks").glob("check-gate.sh.bak.*"))
        assert os.access(str(target / "hooks"), os.W_OK)  # left unlocked by design
    finally:
        _unlock_all(tmp_path)


def test_fresh_install_prints_no_unlock_note(tmp_path):
    target = tmp_path / "proj"
    r = _run(str(target))
    assert r.returncode == 0, r.stderr
    assert "OS-locked" not in r.stdout


@pytest.mark.skipif(ROOTUSER, reason="chmod a-w does not bind root")
def test_selfheal_off_fails_closed_with_attribution(tmp_path):
    target = tmp_path / "proj"
    try:
        _run(str(target), check=True)
        hook = target / "hooks" / "check-gate.sh"
        hook.write_text("#!/usr/bin/env bash\n# STALE\nexit 0\n")
        _lock(str(target))
        r = _run(str(target), env_extra={"AEGIS_SETUP_SELFHEAL": "off"})
        assert r.returncode != 0
        assert "cp-lock" in r.stderr
        assert "AEGIS_SETUP_SELFHEAL" in r.stderr
        assert not os.access(str(target / "hooks"), os.W_OK)  # lock untouched
    finally:
        _unlock_all(tmp_path)


@pytest.mark.skipif(ROOTUSER, reason="chmod a-w does not bind root")
def test_non_aegis_readonly_target_is_not_unlocked(tmp_path):
    target = tmp_path / "proj"
    hooks = target / "hooks"
    hooks.mkdir(parents=True)
    hooks.chmod(0o555)  # user-made read-only dir; NO aegis markers exist
    try:
        r = _run(str(target))
        assert r.returncode != 0
        assert "cp-lock" in r.stderr              # remedy is still explained
        mode = stat.S_IMODE(hooks.stat().st_mode)
        assert mode == 0o555                      # perms untouched (no unlock)
    finally:
        _unlock_all(tmp_path)
```

RED 確認コマンド（期待: T1/T3/T4 = FAIL・T2 = PASS）:
`python3 -m pytest tests/test_setup_locked_target_upgrade.py -v`

### Task 2: self-heal 関数＋main 呼び出し（bin/setup.sh）

`create_framework_baseline` 定義群の後・`INSTALLED_PATHS=()` の前に追加:

```bash
# R3 (iter63): self-heal the OS-lock before copying. cp-lock (moat layer-2)
# chmod a-w's the stable CP at session-start for non-framework task types —
# so the DOCUMENTED upgrade path (status_doctor: "Re-run bin/setup.sh") died
# with `cp: Permission denied` on every install that had ever been used.
# Gated on BOTH (a) an aegis-install marker and (b) an actual lock finding
# (aegis_cp_verify), so a random --target dir with its own read-only hooks/
# is never chmod'd. Re-lock is intentionally NOT done here: the target's next
# session-start (aegis_cp_apply) restores the right state for its task_type;
# the NOTE keeps the unlocked window visible. AEGIS_SETUP_SELFHEAL=off
# (lowercase, AEGIS_NUDGE convention) disables the heal — a locked target then
# fails CLOSED with the attributed error from explain_unwritable_dst.
selfheal_unlock_target() {
  local target="$1"
  if [ "${AEGIS_SETUP_SELFHEAL:-on}" = "off" ]; then
    return 0
  fi
  if [ ! -f "$target/.claude/.aegis-install-version" ] \
     && [ ! -f "$target/hooks/lib/cp-lock.sh" ]; then
    return 0
  fi
  local cplib="$FRAMEWORK_ROOT/hooks/lib/cp-lock.sh"
  if [ ! -f "$cplib" ]; then
    echo "  WARNING: hooks/lib/cp-lock.sh missing in framework; cannot self-heal OS-lock" >&2
    return 0
  fi
  # shellcheck source=/dev/null
  source "$cplib"
  # aegis_cp_verify: rc1 = findings — must not abort under set -e.
  local locked
  locked=$(aegis_cp_verify "$target" framework 2>/dev/null) || true
  [ -n "$locked" ] || return 0
  if aegis_cp_unlock "$target"; then
    echo "  NOTE: target was OS-locked (aegis cp-lock); write access restored for this upgrade."
    echo "        The lock re-engages at the target's next session start."
  else
    echo "  WARNING: could not fully unlock the OS-locked control plane; copies below may fail." >&2
  fi
}
```

main 側（`echo ""` の直後・`--- Required files ---` の前）:

```bash
# R3 (iter63): heal an OS-locked install before any copy (details at the
# function definition).
selfheal_unlock_target "$TARGET"
```

### Task 3: 帰属エラー（bin/setup.sh の copy 経路）

ヘルパー（`resolve_source` の前に追加）:

```bash
# R3 (iter63): attributed abort for an unwritable destination. Under set -e a
# failed cp used to kill the install with only cp's one-line stderr — no
# cause, no remedy, and a mixed-version tree left behind. Attribute the
# OS-lock only when the evidence points at it (dst or its parent dir is
# non-writable); any other failure stays a generic error (no false blame).
explain_unwritable_dst() {
  local dst="$1" why="" d
  if [ -e "$dst" ] && [ ! -w "$dst" ]; then
    why="$dst is not writable"
  else
    # A deep `mkdir -p` failure (creating hooks/lib inside a read-only hooks/)
    # leaves the IMMEDIATE parent non-existent — walk up to the nearest
    # EXISTING ancestor and test that (grill-plan 致命1).
    d="$(dirname "$dst")"
    while [ ! -d "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]; do
      d="$(dirname "$d")"
    done
    if [ -d "$d" ] && [ ! -w "$d" ]; then
      why="directory $d is not writable"
    fi
  fi
  echo "ERROR: copy failed: $dst" >&2
  if [ -n "$why" ]; then
    echo "       $why — likely the aegis OS-lock (hooks/lib/cp-lock.sh, chmod a-w) or a read-only target." >&2
    echo "       setup.sh self-heals the OS-lock unless AEGIS_SETUP_SELFHEAL=off was set;" >&2
    echo "       re-run without it, or unlock manually: source hooks/lib/cp-lock.sh && aegis_cp_unlock <target>" >&2
  fi
}
```

`copy_file` の末尾 2 行を置換:

```bash
  if ! mkdir -p "$(dirname "$dst")"; then
    explain_unwritable_dst "$dst"
    exit 1
  fi
  if ! cp "$src" "$dst"; then
    explain_unwritable_dst "$dst"
    exit 1
  fi
```

`copy_file_force` の `mkdir -p` / `cp -f` も同型に置換。
（`.bak` cp は現状維持: copy_file 側は既存の abort 文言が正・copy_file_force 側は
best-effort `|| true` が D3 仕様。）

### Task 4: GREEN 確認 → 対象スイート → full suite

1. `python3 -m pytest tests/test_setup_locked_target_upgrade.py -v` → 4 PASS
2. `bash -n bin/setup.sh`（構文）
3. setup 系回帰: `python3 -m pytest tests/test_setup_upgrade_overwrite.py tests/test_setup_distribution.py tests/test_setup_failclosed.py tests/test_setup_baseline.py tests/test_setup_prereq.py tests/test_setup_arg_version.py tests/test_setup_broken_settings.py tests/test_permission_allowlist_install.py tests/test_full_profile_runnable_scripts.py -q`
4. full: `python3 -m pytest tests/ -q`（record は qa フェーズで）

## grill-plan で検証してほしい確定事項

- `set -euo pipefail` 下の受け方: `locked=$(aegis_cp_verify …) || true` ／
  `if aegis_cp_unlock …` ／ `if ! cp …` — 素の呼び出しで abort しない形か。
- BSD/GNU `cp -f` の unlink 意味論: locked **dir** では unlink も死ぬ（再現済）。
  locked file＋unlocked dir は cp -f が置換に成功し得る（自己解決・問題なし）。
- T4 の前提: standard profile は required（CLAUDE.md/docs 系）成功後、
  hooks/lib の `mkdir -p` で死ぬ（hooks dir a-w）→ rc≠0 ＋帰属 stderr。
- teardown `chmod -R u+w` で pytest tmp cleanup が壊れない。
- 発火ゲート AND 条件（marker ∧ verify findings）で無関係 dir 副作用ゼロ。

## qa フェーズ（B1 drill）方針

- 実 drill（skip なし）。mutant 候補（~1/changed hunk・`bash -n` 通過の意味変異）:
  1. selfheal ゲート反転: `= "off"` → `!= "off"`（heal 全停止）→ T1 が catch
  2. marker ガード削除相当: `! -f …aegis-install-version` 条件を常真化 → T4 が catch
  3. `aegis_cp_unlock` 呼び出しを no-op 化 → T1 が catch
  4. 帰属メッセージの cp-lock 行削除 → T3/T4 が catch
  5. テスト側 assert 反転系は generator 準拠で
- test_command: `python3 -m pytest tests/test_setup_locked_target_upgrade.py -q`
- drill 後は pyc 汚染対策として full suite を**再実走してから** record（iter62 教訓）。

## ship フェーズ

- version bump 3箇所（iter62 実績 `git show 5df536b` で確定済み）:
  ①`scripts/check_framework_contract.py:24` FRAMEWORK_VERSION
  ②`docs/STATUS.md` frontmatter `framework_version`
  ③`templates/STATUS.template.md:3` `framework_version`。
  v1.23.0 → **v1.24.0（MINOR）**。
- `docs/handover/TO-CLIENT.md` の iter63 行を完了に更新。

## リスク・残余（設計書 §セキュリティ考慮の要約）

- unlock 窓（upgrade 完了〜次回 session-start）: layer-2 の脅威モデル（偶発書込み）
  内では小。NOTE で可視。
- エージェントによる setup.sh 経由の意図的 unlock: 任意スクリプト実行と等価・
  owner chmod が常に可能なことと等価＝残余受容（security レポートに明記）。
- 旧版 cp-lock との path 集合ドリフト: self-heal は framework 現行の
  `aegis_cp_paths` 集合で unlock する。将来集合を狭めた場合の取りこぼしは
  **帰属エラーが安全網**として顕在化させる（silent 死には戻らない）。

## grill-plan 反映簿記（2026-07-07）

- 致命1: explainer の親 dir 判定を「最近傍の実在祖先」遡りに修正（深い mkdir -p
  失敗で帰属が沈黙し T4 が実装後も FAIL する地雷）。→ Task 3 に反映済み。
- 致命2: ROOTUSER skipif（repo 慣習 test_cp_lock_lib.py:15 と同型）を T1/T3/T4 に
  追加（root は chmod a-w に拘束されず T3/T4 が偽 FAIL）。→ Task 1 に反映済み。
- 致命3: bump 3箇所目を templates/STATUS.template.md:3 と確定（先送り排除）。
  → ship 節に反映済み。
- 要検討1: `_run` で環境残留の AEGIS_SETUP_SELFHEAL を pop（env 汚染防御）。
  → Task 1 に反映済み。要検討2（path 集合ドリフト）→ リスク節に受容明記。
