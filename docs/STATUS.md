---
framework: aegis
framework_version: "1.31.0"
project_name: "Aegis"
mode: Dev
phase: security
task_type: framework
task_size: M
task_size_rationale: "iteration 73（framework・locale/byte-injection 掃討＝deny 側 moat フックの `tr`/`grep` を byte-wise 決定化）M 確定（brainstorm Step D・update-task.sh 経由）。設計正本: docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md／記録: docs/specs/2026-07-18-iter73-locale-byte-sweep-brainstorm-record.md。**実証結論（2026-07-18）**: 支配機構は grep 取りこぼしでなく **`tr` クラッシュ**（不正 UTF-8 バイト→`Illegal byte sequence`→`set -euo pipefail` でフックが rc=1・出力なし→fail-open）。crash は check-destructive.sh・check-secrets.sh の**2本に限定**（実測。runtime-state/deploy-gate は python3 抽出でバイト→空 CMD or tr 前に BSD grep でcrashせず＝同型不成立）。**severity は defensive robustness hardening（脅威モデル内の到達性ゼロ・grill1 で実証・2026-07-19）**＝crash は不正バイトのみ・モデルの command は常に valid UTF-8（Unicode→必ず valid UTF-8）で不正バイト到達不能＝SF-009 と同カテゴリ（next_action の HIGH 仮説を実証格下げ）。**それでも直す**＝(1) 制御フックは任意 stdin でクラッシュしない堅牢性契約〔自前 raw fail-safe fallback 迂回・第3の未定義状態=parse 成功後の下流 crash〕(2) iter72 marker.sh 一貫性 (3) stderr ノイズ除去 (4) forward-looking。修正＝各フックの `CMD=$(extract_command)` 直後に `export LC_ALL=C LC_CTYPE=C LANG=C`（抽出の python3 は inherited locale で UTF-8 fidelity 維持・以降 tr/grep byte-wise・両フックは抽出後 python3 非依存を pin）。footprint: hooks/check-destructive.sh＋hooks/check-secrets.sh＋tests＝M（2-5）。control-plane moat を触るため review+qa+security 必須・M のため deploy skip（iter69 前例）。crash-safe trap 等の構造変更は YAGNI で不採（将来 SF 候補）。"
iteration: 73
ui_surface: false
last_updated: "2026-07-18T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: "docs/plans/2026-07-18-iter73-locale-byte-sweep-implementation-plan.md"
  spec: "docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md"
  review: "docs/qa-reports/iter73-review.md"
  qa: "docs/qa-reports/iter73-qa.md"
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
next_action: "**【iter73 security フェーズ＝1次 opus＋盲検2次 fable 物理隔離 clone】** brainstorm+plan+review+qa approved（refs: design/plan/iter73-review.md/iter73-qa.md）・size M・実装コミット 677b71a〜8be219d。**実証済み位置づけ**: defensive robustness hardening・脅威モデル内到達性ゼロ（crash は不正バイトのみ・モデル command は常に valid UTF-8）。**security で独立再確認すべき点**（review で既に強く実証済みだが攻撃面を変えて再検証）: (1) C-locale narrowing が moat の miss（新 fail-open）を作らないか＝review 盲検2次が Unicode 空白 narrowing（SF-016）を摘発済み・非 exploitable（bash 非 word-split）と実証／他の narrowing が無いか (2) PEP 540 劣化が fail-safe (3) command injection 経路ゼロ (4) 新規依存ゼロ。**次アクション＝security（1次=opus・盲検2次=fable 物理隔離 clone）→統合 verdict→（M ゆえ deploy skip）→ship〔v1.31.0→bump〕→docs〔LEARNINGS・SF-016・session_history・iter70 archive 移設〕→dev_ready_for_client 申請→push はユーザー判断**。◆iter73 クローズ後: Fable+Codex 二重網羅レビュー。◆push=`gh auth switch --user yuuya-miyagaki` 必須（active が tigereye だと 403）。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-18"
    mode: Dev
    phase: "docs"
    note: "iter72 / v1.31.0（framework・SF-014 完結編＝marker positive proof のカウント化・**MINOR**＝Stage5 count proof で accept 集合縮小〔all-skip green 不成立〕＋偽陰性修正で正当 green 受理拡大・後方互換）を全 dev ゲート approved まで完走（M＝deploy skip）。動機正本＝docs/security-followups.md SF-014／LEARNINGS line148 conf9。設計正本＝docs/specs/2026-07-16-iter72-count-proof-design.md。実装（session=fable・implementer=opus per-task commit）: `aegis_marker_verdict` に Stage5 count proof 追加＝count 族（unittest/pytest/jest/vitest/cargo/go-v）サマリ検出時に executed=passed+failed（skip 除外）≧1 を要求（`AEGIS_TEST_COUNT_FAMILIES` を patterns.sh 単一ソース化）→unittest all-skip〔`Ran N OK (skipped=N)`〕と go-v all-skip〔`--- SKIP` のみ〕を CLOSED＋cargo doc-tests 空/jest skipped 混在/vitest インデントの pre-existing 偽陰性を修正（verdict IF 不変＝3消費者無改修）。plan(grill-plan Rev.2 致命3〔RED 10件精密化/hybrid forge residual pin/算術 overflow cap〕反映)→implement(Task1 RED 5e10163〔正確に10 failed/34 passed〕→Task2 GREEN be77a85→Task3 record 文書 617a5c4→Task4 SF/SKILL 925a8ae)→**review(1次4角度=opus＋公式 code-review workflow〔high・16agent〕＋親verify=fable＋盲検2次=fable。摘発: false-GREEN 1件〔F-2 vitest all-skip アンカー緩和の副作用で iter71 false→iter72 true 反転〕/false-negative 2件〔F0 unittest MINUS 無アンカー過剰減算・F1 pytest DETECT banner 誤検出 cross-family veto〕/fail-open 3件〔F5/F6/M-1 grep rc 判別〕/moat pin 欠落〔強度F-1 TAB parity〕→fix-forward 2ラウンド fa97241/8e9d589/06b4556・盲検2次は fix 後 新規false-GREEN/negative ゼロ実測で収束)**→qa(B1 drill sanctioned skip〔per-task committed〕＋独立 clone fresh 変異 8/8 KILLED〔**M6=strict field-count guard 無 pin を qa が摘発→pin 追加 e989bcf で是正**〕＋実環境 E2E 6/6＋clone baseline 1290 passed)→**security(1次 opus=approve＋**盲検2次 fable 物理隔離 clone=**reject で High 級 moat bypass〔F-CRIT-1〕摘発**＝UTF-8 locale 下で test 出力サマリ行末に1バイト付与→grep 抽出破綻で Stage5 skip 減算とりこぼし〔all-skip unittest→true・iter72〕＋Stage4 zero-run veto とりこぼし〔forged strong+collected0+byte→true・**iter71 由来 pre-existing**〕の false-GREEN→security 内 fix-forward 90b4b61〔関数冒頭 LC_ALL=C で全 grep byte-wise 決定化〕で CLOSED・pin 2本〔pre-fix で true 再現の非空検証〕・divergence=F-CRIT-1→fix で収束・approve 統合〔--ack〕・injection 0/44・secrets/deps 0)**→ship(v1.30.0→1.31.0 MINOR・bump 3箇所 29cc883・TO-CLIENT)→docs(LEARNINGS line148 に iter72 count proof 追記＋新 conf8〔grep moat は locale 依存＝LC_ALL=C で byte-wise・moat テストは非 ASCII 入力必須・独立レビュー value 4例目〕・SF-014 に iter72 適用＋F-CRIT-1 記録・SF-015 起票・iter69 を evidence-archive 移設〔≤3 維持〕・docs-sync 整合)。実装コミット済（5e10163〜90b4b61＋ship/docs）。**残存**: SF-014 (a)echo/(b)素go all-skip/(c)unittest skip レポータ抑止＝marker 層の原理的天井・drill subsume・恒久策=execution attestation〔iter73+〕。SF-015（pytest all-xfail 偽陰性・pre-existing・Low・fail-closed）。既知 flaky=test_update_gate_lock（回帰外）。**教訓核**: (1) positive proof も証拠の粒度で破れる＝マーカーマッチでなく実行数の算術（skip 除外 count）まで踏み込め・出力ベース proof の床は attestation でしか塞げない（line148 conf9 追補）。(2) grep ベース control-plane は locale 依存＝敵対出力に1バイトで UTF-8 下 false-GREEN＝`LC_ALL=C` で byte-wise 固定・moat 回帰テストは非 ASCII/生バイト入力を含めよ（conf8 新規）。(3) 1次(opus)=approve と盲検2次(fable 物理隔離)=reject の divergence こそ High 級バグの在処＝攻撃面を変える独立レビューの value 4例目（既存 50 pin が全 ASCII で review/qa/1次sec が見落とした）。"
  - date: "2026-07-16"
    mode: Dev
    phase: "docs"
    note: "iter71 / v1.30.0（marker positive proof＝SF-014 恒久策・**MINOR**＝marker.sh 新規内部 lib＋record accept 集合縮小〔green に marker 必須〕＝運用契約 hardening・後方互換）を全 dev ゲート approved まで完走（L＝deploy 含む全フェーズ）。動機正本＝docs/security-followups.md SF-014／LEARNINGS line148 conf9。設計正本＝docs/specs/2026-07-15-iter71-marker-positive-proof-design.md。実装（session=fable・implementer=opus per-task commit）: evidence.sh の4段検証コア（NO_RUN→STRONG→WEAK pair→zero-run gate）を `hooks/lib/marker.sh` に**逐語移動**（byte 一致・挙動不変）し3消費者（evidence.sh source／record・drill subprocess）が同一実装を使う＋record green 記録前に marker verdict 必須（不成立/評価不能 rc2・ログ非書込・受理 green に additive marker:true）＋drill check_baseline に no-test-proof BLOCKED＋patterns.sh の cross-engine 欠陥修正（go marker `[ \\t]`→リテラル TAB／mocha `0 passing(\\b|$)`→`($|[^a-zA-Z])`＝いずれも BSD grep で非機能の pre-existing 欠陥・両エンジン実測）。plan(grill-plan 致命2〔test_check_status.py TestQaDrillGate 移行漏れ=fail-silent すり替わり／record docstring CLOSED 過大主張→npm-echo 残余〕＋要検討4 反映)→implement(Task1 RED 037545c〔19 failed/88 passed〕→Task2 marker.sh 抽出 12227ac→Task3 drill ec24c83→Task4 record c22bf6c→Task5 SKILL b6551de→docs 層 6125e05/6ce7447)→grill-code(Critical0)→review(1次4角度 finder=opus 全 approve_with_notes＋grill-code＋**親verify が F-A〔unittest/go all-skip suite→marker true→judge green〕を独立実証**＋盲検2次=fable 独立 approve_with_notes＝収束・divergence なし→fix-forward 9dc77b1〔skip-suite 残余記録＋moat 保護 pin TestSkipSuiteResidual/TestWeakPairBoundary/TestMarkerZeroRunParity＋mocha `\\b` 修正〕)→qa(B1 drill=sanctioned skip〔per-task committed〕＋fresh 変異 6/6 KILLED〔独立 clone・対称変異も二層被覆で subsumed〕＋実環境 E2E 4/4 PASS〔nomatch/-q 拒否・正規受理 marker:true・import プローブ BLOCKED〕＋clone baseline 1271 passed)→security(1次 opus＋親in-session＋盲検2次 fable 物理隔離 clone・**新規脆弱性0**・command injection 44 calls 0 成功〔argv＋クォートで shell 再解釈経路ゼロ〕・全経路 fail-closed・新規依存0)→ship(v1.29.0→1.30.0 MINOR・bump 3箇所 7aeed78・TO-CLIENT)→docs(LEARNINGS line148 を iter71 恒久策実装済へ更新＋新3件〔positive proof の粒度限界 conf8・逐語移動 byte 一致 pin conf8・cross-engine parity 覆域が pre-existing 欠陥を摘発 conf8〕)。実装コミット済（037545c〜7aeed78）・未 push。**残存**: SF-014 の record/drill zero-run は CLOSED・**残余 F-A（unittest/go all-skip suite が marker true→green・pre-existing・contained〔drill が subsume〕・自己欺瞞脅威モデル）**＋audit_deps positive proof は iter72 恒久策（passed/failed 実数カウント proof）へ。既知 flaky=test_update_gate_lock（回帰外）。**教訓核**: (1) positive proof も証拠の粒度で破れる＝出力マーカー一致でなく passed/failed 実数カウントまで要求せよ（line148 の次の一手・conf8）。(2) 共有 lib への逐語移動は byte 一致を機械照合で pin し挙動変化を1点に絞れ（conf8）。(3) cross-engine parity テストの覆域を全 regex 配列へ広げると pre-existing の engine 乖離を自動摘発できる（mocha `\\b` を実際に摘発・conf8）。"
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
