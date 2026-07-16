---
framework: aegis
framework_version: "1.30.0"
project_name: "Aegis"
mode: Dev
phase: brainstorm
task_type: framework
task_size: L
task_size_rationale: "iteration 71（framework・SF-014 恒久策＝marker positive proof 共有 lib 化・record/drill 適用）L 確定（brainstorm Step D）。設計正本: docs/specs/2026-07-15-iter71-marker-positive-proof-design.md（(1) evidence.sh の 4段検証コア〔NO_RUN→STRONG→WEAK pair→zero-run gate〕を hooks/lib/marker.sh に抽出・挙動不変 (2) record-test-result は green 時に verdict 必須＝不成立/評価不能は rc2・ログ非書込〔`unittest discover -p nomatch`／`npm test`→true 偽 green の根治〕・red は marker 不要 (3) drill check_baseline に no-test-proof BLOCKED〔非ランナー import プローブ偽 PASS の根治〕）。footprint: hooks/lib/marker.sh（新規）＋hooks/lib/evidence.sh＋scripts/record-test-result.py＋scripts/run-test-strength-drill.py＋tests 2-3本＝L（6+）。control-plane（反ガミング moat）を触るため review+qa+security 必須・L のため deploy 含む全フェーズ。audit_deps の positive proof（attestation 型・機構別）は iter72 分離起票・marker 覆域拡張は YAGNI（テーマ純度）。"
iteration: 72
ui_surface: false
last_updated: "2026-07-16T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: pending
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: null
  spec: null
  review: null
  qa: null
  security: null
  deploy: null
  translation: null
external_evidence:
  - type: "second-opinion-v1-foundation-r1-r2"
    scope: "future-proof 再アーキ計画 2 ラウンドレビュー（IDE Chat）"
    findings: "R1: 全面再アーキは YAGNI(P1) / manifest は declarative mirror=第3同期先(P1) / emit.sh の python3 deny 依存=fail-open(P1) / inherit 従属 / context 数値撤廃のコスト退行 / TDD off / drift advisory 放置 / Phase F schema 過大 / STATUS 実態 drift。R2: emit.sh コメントで静的テスト自己矛盾(P1) / design doc 旧方針残骸(P2)。"
    resolution: "全面 v1.0.0=NO-GO、emit.sh 中心の縮約 Foundation=条件付き GO。pure-bash emit.sh で fail-open 解消、seed manifest と check-secrets 集約は descope。Foundation を F0/F1/F2 で実装し main にマージ（183 tests green）。"
  - type: "second-opinion-v0130-r5"
    scope: "v0.13.0 計画 5 ラウンドレビュー"
    findings: "Round 1〜5 で計 25 件の指摘（hook 出力スキーマ陳腐化、TaskCreated/Completed 制御方式、Plan 条件付き許可、effort 配分、pre-compact.sh 同種破損、`if` 単一 rule 制約等）"
    resolution: "Rev.5 で全件反映、Phase 0a 即時実装着手 GO。hotfix/v0122-hook-schema ブランチで開始。"
next_action: "**【iter72 着手＝SF-014 恒久策の完結編：passed/failed 実数カウント proof】** rollover 完了（iter71 は v1.30.0 で完全クローズ・push 済 origin/main=1e70fa0・dev ゲート全 pending・iteration=72・非 requirements refs=null）。今回タスク＝SF-014 残余 F-A の根治: marker の出力**マッチ**でなく passed/failed の**実数カウント**（skip 除外・N≧1 実行）を要求する positive proof（unittest all-skip『Ran N tests OK (skipped=N)』／go all-skip『ok pkg dur』の marker=true 偽 green を封鎖）。audit_deps positive proof（attestation 型・機構別）は iter73 分離のまま維持（テーマ純度・iter71 判断踏襲）。**次アクション＝aegis-brainstorm skill に従い brainstorm 実施（→Step D で update-task.sh・その後 plan→grill-plan→implement〔TDD RED-first・書く=opus〕→grill-code→review〔1次4角度=opus→親verify=fable・盲検2次=fable〕→qa→security→（size 次第で deploy）→ship〔bump〕→docs〔LEARNINGS・session_history 追加時 iter69 を evidence-archive 移設＝≤3 維持〕→dev_ready_for_client 申請→push はユーザー判断）**。◆別トラック: audit_deps positive proof（iter73）／rc3 guard 個別条件回帰網（テスト強度 F1）／保守性 minor 2件（命名語彙・record→drill 依存）／SF-011/012/013。◆push=`gh auth switch --user yuuya-miyagaki` 必須（active が tigereye だと 403）。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-16"
    mode: Dev
    phase: "docs"
    note: "iter71 / v1.30.0（marker positive proof＝SF-014 恒久策・**MINOR**＝marker.sh 新規内部 lib＋record accept 集合縮小〔green に marker 必須〕＝運用契約 hardening・後方互換）を全 dev ゲート approved まで完走（L＝deploy 含む全フェーズ）。動機正本＝docs/security-followups.md SF-014／LEARNINGS line148 conf9。設計正本＝docs/specs/2026-07-15-iter71-marker-positive-proof-design.md。実装（session=fable・implementer=opus per-task commit）: evidence.sh の4段検証コア（NO_RUN→STRONG→WEAK pair→zero-run gate）を `hooks/lib/marker.sh` に**逐語移動**（byte 一致・挙動不変）し3消費者（evidence.sh source／record・drill subprocess）が同一実装を使う＋record green 記録前に marker verdict 必須（不成立/評価不能 rc2・ログ非書込・受理 green に additive marker:true）＋drill check_baseline に no-test-proof BLOCKED＋patterns.sh の cross-engine 欠陥修正（go marker `[ \\t]`→リテラル TAB／mocha `0 passing(\\b|$)`→`($|[^a-zA-Z])`＝いずれも BSD grep で非機能の pre-existing 欠陥・両エンジン実測）。plan(grill-plan 致命2〔test_check_status.py TestQaDrillGate 移行漏れ=fail-silent すり替わり／record docstring CLOSED 過大主張→npm-echo 残余〕＋要検討4 反映)→implement(Task1 RED 037545c〔19 failed/88 passed〕→Task2 marker.sh 抽出 12227ac→Task3 drill ec24c83→Task4 record c22bf6c→Task5 SKILL b6551de→docs 層 6125e05/6ce7447)→grill-code(Critical0)→review(1次4角度 finder=opus 全 approve_with_notes＋grill-code＋**親verify が F-A〔unittest/go all-skip suite→marker true→judge green〕を独立実証**＋盲検2次=fable 独立 approve_with_notes＝収束・divergence なし→fix-forward 9dc77b1〔skip-suite 残余記録＋moat 保護 pin TestSkipSuiteResidual/TestWeakPairBoundary/TestMarkerZeroRunParity＋mocha `\\b` 修正〕)→qa(B1 drill=sanctioned skip〔per-task committed〕＋fresh 変異 6/6 KILLED〔独立 clone・対称変異も二層被覆で subsumed〕＋実環境 E2E 4/4 PASS〔nomatch/-q 拒否・正規受理 marker:true・import プローブ BLOCKED〕＋clone baseline 1271 passed)→security(1次 opus＋親in-session＋盲検2次 fable 物理隔離 clone・**新規脆弱性0**・command injection 44 calls 0 成功〔argv＋クォートで shell 再解釈経路ゼロ〕・全経路 fail-closed・新規依存0)→ship(v1.29.0→1.30.0 MINOR・bump 3箇所 7aeed78・TO-CLIENT)→docs(LEARNINGS line148 を iter71 恒久策実装済へ更新＋新3件〔positive proof の粒度限界 conf8・逐語移動 byte 一致 pin conf8・cross-engine parity 覆域が pre-existing 欠陥を摘発 conf8〕)。実装コミット済（037545c〜7aeed78）・未 push。**残存**: SF-014 の record/drill zero-run は CLOSED・**残余 F-A（unittest/go all-skip suite が marker true→green・pre-existing・contained〔drill が subsume〕・自己欺瞞脅威モデル）**＋audit_deps positive proof は iter72 恒久策（passed/failed 実数カウント proof）へ。既知 flaky=test_update_gate_lock（回帰外）。**教訓核**: (1) positive proof も証拠の粒度で破れる＝出力マーカー一致でなく passed/failed 実数カウントまで要求せよ（line148 の次の一手・conf8）。(2) 共有 lib への逐語移動は byte 一致を機械照合で pin し挙動変化を1点に絞れ（conf8）。(3) cross-engine parity テストの覆域を全 regex 配列へ広げると pre-existing の engine 乖離を自動摘発できる（mocha `\\b` を実際に摘発・conf8）。"
  - date: "2026-07-14"
    mode: Dev
    phase: "docs"
    note: "iter69 / v1.28.0（B1 test-strength drill 強化＝全体レビュー §4 Phase 1 項目 1-5・**MINOR**＝.drill 後方互換 optional key since 追加＋no-run/構文/コメント floor の新チェックはすべて制約の追加で既存 spec 不変）を全 dev ゲート approved まで完走（M＝deploy skip・push 手前で停止）。動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §R4・§R6 罠 l,f／LEARNINGS:76,136。設計正本＝docs/specs/2026-07-14-iter69-drill-hardening-design.md。実装（session=fable・implementer=opus per-task commit）: (1) NO_RUN 拒否＝patterns.sh の AEGIS_TEST_NO_RUN_FLAG_REGEX を bash+grep -qE -e で single-source 消費〔evidence.sh と同一エンジン〕(2) mutant 構文検証 pre-pass＝.py compile()／.sh bash -n〔構文破壊 mutant を spec エラー化〕(3) coverage floor からコメント/空行/py docstring のみの連続ラン除外〔混在ラン維持・AST parse 失敗は厳格劣化〕(4) .drill spec key since で反復基点 diff〔ancestor 検証＋report since: 行〕。brainstorm→plan(grill-plan 致命5/要検討4 全反映=RED 証明力メッセージ照合/grep -e 機構化/RED 期待 33 件精密化/TestQaDrillGate 非退行裏取り/CRLF テスト)→implement(Task1 RED 532611c〔32 failed/39 passed〕→Task2 NO_RUN 1f382f2→Task3 構文検証 46cb28c→Task4 floor 除外 87f270e→Task5 since 79cc8f2→Task6 SKILL 同期 ba1a8e5)→grill-code(Critical0・R4 alias バイパス実証＝collectonly/setup-plan/setup-only を denylist 追加 2e851de)→review(1次4角度 finder=opus a_w_n→**盲検2次=fable が F-1〔Critical: shlex quoting で NO_RUN 迂回・偽PASS を E2E 実証〕＋F-2〔Major: fixtures-per-test 漏れ〕を捕捉**→親verify 裏取り→fix-forward 800948b〔検査系を shlex 正規化に統一・回帰5本〕→独立敵対再検証=fable が閉塞確認 a_w_n)→qa(B1 drill=sanctioned skip〔per-task committed＋since フル diff は tests-bulk floor で不成立を実測・別軸〕＋fresh 変異 M1-M6 全KILLED〔独立 clone・baseline 78 passed〕＋since モード E2E＋敵対フォージ battery＋full 1211 passed/2 skipped record green)→security(1次 opus＋盲検2次 fable 物理隔離 clone とも approve_with_notes・**新規脆弱性0**・injection 4面〔command/source/git-arg/env〕fail-closed を canary 実測・deps N/A ack)→ship(v1.27.0→1.28.0 MINOR・bump 3箇所 2a5cfc9・TO-CLIENT)→docs(LEARNINGS: line136 floor 除外を iter69 恒久対応済へ更新＋line146 物理隔離 clone を conf7→8 昇格候補に＋新3件〔検査系/実行系の正規化不整合 conf8・denylist は positive proof で作れ conf8・緩和は不可能要求の削除限定なら moat 不変 conf7〕・SF-014 起票・iter66 を evidence-archive 移設〔≤3 維持〕・docs-sync 整合)。実装コミット済（532611c〜2a5cfc9）・未 push（push=gh auth switch --user yuuya-miyagaki）。**新規起票**: SF-014（NO_RUN は flag 列挙 denylist＝非フラグ no-run コマンド〔python -c import 等〕でフォージ可能・Major-class・OPEN・**pre-existing**〔1次/盲検2次が cbc49e7 差分実走で確定・iter69 は net 改善〕・contained〔多層防御＋人手プレビュー〕・恒久策=iter70+ positive N-tests-executed proof＋R-2 floor 内部文字列誤免除 Low 相乗り）。既知 flaky=test_update_gate_lock（回帰外・全 run 顕在化せず）。**教訓核**: (1) 検査系と実行系が同じ入力を別経路で解釈すると迂回穴＝サニタイズは実行系と同じ正規化で（raw grep vs shlex.split の不整合が Critical・盲検2次のみ捕捉＝独立性の value 定量化・conf8 line147）。(2) 列挙 denylist は原理的に不完全＝反ガミング moat は拒否リストでなく positive proof〔N tests executed〕で作れ（conf8 line148）。(3) 反ガミング機構の緩和は充足不可能な要求の削除に限れば moat を弱めない〔混在ラン維持・免除ラン mutant は survive→FAIL を実測〕（conf7 line149）。"
  - date: "2026-07-15"
    mode: Dev
    phase: "docs"
    note: "iter70 / v1.29.0（framework・Phase 1 罠の根切り最終項目 1-6＝全体レビュー §4／R6 罠 n・§R10 gate F6・test #3・**MINOR**＝record 引数事前検証〔内部ツールの入力厳格化〕＋audit_deps no-manifest 新状態＋judge カード tests スコープ表示はすべて additive／hardening で公開運用契約不変）を全 dev ゲート approved まで完走（M＝deploy skip）。**これで Phase 1 完遂**（1-1✅iter64／1-2✅iter67／1-3✅iter68／1-4✅iter65／1-5✅iter69／1-6✅iter70）。設計正本＝docs/specs/2026-07-14-iter70-record-guard-judge-card-design.md。実装（session=fable・implementer=opus per-task commit）: (1) record-test-result が実行前・記録前に judge と同一関数 `_norm_cmd_match`（→`runner_cmd_matches`）で runner 照合＋非シェル互換（env prefix／`&& || ; | &` トークン）＋`check_no_run_command` の3段検証＝拒否は rc2・ログ非書込み・非実行〔罠 n〕 (2) audit_deps 第4状態 no-manifest（依存ゼロ repo）→judge info 降格・既知 manifest 40+指標＋`*.csproj`/`*.gemspec`/`*.podspec`/`*.cabal` glob は unverified 維持〔gate F6〕 (3) read_test_result_detail 抽出で判定と表示を同一走査化＋カード tests 行に src/cmd/ts＋`_sanitize_card_field`（注入遮断）〔test #3〕。brainstorm→plan(grill-plan 致命4/要検討4 全反映=UNAUDITABLE_MANIFESTS 指標/RED 分布 16件訂正/非シェル互換検査/テスト前提)→implement(Task1 RED 4eb5a51〔16 failed/70 passed〕→Task2 record 検証 04c728a→Task3 audit_deps d8aacd6→Task4 detail+カード a1bf705)→grill-code(Critical0・fix-forward 3de05e7=サニタイズを全 Unicode 空白 positive 正規化に〔U+2028 偽行スプーフ封鎖〕＋manifest 指標6追加)→review(1次4角度 finder=opus〔仕様=approve/保守性=approve/テスト強度=a_w_n/敵対=a_w_n〕→親verify=fable・盲検2次=fable=approve。**敵対が audit_deps no-manifest 回帰〔Major・fail-visible→fail-silent〕を捕捉→review 内 fix-forward b32deb0＋テスト強度6件 8eec7be**)→qa(B1 drill=sanctioned skip〔per-task committed〕＋fresh 変異 11種 10/11 KILLED〔独立 clone・M4 survivor は多層防御 subsumed で安全性健在〕＋実環境 E2E 3機能 PASS＋full 1243 passed record green)→security(1次 親 harness＋盲検2次 fable 物理隔離 clone・**新規脆弱性0**・command injection 19ケース canary battery で code 実行不成立を shell なし実行で実証・**盲検2次が未収載14エコシステムを実証→security 内 fix-forward bbb6e80**・fail-closed 一貫)→ship(v1.28.0→1.29.0 MINOR・bump 3箇所・TO-CLIENT)→docs(LEARNINGS: line148 conf8→9〔denylist 不完全性が record/drill/audit_deps 3系統に跨る・positive proof 根治〕・line146 隔離 clone 3反復目支持で昇格強く推奨＋新2件〔可視→沈黙降格の fail-silent 回帰 conf8・subsumed mutation の切り分け conf7〕・SF-014 に record 層 zero-test forge＋audit_deps 回帰 CLOSED-in-review＋2段 ecosystem 拡張を追記・iter67 を evidence-archive 移設〔≤3 維持〕)。実装コミット済（4eb5a51〜bbb6e80）。**SF 更新**: SF-014 拡張（record 層 zero-test forge〔unittest discover -p nomatch・npm test→true〕＋audit_deps denylist 残余も同バケット・pre-existing・恒久策=positive N-tests-executed proof・iter71+）。既知 flaky=test_update_gate_lock（回帰外・全 run 顕在化せず）。**教訓核**: (1) 反ガミング denylist の原理的不完全性は record/drill/audit_deps に共通＝positive proof が唯一の根治（conf9 line148）。(2) 可視シグナル（🟡）を沈黙（info）へ降格する変更は列挙の穴が fail-visible→fail-silent 回帰になる＝フォールバックは可視側に倒せ（conf8）。(3) 多層防御下の survived mutant は subsumed（別層が捕捉）か真の穴かを実測で切り分ける（conf7）。"
---

## Summary

Claude Code ネイティブの Aegis 運用フレームワーク。2026-06-05、モデル進化（Opus 4.8）
に耐える future-proof 再アーキに着手。v0.13.0 Phase 0b（新 Skill/Cron gate・Task event hook・
スキル aegis-* 改名）を確定後、Foundation を実装: hook 出力スキーマを `hooks/lib/emit.sh` に
単一化（pure-bash・外部依存ゼロ）、破壊パターンを `hooks/lib/patterns.sh` に隔離、version owner
を一本化。挙動不変・183 tests green・main マージ済み（origin 未push）。

## Recent Decisions

- 設計原則を「保証=決定論的強制 / 手順=モデル委譲 / 揮発値=隔離」の 3 層に分解（再アーキの土台）
- emit.sh は pure-bash（python3/jq 非依存）→ deny/block が fail-open しない（Round 2 P1 解決）
- 全面 v1.0.0 再アーキは見送り、emit.sh 中心の Foundation を先行（YAGNI、Round 1）
- seed manifest と check-secrets の patterns 集約は descope（実消費者が出来てから、Round 2 J-1）
- MCP matcher: `mcp__.*__deploy.*` — `push` は除外（通常リモート更新と区別不能）
- Ref チェック: v0.12.0 は DEPRECATION WARNING のみ、v0.13.0 で ERROR 化予定
- Name lint: regex 一本ではなく、ファイル種別ごとの小さい extractor に分割
- Health check: 警告のみ（ブロックなし）、session-start.sh から呼び出し
- Item 3 (Lean/Full プロファイルモード) はセカンドオピニオンにより v0.13.0 に延期

## Session History

> 2026-04 期（v0.7.0〜v0.12.0）の 5 エントリは `docs/evidence-archive.md` に移設（2026-07-12・health 上限 ≤10 維持）。

- 2026-06-05: future-proof 再アーキ着手。Phase 0b 確定 + Foundation（emit.sh 単一出力源 / patterns.sh / version owner）実装。Round 1/2 セカンドオピニオン反映。183 tests PASS、main マージ（未push）。
- 2026-06-06: Phase R 再配分を連続 ship（routing 0.12.3／context 0.12.4／model-effort／name-hygiene／TDD 0.12.5／evidence 完了強制 0.12.6）。続けて Phase D（仕上げ）: migration guide(v0.12.2→v1.0.0)＋README リフレッシュ＋安定契約/SemVer 明文化＋version **1.0.0**。各タスクで brainstorm→2段グリル→実装→grill-code を完走。195 tests green・tier1/2 PASS。**再アーキ F→R→A→D 全完了＝v1.0.0「トレッドミルから降りる」看板を掲示。**
- 2026-06-07: 機能整合性監査（charter 2026-06-07）。Layer 0-4 で 7 finding（P1×1/P2×4/P3×2）全修復。核心 F6（P1）＝setup.sh が hooks/lib を配布せず install 先で moat 全死→copy_hooks 修復＋scaffold smoke の hook 実発火で install 経路を契約化。v1.3.2 patch（298 tests・tag v1.3.2）。
- 2026-06-28: iter52（framework・permission prompt 交通整理＝read-only 完全性ガード＋allow 10→14・M）完了・push 済 origin/main=5660f99。詳細は git log 5660f99。
- 2026-06-29: iter53（framework・破壊的コマンド警告の日本語化＋REGEX↔WARN parity ドリフトガード・M・v1.14.0 据置）完了・push 済 origin/main=69632d0。詳細は git log 69632d0。
- 2026-07-02: iter54（framework・ドッグフード前 Critical バッチ修正・L・v1.14.0→v1.15.0）完了・push 済 origin/main=9a36d72＝完全クローズ。case-insensitive FS の moat バイパス封鎖（条件付き case-fold・deny-only）＋setup.sh fail-open install 封鎖＋drill quotepath。詳細は git log 9a36d72。
- 2026-07-03: iter55 rollover＋設計着手（ドッグフード一周目 FB・許可リスト単一ソース化 scripts-manifest.tsv ほか）→ v1.16.0 完了・push 済 origin/main=9578612。詳細は git log 9578612。
- 2026-07-05: iter56（M2 FB 6件＋可視性・v1.16.0→v1.17.0）完了・push 済 origin/main=584d22c。起票 backlog=docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md。詳細は git log 584d22c。
- 2026-07-06: iter60（framework・budget ratchet policy 見直し＝drift 支配構造の計数除外・M・v1.20.0→v1.21.0）完了・push 済（origin/main=60b1e22 に内包）。budget-exclude 機構＋濫用ガード3重で iter59 headroom-0 解消。⚠security 盲検2次の `git checkout` 事故→snapshot 復旧（→iter61 で機械防御化）。詳細は git log 9ae1f2f/dfc4ce1。
