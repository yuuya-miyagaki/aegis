# grill 🟢残余 小修正バッチ（v1.5.1）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** grill 🟢残余 5 件（T1 false-RED／T2 deploy-gate stderr 混入／T3 update-gate TOCTOU／T4 stale lock 固着／T5 WRITE_INDICATORS 境界＋find 実行系バイパス）を TDD で解消し v1.5.1 patch とする。

**Architecture:** 設計の正典は `docs/specs/2026-06-11-grill-residual-fixes-design.md`（grill-plan 🔴4・🟡4 反映済み）。分類 regex は `hooks/lib/patterns.sh` 単一ソース＋消費者側改行正規化。ロックは「ロック内で読み→検証→書き」＋ pid ファイル・原子 mv claim。制御 plane 防御は左境界化＋ find 実行系フラグ封鎖。変更した hook/script/lib は同一コミットで `examples/minimal-project/` へ byte-identical 同期（`check_reference_drift.py` が監査）。

**Tech Stack:** bash（BSD/GNU 両対応）、Python 3 `unittest`、regex は BSD/GNU `grep -E` ∩ Python `re` の共通サブセット（`\b`・`[[:space:]]` 禁止 — patterns.sh のみ。check-control-plane.sh の grep 専用 regex はこの制約外）。

**前提（実装セッション冒頭で確認）:**

- カレント: `/Users/miyagakiyuuya/Desktop/personal/superpowers-gstack-antigravitykit-urtorapowers/aegis`
- `docs/STATUS.md` が iteration 19・phase implement 以降であること（plan ゲート承認済み）
- ベースライン確認: `python3 -m unittest discover -s tests 2>&1 | tail -3` → `OK`（436 tests）

---

## 変更ファイルマップ

| 種別 | ファイル | タスク |
|---|---|---|
| lib | `hooks/lib/patterns.sh` | 1 |
| hook | `hooks/post-bash.sh` | 2 |
| script | `scripts/build-judge-card.py` | 2 |
| hook | `hooks/check-deploy-gate.sh` | 3 |
| script | `scripts/update-gate.sh` | 4, 5 |
| hook | `hooks/check-control-plane.sh` | 6 |
| test | `tests/test_patterns_parity.py` | 1 |
| test | `tests/test_judge_card.py` | 2 |
| test | `tests/test_hook_output_schema.py` | 2, 3 |
| test | `tests/test_update_gate_lock.py` | 4, 5 |
| test | `tests/test_check_status.py` | 6 |
| 版数 | `scripts/check_framework_contract.py`, `templates/STATUS.template.md`, `docs/STATUS.md`, `README.md` | 7 |
| ミラー | `examples/minimal-project/hooks/lib/patterns.sh`, `examples/minimal-project/hooks/post-bash.sh`, `examples/minimal-project/scripts/build-judge-card.py`, `examples/minimal-project/hooks/check-deploy-gate.sh`, `examples/minimal-project/scripts/update-gate.sh`, `examples/minimal-project/hooks/check-control-plane.sh` | 各タスク |

---

### Task 1: T1 — patterns.sh コマンド位置アンカー（＋parity fixtures）

**Files:**
- Modify: `hooks/lib/patterns.sh:49-63`（`AEGIS_TEST_RUNNER_REGEX` 全置換）
- Modify: `tests/test_patterns_parity.py`（FIXTURES 全置換＋`normalize()` 追加＋fixture テスト2本を正規化対応）
- Mirror: `examples/minimal-project/hooks/lib/patterns.sh`

- [ ] **Step 1: 失敗するテストを書く — FIXTURES と normalize() を更新**

`tests/test_patterns_parity.py` の `FIXTURES`（現行 20-44 行）を以下で**全置換**し、直後に `normalize()` を追加する:

```python
# (command, is_test_runner) — 消費者は照合前に改行を ';' に正規化する
# （post-bash.sh: tr '\n' ';' ／ build-judge-card.py: cmd.replace("\n", ";")）。
# 本テストも同じ正規化を適用してから両エンジンで照合する。
FIXTURES = [
    ("python3 -m unittest discover -s tests", True),
    ("python -m unittest tests.test_x -v", True),
    ("pytest tests/ -v", True),
    ("python3 -m pytest -x", True),
    ("python -m pytest", True),
    ("npx vitest run", True),
    ("bunx vitest run", True),
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
    ("cd app && vitest", True),
    ("CI=1 pytest -x", True),
    ("FOO=bar BAZ=qux jest", True),
    ("uv run pytest", True),
    ("poetry run pytest tests/", True),
    ("echo build done\nvitest run", True),   # 正規化後の ';' 境界で一致
    # v1.5.1 で意図的に反転（コマンド位置アンカー）: 引数・echo 言及は分類しない
    ("echo pytest", False),
    ("grep vitest package.json", False),
    ("cat jest.config.js", False),
    ("echo done\ngrep pytest log.txt", False),
    # 受容済みの取りこぼし（fail-closed 方向）: ラッパー形は分類されない
    ("time pytest", False),
    ('bash -c "pytest"', False),
    ("git status", False),
    ("ls -la", False),
    ("npm run build", False),
    ("go build ./...", False),
    ("python3 scripts/check_status.py", False),
    ("cargo build", False),
    ("attest something", False),
    ("protest --loud", False),
]


def normalize(cmd: str) -> str:
    """消費者と同一の改行→';' 正規化（grep の行単位 ^ と re の文字列先頭 ^ の差を吸収）。"""
    return cmd.replace("\n", ";")
```

さらに `test_fixtures_python` / `test_fixtures_grep` を正規化適用に変更する:

```python
    def test_fixtures_python(self):
        compiled = [re.compile(p) for p in self.patterns]
        for cmd, expected in FIXTURES:
            got = any(c.search(normalize(cmd)) for c in compiled)
            self.assertEqual(got, expected, f"python re: {cmd!r}")

    def test_fixtures_grep(self):
        for cmd, expected in FIXTURES:
            got = grep_match(normalize(cmd), self.patterns)
            self.assertEqual(got, expected, f"grep -E: {cmd!r}")
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_patterns_parity -v`
Expected: FAIL — `("grep vitest package.json", False)`・`("echo pytest", False)`・`("cat jest.config.js", False)` 等が現行パターンで True になり assert 失敗。

- [ ] **Step 3: patterns.sh を実装**

`hooks/lib/patterns.sh` の 49-63 行（`# Test-runner classification patterns` コメントから配列末尾まで）を以下で**全置換**:

```bash
# Test-runner classification patterns (E1 activity verification).
# Consumed by post-bash.sh (grep -E) and build-judge-card.py (python re).
# CONSTRAINT: stay within the regex subset that behaves identically in BSD/GNU
# `grep -E` AND Python `re` — no [[:space:]], no \b. Use ( |^|$) style
# boundaries instead. tests/test_patterns_parity.py enforces parity with
# shared fixtures; add a fixture line whenever you add a pattern.
#
# Command-position anchor (v1.5.1): a runner name matches only at the start of
# a (sub)command — string start, after ; & | (, across env assignments
# (FOO=bar ), or through known wrappers (npx/bunx, uv/poetry/pipenv run).
# Mentions as arguments (grep vitest package.json) do not match. Consumers
# normalize newlines to ';' BEFORE matching (grep '^' is per-line, python re
# '^' is string-start — normalization keeps the two engines in parity).
_AEGIS_TR_PRE='(^|[;&|(] *)([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)*((npx|bunx) +|(uv|poetry|pipenv) +run +)?'
AEGIS_TEST_RUNNER_REGEX=(
  "${_AEGIS_TR_PRE}vitest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}jest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}pytest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}python3? +-m +pytest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}python3? +-m +unittest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}cargo +test($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}go +test($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}(npm|pnpm|bun|yarn) +(run +)?test(:[-a-zA-Z0-9_]+)?($|[^a-zA-Z0-9_])"
)
```

- [ ] **Step 4: GREEN 確認＋全体回帰**

Run: `python3 -m unittest tests.test_patterns_parity -v`
Expected: PASS（5 テスト全部）
Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`（他テストの回帰なし。post-bash／judge は単一ソース参照のため fixture 反転以外の影響なし）

- [ ] **Step 5: ミラー同期**

```bash
cp hooks/lib/patterns.sh examples/minimal-project/hooks/lib/patterns.sh
```

- [ ] **Step 6: コミット**

```bash
git add hooks/lib/patterns.sh examples/minimal-project/hooks/lib/patterns.sh tests/test_patterns_parity.py
git commit -m "fix(T1): anchor test-runner classification at command position"
```

---

### Task 2: T1 — 消費者の改行正規化（post-bash.sh / build-judge-card.py）

**Files:**
- Modify: `hooks/post-bash.sh:30-36`
- Modify: `scripts/build-judge-card.py:171`（`read_test_result` 内の cmd 取得行）
- Test: `tests/test_judge_card.py`（`TestReadTestResultFromEvidence` に 2 本追加）
- Test: `tests/test_hook_output_schema.py`（`TestPostToolUseFailureHook` に 1 本追加）
- Mirror: `examples/minimal-project/hooks/post-bash.sh`, `examples/minimal-project/scripts/build-judge-card.py`

- [ ] **Step 1: 失敗するテストを書く — judge の複数行分類**

`tests/test_judge_card.py` の `TestReadTestResultFromEvidence` クラス末尾（`test_oversize_current_fp_is_unverified` の後）に追加:

```python
    def test_multiline_command_classified(self):
        """改行入りコマンドは ';' 正規化後に分類される（grep/re パリティ、T1 v1.5.1）。"""
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(_ev_line("echo build done\nvitest run", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_mention_in_args_not_classified(self):
        """引数位置のランナー名言及（grep vitest package.json）は分類されず、
        その失敗が直前の実テスト green を覆さない（false-RED 解消の e2e）。"""
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("vitest run", "ok", fp)
            + _ev_line("grep vitest package.json", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_judge_card.TestReadTestResultFromEvidence -v`
Expected: `test_multiline_command_classified` FAIL（python re は `^` が文字列先頭のみ → 正規化前は unverified）。`test_mention_in_args_not_classified` は Task 1 適用済みなら PASS（回帰ガードとして残す）。

- [ ] **Step 3: build-judge-card.py を実装**

`scripts/build-judge-card.py` の `read_test_result` 内（現行 171 行）:

```python
        cmd = d.get("cmd") or ""
```

を以下へ変更（理由コメント付き）:

```python
        # Newlines normalized to ';' before matching — patterns are anchored at
        # command position and the grep consumer does the same (T1 v1.5.1).
        cmd = (d.get("cmd") or "").replace("\n", ";")
```

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_judge_card -v`
Expected: PASS（全件）

- [ ] **Step 5: post-bash.sh の正規化（回帰ガードテスト＋実装）**

`tests/test_hook_output_schema.py` の `TestPostToolUseFailureHook` に追加（既存 `test_test_runner_failure_emits_react_guidance` の後）:

```python
    def test_multiline_test_command_emits_react_guidance(self):
        """改行入りテストコマンドも正規化後に分類される（T1 v1.5.1 回帰ガード。
        grep は行単位 ^ で正規化前も一致するため RED にはならない — judge 側と
        同一の正規化規約を hook にも固定するのが目的）。"""
        tmp = tempfile.mkdtemp(prefix="aegis-postbash-ml-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        payload = {
            "session_id": "t",
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": "echo build done\nvitest run"},
            "tool_response": {"exitCode": 1, "stdout": "", "stderr": "FAIL"},
        }
        rc, out, err = run_hook(
            "post-bash.sh", payload, env={"AEGIS_ROOT_OVERRIDE": tmp})
        self.assertNotEqual(out, {}, "multiline test command must emit ReAct hint")
        self.assert_posttoolfailure_notification(out, hint="post-bash.sh multiline")
```

`hooks/post-bash.sh` の 30-36 行を以下へ変更:

```bash
# Normalize newlines to ';' before matching: grep '^' is per-line while the
# judge's python re '^' is string-start — normalization keeps both consumers
# of patterns.sh in parity (T1 v1.5.1, tests/test_patterns_parity.py).
CMD_NORM=$(printf '%s' "$CMD" | tr '\n' ';')
IS_TEST=false
for _re in "${AEGIS_TEST_RUNNER_REGEX[@]}"; do
  if printf '%s' "$CMD_NORM" | grep -Eq "$_re"; then
    IS_TEST=true
    break
  fi
done
```

- [ ] **Step 6: GREEN 確認＋全体回帰**

Run: `python3 -m unittest tests.test_hook_output_schema.TestPostToolUseFailureHook -v`
Expected: PASS
Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 7: ミラー同期＋コミット**

```bash
cp hooks/post-bash.sh examples/minimal-project/hooks/post-bash.sh
cp scripts/build-judge-card.py examples/minimal-project/scripts/build-judge-card.py
git add hooks/post-bash.sh scripts/build-judge-card.py \
  examples/minimal-project/hooks/post-bash.sh \
  examples/minimal-project/scripts/build-judge-card.py \
  tests/test_judge_card.py tests/test_hook_output_schema.py
git commit -m "fix(T1): normalize newlines to ';' in both classifier consumers"
```

---

### Task 3: T2 — check-deploy-gate の stderr 分離（mktemp fail-open 封鎖込み）

**Files:**
- Modify: `hooks/check-deploy-gate.sh:56-71`
- Test: `tests/test_hook_output_schema.py`（新クラス `TestDeployGateStderrSeparation`）
- Mirror: `examples/minimal-project/hooks/check-deploy-gate.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_hook_output_schema.py` の `TestPostToolUseHook` クラス定義の**前**に新クラスを追加:

```python
class TestDeployGateStderrSeparation(HookSchemaAssertions):
    """T2 (v1.5.1): check-deploy-gate は判定文面を stdout のみから作る。
    stderr は「RC≠0 かつ stdout 空」の deny 時だけ診断として併合する。
    check_status.py をスタブ化した一時 root + AEGIS_ROOT_OVERRIDE で発火する。"""

    STUB_DENY = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('STDERR_NOISE_MARKER\\n')\n"
        "sys.stdout.write('gate pending: deploy\\n')\n"
        "sys.exit(3)\n"
    )
    STUB_ASK = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('STDERR_NOISE_MARKER\\n')\n"
        "sys.stdout.write('ASK: size-skip deploy confirm\\n')\n"
        "sys.exit(2)\n"
    )
    STUB_SILENT_DENY = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('TRACEBACK_MARKER\\n')\n"
        "sys.exit(3)\n"
    )

    def _root_with_stub(self, stub: str) -> str:
        tmp = tempfile.mkdtemp(prefix="aegis-deploygate-t2-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (Path(tmp) / "docs").mkdir()
        (Path(tmp) / "docs" / "STATUS.md").write_text(
            "---\ntask_type: feature\nphase: implement\nmode: Dev\n"
            "gate_approvals:\n  deploy: pending\n---\n", encoding="utf-8")
        (Path(tmp) / "scripts").mkdir()
        (Path(tmp) / "scripts" / "check_status.py").write_text(
            stub, encoding="utf-8")
        return tmp

    def _fire(self, tmp: str, env_extra: dict | None = None):
        payload = make_pretool_payload("Bash", {"command": "vercel deploy --prod"})
        env = {"AEGIS_ROOT_OVERRIDE": tmp}
        if env_extra:
            env.update(env_extra)
        return run_hook("check-deploy-gate.sh", payload, env=env)

    def test_deny_reason_excludes_stderr(self):
        tmp = self._root_with_stub(self.STUB_DENY)
        rc, out, err = self._fire(tmp)
        self.assert_pretool_decision(out, "deny", hint="T2 deny stdout-only")
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("gate pending: deploy", reason)
        self.assertNotIn("STDERR_NOISE_MARKER", reason)

    def test_ask_reason_excludes_stderr(self):
        tmp = self._root_with_stub(self.STUB_ASK)
        rc, out, err = self._fire(tmp)
        self.assert_pretool_decision(out, "ask", hint="T2 ask stdout-only")
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("size-skip deploy confirm", reason)
        self.assertNotIn("STDERR_NOISE_MARKER", reason)

    def test_empty_stdout_deny_merges_stderr_diagnostic(self):
        tmp = self._root_with_stub(self.STUB_SILENT_DENY)
        rc, out, err = self._fire(tmp)
        self.assert_pretool_decision(out, "deny", hint="T2 diagnostic merge")
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("TRACEBACK_MARKER", reason)

    def test_mktemp_failure_does_not_fail_open(self):
        """TMPDIR 不在で mktemp が死んでも判定経路は維持される（🔴-4）。"""
        tmp = self._root_with_stub(self.STUB_DENY)
        rc, out, err = self._fire(tmp, {"TMPDIR": "/nonexistent-aegis-tmp"})
        self.assert_pretool_decision(out, "deny", hint="T2 mktemp fail-closed")
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_hook_output_schema.TestDeployGateStderrSeparation -v`
Expected: `test_deny_reason_excludes_stderr`・`test_ask_reason_excludes_stderr` FAIL（現行 `2>&1` で NOISE 混入）。`test_empty_stdout_deny_merges_stderr_diagnostic`・`test_mktemp_failure_does_not_fail_open` は現行でも PASS（実装後も維持されることを固定する不変条件）。

- [ ] **Step 3: check-deploy-gate.sh を実装**

`hooks/check-deploy-gate.sh` の 56-71 行（`# set +e:` コメントから 2 つ目の `fi` まで）を以下で**全置換**:

```bash
# set +e: python returning non-zero is expected (deny/ask) — must not abort before emitting JSON.
# stdout/stderr are separated (T2 v1.5.1): decision text comes from stdout
# only; stderr is merged into the deny reason ONLY when stdout is empty
# (interpreter-failure diagnostics). mktemp failure must not kill the hook
# under set -e — fall back to /dev/null (diagnostics lost, gate path intact).
ERR_FILE=$(mktemp 2>/dev/null) || ERR_FILE=/dev/null
set +e
RESULT=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-deploy-ready 2>"$ERR_FILE")
RC=$?
set -e
ERR_CONTENT=""
if [ "$ERR_FILE" != "/dev/null" ]; then
  ERR_CONTENT=$(cat "$ERR_FILE" 2>/dev/null || true)
  rm -f "$ERR_FILE" 2>/dev/null || true
fi
if [ $RC -eq 2 ] && printf '%s' "$RESULT" | grep -q '^ASK:'; then
  MSG=$(printf '%s' "$RESULT" | sed 's/^ASK:[[:space:]]*//' | tr '\n' ' ')
  emit_ask "[deploy-gate] $MSG"
  exit 0
fi
if [ $RC -ne 0 ]; then
  if [ -z "$RESULT" ] && [ -n "$ERR_CONTENT" ]; then
    RESULT="$ERR_CONTENT"
  fi
  MSG=$(printf '%s' "$RESULT" | tr '\n' ' ')
  REASON=$(printf '[deploy-gate] %s' "$MSG")
  emit_deny "$REASON"
  exit 0
fi
```

RC 契約（0=allow / 2+`ASK:`=ask / その他=deny）は不変。

- [ ] **Step 4: GREEN 確認＋全体回帰**

Run: `python3 -m unittest tests.test_hook_output_schema -v 2>&1 | tail -5`
Expected: PASS（全件）
Run: `python3 -m unittest tests.test_failure_policy -v 2>&1 | tail -5`
Expected: PASS（failure policy 表の deploy-gate 行と実発火の突合が維持される）

- [ ] **Step 5: ミラー同期＋コミット**

```bash
cp hooks/check-deploy-gate.sh examples/minimal-project/hooks/check-deploy-gate.sh
git add hooks/check-deploy-gate.sh \
  examples/minimal-project/hooks/check-deploy-gate.sh \
  tests/test_hook_output_schema.py
git commit -m "fix(T2): separate stderr from deploy-gate decision text"
```

---

### Task 4: T3 — update-gate のロック前倒し（CURRENT 読込 TOCTOU 解消）

**Files:**
- Modify: `scripts/update-gate.sh`（:186-202 のロックブロックを :76 直後へ移動＋trap 更新）
- Test: `tests/test_update_gate_lock.py`（2 本追加）
- Mirror: `examples/minimal-project/scripts/update-gate.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_update_gate_lock.py` の `TestUpdateGateLock` クラス末尾に追加:

```python
    def test_lock_acquired_before_current_read_structure(self):
        """構造固定（T3 v1.5.1）: ロック取得（mkdir）が CURRENT 読込より前。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertLess(
            text.index('mkdir "$LOCK_DIR"'), text.index("CURRENT=$("),
            "lock must be acquired before reading CURRENT (TOCTOU)")

    def test_lock_held_blocks_noop_approve(self):
        """ロック保持中は already-approved の no-op 承認も読込前に失敗する
        （旧実装は CURRENT を先に読んで exit 0 していた）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            (root / ".claude" / ".gate-update.lock.d").mkdir(parents=True)
            r = self._run(root, "security", "approve")
            self.assertNotEqual(r.returncode, 0,
                                "lock held → must fail before CURRENT read")
            self.assertIn("lock", (r.stdout + r.stderr).lower())
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_update_gate_lock -v`
Expected: 追加 2 本が FAIL（構造: mkdir のインデックスが CURRENT より後 ／ 挙動: already-approved が exit 0）。既存 3 本は PASS のまま。

- [ ] **Step 3: ロックブロックを移動・trap 更新**

`scripts/update-gate.sh` から現行 186-202 行（`# --- Exclusive lock (P3-3): ...` から `fi` まで）を**削除**し、76 行（`exit 1`／`fi` で STATUS_FILE 確認が終わる箇所）の直後・`# --- Read current value ---` の**前**に以下を挿入:

```bash
# --- Exclusive lock (P3-3): mkdir is atomic on POSIX; flock(1) absent on macOS ---
# Acquired BEFORE reading CURRENT (T3 v1.5.1): read→validate→write all happen
# inside the lock, so a concurrent update cannot invalidate the read (TOCTOU).
LOCK_DIR="${SNAPSHOT_DIR}/.gate-update.lock.d"
mkdir -p "$SNAPSHOT_DIR"
LOCK_OK=false
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_OK=true
    # rm pid first: rmdir alone would always fail once T4's pid file exists.
    trap 'rm -f "$LOCK_DIR/pid" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
    break
  fi
  sleep 0.2
done
if [ "$LOCK_OK" != "true" ]; then
  echo "ERROR: another gate update holds the lock (${LOCK_DIR})."
  echo "Retry shortly. If no other session is running, remove the stale directory."
  exit 1
fi
```

（失敗時文言の pid 対応は Task 5 で行う。）

- [ ] **Step 4: GREEN 確認**

Run: `python3 -m unittest tests.test_update_gate_lock -v`
Expected: PASS（5 本全部。`test_lock_released_then_succeeds` が trap 更新後も解放を保証）

- [ ] **Step 5: ミラー同期＋コミット**

```bash
cp scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
git add scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh \
  tests/test_update_gate_lock.py
git commit -m "fix(T3): acquire gate lock before reading CURRENT (TOCTOU)"
```

---

### Task 5: T4 — stale lock の PID ベース自動回収（原子 mv claim）

**Files:**
- Modify: `scripts/update-gate.sh`（Task 4 で移動したロックブロックを置換）
- Test: `tests/test_update_gate_lock.py`（3 本追加＋既存 1 本の文言確認）
- Mirror: `examples/minimal-project/scripts/update-gate.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_update_gate_lock.py` の `TestUpdateGateLock` クラス末尾に追加。
ファイル先頭の import に `import os` と `import subprocess` が無ければ追加（subprocess は既存）:

```python
    def _dead_pid(self) -> int:
        """確実に死んでいる PID を得る（直近終了の子プロセス）。"""
        p = subprocess.Popen(["true"])
        p.wait()
        return p.pid

    def test_stale_lock_with_dead_pid_is_reclaimed(self):
        """死んだ PID の pid ファイルを持つ stale lock は自動回収され、
        後続の承認が成功する（T4 v1.5.1）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text(str(self._dead_pid()), encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertEqual(r.returncode, 0,
                             f"dead-pid stale lock must be reclaimed: {r.stdout}{r.stderr}")
            self.assertIn("brainstorm: approved",
                          (root / "docs" / "STATUS.md").read_text())
            self.assertFalse(lock.exists(), "reclaimed lock must be released after run")

    def test_lock_with_live_pid_is_not_reclaimed(self):
        """生きた PID（テストランナー自身）を持つロックは回収されず、
        文言が pid を含む「並行実行中」系になる（🟡-4）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text(str(os.getpid()), encoding="utf-8")
            before = (root / "docs" / "STATUS.md").read_text()
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0, "live-pid lock must not be reclaimed")
            self.assertIn(str(os.getpid()), r.stdout + r.stderr,
                          "error must mention the live holder pid")
            self.assertTrue(lock.exists(), "live lock must be left intact")
            self.assertEqual(before, (root / "docs" / "STATUS.md").read_text())

    def test_lock_with_garbage_pid_is_not_reclaimed(self):
        """数字以外の pid 内容は判別不能 → 回収しない（fail-closed）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            (lock / "pid").write_text("not-a-pid", encoding="utf-8")
            r = self._run(root, "brainstorm", "approve")
            self.assertNotEqual(r.returncode, 0, "garbage pid must not be reclaimed")
            self.assertTrue(lock.exists())
```

既存 `test_lock_held_fails_explicitly_without_write`（pid なし lock dir）は
「回収しない」分岐の検証としてそのまま残す（変更不要）。

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_update_gate_lock -v`
Expected: 追加 3 本のうち `test_stale_lock_with_dead_pid_is_reclaimed`（現行は回収せず失敗）と `test_lock_with_live_pid_is_not_reclaimed`（pid 文言なし）が FAIL。`test_lock_with_garbage_pid_is_not_reclaimed` は現行でも PASS（不変条件ガード）。

- [ ] **Step 3: ロックブロックを実装**

Task 4 で挿入したロックブロックの `for` ループ〜失敗メッセージを以下で**全置換**
（`LOCK_DIR=`・`mkdir -p "$SNAPSHOT_DIR"` 行は維持）:

```bash
LOCK_OK=false
LOCK_HOLDER_PID=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_OK=true
    # rm pid first: rmdir alone would always fail once the pid file exists.
    trap 'rm -f "$LOCK_DIR/pid" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
    printf '%s' "$$" > "$LOCK_DIR/pid"
    break
  fi
  # Stale-lock reclaim (T4 v1.5.1): atomic-mv claim protocol. Only a purely
  # numeric pid of a DEAD process is reclaimed; missing/empty/garbage pid or a
  # live holder falls through to wait (fail-closed). mv of the pid file is an
  # atomic rename, so at most one contender wins the claim — a slow loser can
  # never delete a lock that a faster winner has already re-acquired.
  pid1=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  case "$pid1" in
    ''|*[!0-9]*) ;;  # no/garbage pid → do not reclaim
    *)
      LOCK_HOLDER_PID="$pid1"
      if ! kill -0 "$pid1" 2>/dev/null; then
        CLAIM="$LOCK_DIR/pid.claim.$$"
        if mv "$LOCK_DIR/pid" "$CLAIM" 2>/dev/null; then
          pid2=$(cat "$CLAIM" 2>/dev/null || true)
          if [ "$pid2" = "$pid1" ]; then
            rm -f "$CLAIM" 2>/dev/null || true
            rmdir "$LOCK_DIR" 2>/dev/null || true
          else
            # A faster reclaimer re-acquired between our read and mv — undo.
            mv "$CLAIM" "$LOCK_DIR/pid" 2>/dev/null || true
          fi
        fi
      fi
      ;;
  esac
  sleep 0.2
done
if [ "$LOCK_OK" != "true" ]; then
  if [ -n "$LOCK_HOLDER_PID" ] && kill -0 "$LOCK_HOLDER_PID" 2>/dev/null; then
    echo "ERROR: another live gate update (pid ${LOCK_HOLDER_PID}) holds the lock (${LOCK_DIR})."
    echo "Retry shortly."
  else
    echo "ERROR: a stale gate-update lock blocks this run (${LOCK_DIR})."
    echo "Retry shortly. If no other session is running, remove the stale directory."
  fi
  exit 1
fi
```

- [ ] **Step 4: GREEN 確認＋全体回帰**

Run: `python3 -m unittest tests.test_update_gate_lock -v`
Expected: PASS（8 本全部）
Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: ミラー同期＋コミット**

```bash
cp scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
git add scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh \
  tests/test_update_gate_lock.py
git commit -m "fix(T4): reclaim stale gate lock via pid file and atomic-mv claim"
```

---

### Task 6: T5 — WRITE_INDICATORS 左境界＋find 実行系フラグ封鎖

**Files:**
- Modify: `hooks/check-control-plane.sh:141-143`
- Test: `tests/test_check_status.py`（新クラス `TestControlPlaneWriteIndicators`）
- Mirror: `examples/minimal-project/hooks/check-control-plane.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_check_status.py` の `TestControlPlaneAllowlistBypass` クラスの**後**に追加
（`_setup_project`／`_run_hook` は同クラスの流儀を踏襲）:

```python
class TestControlPlaneWriteIndicators(TestControlPlaneAllowlistBypass):
    """T5 (v1.5.1): WRITE_INDICATORS の左境界化と find 実行系フラグ封鎖。
    _setup_project/_run_hook は親クラス（allowlist bypass）の fixture を再利用。"""

    # --- (a) 左境界: 正当読取りの誤 deny 解消 ---

    def test_grep_for_confirm_string_allowed(self):
        """`grep "confirm " hooks/x.sh` — confir「m␣」が rm\\s に誤一致していた。"""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, 'grep "confirm " hooks/check-gate.sh')
            self.assertEqual(out, "{}",
                             f"read-only grep must be allowed: {out}")
        finally:
            tmpdir.cleanup()

    def test_cat_pre_exec_log_allowed(self):
        """ファイル名中の -exec（pre-exec.log）は左境界（直前が英数）で不一致。"""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, "cat hooks/pre-exec.log")
            self.assertEqual(out, "{}",
                             f"filename mention must be allowed: {out}")
        finally:
            tmpdir.cleanup()

    def test_grep_truncate_dash_s_allowed(self):
        """truncate は call 形のみ検知（P3-4 維持）— シェル語の検索は allow。"""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, 'grep "truncate -s" hooks/check-gate.sh')
            self.assertEqual(out, "{}",
                             f"string search must be allowed: {out}")
        finally:
            tmpdir.cleanup()

    # --- (b) find 実行系フラグ: 実バイパスの封鎖 ---

    def test_find_exec_dd_denied(self):
        """`find hooks/ -exec dd of={} +` — v150-security 記録の実バイパス。"""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(
                root, 'find hooks/ -name "*.sh" -exec dd of={} +')
            self.assertIn('"permissionDecision":"deny"', out,
                          f"find -exec write bypass must be denied: {out}")
        finally:
            tmpdir.cleanup()

    def test_find_exec_truncate_denied(self):
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(
                root, 'find hooks/ -name "*.sh" -exec truncate -s 0 {} +')
            self.assertIn('"permissionDecision":"deny"', out,
                          f"find -exec truncate must be denied: {out}")
        finally:
            tmpdir.cleanup()

    def test_find_quoted_delete_denied(self):
        """クォートバイパス `find hooks/ "-delete"` — `\"` が左境界になり一致。"""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, 'find hooks/ "-delete"')
            self.assertIn('"permissionDecision":"deny"', out,
                          f"quoted -delete must be denied: {out}")
        finally:
            tmpdir.cleanup()

    def test_find_delete_denied(self):
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, 'find hooks/ -name "*.bak" -delete')
            self.assertIn('"permissionDecision":"deny"', out,
                          f"find -delete must be denied: {out}")
        finally:
            tmpdir.cleanup()

    # --- 不変条件: 既存の検知が残る ---

    def test_chain_tee_still_denied(self):
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, "cat /tmp/evil.sh | tee hooks/x.sh")
            self.assertIn('"permissionDecision":"deny"', out,
                          f"chained tee write must stay denied: {out}")
        finally:
            tmpdir.cleanup()

    def test_readonly_with_bare_tee_still_denied(self):
        """read-only 先頭でも裸の tee␣（左境界=空白）は書込指標のまま。"""
        tmpdir, root = self._setup_project(task_type="feature")
        try:
            rc, out = self._run_hook(root, "find hooks/ -name tee x.txt")
            # `-name tee x.txt` 中の ` tee ` が一致（fail-closed 容認）
            self.assertIn('"permissionDecision":"deny"', out,
                          f"bare tee indicator must stay active: {out}")
        finally:
            tmpdir.cleanup()
```

- [ ] **Step 2: RED 確認**

Run: `python3 -m unittest tests.test_check_status.TestControlPlaneWriteIndicators -v`
Expected: `test_grep_for_confirm_string_allowed`（現行 `rm\s` 誤一致で deny）、`test_find_exec_dd_denied`・`test_find_exec_truncate_denied`・`test_find_quoted_delete_denied`・`test_find_delete_denied`（現行バイパスで allow）が FAIL。`test_cat_pre_exec_log_allowed`・`test_grep_truncate_dash_s_allowed`・不変条件 2 本は現行でも PASS（実装後も維持を固定）。
（親クラス継承によりベース 4 テストも再実行されるが、同一 fixture なので PASS のまま。）

- [ ] **Step 3: WRITE_INDICATORS を実装**

`hooks/check-control-plane.sh` の 141-143 行（`# unlink/remove/...` コメントと `WRITE_INDICATORS=` 行）を以下で**全置換**:

```bash
    # unlink/remove/rename/truncate require a call form `(` — bare substrings
    # false-positived on read-only greps like `grep -r "remove" hooks/` (P3-4).
    # Word-form indicators carry a left boundary (T5a v1.5.1): without it,
    # `grep "confirm " hooks/x.sh` matched rm\s inside "confirm ". find's
    # write-capable action flags are listed with the same boundary (T5b):
    # `find hooks/ -exec dd of={} +` passed READ_ONLY_STARTS and (no `;`)
    # CHAIN_OPS — a real write bypass. The boundary also keeps filename
    # mentions (pre-exec.log) allowed, and concatenating after `|` avoids a
    # leading `-` pattern, which BSD grep would parse as an option (rc=2 →
    # the `!` negation would turn that crash into fail-open).
    WRITE_INDICATORS='(^|[^A-Za-z0-9_])sed\s+-i|>\s*[^&]|>>\s|(^|[^A-Za-z0-9_])(tee|cp|mv|chmod|rm|mkdir|touch|install|ln)\s|write_text|write_bytes|open\(.*[wax]|\.write\(|Path\(.*\.write|(unlink|remove|rename|truncate)[[:space:]]*\(|(^|[^A-Za-z0-9_])-(exec|execdir|ok|okdir|delete|fprint0?|fprintf|fls)($|[^A-Za-z0-9_])'
```

- [ ] **Step 4: GREEN 確認＋全体回帰**

Run: `python3 -m unittest tests.test_check_status.TestControlPlaneWriteIndicators -v`
Expected: PASS（継承分含め全件）
Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`（既存 control-plane テスト群＝allowlist/realistic-input/P1-1 系の回帰なし）

- [ ] **Step 5: ミラー同期＋コミット**

```bash
cp hooks/check-control-plane.sh examples/minimal-project/hooks/check-control-plane.sh
git add hooks/check-control-plane.sh \
  examples/minimal-project/hooks/check-control-plane.sh \
  tests/test_check_status.py
git commit -m "fix(T5): boundary-anchor write indicators and block find action flags"
```

---

### Task 7: 版数 1.5.1・README Migration・最終検証

**Files:**
- Modify: `scripts/check_framework_contract.py:17`（`FRAMEWORK_VERSION = "1.5.1"`）
- Modify: `templates/STATUS.template.md:3`（`framework_version: "1.5.1"`)
- Modify: `examples/minimal-project/docs/STATUS.md:3`（`framework_version: "1.5.1"` — contract:854-877 が FRAMEWORK_VERSION との一致を強制）
- Modify: `docs/STATUS.md`（frontmatter `framework_version: "1.5.1"`）
- Modify: `docs/architecture-overview.md:4`（`> バージョン: v1.5.1`）＋版数履歴表に v1.5.1 行を追加
- Modify: `README.md:171` 以降（Migration 節の先頭に新節を挿入）
- Mirror: hook/script/lib のミラーは各タスクで同期済み（ここでは drift 検証のみ）

- [ ] **Step 1: 版数の一斉更新**

上記 5 ファイルの `1.5.0`／`v1.5.0`（現在版を示す箇所のみ）を `1.5.1`／`v1.5.1` に更新。
`docs/architecture-overview.md` の版数履歴表（572 行付近、v1.5.0 行の上）に追加:

```markdown
| v1.5.1 | grill 🟢残余 5 件の修正バッチ。T1: テストランナー分類のコマンド位置アンカー＋消費者改行正規化（false-RED 解消）／T2: deploy-gate の stdout/stderr 分離（mktemp fail-open 封鎖込み）／T3: update-gate のロック前倒し（TOCTOU 解消）／T4: stale lock の PID ベース自動回収（原子 mv claim）／T5: WRITE_INDICATORS 左境界化＋find 実行系フラグ封鎖（書込バイパス閉鎖） |
```

取り残し確認:

```bash
grep -rn '1\.5\.0' README.md docs/STATUS.md docs/architecture-overview.md \
  templates/ examples/minimal-project/docs/STATUS.md scripts/check_framework_contract.py
```

Expected: ヒットは「歴史記述」（architecture-overview の v1.5.0 履歴行、README の旧 Migration 節）のみ。

- [ ] **Step 2: README Migration 節を追加**

`README.md` の `## Migration` 直後・`### From v1.4.0 to v1.5.0` の**前**に挿入:

```markdown
### From v1.5.0 to v1.5.1

**Non-breaking — grill 残余修正バッチ（防御強化・誤判定緩和）。**

- **テストランナー分類がコマンド位置アンカーになった（T1）。**
  `grep vitest package.json` や `echo pytest` のような「引数・文字列としての
  言及」はテスト実行と分類されなくなり、その失敗が judge の 🔴 を誘発しない。
  分類から外れたコマンドは unverified 方向に倒れる（fail-open しない）。
  `time pytest` 等のラッパー形は分類されないため、ゲート承認前は実テストを
  直接実行（または `scripts/record-test-result.py` で手動記録）すること。
- deploy ゲートの ask/deny 文面に python の警告や traceback が混入しなくなった（T2）。
- `update-gate.sh` の排他ロックが読み取り前に取得され（T3）、kill 等で残った
  stale lock は保持プロセスの死亡を確認して自動回収される（T4）。生きた並行
  実行がある場合は pid 付きのエラーで待機を案内する。
- `check-control-plane.sh` が `find ... -exec/-delete` 系の書込形を deny する
  ようになり、`grep "confirm " hooks/x.sh` 等の正当読取りの誤 deny が解消（T5）。
```

- [ ] **Step 3: 最終検証スイート**

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3
python3 scripts/check_framework_contract.py
python3 scripts/check_framework_contract.py --profile standard --root examples/minimal-project
python3 scripts/check_reference_drift.py --root .
python3 scripts/eval_scaffold_smoke.py
python3 scripts/check_status.py --root . --strict
```

Expected: 全て PASS／rc=0（テスト総数は 436＋本バッチ追加分）。

- [ ] **Step 4: コミット**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md \
  docs/STATUS.md docs/architecture-overview.md README.md
git commit -m "chore: bump version to 1.5.1 and document migration notes"
```

---

## 完了後のフロー（plan 外・aegis 定着フロー）

実装タスク完走後は aegis の通常手順に従う（このセクションは参照のみ）:

1. **grill-code**: 独立サブエージェント 2 本で敵対的コードレビュー → 指摘修正
2. **テスト記録**: 観測ベース（テスト実行が evidence-log に記録される）。
   docs 簿記は fp 除外済みだが、**テスト記録→ゲート承認の間はコミット禁止**
   （リリース締めは docs 先行コミット→記録→承認→最終同期コミット→tag の順）
3. **4 ゲート承認**: `bash scripts/update-gate.sh <review|qa|security|deploy> approve --ack "..."`、証跡は `docs/qa-reports/v151-*.md`
4. **版締め**: STATUS session_history 追記（最大 3 エントリ）→ `git tag v1.5.1`。origin push はユーザー判断
