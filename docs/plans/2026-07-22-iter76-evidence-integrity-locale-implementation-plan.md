# iter76: evidence 整合＋locale 掃討完了 実装計画

> **For agentic workers:** 実行は `.claude/skills/subagent-dev/SKILL.md`（タスク単位 subagent＋2段レビュー）に従う。各タスクはチェックボックス（`- [ ]`）で追跡する。

**Goal:** washed-green（exit 洗浄）・unknown-src forge が judge green を製造できなくし、`check-runtime-state.sh` の不正バイト crash（fail-open）を消滅させる（roadmap §5 iter76 P0 完了条件）。

**Architecture:** 変更は 4 点＝(W1) check-runtime-state.sh に `LC_ALL=C`（iter73 同型・3 本目で locale 掃討完了）、(W2b) marker.sh に Stage 6「green 矛盾 veto」（exit=0×failure 証拠→false・patterns.sh の fail-token regex 1 本を消費）、(W2a) judge の observed-ok に washed-cmd transparent skip、(W3) judge に src allowlist（終端🟡）。全変更は「green 認定の締め付け」方向のみ＝新規 fail-open なし。

**Tech Stack:** bash 3.2 互換（macOS 既定）・python3 標準ライブラリのみ・BSD/GNU grep parity。

## Global Constraints

- 変更方向は fail-closed のみ: 新規分岐はすべて「green を作らない」方向。red→🟡 の降格を作らない（W2a-3/W2b-2 で pin）。
- パターンは grep -E（ERE）∩ python re の共通部分集合で書く（patterns.sh ヘッダ規約・`(^|\n)` 形は既存 family と同型）。
- marker.sh の Stage 内 grep は既存どおり `-a` 付き（不正バイトで binary 扱いになる GNU grep 対策・iter72 F4）。
- コミットはタスク単位（TDD: RED commit → 各 GREEN commit）。コミットメッセージ末尾に `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 実装 subagent は `model: opus`（工程別 tiering: 書く=opus・検証=session/fable）。レビュー系委譲は routing.md「Verification delegation」6 拘束（read-only 核）をプロンプトに含める。
- 「旧赤/新緑」differential pin が ship 条件（roadmap §5 原則）: Task 1 の RED 実測がその証明。

## 入力

- 参照要件: なし（framework 自己改善）
- 参照設計: `docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md`
- 動機正本: `docs/full-review-2026-07-19-dual-codex-fable.md` §4.2/§4.3/§5、`docs/security-followups.md` SF-012/SF-018

## Deploy Target

- Hosting/Database/CI-CD: **n/a**（ローカル配布のフレームワーク・task_size=M＝deploy phase は size routing で対象外）
- 互換性確認: n/a／認証方式: n/a

## Git 戦略

main 直コミット（本リポジトリの確立済み運用: タスク単位コミット・push はクローズ時）。

## ファイル構造（変更マップ）

- 変更: `hooks/check-runtime-state.sh`（`INPUT=$(cat)` 直後）— W1: C locale export
- 変更: `hooks/lib/patterns.sh`（COUNT_FAMILIES 配列の直後）— W2b: `AEGIS_TEST_FAIL_TOKEN_REGEX` 追加
- 変更: `hooks/lib/marker.sh`（rc3 ガード＋最終 `printf 'true'` 直前）— W2b: Stage 6 矛盾 veto・ガード 8 ソース化
- 変更: `scripts/build-judge-card.py`（`_norm_cmd_match` 付近＋`read_test_result_detail` 走査）— W2a: `_cmd_has_shell_operators`＋washed-ok skip／W3: src allowlist
- テスト: `tests/test_hook_locale_byte.py`（末尾 append）— RS1-4
- テスト: `tests/test_marker_lib.py`（末尾 append＋既存 1 件の exit code 修正）— W2b-1〜5
- テスト: `tests/test_judge_card.py`（末尾 append）— W2a-1〜5・W3-1〜3
- 文書: `docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md`（末尾 append）— 完全性主張の訂正
- 文書: `docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md` — 「新規 regex ゼロ」記述の正確化

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | RED テスト群（挙動契約） | なし |
| Task 2 | check-runtime-state.sh byte-safe 化 | Task 1 の RS pin |
| Task 3 | `AEGIS_TEST_FAIL_TOKEN_REGEX`・marker Stage 6 | Task 1 の W2b pin |
| Task 4 | `_cmd_has_shell_operators()`・src allowlist | Task 1 の W2a/W3 pin |
| Task 5 | 設計正本 2 文書の訂正・full suite green 記録 | Task 2-4 完了 |

循環依存なし。Task 2/3/4 は相互独立（並列可だが同一セッション逐次を推奨・レビュー粒度維持）。

## タスク分解

### Task 1: RED — 差分 pin テスト一式（旧実装で赤）

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** テスト `tests/test_hook_locale_byte.py` / `tests/test_marker_lib.py` / `tests/test_judge_card.py`（いずれも末尾 append・既存行は不変更）
**意図:** iter76 の全挙動変更を「旧=赤」で実測 pin する（roadmap の differential 要件）。
**TDD:** テスト → FAIL 分布確認 → コミット（実装なし）
**受入条件:** 新規 18 テスト中 **11 RED / 7 PASS**（分布は下記）・既存テストは全 green のまま。

- [ ] **Step 1-1: `tests/test_hook_locale_byte.py` 末尾に append**（既存 `run()`・`_UTF8_ENV` の直下慣習に従う。**ファイル冒頭 import に `tempfile` を追加**（現状 json/os/pathlib/subprocess のみ）。allow は `emit_allow`＝`{}` 出力＝`permissionDecision` キー不在＝**`decision is None` 規約**（既存 run() :74-76 と同一）——`"allow"` 文字列と比較してはならない〔grill 致命1〕）

```python
RUNTIME_STATE = ROOT / "hooks" / "check-runtime-state.sh"


def _rs_root(tmp: pathlib.Path) -> pathlib.Path:
    """check-runtime-state.sh 用 scratch root。docs/STATUS.md が無いと
    early-allow で tr に到達しない。task_type は非 framework（feature）に
    して post-fix の期待（STATUS 書込み=deny／無害=allow）を意味あるものに
    する（framework は task_type 判定で early-allow するが、crash 地点の
    tr :121 は判定より前なので pre-fix はどちらでも CRASH する）。"""
    (tmp / "docs").mkdir(parents=True)
    (tmp / "docs" / "STATUS.md").write_text(
        "---\ntask_type: feature\n---\n", encoding="utf-8")
    return tmp


def run_rs(command_str, root):
    """run() の check-runtime-state 版（CLAUDE_PROJECT_DIR 必須）。payload
    構築・0xFF 縮退・CRASH/None==allow 判定は run() と同一規約。"""
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": command_str}},
        ensure_ascii=False,
    ).encode("utf-8").replace(b"\xc3\xbf", b"\xff")
    env = dict(_UTF8_ENV, CLAUDE_PROJECT_DIR=str(root))
    proc = subprocess.run(
        ["bash", str(RUNTIME_STATE)], input=payload, env=env,
        capture_output=True, timeout=30)
    out = proc.stdout.decode(errors="replace").strip()
    if not out:
        return proc.returncode, "CRASH", ""
    try:
        obj = json.loads(out)
    except (ValueError, json.JSONDecodeError):
        return proc.returncode, "CRASH", ""
    hso = obj.get("hookSpecificOutput", {})
    decision = hso.get("permissionDecision")  # None == allow ({} empty object)
    reason = hso.get("permissionDecisionReason", "")
    return proc.returncode, decision, reason


class TestRuntimeStateByteSafety(unittest.TestCase):
    """SF-018 (iter76): check-runtime-state.sh は不正 UTF-8 stdin で crash
    してはならない。crash＝rc1・stdout 空＝decision なし＝唯一の非 framework
    runtime-state ガードの fail-open（iter73 掃討の未適用 3 本目。iter73 設計は
    『python3 抽出でバイト→空 CMD＝同型不成立』と主張したが surrogateescape は
    バイトを温存する＝反証済み・SF-018）。

    mutation-killer 構図: RS1（deny 側）と RS2（allow 側）が対。runtime-state
    の deny 文言は main/fallback 経路で共通のため reason 判別は使えず、RS2 の
    『crash せず判定を通過して {} に到達した』が LC_ALL 挿入位置の変異
    （extraction/tr の後方へ移動）を検出する唯一の証明。RS2 を冗長とみなして
    削らないこと。"""

    def test_rs1_byte_in_status_write_still_denies(self):
        # RS1（differential: pre-fix CRASH）: 0xFF を積んだ runtime-state
        # 書込みが crash せず通常どおり deny される。
        with tempfile.TemporaryDirectory() as d:
            root = _rs_root(pathlib.Path(d))
            rc, decision, _ = run_rs(
                "echo " + chr(0xFF) + " > docs/STATUS.md", root)
            self.assertEqual((rc, decision), (0, "deny"))

    def test_rs2_byte_in_benign_command_allows(self):
        # RS2（differential: pre-fix CRASH）: runtime-state に触れない
        # 0xFF 入りコマンドは allow（None==allow・crash による fail-open
        # ではなく判定を通過した allow であることが要点）。
        with tempfile.TemporaryDirectory() as d:
            root = _rs_root(pathlib.Path(d))
            rc, decision, _ = run_rs("echo " + chr(0xFF) + " hello", root)
            self.assertEqual(rc, 0)
            self.assertIsNone(decision)

    def test_rs3_ascii_status_write_still_denies(self):
        # RS3（非退行）: C locale 化が ASCII 経路の判定を変えない。
        with tempfile.TemporaryDirectory() as d:
            root = _rs_root(pathlib.Path(d))
            rc, decision, _ = run_rs("echo x > docs/STATUS.md", root)
            self.assertEqual((rc, decision), (0, "deny"))

    def test_rs4_japanese_quoted_mention_still_allows(self):
        # RS4（非退行）: C locale 下でも日本語（正 UTF-8 多バイト）は
        # PEP 540 で保全され、OBS-006 carve-out（quoted メッセージ内の
        # STATUS.md 言及は書込みでない）が維持される。
        with tempfile.TemporaryDirectory() as d:
            root = _rs_root(pathlib.Path(d))
            rc, decision, _ = run_rs(
                'git commit -m "docs/STATUS.md を更新"', root)
            self.assertEqual(rc, 0)
            self.assertIsNone(decision)
```

- [ ] **Step 1-2: `tests/test_marker_lib.py` 末尾に append**

```python
PYTEST_FAILED = ("platform darwin -- Python 3.9.6, pytest-8.4.2\n"
                 "rootdir: /tmp/x\ncollected 3 items\n\n"
                 "=========== 1 failed, 2 passed in 0.42s ===========\n")


class TestGreenContradictionVeto(unittest.TestCase):
    """iter76 SF-012(a) Stage 6: 出力に positive な failure 証拠があるのに
    exit code が 0 ＝ exit が洗浄された（`pytest -q; true`）か出力が偽造
    された run ＝ green を証明できない → false。実 red run（exit≠0）は
    軸の対象外＝verdict true のまま（judge の red 信号を守る）。"""

    def test_w2b1_failed_summary_with_exit0_is_false(self):
        # W2b-1（differential: pre-fix true）: washed-green の核。
        rc, out = _verdict(PYTEST_FAILED, "python3 -m pytest -q; true", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_w2b2_failed_summary_with_exit1_stays_true(self):
        # W2b-2（非退行）: 正直な red run — marker は「テストが走った」
        # 証明として true を維持（status=fail 側が red を出す）。
        rc, out = _verdict(PYTEST_FAILED, "python3 -m pytest -q", "1")
        self.assertEqual((rc, out), (0, "true"))

    def test_w2b3_cargo_zero_failed_green_stays_true(self):
        # W2b-3（非退行）: cargo は green でも常に `0 failed` を出力する。
        # 非ゼロアンカーが誤発火しないこと。
        out_text = ("running 3 tests\n"
                    "test tests::a ... ok\n"
                    "test result: ok. 3 passed; 0 failed; 0 ignored; "
                    "0 measured; 0 filtered out; finished in 0.01s\n")
        rc, out = _verdict(out_text, "cargo test", "0")
        self.assertEqual((rc, out), (0, "true"))

    def test_w2b4_unittest_failed_banner_with_exit0_is_false(self):
        # W2b-4（differential: pre-fix true）: unittest は Ran 行に failed
        # カウントを持たない＝FAILED バナー自体が証拠。
        out_text = "Ran 3 tests in 0.010s\n\nFAILED (failures=1)\n"
        rc, out = _verdict(out_text, "python3 -m unittest; true", "0")
        self.assertEqual((rc, out), (0, "false"))

    def test_w2b5_rc3_when_fail_token_regex_emptied(self):
        # W2b-5（differential: pre-fix rc0）: fail-token regex は 8 ソース
        # rc3 ガードの一員 — 空にされた install は「veto が黙って無効」
        # （fail-open）ではなく評価不能（rc3）。
        with tempfile.TemporaryDirectory() as d:
            lib_dir = Path(d)
            shutil.copy(MARKER_LIB, lib_dir / "marker.sh")
            pats = (ROOT / "hooks" / "lib" / "patterns.sh").read_text(
                encoding="utf-8")
            pats = re.sub(r"^AEGIS_TEST_FAIL_TOKEN_REGEX=.*$",
                          "AEGIS_TEST_FAIL_TOKEN_REGEX=''",
                          pats, flags=re.M)
            (lib_dir / "patterns.sh").write_text(pats, encoding="utf-8")
            rc, _out = _verdict(PYTEST_REAL, "python3 -m pytest tests/",
                                "0", lib=lib_dir / "marker.sh")
            self.assertEqual(rc, 3)
```

- [ ] **Step 1-3: `tests/test_judge_card.py` 末尾に append**（fixture は `TestReadTestResultFromEvidence.setUp` と同一形の複製。`_ev_line` は既存のまま・src 差し替えは `test_manual_src_counts` と同じ `json.loads`→書換え方式）

```python
class TestWashedGreenAndSrcAllowlist(unittest.TestCase):
    """iter76 W2a/W3 (SF-012): (a) observed-ok でシェル演算子連結 cmd は
    TRANSPARENT（exit 洗浄＝green を証明できない・fail は red のまま）、
    (b) src allowlist 外は TERMINAL unverified（fail-visible）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        sp.run(["git", "-C", str(self.root), "init", "-q"],
               check=True, capture_output=True)
        sp.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                "-c", "user.name=t", "commit", "-q", "--allow-empty",
                "-m", "init"], check=True, capture_output=True)
        _copy_lib(self.root)
        (self.root / ".claude").mkdir()
        self.log = self.root / ".claude" / "evidence-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_w2a1_washed_ok_cannot_certify_green(self):
        # W2a-1（differential: pre-fix green）: `; true` は exit 0 を偽造
        # する。出力の `1 failed` サマリで marker=true（fixture 既定）でも
        # 複合 cmd の ok は信用できない → 他に entry が無ければ unverified。
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("python3 -m pytest -q; true", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_w2a2_washed_ok_is_transparent_older_clean_green_decides(self):
        # W2a-2（意味論 pin）: washed-ok は trust-scan の undecidable-ok と
        # 同じ TRANSPARENT — 同一 fp のより古い clean green は生きる。
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("python3 -m pytest -q", "ok", fp)
            + _ev_line("python3 -m pytest -q | tee log.txt", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_w2a3_washed_fail_stays_red(self):
        # W2a-3（非退行 pin）: 洗浄形でも fail した run は本物の失敗信号
        # — red を🟡へ降格させない（fail-visible 維持）。
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("python3 -m pytest -q && echo ok", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_w2a4_quoted_operator_is_not_washed(self):
        # W2a-4（誤検知防止 pin）: クォート内演算子は strips マスクで不活性
        # （`pytest -k "a or b|c"` は clean 単一コマンド）。
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line('python3 -m pytest -k "a or b|c"', "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_w2a5_multiline_cmd_is_washed(self):
        # W2a-5（differential: pre-fix green）: 改行はコマンド区切り
        # （`;` 正規化）＝複合コマンドとして扱う。
        fp = judge.current_fingerprint(self.root)
        self.log.write_text(
            _ev_line("python3 -m pytest -q\ntrue", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_w3_1_unknown_src_is_terminal_unverified(self):
        # W3-1（differential: pre-fix green）: allowlist 外 src は
        # decidable-by-default に落ちず終端🟡。
        fp = judge.current_fingerprint(self.root)
        row = json.loads(_ev_line("pytest", "ok", fp))
        row["src"] = "forged"
        self.log.write_text(json.dumps(row) + "\n")
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_w3_2_unknown_src_terminal_blocks_older_green(self):
        # W3-2（differential: pre-fix green）: TERMINAL＝走査停止。偽 src
        # の背後の古い clean green へ透過して green 化してはならない。
        fp = judge.current_fingerprint(self.root)
        row = json.loads(_ev_line("pytest", "ok", fp))
        row["src"] = "forged"
        self.log.write_text(
            _ev_line("python3 -m pytest -q", "ok", fp)
            + json.dumps(row) + "\n")
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_w3_3_missing_src_is_terminal_unverified(self):
        # W3-3（differential: pre-fix green）: src キー欠如も同じ偽造クラス。
        fp = judge.current_fingerprint(self.root)
        row = json.loads(_ev_line("pytest", "ok", fp))
        del row["src"]
        self.log.write_text(json.dumps(row) + "\n")
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_helper_cmd_has_shell_operators(self):
        # ヘルパー単体（grill 要検討1）: e2e（W2a-1/4）が fail した時の
        # 切り分け用。strips は実 patterns.sh からロードした本物を使う。
        strips = judge._tr_strip_patterns(ROOT_DIR)
        self.assertEqual(len(strips), 2)
        self.assertTrue(judge._cmd_has_shell_operators(
            "python3 -m pytest -q; true", strips))
        self.assertTrue(judge._cmd_has_shell_operators(
            "python3 -m pytest -q\ntrue", strips))
        self.assertFalse(judge._cmd_has_shell_operators(
            'python3 -m pytest -k "a or b|c"', strips))
        self.assertFalse(judge._cmd_has_shell_operators(
            "python3 -m pytest -q", strips))
```

- [ ] **Step 1-4: RED 分布を実測**

Run: `python3 -m pytest -q tests/test_hook_locale_byte.py tests/test_marker_lib.py tests/test_judge_card.py`
Expected: **11 failed**（RS1・RS2／W2b-1・W2b-4・W2b-5／W2a-1・W2a-5／W3-1・W3-2・W3-3／helper 単体〔`_cmd_has_shell_operators` 未定義＝AttributeError〕）**/ 7 passed（新規分）**＋既存分は全 passed。
※ RS1/RS2 の fail は decision=="CRASH"（rc1・stdout 空）による。W2b-5 の fail は regex 行が未存在＝re.sub 無置換＝verdict rc0 による。

- [ ] **Step 1-5: コミット**

```bash
git add tests/test_hook_locale_byte.py tests/test_marker_lib.py tests/test_judge_card.py
git commit -m "test(iter76): RED — SF-018 crash pin＋washed-green/src allowlist の differential pin（10 RED/7 PASS 実測）"
```

### Task 2: W1 — check-runtime-state.sh の C locale 化（SF-018）

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `hooks/check-runtime-state.sh:47` 直後 / テスト `tests/test_hook_locale_byte.py`（Task 1 済）
**意図:** iter73 の destructive/secrets と同型の byte-safety を 3 本目（最後の stdin 消費静的 hook）に適用し locale 掃討を完了する。
**TDD:** Task 1 の RS1/RS2 が RED → 本修正 → GREEN
**受入条件:** RS1-RS4 全 green・既存 runtime-state テスト非退行。

- [ ] **Step 2-1: `INPUT=$(cat)`（:47）の直後に挿入**

```bash
# Byte-safety (iter76 SF-018): CMD below is arbitrary tool_input; under a
# UTF-8 locale one invalid byte crashes `tr` ("Illegal byte sequence") and
# `set -e` exits rc=1 with NO decision emitted = fail-open on the ONLY
# non-framework runtime-state guard. C locale processes byte-wise; every
# pattern in this hook is ASCII so matching is unchanged, and the python3
# extraction keeps UTF-8 fidelity under C (PEP 540). Mirrors
# check-destructive.sh / check-secrets.sh (iter73) — locale sweep complete.
export LC_ALL=C LC_CTYPE=C LANG=C
```

- [ ] **Step 2-2: GREEN 確認**

Run: `python3 -m pytest -q tests/test_hook_locale_byte.py`
Expected: 全 passed（RS1-RS4 含む）。

- [ ] **Step 2-3: 周辺非退行**（grill 致命2: `-k "runtime-state"` は式構文エラーになるため使用禁止・実在ファイルを明示実行）

Run: `python3 -m pytest -q tests/test_runtime_state_hook.py tests/test_hook_locale_byte.py`
Expected: 全 passed（check-runtime-state の既存回帰＋RS1-4 が green）。

- [ ] **Step 2-4: コミット**

```bash
git add hooks/check-runtime-state.sh
git commit -m "fix(iter76): SF-018 — check-runtime-state.sh を LC_ALL=C で byte-wise 化（tr crash fail-open 封鎖・locale 掃討完了）"
```

### Task 3: W2b — marker.sh Stage 6「green 矛盾 veto」（SF-012(a)）

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `hooks/lib/patterns.sh`（COUNT_FAMILIES 直後）・`hooks/lib/marker.sh`（rc3 ガード＋:253 `printf 'true'` 直前）/ テスト `tests/test_marker_lib.py`
**意図:** 「exit=0 なのに出力に非ゼロ failure 証拠」＝洗浄/偽造 run を marker 段で false 化。3 消費者（evidence.sh/record/drill）に自動波及。
**TDD:** W2b-1/4/5 RED → 実装 → GREEN。**既存 1 件の意図された flip あり（Step 3-3）**。
**受入条件:** W2b-1〜5 green・`test_unittest_failed_with_skips_true` を正直な exit へ修正・marker/zero-run 既存テスト green。

- [ ] **Step 3-1: `hooks/lib/patterns.sh` の `AEGIS_TEST_COUNT_FAMILIES=(...)` 配列クローズ直後に追加**

```bash
# iter76 SF-012(a): positive FAILURE-evidence tokens, consumed by marker.sh
# Stage 6 (green-contradiction veto): exit_code 0 + any of these in the
# output => the exit was laundered (`pytest -q; true` / `|| true` / `| tee`)
# or the output forged — the run cannot certify green. NONZERO counts only
# (cargo prints `0 failed` on every green run). unittest has no count token
# in its Ran-line, so its FAILED banner is matched directly; go/jest/vitest
# print FAIL-prefixed lines. Incidental FAIL-looking text inside a green
# run's captured body flips true->false only (fail-closed; same accepted
# class as the count-family M-2 residual). ERE∩python-re subset per header;
# in line-oriented grep -E the `\n` alternative degrades to a literal `n`
# (same accepted harmless over-match as the count-family patterns above).
AEGIS_TEST_FAIL_TOKEN_REGEX='(^|[^0-9A-Za-z_])[1-9][0-9]* failed|FAILED \((failures|errors)=|(^|\n)--- FAIL:|(^|\n)FAIL[[:space:]]'
```

- [ ] **Step 3-2: `hooks/lib/marker.sh` を 2 箇所編集**

(a) rc3 ガード（`aegis_marker_verdict` 冒頭）に 1 行追加し、ヘッダコメントの「ALL SEVEN」を「ALL EIGHT」へ更新:

```bash
     [ -z "${AEGIS_TEST_IS_PYTEST_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_FAIL_TOKEN_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_COUNT_FAMILIES[*]:-}" ]; then
```

(b) 関数末尾の `printf 'true'` 直前（Stage 5 ループの後）に挿入:

```bash
  # Stage 6 (iter76 SF-012a): green-contradiction veto. POSITIVE failure
  # evidence in the output while the reported exit code is 0 means the
  # exit was laundered (`pytest -q; true` / `|| true` / `| tee`) or the
  # output forged — either way this run cannot prove green. Real red runs
  # (exit != 0) skip the axis so the caller's red signal survives; empty
  # exit_code (an observer payload without exitCode) skips too — the
  # judge-side washed-cmd check (build-judge-card.py) covers that path.
  if [ "$exit_code" = "0" ] && \
     printf '%s' "$out" | grep -aqE "$AEGIS_TEST_FAIL_TOKEN_REGEX"; then
    printf 'false'
    return 0
  fi
```

- [ ] **Step 3-3: 既存テストの意図された flip を修正** — `tests/test_marker_lib.py::test_unittest_failed_with_skips_true`（:249 付近）は exit_code **"0"** で FAILED 出力に true を期待している。これは washed-green 穴そのものの pin（実 unittest の失敗は exit 1）。exit を正直な `"1"` に変更し、コメントを追記:

```python
    def test_unittest_failed_with_skips_true(self):
        # Red-run verdict (the verdict proves "tests ran", not "green"):
        # Ran(5) - skipped(2) = 3 bodies executed -> true. iter76 Stage 6:
        # exit must be the HONEST nonzero of a failing unittest run — the
        # old exit "0" here encoded the washed-green hole itself (a FAILED
        # banner with exit 0 is now the Stage-6 contradiction -> false,
        # pinned by TestGreenContradictionVeto).
        out = ("Ran 5 tests in 0.010s\n\nFAILED (failures=1, skipped=2)\n")
        rc, verdict = _verdict(out, "python3 -m unittest t", "1")
        self.assertEqual((rc, verdict), (0, "true"))
```

- [ ] **Step 3-4: GREEN 確認**

Run: `python3 -m pytest -q tests/test_marker_lib.py tests/test_test_marker_zero_run.py tests/test_evidence_lib.py tests/test_evidence_hooks.py`
Expected: 全 passed（W2b-1〜5 GREEN 化・既存 flip は Step 3-3 で解消済み・他は不変）。

- [ ] **Step 3-5: コミット**

```bash
git add hooks/lib/patterns.sh hooks/lib/marker.sh tests/test_marker_lib.py
git commit -m "fix(iter76): SF-012(a) — marker Stage 6 green 矛盾 veto（exit0×非ゼロ failed→false・rc3 ガード 8 ソース化）"
```

### Task 4: W2a＋W3 — judge の washed-cmd transparent＋src allowlist

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `scripts/build-judge-card.py`（`_norm_cmd_match` :170 直後＋`read_test_result_detail` 走査 :283 付近）/ テスト `tests/test_judge_card.py`
**意図:** reader（信頼判定の単一権威）で (a) 複合コマンド observed-ok の green 認定を遮断（transparent）・(b) 未知 src を終端🟡化。
**TDD:** W2a-1/5・W3-1/2/3 RED → 実装 → GREEN
**受入条件:** 新規 8 テスト green・trust-scan/manual/observed 既存テスト非退行・`test_judge_card_push.py` green。

- [ ] **Step 4-1: `_norm_cmd_match` の直後にヘルパー追加**

```python
_SHELL_OP_RE = re.compile(r"[;&|]")


def _cmd_has_shell_operators(cmd: str, strips: list) -> bool:
    """True when an observed command carries an UNQUOTED shell control
    operator (; & | — newlines count: normalized to ';'). A compound
    command's exit code belongs to the LAST list member, not the runner
    (`pytest -q; true` exits 0 with failing tests), so an observed entry's
    exit-derived status cannot certify green (SF-012a washed-green).
    Quoted spans are masked to the inert token Q first — the SAME strips
    pipeline as _norm_cmd_match, so `pytest -k "a|b"` stays clean."""
    cmd = (cmd or "").replace("\n", ";")
    for sp in strips:
        cmd = sp.sub("Q", cmd)
    return bool(_SHELL_OP_RE.search(cmd))
```

- [ ] **Step 4-2: `read_test_result_detail` の走査ループに 2 チェック挿入** — `if not _norm_cmd_match(...)` の `continue` と `undecidable = ...` の間:

```python
        # SF-012(b) (iter76): src allowlist — the only real writers are
        # record-test-result.py (src:"manual") and evidence.sh
        # (src:"observed"). Any other/missing src is a hand-written or
        # unknown-writer entry this scan cannot certify — TERMINAL
        # 'unverified' (fail-visible), never decidable-by-default and never
        # skipped-over. A future legitimate src (e.g. "attested", iter77)
        # must be added HERE in the same change that introduces its writer.
        if d.get("src") not in ("manual", "observed"):
            return unverified
        # SF-012(a) (iter76): washed-green — an observed 'ok' whose cmd
        # chains shell operators has an exit code the runner did not
        # produce (`pytest -q; true`). It can certify nothing: TRANSPARENT
        # like undecidable-ok noise (skip; an older clean decidable entry
        # for the SAME fingerprint may still decide). An observed 'fail'
        # with such a cmd stays decidable red — a wash that still failed
        # is a real failure signal (fail-closed keeps it visible).
        if (d.get("src") == "observed" and d.get("status") == "ok"
                and _cmd_has_shell_operators(d.get("cmd"), strips)):
            continue
```

- [ ] **Step 4-3: `read_test_result_detail` の docstring に意味論を追記**（undecidable 段落の直後）:

```
    iter76 (SF-012) adds two hardenings to this scan: (b) a src ALLOWLIST —
    src outside {"manual","observed"} is TERMINAL 'unverified' (a forged or
    unknown-writer entry can neither certify green nor be skipped over);
    (a) WASHED-GREEN — an observed 'ok' whose cmd carries an unquoted shell
    operator (; & |, newlines normalized to ';') is TRANSPARENT (its
    exit-derived status is untrustworthy: `pytest -q; true`), while an
    observed 'fail' with such a cmd stays decidable red.
    Migration note: a legacy entry MISSING the src key hits the allowlist
    terminus (unverified) — fail-visible; re-run the tests to upgrade the
    log (same story as the v1.6.0 marker_verified schema note above).
```

- [ ] **Step 4-4: GREEN 確認**

Run: `python3 -m pytest -q tests/test_judge_card.py tests/test_judge_card_push.py`
Expected: 全 passed（W2a-1〜5・W3-1〜3 GREEN 化・既存 trust-scan 群不変）。

- [ ] **Step 4-5: コミット**

```bash
git add scripts/build-judge-card.py
git commit -m "fix(iter76): SF-012 — judge に washed-cmd transparent（observed-ok 複合コマンド）＋src allowlist（未知 src 終端🟡）"
```

### Task 5: 設計正本の訂正＋full suite green 記録

**blockedBy:** Task 2, 3, 4 | **モデル:** `opus`（文書編集）＋検証は session
**ファイル:** `docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md`（末尾 append）・`docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md`・`docs/specs/2026-07-22-iter76-evidence-integrity-locale-brainstorm-record.md`
**意図:** roadmap 完了条件「設計正本訂正」の充足＋iter76 設計の「新規 regex ゼロ」主張を実装実態（fail-token 1 本追加）へ正確化。
**受入条件:** 訂正が dated 追記（silent rewrite でない）・full suite green・record-test-result で green 記録・contract PASS。

- [ ] **Step 5-1: iter73 設計正本の末尾に追記**

```markdown
## 訂正（2026-07-22・iter76 SF-018）

本設計の「check-runtime-state.sh は python3 抽出が不正バイトで空 CMD になる
ため同型（tr crash→fail-open）は不成立」という完全性主張は**誤り**（iter74
二重レビュー Fable 盲検2次が反証・親実走確認＝SF-018）。CPython は
surrogateescape で不正バイトを温存して CMD に流し、`tr '\n\r' ';;'` が UTF-8
locale 下で crash する（rc=1・decision 未出力＝fail-open）。iter76 で
`INPUT=$(cat)` 直後の `export LC_ALL=C LC_CTYPE=C LANG=C` により本 hook にも
同型修正を適用し locale 掃討を完了した。回帰 pin＝
`tests/test_hook_locale_byte.py::TestRuntimeStateByteSafety`。
```

- [ ] **Step 5-2: iter76 設計/記録の「新規 regex ゼロ」記述を正確化** — design.md「推奨アプローチ > 採用理由」の「新規 regex ゼロ」を「新規 pattern は fail-token 整合軸 1 本のみ（`AEGIS_TEST_FAIL_TOKEN_REGEX`・SF-012(a) 記載の修正方向。count families は unittest の failed を抽出できないため）」へ、brainstorm-record「やらないこと」の同記述に同旨の追記。理由: 計画時精査で count families の EXEC（passed+failed 混合和）から failed 単独を分離できないと判明（roadmap 原則の「regex を足さない」は moat denylist の増殖防止であり、本件は evidence 整合軸＝SF-012(a) が自ら規定する修正）。

- [ ] **Step 5-3: full suite＋契約検証＋green 記録**

```bash
python3 -m pytest -q                                   # 全件 green を確認
python3 scripts/check_framework_contract.py            # PASS を確認
python3 scripts/record-test-result.py "python3 -m pytest -q"   # trusted green 記録
```
Expected: full suite passed（既知 skip 2 件のみ）・contract PASS・record green。
※ record は「全コード確定後」に置く（LEARNINGS: ref-window/newest-entry 規律）。

- [ ] **Step 5-4: コミット**

```bash
git add docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md docs/specs/2026-07-22-iter76-evidence-integrity-locale-brainstorm-record.md
git commit -m "docs(iter76): iter73 設計の完全性主張を訂正（SF-018）＋iter76 設計の fail-token regex 記述を正確化"
```

## 事前準備

- [ ] tree clean・main 最新（HEAD=4519453 以降）
- [ ] baseline: `python3 -m pytest -q` 全 green（1367 passed/2 skipped 目安）を実測してから Task 1 に入る
- [ ] 外部依存なし（bash/python3 標準のみ）

## トレーサビリティ（完了条件 → Task → Test）

| 完了条件（roadmap §5 iter76） | Task | テスト |
|---|---|---|
| `pytest; true` が green 不可 | 3, 4 | W2b-1・W2a-1 |
| `\|\| echo`/`\| tee` 洗浄が green 不可 | 4 | W2a-2（tee は transparent）・W2a-5 |
| fake-output（複合形）が green 不可 | 3, 4 | W2b-4・W2a-1（`\|\|` 形は演算子検出で同経路） |
| unknown-src が green 不可（SF-012(b)） | 4 | W3-1・W3-2・W3-3 |
| runtime-state byte crash 消滅（SF-018） | 2 | RS1・RS2（＋RS3/RS4 非退行） |
| 設計正本訂正 | 5 | n/a（文書・Step 5-1） |
| 「旧赤/新緑」差分 pin | 1 | RED 10 件の実測分布（Step 1-4） |
| red 非降格・green 非退行 | 3, 4 | W2b-2/3・W2a-3/4・既存 green/red pin 群 |

## 自己レビュー

- 仕様カバレッジ: 設計の W1/W2a/W2b/W3 全てに Task と test がある（上表）。
- 曖昧さ: 「washed の fail は red 維持」「未知 src は終端・washed-ok は透明」の非対称は W2a-2/3・W3-2 で挙動 pin 済み＝二義なし。
- 整合性: `_cmd_has_shell_operators` は `_norm_cmd_match` と同一の正規化（改行→`;`・strips マスク）を再実装でなく同型で共有（レビューで byte-parity 確認）。
- 既知の意図された flip: `test_unittest_failed_with_skips_true`（Task 3 Step 3-3）のみ。他の既存テストに exit=0×非ゼロ failed の組合せは無い（grep 実測済み: `0 failed` 形のみ）。

## リスク

- **fail-token の誤発火**（green run の本文出力に `--- FAIL:` 等が混じる）→ true→false（fail-closed）方向のみ・count-family M-2 と同じ受容クラス。cargo `0 failed` のホットケースは W2b-3 で pin。
- **`(^|\n)` の ERE 解釈**（grep -E では `\n`＝リテラル n）→ 既存 family と同型の受容済み over-match（無害方向）。
- **red→🟡 降格の混入** → 設計で回避（W2a は status=ok のみ・Stage 6 は exit=0 のみ）。W2a-3/W2b-2 が pin。
- **観測エントリの exitCode 欠落**（ec=""）→ Stage 6 は発火しない（過剰 false 回避）。washed 形は W2a が reader 側で被覆。単一コマンドで exitCode 欠落×矛盾出力の残余は iter77 attestation の天井に含める。
- **残余（既知天井）**: 単一コマンド fake binary（`./pytest`・PATH hijack）は本 iter の射程外＝SF-014/iter77 attestation。qa フェーズで residual を明示（必要なら test_residual_* pin を qa 時に追加判断）。

## 完了条件

- [ ] 全テスト pass（full suite・contract）
- [ ] Task 1 の RED 分布実測が記録されている（differential 証明）
- [ ] review（1次＋盲検2次）→ qa（B1 drill or sanctioned skip＋fresh 変異）→ security の各ゲート
- [ ] `record-test-result.py` の green が newest（Step 5-3）
- [ ] **qa 引き継ぎ（grill 要検討2）**: observer payload 経路の縦串 E2E（`pytest -q; true` の hook payload → `_check_test_marker`＝marker_verified false 記録）を qa フェーズで実測する（`tests/test_test_marker_zero_run.py` の `_check` ヘルパー再利用可・marker 単体 W2b と judge reader W2a の間の結線確認）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->
