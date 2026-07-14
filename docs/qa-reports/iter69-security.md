# iter69 security レポート — B1 drill 強化（NO_RUN 拒否＋mutant 構文検証＋コメントラン floor 除外＋since baseline）

- 対象: `git diff cbc49e7..HEAD`（scripts/run-test-strength-drill.py・hooks/lib/patterns.sh・tests/・.claude/skills/qa-verification/SKILL.md）
- 構成: 1次 security（`security` agent・opus・実発火 injection battery・隔離 clone）／盲検2次（`security` agent・fable・**物理隔離 clone**・fresh）／親 verify（fable・in-session）
- verdict: **approve_with_notes**（1次=approve_with_notes／盲検2次=approve_with_notes／親 verify 一致）
- **新規脆弱性: 0 件**（本 diff 由来の Critical/High なし・両者独立に到達）
- deploy blocker: なし（M＝deploy skip・auth/secret/HTTPS 等の阻害要因は対象外かつ該当なし）

## 攻撃面の確定

実運用の呼び出しは `check_status.py::run_qa_drill`（承認時）が spec パス（`docs/qa-reports/test-strength.drill`）と `--root`（repo root）を**固定 argv で渡す**。攻撃者制御入力は `.drill` JSON の中身のみ（`test_command`／`timeout_seconds`／`since`／`mutants[].{file,line,original,mutated}`）。`patterns_lib` 引数はテスト専用（CLI/spec 露出なし）。

## OWASP 該当項目＋実測（injection battery・canary 方式）

| 攻撃面 | 手法 | 実測 | 結論 |
|--------|------|------|------|
| **Command Injection（test_command）** | `; touch`／`$(touch)`／backtick／`\|touch`／`&&touch`／改行＋touch／`>file`／`--version;touch` の8ベクタ | **canary 生成ゼロ**。probe は位置引数 $2（shell 再パースなし）・`_execute` は shlex+shell=False で inert argv 化→Errno2（baseline 非green＝fail-closed） | 不成立 |
| **patterns.sh source 悪用** | runtime で `patterns_lib` を攻撃者制御にできるか | 常に `PATTERNS_LIB`（スクリプト位置相対固定）。argparse 露出は --root/--spec/--report のみ・spec/CLI に注入口なし | 不成立（contained） |
| **since git argument-injection** | `--output=FILE`／`--git-dir=/tmp`／`-`／`--all`／`--upload-pack=touch FILE`／`$(touch)`／改行注入 の9ベクタで file-write canary 狙撃 | **全て DrillError・canary ゼロ**。`f"{since}^{{commit}}"` を単一 argv トークン化＋`shell=False`＝option 単体解釈を機構的に破壊。merge-base に届くのは rev-parse 成功時の 40-hex sha のみ | 不成立（contained） |
| **path traversal（since/mutant.file）** | `../../../../etc/passwd` 等 | since=解決不能で reject。mutant.file は anti-gaming(a) が「added（リポ内相対）行」を要求＝新設 syntax_check/non_coverable は anti-gaming 後 or added 交差済みのみ読取 | 不成立（既存ガード保存） |
| **env 汚染（NO_RUN 無効化）** | `AEGIS_TEST_NO_RUN_FLAG_REGEX=''`／`=ZZZ` を環境注入して `--collect-only` を検査 | **両方 BLOCKED**。`source patterns.sh` が無条件再代入＝env override 不発（生 bash probe で source 後に本物 regex 実測）。`FOO=bar cmd` 前置も shlex で argv 先頭＝プログラム名扱い | 不成立 |
| **Sensitive Data / Secrets** | diff の secret パターン grep | ヒットは変数名 `LINE_COMMENT_TOKENS`＋コメントのみ・ハードコード資格情報なし | 該当なし |
| **Vulnerable Dependencies** | 新規依存 | `ast`（stdlib）のみ・第三者依存ゼロ | 該当なし |

## fail-open 退行チェック（新機能）

検査不能6条件を投入し全て fail-closed（DrillError→verdict FAIL）を実測: patterns.sh 不在／regex 未定義（rc=3）／shlex 解析失敗（未終端クォート）／regex 空文字列（`[ -n ]` ガード）／非 git dir の since／構文破壊 mutant（.py compile・.sh bash -n）。floor 除外の劣化も STRICT（`_docstring_lines` は parse 不能で空集合＝免除なし・`_parses` broken→拒否）。**新 fail-open 分岐ゼロ**。混在ラン（コメント+コード）は floor 維持＝偽造面積は増えない（実測）。

## findings

本 diff 由来の新規脆弱性は**ゼロ**。residual は以下（いずれも非ブロッキング）:

### R-1 [Major-class・pre-existing＝SF-014] 非フラグ no-run コマンドで偽 DRILL PASS
- `scripts/run-test-strength-drill.py:62`（check_no_run_command）/ `hooks/lib/patterns.sh:190`。`python3 -c "import m"`／`go test -list`／`py_compile` 等の**テストランナーですらないコマンド**＋import-crash mutant で 0 テスト実行の偽 PASS。
- **差分実測で pre-existing 確定（1次＋盲検2次が独立に到達）**: cbc49e7 の runner は `check_no_run_command` を持たず（flag/非flag とも素通し）、HEAD は flag クラスに拒否を追加したが非フラグは HEAD でも PASS ＝ このクラスの net 変化ゼロ・iter69 は flag カバレッジを増やしただけの net 改善。
- **contained**: anti-gaming floor／baseline-green 要求／mutant survival／qa の test_command 人手プレビュー運用／patterns.sh コメント文書化。恒久策＝iter70+ の positive「N tests executed」proof。**SF-014 起票済み**。

### R-2 [Low・本 diff 由来] floor 免除が複数行文字列内部の `#` 始まり行を誤免除
- `scripts/run-test-strength-drill.py:non_coverable_lines`。py の triple-quote 非docstring 文字列内部で `#` 始まり/空行になっている行を「コメント」と誤分類し floor 免除しうる。
- **PASS 偽造不可を親 verify で実測**: 免除されても宣言 mutant は真に caught される必要があり、文字列/コメント行 mutant は survive→**FAIL**（`verdict: FAIL`・免除ログ `coverage floor exempt ... src/m.py:3-3` を確認）。floor の緩和のみで偽造面積は増えない。
- remediation: py の comment 判定を字句/トークンベース（`tokenize` の COMMENT/NL）へ寄せる＝iter70+ hardening 候補（SF-014 の positive-proof/tokenize 化バケットに同梱）。

## 親 verify（read-only・隔離 clone）

- injection battery の canary 未生成・env override 不発・since arg-injection の DrillError を独立に確認。
- R-1 の pre-existing を差分実走（cbc49e7 vs HEAD）で裏取り。R-2 の PASS 偽造不可を隔離 clone で実測。
- security agent 2体とも本 tree 非汚染（1次は PaC ガードが checkout/rm を拒否したため read-only 版で再走・tree の M は phase=security の STATUS.md と qa 承認生成の test-strength.md=SKIP のみ）。

## 総評

**approve_with_notes。** 本 diff は control-plane（B1 drill）の反ガミング強化で、command/source/git-arg/env の4注入面すべてが fail-closed（canary 実測）、新規脆弱性ゼロ、R4 flag フォージ＋quoting 迂回を実測で閉塞する net moat 改善。residual R-1（非フラグ no-run・pre-existing・SF-014）と R-2（floor 誤免除・Low・PASS 偽造不可）はいずれも非ブロッキングで多層防御＋iter70+ 恒久策で追跡。ブロックは flag 系の穴も残すため ship 推奨。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["1次(opus)・盲検2次(fable・物理隔離 clone)とも新規脆弱性0・approve_with_notes で一致。盲検2次のみ R-2〔floor 内部文字列誤免除・Low・本 diff 由来・PASS 偽造不可〕を追加検出＝親 verify で裏取り済み・iter70+ hardening。SF-014(R-1)の pre-existing 判定は両者独立に一致"]
```
