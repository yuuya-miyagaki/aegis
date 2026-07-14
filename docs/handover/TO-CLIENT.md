# 納品サマリー — iteration 69（v1.28.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.28.0（iter69・**MINOR**＝B1 drill 強化。`.drill` に後方互換 optional key `since` 追加＋no-run/構文/コメント floor の新チェックはすべて「制約の追加」＝既存の正当な drill spec は不変で通る）
- 日付: 2026-07-14
- 担当者: aegis dev フロー（工程別モデル tiering: 疑う=Fable 5／書く=Opus 4.8。実装=implementer opus・review/security 1次=opus・grill/親verify/盲検2次=fable）
- 操作マニュアル: 不要（qa-verification skill に利用手順を同期済み＝`since`/no-run 拒否/構文検証/floor 除外）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲（B1 test-strength drill 強化＝全体レビュー §4 Phase 1 項目 1-5）

**背景**: B1 drill は qa gate 承認時に「テストが弱いバグを見逃さないか」を live 検証する反ガミング機構（moat）。全体レビュー R4 が、`pytest --collect-only` のような**テストを1件も実行しないコマンド**＋構文破壊 mutant で「アサーション0のまま DRILL PASS」を偽造できる穴を実証していた。加えて罠 l（純コメント/docstring 孤立ハンクが coverage floor を不成立にし sanctioned skip を強制）と罠 f（per-task コミットで `git diff HEAD` 空になり drill 不成立）が起票済みだった。

- **(1) NO_RUN 拒否**: `.drill` の test_command が no-run フラグ（`--collect-only` 等）を含むと承認時に BLOCK。判定は evidence.sh と**同じ single source**（`hooks/lib/patterns.sh` の `AEGIS_TEST_NO_RUN_FLAG_REGEX`）を同じエンジン（bash grep -E）で消費＝意味論ドリフトゼロ。
- **(2) mutant 構文検証**: mutant 適用後の全文が構文検査（.py→`compile()`／.sh→`bash -n`）を通ることを baseline 実行前に要求。構文破壊 mutant は spec エラーとして全件列挙 BLOCK（＝「parse エラーで red」を「テストが捕まえた」と偽れない）。
- **(3) コメント/docstring ラン floor 除外**: coverage floor から「コメント/空行/py docstring のみの連続ラン」を自動除外（罠 l 解消）。除外は**充足不可能な要求の削除のみ**——コード行を含む混在ランは floor 維持で偽造面積は増えない。
- **(4) `since` baseline モード**: `.drill` に optional key `"since": "<基点sha>"` を置くと基点以降の committed 変更を drill 対象化（罠 f 解消）。基点は HEAD の祖先必須（非祖先は BLOCK）・report の `since:` 行に記録＝監査可能。CLI flag でなく spec key なのは承認時経路（`run_qa_drill`）が固定 argv のため。

## 変更ファイル

- `scripts/run-test-strength-drill.py`（新規: `check_no_run_command`／`syntax_check_mutants`+`_parses`／`non_coverable_lines`+`_docstring_lines`+`LINE_COMMENT_TOKENS`／`resolve_since_ref`。拡張: `parse_spec`(since 検証)／`anti_gaming_violations`(exempt_lines)／`write_report`(since 行)／`run_drill`(配線)）
- `hooks/lib/patterns.sh`（NO_RUN denylist に実証済みエイリアス追加: `collectonly`/`setup-plan`/`setup-only`/`fixtures-per-test`＋恒久策コメント）
- `tests/test_test_strength_drill.py`（新規テスト群＋fix-forward 回帰5本）
- `.claude/skills/qa-verification/SKILL.md`（since/NO_RUN/構文検証/floor 除外の利用手順を同期）
- version bump: `check_framework_contract.py`／`docs/STATUS.md`／`templates/STATUS.template.md`（1.27.0→1.28.0）

## 証拠

- 設計: `docs/specs/2026-07-14-iter69-drill-hardening-design.md`（＋brainstorm-record）／計画: `docs/plans/2026-07-14-iter69-drill-hardening-implementation-plan.md`（grill-plan 致命5/要検討4 反映記録付き）
- レビュー: `docs/qa-reports/iter69-review.md`（1次4角度 opus＋盲検2次 fable。**盲検2次が F-1〔Critical: shlex quoting で NO_RUN 迂回〕＋F-2〔Major: fixtures-per-test 漏れ〕を E2E 実証→fix-forward→独立敵対再検証で閉塞確認**）
- QA: `docs/qa-reports/iter69-qa.md`（fresh 変異 M1-M6 全 KILLED〔独立 clone〕・since モード E2E・敵対フォージ battery・full suite 1211 passed／B1 drill は tests-bulk floor で sanctioned skip＝実測根拠付き＋代替実証）
- セキュリティ: `docs/qa-reports/iter69-security.md`（1次 opus＋盲検2次 fable 物理隔離 clone とも approve_with_notes・**新規脆弱性0**・injection 4面〔command/source/git-arg/env〕fail-closed を canary 実測）

## テスト・QA・セキュリティ結果の要約

- full suite: **1211 passed / 2 skipped**（record green・以降 docs のみ＝fp 不変）／`check_framework_contract` PASS
- 変異検証: qa fresh 変異 M1-M6（NO_RUN rc 判定/shlex 正規化退行/構文検証 is-False/since ancestor/floor subset/コメント検出）を独立 clone で全 KILLED
- 敵対検証: R4 flag フォージ＋**quoting 迂回**（引用符/隣接連結/タブ改行/`--`/case/全角/略記/`=`/env）すべて BLOCKED・偽 PASS ゼロ・過剰ブロックなし（差分実測 PRE=fake-pass→POST=blocked）

## 残留リスク・既知の制限事項

- **SF-014**（新規起票・OPEN・Major-class・**pre-existing**・非ブロッキング）: NO_RUN は flag 列挙 denylist のため、非フラグ no-run コマンド（`python3 -c "import m"`／`go test -list` 等）＋import-crash mutant で偽 DRILL PASS が依然可能。差分実測（cbc49e7〔iter69 の NO_RUN 導入前〕でも同一偽 PASS）で pre-existing 確定＝iter69 は net 改善。恒久策＝iter70+ の positive「N tests executed」proof。相乗り追跡: floor 免除が複数行文字列内部の `#` 行を誤免除しうる（Low・本 diff 由来・**PASS 偽造不可**を実測）。
- 繰延（Phase 1 残）: iter70=1-6（record-test-result 引数事前検証／deps 無 manifest info 降格／judge カード tests スコープ表示）＝Phase 1 完遂。SF-011/012/013（既存 backlog・Low・pre-existing）。
- 既知 flaky: `test_update_gate_lock`（本 diff 不接触＝回帰外・本 run 全 green）。

## 運用上の注意点

- **`.drill` の書き方が広がった**: (a) test_command に no-run フラグ（`--collect-only` 等）は使えない（承認時 BLOCK）。(b) mutant は構文を保って意味を変える（構文破壊は spec エラー）。(c) per-task コミット済みで `git diff HEAD` が空になった反復は、skip でなく `"since": "<基点sha>"` で基点以降の committed 変更を drill 対象化できる（基点は HEAD 祖先必須）。(d) コメント/空行/docstring だけのハンクは floor から自動除外（mutant 配置不要・承認ログに免除ランが明示）。詳細は qa-verification skill に同期済み。
- ただし本 iter 自身の qa は、全反復 diff が tests ハンク主体で coverage floor が構造的に不成立のため sanctioned skip＋代替実証（fresh 変異 6/6 KILLED）を採った（`since` は罠 f＝空 diff を解くが、tests-bulk floor は別軸の既知エッジ）。

## プロセス上の注記（透明性）

review で 1次（opus・4角度）と初回 verify が見落とした **Critical（shlex quoting で NO_RUN 迂回）を盲検2次（fable・独立）が E2E 実証**し、fix-forward で閉塞できた。独立レビューの価値が定量的に出た反復。security も 1次/盲検2次とも新規脆弱性0・injection 全 fail-closed を canary で実測。
