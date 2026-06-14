# 決定論的コンテキスト予算チェック 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 文脈ロードされる `.claude/skills/*/SKILL.md` と `.claude/rules/*.md` に word 予算を持たせ、超過を決定論的に FAIL させ、tighten-only ratchet で縮小を固定する。

**Architecture:** 単一所有モジュール `scripts/context_budget.py`（対象列挙・registry I/O・word 計測・check・tighten・seed・CLI）を新設。`check_framework_contract.py` が `check()` を import して既存 word 予算と同 family で FAIL に合流。予算は `scripts/context-budgets.json`（path→max_words＋default）。root 専用・非ミラー・setup 非配布。

**Tech Stack:** Python 3（標準ライブラリのみ: json/math/pathlib/sys）、unittest、Make。

参照: 設計書 `docs/specs/2026-06-14-context-budget-design.md`。既存 word 予算は `scripts/check_framework_contract.py`（`MAX_CLAUDE_WORDS`・`TEMPLATE_WORD_LIMITS`・`word_count`）。

---

## File Structure

- Create: `scripts/context_budget.py` — single owner（check＋tighten＋seed＋CLI）。
- Create: `scripts/context-budgets.json` — 予算 registry（seed で生成・commit）。
- Create: `tests/test_context_budget.py` — 単体テスト。
- Modify: `scripts/check_framework_contract.py` — `context_budget.check(ROOT)` を import して呼ぶ（self-bootstrap import）。
- Modify: `Makefile` — `tighten-budgets` ターゲット追加。

---

## Task 1: context_budget.py（check のコア）

**Files:**
- Create: `scripts/context_budget.py`
- Test: `tests/test_context_budget.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_context_budget.py`:

```python
#!/usr/bin/env python3
"""context_budget の単体テスト。"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import context_budget  # noqa: E402


def _mk(root: Path, rel: str, words: int) -> Path:
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(" ".join(["w"] * words) + "\n", encoding="utf-8")
    return p


def _registry(root: Path, data: dict) -> None:
    (Path(root) / "scripts").mkdir(parents=True, exist_ok=True)
    (Path(root) / "scripts" / "context-budgets.json").write_text(
        json.dumps(data), encoding="utf-8")


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_over_budget_fails(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 100)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(
            any("foo/SKILL.md" in f and "100 words > 50" in f for f in failures),
            failures)

    def test_within_budget_passes(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 40)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        self.assertEqual(context_budget.check(self.tmp), [])

    def test_default_guards_unlisted_skill(self):
        _mk(self.tmp, ".claude/skills/big/SKILL.md", 2000)
        _registry(self.tmp, {"default_skill_words": 1500, "budgets": {}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("big/SKILL.md" in f for f in failures), failures)

    def test_rule_default_guards(self):
        _mk(self.tmp, ".claude/rules/r.md", 2000)
        _registry(self.tmp, {"default_rule_words": 500, "budgets": {}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("rules/r.md" in f for f in failures), failures)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_context_budget.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'context_budget'`）

- [ ] **Step 3: context_budget.py を最小実装**

`scripts/context_budget.py`:

```python
#!/usr/bin/env python3
"""Deterministic context-budget check + tighten-only ratchet (roadmap P1).

Single owner of: target enumeration, budget registry I/O, word counting,
the check (FAIL on over-budget), and the ratchet (tighten / seed).
check_framework_contract.py imports check(). Unit = words (len(text.split())).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_WORDS = 1500
DEFAULT_RULE_WORDS = 500


def word_count(text: str) -> int:
    return len(text.split())


def registry_path(root: Path) -> Path:
    return Path(root) / "scripts" / "context-budgets.json"


def load_budgets(root: Path) -> dict:
    p = registry_path(root)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_budgets(root: Path, data: dict) -> None:
    registry_path(root).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def iter_targets(root: Path) -> list[Path]:
    root = Path(root)
    targets = sorted((root / ".claude" / "skills").glob("*/SKILL.md"))
    targets += sorted((root / ".claude" / "rules").glob("*.md"))
    return targets


def _kind(rel: str) -> str:
    return "rule" if "/rules/" in rel.replace("\\", "/") else "skill"


def budget_for(rel: str, data: dict) -> int:
    explicit = data.get("budgets", {}).get(rel)
    if explicit is not None:
        return explicit
    if _kind(rel) == "rule":
        return data.get("default_rule_words", DEFAULT_RULE_WORDS)
    return data.get("default_skill_words", DEFAULT_SKILL_WORDS)


def check(root: Path = ROOT) -> list[str]:
    root = Path(root)
    data = load_budgets(root)
    failures: list[str] = []
    for p in iter_targets(root):
        rel = str(p.relative_to(root))
        count = word_count(p.read_text(encoding="utf-8"))
        budget = budget_for(rel, data)
        if count > budget:
            failures.append(f"{rel} is too large: {count} words > {budget}")
    return failures
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_context_budget.py -q`
Expected: PASS（4 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/context_budget.py tests/test_context_budget.py
git commit -m "feat(context-budget): add check() for skill/rule word budgets"
```

---

## Task 2: tighten / seed / CLI

**Files:**
- Modify: `scripts/context_budget.py`
- Test: `tests/test_context_budget.py`

- [ ] **Step 1: 失敗するテストを追加**

`tests/test_context_budget.py` の末尾（`if __name__` の前）に追加:

```python
class TestRatchet(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-r-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _read(self):
        return json.loads(
            (self.tmp / "scripts" / "context-budgets.json").read_text())

    def test_tighten_lowers_to_current(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 30)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 100}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/foo/SKILL.md"], 30)

    def test_tighten_never_raises(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 80)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 50}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/foo/SKILL.md"], 50)

    def test_tighten_adds_new_file_at_current(self):
        _mk(self.tmp, ".claude/skills/new/SKILL.md", 42)
        _registry(self.tmp, {"budgets": {}})
        context_budget.tighten(self.tmp)
        self.assertEqual(self._read()["budgets"][".claude/skills/new/SKILL.md"], 42)

    def test_seed_uses_headroom_and_skips_existing(self):
        _mk(self.tmp, ".claude/skills/foo/SKILL.md", 100)
        _mk(self.tmp, ".claude/skills/bar/SKILL.md", 50)
        _registry(self.tmp, {"budgets": {".claude/skills/foo/SKILL.md": 999}})
        context_budget.seed(self.tmp, headroom=1.1)
        data = self._read()
        # existing entry untouched
        self.assertEqual(data["budgets"][".claude/skills/foo/SKILL.md"], 999)
        # new entry seeded at ceil(50*1.1)=55
        self.assertEqual(data["budgets"][".claude/skills/bar/SKILL.md"], 55)
        self.assertIn("default_skill_words", data)
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_context_budget.py::TestRatchet -q`
Expected: FAIL（`AttributeError: module 'context_budget' has no attribute 'tighten'`）

- [ ] **Step 3: tighten / seed / main を実装**

`scripts/context_budget.py` の `check()` の後に追加:

```python
def tighten(root: Path = ROOT) -> list[tuple[str, int]]:
    """Lower budgets to current word count (never raise). New files get an
    explicit entry at their current count. Returns changed (rel, new)."""
    root = Path(root)
    data = load_budgets(root)
    budgets = data.setdefault("budgets", {})
    changed: list[tuple[str, int]] = []
    for p in iter_targets(root):
        rel = str(p.relative_to(root))
        count = word_count(p.read_text(encoding="utf-8"))
        if rel not in budgets or count < budgets[rel]:
            budgets[rel] = count
            changed.append((rel, count))
    save_budgets(root, data)
    return changed


def seed(root: Path = ROOT, headroom: float = 1.1) -> list[tuple[str, int]]:
    """Populate budgets for targets that lack an explicit entry, at
    ceil(current * headroom). Existing entries and defaults untouched if set."""
    root = Path(root)
    data = load_budgets(root)
    budgets = data.setdefault("budgets", {})
    data.setdefault("default_skill_words", DEFAULT_SKILL_WORDS)
    data.setdefault("default_rule_words", DEFAULT_RULE_WORDS)
    added: list[tuple[str, int]] = []
    for p in iter_targets(root):
        rel = str(p.relative_to(root))
        if rel in budgets:
            continue
        count = word_count(p.read_text(encoding="utf-8"))
        budgets[rel] = math.ceil(count * headroom)
        added.append((rel, budgets[rel]))
    save_budgets(root, data)
    return added


def main(argv: list[str]) -> int:
    if "--tighten" in argv:
        for rel, new in tighten():
            print(f"tightened {rel} -> {new}")
        return 0
    if "--seed" in argv:
        for rel, new in seed():
            print(f"seeded {rel} -> {new}")
        return 0
    failures = check()
    for f in failures:
        print(f"FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_context_budget.py -q`
Expected: PASS（全 8 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/context_budget.py tests/test_context_budget.py
git commit -m "feat(context-budget): add tighten/seed ratchet and CLI"
```

---

## Task 3: 実 registry を seed して commit

**Files:**
- Create: `scripts/context-budgets.json`

- [ ] **Step 1: seed を実行して registry を生成**

Run: `python3 scripts/context_budget.py --seed`
Expected: `seeded .claude/skills/... -> N` の行が各 skill/rule 分出る。`scripts/context-budgets.json` が生成される。

- [ ] **Step 2: 生成物を確認**

Run: `cat scripts/context-budgets.json` と `python3 scripts/context_budget.py`（引数なし=check）
Expected: check は exit 0（FAIL 出力なし）。registry に `default_skill_words`=1500 / `default_rule_words`=500 ＋ 各 skill/rule の明示 budget（現状 word 数の ceil(×1.1)）が入っていること。seed は全現存ファイルに明示 budget を与えるため、仮に現状が default を超える大きな skill があっても explicit budget が優先され check は緑になる（default は将来追加される新規ファイル用のガード）。

- [ ] **Step 3: コミット**

```bash
git add scripts/context-budgets.json
git commit -m "feat(context-budget): seed registry from current skills/rules (+10% headroom)"
```

---

## Task 4: check_framework_contract.py へ統合

**Files:**
- Modify: `scripts/check_framework_contract.py`
- Test: `tests/test_context_budget.py`

- [ ] **Step 1: 実リポ緑を保証するテストを追加**

`tests/test_context_budget.py` の末尾（`if __name__` の前）に追加:

```python
class TestRealRepoAndContract(unittest.TestCase):
    def test_real_repo_check_is_green(self):
        # seed 済み registry で実リポの全 skill/rule が予算内であること。
        self.assertEqual(context_budget.check(ROOT), [])

    def test_contract_includes_budget_check(self):
        # contract が budget 違反を failures に合流すること（一時 root で検証）。
        import check_framework_contract as cfc
        tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-c-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        # cfc.check_budget は ROOT 固定なので、ここでは context_budget 経由の
        # 合流口が存在することだけを確認する（直接 check_budget を呼ぶ）。
        self.assertTrue(hasattr(cfc, "context_budget"))
```

> 注: contract 本体は ROOT 固定で自己検査する設計のため、tmp root での E2E は行わず「合流口の存在」と「実リポ緑」で担保する。

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_context_budget.py::TestRealRepoAndContract -q`
Expected: `test_contract_includes_budget_check` が FAIL（`cfc` に `context_budget` 属性なし）。`test_real_repo_check_is_green` は PASS（Task 3 で seed 済み）。

- [ ] **Step 3: contract に self-bootstrap import と呼び出しを追加**

`scripts/check_framework_contract.py` の import 群の直後（`ROOT = ...` 定義より後の任意のトップレベル）に追加:

```python
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_budget  # noqa: E402  (single owner of context-budget logic)
```

そして `TEMPLATE_WORD_LIMITS` の for ループ（`f"{tpl_path.relative_to(ROOT)} is too large..."` を append する箇所）の**直後**に追加:

```python
    # Context budget: skills/rules word budgets (roadmap P1).
    failures.extend(context_budget.check(ROOT))
```

- [ ] **Step 4: テストとフルスイートが通ることを確認**

Run: `python3 -m pytest tests/test_context_budget.py -q`
Expected: PASS（全 10 tests）
Run: `python3 scripts/check_framework_contract.py`
Expected: `PASS: aegis contract is aligned`（exit 0）

- [ ] **Step 5: コミット**

```bash
git add scripts/check_framework_contract.py tests/test_context_budget.py
git commit -m "feat(context-budget): wire check into check_framework_contract"
```

---

## Task 5: Makefile ターゲット

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: 既存 Makefile を確認**

Run: `cat Makefile`
Expected: `example` 等の既存ターゲットの書式（タブインデント）を把握。

- [ ] **Step 2: tighten-budgets ターゲットを追加**

`Makefile` に追記（タブインデント厳守）:

```make
.PHONY: tighten-budgets
tighten-budgets:
	python3 scripts/context_budget.py --tighten
```

- [ ] **Step 3: 動作確認（実リポを締めない確認）**

Run: `make tighten-budgets`
Expected: 各 skill/rule の予算が現状（seed の +10% から実数）へ下がる出力。
**注意**: これは registry を変更する。**この時点では締めない方針**なので、変更を破棄する: `git checkout -- scripts/context-budgets.json`（seed の余裕を残す）。ターゲットが動くことの確認のみ。

- [ ] **Step 4: コミット**

```bash
git add Makefile
git commit -m "build(context-budget): add make tighten-budgets target"
```

---

## Task 6: 最終検証＋アーキ同期

**Files:**
- Modify: `docs/architecture-overview.md`（自己検査一覧に1行追加が必要な場合のみ）

- [ ] **Step 1: 自己検査一覧の同期要否を確認**

Run: `grep -n "check_framework_contract\|word\|budget\|自己検査\|self-check" docs/architecture-overview.md | head`
Expected: contract の責務記述があれば「skills/rules の word 予算も検査」を1行追記。`test_arch_overview_currency.py` が要求する数値/一覧があれば同期。

- [ ] **Step 2: 必要なら architecture-overview.md を更新**（該当があれば最小追記）

- [ ] **Step 3: フル検証**

Run（すべて緑であること）:
```bash
python3 -m pytest tests/ -p no:randomly -q
python3 scripts/check_framework_contract.py
python3 scripts/check_reference_drift.py
python3 scripts/run_eval.py --tier 1
python3 scripts/eval_scenario.py
```
Expected: pytest 全 PASS（新規 10 件込み・既知 skip 以外緑）／contract PASS／drift PASS／eval PASS／eval_scenario PASS。

- [ ] **Step 4: コミット**

```bash
git add -A
git commit -m "docs(context-budget): sync architecture-overview; final verification"
```

---

## 補足: ratchet 運用（実装後の使い方）
- 平時: 何もしなくてよい（seed 済み予算＋default が FAIL ガード）。
- skill/rule を削って薄くしたら `make tighten-budgets` で成果を固定（予算が実数へ下がる）。
- 正当に増やしたい時のみ `scripts/context-budgets.json` を手編集で上げる（PR diff に出る＝関所）。

## 注意・既知の制約
- `word_count = len(text.split())` は既存 contract と同一の単純定義（コードブロックや日本語で多少ブレるが、既存 CLAUDE.md 予算と一貫）。
- contract の budget 検査は ROOT（framework repo 自身）固定。downstream `--root` 実行では Aegis 自身の skills を検査する（既存 CLAUDE.md self-check と同じ挙動）。
- `context_budget.py` / `context-budgets.json` は setup 非配布・非ミラー（`MIRROR_DIRS/FILES` に追加しない）。
