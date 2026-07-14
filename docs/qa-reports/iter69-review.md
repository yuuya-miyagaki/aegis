# iter69 review — B1 drill 強化（NO_RUN 拒否＋mutant 構文検証＋コメントラン floor 除外＋since baseline）

- 対象 diff: `git diff cbc49e7..HEAD`（4ファイル・+625/-12）
- 設計正本: docs/specs/2026-07-14-iter69-drill-hardening-design.md
- 計画正本: docs/plans/2026-07-14-iter69-drill-hardening-implementation-plan.md
- レビュー構成: 1次（reviewer・opus・4角度）→ 親 verify（fable・in-session・隔離 clone 実証）→ 盲検2次（reviewer-maintainability・fable・独立）→ **fix-forward 後の敵対再検証（reviewer・fable・独立）**
- verdict: **approve_with_notes**（1次=approve_with_notes / 盲検2次=**reject→fix後 approve_with_notes** / fix 敵対再検証=approve_with_notes / 親 verify=approve_with_notes に収束）
- **本 review の最重要成果**: 盲検2次が本反復の看板「R4 no-run フォージ閉塞」を破る **F-1 [Critical]（shlex quoting 迂回）** を E2E 実証。親 verify で裏取り→ fix-forward（`800948b`）→ 独立敵対再検証で閉塞確認。独立レビューが実効を出した典型。

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 状態 | commit |
|---|------------|------------|------|--------|
| 1 | RED — 失敗テスト先置き | tests/test_test_strength_drill.py | 完了（33 件 RED→GREEN） | 532611c |
| 2 | NO_RUN 拒否（single-source 消費） | scripts/run-test-strength-drill.py | 完了 | 1f382f2 |
| 3 | mutant 構文検証 pre-pass | scripts/run-test-strength-drill.py | 完了 | 46cb28c |
| 4 | コメント/docstring ラン floor 除外 | scripts/run-test-strength-drill.py | 完了 | 87f270e |
| 5 | since baseline＋report `since:` 行 | scripts/run-test-strength-drill.py | 完了 | 79cc8f2 |
| 6 | qa-verification SKILL.md 同期 | .claude/skills/qa-verification/SKILL.md | 完了 | ba1a8e5 |
| G | grill-code fix-forward（NO_RUN denylist 3エイリアス） | hooks/lib/patterns.sh, tests/ | 完了 | 2e851de |
| R | review 盲検2次 fix-forward（shlex 正規化＝F-1 Critical・fixtures-per-test＝F-2 Major） | run-test-strength-drill.py, patterns.sh, tests/ | 完了 | 800948b |

未着手タスク: なし。

## 受入条件6項目 充足マトリクス（1次＋親 verify）

| # | 受入条件 | 判定 | 根拠 |
|---|---------|------|------|
| 1 | collect-only 系は実 patterns.sh 消費で BLOCKED（R4 封鎖・E2E 実証） | 満たす | E2E test_collect_only_command_blocked_e2e＋grill 追加分 collectonly/setup-plan/setup-only の E2E ピン。隔離 clone でフォージ3件 BLOCKED 実測 |
| 2 | 構文破壊 mutant を baseline 前に全件列挙 BLOCK・構文保存/未知ext/parse不能元は素通り | 満たす | syntax_check_mutants・clone で py/sh 破壊 BLOCK＋drift/未知ext skip 実測 |
| 3 | コメント/空行/py docstring のみの連続ランは floor 免除・混在ラン維持・None は従来挙動 | 満たす | non_coverable_lines＋anti_gaming 拡張・混在ラン floor 維持を実測・None 経路テスト有 |
| 4 | spec key since で反復基点 diff・非ancestor/不明refは BLOCK・report に since: 行・省略時完全不変 | 満たす | resolve_since_ref＋write_report 拡張・E2E 3件・全4経路 since threading |
| 5 | 全 pre-check fail-closed（新 fail-open 分岐ゼロ・新例外型ゼロ） | 満たす | 新例外型なし（全 DrillError 集約）・NO_RUN/since/syntax 全失敗経路 fail-closed・floor 計算失敗は厳格化劣化 |
| 6 | full suite GREEN・contract aligned・SKILL 同期・budget PASS | 満たす | 1206 passed/2 skipped・contract aligned・SKILL 同期・budget 違反なし |

## fix-forward した blocking findings（盲検2次・実証→修正→再検証）

### F-1 [Critical→CLOSED] NO_RUN が shlex quoting で迂回可能（偽 PASS を E2E 実証）

- run-test-strength-drill.py:62-90（check_no_run_command）と :491（_execute の shlex.split）の**正規化不整合**。検査系は raw 文字列を grep、実行系は `shlex.split` 後の argv を走らせる。`pytest "--collect-only"`（引用符2文字）は境界 regex `(^|[[:space:]])` に不一致で通り抜け、shlex 後は bare `--collect-only`＝0テスト。import-crash mutant（構文正当→構文検証も素通り）と組んで **verdict PASS・0テスト実行の偽 DRILL PASS を親 verify が隔離 clone で再現**。
- **修正（`800948b`）**: 検査系を実行系と同じ `shlex.split` 正規化に統一（argv join を authoritative・生文字列も defense-in-depth で併検査・クォート不整合は fail-closed）。
- **fix 敵対再検証（独立・fable）**: quoted（single/double）・隣接連結・タブ/改行同梱・`--`以降・case/全角・略記・`=`付き・env プレースホルダの**全迂回ベクトルが BLOCKED**、差分実測で PRE=fake-pass→POST=blocked、過剰ブロックなし・回帰なし。回帰テスト5本追加（`test_quoted_flag_rejected_via_shlex_norm`・`test_real_patterns_rejects_quoted_collect_only`・`test_unparseable_quoting_fail_closed`・`test_real_patterns_rejects_fixtures_per_test`・E2E `test_quoted_collectonly_forge_blocked_e2e`）。

### F-2 [Major→CLOSED] `--fixtures-per-test` denylist 漏れ＋コメント事実誤認

- patterns.sh のコメントが `--fixtures-per-test` を「テスト本体を走らせる」と誤記していたが、実測（`pytest --X -s` の body マーカー0）で **0テスト＝no-run**。denylist にも漏れ。
- **修正（`800948b`）**: `fixtures-per-test` を denylist に追加。コメントを実測事実に訂正（`--setup-show`=body 実行〔denylist 対象外〕／`--fixtures-per-test`=body 非実行〔対象〕を `pytest --X -s` で確認）。

## findings（残余・全て Minor/Info・非ブロッキング）

以下は fix 後に残る Minor/Info。親 verify で各々を裏取りした結論を併記する。

### 敵対（moat）— 親 verify で実証裏取り済み

- **[Major-class・pre-existing→SF-014] 非フラグ no-run コマンドはフォージ可能**（run-test-strength-drill.py:62）。fix 敵対再検証が `python3 -c "import src.m"`（テストランナーですらないコマンド）＋import-crash mutant で **偽 DRILL PASS を隔離 clone で実測**。**親 verify で pre-existing 確定**: cbc49e7（iter69 の NO_RUN 機能導入前）でも同一偽 PASS＝iter69 は net 改善・回帰ゼロ。NO_RUN は flag 列挙 denylist の構造上、非ランナーコマンドを判定できない。恒久策＝positive「N tests executed」proof（iter70+）。**SF-014 起票・本 gate 非ブロック**（脅威モデル＝自己欺瞞・qa の test_command 人手プレビュー・patterns.sh コメント文書化済み）。

- **[Minor conf8] NO_RUN denylist は列挙式で本質的に不完全**（patterns.sh:188 / run-test-strength-drill.py:62-90）。1次が「`--trace-config`・`-k nonexistent`・`go test -run xxx` が allowed に通る」と指摘。**親 verify（隔離 clone 実測）**: (i) `-k nonexistent` は 0 テスト→pytest exit 5→baseline 非green→**BLOCKED**（フォージ不成立）、(ii) `--trace-config` は実際にテストを走らせる＝no-run でない→挙動 mutant は実アサーションが判定（偽 PASS 不成立）。実在するフォージ族（collect-only 系＋import-crash mutant）は grill-code で denylist に collectonly/setup-plan/setup-only を実証追加し閉塞。**残余＝未知の将来エイリアス**は多層防御（anti-gaming(a)・baseline-green 要求・mutant survival）で contained。恒久 fix＝positive "N tests executed" proof（iter70+ 候補・patterns.sh コメント 179-187 に明記）。
- **[Minor conf8] since 恣意選択の残存リスク**（run-test-strength-drill.py:326-352）。古い基点を選び強い変更を基点前に押し込めば弱テスト hunk だけを drill 対象化できる理論経路。ancestor 検証（非祖先 BLOCK 実測）＋report `since:` 行明記（全4経路 threading 実測）＋人手レビューで軽減。設計 R6「軽減可」分類どおり受容。省略時挙動は完全不変（実測）。

### テスト強度 — 親 verify 済み

- **[Minor conf8] `_parses` の未知拡張子 `return None` 分岐は到達不能（equivalent mutant）**（run-test-strength-drill.py:113）。`_parses` は `syntax_check_mutants` からのみ呼ばれ、呼出前に `_SYNTAX_CHECKED_SUFFIXES` でフィルタ済み＝production で未知ext は届かない。変異 survived だが equivalent。line147 は `is False` 判定で True 返却でも BLOCK しない（安全側）。**無対応（dead-defensive）**。
- **[Minor conf7] `_docstring_lines` の `end_lineno is not None` ガードが未テスト**（run-test-strength-drill.py:420）。CPython `ast.parse` は常に end_lineno 付与＝到達困難な防御コード。変異 survived だが実害なし。**無対応**（厳密化するならモック test 1件）。
- **[Minor conf6] `syntax_check_mutants` の precondition skip をテストが理由まで区別しない**（盲検2次 F4）。parse 不能 skip と拡張子対象外 skip を区別しないゆるい assert。precondition skip は fail-closed でなく別経路（apply_mutant drift 検査・baseline red）が受ける設計。**無対応**（統合テスト追加は任意）。

### 保守性 — 記録

- **[Minor conf7] floor 免除の透明化 print が anti_gaming と subset 判定を重複**（run-test-strength-drill.py:653-661）＝**1次(4-1)・盲検2次(F5) の収束シグナル**。同じ `_contiguous_runs`＋`set(run) <= exempt` を2箇所で計算。現状は同一 `exempt` dict を両者に渡すため**論理的乖離は起きない**（同入力・同述語）。リスクは将来の maintenance drift のみ。**follow-up リファクタ候補**（anti_gaming が免除ランも返す設計に）＝iter70+ の maintenance。今回は動作正・両レビューとも非ブロッキング判定。
- **[Minor conf6] `check_no_run_command` の bash script 文字列連結・rc=3 多重化**（run-test-strength-drill.py:73-90）。source 失敗と regex 未定義が同じ rc=3。コメント 71-72＋docstring が意図を伝達。単一 subprocess で意味論ドリフト防止＝設計判断妥当。**無対応**。
- **[Minor conf8] rc≠1 fail-closed は到達困難だが安全側の保険**（盲検2次 F1・run-test-strength-drill.py:87-90）。regex 未定義/patterns.sh 不在は先行チェックで捕捉済みのため rc=2 は稀。将来 regex 破損時の保険として機能。**無対応**。

## 仕様準拠

- 承認時経路（check_status.py::run_qa_drill 固定 argv）・不変対象（check_status.py / update-gate.sh / build-judge-card.py）は diff に含まれず無改修を確認。
- patterns.sh の3エイリアス追加は計画 Global Constraints「patterns.sh は消費のみ」の文面から外れるが、grill-code で実証したフォージ閉塞のための意図的 moat 強化であり single-source 原則（evidence.sh と drill が同一 regex 共有）を保存＝逸脱でなく設計意図の完遂。
- 勝手な追加実装なし。

## 親 verify の独立実測（read-only・隔離 clone）

- フォージ3族（collectonly/setup-plan/setup-only ＋ import-crash mutant）→ 全て BLOCKED。
- `-k nonexistent`→baseline 非green BLOCK／`--trace-config`→テスト実走（no-run でない）を切り分け実証。
- 正常 pytest コマンドは NO_RUN を素通り（over-block なし）。
- レビュー2エージェントとも tree 非汚染（`git status` は phase 遷移の STATUS.md のみ）。

## 総評

**approve_with_notes（fix-forward 後の状態に対して）。** 4新機能はいずれも fail-closed 方向で実装され、設計の「新 fail-open 分岐ゼロ」を満たす。盲検2次が本反復の看板を破る **F-1 Critical（shlex quoting 迂回）** と **F-2 Major** を E2E 実証したが、親 verify で裏取りののち fix-forward（`800948b`・shlex 正規化統一＋denylist 追加＋回帰5本）で閉塞し、独立敵対再検証で「あらゆる列挙フラグ迂回で偽 PASS 不成立・過剰ブロックなし・回帰なし」を確認。fix 後の残 findings は全て Minor/Info。唯一の Major-class 残余（非フラグ no-run コマンドのフォージ）は差分実測で **pre-existing 確定（iter69 は net 改善）** ＝ SF-014 起票・多層防御＋人手プレビュー＋文書化で contained・本 gate 非ブロック。iter69 は R4 の flag 系フォージを閉じる純粋な moat 強化であり、ship すべき（ブロックは flag 系の穴も残す）。

**notes（qa/security への申し送り）:**
1. **SF-014**（Major-class・pre-existing）: NO_RUN は flag 列挙 denylist ＝非フラグ no-run コマンド（`python3 -c "import m"` 等）はフォージ可能。恒久策＝positive「N tests executed」proof（iter70+）。
2. floor 免除の透明化 print が anti_gaming と subset 判定を重複（1次4-1／盲検2次F5／初回盲検F5 の収束）→ iter70+ リファクタ候補。
3. `_docstring_lines` の end_lineno None ガード・`_parses` None 分岐は未テスト（到達困難／equivalent）。
4. line-comment 判定が triple-quote 非docstring 文字列/heredoc 内部を誤免除しうる（偽 PASS 非直結・floor 緩和のみ）。

```claims
tests_pass: true
no_stubs: true
verdict: approve_with_notes
second_opinion:
  verdict: reject_resolved
  divergence_points: ["盲検2次が F-1[Critical: shlex quoting で NO_RUN 迂回]＋F-2[Major: fixtures-per-test 漏れ]を E2E 実証し reject。1次(opus)と初回 verify は見落とし＝独立性が Critical を捕捉。親 verify で裏取り→fix-forward(800948b)→独立敵対再検証で閉塞確認、verdict は approve_with_notes に収束。残 divergence は非フラグ no-run フォージ(SF-014)の扱いのみ＝pre-existing/非ブロッキングで全員一致"]
```
