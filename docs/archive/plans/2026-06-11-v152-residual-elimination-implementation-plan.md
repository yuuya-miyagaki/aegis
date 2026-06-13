# v1.5.2 残余リスク全消化バッチ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v151-security.md 記録の残余 5 件（クォート内 false-RED／入れ子 `((runner))`／`\/` 非ルーティング／claim-mv クラッシュ窓／待機窓 2s）を全消化し v1.5.2 patch で締める。

**Architecture:** 設計書 `docs/specs/2026-06-11-v152-residual-elimination-design.md`（grill-plan 反映済み）に従う。T1=クォート span の不活性トークン `Q` 置換（削除は green 偽装＝禁止）、T2=アンカー `(\( *)*` 拡張、T3=ルーティングクラス `/` 追加、T4=孤児 claim 復元＋O_EXCL（noclobber）採用、T5=待機 50×0.2s。deny 系（check-destructive / check-control-plane / check-secrets）には一切手を入れない。

**Tech Stack:** bash 3.2（macOS）／BSD sed・find／Python 3 `unittest`・`re`。パターンは BSD/GNU `grep -E` と Python `re` の共通サブセット限定（`[[:space:]]`・`\b` 禁止）。

---

## 前提・規約（全タスク共通）

- **TDD**: 各タスックは「失敗するテストを書く → RED 確認 → 最小実装 → GREEN 確認 → ミラー同期 → コミット」。
- **ミラー同期**: `hooks/`・`scripts/` の変更ファイルは `examples/minimal-project/` 配下へ `cp` で byte 同一コピー。怠ると `tests/test_mirror_identity.py::test_real_repository_mirrors_are_identical` が RED になる。
- テスト実行: `python3 -m unittest tests.<module> -v`（個別）／`python3 -m unittest discover -s tests`（全件、ベースライン 461）。
- **実行時間注記**: T5 で待機窓が 10s になるため、「ロックが取れず失敗する」系テスト（既存 4 件＋本計画の新規 guard 数件）は 1 件あたり約 10 秒かかるようになる（仕様どおり。合計 +60s 前後）。
- ロック系テストの mtime 偽装は **dir へのエントリ追加後に** `touch -t` する（エントリ追加で dir mtime が更新されるため順序厳守）。

### 変更ファイル ⇔ ミラー対応

| 本体 | ミラー |
|------|--------|
| `hooks/lib/patterns.sh` | `examples/minimal-project/hooks/lib/patterns.sh` |
| `hooks/post-bash.sh` | `examples/minimal-project/hooks/post-bash.sh` |
| `scripts/build-judge-card.py` | `examples/minimal-project/scripts/build-judge-card.py` |
| `hooks/lib/extract-input.sh` | `examples/minimal-project/hooks/lib/extract-input.sh` |
| `scripts/update-gate.sh` | `examples/minimal-project/scripts/update-gate.sh` |

---

### Task 1: T1a — クォートマスクパターン（patterns.sh）＋ parity ハーネス拡張

**Files:**
- Modify: `hooks/lib/patterns.sh:49-66`（STRIP 変数追加・コメント書換）
- Modify: `tests/test_patterns_parity.py`（マスク込みパイプライン化＋fixtures 追加）
- Mirror: `examples/minimal-project/hooks/lib/patterns.sh`

- [ ] **Step 1: parity ハーネスをマスク込みパイプラインに書き換え、fixtures を追加する**

`tests/test_patterns_parity.py` の `normalize()` を削除し、以下に差し替える（`bash_patterns()` の直前〜クラス定義を変更）。モジュール docstring 末尾に「照合前パイプライン: 改行→';' ＋ クォート span→Q 置換（DQ→SQ 順、T1 v1.5.2）」の一文を追記する。

```python
def normalize_py(cmd: str, strips: list[re.Pattern]) -> str:
    """消費者（build-judge-card.py）と同一の正規化: 改行→';'、
    クォート span→Q 置換（DQ→SQ の順は fixtures でピン留めする規約）。"""
    s = cmd.replace("\n", ";")
    for p in strips:
        s = p.sub("Q", s)
    return s


def normalize_sed(cmd: str, strips: list[str]) -> str:
    """消費者（post-bash.sh）と同一の tr+sed パイプラインを実走する。"""
    script = ('printf %s "$1" | tr "\\n" ";" '
              '| sed -E "s/$2/Q/g" | sed -E "s/$3/Q/g"')
    r = subprocess.run(["bash", "-c", script, "_", cmd, strips[0], strips[1]],
                       capture_output=True, text=True, timeout=10, check=True)
    return r.stdout


def bash_strip_patterns() -> list[str]:
    out = subprocess.run(
        ["bash", "-c",
         'source "$1"; printf "%s\\n%s\\n" '
         '"$AEGIS_TR_STRIP_DQ" "$AEGIS_TR_STRIP_SQ"',
         "_", str(PATTERNS)],
        capture_output=True, text=True, timeout=10, check=True)
    return [l for l in out.stdout.splitlines() if l.strip()]
```

`FIXTURES` 末尾に追加（コメントごと）:

```python
    # --- T1 v1.5.2: クォートマスク（"…"/'…' → Q 置換）---
    # false-RED 根治（v1.5.1 ではクォート内 |runner / ; runner が一致していた）
    ('grep -E "(unittest|pytest)" missing.txt', False),
    ('grep "foo; pytest" missing.txt', False),
    ('grep "a\\" ; pytest" log.txt', False),   # escaped-quote: \\. が \" を吸収
    # 不変ピン（マスク後も先頭ランナーは残る／クォート起動は従来どおり不一致）
    ('pytest "tests/foo bar"', True),
    ('npx "vitest"', False),
    ('echo ""; pytest', True),
    # 反転 fixture（grill A 🔴-1）: Q「置換」を「削除」に revert すると
    # ' pytest' に縮退して True 化＝green 偽装。この行が RED で封鎖する。
    ('"echo" pytest', False),
    # 受容残余（grill A 🟡-2）: 混在クォート横断は unverified=fail-closed 方向
    ("echo 'a\"b'; pytest \"x\"", False),
```

`TestTestRunnerParity` を次のとおり変更・追加:

```python
    @classmethod
    def setUpClass(cls):
        cls.patterns = bash_patterns()
        cls.strips_raw = bash_strip_patterns()
        cls.strips = [re.compile(p) for p in cls.strips_raw]

    def test_strip_patterns_exist_and_sed_safe(self):
        # DQ→SQ の 2 本。'/' を含まない＝sed s/// デリミタ安全（T1 v1.5.2）。
        self.assertEqual(len(self.strips_raw), 2)
        for p in self.strips_raw:
            self.assertNotIn("/", p)

    def test_fixtures_python(self):
        compiled = [re.compile(p) for p in self.patterns]
        for cmd, expected in FIXTURES:
            s = normalize_py(cmd, self.strips)
            got = any(c.search(s) for c in compiled)
            self.assertEqual(got, expected, f"python re: {cmd!r} -> {s!r}")

    def test_fixtures_grep(self):
        for cmd, expected in FIXTURES:
            s = normalize_sed(cmd, self.strips_raw)
            got = grep_match(s, self.patterns)
            self.assertEqual(got, expected, f"grep -E: {cmd!r} -> {s!r}")

    def test_mask_engines_agree(self):
        # sed -E と python re のマスク結果バイト一致（12+ 形、grill 実測の恒久化）。
        for cmd, _ in FIXTURES:
            self.assertEqual(normalize_py(cmd, self.strips),
                             normalize_sed(cmd, self.strips_raw),
                             f"mask parity: {cmd!r}")
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_patterns_parity -v`
Expected: FAIL — `bash_strip_patterns()` が空（`AEGIS_TR_STRIP_DQ` 未定義）で `setUpClass` がエラー、または `test_strip_patterns_exist_and_sed_safe` が FAIL。

- [ ] **Step 3: patterns.sh に STRIP パターンを追加する**

`hooks/lib/patterns.sh` の `_AEGIS_TR_PRE`（現 66 行目）の**直前**に挿入:

```bash
# Quote-span mask (T1 v1.5.2): consumers replace "…"/'…' spans with the inert
# token Q BEFORE matching, so quoted runner mentions — grep -E "(unittest|pytest)" f,
# grep "foo; pytest" f — never reach the classifier (quote-blind false-RED root
# fix). Substitution, NOT deletion: deletion would promote trailing arguments to
# command position ('"echo" pytest' -> ' pytest' = green forgery, grill A red-1).
# Apply DQ then SQ — the order is a convention pinned by the parity fixtures.
# Both patterns stay in the grep-E/python-re common subset and contain no '/'
# (safe as sed s/// payloads). Masking is CLASSIFICATION-ONLY: deny-side hooks
# (check-destructive / check-control-plane / check-secrets) must never mask —
# there it would be a quote-wrapping bypass (fail-open). The evidence log keeps
# the raw command (fidelity / payload_sha unchanged).
AEGIS_TR_STRIP_DQ='"(\\.|[^"\\])*"'
AEGIS_TR_STRIP_SQ="'[^']*'"
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_patterns_parity -v`
Expected: PASS（全 fixtures が両エンジン一致。この時点で消費者は未配線だが、ハーネスがパイプライン仕様を先にピン留めする）

- [ ] **Step 5: ミラー同期と確認**

```bash
cp hooks/lib/patterns.sh examples/minimal-project/hooks/lib/patterns.sh
python3 -m unittest tests.test_mirror_identity -v
```
Expected: PASS

- [ ] **Step 6: コミット**

```bash
git add hooks/lib/patterns.sh examples/minimal-project/hooks/lib/patterns.sh tests/test_patterns_parity.py
git commit -m "feat: add quote-span mask patterns and mask-aware parity harness (v1.5.2 T1a)"
```

---

### Task 2: T1b — 消費者 2 系統へのマスク配線（post-bash.sh / build-judge-card.py）

**Files:**
- Modify: `hooks/post-bash.sh:30-33`
- Modify: `scripts/build-judge-card.py`（`_tr_strip_patterns` 新設＋`read_test_result` 改修）
- Test: `tests/test_judge_card.py`（`TestReadTestResultFromEvidence` に 2 件追加）
- Test: `tests/test_evidence_hooks.py`（post-bash 分類の実発火 2 件追加）
- Test: `tests/test_patterns_parity.py`（deny 境界 guard 1 件追加）
- Mirror: `examples/minimal-project/hooks/post-bash.sh`, `examples/minimal-project/scripts/build-judge-card.py`

- [ ] **Step 1: judge 側の失敗テストを書く**

`tests/test_judge_card.py` の `TestReadTestResultFromEvidence` 末尾に追加:

```python
    def test_quoted_runner_mention_failure_does_not_red(self):
        """クォート内ランナー言及の失敗（grep -E "(unittest|pytest)" f, rc≠0）は
        分類されず、直前の実 green を覆さない（T1 v1.5.2 false-RED 根治 e2e）。"""
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("vitest run", "ok", fp)
            + _ev_line('grep -E "(unittest|pytest)" missing.txt', "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_missing_strip_patterns_is_unverified(self):
        """patterns.sh に STRIP 変数が無い（破損・旧版）場合、判定は
        fail-closed（unverified）に倒れる。"""
        lib = self.root / "hooks" / "lib" / "patterns.sh"
        text = lib.read_text(encoding="utf-8")
        lib.write_text(text.replace("AEGIS_TR_STRIP_DQ", "X_DQ")
                           .replace("AEGIS_TR_STRIP_SQ", "X_SQ"),
                       encoding="utf-8")
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("pytest", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")
```

- [ ] **Step 2: hook 側の失敗テストを書く**

`tests/test_evidence_hooks.py` の `TestPostBashFailureRecords` の後に追加:

```python
class TestPostBashQuoteMask(unittest.TestCase):
    """post-bash.sh（grep 消費者）のクォートマスク（T1 v1.5.2）:
    クォート内ランナー言及の失敗では ReAct ヒントを出さず（emit_allow {}）、
    実ランナー失敗では従来どおり出す。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_quoted_mention_failure_emits_no_react_hint(self):
        rc, out = fire("post-bash.sh",
                       bash_payload('grep -E "(unittest|pytest)" missing.txt'),
                       self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), {})

    def test_real_runner_failure_still_emits_react_hint(self):
        rc, out = fire("post-bash.sh", bash_payload("pytest tests/"), self.root)
        self.assertEqual(rc, 0)
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ReAct", ctx)
```

`tests/test_patterns_parity.py` 末尾に deny 境界 guard を追加（即 PASS の構造固定であり RED ドライバではない）:

```python
class TestMaskScopeBoundary(unittest.TestCase):
    """マスクは分類専用 — deny 系 hook に波及していないこと（fail-open 防止）。"""

    def test_deny_hooks_do_not_reference_strip_patterns(self):
        for h in ("check-destructive.sh", "check-control-plane.sh",
                  "check-secrets.sh"):
            text = (ROOT / "hooks" / h).read_text(encoding="utf-8")
            self.assertNotIn("AEGIS_TR_STRIP", text, h)
```

- [ ] **Step 3: RED 確認**

Run: `python3 -m unittest tests.test_judge_card tests.test_evidence_hooks -v 2>&1 | tail -20`
Expected: FAIL 3 件 — `test_quoted_runner_mention_failure_does_not_red`（red になる）、`test_missing_strip_patterns_is_unverified`（green になる）、`test_quoted_mention_failure_emits_no_react_hint`（ReAct ヒントが出る）。

- [ ] **Step 4: post-bash.sh にマスク段を実装する**

`hooks/post-bash.sh` の 30-33 行目（正規化コメント＋`CMD_NORM=` 行）を差し替え:

```bash
# Normalize before matching (T1 v1.5.1 + v1.5.2, tests/test_patterns_parity.py):
# newlines -> ';' (grep '^' is per-line, the judge's python re '^' is
# string-start), then quoted spans -> inert token Q so quote-blind false-RED
# forms never reach the classifier. Substitution, NOT deletion — deletion would
# promote trailing arguments to command position ('"echo" pytest' = green
# forgery). DQ then SQ, order pinned by the parity fixtures. The patterns
# contain no '/', so they are safe inside the s/// delimiters.
CMD_NORM=$(printf '%s' "$CMD" | tr '\n' ';' \
  | sed -E "s/${AEGIS_TR_STRIP_DQ}/Q/g" | sed -E "s/${AEGIS_TR_STRIP_SQ}/Q/g")
```

- [ ] **Step 5: build-judge-card.py にマスク段を実装する**

`scripts/build-judge-card.py` の `_test_runner_patterns()`（126 行目）の直後に追加:

```python
def _tr_strip_patterns(root: Path) -> list:
    """Load AEGIS_TR_STRIP_DQ/SQ from patterns.sh (single source; same
    bash-source printf route as _test_runner_patterns). DQ-then-SQ order is
    the convention pinned by tests/test_patterns_parity.py. Anything short of
    exactly two compilable patterns makes the caller degrade to 'unverified'
    (fail-closed)."""
    lib = root / "hooks" / "lib" / "patterns.sh"
    if not lib.is_file():
        return []
    try:
        out = subprocess.run(
            ["bash", "-c",
             'source "$1"; printf "%s\\n%s\\n" '
             '"$AEGIS_TR_STRIP_DQ" "$AEGIS_TR_STRIP_SQ"',
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
```

`read_test_result()` を改修 — `pats` 検査の直後に strips 検査を追加し、ループ内の正規化をマスク込みにする:

```python
    pats = _test_runner_patterns(root)
    if not pats:
        return "unverified"
    strips = _tr_strip_patterns(root)
    if len(strips) != 2:
        return "unverified"
```

ループ内（現 171-173 行目のコメント＋ `cmd = ...` 行）を差し替え:

```python
        # Newlines normalized to ';' and quoted spans masked to the inert token
        # Q before matching — the same pipeline as the grep consumer
        # (T1 v1.5.1 + v1.5.2, tests/test_patterns_parity.py).
        cmd = (d.get("cmd") or "").replace("\n", ";")
        for sp in strips:
            cmd = sp.sub("Q", cmd)
```

- [ ] **Step 6: GREEN 確認**

Run: `python3 -m unittest tests.test_judge_card tests.test_evidence_hooks tests.test_patterns_parity -v 2>&1 | tail -5`
Expected: PASS（全件）

- [ ] **Step 7: ミラー同期と確認**

```bash
cp hooks/post-bash.sh examples/minimal-project/hooks/post-bash.sh
cp scripts/build-judge-card.py examples/minimal-project/scripts/build-judge-card.py
python3 -m unittest tests.test_mirror_identity -v
```
Expected: PASS

- [ ] **Step 8: コミット**

```bash
git add hooks/post-bash.sh scripts/build-judge-card.py tests/test_judge_card.py tests/test_evidence_hooks.py tests/test_patterns_parity.py examples/minimal-project/hooks/post-bash.sh examples/minimal-project/scripts/build-judge-card.py
git commit -m "feat: wire quote-span mask into both classifier consumers (v1.5.2 T1b)"
```

---

### Task 3: T2 — コマンド位置アンカーの入れ子 `(` 拡張

**Files:**
- Modify: `hooks/lib/patterns.sh`（`_AEGIS_TR_PRE` とアンカーコメント）
- Test: `tests/test_patterns_parity.py`（fixtures 3 件追加）
- Mirror: `examples/minimal-project/hooks/lib/patterns.sh`

- [ ] **Step 1: 失敗する fixtures を追加する**

`FIXTURES` 末尾に追加:

```python
    # --- T2 v1.5.2: 入れ子サブシェル（unverified 縮小、green 偽装には使えない）---
    ("((pytest))", True),
    ("( (vitest run))", True),
    # 閉じ忘れクォート＝マスク不能な不正形はアンカーが受け皿（defense-in-depth）
    ('grep "(pytest x', False),
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_patterns_parity -v 2>&1 | tail -5`
Expected: FAIL — `((pytest))` と `( (vitest run))` が両エンジンで False。

- [ ] **Step 3: アンカーを拡張し、陳腐化コメントを書き換える**

`hooks/lib/patterns.sh` のアンカーコメント（v1.5.1 の「Command-position anchor」段落、現 56-65 行目）と `_AEGIS_TR_PRE` を差し替え:

```bash
# Command-position anchor (v1.5.1, nested-subshell extension v1.5.2): a runner
# name matches only at the start of a (sub)command — string start, after ; & |,
# through any run of subshell '(' at that position, across env assignments
# (FOO=bar ), or through known wrappers (npx/bunx, uv/poetry/pipenv run).
# Mentions as arguments (grep vitest package.json) do not match. Quoted spans
# are masked to Q before this anchor applies (T1 above), so quoted regex groups
# (grep -E "(pytest|...)") never reach it; the anchor stays as defense-in-depth
# for unmaskable malformed input (e.g. an unclosed quote). Consumers also
# normalize newlines to ';' BEFORE matching (grep '^' is per-line, python re
# '^' is string-start — normalization keeps the two engines in parity).
_AEGIS_TR_PRE='(^|[;&|]) *(\( *)*([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)*((npx|bunx) +|(uv|poetry|pipenv) +run +)?'
```

（変更点は `\(? *` → `(\( *)*` のみ。コメントから「'(' is NOT a bare class member / Nested '((pytest))' is an accepted miss」の旧根拠を除去）

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_patterns_parity -v 2>&1 | tail -5`
Expected: PASS（既存 fixtures 全件無回帰を含む）

- [ ] **Step 5: ミラー同期・コミット**

```bash
cp hooks/lib/patterns.sh examples/minimal-project/hooks/lib/patterns.sh
python3 -m unittest tests.test_mirror_identity -v
git add hooks/lib/patterns.sh examples/minimal-project/hooks/lib/patterns.sh tests/test_patterns_parity.py
git commit -m "feat: extend command-position anchor to nested subshells (v1.5.2 T2)"
```

---

### Task 4: T3 — `\/` エスケープの python3 fidelity ルーティング

**Files:**
- Modify: `hooks/lib/extract-input.sh:45-49`
- Test: `tests/test_evidence_hooks.py`（実発火 1 件追加）
- Mirror: `examples/minimal-project/hooks/lib/extract-input.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_evidence_hooks.py` に追加（`TestPostBashQuoteMask` の後）:

```python
class TestExtractCommandSlashEscapeFidelity(unittest.TestCase):
    """`\\/` のみを含むペイロードも python3 fidelity 経路に乗り、記録される
    コマンドがリテラル 2 文字 `\\/` ではなく `/` になる（T3 v1.5.2）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        self.log = self.root / LOG_REL

    def tearDown(self):
        self.tmp.cleanup()

    def test_slash_escape_payload_recorded_decoded(self):
        raw = ('{"tool_name":"Bash","tool_input":{"command":"ls tests\\/unit"},'
               '"tool_response":{"exitCode":0}}')
        env = os.environ.copy()
        env["AEGIS_ROOT_OVERRIDE"] = str(self.root)
        proc = subprocess.run(
            ["bash", str(ROOT / "hooks" / "post-bash-observe.sh")],
            input=raw, capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(proc.returncode, 0)
        row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["cmd"], "ls tests/unit")
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_evidence_hooks.TestExtractCommandSlashEscapeFidelity -v`
Expected: FAIL — `row["cmd"]` が `ls tests\/unit`（grep 経路のリテラル 2 文字）。

- [ ] **Step 3: ルーティングクラスに `/` を追加する**

`hooks/lib/extract-input.sh` の `extract_command` 内、ルーティングコメントの末文（現 45-48 行目の `The class covers ...` 文）と grep 行を差し替え:

```bash
  # The class covers \\ via its leading backslash member; \/ is included for
  # completeness (v1.5.2 T3) — standard encoders (json.dumps, JSON.stringify)
  # never emit it, but a hand-built or third-party payload may, and the grep
  # path would record it as a literal two-char sequence. The deny-side hook
  # (check-control-plane) routes python3-first independently of this fast-path.
  if printf '%s' "$input" | grep -q '\\[\\nrtbfu"/]'; then
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_evidence_hooks -v 2>&1 | tail -5`
Expected: PASS（既存の fidelity／fast-path テスト無回帰を含む）

- [ ] **Step 5: ミラー同期・コミット**

```bash
cp hooks/lib/extract-input.sh examples/minimal-project/hooks/lib/extract-input.sh
python3 -m unittest tests.test_mirror_identity -v
git add hooks/lib/extract-input.sh examples/minimal-project/hooks/lib/extract-input.sh tests/test_evidence_hooks.py
git commit -m "fix: route backslash-slash escapes through python3 fidelity extraction (v1.5.2 T3)"
```

---

### Task 5: T4a — 孤児 claim 復元（update-gate.sh）

**Files:**
- Modify: `scripts/update-gate.sh`（待機ループ内、mkdir 失敗後〜既存回収の間）
- Test: `tests/test_update_gate_lock.py`（2 件追加）
- Mirror: `examples/minimal-project/scripts/update-gate.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_update_gate_lock.py` 末尾（既存テストの後、`if __name__` の前）に追加:

```python
    def test_orphan_claim_dead_claimer_restored_and_reclaimed(self):
        """claimer 死亡の孤児 claim は pid に復元され、既存 dead-pid 回収路に
        合流して後続承認が成功する（T4a v1.5.2、claim-mv クラッシュ窓の根治）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            claimer = self._dead_pid()
            holder = self._dead_pid()
            (lock / f"pid.claim.{claimer}").write_text(str(holder),
                                                       encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertEqual(r.returncode, 0,
                             f"orphan claim must be restored+reclaimed: "
                             f"{r.stdout}{r.stderr}")
            self.assertIn("brainstorm: approved",
                          (root / "docs" / "STATUS.md").read_text())
            self.assertFalse(lock.exists(),
                             "restored lock must be released after run")

    def test_orphan_claim_live_claimer_left_alone(self):
        """claimer 生存中の claim は復元しない（fail-closed・guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            claim = lock / f"pid.claim.{os.getpid()}"
            claim.write_text(str(self._dead_pid()), encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "live claimer must not be disturbed")
            self.assertTrue(claim.exists(), "live claim must be left intact")
```

`self._run` の `timeout=30` は待機窓 10s + 実行時間に対して十分（変更不要）。

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_update_gate_lock.TestUpdateGateLock.test_orphan_claim_dead_claimer_restored_and_reclaimed -v`
Expected: FAIL — rc≠0（claim は無視され、pid 不在で回収も採用も起きない）。

- [ ] **Step 3: 復元ロジックを実装する**

`scripts/update-gate.sh` の待機ループ内、`mkdir` 失敗後の既存コメント `# Stale-lock reclaim (T4 v1.5.1): ...`（現 93 行目）の**直前**に挿入:

```bash
  # Orphan-claim restore (T4a v1.5.2): per the claim protocol below, pid and
  # pid.claim.* never coexist (a claim is created only by atomically mv-ing the
  # pid file away). A lingering claim whose claimer is DEAD therefore means the
  # claimer crashed between mv and rm/undo — restore it to pid and let the
  # dead-pid reclaim below decide on the ORIGINAL holder pid it contains.
  # Live claimer or non-numeric suffix: leave alone (fail-closed). mv failure
  # is ignored — a concurrent restorer winning the race is equivalent.
  for _claim in "$LOCK_DIR"/pid.claim.*; do
    [ -e "$_claim" ] || continue
    _claimer="${_claim##*.}"
    case "$_claimer" in
      ''|*[!0-9]*) continue ;;
    esac
    if ! kill -0 "$_claimer" 2>/dev/null && [ ! -e "$LOCK_DIR/pid" ]; then
      mv "$_claim" "$LOCK_DIR/pid" 2>/dev/null || true
    fi
  done
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_update_gate_lock -v`
Expected: PASS（既存 8 件＋新 2 件。live-claimer guard は待機窓ぶん時間がかかる）

- [ ] **Step 5: ミラー同期・コミット**

```bash
cp scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
python3 -m unittest tests.test_mirror_identity -v
git add scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh tests/test_update_gate_lock.py
git commit -m "feat: restore orphaned lock claims from dead claimers (v1.5.2 T4a)"
```

---

### Task 6: T4b — pid なしロックの O_EXCL 採用（update-gate.sh）

**Files:**
- Modify: `scripts/update-gate.sh`（待機ループ内、既存回収 `esac` の後〜`sleep 0.2` の間）
- Test: `tests/test_update_gate_lock.py`（4 件追加）
- Mirror: `examples/minimal-project/scripts/update-gate.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_update_gate_lock.py` に追加:

```python
    def _age(self, p: Path) -> None:
        """採用 age-gate（-mmin +1 ＝実効 2 分超）より古い mtime に偽装する。
        必ず dir へのエントリ追加が終わってから呼ぶこと（追加で mtime が戻る）。"""
        subprocess.run(["touch", "-t", "202601010000", str(p)], check=True)

    def test_pidless_old_lock_is_adopted(self):
        """pid なし・実効 2 分超のロックは O_EXCL 採用で引き取られ、
        承認が成功して通常解放される（T4b v1.5.2）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            self._age(lock)
            r = self._run(root, "brainstorm", "approve")
            self.assertEqual(r.returncode, 0,
                             f"aged pid-less lock must be adopted: "
                             f"{r.stdout}{r.stderr}")
            self.assertIn("brainstorm: approved",
                          (root / "docs" / "STATUS.md").read_text())
            self.assertFalse(lock.exists(),
                             "adopted lock must be released after run")

    def test_pidless_young_lock_is_not_adopted(self):
        """若い pid なし dir（mkdir〜pid 書込の正常な瞬間）は採用しない
        （guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "young pid-less dir must not be adopted")
            self.assertTrue(lock.exists())

    def test_old_lock_with_live_claim_is_not_adopted(self):
        """claim が存在する dir は採用対象外（T4a の管轄、guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            claim = lock / f"pid.claim.{os.getpid()}"
            claim.write_text("1", encoding="utf-8")
            self._age(lock)
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(claim.exists())

    def test_empty_pid_old_lock_stays_fail_closed(self):
        """空 pid ファイルは O_EXCL を構造的に失敗させ、採用されない＝
        従来どおり手動削除案内（fail-closed・guard、約10s 待機）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text("", encoding="utf-8")
            self._age(lock)
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "empty pid must stay manual-removal")
            self.assertTrue(lock.exists())
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_update_gate_lock.TestUpdateGateLock.test_pidless_old_lock_is_adopted -v`
Expected: FAIL — rc≠0（採用機構が無く待機後に失敗）。

- [ ] **Step 3: O_EXCL 採用を実装する**

`scripts/update-gate.sh` の待機ループ内、既存回収ブロックの `esac` の後・`sleep 0.2` の**直前**に挿入:

```bash
  # Pid-less adoption (T4b v1.5.2): a crash between mkdir and the pid write
  # (kill -9, trap not yet installed) leaves a pid-less dir forever. NEVER
  # delete it — an age check followed by rm/rmdir is check-then-act and can
  # destroy a NEW live winner's lock (grill-plan A red-2, reproduced). Instead
  # ADOPT it: atomically create our pid via O_EXCL (noclobber) — the kernel
  # picks at most one winner in a single syscall; losers observe a live pid
  # and wait. Age gate: POSIX -mmin +1 compares floor(age/60) > 1, i.e.
  # effectively >2 min (BSD/GNU common; avoids a stat -f/-c fork). Dir mtime
  # refreshes on any entry add/remove, so a freshly acquired or actively
  # contested lock is always young; find of a vanished dir is silenced. An
  # EXISTING empty/garbage pid structurally defeats O_EXCL and stays
  # manual-removal (fail-closed). SIGSTOP >2 min inside the original holder's
  # mkdir->write window can still cross with an adopter — accepted residual
  # (single-user operation), recorded in v152-security.md.
  if [ ! -e "$LOCK_DIR/pid" ]; then
    _has_claim=false
    for _claim in "$LOCK_DIR"/pid.claim.*; do
      [ -e "$_claim" ] && _has_claim=true && break
    done
    if [ "$_has_claim" = "false" ] \
       && [ -n "$(find "$LOCK_DIR" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then
      if ( set -C; printf '%s' "$$" > "$LOCK_DIR/pid" ) 2>/dev/null; then
        LOCK_OK=true
        trap 'rm -f "$LOCK_DIR/pid" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
        break
      fi
    fi
  fi
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_update_gate_lock -v`
Expected: PASS（既存＋T4a＋本タスク 4 件。guard 3 件は各約 10s）

- [ ] **Step 5: ミラー同期・コミット**

```bash
cp scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
python3 -m unittest tests.test_mirror_identity -v
git add scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh tests/test_update_gate_lock.py
git commit -m "feat: adopt aged pid-less gate locks via O_EXCL noclobber (v1.5.2 T4b)"
```

---

### Task 7: T5 — 待機窓 10s 化＋競合ドリル

**Files:**
- Modify: `scripts/update-gate.sh:85`（ループ回数）
- Test: `tests/test_update_gate_lock.py`（構造 1 件＋ドリル 2 件追加）
- Mirror: `examples/minimal-project/scripts/update-gate.sh`

- [ ] **Step 1: 失敗する構造テストとドリルを書く**

`tests/test_update_gate_lock.py` に追加:

```python
    def _spawn(self, root: Path, gate: str, action: str) -> subprocess.Popen:
        return subprocess.Popen(
            ["bash", str(root / "scripts" / "update-gate.sh"), gate, action],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_wait_window_is_50_iterations(self):
        """構造固定（T5 v1.5.2）: 待機ループは 50 回 × 0.2s = 10s。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertIn("for _ in {1..50}; do", text)

    def test_live_contention_both_succeed(self):
        """高速パス（approve/reset）の実競合 2 contender: 敗者も勝者完了後に
        10s 窓内で自力取得し両方成功する（T5。v1.5.1 では敗者 rc=1 だった
        仕様の意図的変更）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            ops = [("brainstorm", "approve"), ("security", "reset")]
            procs = [self._spawn(root, g, a) for g, a in ops]
            outs = [p.communicate(timeout=30) for p in procs]
            self.assertEqual([p.returncode for p in procs], [0, 0],
                             f"both contenders must succeed: {outs}")
            status = (root / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: approved", status)
            self.assertIn("security: pending", status)
            self.assertFalse(
                (root / ".claude" / ".gate-update.lock.d").exists())

    def test_adoption_race_no_lost_update(self):
        """pid なし旧ロックへ 3 contender 同時（T4b×T5 合成ドリル）:
        O_EXCL の単一勝者はカーネル保証。観測契約は「全員逐次成功・
        lost update ゼロ・ロック残留ゼロ」。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            subprocess.run(["touch", "-t", "202601010000", str(lock)],
                           check=True)
            ops = [("brainstorm", "approve"), ("security", "reset"),
                   ("client_ready_for_dev", "reset")]
            procs = [self._spawn(root, g, a) for g, a in ops]
            outs = [p.communicate(timeout=30) for p in procs]
            self.assertEqual([p.returncode for p in procs], [0, 0, 0],
                             f"all contenders must succeed: {outs}")
            status = (root / "docs" / "STATUS.md").read_text()
            self.assertIn("brainstorm: approved", status)
            self.assertIn("security: pending", status)
            self.assertIn("client_ready_for_dev: pending", status)
            self.assertTrue(status.startswith("---"),
                            "frontmatter must not be torn")
            self.assertFalse(lock.exists())
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_update_gate_lock.TestUpdateGateLock.test_wait_window_is_50_iterations -v`
Expected: FAIL（現行は `for _ in 1 2 3 4 5 6 7 8 9 10`）。
注: 競合ドリル 2 件は現行 2s 窓でもタイミング次第で通り得る（決定論的 RED ドライバは構造テスト）。ドリルは堅牢性のピン留めとして追加する。

- [ ] **Step 3: 待機窓を拡大する**

`scripts/update-gate.sh` の待機ループ行を差し替え:

```bash
for _ in {1..50}; do
```

（`{1..50}` は bash 3.2 互換。ロック取得不能時の rc=1 契約・エラーメッセージは不変。qa/security の pre-approve は B1 ドリル＋audit_deps をロック内実行＝分オーダーのため、重ゲート競合の敗者は引き続き rc=1 → 「Retry shortly」が正しい挙動）

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_update_gate_lock -v`
Expected: PASS（全件。「待機して失敗する」系は各約 10s かかる）

- [ ] **Step 5: ミラー同期・コミット**

```bash
cp scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
python3 -m unittest tests.test_mirror_identity -v
git add scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh tests/test_update_gate_lock.py
git commit -m "feat: widen gate-lock wait window to 10s with contention drills (v1.5.2 T5)"
```

---

### Task 8: 版数同期＋ドキュメント

**Files:**
- Modify: `scripts/check_framework_contract.py:17`
- Modify: `templates/STATUS.template.md:3`
- Modify: `examples/minimal-project/docs/STATUS.md:3`
- Modify: `docs/STATUS.md:3`
- Modify: `README.md`（Migration 節）
- Modify: `docs/architecture-overview.md`（4 行目＋履歴表）
- Mirror: `examples/minimal-project/scripts/check_framework_contract.py`（ミラー対象なら同期）

- [ ] **Step 1: 版数を 4 箇所同期する**

以下の 4 ファイルの版数文字列を `"1.5.1"` → `"1.5.2"` に変更:

- `scripts/check_framework_contract.py:17` — `FRAMEWORK_VERSION = "1.5.2"`
- `templates/STATUS.template.md:3` — `framework_version: "1.5.2"`
- `examples/minimal-project/docs/STATUS.md:3` — `framework_version: "1.5.2"`
- `docs/STATUS.md:3` — `framework_version: "1.5.2"`

- [ ] **Step 2: README Migration 節を追加する**

`README.md` の `### From v1.5.0 to v1.5.1` の**直前**に挿入:

```markdown
### From v1.5.1 to v1.5.2

**Non-breaking — v1.5.1 記録残余の全消化バッチ（誤判定根治・可用性向上）。**

- **テストランナー分類にクォートマスク正規化が入った（T1）。** 照合前に
  `"…"`/`'…'` span を不活性トークン `Q` に置換するため、
  `grep -E "(unittest|pytest)" f` や `grep "foo; pytest" f` のような
  クォート内ランナー言及の失敗が judge の 🔴 を誘発しない（false-RED 根治）。
  逆方向の変化として、`npx "vitest"`・`"pytest" -x` などクォートで包んだ
  ランナー起動は分類されず unverified（🟡 ack 可）に倒れる。マスクは分類専用で、
  deny 系 hook と evidence-log の記録（raw コマンド・payload_sha）には適用されない。
- 入れ子サブシェル `((pytest))` がコマンド位置として分類されるようになった（T2）。
- `\/` エスケープを含むペイロードも python3 fidelity 経路で抽出される（T3）。
- `update-gate.sh` のロックが自己修復するようになった（T4）: クラッシュで残った
  孤児 claim（claimer 死亡）は pid に復元して回収し、pid なしロック（実効 2 分超）
  は O_EXCL（noclobber）で原子的に採用する。空/garbage pid は従来どおり
  手動削除案内（fail-closed）。
- ロック待機窓が 2s → 10s に拡大した（T5）。軽量ゲート（reset・brainstorm approve
  等）の実競合は敗者も勝者完了後に自力取得できる。qa/security の pre-approve
  （B1 ドリル・audit_deps をロック内で実行、分オーダー）の競合は引き続き
  rc=1 → 再実行を案内する。
```

- [ ] **Step 3: architecture-overview を更新する**

`docs/architecture-overview.md` 4 行目を `> バージョン: v1.5.2` に変更し、履歴表の v1.5.1 行の下に追加:

```markdown
| v1.5.2 | v1.5.1 記録残余の全消化バッチ。T1: クォートマスク正規化（`"…"`/`'…'` → `Q` 置換、quote-blind false-RED 根治・削除方式は green 偽装のため不採用）／T2: 入れ子サブシェル `((runner))` のアンカー拡張／T3: `\/` エスケープの python3 fidelity ルーティング／T4: ロック自己修復（孤児 claim 復元＋pid なしロックの O_EXCL 採用）／T5: ロック待機窓 2s→10s |
```

- [ ] **Step 4: 整合確認**

```bash
python3 scripts/check_framework_contract.py
python3 scripts/check_framework_contract.py --profile standard --root examples/minimal-project
python3 scripts/check_reference_drift.py --root .
```
Expected: いずれも PASS（版数 4 箇所の同期は contract が検証する）

- [ ] **Step 5: コミット**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md examples/minimal-project/docs/STATUS.md docs/STATUS.md README.md docs/architecture-overview.md
git commit -m "chore: bump framework version to 1.5.2 with migration notes"
```

---

### Task 9: 全回帰＋レースドリル再走（QA 証跡素材）

**Files:** なし（検証のみ。失敗時は該当タスクに戻る）

- [ ] **Step 1: 全回帰を実行する**

```bash
python3 -m unittest discover -s tests
python3 scripts/check_framework_contract.py
python3 scripts/check_framework_contract.py --profile standard --root examples/minimal-project
python3 scripts/check_reference_drift.py --root .
python3 scripts/eval_scaffold_smoke.py
python3 scripts/check_status.py --root . --strict
```
Expected: 全 PASS。テスト件数 461 → 470 台（増分は本計画の新規テスト。件数を控えて QA 証跡に記載）。

- [ ] **Step 2: dead-pid レースドリル 15 回再走（v1.5.1 QA 証跡の再現＋T5 検証）**

一時ディレクトリに scaffold（`tests/test_update_gate_lock.py` の `_scaffold` 相当を bash で再現）を作り、dead-pid stale lock に対して 2 contender × 15 ラウンドを実走する:

```bash
python3 - <<'EOF'
import subprocess, tempfile, shutil, os
from pathlib import Path
ROOT = Path.cwd()
STATUS = (ROOT / "tests" / "test_update_gate_lock.py").read_text().split('STATUS_CONTENT = """')[1].split('"""')[0]
wins = 0
for i in range(15):
    d = Path(tempfile.mkdtemp())
    (d / "docs").mkdir(); (d / "docs" / "STATUS.md").write_text(STATUS)
    (d / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "update-gate.sh", d / "scripts" / "update-gate.sh")
    (d / "scripts" / "check_status.py").symlink_to(ROOT / "scripts" / "check_status.py")
    (d / "hooks" / "lib").mkdir(parents=True)
    (d / "hooks" / "lib" / "frontmatter.sh").symlink_to(ROOT / "hooks" / "lib" / "frontmatter.sh")
    lock = d / ".claude" / ".gate-update.lock.d"; lock.mkdir(parents=True)
    p = subprocess.Popen(["true"]); p.wait()
    (lock / "pid").write_text(str(p.pid))
    procs = [subprocess.Popen(["bash", str(d / "scripts" / "update-gate.sh"), g, a],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for g, a in (("brainstorm", "approve"), ("security", "reset"))]
    rcs = [pr.wait(timeout=60) for pr in procs]
    s = (d / "docs" / "STATUS.md").read_text()
    ok = rcs == [0, 0] and "brainstorm: approved" in s and "security: pending" in s and not lock.exists()
    print(f"round {i+1}: rcs={rcs} ok={ok}")
    wins += ok
    shutil.rmtree(d)
print(f"{wins}/15 rounds clean")
EOF
```
Expected: `15/15 rounds clean`（T5 により**両 contender とも成功**＝v1.5.1 の「敗者 rc=1」からの意図的仕様変更を実証。torn write ゼロ・ロック残留ゼロ）。結果（件数・15/15）を控えて QA 証跡 `docs/qa-reports/v152-qa.md` の素材にする。

- [ ] **Step 3: 完了確認**

未コミット差分が無いこと（`git status`）を確認。以降は計画外の定着フロー（grill-code 独立 2 本 → テスト記録 → review/qa/security/deploy ゲート --ack 承認・証跡 `docs/qa-reports/v152-*.md` → session_history 追記 → tag v1.5.2）へ。**テスト記録後〜ゲート承認の間はコミット禁止**（fingerprint 不一致で unverified 化するため）。

---

## 自己レビュー記録

- 仕様カバレッジ: 設計書 T1〜T5・テスト戦略表・版数/ドキュメント行まで全項目にタスクあり（T1=Task1-2, T2=Task3, T3=Task4, T4=Task5-6, T5=Task7, 版数/docs=Task8, 回帰/ドリル=Task9）
- 設計書の受容残余 2 件（混在クォート横断・SIGSTOP 病的合成）は fixture／コード内コメントとして固定済み。v152-security.md への記録はゲート時の証跡作成で行う
- プレースホルダなし・全ステップ実コード/実コマンド付き・型/シグネチャはタスク間で一貫（`_tr_strip_patterns` / `strips` / `Q`）
