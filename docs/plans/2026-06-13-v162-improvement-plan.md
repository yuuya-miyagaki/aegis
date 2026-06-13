# v1.6.2 改善計画書（第6回全力レビュー fix-forward）

- 起点レポート: `docs/full-review-2026-06-13.md`（charter `full-review-charter-2026-06-13.md`）
- 対象: v1.6.1 → v1.6.2
- 起点 HEAD: `2ac5eb6`
- 期間目安: 1 週間（タスク 7 本）
- 哲学: TDD で**先に PoC を deny に倒すテスト**を書き、grill-plan / grill-code を 2 段運用
- 改訂履歴:
  - v1（2026-06-13）初版
  - v2（2026-06-13）grill-plan 反映: 致命 5 件（K-1 exit_code 経路 / safety.sh REQUIRED 登録 / mirror 同期義務 / 明示マッピング辞書 / fallback identity 契約）＋要検討 5 件＋YAGNI 3 件を消化

## 0. ゴール

第6回レビュー Critical 16 件のうち、**v1.6.2 マージ前必須の 13 件（K-1〜K-13）** を消化する。残る K-14（PERF-1）と K-15（PERF-2）と K-16（README/setup 導線）は v1.7 で構造強化。

各 Task は次を満たして完了：

1. **PoC が deny に倒れる**（Phase A REDTEAM-NN を流用した攻撃テストが赤→緑）
2. **既存テスト 508 件すべて green**（回帰ゼロ）
3. **drift / contract / smoke すべて PASS**
4. **judge card に「テスト緑」が偽装できないことを再 PoC で確認**

## 0.1 ミラー同期義務

aegis は `examples/minimal-project/.claude/` / `hooks/` / `templates/` を **byte-identical mirror** として保持し、`scripts/check_reference_drift.py:MIRROR_DIRS` で常時検査する。本計画は次のソースを編集する：

- `hooks/check-control-plane.sh` / `check-secrets.sh`（Task 2）
- 新規 `hooks/lib/safety.sh`（Task 3）
- 全 deny 系 hook 冒頭の safety 取込み（Task 3）
- `hooks/lib/patterns.sh` の AEGIS_TEST_ZERO_RUN_REGEX 追加（Task 1）
- `templates/hooks.template.json` の timeout フィールド（Task 3）
- `templates/profiles/{minimal,standard,full}.json` の required / recommended（Task 3 / Task 6）

**ルール**:

- 上記のいずれかを改変する Task は、**同一コミット内**で `examples/minimal-project/<対応 path>` を同期する
- 各 Task の受入条件には **`python3 scripts/check_reference_drift.py --strict` PASS** を含む
- 未同期コミットは grill-code で reject

## 1. タスク依存グラフ

```
Task 1 (K-1)  ─┐
                ├─→ Task 3 (K-5/6/7 safety.sh 集約) ─→ Task 6 (K-12) ─→ Task 7 (K-13)
Task 2 (K-2/3/4)┘                                  ↑
                                                   │
Task 4 (K-8/9/11) ─→ Task 5 (K-10) ────────────────┘
```

- **Task 1〜2** は機械側の moat 補強（独立、並行実行可だが TDD 集中力のため直列）
- **Task 3** は Task 1/2 で見えた共通パターン（fail-closed 系）を `hooks/lib/safety.sh` に集約。Task 1/2 完了後でないと API 形状が決まらない
- **Task 4〜5** は配布パスの破壊抑止（独立、setup.sh の編集集中のため直列）
- **Task 6** は K-12（テンプレ配布の対称化）。Task 3 の REQUIRED 追加と同じ profile JSON を触るため Task 3 後
- **Task 7** は docs のみ（K-13 cheatsheet）

## 2. 全タスク完了後の検証

- 第6回 Phase A の REDTEAM-01〜06 すべて deny／ASK に倒れる
- `pytest -v` が 508 + 新規テストで全 green
- `python3 scripts/check_reference_drift.py --strict` PASS
- `python3 scripts/check_framework_contract.py --profile=full --strict` PASS
- `python3 scripts/eval_scaffold_smoke.py` PASS
- 新規シナリオ: `lib 欠落 → hook が明示 DENY`、`hook timeout → 明示 DENY`、`snapshot 部分破損 → fail-closed`

### 2.1 PoC rerun harness の所有

`tests/poc/v162-redteam-rerun.sh` を新設する（**所有: Task 3 末尾**）。中身は REDTEAM-01〜06 / F-01〜03 / DIST-01〜04 を一括再走する bash スクリプト。Task 3 が完了した時点で初版を作成し、Task 4〜7 完了ごとに該当 PoC を有効化する。最終 grill-code 前に全件 PASS を確認。

### 2.2 hook timeout の数値根拠（perf-baseline）

Task 3 で hook ごとに timeout 値を settings に書き込む前に、`docs/perf-baseline.md` を新設して**実測ベースの数値**を残す。手順：

1. クリーン install scaffold を `/tmp/aegis-perf/` に作成
2. 代表 hook（control-plane / secrets / destructive / gate / task-* / post-bash-observe / post-bash）を各 50 回 `time` 計測（JSON 入力は実コマンドの代表 3 種）
3. **90 パーセンタイル × 安全係数 5** を timeout 値として採用。下限 5s、上限 60s
4. `check-secrets.sh` は `find $ROOT -name '.env*'` を回すため、大規模 monorepo（10 万 file 想定）の baseline を別途取り、上限を 30〜60s で個別設定
5. 数値と計測条件を `perf-baseline.md` に表形式で記録（将来の hook 追加時に同手順で更新）

---

## Task 1: K-1 — test-marker forge を 3 経路の独立判定で塞ぐ

### 攻撃 PoC（REDTEAM-01 + grill 派生）

基本 PoC（REDTEAM-01）:

```bash
echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__
# 期待: judge card に「テスト: green」が刻まれてはならない
```

grill で派生した強化 PoC（フィルタ／プロローグ欠落）:

```bash
# G-1: 出力フィルタで zero-run シグナルを削除
echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__ -q 2>&1 | grep -v 'collected\|no tests'
# G-2: stderr 抑制で zero-run シグナルを隠す
echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__ 2>/dev/null
# G-3: pytest プロローグ（platform / rootdir）を伴わない pure echo
echo "===== 3 passed in 0.42s ====="
# G-4: fast-fail で 0 件
pytest --lf
# G-5: ノーマル偽装
echo "OK"; echo "Ran 0 tests in 0.001s"
```

### 仮説

**「runner が走った」と「テストが本当に走った」は別概念**。攻撃側は (a) コマンド (b) 出力 (c) 終了コード のいずれにも介入できるので、**単一軸で守ると必ず迂回される**。3 つの独立判定軸の OR で false 化する。

| 軸 | シグナル | 攻撃側の介入難度 |
| --- | --- | --- |
| 軸 1: 出力 | `collected 0 items` / `Ran 0 tests` / `No tests` / `0 passed` | 中（フィルタで削除可） |
| 軸 2: exit_code | pytest 5 (no tests collected) / unittest 0+`Ran 0` | **高**（外殻 wrapper を通さない限り runner の native exit が出る） |
| 軸 3: プロローグ欠落 | pytest なら `platform .* rootdir:` の冒頭プロローグ。strong marker のみで先頭プロローグが無い→echo 由来疑い | 中（forge 可能だが量が増える） |

3 軸いずれかが zero-run シグナルを出せば `marker_verified=false`。

### 修正対象

- `hooks/lib/patterns.sh:131-134` — 新規配列 `AEGIS_TEST_ZERO_RUN_REGEX`（軸 1）と `AEGIS_TEST_PROLOGUE_REGEX`（軸 3 用）を追加
- `hooks/lib/evidence.sh:50-117` `_check_test_marker` — strong マーカー一致後に 3 軸検査で false 降格
- `hooks/lib/evidence.sh` — `tool_response.exit_code` を JSON から取り出して 軸 2 に渡す
- `scripts/build-judge-card.py:read_test_result` — bash と同じ 3 軸ロジックを python 側にも

### TDD 失敗テスト雛形（先に書く）

新規 `tests/test_test_marker_zero_run.py`:

```python
# 軸 1: 出力検査
def test_strong_marker_with_zero_run_output_is_not_verified():
    """pytest が collected 0 items を出すと strong marker でも false"""
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": 'echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__'},
        "tool_response": {
            "output": "===== 3 passed in 0.42s =====\ncollected 0 items\n",
            "exit_code": 5,
        },
    }
    assert check_test_marker(input_json) == "false"

def test_unittest_ok_with_ran_zero_tests_is_not_verified():
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": "python3 -m unittest"},
        "tool_response": {"output": "Ran 0 tests in 0.001s\nOK\n", "exit_code": 0},
    }
    assert check_test_marker(input_json) == "false"

def test_cargo_test_zero_passed_is_not_verified():
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": "cargo test"},
        "tool_response": {
            "output": "running 0 tests\ntest result: ok. 0 passed; 0 failed; 0 ignored\n",
            "exit_code": 0,
        },
    }
    assert check_test_marker(input_json) == "false"

# 軸 2: exit_code 検査（grill 派生 G-1 / G-2 対応）
def test_pytest_exit_5_implies_not_verified_even_if_output_filtered():
    """G-1/G-2 想定: 攻撃側が `2>/dev/null` や `| grep -v` で
    zero-run の出力シグナルを削除しても、pytest の exit 5 が残れば false"""
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": 'echo "===== 3 passed ====="; pytest -k __NEVER__ 2>/dev/null'},
        "tool_response": {
            "output": "===== 3 passed in 0.42s =====\n",  # フィルタ後の出力
            "exit_code": 5,
        },
    }
    assert check_test_marker(input_json) == "false"

def test_unittest_exit_nonzero_with_strong_marker_is_verified():
    """回帰: unittest が失敗時 (exit=1) でも strong marker があれば
    「テスト走ったが失敗」として verified（失敗は失敗で検出される）"""
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": "python3 -m unittest"},
        "tool_response": {"output": "===== 1 failed in 0.1s =====\n", "exit_code": 1},
    }
    assert check_test_marker(input_json) == "true"

# 軸 3: プロローグ欠落
def test_pytest_strong_marker_without_prologue_is_not_verified():
    """G-3 想定: `echo "===== 3 passed ====="` のみで pytest コマンドを
    一切走らせない場合、プロローグ（platform / rootdir）が出ないので false"""
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": 'echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__'},
        "tool_response": {
            "output": "===== 3 passed in 0.42s =====\n",
            "exit_code": 0,  # echo の exit
        },
    }
    assert check_test_marker(input_json) == "false"

# 回帰
def test_normal_three_passed_still_verified():
    """回帰: 通常の 3 件パスは引き続き true。プロローグあり、exit_code 0、出力に zero-run なし"""
    input_json = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "tool_response": {
            "output": (
                "platform darwin -- Python 3.11.5, pytest-7.4.3\n"
                "rootdir: /home/user/proj\n"
                "collected 3 items\n\n"
                "tests/test_x.py ...\n\n"
                "===== 3 passed in 0.42s =====\n"
            ),
            "exit_code": 0,
        },
    }
    assert check_test_marker(input_json) == "true"
```

`build-judge-card.py` 側にも parity test（既存 `test_patterns_parity.py` に zero-run / exit_code / プロローグ fixture を追加し、bash / python の挙動が一致することを契約）。

### 実装方針

`patterns.sh` に追加：

```bash
# 軸 1: 出力検査
AEGIS_TEST_ZERO_RUN_REGEX=(
  '(^|\n)collected 0 items'
  '(^|\n)Ran 0 tests'
  '(^|\n)No tests (found|ran)'
  '(^|\n)test result: (ok|FAILED)\. 0 passed'
  '(^|\n)Tests:[ \t]+0 passed'
  '(^|\n)Test Files[ \t]+0 passed'
  '(^|\n)0 passing'
  '(^|\n)no tests ran'
)

# 軸 3: runner ごとの「テストが本当に走った時に出るプロローグ」
# pytest なら "platform" / "rootdir" / "collected N items"
# unittest なら "test_xxx (module.Class) ... ok|FAIL" の test_id 行
# cargo なら "running N tests" を伴う
# 「strong marker は出ているがプロローグが完全に欠落」のときは echo 由来疑い
AEGIS_TEST_PROLOGUE_REGEX=(
  '(^|\n)platform [A-Za-z0-9]+ -- Python'   # pytest
  '(^|\n)rootdir: '                          # pytest
  '(^|\n)collected [0-9]+ items?'            # pytest
  '(^|\n)test_[A-Za-z0-9_]+ \([A-Za-z0-9_.]+\)' # unittest
  '(^|\n)running [0-9]+ tests?'              # cargo
  '(^|\n)Test Files [0-9]+ (passed|failed)'  # vitest
)

# 軸 2: runner 別の zero-run exit code（runner regex で識別済みの場合のみ参照）
# pytest exit 5 = no tests collected
# 他 runner は exit code のみでは判別不能（軸 1/3 に委ねる）
AEGIS_TEST_ZERO_RUN_EXIT_PYTEST=5
```

`evidence.sh` の `_check_test_marker` で strong/weak マッチ後、以下のいずれかで `printf 'false\n'; return`：

1. output が `AEGIS_TEST_ZERO_RUN_REGEX` のいずれかにマッチ（軸 1）
2. command が pytest 系 AND exit_code が `AEGIS_TEST_ZERO_RUN_EXIT_PYTEST`（軸 2）
3. command が pytest 系 AND output が `AEGIS_TEST_PROLOGUE_REGEX` のいずれにもマッチしない（軸 3）

軸 3 は他 runner には適用しない（プロローグ無しでも合法なケースが多いため）。**v1.7 で他 runner にも拡張検討**。

### 受入条件

- 上記 7 テストが green
- 既存 `test_evidence_lib.py` / `test_patterns_parity.py` 全 green
- REDTEAM-01 と grill 派生 G-1〜G-5 を `/tmp/aegis-v162-K1-poc/` で再実行し judge card が 🟡 or deny になる
- `python3 scripts/check_reference_drift.py --strict` PASS（patterns.sh の mirror 同期）

---

## Task 2: K-2 / K-3 / K-4 — cmdsub と quoted-var を fail-closed

### 攻撃 PoC（REDTEAM-02 / 03 / 04）

```bash
# K-2: control-plane 純コマンド置換
> "$(echo hooks)/lib/emit.sh"
# K-2: printf -v 経路
printf -v D %s hooks; > $D/lib/emit.sh
# K-2: eval 経路
eval "D=hooks"; > $D/lib/emit.sh
# K-3: secrets quoted var
F=.env; git add "${F}"
# K-4: cmdsub-built git
$(echo git) add .env
```

すべて現状 allow。期待は ASK（K-2）/ ASK（K-3）/ ASK or DENY（K-4）。

### 仮説

- **K-2**: `cmd_var_built_write` は assignment + variable use + write op を要求するが、純コマンド置換は assignment が無い。**「最初の write redirect の write-target に `$(...)` か backtick がある」を 4 番目の独立条件として ASK**。「最初の write redirect の target token のみ」に限定するのは grill 要検討 1 の over-greedy 対策。同時に `printf -v` / `read` / `eval` / `declare` / `local` を assignment 検出に追加
- **K-3**: 既存の var-built git stage 検出 regex は `[^.[:space:]]+[[:space:]]+` の前提でクォート開始 `"` を吸えない。**クォート任意化**で吸う
- **K-4**: 既存の git 検出は全て `git[[:space:]]+...` でリテラル `git` 前提。**`cmd` がコマンド置換 / backtick を含み、かつ word-boundary 付き `.env` または高リスク認証ファイル名を含めば ASK**。safe variant（`.env.example` 等）は事前に strip して false-positive を抑える

### 修正対象

- `hooks/check-control-plane.sh:86-106` `cmd_var_built_write` — 4 番目の条件（write-target 限定の cmdsub 検出）と assignment 検出拡張
- `hooks/check-secrets.sh:149-153` — クォート任意化
- `hooks/check-secrets.sh` 末尾に新規ブロック — cmdsub + word-boundary `.env`/高リスク → ASK（safe-variant 事前 strip 込み）

### TDD 失敗テスト雛形

既存 `tests/test_control_plane_var_expansion.py` に追記:

```python
def test_pure_command_substitution_in_write_target_is_ask():
    cmd = '> "$(echo hooks)/lib/emit.sh"'
    assert run_hook(cmd) == "ask"

def test_backtick_in_write_target_is_ask():
    cmd = '> `echo hooks`/lib/emit.sh'
    assert run_hook(cmd) == "ask"

def test_printf_dash_v_assignment_is_ask():
    cmd = 'printf -v D %s hooks; > $D/lib/emit.sh'
    assert run_hook(cmd) == "ask"

def test_read_assignment_is_ask():
    cmd = 'read D <<<hooks; > $D/lib/emit.sh'
    assert run_hook(cmd) == "ask"

def test_eval_assignment_is_ask():
    cmd = 'eval "D=hooks"; > $D/lib/emit.sh'
    assert run_hook(cmd) == "ask"
```

既存 `tests/test_control_plane_var_expansion.py` に false-positive 抑止テスト追加（grill 要検討 1）：

```python
def test_unrelated_cmdsub_after_chain_does_not_trigger():
    """`a > /tmp/out ; cat $(find . -name '*.log')` の cmdsub は
    write target ではないので ASK にならない"""
    cmd = 'echo a > /tmp/out ; cat $(find . -name "*.log")'
    assert run_hook(cmd) == "allow"

def test_unrelated_cmdsub_in_pipe_does_not_trigger():
    cmd = 'echo a > /tmp/out | grep $(date +%s)'
    assert run_hook(cmd) == "allow"
```

新規 `tests/test_secrets_quoted_var_and_cmdsub.py`:

```python
def test_quoted_var_git_add_dotenv_is_ask():
    cmd = 'F=.env; git add "${F}"'
    assert run_secrets_hook(cmd) == "ask"

def test_single_quoted_var_git_add_dotenv_is_ask():
    """単一クォートは展開されないので「allow でも誤動作はしない」
    が、静的に区別する必然性は薄いので ASK 側に倒す（fail-closed）"""
    cmd = "F=.env; git add '${F}'"
    assert run_secrets_hook(cmd) in ("ask", "deny")

def test_cmdsub_git_add_dotenv_is_ask_or_deny():
    cmd = '$(echo git) add .env'
    assert run_secrets_hook(cmd) in ("ask", "deny")

def test_backtick_git_add_dotenv_is_ask_or_deny():
    cmd = '`echo git` add .env'
    assert run_secrets_hook(cmd) in ("ask", "deny")

def test_cmdsub_git_add_pem_is_ask_or_deny():
    cmd = '$(echo git) add server.pem'
    assert run_secrets_hook(cmd) in ("ask", "deny")

# grill 要検討 2: false-positive 抑止
def test_cmdsub_with_dotenv_inside_identifier_does_not_trigger():
    """`.env` がアイデンティファイア中間文字列なら ASK ではない"""
    cmd = '$(date +%s).env_var_name=foo'
    assert run_secrets_hook(cmd) == "allow"

def test_cmdsub_with_dotenv_example_does_not_trigger():
    """safe variant .env.example は ASK ではない"""
    cmd = '$(echo cat) .env.example'
    assert run_secrets_hook(cmd) == "allow"

def test_cmdsub_with_dotenv_template_does_not_trigger():
    cmd = '$(echo cp) src/.env.template /tmp/foo'
    assert run_secrets_hook(cmd) == "allow"

def test_cmdsub_with_dotenv_word_boundary_triggers():
    """.env が単独 token なら ASK"""
    cmd = '$(echo git) add .env'
    assert run_secrets_hook(cmd) in ("ask", "deny")
```

### 実装方針

`hooks/check-control-plane.sh:86-106` — `cmd_var_built_write` を 3 経路の OR に整理：

```bash
cmd_var_built_write() {
  local cmd="$1"
  # 経路 A: 既存の assignment + variable use + write op
  if _cmd_assigned_var_write "$cmd"; then return 0; fi
  # 経路 B (K-2 新規): 「最初の write redirect の write-target token」に
  # cmdsub / backtick がある場合のみ ASK。チェーンを跨いだ無関係な cmdsub
  # で over-flag しないよう、target を `[|&;]` までで切り出す（grill 要検討 1）。
  local write_target
  write_target=$(printf '%s' "$cmd" | sed -nE 's/^[^>]*>>?[[:space:]]*([^|&;]*).*/\1/p' | head -1)
  if [ -n "$write_target" ] && printf '%s' "$write_target" | grep -qE '\$\(|`'; then
    return 0
  fi
  # 経路 C (K-2 新規): printf -v / read / eval / declare / local による
  # 代替 assignment 形 + write op 共存。
  if printf '%s' "$cmd" | grep -qE \
       '(^|;|&|\|)[[:space:]]*(printf[[:space:]]+-v[[:space:]]+|read[[:space:]]+|eval[[:space:]]+|declare[[:space:]]+|local[[:space:]]+)' && \
     printf '%s' "$cmd" | grep -qE '>>?[[:space:]]*[^&]'; then return 0; fi
  return 1
}
```

`hooks/check-secrets.sh:150` — クォート任意化：

```bash
# 旧: git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}[[:space:]]+([^.[:space:]]+[[:space:]]+)*\$\{?[A-Za-z_]
# 新: git[[:space:]]+${GIT_PRE_OPTS}${GIT_STAGE_VERB}[[:space:]]+(["'\'']?[^.[:space:]]+[[:space:]]+)*["'\'']?\$\{?[A-Za-z_]
```

`hooks/check-secrets.sh` 末尾の `emit_allow` 直前に追加（safe-variant strip + word boundary、grill 要検討 2）：

```bash
# K-4: cmdsub/backtick で git/cmd を組み立てる経路 + .env or 高リスク認証ファイル参照
# 先に safe variant (.env.example/.template/.sample) を strip、その後 word boundary
# 付きで .env を検査。これで `.env.example` や `.env_var_name` を false-positive
# として拾わないことを保証。
K4_STRIPPED=$(printf '%s' "$CMD" | sed -E "s/${SAFE_ENV_SUFFIXES}//g")
if printf '%s' "$CMD" | grep -qE '(\$\(|`)' && \
   printf '%s' "$K4_STRIPPED" | grep -qE "(^|[^A-Za-z0-9_])\.env([^A-Za-z0-9_]|$)|${AEGIS_HIGH_RISK_RE}"; then
  emit_ask "[secrets] コマンドが \$(...) / \`...\` で構築されており、.env や認証ファイルを参照しています — 意図しないステージング/書込みでないか確認してください。"
  exit 0
fi
```

### 受入条件

- 新規 12 テスト + false-positive 抑止 5 テストが green
- 既存 `test_control_plane_var_expansion.py` / `test_check_secrets*` 全 green
- REDTEAM-02 / 03 / 04 を `/tmp/` で再実行し ASK が出る
- `python3 scripts/check_reference_drift.py --strict` PASS（hooks/ の mirror 同期）

---

## Task 3: K-5 / K-6 / K-7 — `hooks/lib/safety.sh` 集約

### 攻撃シナリオ（F-01 / F-02 / F-03）

- **K-5 (F-01)**: `rm hooks/lib/emit.sh` 後、`check-control-plane.sh` 等 deny hook が source 失敗で exit 1 + 空 stdout → Claude Code 仕様で **fail-open**
- **K-6 (F-02)**: hook の timeout 宣言が settings に皆無 → 長時間 hook が native 60s で打ち切られ exit 124 / 137 → fail-open
- **K-7 (F-03)**: `post-status-audit.sh` の snapshot 書込みが `> > >>` の 3 段。中断で `phase:` `mode:` 欠落 → tamper 検出が `[ -n "$OLD_PHASE" ]` で素通り

### 仮説

**「moat hook が静かに 0 ファイル output を出すのは Claude Code 仕様の fail-open に直結する」**。安全対応は 3 種：

1. **lib 欠落** → 明示 DENY を pure-bash で吐いて exit 0
2. **timeout 宣言** → settings.json に timeout 秒を必須化（drift で検査）
3. **snapshot 書込み** → atomic 化（tmp に組み立て→mv）

これらを `hooks/lib/safety.sh` に集約し、全 deny hook で先頭に呼ぶ。

### 修正対象

- 新規 `hooks/lib/safety.sh`
- 全 deny 系 hook（`check-control-plane.sh` / `check-secrets.sh` / `check-destructive.sh` / `check-gate.sh` / `check-task-completed.sh` / `check-task-created.sh`）の冒頭
- `templates/hooks.template.json` / `examples/minimal-project/.claude/settings.json` の各 hook エントリに timeout フィールド（**数値は Section 2.2 perf-baseline で決定**）
- `hooks/post-status-audit.sh:121-125` の snapshot 書込み atomic 化
- `hooks/session-start.sh:23-27` の snapshot 書込み atomic 化
- `scripts/update-gate.sh:328-332` の snapshot 書込み atomic 化
- `hooks/post-status-audit.sh:46-49` の **consumer 側ポリシー実装**（grill 要検討 4）：`OLD_PHASE` 空文字 → block、snapshot ファイル不在 → 初回扱い allow（`.claude/.audit-skip.log` に記録）
- `scripts/check_reference_drift.py` に「全 PreToolUse hook に timeout 宣言」契約を追加
- `docs/hook-failure-policy.md` に「lib 欠落」「timeout」「snapshot 不在」「snapshot 部分破損」4 行追加
- `tests/test_failure_policy.py` に 4 シナリオの contract test 追加
- **safety.sh 自身の REQUIRED 登録（grill 致命 2）**：
  - `templates/profiles/{minimal,standard,full}.json` の `required` に `hooks/lib/safety.sh` を追加
  - **同時に既存の `hooks/lib/secrets-patterns.sh` / `phase-skills.sh` も追加（REDTEAM-05 / S-1 同時消化、第6回送り Task の v1.6.2 前倒し）**
  - `scripts/check_framework_contract.py` の REQUIRED_HOOK_FILES に safety.sh / secrets-patterns.sh / phase-skills.sh を全て登録
  - **将来 drift 抑止**: profile required は `hooks/lib/*.sh` glob 包含への移行を検討（v1.7 で構造化）
- **safety.sh fallback の identity 契約（grill 致命 5）**：
  - 6 deny hook 冒頭の inline fallback ブロックは **完全に同一文字列**であること
  - `tests/test_safety_fallback_identity.py` で 6 hook から抽出したブロックの SHA256 が全て一致することを契約
- 新規 `tests/poc/v162-redteam-rerun.sh`（Section 2.1 で宣言）— REDTEAM-01〜06 / F-01〜03 / DIST-01〜04 を一括再走

### TDD 失敗テスト雛形

新規 `tests/test_safety_lib_missing.py`:

```python
@pytest.mark.parametrize("hook", [
    "check-control-plane.sh", "check-secrets.sh", "check-destructive.sh",
    "check-gate.sh", "check-task-completed.sh", "check-task-created.sh",
])
def test_emit_lib_missing_yields_explicit_deny(hook, tmp_install):
    """hooks/lib/emit.sh を消した状態で全 deny hook が明示 DENY を返す"""
    (tmp_install / "hooks/lib/emit.sh").unlink()
    result = run_hook(tmp_install / "hooks" / hook, '{"tool_input":{"command":"x"}}')
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "integrity" in out["hookSpecificOutput"]["permissionDecisionReason"].lower()
```

新規 `tests/test_hook_timeout_declared.py`:

```python
def test_all_pretooluse_hooks_have_timeout_declared():
    settings = json.load(open("templates/hooks.template.json"))
    for hook_event in ("PreToolUse",):
        for entry in settings["hooks"].get(hook_event, []):
            for sub in entry.get("hooks", []):
                assert "timeout" in sub, f"{hook_event} hook has no timeout: {sub}"
                assert isinstance(sub["timeout"], int)
                assert sub["timeout"] >= 5  # 下限
                assert sub["timeout"] <= 60  # 上限
```

新規 `tests/test_snapshot_atomic.py`（YAGNI で 20 iter に縮減）:

```python
def test_snapshot_write_is_atomic_under_sigkill(tmp_install):
    """SIGKILL 中断で snapshot ファイルが部分書き込みにならない（20 回試行）"""
    # 100 回 → 20 回（grill YAGNI）: 確率的にも 20 回で十分検出可能。
    # CI 時間を抑え flaky を減らす。
    for _ in range(20):
        proc = subprocess.Popen([...], stdin=...)
        proc.kill()
        proc.wait()
        if (tmp_install / ".claude/.gate-snapshot").exists():
            content = (tmp_install / ".claude/.gate-snapshot").read_text()
            if content.strip():
                assert "phase:" in content, "snapshot partial write detected"
                assert "mode:" in content
```

新規 `tests/test_snapshot_consumer_policy.py`（grill 要検討 4）:

```python
def test_snapshot_with_empty_old_phase_is_fail_closed(tmp_install):
    """snapshot ファイルが存在し phase: 行が空文字なら post-status-audit は block"""
    (tmp_install / ".claude/.gate-snapshot").write_text("mode: Dev\nphase:\n")
    result = run_post_status_audit(tmp_install, edit_input)
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_snapshot_missing_is_first_edit_allowance(tmp_install):
    """snapshot ファイルが存在しない時は allow + .claude/.audit-skip.log に記録"""
    snap = tmp_install / ".claude/.gate-snapshot"
    if snap.exists():
        snap.unlink()
    result = run_post_status_audit(tmp_install, edit_input)
    out = json.loads(result.stdout)
    assert out == {} or out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
    assert (tmp_install / ".claude/.audit-skip.log").exists()

def test_three_consecutive_skips_warn_next_session(tmp_install):
    """audit-skip.log が 3 行溜まったら次セッション開始で WARNING"""
    (tmp_install / ".claude/.audit-skip.log").write_text("a\nb\nc\n")
    result = run_session_start(tmp_install)
    assert "audit skip" in result.stdout.lower() or "snapshot" in result.stdout.lower()
```

新規 `tests/test_safety_fallback_identity.py`（grill 致命 5）:

```python
import hashlib, re, pathlib

DENY_HOOKS = [
    "check-control-plane.sh", "check-secrets.sh", "check-destructive.sh",
    "check-gate.sh", "check-task-completed.sh", "check-task-created.sh",
]
FALLBACK_BEGIN = "# AEGIS_SAFETY_FALLBACK_BEGIN"
FALLBACK_END = "# AEGIS_SAFETY_FALLBACK_END"

def _extract_fallback(path):
    text = pathlib.Path(path).read_text()
    m = re.search(
        rf"{re.escape(FALLBACK_BEGIN)}\n(.*?)\n[^\n]*{re.escape(FALLBACK_END)}",
        text, re.DOTALL,
    )
    assert m, f"fallback markers missing in {path}"
    return m.group(1)

def test_all_deny_hooks_have_identical_safety_fallback():
    hooks_dir = pathlib.Path("hooks")
    blocks = [_extract_fallback(hooks_dir / h) for h in DENY_HOOKS]
    digests = {hashlib.sha256(b.encode()).hexdigest() for b in blocks}
    assert len(digests) == 1, f"fallback drift: {digests}"

def test_fallback_block_emits_valid_json_with_static_reason():
    import json
    block = _extract_fallback(pathlib.Path("hooks") / DENY_HOOKS[0])
    # fallback には %s / $VAR が混入していてはいけない（JSON injection 防止）
    assert "%s" not in block
    assert "$reason" not in block
    assert "${" not in block.split("printf")[-1].split("\n")[0]
```

新規 `tests/test_safety_lib_registered_in_profiles.py`（grill 致命 2）:

```python
import json, pathlib

REQUIRED_LIBS = ["safety.sh", "secrets-patterns.sh", "phase-skills.sh"]
PROFILES = ["minimal", "standard", "full"]

def test_safety_libs_in_all_profile_required():
    for prof in PROFILES:
        data = json.loads(
            (pathlib.Path("templates/profiles") / f"{prof}.json").read_text()
        )
        required = set(data.get("required", []))
        for lib in REQUIRED_LIBS:
            assert f"hooks/lib/{lib}" in required, \
                f"hooks/lib/{lib} missing from {prof}.json required"

def test_safety_libs_in_framework_contract_required_hook_files():
    from check_framework_contract import REQUIRED_HOOK_FILES
    for lib in REQUIRED_LIBS:
        assert f"hooks/lib/{lib}" in REQUIRED_HOOK_FILES

def test_removing_safety_lib_causes_install_smoke_failure(tmp_path):
    """install 先で hooks/lib/safety.sh を消すと eval_scaffold_smoke が FAIL"""
    project = tmp_path / "proj"
    subprocess.run([SETUP_SH, "--profile=standard", f"--target={project}", "--yes"], check=True)
    (project / "hooks/lib/safety.sh").unlink()
    result = subprocess.run(
        [SCAFFOLD_SMOKE, "--root", str(project)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "safety" in result.stdout.lower() or "safety" in result.stderr.lower()
```

### 実装方針

`hooks/lib/safety.sh`（grill 致命 5: 動的 reason を取らず静的 deny に統一）:

```bash
#!/usr/bin/env bash
# Pure-bash safety helpers. Source FIRST in every deny hook so that even when
# emit.sh / extract-input.sh / patterns.sh fail to source, we still emit a
# structured deny (fail-closed) instead of empty stdout + exit 1 (fail-open).
#
# DESIGN: The fallback inline block in each deny hook MUST be byte-identical
# (enforced by tests/test_safety_fallback_identity.py). The reason string is
# STATIC — no %s / $VAR substitution — to eliminate JSON-injection risk and
# remove drift surface. The reason is fixed at "[integrity] hook safety lib
# unavailable" and the specific failure (e.g. which lib failed) is delegated
# to a stderr line for the operator log.

# Emit an explicit deny that does not depend on emit.sh.
# Caller's stderr_hint is logged but NOT included in the JSON reason (JSON
# stays a literal — see above).
_aegis_emit_fail_closed_deny() {
  local stderr_hint="${1:-unspecified}"
  printf '[aegis-safety] fail-closed: %s\n' "$stderr_hint" >&2
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}}'
  exit 0
}

# Source a lib file; on failure, fail-closed.
aegis_require_lib() {
  local lib="$1"
  # shellcheck disable=SC1090
  source "$lib" 2>/dev/null || _aegis_emit_fail_closed_deny "lib source failed: $(basename "$lib")"
}
```

各 deny hook の冒頭に置く**統一 fallback ブロック**（identity 契約で SHA 一致を強制、`AEGIS_SAFETY_FALLBACK_BEGIN`/`END` マーカーで抽出）：

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# AEGIS_SAFETY_FALLBACK_BEGIN — DO NOT EDIT (sha-locked by tests/test_safety_fallback_identity.py)
if ! source "${SCRIPT_DIR}/lib/safety.sh" 2>/dev/null; then
  printf '[aegis-safety] fail-closed: safety.sh source failed\n' >&2
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}}'
  exit 0
fi
# AEGIS_SAFETY_FALLBACK_END
aegis_require_lib "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib "${SCRIPT_DIR}/lib/extract-input.sh"
# ...残り
```

snapshot 書込み atomic 化（`post-status-audit.sh` / `session-start.sh` / `update-gate.sh` の 3 箇所同時、YAGNI 検討の結果**同型なので一気に潰す**）：

```bash
# 旧: sed > FILE; grep >> FILE; grep >> FILE
# 新（atomic write）:
TMP="${SNAPSHOT_FILE}.tmp.$$"
{
  sed -n '/^---$/,/^---$/p' "$STATUS_FILE" 2>/dev/null
  grep -m1 '^phase:' "$STATUS_FILE" 2>/dev/null
  grep -m1 '^mode:' "$STATUS_FILE" 2>/dev/null
} > "$TMP" && mv "$TMP" "$SNAPSHOT_FILE" || {
  rm -f "$TMP" 2>/dev/null
  printf '[aegis-safety] snapshot write failed (atomic mv error)\n' >&2
}
```

consumer 側ポリシー（`post-status-audit.sh:46-49`、grill 要検討 4）：

```bash
# snapshot ファイル不在 → 初回扱い: allow + skip 記録
if [ ! -f "$SNAPSHOT_FILE" ]; then
  printf '%s\n' "$(date -u +%FT%TZ) first-edit allowance (snapshot missing)" \
    >> "${ROOT}/.claude/.audit-skip.log"
  emit_allow
  exit 0
fi

# snapshot 存在 → 必須フィールド検査。空文字 / 欠落は fail-closed
OLD_PHASE=$(grep -m1 '^phase:' "$SNAPSHOT_FILE" | sed 's/^phase:[[:space:]]*//')
OLD_MODE=$(grep -m1 '^mode:' "$SNAPSHOT_FILE" | sed 's/^mode:[[:space:]]*//')
if [ -z "$OLD_PHASE" ] || [ -z "$OLD_MODE" ]; then
  emit_deny "[integrity] snapshot ファイルに必須フィールド (phase / mode) が欠落しています。手動編集や中断書き込みの可能性 — .claude/.gate-snapshot を確認するか /recover を実行してください。"
  exit 0
fi
```

`session-start.sh` で `.claude/.audit-skip.log` が **3 行以上**溜まっていれば warning を additionalContext に注入（連続スキップ検知）。

timeout 宣言（`templates/hooks.template.json`、**値は Section 2.2 perf-baseline で決定**）：

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PROJECT_DIR}/hooks/check-control-plane.sh",
  "timeout": 30
}
```

`check-secrets.sh` は `find $ROOT -name '.env*'` を伴うため別途上限（30〜60s）。具体値は perf-baseline 計測結果を `docs/perf-baseline.md` に記録した上で確定。

### 受入条件

- 新規 6 テストファイル全 green:
  - `test_safety_lib_missing.py`
  - `test_hook_timeout_declared.py`
  - `test_snapshot_atomic.py`（20 iter）
  - `test_snapshot_consumer_policy.py`
  - `test_safety_fallback_identity.py`
  - `test_safety_lib_registered_in_profiles.py`
- 既存 `test_failure_policy.py` 全 green（policy doc との整合）
- F-01 / F-02 / F-03 / REDTEAM-05 を `/tmp/` で再現し明示 deny が出る
- `docs/perf-baseline.md` が存在し各 hook の計測値が表形式で記録されている
- `tests/poc/v162-redteam-rerun.sh` が初版として REDTEAM-01〜06 / F-01〜03 を実行できる（DIST-01〜04 は Task 4 で有効化）
- drift / contract / smoke 全 PASS（mirror 同期含む）

---

## Task 4: K-8 / K-9 / K-11 — 配布パスの破壊抑止

### 攻撃シナリオ（DIST-01 / DIST-02 / DIST-04）

- **K-8 (DIST-01)**: `bin/setup.sh` 実行で既存 `.claude/settings.local.json` の `permissions.allow` が静かに消失
- **K-9 (DIST-02)**: 旧版（v1.4.x）から v1.6.1 upgrade で `hooks/lib/emit.sh` が `SKIP (exists)` 残留 → 新 hook が `emit_ask: command not found` → exit 127 → fail-open
- **K-11 (DIST-04)**: `framework_version: "1.4.0"` のまま v1.6.1 setup を当てても doctor / contract が版差分を見ない

### 仮説

- 配布は「ユーザ管理領域（permissions/env/その他将来追加される top-level key）」と「framework 管理領域（hooks セクション、hooks/lib/*、scripts/、.claude/agents/、.claude/skills/、.claude/rules/）」を**明確に分離**
- settings.local.json の**`hooks` 以外の全 key を保存**（永続的な互換性のため。grill 致命 4 対応）。Claude Code の将来の新規 top-level key（例: `mcpServers` の拡張）にも自動追随
- framework 管理領域は強制上書き。ユーザの自前 hook をどこに置くかは**ドキュメント化**（`.claude/settings.json` に書く運用を README で案内）
- `framework_version` を install 時に `.claude/.aegis-install-version` に書く
- doctor は version stamp を読み framework と差があれば WARN
- `--target` が framework_root 自身なら abort（DIST-12 を前倒し、grill 致命 2 と関連する safety）

### 修正対象

- `bin/setup.sh:113-196` `generate_settings()` — 既存 settings.local.json を読み **hooks 以外の全 key を保存**、hooks セクションのみ置換
- `bin/setup.sh:82-96` `copy_file()` — `hooks/lib/*.sh` 系は `force=true` 相当で強制上書き
- `bin/setup.sh` 末尾 — `.claude/.aegis-install-version` に framework_version 書き込み
- `bin/setup.sh` の `--target` 検証 — framework_root 自身なら abort（DIST-12 前倒し）
- `scripts/status_doctor.py` — version stamp と framework version の照合を追加
- `scripts/check_framework_contract.py` — version stamp 検査追加（install target 指定時のみ）
- `README.md` — 「ユーザ自前の hook は `.claude/settings.json` に書き、aegis 管理の `.claude/settings.local.json` とは別ファイル扱い」の運用ガイドを追記
- `docs/qa-reports/v162-review.md`（リリース時作成）— **「v1.6.2 から既存 settings.local.json は再 install 時に `.bak.<ts>` で退避します」の behavioral change 告知**（grill 要検討 5）

### TDD 失敗テスト雛形

新規 `tests/test_setup_preserves_user_settings.py`:

```python
def test_existing_permissions_allow_preserved(tmp_path):
    """既存 settings.local.json の permissions.allow がリインストールで保存される"""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".claude").mkdir()
    existing = {
        "permissions": {"allow": ["Bash(npm:*)"]},
        "hooks": {},
    }
    (project / ".claude/settings.local.json").write_text(json.dumps(existing))
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    after = json.loads((project / ".claude/settings.local.json").read_text())
    assert "Bash(npm:*)" in after["permissions"]["allow"], "user permission lost"

def test_existing_env_preserved(tmp_path):
    """env も保存される"""
    project = tmp_path / "proj"; project.mkdir(); (project / ".claude").mkdir()
    existing = {"env": {"MY_VAR": "x"}, "hooks": {}}
    (project / ".claude/settings.local.json").write_text(json.dumps(existing))
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    after = json.loads((project / ".claude/settings.local.json").read_text())
    assert after.get("env", {}).get("MY_VAR") == "x"

def test_unknown_top_level_key_preserved(tmp_path):
    """grill 致命 4: 将来 Claude Code が追加する未知の key も保存される"""
    project = tmp_path / "proj"; project.mkdir(); (project / ".claude").mkdir()
    existing = {"futureKey": {"x": 1}, "hooks": {}}
    (project / ".claude/settings.local.json").write_text(json.dumps(existing))
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    after = json.loads((project / ".claude/settings.local.json").read_text())
    assert after.get("futureKey", {}).get("x") == 1, "unknown key lost"

def test_hooks_section_is_overwritten(tmp_path):
    """hooks セクションは framework 管理＝強制上書き"""
    project = tmp_path / "proj"; project.mkdir(); (project / ".claude").mkdir()
    existing = {"hooks": {"PreToolUse": [{"matcher": "Custom", "hooks": []}]}}
    (project / ".claude/settings.local.json").write_text(json.dumps(existing))
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    after = json.loads((project / ".claude/settings.local.json").read_text())
    matchers = [e.get("matcher") for e in after["hooks"].get("PreToolUse", [])]
    assert "Custom" not in matchers, "user hooks section should be overwritten"

def test_backup_created_on_overwrite(tmp_path):
    """既存ファイルがあれば .bak.<ts> が作られる（behavioral change の周知必要）"""
    project = tmp_path / "proj"; project.mkdir(); (project / ".claude").mkdir()
    (project / ".claude/settings.local.json").write_text('{"hooks":{}}')
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    baks = list((project / ".claude").glob("settings.local.json.bak.*"))
    assert len(baks) >= 1, "no backup file created"

def test_target_equal_to_framework_root_is_rejected(tmp_path):
    """DIST-12 前倒し: framework 自身に install しようとすると abort"""
    framework_root = pathlib.Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [str(SETUP_SH), "--profile=standard", f"--target={framework_root}", "--yes"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "framework" in (result.stderr + result.stdout).lower()
```

新規 `tests/test_setup_upgrades_libs.py`:

```python
def test_old_lib_overwritten_on_reinstall(tmp_path):
    """旧版の emit.sh が新版の関数を持たない時、再 install で強制上書きされる"""
    project = tmp_path / "proj"
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    (project / "hooks/lib/emit.sh").write_text("# old stub\nemit_allow() { :; }\n")
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    content = (project / "hooks/lib/emit.sh").read_text()
    assert "emit_ask" in content, "lib not force-upgraded"
```

新規 `tests/test_version_stamp.py`:

```python
def test_install_writes_version_stamp(tmp_path):
    project = tmp_path / "proj"
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    stamp = (project / ".claude/.aegis-install-version").read_text().strip()
    assert stamp == FRAMEWORK_VERSION

def test_doctor_detects_version_mismatch(tmp_path):
    project = tmp_path / "proj"
    subprocess.run([str(SETUP_SH), "--profile=standard", f"--target={project}", "--yes"], check=True)
    (project / ".claude/.aegis-install-version").write_text("1.4.0\n")
    result = subprocess.run([str(STATUS_DOCTOR), "--root", str(project)], capture_output=True, text=True)
    assert "version" in result.stdout.lower()
    assert result.returncode != 0
```

### 実装方針

`bin/setup.sh` の `generate_settings()` の最初に（grill 致命 4: hooks 以外の全 key を保存）：

```bash
# 既存 settings.local.json を読み、hooks 以外の全 key を保存して退避
if [ -f "$dst" ]; then
  cp "$dst" "${dst}.bak.$(date +%s)" 2>/dev/null || true
  # framework 生成後にユーザ key をマージする stash を作る
  python3 - "$dst" > "${dst}.user-keys.tmp" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
except Exception:
    data = {}
# hooks は framework 所有なので除外、それ以外の top-level key 全てを保存
user_keys = {k: v for k, v in data.items() if k != "hooks"}
print(json.dumps(user_keys))
PY
fi
# ... framework が settings.local.json を生成 ...

# 生成後にユーザ key を上書きマージ（hooks は触らない）
if [ -f "${dst}.user-keys.tmp" ]; then
  python3 - "$dst" "${dst}.user-keys.tmp" <<'PY'
import json, sys
with open(sys.argv[1]) as f: gen = json.load(f)
with open(sys.argv[2]) as f: user = json.load(f)
for k, v in user.items():
    gen[k] = v  # hooks 以外を全部 user 値で上書き
with open(sys.argv[1], 'w') as f: json.dump(gen, f, indent=2)
PY
  rm -f "${dst}.user-keys.tmp"
fi
```

`bin/setup.sh` の引数検証部に framework_root 自己検出 abort を追加：

```bash
# DIST-12 前倒し: framework_root 自身への install を禁止
framework_root="$(cd "$(dirname "$0")/.." && pwd -P)"
target_real="$(cd "$TARGET" && pwd -P 2>/dev/null || echo "$TARGET")"
if [ "$target_real" = "$framework_root" ]; then
  echo "ERROR: cannot install into the framework repo itself ($framework_root)" >&2
  echo "       Use --target=<your-project-dir>" >&2
  exit 1
fi
```

lib 強制上書き：

```bash
# copy_hooks() 内
for lib in hooks/lib/*.sh; do
  cp -f "${SRC}/${lib}" "${TARGET}/${lib}"  # SKIP しない
done
```

version stamp：

```bash
# setup.sh 末尾
mkdir -p "${TARGET}/.claude"
printf '%s\n' "$FRAMEWORK_VERSION" > "${TARGET}/.claude/.aegis-install-version"
```

### 受入条件

- 新規 8 テスト green（permissions / env / unknown key / hooks 上書き / backup / target=framework_root / lib upgrade / version stamp）
- 既存 setup 系テスト全 green
- DIST-01 / DIST-02 / DIST-04 / DIST-12 を `/tmp/` で再現し問題ないことを確認
- `tests/poc/v162-redteam-rerun.sh` に DIST-01〜04 シナリオを追加して PASS
- README に「ユーザ自前 hook は `.claude/settings.json` に置く」の運用ガイドが入っている
- `docs/qa-reports/v162-review.md` 草稿に **behavioral change（既存 settings.local.json は `.bak.<ts>` 退避）** が明記されている

---

## Task 5: K-10 — setup prereq 検査

### 攻撃シナリオ（DIST-03）

```bash
# 偽 python3 stub（exit 127）を PATH 先頭に置いて
bin/setup.sh --profile=standard --target=/tmp/foo --yes
# 観察: "Setup complete." EXIT=0、しかし install 先には .gitignore 1 枚しか作られない
```

### 仮説

`set -euo pipefail` 下の process substitution `< <(parse_json_array ...)` は pipefail を伝播しない。`parse_json_array` が python3 不在で 0 件返しても、while ループが 0 回回って静かに成功する。

### 修正対象

- `bin/setup.sh:4-30`（先頭プリアンブル付近）に prereq 検査ブロック追加
- `bin/setup.sh:99-110` `parse_json_array` に件数チェック

### TDD 失敗テスト雛形

新規 `tests/test_setup_prereq.py`:

```python
def test_setup_fails_loudly_without_python3(tmp_path):
    """偽 python3 stub を PATH に置くと setup は早期 exit 1 する"""
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    (stub_dir / "python3").write_text("#!/bin/sh\nexit 127\n")
    (stub_dir / "python3").chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{stub_dir}:{env['PATH']}"
    result = subprocess.run(
        [str(SETUP_SH), "--profile=standard", f"--target={tmp_path / 'proj'}", "--yes"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "python3" in result.stderr.lower()

def test_setup_succeeds_when_python3_runs_but_returns_empty_array(tmp_path):
    """parse_json_array は『python3 が走ったか』のみ検査。
    minimal profile は recommended が空配列でも合法なので、空配列 ≠ エラー。
    grill 要検討の通り、件数は profile 仕様の自由度のため検査しない。"""
    # minimal profile を target に install して exit 0
    project = tmp_path / "proj"
    result = subprocess.run(
        [str(SETUP_SH), "--profile=minimal", f"--target={project}", "--yes"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0

def test_parse_json_array_aborts_when_python3_crashes(tmp_path):
    """python3 が走った結果 stderr に出力して exit 非 0 なら setup 全体が abort"""
    # 壊れた profile JSON を渡して python3 が落ちるシナリオ
    ...
```

### 実装方針

`bin/setup.sh` の冒頭（`set -euo pipefail` の直後）：

```bash
# Prereq checks (K-10 / DIST-03)
require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  fi
}
require_cmd python3
require_cmd bash

# bash 4+ 推奨だが BSD 3.2 でも動くので警告のみ
if ((BASH_VERSINFO[0] < 4)); then
  echo "WARNING: bash 4+ recommended (current: ${BASH_VERSION})" >&2
fi
```

`parse_json_array` の戻り値検査：

```bash
parse_json_array() {
  local out
  out=$(python3 -c '...' "$1" "$2") || { echo "ERROR: parse_json_array failed for $2" >&2; exit 1; }
  printf '%s\n' "$out"
}
```

### 受入条件

- 新規テスト green
- 既存 setup テスト全 green
- DIST-03 を `/tmp/` で再現し明示 ERROR が出る

---

## Task 6: K-12 — full profile に必須テンプレ追加

### シナリオ（JNY-07）

`full.json` は `BRAINSTORM-RECORD / SPEC / TRANSLATION-MAPPING / RUNBOOK / MANUAL / UAT-RESULTS` の 6 件のみを配布。だが `client_ready_for_dev` は **PRD / SCOPE / NFR / ACCEPTANCE / HANDOVER-TO-DEV / translation** の 6 件を sentinel 付きで要求。非エンジニアは「テンプレが無いのにテンプレ通り埋めろ」で詰む。

### 仮説

機械検査 (`scripts/check_status.py:CLIENT_GATE_ARTIFACTS` / `DEV_GATE_ARTIFACTS`) と install 配布 (`templates/profiles/full.json` の `recommended`) は**双方向に対称**でなければならない。今後の drift を恒久封鎖するため **明示マッピング辞書 + parity test** を追加。stem 抽出（grill 致命 4 で指摘）は使わない。

### 修正対象

- 新規 `scripts/_artifact_template_map.py` — 単一所有の `ARTIFACT_TO_TEMPLATE` dict
- `scripts/check_status.py` — `_artifact_template_map` を import して使用、stem 抽出を廃止
- `templates/profiles/full.json:recommended` に PRD / SCOPE / NFR / ACCEPTANCE / HANDOVER-TO-DEV / HANDOVER-TO-CLIENT / PLAN / QA-REPORT / REVIEW / SECURITY-REVIEW / DEPLOY-CHECKLIST / DECISION / VERIFICATION / SECOND-OPINION を追加
- `scripts/check_status.py:942-947` の deny メッセージに `ARTIFACT_TO_TEMPLATE[path]` を引いてテンプレ場所を表示
- 新規 `tests/test_profile_checker_parity.py`（CLIENT 側と DEV 側の独立 parity test）

### TDD 失敗テスト雛形

新規 `scripts/_artifact_template_map.py`（grill 致命 4: stem 抽出を廃して明示 dict）:

```python
"""Single source of truth: artifact path → template path mapping.

stem 抽出（pathlib.Path(p).stem）は HANDOVER-TO-DEV / TRANSLATION-MAPPING /
SECOND-OPINION 等の non-1:1 命名で破綻するため、明示 dict で固定する。
check_status.py（gate 検査）と tests/test_profile_checker_parity.py
（parity 契約）はこの dict のみを参照する。
"""

ARTIFACT_TO_TEMPLATE = {
    # Client gate
    "docs/requirements/PRD.md":         "templates/PRD.template.md",
    "docs/requirements/SCOPE.md":       "templates/SCOPE.template.md",
    "docs/requirements/NFR.md":         "templates/NFR.template.md",
    "docs/requirements/ACCEPTANCE.md":  "templates/ACCEPTANCE.template.md",
    "docs/handover/TO-DEV.md":          "templates/HANDOVER-TO-DEV.template.md",
    "docs/translation/mapping.md":      "templates/TRANSLATION-MAPPING.template.md",
    # Dev gate（dev_ready_for_client 側で追加要求が出るもの）
    "docs/handover/TO-CLIENT.md":       "templates/HANDOVER-TO-CLIENT.template.md",
    "docs/plans/PLAN.md":               "templates/PLAN.template.md",
    "docs/qa-reports/QA-REPORT.md":     "templates/QA-REPORT.template.md",
    "docs/qa-reports/REVIEW.md":        "templates/REVIEW.template.md",
    "docs/qa-reports/SECURITY-REVIEW.md": "templates/SECURITY-REVIEW.template.md",
    "docs/qa-reports/DEPLOY-CHECKLIST.md": "templates/DEPLOY-CHECKLIST.template.md",
    # 参考成果物（gate 必須ではないが onboarding 教材で要求）
    "docs/decisions/DECISION.md":       "templates/DECISION.template.md",
    "docs/qa-reports/VERIFICATION.md":  "templates/VERIFICATION.template.md",
    "docs/second-opinion.md":           "templates/SECOND-OPINION.template.md",
}
```

新規 `tests/test_profile_checker_parity.py`:

```python
from scripts._artifact_template_map import ARTIFACT_TO_TEMPLATE
import json, pathlib

PROFILE_FULL = pathlib.Path("templates/profiles/full.json")

def _gate_artifacts_from_checker(gate_name):
    """check_status.py の <GATE>_GATE_ARTIFACTS 定数を import"""
    from check_status import CLIENT_GATE_ARTIFACTS, DEV_GATE_ARTIFACTS
    return {
        "client_ready_for_dev": CLIENT_GATE_ARTIFACTS,
        "dev_ready_for_client": DEV_GATE_ARTIFACTS,
    }[gate_name]

def test_artifact_template_map_covers_all_client_gate_artifacts():
    """ARTIFACT_TO_TEMPLATE は client_ready_for_dev の全 artifact を網羅"""
    for path, _sentinel in _gate_artifacts_from_checker("client_ready_for_dev"):
        assert path in ARTIFACT_TO_TEMPLATE, \
            f"{path} required by client_ready_for_dev but not in ARTIFACT_TO_TEMPLATE"

def test_artifact_template_map_covers_all_dev_gate_artifacts():
    for path, _sentinel in _gate_artifacts_from_checker("dev_ready_for_client"):
        assert path in ARTIFACT_TO_TEMPLATE, \
            f"{path} required by dev_ready_for_client but not in ARTIFACT_TO_TEMPLATE"

def test_full_profile_distributes_all_required_templates():
    """full profile の recommended が ARTIFACT_TO_TEMPLATE の全 template を含む"""
    profile = json.loads(PROFILE_FULL.read_text())
    distributed = set(profile.get("recommended", []))
    for artifact, template in ARTIFACT_TO_TEMPLATE.items():
        assert template in distributed, \
            f"{template} (for {artifact}) required by mapping but not in full profile"

def test_all_template_paths_in_map_exist_on_disk():
    """mapping 内の template path が実在する（タイポ検出）"""
    for artifact, template in ARTIFACT_TO_TEMPLATE.items():
        assert pathlib.Path(template).exists(), \
            f"{template} (for {artifact}) does not exist on disk"

def test_deny_message_includes_template_path(tmp_path):
    """deny メッセージにテンプレ場所が含まれる"""
    # 空の docs/ で client_ready_for_dev pre-approve → deny メッセージ取得
    project = tmp_path / "proj"
    # ... setup ...
    result = subprocess.run(
        [CHECK_STATUS, "--pre-approve-gate", "client_ready_for_dev", "--root", str(project)],
        capture_output=True, text=True,
    )
    assert "templates/PRD.template.md" in (result.stdout + result.stderr)
    assert "templates/HANDOVER-TO-DEV.template.md" in (result.stdout + result.stderr)
```

### 実装方針

`templates/profiles/full.json` の `recommended` を拡張。並行して `check_status.py` の deny メッセージ生成箇所で（stem 抽出ではなく明示 dict を使う）：

```python
from scripts._artifact_template_map import ARTIFACT_TO_TEMPLATE

def _missing_artifact_message(gate_name, missing):
    lines = [f"[{gate_name}] 必須成果物が不足しています:"]
    for path, sentinel in missing:
        template = ARTIFACT_TO_TEMPLATE.get(path, "（mapping 未登録 — 計画書 Task 6 を更新）")
        lines.append(f"  - {path}（テンプレ: {template}）")
    return "\n".join(lines)
```

`ARTIFACT_TO_TEMPLATE` に登録漏れがあれば deny メッセージで明示的に「mapping 未登録」と出るので、テスト失敗時の追跡が容易。

### 受入条件

- 新規 parity test 5 件すべて green（CLIENT 網羅 / DEV 網羅 / profile 配布 / template 実在 / deny メッセージ）
- 既存 client_ready_for_dev / dev_ready_for_client テスト全 green
- 新規 install で `docs/requirements/PRD.md` 等の全テンプレが配布される（mapping 全 path）
- JNY-06 deny メッセージにテンプレ場所が出る（明示 dict 経由）
- mirror 同期: `examples/minimal-project/templates/` も含めて drift PASS

---

## Task 7: K-13 — cheatsheet に 🟡 ack 判断例

### シナリオ（JNY-12）

`docs/onboarding/03-cheatsheet.md:64` は 「🟡=要確認（--ack で承認）」 とだけ書く。**「いつ ack せず止めるべきか」の判断例が無い**ため非エンジニアが「LLM 大丈夫って言ってるから」で機械事実を読まず ack 連打 → moat の決定論ガードを人間側で無効化。

### 仮説

cheatsheet に **「🟡 のうち ack していい例／ダメな例」を 3-5 例**示す。例は「自分が判断できる」を最優先（「LLM が言った」を根拠としない指針）。

### 修正対象

- `docs/onboarding/03-cheatsheet.md`（🟡 ack セクション追記）

### 実装方針

cheatsheet に追加するセクション（grill YAGNI で 4 代表例に絞り、Task 1 (K-1) 修正後の状態を反映）：

```markdown
### 🟡 を ack していい例／ダメな例

K-1 修正後（v1.6.2 以降）、テスト 0 件実行は marker_verified=false となり 🟡 を介さず
🔴 直行になる。下記は v1.6.2 で残る代表的な 🟡 状況の判断基準。

| 状況 | ack 可否 | 理由 |
| --- | --- | --- |
| **qa**: テスト未記録（marker_verified=false） | ❌ 不可 | テストが本当に走ったかが事実として未確認。実テスト走行→`record-test-result.py` で記録後に再判定 |
| **review**: 第2意見が未取得 + 規模 S（1 ファイル） | ✅ 可 | 影響範囲が小さい場合は state-machine 規約で省略可。差分 30 行以下を目安 |
| **security**: 漏洩キー検査（`grep -rE 'sk-[A-Za-z0-9]{20,}'` 等）未実施 | ❌ 不可 | check-secrets の hook が deny しなくても、ユーザ側で目視確認した記録を `docs/qa-reports/v*-security.md` に残してから ack |
| **deploy**: rollback 手順が `TBD` のまま | ❌ 不可 | 障害時の戻し手順が無いままの deploy は禁止。RUNBOOK.md / DEPLOY-CHECKLIST.md に具体手順を書く |

**根本ルール**: 🟡 は「LLM が大丈夫と言った」を根拠にしないこと。あなた（オーナー）が judge card の「機械が見た事実」欄を読み、自分で判断できるときだけ ack。判断が付かないなら止めて second-opinion.md を書く。
```

### 受入条件

- cheatsheet 改訂が markdownlint PASS
- 既存 cheatsheet テストがあれば全 green
- K-1 修正と整合（「pytest -k <NOMATCH>」例は本表から削除済み＝Task 1 完了が前提）

---

## 3. 全タスク終了後のリリース手順

1. **grill-code（Task 18）**：v1.6.2 全コミットを攻撃側から再 PoC（`tests/poc/v162-redteam-rerun.sh` を含む）
2. **gate 消化**：review / qa / security / deploy を judge card で評価し ack 承認
3. **`docs/qa-reports/v162-*.md`** 4 点セット作成。**review.md に behavioral change（既存 settings.local.json は `.bak.<ts>` で退避）を必須記載**（grill 要検討 5）
4. **`bin/aegis` 等の framework_version を 1.6.2 に bump**
5. **CHANGELOG / README 更新**（最新 1〜2 リリースのみ本文残し）。READMEに「ユーザ自前 hook は `.claude/settings.json` に置く」運用ガイドが入っていることを確認
6. **tag `v1.6.2` を打って origin push**

### 3.1 behavioral change の周知

v1.6.2 は patch だが Task 4 が**既存 `.claude/settings.local.json` を再 install 時に `.bak.<ts>` で退避する**挙動変更を含む。CHANGELOG に **「Notable behavior change」** セクションで明示し、`docs/qa-reports/v162-review.md` でも該当節を立てる。

## 4. 残課題（v1.7 へ送り）

本計画には含めない（v1.7 charter で取り組む）：

- **K-14**: PostToolUse Bash 400ms/call（fingerprint cache + IS_TEST 早期判定）
- **K-15**: update_gate_lock テスト 88s sleep（monkeypatched poller + pytest-xdist）
- **K-16**: README トップ 200 行の専門語 + setup 出力末尾「次の一手」
- **S-2〜S-23**: 第5回 / 第6回の 🟡 級所見（S-1 は本計画 Task 3 で前倒し消化）
- **T3**: `bin/aegis-doctor` 集約コマンド新設（DIST-05 / DIST-12 のうち DIST-12 は本計画で前倒し済み）
- **T4 構造化**: profile required の `hooks/lib/*.sh` glob 包含（手書き列挙の drift を畳む）

## 5. 検証スクリプト一式

すべて grill 完了後に通すコマンド：

```bash
cd /Users/miyagakiyuuya/Desktop/personal/superpowers-gstack-antigravitykit-urtorapowers/aegis

# 1. 全テスト
pytest -v

# 2. drift / contract / smoke（mirror チェック必須）
python3 scripts/check_reference_drift.py --strict
python3 scripts/check_framework_contract.py --profile=minimal --strict
python3 scripts/check_framework_contract.py --profile=standard --strict
python3 scripts/check_framework_contract.py --profile=full --strict
python3 scripts/eval_scaffold_smoke.py

# 3. 再 PoC（/tmp scaffold）
bash tests/poc/v162-redteam-rerun.sh  # Task 3 末尾で初版作成

# 4. perf-baseline の更新確認
test -f docs/perf-baseline.md
```

`tests/poc/v162-redteam-rerun.sh` は REDTEAM-01〜06 / F-01〜03 / DIST-01〜04 を一括再走するハーネス。**所有 Task は Task 3 末尾**、各 Task 完了時に該当 PoC を有効化していく。
