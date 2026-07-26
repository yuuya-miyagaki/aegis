# QA レポート — iter77（SF-020 case-fold / SF-021 stage エイリアス）
<!-- 正本: qa agent -->

## 対象

- 変更内容: iter77 実装 `ad04973..d4cea18`（check-destructive.sh raw 経路 grep -i 化／check-secrets.sh `_STAGE_BROAD_RE (add|stage)` 拡張＋文言汎化／tests/test_moat_case_fold_stage_alias.py 19 pin）
- 環境: macOS（darwin 25.0.0）・python3 pytest・bash hooks・ローカル（デプロイ非該当）
- ui_surface: false（ブラウザ QA 非該当）

## 機能対照表（要件/plan の機能 → 検証）

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|----------------|---------|---------|------|
| 1 | SF-020 raw 大文字 destructive 封鎖 | check-destructive.sh 4 grep サイト | pin D-1〜D-7b＋敵対 65+ 入力実走 | PASS |
| 2 | SF-020 redirect システムパス大文字 | 同上（同配列 grep） | pin D-3＋`> /ETC`/`/USR` 実走 | PASS |
| 3 | SF-020 safe-artifact 非弱体化 | SAFE_TARGETS sed 非 fold | pin D-5（不変）/D-6（大文字は ask） | PASS |
| 4 | SF-021 stage エイリアス broad 封鎖 | `_STAGE_BROAD_RE` | pin S-1/2/3/5/5b＋敵対実走 | PASS |
| 5 | SF-021 update-index 除外の正当性 | `_STAGE_ENV_RE`（別経路）不変 | `git update-index --add .env`→deny 実走 | PASS |
| 6 | moat 非弱体化 | 既存 pin 全体 | full 1411 passed/削除0/failure0 | PASS |

実装漏れ（検証対象なし）: なし。

## 実施した確認

- [x] 新規 pin スイート実行（19 pin）
- [x] full suite 実行（trusted runner・record）
- [x] contract / drift / doctor 実行
- [x] テスト強度（mutation drill）— since 案の BLOCKED を実測し sanctioned skip＋代替実証
- [x] plan の受入条件と突合（対照表・トレーサビリティ）

## 実行コマンド

```bash
python3 -m pytest tests/test_moat_case_fold_stage_alias.py      # 19 passed
python3 scripts/record-test-result.py "python3 -m pytest"       # recorded: green (1411 passed/2 skipped)
python3 scripts/check_framework_contract.py                     # PASS
python3 scripts/check_reference_drift.py                        # PASS
python3 scripts/status_doctor.py                                # PASS
python3 scripts/run-test-strength-drill.py --root . \
  --spec docs/qa-reports/test-strength.drill --report docs/qa-reports/test-strength.md  # since 案は DRILL BLOCKED → skip へ
```

## 結果

- Pass: 新規 19 pin・full 1411 passed・contract/drift/doctor・moat 非弱体化・敵対バイパス 0 件
- Fail: なし
- Skip: full suite 中 2 skipped（既存の環境依存 skip・本変更由来でない）

## テスト強度（mutation drill）— sanctioned skip＋代替実証

`.drill` は skip 宣言。理由: iter77 は per-task commit 済み framework 改修＝working-tree diff が空になる縁ケース。`since:ad04973` 案は実走で **DRILL BLOCKED** を実測（coverage floor が (a) check-secrets.sh の emit_deny 文言 3 行〔テストが文言を pin しない意図的設計〕・(b) 新規テストファイル全体〔テストコード自体は変異で強度証明できない循環〕に mutant を要求＝framework 混在 diff の構造的不成立・LEARNINGS line33/54）。

代替実証（review フェーズで親 or reviewer が scratchpad コピー側で実走・本体 tree 不接触）:

**差分歯 mutation 6/6 に検知者確立**（元 tree の git status 空を確認済み）:

| 変異（機能追加行を 1 つだけ巻き戻し） | 検知テスト | 判定 |
|---|---|---|
| (a) 本体 rm再帰特例の -i 除去 | D-1/D-2/D-6/D-6b | 歯あり |
| (b) 本体 CMD_REGEX ループの -i 除去 | D-3/D-4a/D-4b | 歯あり |
| (c) fallback rm の -i 除去 | D-7 | 歯あり |
| (d) fallback CMD_REGEX の -i 除去 | **検知者不在→D-7b 追加で封鎖**（再走で FAIL 実証） | 封鎖済 |
| (e) `(add\|stage)`→`add` 巻き戻し | S-1/S-2/S-3/S-5/S-5b | 歯あり |
| (f) treadmill: -i を `(RM\|rm)` 手動 alternation 置換 | D-6b（混在 `Rm -rF`） | 歯あり |

**RED-first**: 現 19 pin を旧実装（ad04973）で実走 → 14 failed / 5 passed（review 盲検2次＋親が独立再現）。

**敵対クラス内バイパス 0 件**: SF-020（大文字/混在/長flag/redirect大文字/fallback）65+ 入力・SF-021（stage alias 全 broad 綴り・case-fold・GIT_PRE_OPTS・難読化）を実 hook 実走。回帰誤検知 0 件。

## Blockers

なし。

## Claims（judge が機械読取する）

```claims
verdict: approve
tests_pass: true
drill: skip (sanctioned; framework per-task-committed edge case; since-run BLOCKED by coverage floor on wording/test hunks; alternative proof = 6/6 differential-tooth mutation caught + 14 RED + adversarial 0-bypass, all in iter77-review.md)
full_suite: 1411 passed / 2 skipped
record: green (marker true, src=manual)
moat_non_weakening: "1395 pre-existing green all maintained + new pins; deletions 0, failures 0"
```

<!-- exit-check: 全チェック実施・結果記入済み → security へ -->
