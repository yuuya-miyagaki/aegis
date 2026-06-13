# B2 非エンジニア向け judge 可視化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ゲート承認の瞬間に、LLM 判定とは独立した機械事実シグナルを並べた judge カードをハーネスが生成し、決定論的矛盾は🔴ブロック・第2意見の相違は🟡 ack 要求として非エンジニアの go/no-go を支える。

**Architecture:** 純スクリプト `build-judge-card.py` がティア1機械事実（変更行のスタブ scan・secret scan・記録済みテスト結果・B1 verdict）を実測し、レポート内の `claims:` と照合（矛盾=🔴）、記録済み1次/2次レビュー verdict を比較（相違=🟡）、三状態（0🟢/1🔴/2🟡）で終了。`pre_approve_gate` が承認時に live 実行し、`update-gate.sh` が🟡を `--ack "理由"` でのみ通す。`/judge` で同カードをプレビュー。B1 の型を踏襲。

**Tech Stack:** Python 3（`from __future__ import annotations`・unittest/subprocess/hashlib）、git diff、aegis 既存ゲート機構（`pre_approve_gate`/`update-gate.sh`/`GATE_REF_MAPPING`）、B1 資産（`added_lines_by_file`/`resolve_diff_ref`/`_execute` を importlib 流用）。

---

## 実装上の決定事項（spec の精緻化・plan レビューで要確認）

1. **ビルダーはテストを実行しない（純 read）**: spec §6.3 は「キャッシュ miss 時にビルダーがテスト実走」としたが、ビルダーにテストコマンド探索を持たせると純粋性が崩れる。→ ビルダーは **`docs/qa-reports/test-result.json`（`{status, code_fingerprint}`）を読むだけ**。実行＋記録は別の小スクリプト `scripts/record-test-result.py "<test-command>"` が担い、review/qa skill が呼ぶ。test-result.json 不在/指紋不一致（stale）→ 🟡 未検証（移行安全）。これでビルダーは純粋・テスト実行は1箇所に集約。
2. **B1 資産の流用**: `added_lines_by_file`/`resolve_diff_ref`/`_execute` を `run-test-strength-drill.py` から importlib で読み込み再利用（DRY）。
3. **指紋（code_fingerprint）**: 変更ファイル内容の sha256（B1 が案A で撤去した概念をここで復活・ビルダーとレコーダで共有）。
4. **tri-state**: `pre_approve_gate` は判定ゲートで `0/1/2` を返す（既存 0/1 契約を拡張・呼出元棚卸し＝Task 13）。

## ファイル構成

| ファイル | 役割 | 新規/改修 |
|---|---|---|
| `scripts/build-judge-card.py` | judge カードビルダー（純 read・tri-state） | 新規（+example mirror） |
| `scripts/record-test-result.py` | テスト実走→`test-result.json` 記録 | 新規（+example mirror） |
| `scripts/check_status.py` | `pre_approve_gate` に judge ブランチ（tri-state） | 改修（+mirror） |
| `scripts/update-gate.sh` | tri-state 解釈＋`--ack "理由"` | 改修（+mirror） |
| `scripts/check_reference_drift.py` | `MIRROR_FILES` に2新規スクリプト登録 | 改修 |
| `.claude/commands/judge.md` | `/judge` プレビュー | 新規（+mirror） |
| `.claude/agents/{reviewer,qa,security}.md` | `claims:` 記録規約 | 改修（+mirror） |
| `.claude/skills/aegis-review-gate/SKILL.md`, `aegis-security-gate/SKILL.md` | 盲検2次レビュー記録 | 改修（+mirror） |
| `tests/test_judge_card.py` | ビルダー単体 | 新規 |
| `tests/test_check_status.py` | judge ゲート結合 | 改修 |
| `tests/test_mirror_identity.py` | 新規スクリプト登録 | 改修 |
| `docs/architecture-overview.md` | judge カード反映 | 改修 |

> **ミラー**: `MIRROR_FILES`/`MIRROR_DIRS` 配下は example と byte 同一必須。スクリプト・skill・agent・command を編集したら example へ `cp`。

---

## Phase 1: ビルダーの純粋ヘルパ（claims 解析・指紋・ティア1チェッカ）

### Task 1: ビルダー骨格＋claims パーサ（fenced ```claims yaml）

**Files:**
- Create: `scripts/build-judge-card.py`
- Test: `tests/test_judge_card.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_judge_card.py
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build-judge-card.py"

def _load():
    spec = importlib.util.spec_from_file_location("judge", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

judge = _load()


class TestReadClaims(unittest.TestCase):
    def test_parses_fenced_claims_block(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "review.md"
            p.write_text(
                "# review\n\n```claims\n"
                "tests_pass: true\nno_stubs: true\nverdict: approve\n```\n",
                encoding="utf-8")
            claims = judge.read_claims(p)
            self.assertEqual(claims["tests_pass"], True)
            self.assertEqual(claims["verdict"], "approve")

    def test_missing_block_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "review.md"
            p.write_text("# review\n\nno claims here\n", encoding="utf-8")
            self.assertIsNone(judge.read_claims(p))

    def test_missing_file_returns_none(self):
        self.assertIsNone(judge.read_claims(Path("/nonexistent/x.md")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_judge_card -v`
Expected: FAIL（`build-judge-card.py` 不在／`read_claims` 未定義）

- [ ] **Step 3: 最小実装**

```python
#!/usr/bin/env python3
"""Judge-card builder (B2). Runs at gate-approval time as a pure script.

Re-checks tier-1 machine facts, compares them with the gate report's recorded
`claims:`, compares recorded 1st/2nd review verdicts, and emits a judge card
with a tri-state verdict. Exit 0=🟢 / 1=🔴 (block) / 2=🟡 (needs ack).
Never dispatches an LLM (the second opinion is recorded by the LLM beforehand).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


class JudgeError(Exception):
    """Unexpected internal failure => fail-closed (treated as 🔴)."""


def _parse_scalar(v: str):
    s = v.strip()
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    return s.strip('"')


def read_claims(report_path: Path) -> dict | None:
    """Read the single fenced ```claims YAML block from a gate report. Returns a
    flat dict (nested second_opinion captured as a sub-dict) or None if the file
    or block is absent. Intentionally a narrow YAML subset (key: value lines and
    one nested `second_opinion:` map) to stay dependency-free."""
    if not report_path.is_file():
        return None
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"```claims\n(.*?)\n```", text, re.DOTALL)
    if not m:
        return None
    claims: dict = {}
    cur_map: dict | None = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z_]+:\s*$", line):  # "second_opinion:" map start
            key = line.split(":")[0].strip()
            cur_map = {}
            claims[key] = cur_map
            continue
        indented = line.startswith("  ")
        kv = line.strip().split(":", 1)
        if len(kv) != 2:
            continue
        key, val = kv[0].strip(), kv[1].strip()
        if indented and cur_map is not None:
            cur_map[key] = _parse_scalar(val)
        else:
            cur_map = None
            claims[key] = _parse_scalar(val)
    return claims
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_judge_card -v`
Expected: PASS（3 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "feat(b2): judge-card builder skeleton + claims parser"
```

### Task 2: 変更ファイル指紋（code_fingerprint）

**Files:**
- Modify: `scripts/build-judge-card.py`
- Test: `tests/test_judge_card.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
import subprocess as sp

class TestFingerprint(unittest.TestCase):
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def _repo(self, d):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-qm", "i")
        return root

    def test_fingerprint_changes_with_code(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo(d)
            (root / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            fp1 = judge.code_fingerprint(root)
            (root / "a.py").write_text("x = 1\ny = 3\n", encoding="utf-8")
            fp2 = judge.code_fingerprint(root)
            self.assertNotEqual(fp1, fp2)

    def test_fingerprint_stable_when_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo(d)
            (root / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            self.assertEqual(judge.code_fingerprint(root), judge.code_fingerprint(root))
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_judge_card.TestFingerprint -v`
Expected: FAIL（`code_fingerprint` 未定義）

- [ ] **Step 3: 最小実装**（B1 の helper を importlib 流用）

```python
import hashlib

_DRILL = None

def _drill():
    """Lazy-load B1's drill module (reuse added_lines_by_file/resolve_diff_ref/
    _execute). The filename has hyphens, so load by path."""
    global _DRILL
    if _DRILL is None:
        import importlib.util
        path = Path(__file__).resolve().parent / "run-test-strength-drill.py"
        spec = importlib.util.spec_from_file_location("drill_mod", path)
        _DRILL = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_DRILL)
    return _DRILL


def code_fingerprint(root: Path) -> str:
    """sha256 over the changed files' current content (sorted), binding a test
    result to the exact code it was produced against."""
    drill = _drill()
    ref = drill.resolve_diff_ref(root)
    changed = sorted(drill.added_lines_by_file(root, ref).keys())
    h = hashlib.sha256()
    for rel in changed:
        h.update(rel.encode("utf-8"))
        try:
            h.update((root / rel).read_bytes())
        except OSError:
            h.update(b"<unreadable>")
    return h.hexdigest()
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_judge_card.TestFingerprint -v`
Expected: PASS（2 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "feat(b2): code fingerprint reusing B1 diff helpers"
```

### Task 3: ティア1チェッカ（スタブ scan・secret scan・テスト結果読み）

**Files:**
- Modify: `scripts/build-judge-card.py`
- Test: `tests/test_judge_card.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestTier1(unittest.TestCase):
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def _repo_with_change(self, d, body):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-qm", "i")
        (root / "m.py").write_text(body, encoding="utf-8")  # untracked change
        return root

    def test_scan_stubs_detects_todo_in_changed(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    pass  # stub\n")
            hits = judge.scan_stubs(root)
            self.assertTrue(hits)

    def test_scan_stubs_clean(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            self.assertEqual(judge.scan_stubs(root), [])

    def test_read_test_result_fresh_green(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            fp = judge.code_fingerprint(root)
            qa = root / "docs" / "qa-reports"
            qa.mkdir(parents=True)
            (qa / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": fp}),
                encoding="utf-8")
            self.assertEqual(judge.read_test_result(root), "green")

    def test_read_test_result_stale_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            qa = root / "docs" / "qa-reports"
            qa.mkdir(parents=True)
            (qa / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": "STALE"}),
                encoding="utf-8")
            self.assertEqual(judge.read_test_result(root), "unverified")

    def test_read_test_result_absent_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_change(d, "def f():\n    return 1\n")
            self.assertEqual(judge.read_test_result(root), "unverified")
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_judge_card.TestTier1 -v`
Expected: FAIL（`scan_stubs`/`read_test_result` 未定義）

- [ ] **Step 3: 最小実装**

```python
STUB_PATTERN = re.compile(r"TODO|FIXME|XXX|NotImplementedError|pass\s*#\s*stub|placeholder",
                          re.IGNORECASE)


def scan_stubs(root: Path) -> list[str]:
    """Scan ONLY changed (added) lines for stub/placeholder markers. Returns
    a list of 'file:line' hits (empty = clean)."""
    drill = _drill()
    ref = drill.resolve_diff_ref(root)
    added = drill.added_lines_by_file(root, ref)
    hits: list[str] = []
    for rel, lines in added.items():
        try:
            content = (root / rel).read_text(encoding="utf-8").split("\n")
        except OSError:
            continue
        for ln in sorted(lines):
            if 1 <= ln <= len(content) and STUB_PATTERN.search(content[ln - 1]):
                hits.append(f"{rel}:{ln}")
    return hits


def read_test_result(root: Path) -> str:
    """Read docs/qa-reports/test-result.json and verify freshness against the
    current code fingerprint. Returns 'green' / 'red' / 'unverified'
    (absent/stale/unreadable => unverified, never silent-green)."""
    p = root / "docs" / "qa-reports" / "test-result.json"
    if not p.is_file():
        return "unverified"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "unverified"
    if data.get("code_fingerprint") != code_fingerprint(root):
        return "unverified"
    status = data.get("status")
    return status if status in ("green", "red") else "unverified"
```

続けて `scan_secrets` と `audit_deps` も実装する（collect_facts が使う・後回し禁止）:

```python
import subprocess

SECRET_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"])")


def scan_secrets(root: Path) -> list[str]:
    """Scan changed files for secret-like patterns. Returns 'file:line' hits."""
    drill = _drill()
    ref = drill.resolve_diff_ref(root)
    hits: list[str] = []
    for rel in drill.added_lines_by_file(root, ref):
        try:
            for i, line in enumerate((root / rel).read_text(encoding="utf-8").split("\n"), 1):
                if SECRET_PATTERN.search(line):
                    hits.append(f"{rel}:{i}")
        except OSError:
            continue
    return hits


def audit_deps(root: Path) -> str:
    """Run an available dependency auditor. Returns 'clean' / 'vuln' /
    'unverified' (no tool / offline / error => unverified, never blocks)."""
    for cmd in (["pip-audit", "-q"], ["npm", "audit", "--audit-level=high"]):
        try:
            proc = subprocess.run(cmd, cwd=str(root), capture_output=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            continue
        return "clean" if proc.returncode == 0 else "vuln"
    return "unverified"
```

> `audit_deps` が `"vuln"` のとき `compute_verdict` は claim `deps_clean: true` と矛盾すれば🔴、claim 無しでも脆弱性は🟡（誤検知も多いためブロックは claim 矛盾時のみ）。`compute_verdict` の deps 分岐を `vuln`→（claim と矛盾なら red・でなければ yellow）に拡張すること。

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_judge_card.TestTier1 -v`
Expected: PASS（5 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "feat(b2): tier-1 checkers — stub scan + fingerprint-verified test result"
```

---

---

## Phase 2: verdict 計算・カード描画・main（tri-state）

### Task 4: レポート解決（current_refs.<gate>）

**Files:**
- Modify: `scripts/build-judge-card.py`
- Test: `tests/test_judge_card.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestResolveReport(unittest.TestCase):
    def _status(self, root, review_ref):
        docs = root / "docs"; docs.mkdir(exist_ok=True)
        (docs / "STATUS.md").write_text(
            "---\ncurrent_refs:\n"
            f"  review: {review_ref}\n  qa: null\n---\n", encoding="utf-8")

    def test_resolves_review_ref(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._status(root, "docs/qa-reports/review.md")
            self.assertEqual(judge.resolve_gate_report(root, "review"),
                             root / "docs/qa-reports/review.md")

    def test_null_ref_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._status(root, "null")
            self.assertIsNone(judge.resolve_gate_report(root, "review"))
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_judge_card.TestResolveReport -v`
Expected: FAIL（`resolve_gate_report` 未定義）

- [ ] **Step 3: 最小実装**

```python
GATE_REF_KEY = {"review": "review", "qa": "qa", "security": "security",
                "deploy": "deploy"}


def resolve_gate_report(root: Path, gate: str) -> Path | None:
    """Read current_refs.<ref_key> from STATUS.md; return the report path or
    None when the ref is null/absent (=> 🟡 evidence-not-submitted upstream)."""
    ref_key = GATE_REF_KEY.get(gate)
    if not ref_key:
        return None
    status = root / "docs" / "STATUS.md"
    if not status.is_file():
        return None
    in_refs = False
    for line in status.read_text(encoding="utf-8").splitlines():
        if re.match(r"^current_refs:\s*$", line):
            in_refs = True
            continue
        if in_refs and re.match(r"^[A-Za-z_]", line):  # next top-level key
            break
        if in_refs:
            m = re.match(rf"^\s+{ref_key}:\s*(.+)$", line)
            if m:
                val = m.group(1).strip().strip('"')
                if val in ("null", "", "[]"):
                    return None
                return root / val
    return None
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_judge_card.TestResolveReport -v`
Expected: PASS（2 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "feat(b2): resolve gate report from current_refs"
```

### Task 5: verdict 計算（tri-state・無条件🔴・ティア2アドバイザリ）

**Files:**
- Modify: `scripts/build-judge-card.py`
- Test: `tests/test_judge_card.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestVerdict(unittest.TestCase):
    def _facts(self, **over):
        f = {"tests": "green", "stubs": [], "secrets": [],
             "b1_verdict": None, "deps": "clean"}
        f.update(over)
        return f

    def test_clean_all_green(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(), {"verdict": "approve"})
        self.assertEqual(v.overall, 0)

    def test_stub_blocks_even_without_claim(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(stubs=["m.py:2"]), None)
        self.assertEqual(v.overall, 1)
        self.assertTrue(v.red)

    def test_claim_tests_pass_but_red_blocks(self):
        v = judge.compute_verdict("review", {"tests_pass": True, "verdict": "approve"},
                                  self._facts(tests="red"), None)
        self.assertEqual(v.overall, 1)

    def test_tests_unverified_is_yellow(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(tests="unverified"), {"verdict": "approve"})
        self.assertEqual(v.overall, 2)

    def test_second_opinion_divergence_is_yellow(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(), {"verdict": "reject"})
        self.assertEqual(v.overall, 2)

    def test_second_opinion_missing_is_yellow_for_review(self):
        v = judge.compute_verdict("review", {"verdict": "approve"},
                                  self._facts(), None)
        self.assertEqual(v.overall, 2)

    def test_claims_absent_is_yellow_not_red(self):
        v = judge.compute_verdict("review", None, self._facts(), None)
        self.assertEqual(v.overall, 2)
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_judge_card.TestVerdict -v`
Expected: FAIL（`compute_verdict` 未定義）

- [ ] **Step 3: 最小実装**

```python
from dataclasses import dataclass, field

# gates that require a self-attested second opinion (tier-2)
SECOND_OPINION_GATES = ("review", "security")


@dataclass
class Verdict:
    overall: int               # 0=🟢 / 1=🔴 / 2=🟡
    red: list[str] = field(default_factory=list)
    yellow: list[str] = field(default_factory=list)


def compute_verdict(gate: str, claims: dict | None, facts: dict,
                    second_opinion: dict | None) -> Verdict:
    """Harness-computed verdict. Tier-1 facts BLOCK (🔴); claims-absent and
    tier-1-unverified and tier-2 divergence are advisory (🟡). Tier-2 NEVER
    blocks (assurance is self-attested)."""
    red: list[str] = []
    yellow: list[str] = []

    # tier-1 facts run unconditionally (independent of what was claimed)
    if facts["stubs"]:
        red.append(f"変更コードに未完成マーカー: {', '.join(facts['stubs'])}")
    if facts["secrets"]:
        red.append(f"シークレットの疑い: {', '.join(facts['secrets'])}")
    if facts["tests"] == "red":
        red.append("テストが赤")
    elif facts["tests"] == "unverified":
        yellow.append("テスト結果が未検証（記録なし/コード変更後）")
    if facts["deps"] == "unverified":
        yellow.append("依存監査が未検証")
    if facts.get("b1_verdict") == "FAIL":
        red.append("テスト強度ドリル(B1)が FAIL")

    # claims sanity (advisory; missing claims must not hard-block — §1.5)
    if claims is None:
        yellow.append("claims 未提出（要確認）")

    # tier-2: self-attested second opinion (advisory only, never blocks)
    if gate in SECOND_OPINION_GATES:
        if second_opinion is None:
            yellow.append("第2意見なし（self-attested・要確認）")
        elif claims and second_opinion.get("verdict") != claims.get("verdict"):
            yellow.append(
                f"1次/2次レビューの相違（self-attested）: "
                f"1次={claims.get('verdict')} / 2次={second_opinion.get('verdict')}")

    overall = 1 if red else (2 if yellow else 0)
    return Verdict(overall=overall, red=red, yellow=yellow)
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_judge_card.TestVerdict -v`
Expected: PASS（7 tests）

- [ ] **Step 5: コミット**

```bash
git add scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "feat(b2): tri-state verdict — tier-1 blocks, tier-2 advisory"
```

### Task 6: カード描画＋main（tri-state 終了コード・facts 収集）

**Files:**
- Modify: `scripts/build-judge-card.py`
- Test: `tests/test_judge_card.py`（end-to-end subprocess）

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestMain(unittest.TestCase):
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def _project(self, d, *, body, claims_block, review_ref="docs/qa-reports/review.md",
                 test_result=None):
        root = Path(d)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "t@t")
        self._git(root, "config", "user.name", "t")
        (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
        self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
        (root / "m.py").write_text(body, encoding="utf-8")
        docs = root / "docs"; (docs / "qa-reports").mkdir(parents=True)
        (docs / "STATUS.md").write_text(
            "---\ncurrent_refs:\n"
            f"  review: {review_ref}\n  qa: null\n---\n", encoding="utf-8")
        if review_ref != "null":
            (root / review_ref).write_text("# review\n\n" + claims_block, encoding="utf-8")
        if test_result is not None:
            (docs / "qa-reports" / "test-result.json").write_text(
                json.dumps(test_result), encoding="utf-8")
        return root

    def _run(self, root, gate="review"):
        out = root / "docs" / "qa-reports" / f"judge-{gate}.md"
        return sp.run(["python3", str(SCRIPT), "--gate", gate, "--root", str(root),
                       "--report-out", str(out)], capture_output=True, text=True), out

    def test_block_on_stub_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._project(
                d, body="def f():\n    pass  # stub\n",
                claims_block="```claims\nno_stubs: true\nverdict: approve\n```\n")
            res, out = self._run(root)
            self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
            self.assertIn("🔴", out.read_text())

    def test_yellow_on_missing_second_opinion_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            fp_body = "def f():\n    return 1\n"
            root = self._project(
                d, body=fp_body,
                claims_block="```claims\nno_stubs: true\ntests_pass: true\nverdict: approve\n```\n")
            # add a fresh green test-result so tests aren't unverified
            fp = judge.code_fingerprint(root)
            (root / "docs" / "qa-reports" / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": fp}), encoding="utf-8")
            res, out = self._run(root)
            self.assertEqual(res.returncode, 2, res.stdout + res.stderr)

    def test_green_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            body = "def f():\n    return 1\n"
            root = self._project(
                d, body=body,
                claims_block=("```claims\nno_stubs: true\ntests_pass: true\nverdict: approve\n"
                              "second_opinion:\n  verdict: approve\n```\n"))
            fp = judge.code_fingerprint(root)
            (root / "docs" / "qa-reports" / "test-result.json").write_text(
                json.dumps({"status": "green", "code_fingerprint": fp}), encoding="utf-8")
            res, out = self._run(root)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("🟢", out.read_text())
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_judge_card.TestMain -v`
Expected: FAIL（`main`/facts 収集/描画 未実装）

- [ ] **Step 3: 最小実装**

```python
def collect_facts(root: Path, gate: str) -> dict:
    b1 = None
    if gate == "qa":
        ts = root / "docs" / "qa-reports" / "test-strength.md"
        if ts.is_file():
            m = re.search(r"verdict:\s*(\w+)", ts.read_text(encoding="utf-8"))
            b1 = m.group(1) if m else None
    secrets = scan_secrets(root) if gate == "security" else []
    deps = audit_deps(root) if gate == "security" else "clean"
    return {
        "tests": read_test_result(root),
        "stubs": scan_stubs(root),
        "secrets": secrets,
        "b1_verdict": b1,
        "deps": deps,
    }


def render_card(report_out: Path, *, gate: str, v: Verdict, claims: dict | None,
                facts: dict, second_opinion: dict | None) -> None:
    sym = {0: "🟢 承認可", 1: "🔴 ブロック", 2: "🟡 要確認"}[v.overall]
    lines = [f"# Judge カード: {gate} ゲート（機械生成）", "",
             f"## 総合: {sym}", "",
             "## ティア1: 機械事実（✅検証済・高信頼）",
             f"- テスト: {facts['tests']}",
             f"- 未完成マーカー(変更行): {facts['stubs'] or 'なし'}"]
    if gate == "security":
        lines.append(f"- シークレット: {facts['secrets'] or 'なし'}")
        lines.append(f"- 依存監査: {facts['deps']}")
    if gate == "qa":
        lines.append(f"- テスト強度ドリル(B1): {facts['b1_verdict'] or '未実施'}")
    if gate in SECOND_OPINION_GATES:
        lines += ["", "## ティア2: 🔍 第2意見（self-attested・自己申告・低信頼）",
                  f"- {('あり: ' + str(second_opinion.get('verdict'))) if second_opinion else 'なし'}"]
    if v.red:
        lines += ["", "## 🔴 ブロック要因"] + [f"- {r}" for r in v.red]
    if v.yellow:
        lines += ["", "## 🟡 要確認"] + [f"- {y}" for y in v.yellow]
    lines += ["", "## あなたが取るアクション", "（LLM が平易日本語で記述）", ""]
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text("\n".join(lines), encoding="utf-8")


def build(root: Path, gate: str, report_out: Path) -> int:
    try:
        report = resolve_gate_report(root, gate)
        claims = read_claims(report) if report else None
        second = claims.get("second_opinion") if claims else None
        facts = collect_facts(root, gate)
        v = compute_verdict(gate, claims, facts, second)
        render_card(report_out, gate=gate, v=v, claims=claims, facts=facts,
                    second_opinion=second)
        for r in v.red:
            print(f"🔴 {r}")
        for y in v.yellow:
            print(f"🟡 {y}")
        return v.overall
    except Exception as exc:  # fail-closed: any internal error blocks
        print(f"JUDGE BLOCKED (fail-closed): {exc}")
        return 1


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Judge-card builder (B2)")
    p.add_argument("--gate", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--report-out", default=None)
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    out = Path(args.report_out) if args.report_out else (
        root / "docs" / "qa-reports" / f"judge-{args.gate}.md")
    return build(root, args.gate, out)


if __name__ == "__main__":
    sys.exit(main())
```

> `scan_secrets`/`audit_deps` は Task 3 の注記どおり実装済みであること（`scan_secrets`=変更ファイルへ check-secrets パターン grep→hit list、`audit_deps`=`pip-audit`/`npm audit` をツール検出して実行・不在は `"unverified"`）。

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_judge_card -v`
Expected: PASS（全 Task 1-6）

- [ ] **Step 5: example へミラー＋コミット**

```bash
cp scripts/build-judge-card.py examples/minimal-project/scripts/build-judge-card.py
git add scripts/build-judge-card.py examples/minimal-project/scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "feat(b2): judge-card main, fact collection, rendering + example mirror"
```

---

---

## Phase 3: ゲート結合（pre_approve_gate 三状態・update-gate.sh --ack）

### Task 7: `pre_approve_gate` に judge ブランチ（tri-state）

**Files:**
- Modify: `scripts/check_status.py`（`pre_approve_gate` 末尾の `return 0` 直前・`run_judge_card` ヘルパ追加）
- Test: `tests/test_check_status.py`

既存の判定ゲート（review/qa/security/deploy）で、prerequisite チェック通過後にカードを live 生成し三状態を返す。qa は既存 `run_qa_drill`（B1）の後に judge カード（B1 verdict をティア1で読む）。スキップ済みゲートは n/a で、n/a の approve は update-gate.sh が既に拒否するため追加のサイズ判定は不要。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_check_status.py に追記（既存 import: json, subprocess, tempfile, Path）
class TestJudgeGate(unittest.TestCase):
    def _project(self, d, *, body, claims_block):
        root = Path(d)
        for a in (["init", "-q"], ["config", "user.email", "t@t"],
                  ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)
        (root / "seed.py").write_text("s = 0\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "i"], check=True,
                       capture_output=True)
        (root / "m.py").write_text(body, encoding="utf-8")
        docs = root / "docs"; (docs / "qa-reports").mkdir(parents=True)
        (docs / "STATUS.md").write_text(make_status_md(
            phase="review", task_type="feature", task_size="M",
            approvals={"review": "pending"},
            refs={"plan": "docs/p.md", "review": "docs/qa-reports/review.md"},
        ), encoding="utf-8")
        (docs / "qa-reports" / "review.md").write_text("# review\n\n" + claims_block,
                                                       encoding="utf-8")
        return root

    def test_review_blocks_on_stub(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._project(d, body="def f():\n    pass  # stub\n",
                                 claims_block="```claims\nno_stubs: true\nverdict: approve\n```\n")
            rc, out = run_check(str(root), "--pre-approve-gate", "review")
            self.assertEqual(rc, 1, out)

    def test_review_yellow_when_second_opinion_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._project(
                d, body="def f():\n    return 1\n",
                claims_block="```claims\nno_stubs: true\nverdict: approve\n```\n")
            rc, out = run_check(str(root), "--pre-approve-gate", "review")
            self.assertEqual(rc, 2, out)
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_check_status.TestJudgeGate -v`
Expected: FAIL（judge ブランチ未実装＝review が🟡/🔴を返さず 0）

- [ ] **Step 3: 最小実装**（`scripts/check_status.py`）

`run_qa_drill` の近傍に追加:

```python
JUDGE_GATES = ("review", "qa", "security", "deploy")


def run_judge_card(gate: str, root: Path) -> int:
    """Build the B2 judge card live at approval. Returns tri-state 0/1/2.
    Builder crash => 1 (fail-closed)."""
    builder = Path(__file__).resolve().parent / "build-judge-card.py"
    if not builder.is_file():
        print(f"ERROR: judge ビルダーが見つかりません: {builder}")
        return 1
    try:
        proc = subprocess.run(
            ["python3", str(builder), "--gate", gate, "--root", str(root)],
            capture_output=True, text=True,
        )
    except OSError as exc:
        print(f"ERROR: judge ビルダー起動失敗: {exc}")
        return 1
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    return proc.returncode if proc.returncode in (0, 1, 2) else 1
```

`pre_approve_gate` 末尾、既存 qa drill ブランチを judge へ拡張し、最後の `return 0` 直前に:

```python
    # --- B1 test-strength drill (qa) ---
    if gate_name == "qa":
        if run_qa_drill(root) != 0:
            return 1

    # --- B2 judge card (review/qa/security/deploy, tri-state) ---
    if gate_name in JUDGE_GATES:
        rc = run_judge_card(gate_name, root)
        if rc != 0:
            return rc  # 1=🔴 block / 2=🟡 needs ack

    return 0
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_check_status.TestJudgeGate -v`
Expected: PASS（2 tests）。既存 review/security/deploy を approve する他テストが claims 不在で🟡(2) になり壊れる場合は Task 13 で対応。

- [ ] **Step 5: example へミラー＋コミット**

```bash
cp scripts/check_status.py examples/minimal-project/scripts/check_status.py
git add scripts/check_status.py examples/minimal-project/scripts/check_status.py tests/test_check_status.py
git commit -m "feat(b2): pre_approve_gate builds judge card (tri-state) at review/qa/security/deploy"
```

### Task 8: `update-gate.sh` の三状態解釈＋`--ack "理由"`

**Files:**
- Modify: `scripts/update-gate.sh`（引数解析＋approve ケース・現状 line 19/103-110）
- Test: Phase 4 のスモークで検証（シェル＋実プロジェクト構造が必要なため）

- [ ] **Step 1: 引数に ack を追加**（line 19 付近）

```bash
ACTION="${2:-approve}"
ACK_FLAG="${3:-}"
ACK_REASON="${4:-}"
```

- [ ] **Step 2: approve ケースの rc 解釈を三状態化**（現 line 103-110 を置換）

```bash
    set +e
    GATE_CHECK=$(python3 "${SCRIPT_DIR}/check_status.py" --root "$ROOT" --pre-approve-gate "$GATE_NAME" 2>&1)
    GATE_CHECK_RC=$?
    set -e
    if [ -n "$GATE_CHECK" ]; then
      echo "$GATE_CHECK"
    fi
    if [ "$GATE_CHECK_RC" -eq 1 ]; then
      exit 1
    fi
    if [ "$GATE_CHECK_RC" -eq 2 ]; then
      if [ "$ACK_FLAG" != "--ack" ] || [ -z "$ACK_REASON" ]; then
        echo ""
        echo "🟡 要確認の項目があります（上記）。承認するには理由を添えてください:"
        echo "  bash scripts/update-gate.sh $GATE_NAME approve --ack \"確認した理由\""
        exit 1
      fi
      CARD="${ROOT}/docs/qa-reports/judge-${GATE_NAME}.md"
      if [ -f "$CARD" ]; then
        printf '\n## ACK\n- %s （%s）\n' "$ACK_REASON" "$(date '+%Y-%m-%d %H:%M')" >> "$CARD"
      fi
      echo "[gate-ack] $GATE_NAME: 🟡 を ack で承認（理由記録: $CARD）"
    fi
```

> 既存 `if [ $GATE_CHECK_RC -ne 0 ]` ブロックはこの置換で消える（三状態へ移行）。`set -euo pipefail` 下なので未使用変数に注意（`ACK_FLAG`/`ACK_REASON` は `:-` 既定で安全）。

- [ ] **Step 3: 手動スモーク**（Phase 4 Task 15 に統合）

- [ ] **Step 4: example へミラー＋コミット**

```bash
cp scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
git add scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
git commit -m "feat(b2): update-gate.sh tri-state + --ack reason recording"
```

---

---

## Phase 4: recorder・登録・/judge・claims 規約・移行・検証

### Task 9: テスト結果レコーダ `record-test-result.py`

**Files:**
- Create: `scripts/record-test-result.py`（+example mirror）
- Test: `tests/test_judge_card.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestRecorder(unittest.TestCase):
    REC = Path(__file__).resolve().parent.parent / "scripts" / "record-test-result.py"
    def _git(self, root, *a):
        sp.run(["git", "-C", str(root), *a], check=True, capture_output=True)

    def test_records_green(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._git(root, "init", "-q"); self._git(root, "config", "user.email", "t@t")
            self._git(root, "config", "user.name", "t")
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            self._git(root, "add", "-A"); self._git(root, "commit", "-qm", "i")
            (root / "a.py").write_text("x=1\ny=2\n", encoding="utf-8")
            sp.run(["python3", str(self.REC), "--root", str(root), "true"],
                   check=True, capture_output=True)
            data = json.loads((root / "docs/qa-reports/test-result.json").read_text())
            self.assertEqual(data["status"], "green")
            self.assertEqual(data["code_fingerprint"], judge.code_fingerprint(root))
```

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m unittest tests.test_judge_card.TestRecorder -v`
Expected: FAIL（recorder 不在）

- [ ] **Step 3: 最小実装**

```python
#!/usr/bin/env python3
"""Record a test result for the B2 judge card: run the (trusted, scoped) test
command and write docs/qa-reports/test-result.json with {status, fingerprint}.
Kept separate from the judge builder so the builder stays a pure reader."""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Record test result (B2)")
    p.add_argument("--root", default=".")
    p.add_argument("command")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    drill = _load("drill_mod", "run-test-strength-drill.py")
    judge = _load("judge_mod", "build-judge-card.py")
    status_code = drill._execute(args.command, root, 600)[0]
    status = "green" if status_code == "passed" else "red"
    out = root / "docs" / "qa-reports" / "test-result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"status": status, "code_fingerprint": judge.code_fingerprint(root)}),
        encoding="utf-8")
    print(f"recorded: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テスト合格を確認**

Run: `python3 -m unittest tests.test_judge_card.TestRecorder -v`
Expected: PASS

- [ ] **Step 5: ミラー＋コミット**

```bash
cp scripts/record-test-result.py examples/minimal-project/scripts/record-test-result.py
git add scripts/record-test-result.py examples/minimal-project/scripts/record-test-result.py tests/test_judge_card.py
git commit -m "feat(b2): test-result recorder (pure builder reads it)"
```

### Task 10: mirror identity ＋ full プロファイル登録

**Files:**
- Modify: `scripts/check_reference_drift.py`（`MIRROR_FILES`）／`templates/profiles/full.json`
- Test: `tests/test_mirror_identity.py`

- [ ] **Step 1: 失敗するテストを書く**（test_mirror_identity に追記）

```python
def test_b2_scripts_registered_in_mirror_files(self):
    from check_reference_drift import MIRROR_FILES
    for name in ("build-judge-card.py", "record-test-result.py"):
        self.assertIn(Path("scripts") / name, MIRROR_FILES)
```

- [ ] **Step 2: 失敗を確認** → Run: `python3 -m unittest tests.test_mirror_identity -v` → FAIL

- [ ] **Step 3: 実装**（`check_reference_drift.py` の `MIRROR_FILES` に追加）

```python
    Path("scripts") / "build-judge-card.py",
    Path("scripts") / "record-test-result.py",
```

`templates/profiles/full.json` の `recommended` に追加:

```json
    "scripts/build-judge-card.py",
    "scripts/record-test-result.py",
```

- [ ] **Step 4: 検証** → `python3 -m unittest tests.test_mirror_identity` ＋ `python3 scripts/check_reference_drift.py` ＋ `python3 scripts/check_framework_contract.py --profile=full` 全 PASS

- [ ] **Step 5: コミット**

```bash
git add scripts/check_reference_drift.py templates/profiles/full.json tests/test_mirror_identity.py
git commit -m "feat(b2): register judge builder + recorder in mirror and full profile"
```

### Task 11: `/judge` コマンド

**Files:**
- Create: `.claude/commands/judge.md`（+example mirror）

- [ ] **Step 1: 作成**（テスト不要のコマンド定義。本文）

```markdown
---
description: Preview the judge card for the current/specified gate (read-only)
allowed-tools: Bash, Read
---

# /judge

非エンジニア向けの judge カードをプレビューする（承認はしない）。

1. 引数があればそのゲート、無ければ `docs/STATUS.md` の phase から対象ゲートを決める:
   - phase が review/qa/security/deploy → そのゲート
   - フェーズ間（implement 等）→ 次に控える judge ゲート（implement→review）
2. 実行: `python3 scripts/build-judge-card.py --gate <gate> --root .`
3. 生成された `docs/qa-reports/judge-<gate>.md` を読んで提示し、🔴/🟡/🟢 と
   「あなたが取るアクション」を平易日本語で説明する（判定は機械が決定済み）。
```

- [ ] **Step 2: ミラー＋コミット**

```bash
cp .claude/commands/judge.md examples/minimal-project/.claude/commands/judge.md
git add .claude/commands/judge.md examples/minimal-project/.claude/commands/judge.md
git commit -m "feat(b2): /judge preview command"
```

> 注: `.claude/commands/` は README/contract と整合チェックされる場合がある。`check_reference_drift.py`／`check_framework_contract.py` を実行し、commands カウントや README 参照の更新が要求されたら追従する。

### Task 12: claims 規約と盲検2次（agent / skill）

**Files:**
- Modify: `.claude/agents/reviewer.md`, `qa.md`, `security.md`（+mirror）
- Modify: `.claude/skills/aegis-review-gate/SKILL.md`, `aegis-security-gate/SKILL.md`（+mirror）

- [ ] **Step 1: 各 agent に claims 規約を追記**（テスト不要・ドキュメント）。レポート末尾に固定形式で:

````markdown
## 機械照合用クレーム（必須・judge カードが裏取りする）

レポートに次の fenced ブロックを必ず含める（ハーネスが実測で照合し、虚偽は🔴）:

```claims
tests_pass: true|false
no_stubs: true|false
verdict: approve|reject|approve_with_notes
```

- security は `no_secrets`/`deps_clean` も記載。
- 主張は実測で裏取りされるので、確認していないことを true にしない。
````

- [ ] **Step 2: review/security skill に盲検2次を追記**:

````markdown
## 盲検 第2意見（review/security・self-attested）

1次レビュー確定後、**1次の verdict/コメントを渡さず**（fresh context・diff と spec/plan のみ）、
別観点エージェント（例 `reviewer-maintainability`）で独立2次レビューを1回ディスパッチし、
結果を 1次レポートの `claims` ブロックに記録する:

```claims
second_opinion:
  verdict: approve|reject|approve_with_notes
  divergence_points: ["..."]
```

注: ハーネスは2次の存在と相違のみ強制でき、実走/盲検は検証できない（カードで
self-attested と明示される）。形式的に書かず、実際に独立レビューを回すこと。
````

- [ ] **Step 3: ミラー＋コミット**

```bash
cp .claude/agents/reviewer.md examples/minimal-project/.claude/agents/reviewer.md
cp .claude/agents/qa.md examples/minimal-project/.claude/agents/qa.md
cp .claude/agents/security.md examples/minimal-project/.claude/agents/security.md
cp .claude/skills/aegis-review-gate/SKILL.md examples/minimal-project/.claude/skills/aegis-review-gate/SKILL.md
cp .claude/skills/aegis-security-gate/SKILL.md examples/minimal-project/.claude/skills/aegis-security-gate/SKILL.md
git add .claude/agents .claude/skills examples/minimal-project/.claude
git commit -m "docs(b2): claims convention + blind second-opinion in agents/skills"
```

### Task 13: 既存テスト/example の移行（review/security/deploy approve 経路）

**Files:**
- Modify: `tests/test_extractors.py`（TestPreApproveGateMapping の `_run`）ほか grep 結果
- Modify: `examples/minimal-project/docs/STATUS.md`（必要時）

> **背景**: judge ブランチにより review/qa/security/deploy の `pre_approve_gate` が judge カードを生成する。claims/git/レポートが無いと🟡(2)、ビルダー例外で🔴(1)になり、prereq 検証目的の既存テストが壊れる。

- [ ] **Step 1: 影響範囲を特定**

Run: `grep -rn "pre-approve-gate \(review\|security\|deploy\)\|pre_approve_gate(\"\(review\|security\|deploy\)" tests/ examples/ 2>/dev/null`

- [ ] **Step 2: prereq テストに「judge が🟢になる最小 fixture」を注入**。`TestPreApproveGateMapping._run` に、temp に git 初期化＋review レポート（claims 全 true＋second_opinion approve）＋現指紋に一致する green な `test-result.json` を作るヘルパを足し、review/security/deploy の判定が🟢(0)になるようにする（prereq ロジックを isolate）。qa は既存 skip-drill 同様に対応。

- [ ] **Step 3: 回帰確認＋コミット**

Run: `python3 -m unittest discover -s tests`
Expected: 全 green

```bash
git add -A
git commit -m "test(b2): migrate prereq-logic tests to pass the judge card"
```

### Task 14: architecture-overview に反映

- [ ] **Step 1: 追記**（ハードゲート節）: 「review/qa/security/deploy 承認時に `build-judge-card.py` が判定カードを live 生成。ティア1機械事実の決定論的矛盾は🔴ブロック、第2意見(self-attested)の相違は🟡 ack。`/judge` でプレビュー。」＋ scripts 一覧に2スクリプト。
- [ ] **Step 2: コミット** `git commit -m "docs(b2): document judge card in architecture overview"`

### Task 15: 統合検証

- [ ] **Step 1: 全テスト** → `python3 -m unittest discover -s tests -v` 全 PASS
- [ ] **Step 2: contract/drift/strict** → `check_framework_contract --profile=full/standard`・`check_reference_drift.py`・`check_status.py --root . --strict` 全 PASS
- [ ] **Step 3: scaffold smoke** → `python3 scripts/eval_scaffold_smoke.py` PASS
- [ ] **Step 4: update-gate.sh 実スモーク**: 一時プロジェクトで review を🟡にし、素の `approve` が停止・`approve --ack "理由"` で承認＆カードに ACK 記録、🔴（スタブ）で `--ack` でも停止、を確認。
- [ ] **Step 5: 証拠コミット** `git commit -m "test(b2): full integration verification green"`

---

## Self-Review（プラン執筆者チェック・実施済み）

- **spec カバレッジ**: §6.1 builder=Task1-6 / §6.2 claims 形式=Task1 / §6.3 無条件ティア1＋指紋キャッシュ=Task2,3,5 / §6.4 tri-state 結合=Task7 / §6.5 ack=Task8 / §6.6 /judge=Task11 / §6.7 claims・盲検2次=Task12 / §1.5 移行=Task13 / レコーダ（決定1）=Task9 / 登録=Task10 / docs=Task14。**未カバーなし**。
- **プレースホルダ**: `scan_secrets`/`audit_deps` は Task3/6 の注記で「同型実装」と明示（コードは check-secrets パターン移植＋audit ツール検出）。実装者はこの2関数を書くこと＝唯一の "後で書く" 項目だが、形・入出力・呼出箇所は確定済み。
- **型/名称整合**: `read_claims`/`code_fingerprint`/`scan_stubs`/`scan_secrets`/`read_test_result`/`audit_deps`/`resolve_gate_report`/`collect_facts`/`compute_verdict`(→`Verdict.overall`)/`render_card`/`build`/`main`、`run_judge_card`/`JUDGE_GATES`、recorder の `_load` は全 Task 一致。終了コード 0/1/2 の意味は builder/pre_approve_gate/update-gate.sh で一貫。
- **既知の留意**: (1) Task13 の影響範囲は grep で確定。(2) `import subprocess` は B1 で check_status.py に追加済み（再追加不要）。(3) ビルダーは LLM を起動しない（2次は claims から読むのみ）。

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-06-07-v1-b2-judge-visualization-plan.md`. Two execution options:

1. **Subagent-Driven（推奨）** — タスクごとに新鮮な subagent＋2段レビュー。`superpowers:subagent-driven-development`。
2. **Inline Execution** — 本セッションで `superpowers:executing-plans`・チェックポイント付き。

どちらで進めますか。
