# 納品サマリー — iteration 70（v1.29.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.29.0（iter70・**MINOR**＝Phase 1 罠の根切り最終項目 1-6。record の引数事前検証・audit_deps の no-manifest 状態追加・judge カードのテストスコープ表示はすべて「制約の追加／新規表示／内部ツールのハードニング」で、既存の正当な運用は不変）
- 日付: 2026-07-15
- 担当者: aegis dev フロー（工程別モデル tiering: 疑う=Fable 5／書く=Opus 4.8。実装=implementer opus・review/security 1次 finder=opus・grill/親verify/盲検2次=fable）
- 操作マニュアル: 不要（record-test-result の使い方は既存の qa-verification skill／03-cheatsheet に集約済み。本 iter は挙動の厳格化＝新規手順なし）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲（全体レビュー §4 Phase 1 項目 1-6 → Phase 1 完遂）

**背景**: Phase 1「罠の根切り」の最終バッチ。全体レビュー R6 罠 n・§R10 gate F6・test #3 が対象。

- **(1) record-test-result 引数事前検証〔罠 n〕**: manual evidence writer が引数を**実行前・記録前**に3段検証。(i) judge と**同一関数**（`_norm_cmd_match`）でテストランナー照合、(ii) 非シェル互換検査（env 代入 prefix `FOO=1 …`／シェル演算子トークン `&& || ; | &`）、(iii) NO_RUN フラグ（`--collect-only` 等）。非該当は usage エラー（rc2・**ログ非書込み・非実行**）。「judge が読めないコマンドは最初から記録させない」＝受理集合を judge の可視集合と単一ソース化。引数事故で判定不能エントリが混入する混乱と、no-run コマンドを manual green として偽装する経路を書込み前に遮断。
- **(2) deps 無 manifest info 降格〔gate F6〕**: `audit_deps` に第4状態 `no-manifest`（依存 manifest がゼロの repo）を追加し、judge は 🟡（要 ack）でなく info 行にする。依存ゼロ repo（aegis 自身を含む）が毎 iteration 抱えていた無意味な ack の踏み車を解消。実依存を宣言する manifest（lockfile 単独・.NET・conda・Deno・CocoaPods・Haskell・sbt・Clojure・Julia・R・Perl・vcpkg・conan・meson・bazel 等 40+ 指標＋`*.csproj`/`*.gemspec`/`*.podspec`/`*.cabal` glob）は `unverified` を維持＝fail-visible。
- **(3) judge カード tests スコープ表示〔test #3〕**: `read_test_result_detail` を抽出し判定と表示を同一走査化。カードの「テスト: green」行に判定源（`src` / `cmd` / `ts`）を付記＝単一ファイル green と full suite green を見分け可能に（fail-visible の欠け解消）。表示は `_sanitize_card_field`（改行・全 Unicode 空白・バッククォート・`#`・120 字切詰）でカード注入を遮断。判定意味論は不変（表示のみ）。

## 変更ファイル

- `scripts/record-test-result.py`（実行前検証3段＝`runner_cmd_matches`／非シェル互換〔`_SHELL_OP_TOKENS`〕／`check_no_run_command`・`_reject` ヘルパ・module docstring に検証契約＋SF-014 残余明記）
- `scripts/build-judge-card.py`（`_norm_cmd_match`/`runner_cmd_matches` 抽出・`audit_deps` no-manifest＋`UNAUDITABLE_MANIFESTS`/`UNAUDITABLE_MANIFEST_GLOBS`・`compute_verdict` info 分岐・`read_test_result_detail`＋`read_test_result` 互換 wrapper・`collect_facts` 拡張・`_sanitize_card_field`＋`render_card` スコープ表示）
- `tests/test_record_test_result.py`（新規9＋fix-forward）／`tests/test_judge_card.py`（audit_deps 網羅・detail・カードスコープ・サニタイズ・ecosystem 回帰）
- `docs/security-followups.md`（SF-014 に record 層 zero-test forge 2実測＋audit_deps 回帰 CLOSED-in-review＋2段 ecosystem 拡張を追記）
- version bump: `check_framework_contract.py`／`docs/STATUS.md`／`templates/STATUS.template.md`（1.28.0→1.29.0）

## 証拠

- 設計: `docs/specs/2026-07-14-iter70-record-guard-judge-card-design.md`（＋brainstorm-record）／計画: `docs/plans/2026-07-14-iter70-record-guard-judge-card-implementation-plan.md`（grill-plan 致命4/要検討4 反映記録付き）
- レビュー: `docs/qa-reports/iter70-review.md`（1次4角度 opus〔仕様=approve/保守性=approve/テスト強度=a_w_n/敵対=a_w_n〕＋盲検2次 fable=approve＋親verify。**敵対が audit_deps 回帰〔Major〕と zero-test forge〔SF-014 同クラス〕を捕捉→回帰は review 内 fix-forward、テスト強度 6 findings もテスト追加で fix-forward**）
- QA: `docs/qa-reports/iter70-qa.md`（fresh 変異 11 種を独立 clone で実走 10/11 KILLED〔唯一の survivor M4 は多層防御 subsumed で安全性健在〕・実環境 E2E 3機能 PASS・full suite 1243 passed／B1 drill は per-task committed で sanctioned skip＋代替実証）
- セキュリティ: `docs/qa-reports/iter70-security.md`（1次 親 harness＋盲検2次 fable 物理隔離 clone・**新規脆弱性0**・command injection を 19 ケースの canary battery で code 実行不成立を実証〔shell なし実行〕・fail-closed 一貫）

## テスト・QA・セキュリティ結果の要約

- full suite: **1243 passed / 2 skipped**（record green・既知 flaky test_update_gate_lock 非顕在）／`check_framework_contract` PASS
- 変異検証: qa fresh 変異 11 種を独立 clone で 10 KILLED（M1-M3 record 検証各段・M5-M8 audit_deps 分岐・M9-M11 detail/サニタイズ）。survivor M4（record shlex→str.split）は step3 check_no_run_command の shlex が同じ不正クォートを捕捉する多層防御で、安全性（不正クォート→fail-closed）は健在
- セキュリティ: command injection 19 ケース（`;`/`&&`/`|`/`&`/`$()`/backtick/`>`/改行/env/quoted/brace/subshell）すべて canary 未生成＝code 実行不成立を 1次・2次独立実測。shell なし実行で payload は runner への不活性引数化。audit_deps 40+ 種で unverified 維持を実測

## 残留リスク・既知の制限事項

- **SF-014（拡張・OPEN・非ブロッキング）**: 反ガミングの列挙 denylist の原理的不完全性。(a) **record 層 zero-test forge**＝`unittest discover -p <nomatch>`（exit 0）や `npm test`→`"test":"true"` は runner 該当かつ0テスト実行で green 記録可能（pre-existing・差分実測で iter70 は accept 集合を狭めた net 改善）。(b) **audit_deps no-manifest denylist 残余**＝未知エコシステムの manifest は誤って no-manifest になりうる（本 iter で 40+ 指標＋glob へ2段拡張し実証済み gap は閉塞・実脆弱性は隠蔽不能＝視認性のみ）。**恒久策=positive「N≧1 テスト実行」proof**（iter71+）。多層防御（judge fp/marker・人手プレビュー）で contained。
- 既存 backlog: SF-011/012/013（Low・pre-existing）。
- 既知 flaky: `test_update_gate_lock`（本 diff 不接触＝回帰外・本 run 全 green）。
- Phase 1 は本 iter で**完遂**（1-1✅iter64／1-2✅iter67／1-3✅iter68／1-4✅iter65／1-5✅iter69／1-6✅iter70）。

## 運用上の注意点

- **`record-test-result.py` の受理が厳格化**: テストランナーコマンド（pytest/unittest/jest/go test 等）のみ受理。非ランナー・no-run フラグ・env 代入 prefix・シェル演算子を含むコマンドは usage エラー（rc2）で**記録もされない**。従来どおり `python3 scripts/record-test-result.py "python3 -m pytest -q"` の形で使う。
- **judge カードの deps 表示**: 依存 manifest ゼロの repo は `依存監査: no-manifest`（info・ack 不要）。依存を宣言する repo は従来どおり `unverified`（🟡・ack 要）。
- **judge カードの tests 行**: `- テスト: green（判定源: src=… / cmd=… / ts=…）` で、どのコマンドの結果かが可視化される。

## プロセス上の注記（透明性）

- 敵対レビュー（opus）が **audit_deps の no-manifest 回帰〔fail-visible→fail-silent〕を捕捉**し review 内で fix-forward、さらに security 盲検2次（fable・物理隔離）が **14 の未収載エコシステムを実証**して2段目の閉塞に繋げた＝独立レビューが moat の網羅性を実測で押し上げた反復。
- record 層・audit_deps の zero-test/no-manifest はいずれも「列挙 denylist の原理的不完全性」という同一クラスで、positive proof（SF-014）が恒久策という理解を差分実測で裏付けた。
