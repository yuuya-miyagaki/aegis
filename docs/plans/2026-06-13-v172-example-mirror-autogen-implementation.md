# example ミラー自動生成 実装計画（P3-A / v1.7.2）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `scripts/sync_example_mirror.py` と `make example` で root のミラー制御ファイルを `examples/minimal-project/` へ自動同期し、手動 cp の保守税を消す（安全網は非破壊）。

**Architecture:** 生成器は `check_reference_drift` から `MIRROR_DIRS/MIRROR_FILES/MIRROR_ALLOWLIST` を import（生成と検証が同一マニフェスト共有）。root→example を `shutil.copy2`（mode 保持）、allowlist skip、MIRROR_DIRS 配下の stale を除去。検証は既存 `check_mirror_identity`（drift）に委任。

**Tech Stack:** Python 3（標準ライブラリのみ: shutil/pathlib/sys）、Make。

設計書: `docs/plans/2026-06-13-example-mirror-autogen-design.md`

---

## File Structure

- `scripts/sync_example_mirror.py` — 同期エンジン（`sync_mirror(root)` 関数＋`main()`）。新規。
- `Makefile` — `make example` ターゲット（スクリプトを呼ぶだけ）。新規。
- `tests/test_sync_example_mirror.py` — `sync_mirror` の単体テスト。新規。
- `README.md` — dev/メンテ手順に `make example` を1文追記。
- 版数4箇所（v1.7.1→v1.7.2）。

---

## Task 1: sync_example_mirror.py（同期エンジン）

**Files:**
- Create: `scripts/sync_example_mirror.py`
- Test: `tests/test_sync_example_mirror.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/test_sync_example_mirror.py` を新規作成:

```python
#!/usr/bin/env python3
"""scripts/sync_example_mirror.py の単体テスト（P3-A）。

実マニフェスト（check_reference_drift の MIRROR_DIRS 等）を使い、fake root +
example レイアウトに対して sync_mirror の copy / allowlist skip / stale 除去 /
mode 保持 / 冪等を検証する。実 repo は変更しない。"""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_example_mirror import sync_mirror  # noqa: E402


def _write(p: Path, text: str, *, executable: bool = False) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if executable:
        p.chmod(p.stat().st_mode | stat.S_IXUSR)


class TestSyncMirror(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        # root 側の制御ファイル
        _write(d / "hooks" / "foo.sh", "#!/bin/sh\necho NEW\n", executable=True)
        _write(d / ".claude" / "skills" / "x" / "SKILL.md", "---\nname: x\n---\n")
        _write(d / ".claude" / "commands" / "validate.md", "ROOT validate\n")
        # example 側
        ex = d / "examples" / "minimal-project"
        _write(ex / "CLAUDE.md", "PROJECT-SPECIFIC\n")  # 分岐（MIRROR_DIRS 外）
        _write(ex / ".claude" / "commands" / "validate.md", "EXAMPLE validate\n")  # allowlist
        _write(ex / "hooks" / "stale.sh", "#!/bin/sh\necho OLD\n")  # root に無い stale
        return d

    def test_copies_mirror_file_byte_identical(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            src = (root / "hooks" / "foo.sh").read_bytes()
            dst = (root / "examples" / "minimal-project" / "hooks" / "foo.sh").read_bytes()
            self.assertEqual(src, dst)

    def test_preserves_executable_mode(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            dst = root / "examples" / "minimal-project" / "hooks" / "foo.sh"
            self.assertTrue(os.access(dst, os.X_OK), "executable bit must be preserved")

    def test_allowlist_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            v = (root / "examples" / "minimal-project" / ".claude" / "commands" / "validate.md").read_text()
            self.assertEqual(v, "EXAMPLE validate\n", "allowlisted file must not be overwritten")

    def test_stale_mirror_file_removed(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            stale = root / "examples" / "minimal-project" / "hooks" / "stale.sh"
            self.assertFalse(stale.exists(), "stale mirror file (absent in root) must be removed")

    def test_divergent_file_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            cm = (root / "examples" / "minimal-project" / "CLAUDE.md").read_text()
            self.assertEqual(cm, "PROJECT-SPECIFIC\n", "MIRROR_DIRS 外の分岐ファイルは不可侵")

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._scaffold(Path(t))
            sync_mirror(root)
            first = sorted(p.relative_to(root).as_posix()
                           for p in (root / "examples").rglob("*") if p.is_file())
            sync_mirror(root)
            second = sorted(p.relative_to(root).as_posix()
                            for p in (root / "examples").rglob("*") if p.is_file())
            self.assertEqual(first, second, "2回実行で同結果（冪等）")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m unittest tests.test_sync_example_mirror -v`
Expected: ImportError / `No module named 'sync_example_mirror'`（スクリプト未作成）。

- [ ] **Step 3: sync_example_mirror.py を実装**

`scripts/sync_example_mirror.py` を新規作成:

```python
#!/usr/bin/env python3
"""Sync the example mirror from the framework root (P3-A / M1).

Control files under MIRROR_DIRS + MIRROR_FILES are byte-identical copies of the
framework root (enforced by check_reference_drift.check_mirror_identity). This
regenerates them so editing a root control file no longer needs manual cp.

Single manifest: MIRROR_DIRS/MIRROR_FILES/MIRROR_ALLOWLIST are imported from
check_reference_drift so generation and verification cannot diverge.

This writes ONLY the mirror portion. Example-specific divergent files (CLAUDE.md,
docs/STATUS.md, docs/requirements/*, etc.) live outside MIRROR_DIRS and are never
touched. Allowlisted scaffold-safe variants (validate.md/retro.md) are skipped.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from check_reference_drift import (  # noqa: E402
    MIRROR_ALLOWLIST,
    MIRROR_DIRS,
    MIRROR_FILES,
)


def sync_mirror(root: Path) -> list[str]:
    """Copy mirror control files root -> examples/minimal-project, skipping the
    allowlist and removing stale files under MIRROR_DIRS. Returns the actions
    taken (for logging/idempotency inspection)."""
    example_root = root / "examples" / "minimal-project"
    actions: list[str] = []

    # 1. Copy: every file under MIRROR_DIRS + the explicit MIRROR_FILES.
    candidates: list[Path] = []
    for d in MIRROR_DIRS:
        root_dir = root / d
        if not root_dir.is_dir():
            continue
        for p in sorted(root_dir.rglob("*")):
            if p.is_file():
                candidates.append(p.relative_to(root))
    candidates.extend(MIRROR_FILES)

    for rel in candidates:
        if rel in MIRROR_ALLOWLIST:
            continue
        src = root / rel
        if not src.is_file():
            continue
        dst = example_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)  # copy2 preserves mode (executable bits)
        actions.append(f"copy {rel.as_posix()}")

    # 2. Remove stale: files under MIRROR_DIRS that exist in the example but no
    #    longer in root (e.g. a hook removed upstream). Allowlist is preserved.
    #    Divergent files live outside MIRROR_DIRS, so they are never considered.
    for d in MIRROR_DIRS:
        ex_dir = example_root / d
        if not ex_dir.is_dir():
            continue
        for p in sorted(ex_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(example_root)
            if rel in MIRROR_ALLOWLIST:
                continue
            if not (root / rel).is_file():
                p.unlink()
                actions.append(f"remove {rel.as_posix()}")

    return actions


def main() -> int:
    actions = sync_mirror(ROOT)
    for a in actions:
        print(a)
    print(f"example mirror synced ({len(actions)} action(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストを実行して緑を確認**

Run: `python3 -m unittest tests.test_sync_example_mirror -v`
Expected: 6 テスト全 PASS。

- [ ] **Step 5: Commit**

```bash
git add scripts/sync_example_mirror.py tests/test_sync_example_mirror.py
git commit -m "$(cat <<'EOF'
feat(scripts): add sync_example_mirror.py (M1 example auto-gen)

check_reference_drift の MIRROR_* を import し root→example を copy
（allowlist skip・mode 保持・stale 除去）。検証は既存 check_mirror_identity
に委任し安全網は非破壊。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Makefile + README

**Files:**
- Create: `Makefile`
- Modify: `README.md`

- [ ] **Step 1: Makefile を作成**

`Makefile` を新規作成（タブインデント必須）:

```makefile
.PHONY: example

# Regenerate the browsable example mirror from the framework root.
# Run after editing any control file under hooks/, scripts/, or .claude/.
example:
	python3 scripts/sync_example_mirror.py
```

- [ ] **Step 2: 動作確認（実 repo・冪等＝無変更のはず）**

Run: `make example && git status --porcelain examples/minimal-project | head`
Expected: `example mirror synced (...)` 出力、`git status` は **空**（現在 in-sync なので無変更）。

- [ ] **Step 3: README に dev 手順を追記**

`README.md` の開発/コントリビュート手順、なければ profiles 節付近に1文追記する:

```
開発時、`hooks/`・`scripts/`・`.claude/` の制御ファイルを編集したら `make example` を実行して `examples/minimal-project/` のミラーを再生成する（未実行は `check_reference_drift.py` の mirror identity が検知する）。
```

挿入位置は `grep -n "profile\|## " README.md` で適切な節を特定して追記。

- [ ] **Step 4: Commit**

```bash
git add Makefile README.md
git commit -m "$(cat <<'EOF'
feat(make): add `make example` mirror regen target + dev note (M1)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 実 repo 同期の無変更確認 + drift

**Files:** なし（検証のみ）

- [ ] **Step 1: 実 repo で同期し無変更を確認**

Run: `python3 scripts/sync_example_mirror.py && git status --porcelain examples/minimal-project`
Expected: 出力に `example mirror synced`、`git status --porcelain` は空（現状 in-sync ＝生成器が現状を再現できる＝回帰なしの実証）。

- [ ] **Step 2: drift / mirror identity が緑**

Run: `python3 -m unittest tests.test_mirror_identity 2>&1 | tail -3 && python3 scripts/check_reference_drift.py 2>&1 | tail -2`
Expected: mirror identity OK、`PASS: no reference drift detected`。

（このタスクはコミット不要。生成器が現状と byte 一致なら git diff は空。）

---

## Task 4: framework_version を 1.7.2 へ（4箇所同期）

**Files:**
- Modify: `scripts/check_framework_contract.py`（`FRAMEWORK_VERSION = "1.7.1"`）
- Modify: `templates/STATUS.template.md`（`framework_version: "1.7.1"`）
- Modify: `examples/minimal-project/docs/STATUS.md`（`framework_version: "1.7.1"`）
- Modify: `docs/STATUS.md`（`framework_version: "1.7.1"`）

- [ ] **Step 1: 4箇所を 1.7.2 に更新**

各ファイルの `1.7.1` → `1.7.2`（`FRAMEWORK_VERSION = "1.7.2"` / `framework_version: "1.7.2"`）。

注: example STATUS.md は MIRROR_DIRS 外の分岐ファイルなので sync 対象外＝手で更新する。

- [ ] **Step 2: contract 全 profile で版数同期を確認**

Run: `python3 scripts/check_framework_contract.py --profile=full && python3 scripts/check_framework_contract.py --profile=standard --root=. && python3 scripts/check_framework_contract.py --profile=minimal --root=.`
Expected: 3 profile すべて PASS。

- [ ] **Step 3: Commit**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md examples/minimal-project/docs/STATUS.md docs/STATUS.md
git commit -m "$(cat <<'EOF'
chore: bump framework_version to 1.7.2 (M1 example mirror auto-gen)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 全体検証ゲート + STATUS 更新

- [ ] **Step 1: 全テスト**

Run: `python3 -m unittest discover tests > /tmp/m1_tests.log 2>&1; echo "EXIT=$?"; grep -E "^(Ran|OK|FAILED)" /tmp/m1_tests.log`
Expected: `EXIT=0`、`OK`（新規6テスト分増）。

- [ ] **Step 2: contract / drift / smoke / PoC**

Run:
```bash
for p in minimal standard; do python3 scripts/check_framework_contract.py --profile=$p --root=. || echo "FAIL:$p"; done
python3 scripts/check_framework_contract.py --profile=full || echo "FAIL:full"
python3 scripts/check_reference_drift.py 2>&1 | tail -1
python3 scripts/eval_scaffold_smoke.py 2>&1 | tail -3
bash tests/poc/v162-redteam-rerun.sh 2>&1 | tail -1
bash tests/poc/v163-redteam.sh 2>&1 | tail -1
```
Expected: 全 PASS、`FAIL:` なし、PoC 18/18・5/5。

- [ ] **Step 3: docs/STATUS.md を v1.7.2 着地で更新**

`iteration` を 27 に、`next_action`/`session_history`（最新3件維持）/ `current_refs.plan`・`spec` を M1 着地内容へ更新。

- [ ] **Step 4: 最終コミット**

```bash
git add docs/STATUS.md
git commit -m "$(cat <<'EOF'
chore(STATUS): record v1.7.2 M1 example mirror auto-gen landing

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review メモ

- **Spec coverage:** 設計 §1(アーキ)=Task1,2 / §2(同期ロジック copy/allowlist/mode/stale)=Task1 テスト＋実装 / §3(境界＝分岐不可侵)=Task1 test_divergent_file_untouched / §4(--check 無し)=設計通り生成器は write 専任 / §5(テスト)=Task1 / §6(版数・docs)=Task2,4 / §7(検証)=Task3,5 / §8(非ゴール)=committed 除去せず・安全網非改廃。
- **Type consistency:** 関数名 `sync_mirror(root) -> list[str]`、import 元 `check_reference_drift`、定数 `MIRROR_DIRS/MIRROR_FILES/MIRROR_ALLOWLIST` を一貫。版数 old `1.7.1` → new `1.7.2` 一貫。
- **No placeholders:** 各 step に実コード/実コマンド/期待出力。
- **grill-plan 重点:** ①stale 除去が MIRROR_DIRS 限定で分岐ファイルを誤削除しないこと（test_divergent_file_untouched＋MIRROR_DIRS 外は走査しない設計）②MIRROR_FILES の stale は除去対象外（個別ファイル・churn 稀・drift も両在前提）＝意図的か要確認 ③`shutil.copy2` の mode 保持が CI/別 FS で効くか ④生成器が import する MIRROR_* と drift の検証が同一実体であること（同一 import で構造保証）。
