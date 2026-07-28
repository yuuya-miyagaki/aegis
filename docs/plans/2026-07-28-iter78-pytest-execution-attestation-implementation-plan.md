# iter78 pytest execution attestation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-dev（.claude/skills/subagent-dev/SKILL.md）で task 単位に実装。Steps は checkbox (`- [ ]`) で追跡。

**Goal:** テスト実行証跡を出力テキスト解析から「argv spawn＋pytest 構造化イベント」の positive proof に一本化し、pytest family の decisive green を `src:"attested"` のみに制限する（SF-014/SF-022 根治・SF-015 attested 経路解消）。

**Architecture:** 新 CLI `scripts/attest-test-run.py` が pytest を shell なし argv spawn（`-p aegis_attest_plugin` 注入）で起動し、プラグインが書く JSONL イベントと waitpid の実 exit code を突合して `src:"attested"` エントリを evidence-log に記録。judge は pytest family の observed/manual 'ok' を transparent 化し、attested のみ decisive green とする。

**Tech Stack:** python3 stdlib のみ（追加依存ゼロ）。pytest family 判定は `hooks/lib/patterns.sh` の `AEGIS_TEST_IS_PYTEST_REGEX` を単一ソースとして bash-source 経由で読む。

**設計正本:** `docs/specs/2026-07-28-iter78-pytest-execution-attestation-design.md`（本 plan と乖離したら design が正）

## Global Constraints

- 外部依存ゼロ（stdlib/pure-bash のみ）。`hooks/lib/patterns.sh`・`hooks/lib/marker.sh` は**変更しない**。
- fail-closed 原則: 評価不能（イベント欠落・JSON 破損・exitstatus 突合不一致・IS_PYTEST regex 読込失敗）は green 側に倒さない。
- 非 pytest ランナー（jest/go/cargo/unittest/npm）は marker 経路のまま**挙動不変**。
- 既存 pin の**削除は 0**。契約変更で反転する pin は「契約更新」として1件ずつ理由コメント付きで書き替える（Task 4 の一覧）。
- コミットは per-task。コミットメッセージ末尾に `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。
- 版数 bump（v1.31.4→v1.32.0）は ship フェーズで行う（本 plan のスコープ外）。

## ファイル構成

| ファイル | 種別 | 責務 |
|---|---|---|
| `scripts/aegis_attest_plugin.py` | 新規 | pytest プラグイン。イベントの忠実な JSONL 書出のみ（判定しない） |
| `scripts/attest-test-run.py` | 新規 | attestor CLI: 検証→argv spawn→イベント/exit 突合→evidence-log 記録 |
| `scripts/build-judge-card.py` | 改修 | `_is_pytest_regex` loader＋`is_pytest_family_cmd`＋src allowlist attested＋pytest-green 制限 |
| `scripts/record-test-result.py` | 改修 | pytest family を rc2 で attest へ誘導 |
| `hooks/lib/scripts-manifest.tsv` | 改修 | 新規 2 スクリプトの分類行追加 |
| `tests/test_attest_execution.py` | 新規 | attest 全 pin（unit＋e2e＋differential） |
| `tests/test_test_runner_realness.py` ほか | 改修 | 契約更新 pin（Task 4 一覧） |
| `.claude/skills/qa-verification/SKILL.md`・`.claude/skills/tdd/SKILL.md`（言及があれば） | 改修 | pytest は attest 経由の手順に更新 |

---

### Task 1: RED — 差分 pin バッテリ（旧実装で赤を実測）

**Files:**
- Create: `tests/test_attest_execution.py`
- Test: 同上

**Interfaces（後続 Task が満たすべき契約）:**
- `scripts/attest-test-run.py` CLI: `python3 scripts/attest-test-run.py [--root R] [--timeout N] "<pytest cmd>"`。rc0=記録済（stdout `attested: green` / rc1=記録済 red `attested: red`）・rc2=不成立/拒否（記録なし・stderr に理由）。
- evidence エントリ: `{"v":1,"ts":…,"src":"attested","cmd":…,"status":"ok|fail","payload_sha":…,"fp":…,"counts":{"executed":n,"passed":n,"failed":n,"skipped":n,"errors":n,"xfailed":n,"xpassed":n,"collection_errors":n},"exit":n}`
- `build-judge-card.py` 追加公開関数: `is_pytest_family_cmd(root: Path, cmd: str) -> bool | None`（None=読込不能 fail-closed）。
- judge 契約: pytest family × src∈{manual,observed} × status ok → transparent skip。src=attested → fp 一致で status 通り decidable。

- [ ] **Step 1: テストファイル作成（下記グループを全部書く）**

グループ A — attestor 検証拒否（実行前 rc2・記録なし）:
- `test_reject_non_pytest_cmd`（`npm test` → rc2・stderr に record 誘導）
- `test_reject_shell_operator`（`python3 -m pytest; true` → rc2）
- `test_reject_env_assign_prefix`（`X=1 pytest` → rc2）
- `test_reject_plugin_suppression`（`pytest -p no:aegis_attest_plugin` → rc2）
- `test_reject_unparsable_quote`（`pytest "x` → rc2）

グループ B — attest e2e（tmp git repo＋極小 suite を作って実走）:
- `test_green_recorded_on_passing_suite`（2 passed → rc0・エントリ src=attested/status ok/counts.executed==2/exit==0）
- `test_red_recorded_on_failing_suite`（1 failed → rc1・status fail・fail-visible）
- `test_zero_run_rejected_all_skip`（全 `@pytest.mark.skip` → rc2・記録なし）
- `test_no_tests_collected_recorded_red`（テスト 0 収集・pytest exit 5 → **rc1・status fail 記録**。exit≠0 は red の実信号＝record の exit-5 先例と整合・fail-visible。rc2 は「exit 0 なのに proof なし」の場合のみ）
- `test_collect_only_rejected`（`pytest --collect-only` → executed=0 → rc2。NO_RUN denylist なしで positive proof が塞ぐことの実証）
- `test_all_xfail_green`（全 `@pytest.mark.xfail` で失敗する suite → exit 0・executed==N → rc0 green＝SF-015 の attested 経路解消 pin）
- `test_collection_error_red`（import エラー suite → status fail・counts.collection_errors>=1）
- `test_fake_output_ignored`（テスト内で `===== 999 passed in 0.01s =====` を print しつつ assert False → status fail＝出力非依存の本命構造 pin）
- `test_event_file_sabotage_fails_closed`（conftest の sessionfinish で event ファイルを truncate → rc2・green 不能＝in-process 妨害が fail-closed 側に倒れる実証）

グループ C — judge 契約（既存 judge テストのヘルパー流儀で evidence-log を組み立て）:
- `test_observed_pytest_ok_no_longer_decides`（observed/ok/marker_verified:true/fp 一致の pytest エントリのみ → 旧: green・新: unverified）**← Task 1 時点で赤になる differential の主役**
- `test_manual_pytest_ok_no_longer_decides`（manual/ok/fp 一致の pytest エントリのみ → 旧: green・新: unverified＝manual 経路も同時に閉じる differential）
- `test_observed_pytest_ok_transparent_falls_through_to_attested`（新しい observed pytest ok の下に attested ok → green）
- `test_attested_decides_green` / `test_attested_decides_red`（手書き attested エントリ・fp 一致）
- `test_attested_stale_fp_unverified`
- `test_observed_pytest_fail_still_red`（fail-visible 維持）
- `test_non_pytest_observed_ok_still_decides`（`npm test` observed ok marker_verified:true → green のまま＝非 pytest 不変 pin）
- `test_manual_nonpytest_still_decides`（unittest 系 manual ok → green のまま）
- `test_attested_washed_cmd_transparent`（手書き attested ok＋cmd に `;` → transparent＝防御多層 pin）
- `test_is_pytest_family_cmd_none_fail_closed`（patterns.sh 不在 root → None・judge は unverified）
- `test_handwritten_attested_residual_documented`（counts なし手書き attested ok が status で決まる＝manual と同じ pre-existing 天井の documenting pin）

グループ D — record 誘導:
- `test_record_rejects_pytest_family`（`python3 -m pytest` → rc2・stderr に attest-test-run.py 誘導・ログ非書込）
- `test_record_nonpytest_unchanged`（既存の非 pytest 受理経路が不変であることの回帰 pin・例: unittest 系は従来コードパスに到達）

- [ ] **Step 2: RED を実測して記録**

Run: `python3 -m pytest tests/test_attest_execution.py -v 2>&1 | tail -15`
Expected: グループ A/B/D と C の新契約 pin が FAIL（attest-test-run.py 不在・judge 旧契約）。**赤/緑の実数を控えて Task 6 の統合検証と付き合わせる**（iter77 の記録ずれ教訓）。

- [ ] **Step 3: Commit**

```bash
git add tests/test_attest_execution.py
git commit -m "test(iter78): attestation RED バッテリ — attestor 検証/e2e/judge 契約/record 誘導の差分 pin（赤N/緑M 実測）"
```

---

### Task 2: aegis_attest_plugin.py（イベント書出プラグイン）

**Files:**
- Create: `scripts/aegis_attest_plugin.py`
- Modify: `hooks/lib/scripts-manifest.tsv`（`scripts/aegis_attest_plugin.py	import-only` 行追加・**タブ区切り厳格**）

**Interfaces:**
- Produces: 環境変数 `AEGIS_ATTEST_EVENT_PATH` が指すファイルへ JSONL 追記。イベント3種:
  - `{"e":"collect_error","nodeid":<str>}`（pytest_collectreport の report.failed 時）
  - `{"e":"test","nodeid":<str>,"when":"setup|call|teardown","outcome":"passed|failed|skipped","wasxfail":<bool>}`
  - `{"e":"sessionfinish","exitstatus":<int>}`
- env 未設定時は**完全 no-op**（誤 import 安全）。書出失敗は握って続行（テスト実行を壊さない。fail-closed 保証は attestor 側の突合が持つ）。

- [ ] **Step 1: 実装**

```python
#!/usr/bin/env python3
"""pytest attestation plugin (iter78). Writes structured execution events to
$AEGIS_ATTEST_EVENT_PATH as JSONL. FAITHFUL RECORDING ONLY — no counting, no
verdict; aggregation lives in scripts/attest-test-run.py so there is exactly
one decision point. No-op without the env var (safe to import anywhere).
Internal failures are swallowed: a dead plugin must not break the test run;
missing events fail CLOSED at the attestor (rc2, no green)."""
import json
import os

_PATH = os.environ.get("AEGIS_ATTEST_EVENT_PATH")


def _emit(obj):
    if not _PATH:
        return
    try:
        with open(_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


def pytest_collectreport(report):
    try:
        if report.failed:
            _emit({"e": "collect_error", "nodeid": str(getattr(report, "nodeid", ""))})
    except Exception:
        pass


def pytest_runtest_logreport(report):
    try:
        _emit({"e": "test", "nodeid": str(report.nodeid), "when": str(report.when),
               "outcome": str(report.outcome),
               "wasxfail": hasattr(report, "wasxfail")})
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    try:
        _emit({"e": "sessionfinish", "exitstatus": int(exitstatus)})
    except Exception:
        pass
```

- [ ] **Step 2: manifest 行を追加**（`printf 'scripts/aegis_attest_plugin.py\timport-only\n'` の内容を該当セクションに Edit で追記。タブ必須）

- [ ] **Step 3: contract 検査で方向1を確認**

Run: `python3 scripts/check_framework_contract.py 2>&1 | tail -3`
Expected: scripts-manifest 系 FAIL なし（attest-test-run.py 未作成の行は**まだ追加しない**こと）

- [ ] **Step 4: Commit**

```bash
git add scripts/aegis_attest_plugin.py hooks/lib/scripts-manifest.tsv
git commit -m "feat(iter78): aegis_attest_plugin — pytest 構造化イベントの忠実書出（判定なし・no-op 安全）"
```

---

### Task 3: attest-test-run.py（attestor CLI）

**Files:**
- Create: `scripts/attest-test-run.py`
- Modify: `hooks/lib/scripts-manifest.tsv`（`scripts/attest-test-run.py	ask` 行追加）
- Test: `tests/test_attest_execution.py` グループ A/B が緑になる

**Interfaces:**
- Consumes: `build-judge-card.py` の `is_pytest_family_cmd`（Task 4 で追加。**本 Task 時点では judge に loader ごと先行追加してよい**が、二重実装は禁止＝必ず judge 側に置き attestor は `_load` で使う。record と同じ `_load("judge_mod", "build-judge-card.py")` パターン）、`judge.current_fingerprint(root)`。
- Produces: evidence-log の attested エントリ（Task 1 Interfaces のスキーマ）。

- [ ] **Step 1: 実装**

構成（record-test-result.py の文体・usage 誘導を踏襲）:

```python
#!/usr/bin/env python3
"""Execution attestation for pytest (iter78, SF-014/SF-022 root fix).

Runs the given pytest command WITHOUT a shell (argv spawn — exit laundering
like `; true` is impossible by construction), injects the event plugin
(scripts/aegis_attest_plugin.py), and reconciles the structured event stream
against the child's REAL exit code (waitpid). The child's stdout/stderr are
inherited, NEVER parsed — fake output cannot produce events. A green record
requires exit==0 AND executed>=1 AND failed==errors==collection_errors==0,
where executed = passed+failed+xfailed+xpassed from call-phase events (skips
excluded; an all-xfail suite IS executed — closes the SF-015 false negative
on this path). Any evaluation gap (missing sessionfinish, exitstatus !=
returncode, corrupt event JSON, timeout) is rc2: no record, no green —
fail-closed. Residual ceiling (documented, pre-existing class): in-process
sabotage (conftest unregistering the plugin / forging events) and
hand-written log entries — deliberate self-deception, contained by
defence-in-depth (drill, human preview, fingerprint)."""
```

処理手順（すべて実装すること）:
1. argparse: `--root`（default "."）・`--timeout`（int・default 600）・`command`（単一文字列）。
2. `_load` で judge module を読み込み（record と同一パターン）。
3. 検証（順に・全て rc2＋stderr 誘導・記録なし）:
   - `judge.is_pytest_family_cmd(root, args.command[:500])` が None → 「patterns.sh を読み込めません…fail-closed」／False → 「pytest family ではありません。非 pytest ランナーは scripts/record-test-result.py を使ってください」
   - `shlex.split` 失敗／空 argv／`"=" in argv[0]`／argv 中に `{"&&","||",";","|","&"}`（record の `_SHELL_OP_TOKENS` と同集合）
   - `-p` 妨害: argv を走査し、`-p` の次トークンまたは `-p` 直結値（`-pno:...`）に文字列 `aegis_attest_plugin` を含む → rc2「attestation プラグインの指定/打ち消しは禁止」
4. イベントファイル: `root/.claude/tmp/` を mkdir -p し `tempfile.mkstemp(prefix="attest-", suffix=".jsonl", dir=...)` で作成（空で close）。
5. spawn: `subprocess.run(argv + ["-p", "aegis_attest_plugin"], cwd=str(root), timeout=args.timeout, env=child_env, shell=False)`。`child_env` = `os.environ` コピー＋`PYTHONPATH` の**先頭**に `Path(__file__).resolve().parent`（scripts/）を `os.pathsep` 連結＋`AEGIS_ATTEST_EVENT_PATH=<イベントファイル絶対パス>`。stdout/stderr は**継承**（capture しない）。TimeoutExpired → rc2。
6. イベント読取: JSONL を1行ずつ `json.loads`。**1行でも破損 → rc2**（fail-closed）。集計:
   - `calls = {}` に `when=="call"` の `(outcome, wasxfail)` を nodeid キーで格納（同一 nodeid は最後を採用）
   - `errors` = setup/teardown の failed 件数、`skipped` = setup の skipped 件数＋call の素 skipped（wasxfail なし）件数
   - `passed`=call passed かつ非 wasxfail／`xpassed`=call passed かつ wasxfail／`failed`=call failed／`xfailed`=call skipped かつ wasxfail
   - `executed = passed + failed + xfailed + xpassed`
   - `collection_errors` = collect_error 件数、`sessionfinish` = exitstatus（欠落は None）
7. 突合（順に・rc2＝記録なし）:
   - `sessionfinish is None` → rc2「イベント欠落＝attest 不成立」
   - `sessionfinish != proc.returncode` → rc2「exit 突合不一致」
   - `proc.returncode == 0 and (failed or errors or collection_errors)` → rc2「exit 0 なのに失敗イベント＝不整合」
   - `proc.returncode == 0 and executed == 0` → rc2「実行 0 件（all-skip / collect-only）は green 不成立」
   - ※ `returncode != 0` は突合系（sessionfinish 欠落/不一致）を除き **red として記録**（exit 5 の収集 0 も red＝record の exit-5 先例と整合・fail-visible）。
8. 記録: `status = "ok" if returncode == 0 else "fail"`。エントリは Task 1 スキーマ通り（`cmd` はユーザーコマンド `[:500]`＝注入 `-p` を含めない・`payload_sha` はイベントファイル生バイトの sha256・`fp` は `judge.current_fingerprint(root)`）。`.claude/evidence-log.jsonl` へ追記。stdout に `attested: green|red`。rc は green=0／red=1。**イベントファイルは try/finally で全パス（timeout・rc2 含む）削除**。

- [ ] **Step 2: manifest 行を追加**（`scripts/attest-test-run.py	ask`）

- [ ] **Step 3: グループ A/B を実行**

Run: `python3 -m pytest tests/test_attest_execution.py -v -k "reject or recorded or zero_run or collect or xfail or fake_output or sabotage" 2>&1 | tail -15`
Expected: グループ A/B 全 PASS（judge/record 由来の C/D はまだ赤）

- [ ] **Step 4: contract 検査**

Run: `python3 scripts/check_framework_contract.py 2>&1 | tail -3`
Expected: FAIL なし

- [ ] **Step 5: Commit**

```bash
git add scripts/attest-test-run.py hooks/lib/scripts-manifest.tsv
git commit -m "feat(iter78): attest-test-run — argv spawn＋イベント/exit 突合で positive proof・src=attested 記録"
```

---

### Task 4: build-judge-card.py（attested 受入＋pytest-green 制限）＋契約更新 pin

**Files:**
- Modify: `scripts/build-judge-card.py`
- Modify: 契約更新対象の既存テスト（下記一覧・**削除禁止・1件ずつ理由コメント**）
- Test: `tests/test_attest_execution.py` グループ C が緑

**Interfaces:**
- Produces: `is_pytest_family_cmd(root, cmd) -> bool | None`（attestor/record が `_load` 消費）。judge scan の新契約（Task 1 Interfaces）。

- [ ] **Step 1: `_is_pytest_regex` loader＋`is_pytest_family_cmd` を追加**

`_tr_strip_patterns` の直後に配置:

```python
def _is_pytest_regex(root: Path):
    """Load AEGIS_TEST_IS_PYTEST_REGEX from patterns.sh (single source; same
    bash-source printf route as _test_runner_patterns). None = unreadable /
    uncompilable — callers must fail CLOSED (unverified / rc2), never treat
    as 'not pytest'."""
    lib = root / "hooks" / "lib" / "patterns.sh"
    if not lib.is_file():
        return None
    try:
        out = subprocess.run(
            ["bash", "-c",
             'source "$1"; printf "%s" "$AEGIS_TEST_IS_PYTEST_REGEX"',
             "_", str(lib)],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    raw = out.stdout.strip()
    if not raw:
        return None
    try:
        return re.compile(raw)
    except re.error:
        return None


def is_pytest_family_cmd(root: Path, cmd: str) -> bool | None:
    """Is `cmd` in the pytest family, per the SAME normalization pipeline as
    _norm_cmd_match (newlines→';', quoted spans masked to Q)? None = cannot
    evaluate (fail-closed). Single source for the judge scan's green
    restriction, attest-test-run.py's admission check, and
    record-test-result.py's redirect — checker == consumer."""
    ispy = _is_pytest_regex(root)
    if ispy is None:
        return None
    strips = _tr_strip_patterns(root)
    if len(strips) != 2:
        return None
    c = (cmd or "").replace("\n", ";")
    for sp in strips:
        c = sp.sub("Q", c)
    return bool(ispy.search(c))
```

- [ ] **Step 2: `read_test_result_detail` の scan を変更**

1. 冒頭の loader 群に追加（fail-closed）:
```python
    ispy = _is_pytest_regex(root)
    if ispy is None:
        return unverified
```
2. src allowlist（`:336` 付近）を `("manual", "observed", "attested")` に拡張し、コメントの「A future legitimate src」注記を「iter78 で導入済み」に更新。
3. allowlist 直後・washed-green の**前**に pytest-green 制限を挿入:
```python
        # iter78 (SF-014/SF-022 root fix): pytest-family green is decided by
        # EXECUTION ATTESTATION only. An observed/manual 'ok' whose cmd is in
        # the pytest family carries only output/exit-derived proof — the very
        # layer the attestation replaces — so it can certify nothing:
        # TRANSPARENT (an older attested entry for the SAME fingerprint may
        # still decide). 'fail' stays decidable red (fail-visible). Non-pytest
        # runners keep the marker path unchanged (roadmap §6: no simultaneous
        # ecosystem adapters).
        _norm = (d.get("cmd") or "").replace("\n", ";")
        for _sp in strips:
            _norm = _sp.sub("Q", _norm)
        if (d.get("src") in ("manual", "observed")
                and d.get("status") == "ok" and ispy.search(_norm)):
            continue
```
4. washed-green 判定（`:345`）の `d.get("src") == "observed"` を `d.get("src") in ("observed", "attested")` に拡張（attested の実 writer は shell 演算子 cmd を構造上生成しない＝該当は手書き偽造のみ。透明化は純安全側の多層防御）。コメントに1行追記。
- `undecidable`（marker_verified 検査）は observed 限定のまま**変更しない**（attested は marker 非依存）。

- [ ] **Step 3: 契約更新 pin の書き替え（削除 0）**

grill-plan 実測（2026-07-28・親が対象 3 ファイルの全 `_ev_line`/record 呼出を読んで分類）で確定した契約更新は **2 クラス・約 16 件**。方針: **pin の目的（何を守るか）は不変のまま、pytest 固有でない目的の pin はコマンドを非 pytest ランナーへ機械的に差し替えて保存**。各書き替えに `iter78 契約更新:` で始まる理由コメントを付ける。**削除 0**。

**スワップ標準レシピ**: judge-scan 系合成エントリは cmd `pytest`/`python3 -m pytest …` → `python3 -m unittest`（runner regex 一致・marker 経路存続）へ。washed/クォート系は `jest …`/`npm test` 形も可。record 実走系は t_pass.py/t_fail.py（pytest 形式）の**unittest 双子**（`u_pass.py`/`u_fail.py`: `unittest.TestCase` サブクラス・`python3 -m unittest` で実走・weak pair marker `Ran N tests in`+`OK`/`FAILED` が実出力で成立）を fixture に追加して差し替え。

クラス A — assertion が反転する（書き替え必須）:

| # | テスト | 反転 |
|---|---|---|
| A1 | `test_judge_card.py::TestReadTestResult::test_broken_lines_skipped` | pytest ok green→unverified（cmd スワップ） |
| A2 | `test_judge_card.py::TestReadTestResult::test_rotated_dot1_is_scanned` | 同上 |
| A3 | `test_judge_card.py::test_w2a2_washed_ok_is_transparent_older_clean_green_decides` | 古い clean pytest ok green→unverified（両 cmd を npm/jest へ） |
| A4 | `test_judge_card.py::test_w2a4_quoted_operator_is_not_washed` | pytest ok green→unverified（`jest -t "a|b"` 形へ） |
| A5 | `test_judge_card.py::test_passing_command_appends_manual_ok` | record 経由 pytest manual ok → rc2（unittest 双子実走へ） |
| A6 | `test_test_runner_realness.py::test_entry_with_marker_verified_true_and_ok_returns_green` | observed pytest ok green→unverified（cmd スワップ。pytest 版の新契約は Task 1 C が pin） |
| A7 | `test_test_runner_realness.py::test_manual_record_is_trusted_even_without_marker` | manual pytest ok green→unverified（cmd スワップ） |
| A8 | `test_test_runner_realness.py::test_trusted_green_survives_noise_ok_entry` | trusted green の cmd が pytest → unverified（ヘルパー default cmd="pytest tests/" ごとスワップ） |
| A9 | `test_test_runner_realness.py::test_marker_verified_green_survives_noise_ok_entry` | 同上 |
| A10 | `test_record_test_result.py::test_valid_runner_still_records` | pytest manual green rc0→rc2（unittest 双子実走へ） |
| A11 | `test_record_test_result.py::test_red_run_recorded_without_marker` | pytest manual red rc0→rc2（同上） |
| A12 | `test_record_test_result.py::test_quiet_pytest_green_rejected_with_guidance` | 旧: 実行後 marker 不成立 rc2（`-q` 案内）→ 新: 実行前 redirect rc2。**redirect pin に転用**（quiet pytest が実行されず attest 誘導 rc2 になること＋`-q` は attest では制約でなくなる旨をコメント） |
| A13 | `test_record_test_result.py::test_marker_lib_missing_fail_closed` | 旧: pytest cmd で marker lib 欠如 rc2 → 新: redirect が先に発火し目的が死ぬ → cmd を unittest 形へスワップして fail-closed pin を保存 |

クラス B — assertion は通るが pin の検出力が死ぬ（cmd スワップで保存）:

| # | テスト | 理由 |
|---|---|---|
| B1 | `test_judge_card.py::TestReadTestResult::test_stale_fp_is_unverified` | pytest ok は fp 検査前に transparent 化＝fp gate を踏まなくなる → unittest へ |
| B2 | `test_judge_card.py::TestReadTestResult::test_newest_stale_does_not_fall_back_to_older_fresh` | 同上（no-fallback の検出力保存） |
| B3 | `test_judge_card.py::test_mask_is_substitution_not_deletion` | 削除変異時の green 偽装経路が pytest 制限で塞がれ mutation killer が無効化 → `"echo" vitest run` 形へ |
| B4 | `test_test_runner_realness.py::test_entry_without_marker_verified_field_returns_unverified` | schema 欠如の透明化 pin が pytest 制限に先取りされる → unittest へ |
| B5 | `test_test_runner_realness.py::test_entry_with_marker_verified_false_returns_unverified` | 同上 |

非反転の確認済み（変更しない）: `test_fail_with_matching_fp_is_red`・`test_latest_matching_entry_wins`・`test_w2a3_washed_fail_stays_red`・`test_w2a5_multiline_cmd_is_washed`・W3-1/2/3（src="forged"）・`test_decidable_red_cannot_be_laundered_by_noise_ok_entry`・`test_evidence_hooks.py::test_observed_ok_certifies_green`（unittest）・record の no_run/env/operator/quote/zero-run/npm 系（redirect を既存検証の**後**に置くため文言不変＝Task 5 参照）。

手順（必須）: 本 Task の実装後に `python3 -m pytest tests/test_judge_card.py tests/test_test_runner_realness.py tests/test_record_test_result.py tests/test_evidence_lib.py tests/test_evidence_hooks.py -v 2>&1 | tail -20` を回し、落ちた全件が上表と一致することを突合。**表外の落ちが出たら同方針で書き替えてこの表に追記**（silent 修正禁止）。

- [ ] **Step 4: グループ C＋既存 judge 系を実行**

Run: `python3 -m pytest tests/test_attest_execution.py tests/test_test_runner_realness.py tests/test_judge_card.py tests/test_evidence_lib.py tests/test_evidence_hooks.py -v 2>&1 | tail -8`
Expected: 全 PASS（グループ D のみ残赤）

- [ ] **Step 5: Commit**

```bash
git add scripts/build-judge-card.py tests/
git commit -m "feat(iter78): judge — src=attested 受入＋pytest family の decisive green を attested のみに制限（契約更新 pin N 件・削除0）"
```

---

### Task 5: record-test-result.py（pytest family 誘導）

**Files:**
- Modify: `scripts/record-test-result.py`
- Test: `tests/test_attest_execution.py` グループ D が緑

**Interfaces:**
- Consumes: `judge.is_pytest_family_cmd`（Task 4）。

- [ ] **Step 1: 実装**

**挿入位置は step 3（NO_RUN 検査）の後・`drill._execute` の直前**（step 1 直後ではない）。理由: 既存の malformation 系 pin（no-run flag／env prefix／shell operator／unparsable quote）の rc2 文言を保存し契約更新の面積を最小化する。pytest × malformed は従来文言のまま rc2、pytest × well-formed のみが redirect に到達する（どちらも記録なし＝安全性は同値）。

```python
    # iter78: pytest-family results are recorded via EXECUTION ATTESTATION
    # only (scripts/attest-test-run.py — argv spawn + structured events).
    # This writer's marker-based proof is the output layer the attestation
    # replaces; keeping a second green path here would let a forged output
    # bypass the stronger proof. Red goes through attest too — one path per
    # runner family. Placed AFTER the malformation checks so their rc2
    # messages are preserved; a well-formed pytest cmd is redirected BEFORE
    # execution. None = patterns unreadable — fail-closed like step 1.
    fam = judge.is_pytest_family_cmd(root, args.command[:500])
    if fam is None:
        return _reject("patterns.sh を読み込めません — pytest family 判定を実行"
                       "できないため fail-closed（framework install が壊れています）")
    if fam:
        return _reject(
            "pytest family は execution attestation 経由でのみ記録します: "
            'python3 scripts/attest-test-run.py "<コマンド>" を使ってください'
            "（green/red とも attest 側で記録・出力ベース marker 経路は廃止）")
```

module docstring の Residual 節に1段落追記: 「iter78: pytest family は本スクリプトから attestation へ移管（出力ベース残余 (a)-(c) は非 pytest ランナーにのみ残る）」。

- [ ] **Step 2: グループ D＋record 既存テストを実行**

Run: `python3 -m pytest tests/test_attest_execution.py tests/test_test_runner_realness.py -v 2>&1 | tail -8`
Expected: 全 PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/record-test-result.py tests/
git commit -m "feat(iter78): record — pytest family を attest-test-run へ rc2 誘導（経路一本化）"
```

---

### Task 6: 統合検証＋ドッグフード attest

- [ ] **Step 1: full suite**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: 全 green（Task 1 で控えた赤の実数が全て緑化・skip 数は従来通り）

- [ ] **Step 2: ドッグフード attest（本 repo の suite を attestor で実走）**

Run: `python3 scripts/attest-test-run.py --timeout 1800 "python3 -m pytest"`（rc0・`attested: green`。フル suite は e2e が子 pytest を多数 spawn するため timeout を明示的に広げる）
→ `python3 scripts/build-judge-card.py 2>/dev/null | grep -i test`（または judge card 出力相当）で tests:green・src=attested を確認。
※ 注意: attest 実行自体の observed エントリ（`attest-test-run.py Q` 形）は runner 非該当で scan 対象外＝attested が deciding entry になることを確認する。

- [ ] **Step 3: contract / drift / doctor**

Run: `python3 scripts/check_framework_contract.py 2>&1 | tail -3 && python3 scripts/check_reference_drift.py 2>&1 | tail -3 && python3 scripts/status_doctor.py 2>&1 | tail -2`
Expected: すべて PASS

- [ ] **Step 4: skill 手順の更新**

`.claude/skills/qa-verification/SKILL.md` の「手動記録の green は marker verdict 必須」節（L46-50）に pytest→attest の一段落を追記（非 pytest は従来通り record）。tdd/SKILL.md は record 言及なし＝変更不要（Explore 確認済み）。`hooks/lib/evidence.sh` ヘッダの schema コメント（L16 付近「record-test-result.py appends the same schema with src:"manual"」）に attested writer（attest-test-run.py・counts/exit 付き）の1行を追記＝3 writer の文書整合。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(iter78): 統合検証 — full green・ドッグフード attest green・skill 手順を attest 経由に更新"
```

---

## Self-Review チェック（plan 完成時に実施済みであること)

1. spec カバレッジ: design の全節（attestor/plugin/judge/record/manifest/テスト戦略 7 分類）に対応 Task あり。
2. placeholder ゼロ（AFFECTED-PINS は grill-plan 実測で A1-A13＋B1-B5 に確定済み）。
3. 型/名前整合: `is_pytest_family_cmd`・`AEGIS_ATTEST_EVENT_PATH`・イベント3種・counts 8 キーは全 Task で同一綴り。

## grill-plan 反映記録（2026-07-28）

- 致命1: 反転 pin の undercount（Explore 1次調査 6 件→親実測 A13＋B5=18 件）→ Task 4 に全量表＋スワップ標準レシピ＋実測突合手順を明記。
- 致命2: pytest exit 5 の期待矛盾（グループ B が rc2・verdict 規則が red）→ red 記録 rc1 に統一（record の exit-5 先例と整合・fail-visible）。
- 致命3: record redirect の挿入位置が step1 直後だと malformation 系 pin の文言が全滅→ NO_RUN 後・実行前へ移動（churn 最小化・安全性同値）。
- 要検討反映: dogfood attest に `--timeout 1800` 明示／イベントファイルは try/finally 全パス削除／evidence.sh ヘッダに attested writer 追記。
- YAGNI 確認: attested counts の judge カード表示は不要（`判定源: src=` の汎用表示で attested が出ることを親が実測確認済み）。
