# M4 — 観測 hook の fingerprint/marker をホットパスから外す（rebuild）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全 Bash コマンドで無条件に払っている fingerprint（git サブプロセス＋全変更ファイル read）と test-marker（python3＋grep）計算を、**テストランナー検出時のみ**に限定し、非テストコマンドは安価記録にする。ゲート時の保証（fail-closed・silent-green 禁止・fingerprint binding）は不変。

**Architecture:** 消費側 `build-judge-card.read_test_result` は evidence ログのうち **`AEGIS_TEST_RUNNER_REGEX` に一致するエントリだけ**を判定対象にし、`fp == 現worktree fp`（64-hex 必須）＋ observed なら `marker_verified is True` を要求して 🟢 を出す。よって非ランナーエントリの fp/marker は誰も読まない。`append_evidence` 内で、消費側と**同一の正規化＋同一パターン**でランナーか判定し、ランナーのみ fp+marker を計算する。検出述語は既に `post-bash.sh` に存在するものを共有関数 `is_test_runner_cmd()`（evidence.sh）に一本化し、recorder・ReAct ヒント・gate reader が**絶対に食い違わない**ようにする。番兵 `fp:"skipped"` は 64-hex でないため構造的に緑にならない＝**誤緑経路はゼロ**、取りこぼしても fail-closed（🟡）。

**Tech Stack:** bash（hooks/lib）、python3（テスト＝unittest）、shasum/sha256sum、git。検証は pytest＋`check_framework_contract.py`＋`run_eval.py`(Tier1)＋`eval_scaffold_smoke.py`＋dangling grep の多層。

---

## 不変条件（実装中ずっと守る）

- **silent-green を増やさない**: 🟢 を出す条件（ランナー一致 ∧ fp==current(64hex) ∧ marker==True ∧ status ok）と、それを計算する `fingerprint_worktree`/`_check_test_marker` のロジックは**一切変えない**。変えるのは「いつ呼ぶか」だけ。
- **検出述語は単一ソース**: `is_test_runner_cmd()` は消費側 `read_test_result` の正規化（改行→`;`、クォート span を `Q` にマスク DQ→SQ）＋ `AEGIS_TEST_RUNNER_REGEX` と同一。`tests/test_patterns_parity.py` のパリティ前提を崩さない。
- **取りこぼしは安全側**: 検出が消費側より狭くても、fp が `skipped`（非 hex）になるだけで reader は 🟡 unverified（fail-closed）。広くても無駄計算のみ。
- **green-between-tasks**: 各タスク末でテスト緑。新挙動テストは RED→GREEN を実証。

## ファイル構成

- Modify `hooks/lib/evidence.sh` — 共有関数 `is_test_runner_cmd()` を追加、`append_evidence` を条件分岐に、ヘッダ schema コメントを更新。
- Modify `hooks/post-bash.sh` — インライン検出ループだけを `is_test_runner_cmd()` 呼び出しに置換（`source patterns.sh` は明示依存として残す）。
- Modify `tests/test_evidence_lib.py` — 非ランナー skip / ランナー fp / 共有関数分類の新規テスト。
- Modify `tests/test_evidence_hooks.py` — 非ランナー観測が緑認証しない不変条件ガード（結合テスト）。

**重要（配布・契約）**: 共有関数は**既存 evidence.sh 内**に置く＝**新規 lib ファイルを足さない**。`bin/setup.sh` の copy_hooks は evidence.sh/post-bash.sh を既に配布済みなので配布経路は無影響。`check_framework_contract.py` の `REQUIRED_HOOK_FILES`（131-177行）は post-bash.sh/evidence.sh の**存在チェックのみ・内容は assert しない**ので、中身の改変で契約は壊れない（版も触らない＝3箇所一致は維持）。

> **コミットの Bash gotcha 回避**: メッセージは `Write` で `/tmp/aegis-m4-msgN.txt` に作り `git commit -F <file>` を使う。パスは常にダブルクォート。

## アーキ選択の記録（盲検2次レビュー向け）

採用＝**A: 検出でゲート**（ランナー検出時のみ fingerprint＋marker を計算）。
代替＝**A': marker でゲート**（marker を毎回計算し true のときだけ fingerprint）。A' は新述語ゼロで silent-green 面が最小だが、python3 marker を毎コマンド払う。A は fingerprint＋marker の両方を非ランナーで省け、検出述語は**既存 `post-bash.sh` のものを再利用**＝新規面は実質ゼロ・`test_patterns_parity.py` でパリティ保証済み。両案とも取りこぼしは fail-closed。盲検2次に A vs A' を独立判断させる。

---

## 実装前（フレームワーク状態の移行・コード計画の外）

grill 反映後・Task 0 着手前に、`docs/STATUS.md` を iteration 33 へ移行する（framework_version は触らない）:
- `iteration: 33`、`phase: plan`、`task_type: framework`、`task_size`（L 見込み・確定時に rationale 記載）。
- `gate_approvals`: `brainstorm: approved`（設計書 #4 が承認済）、`plan: approved`（本 grill-plan 通過後）、`review/qa/security/deploy: pending`、`client_ready_for_dev: n/a`。
- `current_refs`: `plan` ＝本計画、`spec` ＝ `docs/plans/2026-06-20-aegis-simplification-design.md`、`requirements` 据置、他 null。
- `failure_tracking: null`、`blockers`: second-opinion.md は iteration 32 の別件のため整理（M4 とは無関係＝archive 化 or 参照外し）。
- `external_evidence` は最新3件維持（HEALTH 警告どおり）。

---

### Task 0: 着手前ベースライン（緑であることの実証）

**Files:** なし（読取・実行のみ）

- [ ] **Step 1: 多層ベースラインが全緑であることを確認（pytest だけで判定しない）**

Run（全て 0 終了であること）:
```bash
python3 -m pytest -q
python3 scripts/check_framework_contract.py
python3 scripts/run_eval.py --tier 1
python3 scripts/eval_scaffold_smoke.py
```
Expected: 全 PASS（contract は 1.12.0 で緑）。ここで赤があれば**先行する pre-existing 障害**なので、M4 着手前に切り分ける（引き継ぎ教訓①）。

- [ ] **Step 2: contract が hook 内容を assert しないことの再確認**

Run: `grep -n "post-bash\|evidence\|fingerprint" scripts/check_framework_contract.py`
Expected: `REQUIRED_HOOK_FILES` の**存在チェックのみ**（内容 grep なし）＝本改修で contract は壊れない、を確証。

---

### Task 1: 共有テストランナー分類関数 `is_test_runner_cmd()` を evidence.sh に追加

**Files:**
- Modify: `hooks/lib/evidence.sh`（`append_evidence` の直前に関数追加）
- Test: `tests/test_evidence_lib.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_evidence_lib.py` の `import` 群の下（`LOG_REL` 定義の後あたり）にヘルパと、`TestAppendEvidence` の上に新クラスを追加する。

```python
def run_is_test_runner(cmd: str) -> str:
    """evidence.sh の is_test_runner_cmd を直接呼び、stdout("true"/"false")を返す。"""
    script = 'source "%s"; is_test_runner_cmd "$(cat)"' % LIB
    proc = subprocess.run(["bash", "-c", script], input=cmd,
                          capture_output=True, text=True, timeout=60)
    return proc.stdout


class TestIsTestRunnerCmd(unittest.TestCase):
    """is_test_runner_cmd は recorder / post-bash.sh / gate reader が共有する
    単一ソース分類器。消費側 read_test_result と同じ正規化＋パターンで判定する。"""

    def test_runner_commands_true(self):
        for cmd in ("pytest tests/", "python3 -m unittest",
                    "npm run test", "cargo test", "go test ./...",
                    "uv run pytest"):
            self.assertEqual(run_is_test_runner(cmd), "true", f"cmd={cmd!r}")

    def test_non_runner_commands_false(self):
        for cmd in ("ls -la", "git status", "echo pytest",
                    'grep -E "(pytest|jest)" file.txt', "cat pytest.ini"):
            self.assertEqual(run_is_test_runner(cmd), "false", f"cmd={cmd!r}")
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest tests/test_evidence_lib.py::TestIsTestRunnerCmd -v`
Expected: FAIL（`is_test_runner_cmd: command not found` で stdout が空 → `"" != "true"`）

- [ ] **Step 3: 最小実装**

`hooks/lib/evidence.sh` の `# append_evidence <root> ...` コメント行の**直前**に以下を挿入する（patterns.sh は本ファイル冒頭で source 済み＝`AEGIS_TR_STRIP_DQ`/`AEGIS_TR_STRIP_SQ`/`AEGIS_TEST_RUNNER_REGEX` が利用可能）。

```bash
# is_test_runner_cmd <cmd> — print "true" if <cmd> is a test-runner invocation,
# else "false". Single-source classifier shared by the evidence recorder
# (append_evidence), the ReAct hint (post-bash.sh), and — by construction of the
# same normalization + patterns — the gate-time reader (build-judge-card.
# read_test_result). Normalization mirrors the reader: newlines -> ';', quoted
# spans masked to the inert token Q (DQ then SQ, T1 v1.5.2), then
# AEGIS_TEST_RUNNER_REGEX. Any drift can only fail-closed: a missed runner
# records fp="skipped" -> the reader reports 🟡 unverified, never silent-green.
#
# Hot-path cost: ONE sed (two -e scripts, DQ then SQ — identical to two piped
# seds for s///g) + ONE grep (all patterns as -e args = OR, same as the reader's
# any()). The `[@]:-` default and the _ge-count guard keep it safe under
# `set -u` on bash 3.2 (macOS) when the array is somehow empty.
is_test_runner_cmd() {
  local cmd="$1" norm _re
  norm=$(printf '%s' "$cmd" | tr '\n' ';' \
    | sed -E -e "s/${AEGIS_TR_STRIP_DQ}/Q/g" -e "s/${AEGIS_TR_STRIP_SQ}/Q/g")
  local _ge=()
  for _re in "${AEGIS_TEST_RUNNER_REGEX[@]:-}"; do
    [ -n "$_re" ] && _ge+=(-e "$_re")
  done
  if [ "${#_ge[@]}" -gt 0 ] && printf '%s' "$norm" | grep -Eq "${_ge[@]}"; then
    printf 'true'
    return 0
  fi
  printf 'false'
  return 0
}
```

- [ ] **Step 4: GREEN を確認**

Run: `python3 -m pytest tests/test_evidence_lib.py::TestIsTestRunnerCmd -v`
Expected: PASS（2 ケース）

- [ ] **Step 5: コミット**

```bash
git add hooks/lib/evidence.sh tests/test_evidence_lib.py
git commit -F /tmp/aegis-m4-msg1.txt   # "feat(evidence): add shared is_test_runner_cmd classifier (M4 prep)"
```

---

### Task 2: `append_evidence` で fp+marker をランナー検出時のみ計算（コア変更）

**Files:**
- Modify: `hooks/lib/evidence.sh`（`append_evidence` 本体＋ヘッダ schema コメント）
- Test: `tests/test_evidence_lib.py`

- [ ] **Step 1: 失敗するテストを書く**

`TestAppendEvidence` クラス内に追加する。

```python
    def test_non_runner_cmd_skips_fingerprint(self):
        """M4: 非ランナーは fp 番兵 'skipped' + marker_verified false の安価記録。
        cmd/payload_sha は維持（cheap・監査値）。reader は非ランナーを無視し、
        非 hex 番兵は構造的に緑にならない。"""
        run_append(self.root, "ok", payload_for("ls -la"))
        d = self.read_lines()[0]
        self.assertEqual(d["fp"], "skipped")
        self.assertEqual(d["marker_verified"], False)
        self.assertEqual(d["cmd"], "ls -la")
        self.assertRegex(d["payload_sha"], r"^[0-9a-f]{64}$")

    def test_runner_cmd_still_fingerprints(self):
        """M4: ランナーはフル記録（64-hex fp）を維持＝reader の fp-binding が機能。"""
        run_append(self.root, "ok", payload_for("pytest tests/"))
        d = self.read_lines()[0]
        self.assertRegex(d["fp"], r"^[0-9a-f]{64}$")
```

- [ ] **Step 2: RED を確認**

Run: `python3 -m pytest "tests/test_evidence_lib.py::TestAppendEvidence::test_non_runner_cmd_skips_fingerprint" -v`
Expected: FAIL（現状は `ls -la` でも 64-hex fp を計算するため `"…hex…" != "skipped"`）

- [ ] **Step 3: 最小実装**

`hooks/lib/evidence.sh` の `append_evidence` 本体を、`fp=` と `marker_verified=` の無条件計算を**条件分岐**に置き換える。現状（参考）:

```bash
  cmd="$(extract_command "$input" 2>/dev/null)" || cmd=""
  cmd="${cmd:0:500}"
  payload_sha="$(printf '%s' "${input:0:65536}" | _fp_sha256 2>/dev/null)" || payload_sha=""
  fp="$(fingerprint_worktree "$root" 2>/dev/null)" || fp="error"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts=""
  marker_verified="$(_check_test_marker "$input" 2>/dev/null)" || marker_verified="false"
```

を、次に置き換える:

```bash
  cmd="$(extract_command "$input" 2>/dev/null)" || cmd=""
  cmd="${cmd:0:500}"
  payload_sha="$(printf '%s' "${input:0:65536}" | _fp_sha256 2>/dev/null)" || payload_sha=""
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || ts=""
  # M4 hot-path cost control: the fingerprint (git subprocesses + file reads)
  # and the marker check (python3 + greps) are ONLY consumed for test-runner
  # entries — build-judge-card.read_test_result ignores every other entry.
  # Compute them only when the command is a test runner (classified on the
  # truncated, to-be-stored cmd so the decision matches the reader's input
  # exactly); otherwise record a cheap entry with a non-hex fp sentinel that
  # can never certify green. A misclassification only fails closed (sentinel
  # fp != current fp -> 🟡 unverified).
  if [ "$(is_test_runner_cmd "$cmd")" = "true" ]; then
    fp="$(fingerprint_worktree "$root" 2>/dev/null)" || fp="error"
    marker_verified="$(_check_test_marker "$input" 2>/dev/null)" || marker_verified="false"
  else
    fp="skipped"
    marker_verified="false"
  fi
```

続いて、ファイル冒頭の schema コメント（`#   {"v":1,...,"fp":"<fingerprint.sh token>"}` のブロック）に、fp 番兵を 1 行追記する。`#    stdin>","fp":"<fingerprint.sh token>"}` の行の直後に:

```bash
#   For NON-test-runner commands (M4) fp is the literal "skipped" and
#   marker_verified is false — the reader ignores those entries, so the heavy
#   fingerprint/marker computation is skipped on the hot path.
```

- [ ] **Step 4: GREEN を確認（新規＋既存回帰）**

Run: `python3 -m pytest tests/test_evidence_lib.py -v`
Expected: PASS（新規 2 ＋ 既存全件。既存はランナー給餌 or fp 非 assert のため不変）

- [ ] **Step 5: コミット**

```bash
git add hooks/lib/evidence.sh tests/test_evidence_lib.py
git commit -F /tmp/aegis-m4-msg2.txt   # "perf(evidence): gate fingerprint/marker on test-runner detection (M4)"
```

---

### Task 3: `post-bash.sh` の検出を共有関数に統合（DRY・純リファクタ）

**Files:**
- Modify: `hooks/post-bash.sh`
- Test:（新規なし。既存 `tests/test_evidence_hooks.py::TestPostBashQuoteMask` が安全網）

- [ ] **Step 1: リファクタ前に既存テストが緑であることを確認（characterization）**

Run: `python3 -m pytest tests/test_evidence_hooks.py -v`
Expected: PASS（特に `test_quoted_mention_failure_emits_no_react_hint` / `test_real_runner_failure_still_emits_react_hint`）

- [ ] **Step 2: インライン検出ループ「だけ」を共有関数呼び出しに置換**

`hooks/post-bash.sh` の現状ブロック（**`source patterns.sh` 行は残す**＝is_test_runner_cmd が依存する配列の明示依存。置換するのは正規化＋ループ部分のみ）:

```bash
# Only act on test runner commands (single source: patterns.sh).
source "${SCRIPT_DIR}/lib/patterns.sh"
# Normalize before matching (T1 v1.5.1 + v1.5.2, tests/test_patterns_parity.py):
# newlines -> ';' (grep '^' is per-line, the judge's python re '^' is
# string-start), then quoted spans -> inert token Q so quote-blind false-RED
# forms never reach the classifier. Substitution, NOT deletion — deletion would
# promote trailing arguments to command position ('"echo" pytest' = green
# forgery). DQ then SQ, order pinned by the parity fixtures. The patterns
# contain no '/', so they are safe inside the s/// delimiters.
CMD_NORM=$(printf '%s' "$CMD" | tr '\n' ';' \
  | sed -E "s/${AEGIS_TR_STRIP_DQ}/Q/g" | sed -E "s/${AEGIS_TR_STRIP_SQ}/Q/g")
IS_TEST=false
for _re in "${AEGIS_TEST_RUNNER_REGEX[@]}"; do
  if printf '%s' "$CMD_NORM" | grep -Eq "$_re"; then
    IS_TEST=true
    break
  fi
done

if [ "$IS_TEST" = true ]; then
```

を、次に置き換える（先頭の `source "${SCRIPT_DIR}/lib/patterns.sh"` は**温存**。`is_test_runner_cmd` は冒頭で source 済みの evidence.sh から提供される）:

```bash
# Only act on test runner commands. Classify via the shared single-source
# helper (is_test_runner_cmd, from the already-sourced evidence.sh) so the
# ReAct hint, the evidence recorder, and the gate-time reader can never diverge.
# It applies the same normalization (newlines -> ';', quoted spans masked to Q,
# DQ then SQ, T1 v1.5.2) and AEGIS_TEST_RUNNER_REGEX.
source "${SCRIPT_DIR}/lib/patterns.sh"
IS_TEST=$(is_test_runner_cmd "$CMD")

if [ "$IS_TEST" = "true" ]; then
```

- [ ] **Step 3: 既存テストが緑のまま（挙動不変）を確認**

Run: `python3 -m pytest tests/test_evidence_hooks.py tests/test_patterns_parity.py -v`
Expected: PASS（リファクタ前と同一結果）

- [ ] **Step 4: コミット**

```bash
git add hooks/post-bash.sh
git commit -F /tmp/aegis-m4-msg3.txt   # "refactor(hooks): post-bash.sh uses shared is_test_runner_cmd (DRY)"
```

---

### Task 4: 非ランナー観測が緑認証しない不変条件ガード＋多層検証

> 版（framework_version）は**上げない**。他3つの簡素化 WS と同じく 1.12.0 据置（`iteration:33` は STATUS の counter で framework_version と直交）。3箇所一致は触らなければ維持。

**Files:**
- Modify: `tests/test_evidence_hooks.py`（不変条件ガード 1 件）

- [ ] **Step 1: 不変条件ガードを書く（feature の RED は Task 2 が担う・これは回帰固定）**

`tests/test_evidence_hooks.py::TestObserveToJudgeEndToEnd` クラスに追加する。

```python
    def test_non_runner_observation_does_not_certify(self):
        """M4 不変条件: 非ランナーコマンドの観測は read_test_result を緑にしない
        （reader はランナーエントリのみ判定。fp 番兵 'skipped' は非 hex）。
        この性質は M4 前後で不変＝feature テストでなく回帰ガード。"""
        rc, _ = fire("post-bash-observe.sh", bash_payload("ls -la"), self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(judge.read_test_result(self.root), "unverified")
```

- [ ] **Step 2: GREEN を確認**

Run: `python3 -m pytest "tests/test_evidence_hooks.py::TestObserveToJudgeEndToEnd::test_non_runner_observation_does_not_certify" -v`
Expected: PASS（`ls -la` は fp="skipped"・marker false → reader は runner 不一致で unverified）

> 注（正直な位置づけ）: この契約は**旧コードでも成立**する（reader は元から非ランナーを無視）。M4 が壊していないことを固定する不変条件ガードであり、RED→GREEN の feature 実証は Task 2 のユニットテストが担う。「RED を見た」と書かない。

- [ ] **Step 3: 多層検証（全緑）**

Run（順に・全て 0 で終了。pytest だけで判定しない＝引き継ぎ教訓①）:
```bash
python3 -m pytest -q
python3 scripts/check_framework_contract.py
python3 scripts/run_eval.py --tier 1
python3 scripts/eval_scaffold_smoke.py
```
Expected: pytest 全 PASS、contract OK（版 1.12.0 のまま3箇所一致）、Tier1 PASS、scaffold smoke PASS

- [ ] **Step 4: 想定外参照ゼロの確認**

Run: `grep -rn "is_test_runner_cmd" hooks scripts tests | grep -v "evidence.sh\|post-bash.sh\|test_evidence_lib.py"`
Expected: 空（定義と想定呼び出し元以外から参照されない）

- [ ] **Step 5: コミット**

```bash
git add tests/test_evidence_hooks.py
git commit -F /tmp/aegis-m4-msg4.txt   # "test(evidence): pin non-runner observation never certifies green (M4)"
```

---

## 実装後（plan の外・フレームワークフロー）

1. `grill-code` を回し 🔴/🟡 を全て潰す（per-task TDD 完了後・push 前）。特に: 検出述語の取りこぼし方向、番兵が緑を作らないこと、両呼出元（observe=ok / post-bash=fail）のカバレッジ、marker forge 防御の不変性。
2. **REDTEAM PoC**: `bash tests/poc/v162-redteam-rerun.sh`（marker forge 群が引き続き全 fail-closed か）。
3. **盲検2次レビュー**: 1次 verdict を渡さず `reviewer`（または `security`）で独立レビュー1回 → 1次レポートの `claims` に記録（検証境界の感応度）。
4. ゲート: review→qa→security（→deploy は L 規定。solo のため push-readiness として扱う）。`build-judge-card.py` で各ゲートの judge カード生成→承認。
5. `docs/LEARNINGS.md` に教訓を記録（ホットパス・条件記録・単一ソース述語）。
6. 明示承認を得てから push（自動 push しない）。

## Self-Review チェック

- **Spec coverage**: 設計#4「テストランナー検出時／ゲート時の遅延計算へ寄せる・保証は不変」＝Task 1-3 で実装。守る核「M4 の保証は維持・実装だけ作り替え」＝🟢 条件と計算ロジック不変。
- **Placeholder scan**: なし（全 step に実コード／実コマンド）。
- **Type/Name consistency**: 関数名 `is_test_runner_cmd`（Task1 定義 / Task2・Task3 使用）一致。番兵 `"skipped"`（Task2 出力 / Task2・Task4 テスト期待）一致。出力 `"true"/"false"`（Task1 関数 / Task2・Task3 比較 `= "true"`）一致。版バンプなし＝整合対象なし。
