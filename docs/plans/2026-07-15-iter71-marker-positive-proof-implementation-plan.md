# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- この変更で達成すること: SF-014 恒久策 — 反ガミング検証を「悪い入力の列挙（denylist）」から「良い実行の証明（positive proof）」へ置換する。
  1. evidence.sh の 4 段検証コア（NO_RUN 失格 → STRONG marker → WEAK pair → zero-run gate）を `hooks/lib/marker.sh` に**移動のみ・変更なし**で抽出し、3 消費者（evidence.sh=source / record=subprocess / drill=subprocess）が同一実装を使う
  2. `record-test-result.py` は green（exit 0）の記録前に marker verdict を必須化 — 不成立/評価不能は **rc2・ログ非書込・stderr 案内**（`unittest discover -p <nomatch>` exit0 / `npm test`→`"test":"true"` の偽 green を根治）。red は marker 不要で従来通り記録
  3. drill `check_baseline` は exit-green の後に verdict を要求 — 不成立は `DRILL BLOCKED (baseline no-test-proof)`（非ランナー import プローブ＋import-crash mutant の偽 DRILL PASS を根治）

## 入力

- 参照要件: なし（framework 自己改善・動機正本 = docs/security-followups.md SF-014／docs/LEARNINGS.md line148 conf9）
- 参照設計: docs/specs/2026-07-15-iter71-marker-positive-proof-design.md

## 事前実測（計画時に実施済み・設計の裏取り）

1. **`pytest -q` は marker を出さない**（pytest 8.4.2 実測）: `-q` の最終行は `1 passed in 0.00s`（`===` 装飾なし）で STRONG regex `={3,} [0-9]+ (passed|failed)` に**非マッチ**、prologue（platform/rootdir/plugins/collected）も**ゼロ**。→ 本 iter 後、`pytest -q` の green は record で **rc2 拒否**される（brainstorm 決定「marker 不成立 green は rc2」の範囲内・意図した運用変更）。対処は「`-q` を外す」で常に可能。usage 文字列・judge 🟡 案内（build-judge-card.py:523 に `-q` 例あり）・既存テスト・SKILL を非 quiet に更新する（Task 1/4/5）。
2. **`python3 -m unittest discover -p 'nomatch*'`**: exit 0・出力 `Ran 0 tests in 0.000s / OK`（実測）→ WEAK pair はヒットするが zero-run 軸1 `(^|\n)Ran 0 tests` で false → 拒否経路が成立する。
3. **`npm test`＋`"test":"true"`**: exit 0・出力 `> test / > true`（実測・npm 11 系）→ marker 皆無で false。
4. **pytest デフォルト出力**: prologue（platform/rootdir/plugins/collected）＋ STRONG marker とも実在（実測）→ 正規 green の受理経路が成立する。
5. **既存 drill テストのダミー test_command**（`true`／`grep -q …`）は新 baseline 検査で全て no-test-proof になる → 実ランナー（unittest）fixture への移行が必要（Task 1 で both-green 移行）。

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: n/a（ローカル CLI スクリプト・framework 自体。配布経路は `bin/setup.sh` — `hooks/lib/*.sh` glob コピーのため新規 marker.sh は**自動配布**・setup.sh 変更不要〔確認済み: setup.sh:510〕）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: Yes（デプロイ対象なし。L サイズのため deploy phase は実施 — 内容は deploy skill 正本に従い install 経路検証〔setup.sh scaffold smoke で marker.sh が配布先に存在し record/drill が fail-closed でなく動作すること〕を想定）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

Project Overrides 未定義・従来慣行どおり main 直行の per-task commit（framework repo・iter67-70 前例）。

## ファイル構造（変更マップ）

- 新規: `hooks/lib/marker.sh` — `aegis_marker_verdict <exit_code> <command>`（stdin=出力全文 → stdout `true`/`false`・rc3=評価不能）。4 段検証を evidence.sh から**逐語移動**。patterns.sh を自 dir から source
- 変更: `hooks/lib/evidence.sh` — `_check_test_marker` の 4 段部分（現 126-199 行）を削除し marker.sh 委譲に置換（JSON 抽出・head4KiB+tail4KiB 窓は残す＝**挙動不変**）。冒頭に `source marker.sh` 追加
- 変更: `scripts/run-test-strength-drill.py` — `MARKER_LIB` 定数＋`marker_verdict()` ヘルパ（rc3/失敗=DrillError）＋`check_baseline` の green 確定前 verdict（不成立→`"no-test-proof"`）＋`run_drill` の BLOCKED メッセージ分岐
- 変更: `scripts/record-test-result.py` — green 時 verdict 必須（false→rc2/DrillError→rc2・ログ非書込）＋受理 green エントリに `"marker": true`（judge 非消費の additive 監査フィールド）＋usage 文字列の `-q` 除去＋docstring の Residual 節更新
- 変更: `scripts/build-judge-card.py:523` — 🟡 案内の record 例から `-q` を除去（文字列 1 箇所のみ・ロジック不変）
- 新規: `tests/test_marker_lib.py` — marker.sh 単体（bash subprocess 直叩き・11 件）
- 変更: `tests/test_record_test_result.py` — marker 必須化テスト追加＋受理経路ピン更新
- 変更: `tests/test_test_strength_drill.py` — no-test-proof テスト追加＋`check_baseline("true")` 期待更新＋ダミー test_command の実ランナー移行（`_write_probe_test` ヘルパ）
- 変更: `tests/test_judge_card.py` — `_pytest()` ヘルパの `-q` 除去（1 行・both-green）
- 変更: `.claude/skills/qa-verification/SKILL.md` — `.drill` spec の test_command 要件（positive proof・`-q` 不可）＋baseline no-test-proof の説明追記

**不変で pin されるもの**: `hooks/lib/patterns.sh`（regex 単一ソース・無変更）／`tests/test_patterns_parity.py`（無変更）／`tests/test_test_marker_zero_run.py`・`tests/test_evidence_lib.py`・`tests/test_evidence_hooks.py`（無変更 = evidence.sh 挙動不変の回帰網）。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | RED テスト一式（M1-M11 / R1-R7 / D1-D2）＋both-green 移行（drill fixture 実ランナー化・judge `_pytest` -q 除去・D3） | 設計ノートの受入条件 |
| Task 2 | `hooks/lib/marker.sh::aegis_marker_verdict`＋evidence.sh 委譲 | Task 1 の RED（M 系） |
| Task 3 | `drill.marker_verdict()`＋`check_baseline` no-test-proof＋run_drill メッセージ | Task 2 の marker.sh・Task 1 の RED（D 系） |
| Task 4 | record green-gate（rc2 拒否・`marker:true`）＋usage/judge 案内文更新 | Task 3 の `drill.marker_verdict`・Task 1 の RED（R 系） |
| Task 5 | SKILL 追記＋full suite 無退行の実測記録 | Task 2-4 の確定挙動 |

循環依存なし。Task 2→3→4 は依存順で**逐次実行**（Task 4 は record が `drill.marker_verdict` を import 消費）。

## タスク分解

> 各タスクは implementer サブエージェント（dispatch `model: "opus"`・per-task commit）。レビュー系は read-only（routing.md Verification delegation 6拘束）。

### タスク 1: RED — テスト先行作成＋both-green 移行

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** 新規 `tests/test_marker_lib.py` / 変更 `tests/test_record_test_result.py`・`tests/test_test_strength_drill.py`・`tests/test_judge_card.py`
**意図:** 偽 green（record）・偽 DRILL PASS（drill）が**現行コードで成立すること**を失敗テストとして RED 証明し、既存 fixture を新仕様と両立する形（実ランナー）へ both-green 移行する。

**1-A. `tests/test_marker_lib.py`（新規・M1-M11・全て RED〔marker.sh 不在によるエラー RED〕）**

ハーネス（test_test_marker_zero_run.py の bash 直叩き流儀）:

```python
ROOT = Path(__file__).resolve().parents[1]
MARKER_LIB = ROOT / "hooks" / "lib" / "marker.sh"

def _verdict(output: str, cmd: str, exit_code: str = "0", lib=None):
    lib = MARKER_LIB if lib is None else lib
    proc = subprocess.run(
        ["bash", "-c",
         'source "$1" >/dev/null 2>&1 || exit 3; aegis_marker_verdict "$2" "$3"',
         "_", str(lib), exit_code, cmd],
        input=output, capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stdout.strip()

PYTEST_REAL = ("platform darwin -- Python 3.9.6, pytest-8.4.2\n"
               "rootdir: /tmp/x\ncollected 3 items\n\n"
               "=========== 3 passed in 0.42s ===========\n")
```

| # | テスト | 入力 | 期待 |
|---|---|---|---|
| M1 | rc3_when_patterns_missing | marker.sh **だけ**を tmpdir にコピーして source（patterns.sh 不在） | rc==3 |
| M2 | strong_with_prologue_true | PYTEST_REAL / `python3 -m pytest tests/` / "0" | (0, "true") |
| M3 | strong_without_prologue_false | `"=== 3 passed in 0.42s ===\n"` のみ / pytest cmd / "0" | (0, "false")（軸3） |
| M4 | pytest_exit5_false | PYTEST_REAL / pytest cmd / **"5"** | (0, "false")（軸2） |
| M5 | weak_pair_true | `"Ran 3 tests in 0.012s\n\nOK\n"` / `python3 -m unittest t` | (0, "true") |
| M6 | weak_half_false | `"Ran 3 tests in 0.012s\n"`（OK なし） | (0, "false") |
| M7 | zero_run_false | `"Ran 0 tests in 0.000s\n\nOK\n"` | (0, "false")（軸1） |
| M8 | no_run_flag_false | PYTEST_REAL / `pytest --collect-only` | (0, "false")（Stage1） |
| M9 | empty_stdin_false | `""` / 任意 cmd | (0, "false") |
| M10 | go_marker_true | `"ok  \texample.com/pkg\t0.123s\n"` / `go test ./...` | (0, "true")（prologue 要求は pytest 系のみ） |
| M11 | forged_strong_plus_collected0_false | `"===== 3 passed in 0.42s =====\ncollected 0 items\n"` / `pytest -k x` / "0" | (0, "false")（REDTEAM-01 同型） |

**1-B. `tests/test_record_test_result.py` 追記・更新（R1-R7）**

既存 `_RecordFixture`（tmp git repo＋hooks/lib copytree＋t_pass/t_fail）をそのまま継承。新クラス `TestRecordMarkerProof`:

```python
def test_zero_run_green_rejected(self):                      # R1: RED
    rc, err = _run_main(["--root", str(self.root),
                         'python3 -m unittest discover -p "nomatch*"'])
    self.assertEqual(rc, 2, err)
    self.assertFalse(self.log.exists())
    self.assertIn("positive proof", err)

def test_quiet_pytest_green_rejected_with_guidance(self):    # R2: RED
    rc, err = _run_main(["--root", str(self.root),
                         f"python3 -m pytest -q {self.root / 't_pass.py'}"])
    self.assertEqual(rc, 2, err)
    self.assertFalse(self.log.exists())
    self.assertIn("-q", err)   # 「-q を外す」案内が届くこと

@unittest.skipUnless(shutil.which("npm"), "npm not installed")
def test_npm_true_green_rejected(self):                      # R3: RED（npm 有時）
    (self.root / "package.json").write_text(
        '{"scripts": {"test": "true"}}', encoding="utf-8")
    rc, err = _run_main(["--root", str(self.root), "npm test"])
    self.assertEqual(rc, 2, err)
    self.assertFalse(self.log.exists())

def test_red_run_recorded_without_marker(self):              # R5: both-green ピン
    rc, err = _run_main(["--root", str(self.root),
                         f"python3 -m pytest {self.root / 't_fail.py'}"])
    self.assertEqual(rc, 0, err)   # red 記録は正常終了（従来どおり）
    row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[-1])
    self.assertEqual(row["status"], "fail")
    self.assertNotIn("marker", row)

def test_marker_lib_missing_fail_closed(self):               # R6: RED
    (self.root / "hooks" / "lib" / "marker.sh").unlink(missing_ok=True)
    rc, err = _run_main(["--root", str(self.root),
                         f"python3 -m pytest {self.root / 't_pass.py'}"])
    self.assertEqual(rc, 2, err)
    self.assertFalse(self.log.exists())

def test_large_output_tail_marker_green(self):               # R7: RED（64KiB 罠 pin）
    (self.root / "t_big.py").write_text(
        "import unittest\nclass T(unittest.TestCase):\n"
        "    def test_big(self):\n        print('x' * 70000)\n",
        encoding="utf-8")
    rc, err = _run_main(["--root", str(self.root), "python3 -m unittest t_big"])
    self.assertEqual(rc, 0, err)
    row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[-1])
    self.assertEqual(row["status"], "ok")
    self.assertIs(row.get("marker"), True)   # verdict が全文（>64KiB）に走った証明
```

既存 `TestRecordAccept.test_valid_runner_still_records` を **R4 に更新**（RED）: cmd の `-q` を除去し `python3 -m pytest {t_pass.py}` に、末尾へ `self.assertIs(row.get("marker"), True)` を追加。

**1-C. `tests/test_test_strength_drill.py` 追記・更新（D1-D3＋fixture 移行）**

D2（既存 `TestCheckBaseline.test_green` を更新・RED）:

```python
def test_green_without_marker_is_no_test_proof(self):
    # iter71 SF-014: `true` は exit 0 だがテスト実行を証明しない。
    with tempfile.TemporaryDirectory() as d:
        status, _ = drill.check_baseline("true", Path(d), 10)
        self.assertEqual(status, "no-test-proof")
```

D3（新規・both-green ピン）:

```python
def test_real_runner_green(self):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "t_ok.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_ok(self):\n        pass\n", encoding="utf-8")
        status, _ = drill.check_baseline("python3 -m unittest t_ok", root, 30)
        self.assertEqual(status, "green")
```

D1（新規・RED — iter69 の R4 forge を E2E で再現し、新仕様で BLOCKED を要求）:

```python
def test_import_probe_baseline_blocked_no_test_proof(self):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _git_init(root)
        (root / "m.py").write_text("a = 1\n", encoding="utf-8")
        _git(root, "add", "-A"); _git(root, "commit", "-qm", "i")
        (root / "m.py").write_text("a = 1\nb = 2\n", encoding="utf-8")  # 行2=added
        spec = root / "s.drill"
        spec.write_text(json.dumps({
            "test_command": 'python3 -c "import m"',   # 非ランナー import プローブ
            "timeout_seconds": 10,
            "mutants": [{"file": "m.py", "line": 2,
                         "original": "b = 2", "mutated": "b = 1/0"}],  # import-crash
        }), encoding="utf-8")
        report = root / "r.md"
        res = self._run(root, spec, report)
        # 現行: baseline green→mutant caught→PASS rc0（偽 PASS の RED 証明）。
        # 新仕様: baseline no-test-proof で BLOCKED rc1。
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("no-test-proof", res.stdout)
        self.assertIn("baseline: no-test-proof", report.read_text())
```

fixture 移行（both-green・同コミット内）— モジュールヘルパを追加し、ダミー test_command を実ランナー化:

```python
def _write_probe_test(root: Path, needle: str, target: str) -> str:
    """grep -q ダミーの実ランナー置換（iter71: baseline は positive proof 必須）。
    必ず git add/commit の後に呼ぶ（untracked＝coverage floor 非対象を保つ）。"""
    (root / "t_probe.py").write_text(
        "import unittest, pathlib\n"
        "class T(unittest.TestCase):\n"
        "    def test_probe(self):\n"
        f"        self.assertIn({needle!r}, "
        f"pathlib.Path({target!r}).read_text())\n", encoding="utf-8")
    return "python3 -m unittest t_probe"
```

移行手順: `grep -rn "test_command" tests/` で **repo 全域**の出現を列挙し（計画時実測: test_test_strength_drill.py 39/52〔parse_spec のみ・実行なし→**据置**〕、344/365/392/439/566/594/620〔grep -q 系〕、411〔blind `true`〕、455〔not-a-git-repo `true`・baseline 到達前に BLOCK→**据置**＋理由コメント〕、472-542〔NO_RUN 系・baseline 到達前に BLOCK→**据置**〕、**test_check_status.py 2365〔`TestQaDrillGate._project` — `run_check --pre-approve-gate qa`→run_qa_drill 経由で実 drill に到達・移行必須〕**）、**baseline に到達するテストだけ**を `_write_probe_test`（blind は pass のみの `t_blind.py`）へ置換する。`test_no_commit_repo_pass_exit0` は staged 検出のため **`git add -A` の後に** probe を書く順序を厳守（先に書くと empty-tree diff で probe 自体が coverage floor 対象になり BLOCKED）。`tests/test_drill_quotepath.py` は added_lines_by_file 単体のみで baseline 非到達（計画時確認済み・変更不要）。

`test_check_status.py::TestQaDrillGate._project` の移行（grill-plan 致命1）: 通常ケースは assertIn probe（`_write_probe_test` 同型・fixture の commit 後に書く）、**blind ケースは pass のみの unittest モジュール**に置換する — `"true"` のまま残すと Task 3 以降 `test_qa_with_surviving_mutant_blocks` の rc1 期待が「baseline BLOCKED」で**偶然満たされ続け**、「生存 mutant が qa を block する」pin が沈黙で検証対象を失う（fail-silent 回帰・iter70 教訓(2) 同型）。blind を実ランナー化することで baseline は green のまま mutant 生存 → block の経路を保存する。`test_qa_passing_drill_then_judge_yellow_ackable` も同 fixture のため同時に守られる。

**1-D. `tests/test_judge_card.py`**: `_pytest()` ヘルパ（line 670）の `-q` を除去（both-green — 現行でも新仕様でも受理される）。

**1-E. `tests/test_test_runner_realness.py:271`** `test_manual_record_is_trusted_even_without_marker` の docstring に注記を追記（both-green・挙動不変）: 「judge 側の読み契約（src=manual は marker_verified 不問で decidable）は iter71 でも不変。iter71 は **record の write-time** に marker verdict を強制し、green の偽造入口を書込み前に閉じた — 直接ログ改竄は fingerprint/人手プレビュー層の担当（従来どおり）」。名前だけ読むと iter71 と矛盾して見えるため。

**RED 分布の期待**: FAIL/ERROR = **M1-M11（11・marker.sh 不在によるエラー RED）＋R1・R2・R4・R6・R7（5）＋D1・D2（2）= 18 件**（＋npm 有環境では R3 で 19 件）。**both-green（RED にならない）= R5・D3・fixture 移行・1-D** — RED コミットの証明力はこの区分の明示で担保する。実測分布をコミットメッセージに記録し、期待と食い違えば原因を特定してから進む。移行後の既存 drill テストが**現行実装で green のまま**であることも同時に確認する（実ランナー化は現行の exit-code baseline でも green）。
**Deliverable:** [ ] RED コミット（分布記録付き）

### タスク 2: GREEN (1) — marker.sh 抽出＋evidence.sh 委譲（挙動不変）

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 新規 `hooks/lib/marker.sh` / 変更 `hooks/lib/evidence.sh`
**意図:** 4 段検証の単一実装化。evidence.sh は抽出（JSON→cmd/out/exit_code・head4KiB+tail4KiB 窓）だけ残し判定を委譲する。

`hooks/lib/marker.sh`（全文・stage 部は evidence.sh 現 126-199 行の**逐語移動**）:

```bash
#!/usr/bin/env bash
# Marker positive-proof core (SF-014 / iter71). Single implementation of the
# 4-stage "did >=1 test actually execute" verdict, consumed by THREE callers:
#   - hooks/lib/evidence.sh              (source; hook-observed entries)
#   - scripts/record-test-result.py      (subprocess; green-record gate)
#   - scripts/run-test-strength-drill.py (subprocess; baseline proof gate)
# Stage logic MOVED VERBATIM from evidence.sh _check_test_marker (C-2 v1.6.1 /
# K-1 v1.6.2); pattern data stays single-sourced in patterns.sh.
#
# aegis_marker_verdict <exit_code> <command>
#   stdin : test output text (the CALLER decides windowing; record/drill pass
#           the FULL text, evidence.sh passes its head+tail window)
#   stdout: "true" | "false" with rc 0
#   rc 3  : evaluation impossible (patterns.sh not loaded / pattern data
#           missing) — every caller must treat this as NOT verified.
# NOTE: the rc3 guard below requires ALL SIX pattern sources non-empty.
# If a future patterns.sh edit legitimately empties one (e.g. every runner
# gains a STRONG marker and PAIRS goes away), update the guard in the SAME
# change — otherwise every consumer hard-fails with rc3.

_AEGIS_MARKER_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=patterns.sh
source "${_AEGIS_MARKER_LIB_DIR}/patterns.sh" 2>/dev/null || true

aegis_marker_verdict() {
  local exit_code="$1" cmd="$2" out pat split anchor companion
  # rc3 guard: the verdict is meaningless without the full pattern data.
  # ${arr[*]:-} keeps this bash-3.2 / set-u safe when patterns.sh is absent.
  if [ -z "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_PAIRS[*]:-}" ] || \
     [ -z "${AEGIS_TEST_ZERO_RUN_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PROLOGUE_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_IS_PYTEST_REGEX:-}" ]; then
    return 3
  fi
  out="$(cat)"
  if [ -z "$out" ]; then
    printf 'false'
    return 0
  fi
  # ---- 以降、evidence.sh 現 126-199 行を逐語移動（$out/$cmd/$exit_code は
  # ---- 本関数のローカル）。Stage 1 no-run / Stage 2 STRONG / Stage 3 WEAK
  # ---- pair / Stage 4 zero-run gate（軸1 出力・軸2 pytest exit5・軸3
  # ---- prologue）→ printf 'true'
}
```

`hooks/lib/evidence.sh` の変更:

1. `source "${_EV_LIB_DIR}/patterns.sh"` の直後に `source "${_EV_LIB_DIR}/marker.sh"` を追加（patterns.sh は is_test_runner_cmd の AEGIS_TR_STRIP_* 用に残す。marker.sh 内の再 source は変数代入の冪等で無害）。
2. `_check_test_marker` の現 126-199 行（Stage 1〜4＋末尾 `printf 'true'`）を以下に置換:

```bash
  # Stages 1-4 moved to marker.sh (iter71 SF-014 shared positive-proof core).
  # Any non-"true" outcome — including rc3 evaluation-impossible — maps to
  # "false": identical on all normal paths, fail-closed on a gutted install
  # (a HALF-loaded patterns.sh that previously skipped Stage 1 now yields
  # rc3 -> false instead of a possible true).
  local verdict
  verdict="$(printf '%s' "$out" | aegis_marker_verdict "$exit_code" "$cmd" 2>/dev/null)" || verdict="false"
  if [ "$verdict" = "true" ]; then
    printf 'true'
  else
    printf 'false'
  fi
}
```

置換に伴い、wrapper 側 `local` 宣言から不要になった `pat split anchor companion` を除去する（stage 移動後は未使用 — 3年後の読者が「どこで使うのか」を探さないため）。

3. `_check_test_marker` の冒頭コメント（Pipeline 説明）に「stage 本体は marker.sh・単一実装」を追記。
4. ファイルヘッダのスキーマ注記（現 16 行付近 `record-test-result.py appends the same schema with src:"manual"`）に「manual green は optional `"marker": true` を持ち得る（iter71）」を追記。

**挙動不変の境界（明示）**: 全正常経路は同一（regex・順序・入力窓とも不変）。唯一の差は「patterns.sh が**部分読込**された破損 install で旧コードが true を返し得た縮退経路」が rc3→false に厳格化される点 — fail-closed 方向のみで、正規 install では到達不能。
**TDD:** M1-M11 が GREEN・`tests/test_test_marker_zero_run.py`／`test_evidence_lib.py`／`test_evidence_hooks.py`／`test_patterns_parity.py` 無退行 → コミット
**受入条件:** marker.sh 単体で bash 3.2 構文互換（`bash -n` 通過・連想配列/mapfile 不使用）・evidence.sh 経由の全既存ピン green
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 3: GREEN (2) — drill: marker_verdict ヘルパ＋baseline no-test-proof

**blockedBy:** Task 2 | **モデル:** `opus`
**ファイル:** `scripts/run-test-strength-drill.py`
**意図:** 偽 DRILL PASS の根治。評価不能は DrillError（fail-closed）、不成立は専用 status で報告する。

`PATTERNS_LIB` の直後に追加（patterns.sh と同じ理由で **framework 位置相対**・--root は scratch clone を指しうる）:

```python
MARKER_LIB = FRAMEWORK_ROOT / "hooks" / "lib" / "marker.sh"


def marker_verdict(output: str, command: str, exit_code: int = 0,
                   marker_lib: Path | None = None) -> bool:
    """Positive proof (SF-014 iter71): run the shared 4-stage verdict
    (hooks/lib/marker.sh aegis_marker_verdict) over the FULL output.
    True/False verdict; any condition that prevents evaluation — missing
    lib, rc3, subprocess failure, unexpected stdout — raises DrillError
    (fail-closed). marker.sh sources patterns.sh from its own directory,
    so the pattern data always matches the lib actually consulted."""
    lib = Path(marker_lib) if marker_lib is not None else MARKER_LIB
    if not lib.is_file():
        raise DrillError(
            f"marker.sh not found: {lib} — positive proof 検査を実行できない"
            f"ため fail-closed（framework install が壊れています）")
    script = ('source "$1" >/dev/null 2>&1 || exit 3; '
              'aegis_marker_verdict "$2" "$3"')
    try:
        proc = subprocess.run(
            ["bash", "-c", script, "_", str(lib), str(exit_code), command],
            input=(output or "").encode("utf-8", errors="replace"),
            capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DrillError(f"marker 検査の実行に失敗（fail-closed）: {exc}")
    if proc.returncode == 3:
        raise DrillError(
            "marker regex を patterns.sh から読み込めません（rc=3）— fail-closed")
    verdict = proc.stdout.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0 or verdict not in ("true", "false"):
        raise DrillError(
            f"marker 検査が不正終了（rc={proc.returncode}, out={verdict!r}）"
            f"— fail-closed")
    return verdict == "true"
```

`check_baseline` の green 確定部を置換:

```python
    if first == "passed" and second == "passed":
        # SF-014 (iter71): exit 0 alone does not prove any test ran — require
        # the shared positive-proof verdict on BOTH green outputs.
        for out in (out1, out2):
            if not marker_verdict(out, command):
                return "no-test-proof", out
        return "green", ""
```

（red/flaky/inconclusive 経路は不変 — marker 検査は green-green 確定時のみ。DrillError は伝播し run_drill の既存 `except DrillError` で BLOCKED fail-closed＋report baseline=inconclusive になる。`check_baseline` docstring の戻り値列挙に `'no-test-proof'（both-passed だが positive proof 不成立）` を追記する。report の `baseline:` 行を値で分岐する消費者は不在（計画時 grep 確認済み — run_qa_drill は drill の exit code のみ消費）のため新値は additive。）

`run_drill` の baseline 分岐にメッセージ分岐を挿入（tail 出力・write_report は既存共通のまま）:

```python
        if base != "green":
            if base == "no-test-proof":
                print("DRILL BLOCKED (baseline no-test-proof): baseline は "
                      "exit 0 ですが、テスト実行の positive proof（ランナーの"
                      "サマリ marker）が出力にありません。test_command は実"
                      "ランナーで書いてください（pytest はデフォルト出力＝"
                      "-q 不可 / unittest / jest / vitest / go / cargo）。")
            else:
                print(f"DRILL BLOCKED (baseline {base}): tests must be green "
                      f"and stable before drilling.")
```

**不変**: sanctioned skip 経路・mutant 実行側（apply_mutant_and_test）・check_no_run_command・write_report スキーマ（baseline 値に `no-test-proof` が増えるのは additive）。
**TDD:** D1-D3 が GREEN・移行済み drill 全テスト＋`test_drill_quotepath.py` 無退行 → コミット
**受入条件:** D1 の report に `baseline: no-test-proof`・stdout に案内文・rc1
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 4: GREEN (3) — record: green の positive proof 必須化

**blockedBy:** Task 3 | **モデル:** `opus`
**ファイル:** `scripts/record-test-result.py` / `scripts/build-judge-card.py`（案内文字列 1 箇所）
**意図:** 罠 SF-014 の record 層根治。judge が読める green は「N≧1 件のテストが実際に走った」証明付きのみ。

`main()` の `_execute` 以降を置換:

```python
    status_code, output = drill._execute(args.command, root, 600)
    status = "ok" if status_code == "passed" else "fail"
    # 4) positive proof (SF-014 iter71): a GREEN record additionally requires
    # the shared 4-stage marker verdict (hooks/lib/marker.sh — the same
    # implementation the hook observer consumes) over the FULL output.
    # payload_sha keeps its 64 KiB cap below, but runners print their summary
    # at the TAIL — never pass the capped prefix to the verdict.
    # red (exit != 0) is recorded as-is: failure is fail-visible, not a
    # gaming vector.
    marker_proven = False
    if status == "ok":
        try:
            marker_proven = drill.marker_verdict(
                output or "", args.command[:500],
                marker_lib=root / "hooks" / "lib" / "marker.sh")
        except drill.DrillError as exc:
            return _reject(f"marker 検査を実行できません — fail-closed: {exc}")
        if not marker_proven:
            return _reject(
                "exit 0 ですが、テスト実行の positive proof（ランナーのサマリ "
                "marker）が出力にありません — 0 件実行の green（例: unittest "
                "discover のパターン不一致 / `npm test` が `true` に束縛）は"
                "記録しません。pytest は `-q` を外して実行してください（marker "
                "はデフォルト出力の `===== N passed =====` 行）。対応ランナー: "
                "pytest（デフォルト出力）/ jest / vitest / go test / cargo test "
                "/ unittest。未収載ランナーは hooks/lib/patterns.sh の marker "
                "追加を検討してください")
    out_bytes = (output or "")[:65536].encode("utf-8", errors="replace")
    entry = {
        # …既存フィールドは不変…
    }
    if marker_proven:
        entry["marker"] = True   # additive 監査フィールド（judge 非消費）
```

付随更新（同コミット）:
- record は **対象 root** の marker.sh（＝judge が読む patterns.sh と同居する install）を使う — `drill.check_no_run_command(..., patterns_lib=root/…)` と同じ根拠。marker.sh は自 dir の patterns.sh を source するため patterns/marker の取り違えは構造上起きない。
- usage 文字列: `正しい例: python3 scripts/record-test-result.py "python3 -m pytest"`（`-q` 除去 — 実測で `-q` は marker/prologue とも出さない）。
- docstring: 「Residual (SF-014 class, NOT closed here)」節を次の内容へ書き換え（grill-plan 致命2: 「CLOSED」単独は過大主張）: 「**0件実行フォージ**（runner 該当・exit 0・0 テスト実行の green）は iter71 の positive proof（marker verdict 必須・rc2 拒否）で CLOSED。**残余**: 出力を任意 script が完全支配するランナー — `npm test` の script に marker 風文字列を echo させる等 — は marker（出力ベースの証明）では原理的に区別できない。列挙で塞ぎに行かない（denylist 回帰）。fingerprint/judge/人手プレビュー/drill の多層で contained・SF-014 の docs 更新（iter71 docs phase）と audit_deps トラック（iter72）に引き継ぐ」。`marker` フィールドの意味（judge 非消費・監査透明性）も追記。
- `scripts/build-judge-card.py:523` の 🟡 案内文字列 `"python3 -m pytest -q"` → `"python3 -m pytest"`（record が拒否する例を judge が案内し続ける矛盾の解消・ロジック不変）。

**判断根拠（pin）**: verdict へ渡す exit_code は green 経路で定義上 0（`_execute` が returncode==0 のときのみ "passed"）→ 定数 0 で正しい。pytest の exit 5（zero collected）は red 経路に落ち従来通り red 記録（gaming 経路でない）。
**TDD:** R1-R7 が GREEN・`tests/test_judge_card.py`（TestRecordTestResultManual 3 件が marker 付きエントリを judge に読ませる非退行網）green → コミット
**受入条件:** 拒否は rc2・ログ非書込・非実行副作用なし（marker 検査は実行後のため「非実行」は従来検証 1-3 の契約のまま）・受理 green エントリに `"marker": true`
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 5: SKILL/文書同期＋full suite 実測

**blockedBy:** Task 2-4 | **モデル:** `opus`
**ファイル:** `.claude/skills/qa-verification/SKILL.md`
**意図:** 運用契約の変更（`-q` 不可・no-test-proof BLOCKED・record rc2 の新事由）を運用者向け正本に同期する。

- `.drill` spec の `test_command` 説明（SKILL 94 行付近）に追記: 「実ランナー必須（positive proof）— baseline 出力にランナーのサマリ marker が必要。pytest は `-q` 不可（marker が出ない）。`grep`/`true` 等の非ランナーは `DRILL BLOCKED (baseline no-test-proof)`」。
- record の言及箇所（なければ evidence 節）に「green は marker verdict 必須・不成立は rc2・red は従来通り」を 2-3 行で追記。
- 変更は追記のみ（既存手順の削除なし）。context budget: `python3 scripts/context_budget.py` を実行し予算内を確認。

**TDD:** 文書タスクのためテストなし（スキップ理由: 挙動を持たない・budget チェックで代替）→ full suite `python3 -m pytest tests/` を実走し、**passed 数と所要時間を実測してコミットメッセージへ記録**（fixture 実ランナー化による増分を可視化）→ コミット
**受入条件:** 全テスト green・budget PASS・SKILL 記述が実装挙動（rc2 文言・BLOCKED 文言）と一致
**Deliverable:** [ ] 文書同期 [ ] full suite 実測記録

## External Integrations

該当なし（外部サービス連携なし・bash/grep は framework 既存前提）。

## 事前準備

- [x] pytest 8.4.2／npm 実在（計画時実測）— R3 は `skipUnless(which("npm"))` で環境非依存化
- [ ] ベースブランチ main が最新・tree クリーン（rollover コミット 8b64326 起点）
- [ ] 依存パッケージ追加なし（bash＋grep＋python3 標準のみ）

## トレーサビリティ（要件 → AC → Task → Test）

| 要件（設計ノート） | AC | Task | テスト |
|------|----|------|--------------|
| 4 段検証コアの共有 lib 化（挙動不変） | marker.sh 単体 11 挙動＋evidence.sh 既存ピン無退行 | Task 2 | tests/test_marker_lib.py M1-M11＋test_test_marker_zero_run.py（無変更） |
| record: green は marker 必須・不成立 rc2・ログ非書込 | R1/R2/R3/R6 拒否・R4/R7 受理 | Task 4 | tests/test_record_test_result.py |
| record: red は marker 不要で従来記録 | R5 | Task 4 | 同上 |
| 64KiB 先頭 cap×末尾 marker 罠（verdict は全文） | R7 | Task 4 | 同上 |
| drill: baseline no-test-proof BLOCKED | D1/D2 | Task 3 | tests/test_test_strength_drill.py |
| drill: 正規 baseline 非退行 | D3＋移行済み E2E 群 | Task 1/3 | 同上 |
| 評価不能=拒否（rc3 fail-closed・緩和なし） | M1・R6・helper DrillError | Task 2/3/4 | M1/R6＋run_drill 既存 except 経路 |
| 運用契約の文書同期 | SKILL 記述一致 | Task 5 | 目視＋budget |

## 自己レビュー

- 仕様カバレッジ: 設計ノートの 4 ユニット（marker.sh/evidence.sh/record/drill）全てに Task と RED テストがある。設計「テスト戦略」の全項目（nomatch/npm-true/正規 pytest/red 非退行/patterns 欠損/64KiB/import プローブ/正規 baseline/rc3/STRONG/WEAK 両半/zero-run/pair 片半/echo 偽造/exit5）を M/R/D 系へ写像済み
- 曖昧さ検出: 「挙動不変」の唯一の例外（部分読込 patterns の rc3 厳格化）を Task 2 に明記。exit_code=0 定数の根拠を Task 4 に pin
- 型の整合性: `marker_verdict(output, command, exit_code=0, marker_lib=None) -> bool` を Task 3 で定義し Task 4 が同シグネチャで消費。`aegis_marker_verdict <exit_code> <command>` の引数順は設計ノートと一致
- 境界整合性: Boundary Map の Consumes は全て先行 Task の Produces に存在

## リスク

- リスク1: `pytest -q` の正規 green が拒否される（意図した運用変更・実測裏取り済み）→ 対策: stderr/BLOCKED 文言で「`-q` を外す」を明示・usage/judge 案内/SKILL/既存テストを同期（R2 が案内文を pin）。将来の `-q` 対応は marker 覆域拡張として descope（brainstorm 決定・axis 3 の緩和は moat 弱体化のため単独 iter で審査）
- リスク2: 既存 drill テストのダミー test_command 全滅 → 対策: Task 1 で実ランナーへ both-green 移行（現行実装でも green を確認してからコミット）・baseline 非到達テストは据置＋理由コメント
- リスク3: suite 実行時間増（fixture 実ランナー化・E2E あたり実行 3-6 回×約 0.1-0.2s）→ 対策: Task 5 で所要時間を実測記録・許容（推定 +5〜10s）
- リスク4: bash 3.2 互換（LEARNINGS line130）→ 対策: marker.sh は移動コード＋`${arr[*]:-}` ガードのみ（連想配列/mapfile 不使用）・`bash -n` を受入条件化
- リスク5: `$(cat)` は NUL を落とし末尾改行を剥ぐ → marker regex は `(^|\n)` アンカーで内容行を見るため判定に影響なし（注記のみ・挙動変更なし）
- リスク6: record の marker 検査は実行「後」に走る（コマンド副作用は発生済み）→ 契約上問題なし: record の「非実行」保証は検証 1-3（runner/シェル互換/NO_RUN）の事前検証に限られ、marker は「記録前」ゲート。テスト R1 は記録阻止（ログ非書込）を pin
- リスク7（**残余・実装で塞がない**）: 出力を任意 script が支配するランナーの echo-marker 偽装 — `npm test` の script を `echo 'Tests: 3 passed, 3 total'` にすると STRONG jest marker がヒットし verdict true になる（grill-plan 致命2 で実証）。marker は出力ベースの証明であり、この層は原理的に区別不能。列挙で塞ぎに行かない（denylist 回帰＝SF-014 の再生産）。fingerprint/judge/人手プレビュー/drill（echo script は mutant を殺せず FAIL）の多層で contained。record docstring（Task 4）と SF-014（docs phase）へ明記する
- リスク8（判断記録）: profile manifest（templates/profiles/*.json）へ marker.sh を追加**しない** — record が同様にハード依存する patterns.sh も未収載の既存慣行と整合し、欠損時は rc2 の可視 fail-closed で沈黙劣化しないため（配布自体は setup.sh の hooks/lib/*.sh glob で全プロファイル共通）

## 完了条件

- [ ] 全テスト pass（full suite・移行後の実測数を記録）
- [ ] レビュー完了（subagent-dev の 2 段階レビュー＋phase-level review）
- [ ] evidence.sh 挙動不変の回帰網（test_test_marker_zero_run.py 等・無変更のまま）green
- [ ] 拒否経路の手動 E2E（qa フェーズ）: nomatch discover→rc2／`-q`→rc2＋案内／正規 pytest→green＋marker:true／import プローブ drill→BLOCKED

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->
