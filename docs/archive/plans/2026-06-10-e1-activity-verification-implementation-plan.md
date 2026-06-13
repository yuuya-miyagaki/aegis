# E1 Activity Verification 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** エージェントの「テストした」という自己申告ではなく、hook が観測した Bash 実行記録（evidence-log）を judge card の唯一のテスト判定ソースにする。

**Architecture:** PostToolUse/PostToolUseFailure(Bash) が全 Bash 実行のメタを `.claude/evidence-log.jsonl` に追記（記録=fail-open）。ゲート承認時に `build-judge-card.py` がログを分類・worktree fingerprint で鮮度照合し tri-state 判定（判定=fail-closed: 記録なし/不一致は 🟡 unverified）。fingerprint は `hooks/lib/fingerprint.sh` が単一所有し、Python はサブプロセス呼出しで利用（bash/python 二重実装の drift を排除）。

**Tech Stack:** bash 3.2 互換（BSD/macOS）、Python 3.9、python3 -m unittest、git、shasum/sha256sum

**参照設計:** `docs/specs/2026-06-10-e1-activity-verification-design.md`
**要件:** `docs/evolution-review-2026-06-10.md` §5 E1

**スコープ外:** grill 🟢4件（check-deploy-gate stderr / update-gate TOCTOU / stale lock 回収 / WRITE_INDICATORS 左境界）は本計画に同梱しない（E1 の改修ファイルと重なりが薄く、L タスクの焦点を保つため別 S/M バッチで実施）。

**設計からの逸脱（2件・要承認）:**

1. スキーマの `out_sha`（出力先頭 64KB の sha256）を `payload_sha`（hook 生入力 JSON 先頭 64KB の sha256）に変更する。理由: 記録経路は pure-bash 制約があり、JSON 内の出力本文抽出は python3 なしでは忠実に行えない。生ペイロードはコマンドと応答の両方を含むため監査価値は同等。Task 12 で spec も同期する。
2. fingerprint の比較基準を spec の「merge-base 比」から「HEAD（無ければ empty-tree）比＋ **HEAD コミット sha をハッシュ入力に混入**」に変更する。理由: merge-base はブランチ運用前提であり、main 直行開発の aegis では HEAD 比と同値、かつ既存 `resolve_diff_ref`（run-test-strength-drill.py）と整合。HEAD sha 混入は grill-plan 🔴1 対応 — これが無いと「コミット→テスト→さらにコミット」でクリーンツリー同士の fp が一致し、未テストコードが green 認証される。Task 12 で spec も同期する。

**運用注記（grill-plan 🟢8）:** aegis フレームワーク repo 自身には `.claude/settings.json` が無く observer hook は発火しない。よって v1.5.0 自身のゲート承認では、テスト行は `python3 scripts/record-test-result.py --root . "python3 -m unittest discover -s tests"` の手動記録（src:"manual"）で green 化するか、🟡 unverified を `--ack` する。

**作業ディレクトリ:** リポジトリは `aegis/`（ネスト git repo）。全コマンドは aegis ルートで実行する。

**テスト実行の作法:** pytest は無い。`python3 -m unittest tests.test_<name> -v` を使う。BSD sed（`sed -i ''`）。

---

### Task 1: hooks/lib/fingerprint.sh（worktree fingerprint の単一所有者）

**Files:**
- Create: `hooks/lib/fingerprint.sh`
- Test: `tests/test_fingerprint_lib.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_fingerprint_lib.py` を新規作成:

```python
#!/usr/bin/env python3
"""fingerprint.sh — worktree fingerprint 単一所有者の契約テスト。

トークン契約: stdout 1行 = 64-hex sha256 | "oversize" | "nogit" | "error"、
常に rc=0。判定対象: HEAD コミット sha（無ければ empty-tree 定数）＋
HEAD 比の変更ファイル＋未追跡ファイル。docs/ と .claude/ プレフィックスは
除外（build-judge-card NONCODE_PREFIXES と同義）。
HEAD sha をハッシュ入力に混入する理由: クリーンツリー同士の fp 一致で
未テストの新コミットが green 認証されるのを防ぐ（grill-plan 🔴1）。
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FP = ROOT / "hooks" / "lib" / "fingerprint.sh"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def run_fp(root: Path, env_extra: dict | None = None) -> str:
    import os
    env = os.environ.copy()
    env.update(env_extra or {})
    proc = subprocess.run(["bash", str(FP), str(root)],
                          capture_output=True, text=True, timeout=60, env=env)
    assert proc.returncode == 0, f"rc={proc.returncode} stderr={proc.stderr}"
    return proc.stdout.strip()


def make_repo(d: Path) -> None:
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "init"], check=True)


class TestFingerprint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nogit_token(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(run_fp(Path(d)), "nogit")

    def test_clean_tree_is_deterministic_hex(self):
        a = run_fp(self.root)
        b = run_fp(self.root)
        self.assertRegex(a, HEX64)
        self.assertEqual(a, b)

    def test_untracked_code_file_changes_fp(self):
        before = run_fp(self.root)
        (self.root / "app.py").write_text("print(1)\n")
        after = run_fp(self.root)
        self.assertNotEqual(before, after)
        self.assertRegex(after, HEX64)

    def test_content_change_changes_fp(self):
        (self.root / "app.py").write_text("print(1)\n")
        a = run_fp(self.root)
        (self.root / "app.py").write_text("print(2)\n")
        b = run_fp(self.root)
        self.assertNotEqual(a, b)

    def test_docs_and_claude_excluded(self):
        (self.root / "app.py").write_text("print(1)\n")
        base = run_fp(self.root)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "STATUS.md").write_text("x\n")
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "snap").write_text("y\n")
        self.assertEqual(run_fp(self.root), base)

    def test_oversize_by_file_count(self):
        (self.root / "a.py").write_text("1\n")
        (self.root / "b.py").write_text("2\n")
        self.assertEqual(
            run_fp(self.root, {"AEGIS_FP_MAX_FILES": "1"}), "oversize")

    def test_oversize_by_bytes(self):
        (self.root / "big.py").write_text("x" * 100)
        self.assertEqual(
            run_fp(self.root, {"AEGIS_FP_MAX_BYTES": "10"}), "oversize")

    def test_repo_without_head_uses_empty_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "-C", d, "init", "-q"], check=True)
            (root / "app.py").write_text("print(1)\n")
            self.assertRegex(run_fp(root), HEX64)

    def test_new_commit_changes_fp_even_when_tree_clean(self):
        # grill-plan 🔴1: クリーンツリー同士でも HEAD が進めば fp は変わる。
        # さもなくば「コミット→テスト→さらにコミット」で未テストコードが
        # 記録時 fp と一致し green 認証される。
        a = run_fp(self.root)
        (self.root / "app.py").write_text("print(1)\n")
        subprocess.run(["git", "-C", str(self.root), "add", "app.py"],
                       check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-q", "-m", "x"],
                       check=True)
        b = run_fp(self.root)  # ツリーは再びクリーン
        self.assertRegex(b, HEX64)
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m unittest tests.test_fingerprint_lib -v`
Expected: 全ケース FAIL/ERROR（fingerprint.sh が存在しない）

- [ ] **Step 3: fingerprint.sh を実装**

`hooks/lib/fingerprint.sh` を新規作成:

```bash
#!/usr/bin/env bash
# Worktree fingerprint — SINGLE OWNER of the evidence-binding fingerprint.
# Binds an observed execution to the exact code it ran against (E1).
#
# Contract (consumed by evidence.sh and build-judge-card.py current_fingerprint):
#   stdout = one token: 64-hex sha256 | "oversize" | "nogit" | "error"; rc=0 on
#   all of these paths. Readers must require a 64-hex value before trusting
#   equality (token==token must never certify, e.g. nogit==nogit).
#
# Hash input = HEAD commit sha (empty-tree constant when no commits) + changed
# files vs HEAD + untracked files. Mixing in the HEAD sha is load-bearing:
# without it, any two clean trees share one fingerprint and a NEW untested
# commit would match an old recording (silent green). docs/ and .claude/ are
# excluded (mirrors build-judge-card NONCODE_PREFIXES) so documentation and
# harness bookkeeping never invalidate a recording. A failing git diff returns
# "error", never an empty list (an empty list would alias the clean-tree hash).
#
# Source: source "$(dirname "$0")/lib/fingerprint.sh"
# Exec:   bash hooks/lib/fingerprint.sh <root>

AEGIS_FP_MAX_FILES="${AEGIS_FP_MAX_FILES:-200}"
AEGIS_FP_MAX_BYTES="${AEGIS_FP_MAX_BYTES:-10485760}"
AEGIS_FP_EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# sha256 via shasum (macOS) or sha256sum (Linux). stdin -> 64-hex on stdout.
_fp_sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
  else
    sha256sum | awk '{print $1}'
  fi
}

fingerprint_worktree() {
  local root="${1:-.}"
  if ! git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'nogit\n'
    return 0
  fi
  local head="$AEGIS_FP_EMPTY_TREE" ref="$AEGIS_FP_EMPTY_TREE"
  if git -C "$root" rev-parse --verify -q HEAD >/dev/null 2>&1; then
    head=$(git -C "$root" rev-parse HEAD 2>/dev/null) || { printf 'error\n'; return 0; }
    ref="HEAD"
  fi
  local diff_files untracked_files
  diff_files=$(git -C "$root" diff --name-only "$ref" -- 2>/dev/null) \
    || { printf 'error\n'; return 0; }
  untracked_files=$(git -C "$root" ls-files --others --exclude-standard 2>/dev/null) \
    || { printf 'error\n'; return 0; }
  local files
  files=$(printf '%s\n%s\n' "$diff_files" "$untracked_files" \
           | LC_ALL=C sort -u | grep -v -e '^docs/' -e '^\.claude/' -e '^$' || true)
  local count=0 bytes=0 rel size
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    count=$((count + 1))
    if [ -f "$root/$rel" ]; then
      size=$(wc -c < "$root/$rel" 2>/dev/null | tr -d '[:space:]') || size=0
      bytes=$((bytes + ${size:-0}))
    fi
  done <<EOF_COUNT
$files
EOF_COUNT
  if [ "$count" -gt "$AEGIS_FP_MAX_FILES" ] || [ "$bytes" -gt "$AEGIS_FP_MAX_BYTES" ]; then
    printf 'oversize\n'
    return 0
  fi
  {
    printf 'head:%s\n' "$head"
    while IFS= read -r rel; do
      [ -n "$rel" ] || continue
      printf '%s' "$rel"
      cat "$root/$rel" 2>/dev/null || printf '<unreadable>'
    done <<EOF_HASH
$files
EOF_HASH
  } | _fp_sha256
}

# Direct execution (python callers): bash fingerprint.sh <root>
if [ "${BASH_SOURCE[0]:-}" = "$0" ]; then
  fingerprint_worktree "${1:-.}"
fi
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m unittest tests.test_fingerprint_lib -v`
Expected: 9 tests PASS

- [ ] **Step 5: コミット**

```bash
git add hooks/lib/fingerprint.sh tests/test_fingerprint_lib.py
git commit -m "feat(e1): add fingerprint.sh — single owner of worktree fingerprint"
```

---

### Task 2: hooks/lib/evidence.sh（記録・ローテーション）

**Files:**
- Create: `hooks/lib/evidence.sh`
- Test: `tests/test_evidence_lib.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_evidence_lib.py` を新規作成:

```python
#!/usr/bin/env python3
"""evidence.sh — evidence-log 追記/ローテーションの契約テスト。

記録は fail-open（常に rc=0・本体を止めない）。スキーマ:
{"v":1,"ts":...,"src":"observed","cmd":...,"status":"ok|fail",
 "payload_sha":...,"fp":...}
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "evidence.sh"
LOG_REL = ".claude/evidence-log.jsonl"


def run_append(root: Path, status: str, payload: str,
               env_extra: dict | None = None) -> int:
    import os
    env = os.environ.copy()
    env.update(env_extra or {})
    script = (f'source "{LIB}"; '
              f'append_evidence "{root}" {status} "$(cat)"')
    proc = subprocess.run(["bash", "-c", script], input=payload,
                          capture_output=True, text=True, timeout=60, env=env)
    return proc.returncode


def run_rotate(root: Path, env_extra: dict | None = None) -> int:
    import os
    env = os.environ.copy()
    env.update(env_extra or {})
    script = f'source "{LIB}"; rotate_evidence_log "{root}"'
    proc = subprocess.run(["bash", "-c", script],
                          capture_output=True, text=True, timeout=60, env=env)
    return proc.returncode


def make_repo(d: Path) -> None:
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "init"], check=True)


def payload_for(cmd: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})


class TestAppendEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def read_lines(self):
        return [json.loads(line) for line in
                self.log.read_text(encoding="utf-8").splitlines() if line]

    def test_append_ok_writes_valid_json_line(self):
        rc = run_append(self.root, "ok", payload_for("python3 -m unittest"))
        self.assertEqual(rc, 0)
        rows = self.read_lines()
        self.assertEqual(len(rows), 1)
        d = rows[0]
        self.assertEqual(d["v"], 1)
        self.assertEqual(d["src"], "observed")
        self.assertEqual(d["status"], "ok")
        self.assertEqual(d["cmd"], "python3 -m unittest")
        self.assertRegex(d["payload_sha"], r"^[0-9a-f]{64}$")
        self.assertRegex(d["fp"], r"^[0-9a-f]{64}$")
        self.assertIn("T", d["ts"])

    def test_append_fail_status(self):
        run_append(self.root, "fail", payload_for("pytest"))
        self.assertEqual(self.read_lines()[0]["status"], "fail")

    def test_cmd_with_quotes_and_newlines_stays_valid_json(self):
        cmd = 'echo "a\nb"\tc\\d'
        run_append(self.root, "ok", payload_for(cmd))
        rows = self.read_lines()  # json.loads が通ること自体が検証
        self.assertEqual(len(rows), 1)

    def test_cmd_truncated_to_500(self):
        run_append(self.root, "ok", payload_for("x" * 1000))
        self.assertEqual(len(self.read_lines()[0]["cmd"]), 500)

    def test_broken_payload_still_rc0_and_appends(self):
        rc = run_append(self.root, "ok", "not-json{{{")
        self.assertEqual(rc, 0)
        rows = self.read_lines()
        self.assertEqual(rows[0]["cmd"], "")  # コマンド抽出不能でも記録は残る

    def test_append_is_appending(self):
        run_append(self.root, "ok", payload_for("a"))
        run_append(self.root, "fail", payload_for("b"))
        self.assertEqual([r["cmd"] for r in self.read_lines()], ["a", "b"])


class TestRotate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def test_rotate_creates_empty_file_when_absent(self):
        rc = run_rotate(self.root)
        self.assertEqual(rc, 0)
        self.assertTrue(self.log.is_file())
        self.assertEqual(self.log.read_text(encoding="utf-8"), "")

    def test_rotate_keeps_small_file(self):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_text('{"v":1}\n')
        run_rotate(self.root)
        self.assertEqual(self.log.read_text(encoding="utf-8"), '{"v":1}\n')
        self.assertFalse((self.root / (LOG_REL + ".1")).exists())

    def test_rotate_moves_oversized_to_dot1(self):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_text('{"v":1}\n' * 10)
        run_rotate(self.root, {"AEGIS_EVIDENCE_MAX_BYTES": "10"})
        self.assertTrue((self.root / (LOG_REL + ".1")).is_file())
        self.assertEqual(self.log.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m unittest tests.test_evidence_lib -v`
Expected: 全ケース FAIL/ERROR（evidence.sh 不在）

- [ ] **Step 3: evidence.sh を実装**

`hooks/lib/evidence.sh` を新規作成:

```bash
#!/usr/bin/env bash
# Evidence log writer — append-only observation of Bash executions (E1).
#
# Policy (docs/hook-failure-policy.md): recording is fail-open BY DESIGN —
# the observer must never break the session. A missing record fail-closes at
# the DECISION point instead (judge card reports 🟡 unverified), so a dead
# observer can degrade but never silently certify.
#
# Schema (one JSON line per execution):
#   {"v":1,"ts":"<utc>","src":"observed","cmd":"<first 500 chars>",
#    "status":"ok|fail","payload_sha":"<sha256 of first 64KB of raw hook
#    stdin>","fp":"<fingerprint.sh token>"}
# record-test-result.py appends the same schema with src:"manual".
#
# Source: source "$(dirname "$0")/lib/evidence.sh"

_EV_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_EV_LIB_DIR}/extract-input.sh"
source "${_EV_LIB_DIR}/emit.sh"
source "${_EV_LIB_DIR}/fingerprint.sh"

AEGIS_EVIDENCE_MAX_BYTES="${AEGIS_EVIDENCE_MAX_BYTES:-1048576}"

evidence_log_path() { printf '%s/.claude/evidence-log.jsonl' "${1:-.}"; }

# append_evidence <root> <ok|fail> <raw-hook-input-json>  — always returns 0.
append_evidence() {
  local root="$1" status="$2" input="$3"
  local log cmd payload_sha fp ts
  log="$(evidence_log_path "$root")"
  mkdir -p "$(dirname "$log")" 2>/dev/null || return 0
  cmd="$(extract_command "$input" 2>/dev/null)" || cmd=""
  cmd="${cmd:0:500}"
  payload_sha="$(printf '%s' "${input:0:65536}" | _fp_sha256 2>/dev/null)" || payload_sha=""
  fp="$(fingerprint_worktree "$root" 2>/dev/null)" || fp="error"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts=""
  printf '{"v":1,"ts":"%s","src":"observed","cmd":"%s","status":"%s","payload_sha":"%s","fp":"%s"}\n' \
    "$ts" "$(_aegis_json_escape "$cmd")" "$status" "$payload_sha" "$fp" \
    >> "$log" 2>/dev/null || true
  return 0
}

# rotate_evidence_log <root> — size-capped rotation + liveness touch.
# The touched (possibly empty) file is the "observer layer alive" signal
# consumed by check-task-completed.sh; rotation keeps one .1 generation,
# which read_test_result also scans.
rotate_evidence_log() {
  local root="$1" log size
  log="$(evidence_log_path "$root")"
  mkdir -p "$(dirname "$log")" 2>/dev/null || return 0
  if [ -f "$log" ]; then
    size=$(wc -c < "$log" 2>/dev/null | tr -d '[:space:]') || size=0
    if [ "${size:-0}" -gt "$AEGIS_EVIDENCE_MAX_BYTES" ]; then
      mv -f "$log" "${log}.1" 2>/dev/null || true
    fi
  fi
  : >> "$log" 2>/dev/null || true
  return 0
}
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m unittest tests.test_evidence_lib -v`
Expected: 9 tests PASS

- [ ] **Step 5: コミット**

```bash
git add hooks/lib/evidence.sh tests/test_evidence_lib.py
git commit -m "feat(e1): add evidence.sh — append-only Bash execution log with rotation"
```

---

### Task 3: patterns.sh にテストランナー分類（grep -E / python re 共通サブセット）

**Files:**
- Modify: `hooks/lib/patterns.sh`（末尾に追記）
- Test: `tests/test_patterns_parity.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_patterns_parity.py` を新規作成:

```python
#!/usr/bin/env python3
"""AEGIS_TEST_RUNNER_REGEX — bash(grep -E)/python(re) パリティ契約。

パターンは両エンジンで同一判定でなければならない（分類は patterns.sh が
単一ソース、消費者は post-bash.sh=grep -E と build-judge-card.py=re の2系統）。
共有フィクスチャで両エンジンの判定一致と期待値を検証する。
禁止構文: [[:space:]] / \\b（エンジン間で挙動が割れるため）。
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "hooks" / "lib" / "patterns.sh"

# (command, is_test_runner)
FIXTURES = [
    ("python3 -m unittest discover -s tests", True),
    ("python -m unittest tests.test_x -v", True),
    ("pytest tests/ -v", True),
    ("npx vitest run", True),
    ("vitest", True),
    ("npx jest --ci", True),
    ("cargo test --all", True),
    ("go test ./...", True),
    ("npm test", True),
    ("npm run test", True),
    ("npm run test:unit", True),
    ("pnpm test", True),
    ("bun test", True),
    ("yarn test", True),
    ("echo pytest", True),   # 文字列一致は許容（記録側は全実行を保存済み）
    ("git status", False),
    ("ls -la", False),
    ("npm run build", False),
    ("go build ./...", False),
    ("python3 scripts/check_status.py", False),
    ("cargo build", False),
    ("attest something", False),
    ("protest --loud", False),
]


def bash_patterns() -> list[str]:
    out = subprocess.run(
        ["bash", "-c",
         'source "$1"; printf "%s\\n" "${AEGIS_TEST_RUNNER_REGEX[@]}"',
         "_", str(PATTERNS)],
        capture_output=True, text=True, timeout=10, check=True)
    return [l for l in out.stdout.splitlines() if l.strip()]


def grep_match(cmd: str, patterns: list[str]) -> bool:
    for p in patterns:
        r = subprocess.run(["grep", "-Eq", p],
                           input=cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return True
    return False


class TestTestRunnerParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = bash_patterns()

    def test_patterns_exist(self):
        self.assertGreaterEqual(len(self.patterns), 5)

    def test_no_engine_splitting_syntax(self):
        for p in self.patterns:
            self.assertNotIn("[[:", p, f"POSIX class in {p}")
            self.assertNotIn("\\b", p, f"\\b in {p}")

    def test_python_re_compiles(self):
        for p in self.patterns:
            re.compile(p)

    def test_fixtures_python(self):
        compiled = [re.compile(p) for p in self.patterns]
        for cmd, expected in FIXTURES:
            got = any(c.search(cmd) for c in compiled)
            self.assertEqual(got, expected, f"python re: {cmd!r}")

    def test_fixtures_grep(self):
        for cmd, expected in FIXTURES:
            got = grep_match(cmd, self.patterns)
            self.assertEqual(got, expected, f"grep -E: {cmd!r}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m unittest tests.test_patterns_parity -v`
Expected: FAIL（AEGIS_TEST_RUNNER_REGEX 未定義 → bash_patterns が空/エラー）

- [ ] **Step 3: patterns.sh に追記**

`hooks/lib/patterns.sh` 末尾に追加:

```bash
# Test-runner classification patterns (E1 activity verification).
# Consumed by post-bash.sh (grep -E) and build-judge-card.py (python re).
# CONSTRAINT: stay within the regex subset that behaves identically in BSD/GNU
# `grep -E` AND Python `re` — no [[:space:]], no \b. Use ( |^|$) style
# boundaries instead. tests/test_patterns_parity.py enforces parity with
# shared fixtures; add a fixture line whenever you add a pattern.
AEGIS_TEST_RUNNER_REGEX=(
  '(^|[^a-zA-Z0-9_])(npx +)?vitest($|[^a-zA-Z0-9_])'
  '(^|[^a-zA-Z0-9_])(npx +)?jest($|[^a-zA-Z0-9_])'
  '(^|[^a-zA-Z0-9_])pytest($|[^a-zA-Z0-9_])'
  '(^|[^a-zA-Z0-9_])python3? +-m +unittest($|[^a-zA-Z0-9_])'
  '(^|[^a-zA-Z0-9_])cargo +test($|[^a-zA-Z0-9_])'
  '(^|[^a-zA-Z0-9_])go +test($|[^a-zA-Z0-9_])'
  '(^|[^a-zA-Z0-9_])(npm|pnpm|bun|yarn) +(run +)?test(:[-a-zA-Z0-9_]+)?($|[^a-zA-Z0-9_])'
)
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m unittest tests.test_patterns_parity -v`
Expected: 5 tests PASS。fixture が落ちる場合はパターン側を直す（fixture の期待値が正）

- [ ] **Step 5: ミラー同期＋コミット**

patterns.sh は mirror 比較対象（check_reference_drift.py MIRROR_DIRS の hooks/）のため、同一コミットで同期する（grill-plan 🟡7: 中間コミットを赤にしない）:

```bash
cp hooks/lib/patterns.sh examples/minimal-project/hooks/lib/
git add hooks/lib/patterns.sh examples/minimal-project/hooks/lib/patterns.sh tests/test_patterns_parity.py
git commit -m "feat(e1): add test-runner classification patterns with grep/re parity contract"
```

---

### Task 4: hooks/post-bash-observe.sh（新規 PostToolUse/Bash hook）

**Files:**
- Create: `hooks/post-bash-observe.sh`
- Modify: `docs/hook-failure-policy.md:25` 付近（表に1行追加）
- Test: `tests/test_evidence_hooks.py`（新規）

命名注意: `tests/test_failure_policy.py` の `ROW_RE` は `post-[a-z-]+\.sh` を要求するため、hook 名は `post-bash-observe.sh` とする（`observe-bash.sh` は表で認識されない）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_evidence_hooks.py` を新規作成:

```python
#!/usr/bin/env python3
"""E1 観測 hook の実発火テスト（post-bash-observe.sh / post-bash.sh 失敗側）。"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_REL = ".claude/evidence-log.jsonl"


def fire(script: str, payload: dict, root: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["AEGIS_ROOT_OVERRIDE"] = str(root)
    proc = subprocess.run(
        ["bash", str(ROOT / "hooks" / script)],
        input=json.dumps(payload), capture_output=True, text=True,
        timeout=60, env=env)
    return proc.returncode, proc.stdout


def make_repo(d: Path) -> None:
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "init"], check=True)


def bash_payload(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd},
            "tool_response": {"exitCode": 0}}


class TestPostBashObserve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def test_records_ok_and_allows(self):
        rc, out = fire("post-bash-observe.sh",
                       bash_payload("python3 -m unittest"), self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), {})  # emit_allow
        row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["cmd"], "python3 -m unittest")

    def test_raw_garbage_input_still_allows_rc0(self):
        env = os.environ.copy()
        env["AEGIS_ROOT_OVERRIDE"] = str(self.root)
        proc = subprocess.run(
            ["bash", str(ROOT / "hooks" / "post-bash-observe.sh")],
            input="garbage not json", capture_output=True, text=True,
            timeout=60, env=env)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout), {})


class TestPostBashFailureRecords(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_hook_records_fail_status(self):
        rc, _ = fire("post-bash.sh", bash_payload("pytest tests/"), self.root)
        self.assertEqual(rc, 0)
        row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["cmd"], "pytest tests/")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m unittest tests.test_evidence_hooks -v`
Expected: post-bash-observe 系 = ERROR（hook 不在）、post-bash 失敗側 = FAIL（記録なし）

- [ ] **Step 3: post-bash-observe.sh を実装**

`hooks/post-bash-observe.sh` を新規作成:

```bash
#!/usr/bin/env bash
# PostToolUse hook for Bash (success path): record the execution into the
# evidence log (E1 activity verification). Observation only — ALWAYS allows.
# Failed executions are recorded by post-bash.sh (PostToolUseFailure).
#
# Failure policy: advisory / fail-open at record time. The missing-record case
# fail-closes at gate time (judge card 🟡 unverified) — see
# docs/hook-failure-policy.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/emit.sh"
source "${SCRIPT_DIR}/lib/evidence.sh"

DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Test fixtures isolate via AEGIS_ROOT_OVERRIDE (same as check-task-completed).
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"

INPUT=$(cat || true)
append_evidence "$ROOT" ok "$INPUT" || true
emit_allow
exit 0
```

- [ ] **Step 4: post-bash.sh に失敗記録を追加**

`hooks/post-bash.sh` の `INPUT=$(cat)` の直後（`CMD=` 抽出の前）に追加:

```bash
# E1: record the failed execution into the evidence log (success path is
# recorded by post-bash-observe.sh). Observation is fail-open.
source "${SCRIPT_DIR}/lib/evidence.sh"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"
append_evidence "$ROOT" fail "$INPUT" || true
```

さらに既存の `case "$CMD" in *vitest*|...)` ブロックを patterns.sh の単一ソースに置換:

```bash
# Only act on test runner commands (single source: patterns.sh).
source "${SCRIPT_DIR}/lib/patterns.sh"
IS_TEST=false
for _re in "${AEGIS_TEST_RUNNER_REGEX[@]}"; do
  if printf '%s' "$CMD" | grep -Eq "$_re"; then
    IS_TEST=true
    break
  fi
done
```

- [ ] **Step 5: failure-policy 表に行を追加**

`docs/hook-failure-policy.md` の表の `post-bash.sh` 行の直後に追加:

```markdown
| post-bash-observe.sh | advisory | なし | 通常動作 | allow |
```

- [ ] **Step 6: failure-policy 実発火テストに advisory ケースを追加**

grill-plan 🟡6: 自動で新行を取り込むのはパース失敗系（test_failure_policy.py:267-285）のみ。python3 遮断系（:127-166, :226-252）は固定リストのため、advisory ケース（:229-239 付近）の hook リストに `"post-bash-observe.sh"` を1行追加し、「python3 遮断でも allow」を実発火で固定する。

- [ ] **Step 7: GREEN を確認（個別＋ポリシー突合＋スキーマ）**

Run: `python3 -m unittest tests.test_evidence_hooks tests.test_failure_policy tests.test_hook_output_schema -v`
Expected: 全 PASS（表の新行はパース系が自動取込み、python3 遮断は Step 6 の追加で突合）

- [ ] **Step 8: ミラー同期＋コミット**

post-bash.sh は mirror 比較対象のため同一コミットで同期する（post-bash-observe.sh の mirror 配置は Task 5 でまとめて行う — mirror は両側存在ファイルのみ比較するため新規ファイルは中間赤にならない）:

```bash
cp hooks/post-bash.sh examples/minimal-project/hooks/
git add hooks/post-bash-observe.sh hooks/post-bash.sh examples/minimal-project/hooks/post-bash.sh docs/hook-failure-policy.md tests/test_evidence_hooks.py tests/test_failure_policy.py
git commit -m "feat(e1): add post-bash-observe hook and failure-side recording"
```

---

### Task 5: 配線（template / profiles / contract 追跡 / mirror 同期）

**Files:**
- Modify: `templates/hooks.template.json`（PostToolUse に Bash matcher 追加）
- Modify: `templates/profiles/standard.json` / `templates/profiles/full.json`（hooks_include）
- Modify: `scripts/check_framework_contract.py:126` 付近（REQUIRED_HOOK_FILES）
- Modify: `examples/minimal-project/hooks/`（mirror 同期）

- [ ] **Step 1: RED を確認（先に契約を破る状態を作る）**

`templates/hooks.template.json` の `PostToolUse` 配列に追加（既存 Edit|Write エントリの後）:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"${CLAUDE_PROJECT_DIR:-.}\"/hooks/post-bash-observe.sh"
    }
  ]
}
```

Run: `python3 -m unittest tests.test_hook_required_coverage -v`
Expected: FAIL（registered ⊆ REQUIRED 違反: post-bash-observe.sh が REQUIRED_HOOK_FILES に無い）

- [ ] **Step 2: contract 追跡に追加**

`scripts/check_framework_contract.py` の REQUIRED_HOOK_FILES リスト（`hooks/check-task-completed.sh` の行の後）に追加:

```python
    # E1 activity verification (v1.5.0): observer hook + its lib life support.
    ROOT / "hooks/post-bash-observe.sh",
    ROOT / "hooks/lib/evidence.sh",
    ROOT / "hooks/lib/fingerprint.sh",
```

- [ ] **Step 3: profiles に追加**

`templates/profiles/standard.json` の `hooks_include` に `"post-bash-observe.sh"` と `"post-bash.sh"` を追加（post-bash.sh も入れる理由: 失敗実行が記録されないと「最新一致エントリ」が古い ok を拾い偽 green になるため、観測は成功/失敗で対にする）。
`templates/profiles/full.json` の `hooks_include` に `"post-bash-observe.sh"` を追加。

- [ ] **Step 4: mirror 同期**

```bash
cp hooks/post-bash-observe.sh hooks/post-bash.sh examples/minimal-project/hooks/
cp hooks/lib/evidence.sh hooks/lib/fingerprint.sh hooks/lib/patterns.sh examples/minimal-project/hooks/lib/
```

- [ ] **Step 5: GREEN を確認**

Run: `python3 -m unittest tests.test_hook_required_coverage tests.test_mirror_identity -v && python3 scripts/check_framework_contract.py`
Expected: 全 PASS（contract は version 不一致以外エラーなし）

- [ ] **Step 6: コミット**

```bash
git add templates/hooks.template.json templates/profiles/standard.json templates/profiles/full.json scripts/check_framework_contract.py examples/minimal-project/hooks/
git commit -m "feat(e1): wire post-bash-observe into template/profiles/contract/mirror"
```

---

### Task 6: build-judge-card.py — read_test_result を観測ログ読みに置換（Task 7 と単一作業単位）

**Files:**
- Modify: `scripts/build-judge-card.py:58-111`（code_fingerprint / read_test_result）
- Modify: `examples/minimal-project/scripts/build-judge-card.py`（mirror — MIRROR_FILES 対象）
- Test: `tests/test_judge_card.py`（read_test_result 系＋TestRecorder 系＋`_project()` フィクスチャを書換え）

**結合注意（grill-plan 🔴3）:** 旧 `record-test-result.py:34` は `judge.code_fingerprint` を呼び、`tests/test_judge_card.py:374-403` の TestRecorder がそれを subprocess 実行する。`code_fingerprint` 削除と同時に旧スクリプトは AttributeError で死ぬため、**Task 6 と Task 7 は連続で実施し、GREEN 確認とコミットは Task 7 末尾でまとめて行う**（中間状態で full suite を走らせない）。また `TestVerdict._project()`（:303-321）は fixture root に hooks/lib を置かないため、改修後は `current_fingerprint` → `nolib` → tests=unverified となる。`_project()` に `shutil.copytree(ROOT / "hooks" / "lib", root / "hooks" / "lib")` ＋ git init ＋ `judge.current_fingerprint(root)` で fp を得た evidence-log 注入を追加し、green 前提のケース（`test_green_exit0` 等）を成立させること。

- [ ] **Step 1: 既存の read_test_result/test-result.json 依存テストを特定**

Run: `grep -n "test-result\|read_test_result\|code_fingerprint" tests/test_judge_card.py`
該当ケースを Step 2 の新契約に書き換える（test-result.json フィクスチャは evidence-log フィクスチャへ）。

- [ ] **Step 2: 失敗するテストを書く（書換え）**

`tests/test_judge_card.py` の read_test_result 系を以下の契約に置換（既存のテストヘルパー/フィクスチャ流儀に合わせ、tmp git repo + `hooks/lib/` 一式コピーを行うこと。コピーには `shutil.copytree(ROOT / "hooks" / "lib", root / "hooks" / "lib")` を使う）:

```python
# 新契約（evidence-log ベース）。root には hooks/lib/{fingerprint,patterns}.sh
# のコピーと git repo が必要。
def _ev_line(cmd: str, status: str, fp: str) -> str:
    return json.dumps({"v": 1, "ts": "2026-06-10T00:00:00Z", "src": "observed",
                       "cmd": cmd, "status": status,
                       "payload_sha": "0" * 64, "fp": fp}) + "\n"

class TestReadTestResultFromEvidence(unittest.TestCase):
    # setUp: tmp git repo 作成 + hooks/lib コピー + .claude/ 作成。
    # current fingerprint は judge.current_fingerprint(root) で取得して
    # fixture に埋める。

    def test_no_log_is_unverified(self):
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_ok_with_matching_fp_is_green(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("python3 -m unittest", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_fail_with_matching_fp_is_red(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("pytest", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_stale_fp_is_unverified(self):
        self.log.write_text(_ev_line("pytest", "ok", "f" * 64))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_non_test_commands_ignored(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("git status", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_latest_matching_entry_wins(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("pytest", "ok", fp) + _ev_line("pytest", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_broken_lines_skipped(self):
        fp = judge.current_fingerprint(self.root)
        self.log.write_text("{{{broken\n" + _ev_line("pytest", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_rotated_dot1_is_scanned(self):
        fp = judge.current_fingerprint(self.root)
        (self.root / ".claude" / "evidence-log.jsonl.1").write_text(
            _ev_line("pytest", "ok", fp))
        self.log.write_text("")
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_manual_src_counts(self):
        fp = judge.current_fingerprint(self.root)
        row = json.loads(_ev_line("python3 -m unittest", "ok", fp))
        row["src"] = "manual"
        self.log.write_text(json.dumps(row) + "\n")
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_oversize_current_fp_is_unverified(self):
        # AEGIS_FP_MAX_FILES=0 相当は作れないため、巨大変更を作るより
        # current_fingerprint が hex64 以外を返す経路を直接検証する:
        # hooks/lib/fingerprint.sh を削除 → "nolib" → unverified。
        import shutil
        shutil.rmtree(self.root / "hooks")
        fpval = judge.current_fingerprint(self.root)
        self.assertEqual(fpval, "nolib")
        self.assertEqual(judge.read_test_result(self.root), "unverified")
```

- [ ] **Step 3: RED を確認**

Run: `python3 -m unittest tests.test_judge_card -v`
Expected: 新ケース FAIL（current_fingerprint 未定義等）

- [ ] **Step 4: build-judge-card.py を改修**

(a) `code_fingerprint()`（scripts/build-judge-card.py:58-70）を削除し、以下に置換:

```python
def current_fingerprint(root: Path) -> str:
    """Delegate to hooks/lib/fingerprint.sh — the SINGLE OWNER of the
    fingerprint definition (a python reimplementation would drift). Returns the
    token verbatim; callers must require 64-hex before trusting equality."""
    fp_lib = root / "hooks" / "lib" / "fingerprint.sh"
    if not fp_lib.is_file():
        return "nolib"
    try:
        proc = subprocess.run(["bash", str(fp_lib), str(root)],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "error"
    if proc.returncode != 0:
        return "error"
    return proc.stdout.strip()
```

(b) `read_test_result()`（scripts/build-judge-card.py:97-111）を以下に置換:

```python
EVIDENCE_LOG_REL = Path(".claude") / "evidence-log.jsonl"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _test_runner_patterns(root: Path) -> list:
    """Load AEGIS_TEST_RUNNER_REGEX from patterns.sh (single source). The
    patterns are contract-bound to the grep-E/python-re common subset
    (tests/test_patterns_parity.py)."""
    lib = root / "hooks" / "lib" / "patterns.sh"
    if not lib.is_file():
        return []
    try:
        out = subprocess.run(
            ["bash", "-c",
             'source "$1"; printf "%s\\n" "${AEGIS_TEST_RUNNER_REGEX[@]}"',
             "_", str(lib)],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    pats = []
    for raw in out.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            pats.append(re.compile(raw))
        except re.error:
            continue
    return pats


def _evidence_entries(root: Path) -> list:
    """Parse evidence-log (rotated .1 first, then current = oldest->newest).
    Broken lines are skipped — the judge must degrade to 'unverified', never
    crash (silent-green is the only forbidden failure mode)."""
    entries = []
    for name in (str(EVIDENCE_LOG_REL) + ".1", str(EVIDENCE_LOG_REL)):
        p = root / name
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict):
                entries.append(d)
    return entries


def read_test_result(root: Path) -> str:
    """'green' / 'red' / 'unverified' from the OBSERVED evidence log (E1).

    The newest test-runner entry decides; its fp must equal the CURRENT
    worktree fingerprint (both 64-hex). Anything else — no log, no matching
    entry, stale/oversize/nogit fingerprint, unreadable patterns — is
    'unverified' (🟡 ack-able), never silent-green."""
    pats = _test_runner_patterns(root)
    if not pats:
        return "unverified"
    current = current_fingerprint(root)
    if not _HEX64.match(current):
        return "unverified"
    for d in reversed(_evidence_entries(root)):
        if d.get("status") not in ("ok", "fail"):
            continue
        cmd = d.get("cmd") or ""
        if not any(p.search(cmd) for p in pats):
            continue
        if (d.get("fp") or "") != current:
            return "unverified"
        return "green" if d.get("status") == "ok" else "red"
    return "unverified"
```

注意: `collect_facts` / `render_card` / `compute_verdict` は無変更（"tests" の値域 green/red/unverified は不変）。`code_fingerprint` の他の参照が無いことを `grep -rn "code_fingerprint" scripts/ tests/` で確認し、残参照（record-test-result.py — Task 7 で書換え）以外があれば修正する。

- [ ] **Step 5: そのまま Task 7 へ進む**

GREEN 確認・コミットは Task 7 末尾でまとめて行う（結合注意参照）。read_test_result 系の新ケースのみの部分確認は可: `python3 -m unittest tests.test_judge_card.TestReadTestResultFromEvidence -v`

---

### Task 7: record-test-result.py — 手動フォールバック書き手に改修（Task 6 の続き・同一コミット）

**Files:**
- Modify: `scripts/record-test-result.py`（全面書換え）
- Modify: `examples/minimal-project/scripts/record-test-result.py`（mirror — MIRROR_FILES 対象）
- Test: `tests/test_judge_card.py`（または record 系テストの所在に合わせる: `grep -rn "record-test-result\|record_test_result" tests/` で特定）

- [ ] **Step 1: 失敗するテストを書く**

record 系テストを以下の契約に書換え（フィクスチャ: tmp git repo + hooks/lib コピー）:

```python
class TestRecordTestResultManual(unittest.TestCase):
    def test_passing_command_appends_manual_ok(self):
        rc = record.main(["--root", str(self.root), "true"])
        self.assertEqual(rc, 0)
        row = json.loads((self.root / ".claude" / "evidence-log.jsonl")
                         .read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(row["src"], "manual")
        self.assertEqual(row["status"], "ok")
        self.assertRegex(row["fp"], r"^[0-9a-f]{64}$")

    def test_failing_command_appends_manual_fail(self):
        record.main(["--root", str(self.root), "false"])
        row = json.loads((self.root / ".claude" / "evidence-log.jsonl")
                         .read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(row["status"], "fail")

    def test_no_test_result_json_written(self):
        record.main(["--root", str(self.root), "true"])
        self.assertFalse(
            (self.root / "docs" / "qa-reports" / "test-result.json").exists())
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m unittest tests.test_judge_card -v`（record テストの所在ファイル）
Expected: 新ケース FAIL

- [ ] **Step 3: record-test-result.py を書換え**

```python
#!/usr/bin/env python3
"""Manual fallback writer for the E1 evidence log: run the (trusted, scoped)
test command itself and append the result with src:"manual". Used when tests
were run OUTSIDE Claude Code (no hook observation). Same schema as
hooks/lib/evidence.sh; the judge treats manual and observed alike because this
script executed the command itself (trusted runner, not self-report)."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Record test result (E1 manual)")
    p.add_argument("--root", default=".")
    p.add_argument("command")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    drill = _load("drill_mod", "run-test-strength-drill.py")
    judge = _load("judge_mod", "build-judge-card.py")
    status_code, output = drill._execute(args.command, root, 600)
    status = "ok" if status_code == "passed" else "fail"
    out_bytes = (output or "")[:65536].encode("utf-8", errors="replace")
    entry = {
        "v": 1,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "src": "manual",
        "cmd": args.command[:500],
        "status": status,
        "payload_sha": hashlib.sha256(out_bytes).hexdigest(),
        "fp": judge.current_fingerprint(root),
    }
    log = root / ".claude" / "evidence-log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"recorded: {'green' if status == 'ok' else 'red'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: GREEN を確認（Task 6 分も含む）＋旧 test-result.json 参照の掃除**

Run: `python3 -m unittest tests.test_judge_card -v && grep -rn "test-result.json" scripts/ hooks/ tests/ .claude/ docs/hook-failure-policy.md`
Expected: test_judge_card 全 PASS（Task 6 の judge 改修＋本タスクの recorder 改修の両方）。残参照はドキュメント類のみ（コード/テストの残参照があれば修正。skills 内の手順記述は Task 12 で更新）

- [ ] **Step 5: ミラー同期＋コミット（Task 6 と一括・grill-plan 🔴2/🔴3）**

```bash
cp scripts/build-judge-card.py scripts/record-test-result.py examples/minimal-project/scripts/
git add scripts/build-judge-card.py scripts/record-test-result.py examples/minimal-project/scripts/build-judge-card.py examples/minimal-project/scripts/record-test-result.py tests/test_judge_card.py
git commit -m "feat(e1): judge card and recorder read/write the observed evidence log"
```

---

### Task 8: check-task-completed.sh — 観測系生存チェック

**Files:**
- Modify: `hooks/check-task-completed.sh:96` 付近（next_action チェックの後）
- Test: `tests/test_hook_output_schema.py` の check-task-completed 系フィクスチャ

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_hook_output_schema.py` の `TestTaskCompletedHook`（:797 付近）に追加。実在ヘルパーは `self._write_status(next_action=...)` / `self._payload(subject)` / `run_hook(name, payload, cwd=Path(self.tmp), env=...)` →（rc, out:dict, err:str）:

```python
def test_missing_evidence_log_pushes_back(self):
    self._write_status(next_action="Move to qa phase")
    (Path(self.tmp) / ".claude" / "evidence-log.jsonl").unlink()  # setUp の touch を取り消す
    rc, out, err = run_hook(
        "check-task-completed.sh",
        self._payload("Task foo done"),
        cwd=Path(self.tmp),
        env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
    )
    self.assertEqual(rc, 2)
    self.assertEqual(out, {})
    self.assertIn("evidence-log", err)

def test_empty_evidence_log_passes(self):
    self._write_status(next_action="Move to qa phase")  # 空ファイルは setUp が touch 済み
    rc, out, err = run_hook(
        "check-task-completed.sh",
        self._payload("Task foo done"),
        cwd=Path(self.tmp),
        env={"AEGIS_ROOT_OVERRIDE": str(self.tmp)},
    )
    self.assertEqual(rc, 0)
    self.assertEqual(out, {})
```

`TestTaskCompletedHook.setUp` の `.claude` mkdir の後に `(Path(self.tmp) / ".claude" / "evidence-log.jsonl").touch()` を追加する（さもなくば既存の正常系が新チェックで全部 exit 2 になる）。next_action 空の差し戻しテスト群は生存チェックより前に exit 2 するため無影響。

- [ ] **Step 2: RED を確認**

Run: `python3 -m unittest tests.test_hook_output_schema -v 2>&1 | tail -20`
Expected: 新ケース FAIL（現状はログ不在でも pass-through）

- [ ] **Step 3: check-task-completed.sh に追加**

`hooks/check-task-completed.sh` の next_action チェックブロック（exit 2 の後、evidence integrity の前）に挿入:

```bash
# E1: observer liveness. The evidence log file is created/touched by
# session-start (rotate_evidence_log) on EVERY session, so its absence means
# the hook layer never ran in this workspace (the silent fail-open class found
# in v1.4.0 grill: CLAUDE_PROJECT_DIR unset). An empty file passes — only
# total absence pushes back. Policy: moat → 差し戻し.
if [ ! -f "${ROOT}/.claude/evidence-log.jsonl" ]; then
  printf '[task-completed] evidence-log が存在しません（hook 観測系が未稼働の可能性）。hooks 配線と session-start の発火を確認してから完了してください。\n' >&2
  exit 2
fi
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m unittest tests.test_hook_output_schema tests.test_failure_policy -v 2>&1 | tail -5`
Expected: 全 PASS（failure_policy の task-completed 行は「差し戻し」宣言のまま整合）

- [ ] **Step 5: mirror 同期＋コミット**

```bash
cp hooks/check-task-completed.sh examples/minimal-project/hooks/
git add hooks/check-task-completed.sh examples/minimal-project/hooks/check-task-completed.sh tests/test_hook_output_schema.py
git commit -m "feat(e1): task completion requires a live observer (evidence-log presence)"
```

---

### Task 9: session-start.sh — ローテーション＋生存 touch

**Files:**
- Modify: `hooks/session-start.sh:27` 付近（snapshot 初期化の後）
- Test: `tests/test_evidence_lib.py` に統合テスト1件追加

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_evidence_lib.py` に追加:

```python
class TestSessionStartRotates(unittest.TestCase):
    def test_session_start_touches_evidence_log(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_repo(root)
            (root / "docs").mkdir()
            (root / "docs" / "STATUS.md").write_text(
                "---\nmode: Dev\nphase: plan\nnext_action: x\n---\n")
            (root / "hooks").mkdir()
            (root / "hooks" / "lib").mkdir()
            for f in ("emit.sh", "frontmatter.sh", "extract-input.sh",
                      "fingerprint.sh", "evidence.sh", "patterns.sh"):
                (root / "hooks" / "lib" / f).write_bytes(
                    (ROOT / "hooks" / "lib" / f).read_bytes())
            (root / "hooks" / "session-start.sh").write_bytes(
                (ROOT / "hooks" / "session-start.sh").read_bytes())
            proc = subprocess.run(
                ["bash", str(root / "hooks" / "session-start.sh")],
                input="{}", capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0)
            self.assertTrue((root / LOG_REL).is_file())
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m unittest tests.test_evidence_lib -v`
Expected: 新ケース FAIL（ログ未作成）

- [ ] **Step 3: session-start.sh に追加**

`hooks/session-start.sh` の snapshot 初期化ブロック（`grep -m1 "^mode:" ... >> "$SNAPSHOT_FILE"` 行）の直後に追加:

```bash
# E1: rotate + touch the evidence log. The (possibly empty) file is the
# "observer layer alive" liveness signal consumed by check-task-completed.sh.
source "${SCRIPT_DIR}/lib/evidence.sh"
rotate_evidence_log "$ROOT" || true
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m unittest tests.test_evidence_lib tests.test_hook_output_schema tests.test_failure_policy -v 2>&1 | tail -5`
Expected: 全 PASS

- [ ] **Step 5: mirror 同期＋コミット**

```bash
cp hooks/session-start.sh examples/minimal-project/hooks/
git add hooks/session-start.sh examples/minimal-project/hooks/session-start.sh tests/test_evidence_lib.py
git commit -m "feat(e1): session-start rotates and touches the evidence log (liveness signal)"
```

---

### Task 10: gitignore（本体リポジトリ＋install 先）

**Files:**
- Modify: `.gitignore`
- Modify: `bin/setup.sh`（install 先の .gitignore に追記する処理）

- [ ] **Step 1: 本体 .gitignore に追加**

`.gitignore` の `# Runtime artifacts` セクションに追加:

```
.claude/evidence-log.jsonl
.claude/evidence-log.jsonl.1
```

- [ ] **Step 2: setup.sh に install 先 gitignore 追記を実装**

`bin/setup.sh` の `copy_hooks` 関数定義の後に追加し、末尾の `copy_hooks "$PROFILE_JSON" "$TARGET"` の次行で呼び出す:

```bash
ensure_target_gitignore() {
  local target="$1"
  local entries=".claude/evidence-log.jsonl
.claude/evidence-log.jsonl.1
.claude/.gate-snapshot
.claude/.task-event-debug.log"
  local entry
  while IFS= read -r entry; do
    [ -n "$entry" ] || continue
    if [ ! -f "$target/.gitignore" ] || ! grep -qxF "$entry" "$target/.gitignore"; then
      printf '%s\n' "$entry" >> "$target/.gitignore"
    fi
  done <<EOF_GI
$entries
EOF_GI
}
```

呼び出し: `ensure_target_gitignore "$TARGET"`

- [ ] **Step 3: 動作確認（手動 smoke）**

Run: `T=$(mktemp -d) && bash bin/setup.sh --profile=standard --target="$T" >/dev/null && cat "$T/.gitignore" && bash bin/setup.sh --profile=standard --target="$T" >/dev/null && grep -c evidence-log "$T/.gitignore" && rm -rf "$T"`
Expected: 4 エントリが出力され、2回目の実行後も `grep -c evidence-log` が 2 のまま（jsonl と .1 の2行＝冪等）。CLI は等号形式（`--profile=X --target=Y`）— bin/setup.sh:14-28 のパーサは空白区切り形式を受理しない（grill-plan 🟡5）

- [ ] **Step 4: コミット**

```bash
git add .gitignore bin/setup.sh
git commit -m "feat(e1): gitignore evidence-log in framework repo and install targets"
```

---

### Task 11: scaffold smoke 拡張（install 先で observer 実発火）

**Files:**
- Modify: `scripts/eval_scaffold_smoke.py:102-199`（verify_hooks_runnable に追加）

- [ ] **Step 1: smoke に観測検査を追加**

`verify_hooks_runnable` 内（check-control-plane 検査の後）に追加。標準・full では post-bash-observe が配布されるため、実発火→ログ追記まで検証する:

```python
    # E1: the observer must RECORD a Bash execution into the evidence log.
    # F6 lesson: install-path artifacts are verified by FIRING them, not by
    # static listing — a distributed-but-dead observer is the silent
    # fail-open class this feature exists to close.
    if profile in ("standard", "full"):
        r = _fire_hook(target, "hooks/post-bash-observe.sh",
                       _hook_stdin(target, "Bash", {"command": "echo smoke-e1"}))
        if r.returncode != 0:
            return False, f"post-bash-observe.sh rc={r.returncode}"
        if r.stdout.strip() != "{}":
            return False, f"post-bash-observe.sh unexpected output: {r.stdout!r}"
        ev = target / ".claude" / "evidence-log.jsonl"
        if not ev.is_file():
            return False, "post-bash-observe.sh did not create evidence-log"
        if '"cmd":"echo smoke-e1"' not in ev.read_text(encoding="utf-8"):
            return False, "post-bash-observe.sh did not append the execution"
```

注意: `_fire_hook` / `_hook_stdin` の実シグネチャ（scripts/eval_scaffold_smoke.py:59-100）に合わせて呼び出すこと。判定は `_decision` ではなく `r.stdout.strip() != "{}"` を使う — `_decision` は permissionDecision 不在時に `""` を返すため emit_allow の `{}` では常に空になり、smoke が誤 FAIL する（grill-plan 🟡4。check-gate B-1 検査と同形）。

- [ ] **Step 2: smoke を実行して確認**

Run: `python3 scripts/eval_scaffold_smoke.py`
Expected: minimal/standard/full 全プロファイル PASS（rc=0）

- [ ] **Step 3: コミット**

```bash
git add scripts/eval_scaffold_smoke.py
git commit -m "feat(e1): scaffold smoke fires the observer and asserts evidence-log append"
```

---

### Task 12: ドキュメント同期（spec 逸脱・skills 手順・README）

**Files:**
- Modify: `docs/specs/2026-06-10-e1-activity-verification-design.md`（out_sha → payload_sha）
- Modify: `.claude/skills/` 内の test-result.json / record-test-result 言及（`grep -rln "test-result" .claude/skills/` で特定）
- Modify: `README.md`（観測検証の1段落、`grep -n "judge" README.md` で挿入位置を特定）

- [ ] **Step 1: spec の逸脱2件を反映**

(a) design.md のスキーマ行 `"out_sha":"<出力先頭64KBのsha256>"` を `"payload_sha":"<hook 生入力 JSON 先頭64KBのsha256>"` に変更し、インターフェース定義の同項目にも実装注記を1行追加: 「pure-bash 制約により JSON 内出力本文の抽出は行わず、生ペイロード（コマンド＋応答を含む）をハッシュする」。
(b) design.md の fingerprint 記述「merge-base 比の変更コードファイル…の現内容 sha256」を「HEAD（無ければ empty-tree）比の変更コードファイル＋未追跡ファイルの現内容に **HEAD コミット sha を混入**した sha256。トークンは `64-hex | oversize | nogit | error`」に更新する（grill-plan 🔴1 対応の設計確定）。

- [ ] **Step 2: skills / コマンド手順の更新**

Run: `grep -rln "test-result.json\|record-test-result" .claude/`
各ヒットについて: judge card の説明を「テスト判定は evidence-log（hook 観測）由来。Claude Code 外でテストした場合のみ `python3 scripts/record-test-result.py --root . "<test command>"` で手動記録」に書き換える。

- [ ] **Step 3: README に E1 の1段落**

README の judge card / tri-state を説明している節に追加:

```markdown
### Activity verification (v1.5.0)

ゲート承認時のテスト判定は、エージェントの自己申告ではなく hook が観測した
実行記録（`.claude/evidence-log.jsonl`）に基づく。PostToolUse/PostToolUseFailure
(Bash) が全実行のメタ（コマンド・成否・worktree fingerprint）を記録し、judge card
が現在のコードと一致する最新のテスト実行を照合する。記録が無い・コード変更後の
場合は 🟡 unverified（`--ack` で承認可）、観測された red は 🔴 ブロック。
Claude Code 外でテストを実行した場合は `scripts/record-test-result.py` で
手動記録できる（同一スキーマ・src:"manual"）。
```

- [ ] **Step 4: コミット**

```bash
git add docs/specs/2026-06-10-e1-activity-verification-design.md .claude/ README.md
git commit -m "docs(e1): sync spec payload_sha deviation, skills, and README"
```

---

### Task 13: 版数 v1.5.0 ＋ 全量検証

**Files:**
- Modify: `scripts/check_framework_contract.py:17`（FRAMEWORK_VERSION）
- Modify: `docs/STATUS.md`（framework_version — 版数同期チェックに従う）

- [ ] **Step 1: 版数を更新**

`scripts/check_framework_contract.py:17` を `FRAMEWORK_VERSION = "1.5.0"` に変更。
`docs/STATUS.md` frontmatter の `framework_version:` を `"1.5.0"` に変更。
Run: `python3 scripts/check_framework_contract.py`
Expected: PASS（他に版数同期箇所があればエラーメッセージが指すので追従）

- [ ] **Step 2: 全量検証（リリース前と同一セット）**

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3
python3 scripts/check_framework_contract.py
python3 scripts/check_reference_drift.py
python3 scripts/eval_scaffold_smoke.py
```

Expected: tests 全 PASS（既存 389 + 新規 ≈30）、contract / drift / smoke PASS

- [ ] **Step 3: コミット**

```bash
git add scripts/check_framework_contract.py docs/STATUS.md
git commit -m "chore(e1): bump framework version to 1.5.0"
```

---

## 実装後フロー（aegis 定着フロー）

1. grill-code（2段グリル後段）で実装全体をレビュー
2. review → qa → security → deploy ゲートを judge card（本機能でテスト行が観測ベースになった状態）で承認
3. v1.5.0 タグ・origin push はユーザー判断
4. LEARNINGS: E1 で得た所見（観測の死角: subagent 外実行・記録時 fingerprint コスト等）を記録
