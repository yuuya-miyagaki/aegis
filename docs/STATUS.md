---
framework: aegis
framework_version: "1.26.1"
project_name: "Aegis"
mode: Dev
phase: qa
task_type: framework
task_size: M
task_size_rationale: "iteration 67（framework・judge test-fact 判定堅牢化）M 確定（brainstorm Step D・update-task.sh 経由）。設計正本: docs/specs/2026-07-12-iter67-judge-test-fact-robustness-design.md（trust-scan＝read_test_result の走査で undecidable〔observed かつ marker_verified≠true〕かつ status=ok のエントリを情報ゼロ＝透明として skip・判定は最新 decidable〔manual／observed+marker=true〕が下す。undecidable-fail 終端 unverified・fp 不一致終端・decidable ゼロ→unverified は不変＝C-2/K-1/fp backstop 無緩和。red 洗浄経路〔decidable red 後の no-run コマンドで red→🟡〕も封鎖＝厳格化）。footprint: scripts/build-judge-card.py＋tests/test_test_runner_realness.py＝M（2-5）。control-plane（gate 判定ロジック）を触るため review+qa+security 必須・M のため deploy skip。候補#2 ref-window 原子化は iter68 第一候補へ繰越・#3 は独立 maintenance へ。"
iteration: 67
ui_surface: false
last_updated: "2026-07-12T07:10:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: "docs/plans/2026-07-12-iter67-judge-test-fact-robustness-implementation-plan.md"
  spec: "docs/specs/2026-07-12-iter67-judge-test-fact-robustness-design.md"
  review: "docs/qa-reports/iter67-review.md"
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
next_action: "**【iter67 qa 着手（自走）】** review approved（judge 🟢・正本=docs/qa-reports/iter67-review.md）: 1次4角度（A 仕様=approve/B 敵対=approve〔FB-1 washed-green は baseline 差分で pre-existing 実証・Low・SF-012 起票予定〕/C テスト強度=a_w_n→3段系列ピン fix-forward 70ace79/D 保守性=a_w_n→D-1 fix-forward）＋盲検2次=fable a_w_n（F1 docstring 定義乖離/F3 guidance 省略→fix-forward 0739a79・divergence なし）。次=qa gate: B1 drill 判断（per-task committed＝diff 空なら conf7 の sanctioned skip＋代替実証〔fresh 変異・grill 変異2種は実証済み〕）→judge preview の実地確認（trust-scan 発火＝本 iter の manual green が noise を透過するか）→full record green→qa ref→承認。◆既知 flaky=test_update_gate_lock（回帰外）。◆push=ユーザー指示待ち。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-09"
    mode: Dev
    phase: "docs"
    note: "iter64 / v1.25.0（fingerprint tree-hash 化＝全体レビュー R6 根1・§4 Phase 1「1-1」＋setup OR marker 厳格化＝iter63 LOW-1 解消）を全 dev ゲート approved まで完走（M＝deploy skip・push 手前で停止）。動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R6 根1・§4 Phase 1（1-1）／iter63 LOW-1。実装: hooks/lib/fingerprint.sh のハッシュ入力 `head:<sha>` を「非 docs/.claude の committed tree-hash」（`git ls-tree -r HEAD` を docs/・.claude/ 除外→sha256・char-class `[.]claude/` でリテラルドット固定）に置換＝docs-only コミットで green が無効化する罠 r を根切りしつつ code コミットで fp が動く silent-green 防止を完全保存・token 契約/consumer 不変＋bin/setup.sh selfheal 身元判定を `.aegis-install-version` OR cp-lock.sh から stamp 単独へ（stamp K-11 2026-06-13 が cp-lock 2026-06-21 より先行導入で正規 self-heal 不喪失）。新規テスト4（docs-only 不感/aclaude 誤除外回帰/root-docs ファイル包含/without-stamp fail-closed）RED-first。brainstorm→plan(grill-plan 致命1=escaping over-exclusion〔$'\\t\\.claude/' が bash で bare-dot 化〕→char-class を実 grep 実証で反映)→implement(TDD RED-first)→grill-code(致命0)→review(1次 in-session＋テスト強度 23 passed 無回帰＋盲検2次 approve_with_notes・mutant flip で歯・fix-forward: docs 非対称コメント＋root-docs テスト)→qa(B1 drill=**skip**〔実装コミット済 992ff4f・diff 空／純コメントハンクは coverage floor 除外の既知限界 §1-5〕＋代替実証: 4新規 RED-first＋4種一時変異 RED＋coverage 空白3件を実 git 安全確認・full 1080 recorded green)→security(1次 in-session＋盲検2次 security 動的実証〔injection 6種非実行・clean→clean pin・移行 fail-closed・OR marker 発火面縮小・date-ordering git log 裏取り〕・Findings HIGH/MEDIUM/LOW 0・両者 approve 収束・**iter63 LOW-1 をクローズ**・deps🟡 ack)→ship(v1.24→1.25 MINOR・bump 3箇所〔check_framework_contract.py/STATUS/STATUS.template〕・TO-CLIENT・README を stamp 単独に更新)→docs(LEARNINGS 3件＋iter57 conf9 罠 r を解消済みに更新)。実装コミット済（992ff4f・qa skip のため per-task commit・ship で bump 込み amend 予定）・未 push（push=gh auth switch --user yuuya-miyagaki）。**教訓核**: (1) シェルで組む grep のドットは `\\.` でなく `[.]` で固定（ANSI-C クォートがバックスラッシュを剥がし bare-dot 化＝silent-green 穴・grill-plan 実 grep で捕捉）（conf8）。(2) コメント修正の孤立ハンクは B1 floor を満たせず commit→skip が sanctioned（conf7）。(3) gate ref は承認前に置くと pending→null-ref 不変条件違反で contract red＝record green→ref→承認を pytest 挟まず連続（conf8・全体レビュー 1-3 罠が実地顕在化）。"
  - date: "2026-07-12"
    mode: Dev
    phase: "docs"
    note: "iter65 / v1.26.0（S サイズ修復＝全体レビュー §4 Phase 1 項目 1-4・R2🔴）を全 dev ゲート approved まで完走（M＝deploy skip・push 手前で停止）。動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §R2/§4 表 1-4。実装（工程別 model tiering: 疑う=Fable 5／書く=Opus 4.8）: Fix 1 check-gate.sh を pure-bash size-aware 化（S→brainstorm gate/他・未設定・不正値→plan gate・approved OR n/a 許容・python 委譲は fail-open 退行で不採用・task_size は frontmatter スコープ読み）＋Fix 2 check_phase_transition の terminal 空リスト穴を明示 deny（Fix 3a 後 dormant・将来 size 追加への defense in depth）＋Fix 3a SIZE_ALLOWED_PHASES[S] に docs 追加（罠 q 根絶・terminal 統一・純加算）＋drift-guard（bash の size→gate 複製が python SoT から drift したら赤・iter53 parity 型）＋guidance 同期（state-machine.md/architecture-overview.md 姉妹表）。三者不整合（rule 文書○/python○/bash hook ✗）を bash 側へ揃えた。brainstorm→plan(grill-plan 致命2=Task2 monkeypatch が subprocess ハーネスと矛盾→in-process import 明記/リスク3 S降格迂回の受容 stance 確定＋要検討5 全反映)→implement(TDD RED-first・implementer=opus per-task commit)→grill-code(Critical0・fix-forward=docstring 同期)→review(1次4角度 finder=opus→親 verify=fable・盲検2次=fable 収束 approve_with_notes・Major3件 fix-forward=b9c95f7 本文spoof封鎖〔frontmatter スコープ読み〕/89264c7 else分岐 n/a許容ピン/ef1cd9b 姉妹表同期)→qa(B1 drill=skip〔per-task committed・iter64 conf7〕＋qa一次 fresh 変異 M1-M4 全kill＋full suite 1096 passed/2 skipped 緑記録)→security(1次 in-session＋盲検2次=fable・injection/secrets/data-exposure なし実測・SF-010 residual ack〔severity Major→Medium 較正〕・両者 approve_with_notes 収束)→ship(v1.25→1.26 MINOR・bump 3箇所〔check_framework_contract.py/STATUS/STATUS.template〕・TO-CLIENT)→docs(LEARNINGS: S編集不能/framework-M唯一クリーンを解消済へ更新＋新3件〔設計核/gate 昇格の parser・audit 穴/flaky 切り分け〕＋ref-window conf8→9)。実装コミット済（c17be50〜31c816d）・未 push（push=gh auth switch --user yuuya-miyagaki）。**残存**: SF-010（task_size empty-baseline raw-Edit×migration-grace 穴・Medium・OPEN）はユーザー承認で次反復 iter66 分離（F-1/F-2 パーサ drift 同梱）。既知 flaky=test_update_gate_lock（lock 待ちタイミング・diff 不接触＝回帰外）。**教訓核**: (1) gate 判定に OPTIONAL フィールドを昇格させるとパーサの緩さ＋監査カバレッジ穴が初めて gate-bypass に転化（読取厳格性と監査を機能追加と同時に検証）。(2) 実装層だけの三者不整合は緩い bash を厳しい python に意味で揃え parity guard をセットに。(3) record red は ref-window 一過性→flaky の順で切り分け（機構不接触なら回帰外）。"
  - date: "2026-07-12"
    mode: Dev
    phase: "docs"
    note: "iter66 / v1.26.1（SF-010 封鎖＋frontmatter 読取意味論統一・**PATCH**＝既存 moat の穴を塞ぐ security fix・公開契約不変）を全 dev ゲート approved まで完走（M＝deploy skip・push 手前で停止）。動機正本＝docs/security-followups.md SF-010（iter65 review 検出）。設計正本＝docs/specs/2026-07-12-iter66-sf010-parser-unification-design.md。実装（工程別 model tiering: 疑う=Fable 5／書く=Opus 4.8）: Fix ① post-status-audit migration-grace を task fields＋gate loop とも『真の旧フォーマット snapshot（必須キー task_type 行/gate_approvals 節すら無い）』限定に絞り込み（feff60c・SF-010 本丸＋(iii) gate loop）＋Fix ② frontmatter_value を library 級スコープ化（abf6d04・本文 spoof 不可視/未終端 fail-closed/bare 温存）＋Fix ③ snapshot 生成スコープ化＋regen silent-fail 修復＋gate 節ガード（c5f63e4）＋Fix ④ gate_value 本文 fallback を ---無しファイル限定（c5f5fd2・F-2）＋Fix ⑤ python extract_scalar_value 行順 first-match＋extract_approval_map 先勝ち（6229fd5・F-1・bash grep -m1 に一致）＋check-gate dedup（c3d7e76）＋parity drift-guard fixture a-k（fba9b08）。session=fable・実装 implementer=opus per-task commit。brainstorm→plan(grill-plan 致命2=gate tamper loop にも同型 grace 実在→Task4 を gate loop 込みに拡張/読点 census タスク追加)→implement(TDD RED-first)→grill-code(Critical0・🟡3+🟢1 fix-forward 1934c98)→review(1次4角度 finder=opus→親verify=fable・盲検2次=fable approve 収束・Major×4 fix-forward 6148a60=bash 値正規化を python に一致/gate_value 行頭2-space アンカー/parity g-k)→qa(B1 drill=skip〔per-task committed・conf7〕＋qa一次 fresh 変異 M1-M5 全kill〔計14テスト・scratch clone〕＋SF-010 閉塞 4ケース hook 直接発火再実測＋full 1138 passed/2 skipped 緑記録)→security(1次 opus 実 hook 発火 findings0＋親verify で pre-existing/contained 裏取り＋盲検2次=fable fresh 独立 approve・新規脆弱性0・deps N/A ack)→ship(v1.26.0→1.26.1 PATCH〔README ポリシー fixes=PATCH・公開契約不変・ユーザー選択〕・bump 3箇所・TO-CLIENT)→docs(SF-010 CLOSED 化＋LEARNINGS: line139 conf8→9〔SF-010 封鎖・後方互換 grace は必須キー存在で線引き〕/line137 ref-window に judge test-fact 最新マッチ軸追加/新 conf8〔盲検2次 pre-existing 乖離の扱い＝SF-011〕)。実装コミット済（abf6d04〜dace3b7）・未 push（push=gh auth switch --user yuuya-miyagaki）。**新規起票**: SF-011（read_frontmatter↔extract_frontmatter 終端デリミタ差・Low・OPEN・pre-existing・3層 contained〔check-gate fail-closed/update-gate.sh 必須/--strict PyYAML reject〕・盲検2次検出・次反復 hardening）。既知 flaky=test_update_gate_lock（回帰外・本 run 顕在化せず）。**教訓核**: (1) 後方互換の grace 窓は『OPTIONAL フィールドの空』でなく『必須フィールドの存在/不在』で線引きせよ（OPTIONAL の空は正規状態と区別できず fail-open 窓）＝SF-010 根因（昇格候補）。(2) judge tier-1 test-fact は evidence-log の最新 test-runner マッチを採るので record green 後にクォート外の生 pytest を走らせると unverified 降格＝件数確認は record 前に・締めは record-test-result（conf9 line137 に軸追加）。(3) 盲検2次が pre-existing 乖離を掘ったら differential battery（baseline vs HEAD）で回帰でないことと多層 contained を実測してから gate 判断（ブロック vs 起票）に反映＝『実証してから限界主張』。"
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
