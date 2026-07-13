# Evidence Archive

Archived external_evidence entries from `docs/STATUS.md`.
STATUS.md retains only the latest 3 entries; older entries are moved here.

## Archived Entries

### codex-review-round-1 (v0.5.0 Phase 1-7)

- **findings:** P1x3 (gate接続, contract, security pattern), P2x2 (iteration refs, browser QA), P3x1 (STATUS更新)
- **resolution:** 全P1修正済み、P2修正済み、P3一部修正+理由付き現状維持

### codex-review-round-2 (v0.5.0 修正後)

- **findings:** P2x1 (n/a gate stale ref), P3x1 (external evidence構造化)
- **resolution:** P2 PaC実装、P3 external_evidence追加

### codex-review-v060-round-1 (v0.6.0 Phase 0-5)

- **findings:** P1x2 (post-status-audit不完全, /gate構造矛盾), P2x1 (template bootstrap失敗)
- **resolution:** 全3件修正。update-gate.sh新設、post-status-audit全8ゲート化、template task_size除去

### codex-review-v060-round-2 (v0.6.0 配布整合)

- **findings:** P1x1 (README update-gate.sh手順欠落), P2x1 (example update-gate.sh未同梱)
- **resolution:** README Step10追加、example scripts/コピー

### session-history: iteration 18 (v1.5.0 E1 activity verification, 2026-06-11)

検証の実行ベース化を 13 タスク TDD で完走。hook 観測の Bash 実行記録 `.claude/evidence-log.jsonl` を judge card テスト判定の唯一ソース化（自己申告 test-result.json 廃止）、fingerprint.sh 単一所有（HEAD sha 混入）、記録=fail-open／判定=fail-closed、observer 生存チェック（TaskCompleted 差し戻し）、smoke の観測系実発火。設計逸脱2件（payload_sha／HEAD 比 fingerprint）はユーザー事前承認・spec 同期済み。grill-code（独立2サブエージェント）が 🔴1（quotepath で非ASCII名の fp 不感＝silent green・実証付き）＋🟡4（無区切り連結衝突／example observer 未登録＋presence 穴／smoke 失敗側未発火／観測→判定 e2e 不在）を検出し全て同セッション修正。436 tests OK・contract・drift・smoke 全 PASS。テスト行は record-test-result.py の手動記録（manual ok・fp 一致）で green、4 ゲートを --ack 承認。v1.5.0 minor で締め・tag v1.5.0。

### session-history: iteration 20 (v1.5.2 残余消化, 2026-06-11)

v151-security.md 記録の残余 5 系統を Task 1〜9 TDD で完走（461→479 tests）。T1=クォート span の Q 置換マスク（false-RED 根治、置換であって削除でない＝green 偽装封鎖、sed/python re バイト一致パリティ、len(strips)!=2→unverified の fail-closed ガード、deny 系 3 hook 不波及を TestMaskScopeBoundary で契約化）、T2=入れ子 ( アンカー、T3=フィデリティ ルーティング、T4=孤児 claim 復元＋pid なしロックの O_EXCL 採用、T5=待機窓 10s。grill-code 独立 2 本（A=条件付き 🟡1、B=🟢3）: A J1=マスク置換が production 消費者で未ピン → mutation-killer テストで充足（b79184a）。受容残余（混在クォート横断・SIGSTOP >2分窓・PID 再利用）は v152-security.md に記録。v1.5.2 patch・tag v1.5.2。

### session-history: iteration 34 (レビュー集中修正, 2026-06-21)

全力レビュー（内製5レンズ）＋外部レビュー(E1-E5)の確定 P1/P2 を TDD で修正。A1 emit.sh 利用 6 hook の fail-closed 統一（byte-identity 12 hook・新規 test_hook_emit_failclosed が emit.sh を使う check-*.sh の fallback 必須を動的検査）/ A2 standard で moat4 hook required-registration / C1 setup baseline を実コピー path 限定 / B1 vacuous safety test 実効化 / B3 missing-ref rc 検証 / D1 README 数字+guarantee 限定 / D2 check-secrets scope / 版 1.12.1。検証: full suite 1006 passed/1 skip・contract(full)・Tier1・各タスク RED→GREEN・盲検3エージェント（核心の fail-closed/normal-path を実走確認・Critical0・scope creep0）。grill-plan 致命2（Task0 を update-gate.sh 経路へ・B4 phase↔gate 自動検査は YAGNI で Batch E 繰延）と grill-code 🟡1 を反映。review gate approve。qa/security/deploy はユーザー判断で短絡し push で締め。コミット f8aff7a〜dd4c593。push は yuuya-miyagaki。

### session-history: iteration 33 (M4 rebuild・簡素化 WS4 最終, 2026-06-21)

観測 hook（E1）の fingerprint/marker 計算を全 Bash hot-path からテストランナー検出時のみへ寄せた。共有 is_test_runner_cmd（evidence.sh・消費側 read_test_result と同一正規化＋AEGIS_TEST_RUNNER_REGEX・単一 sed -e -e/単一 grep -e -e・bash3.2 安全）を新設し append_evidence を条件分岐＝非ランナーは fp 番兵 'skipped'＋marker false の安価記録。post-bash.sh の検出も同関数へ統合（単一ソース化＝recorder/ヒント/reader がドリフト不能）。ゲート時の緑認証ロジック（fail-closed・silent-green 禁止・fp binding）は byte 不変＝『いつ呼ぶか』だけ変更。grill-code（🔴0・🟡1 closed・🟢2 受容）→REDTEAM PoC 18/18→盲検2次 security 独立 approve。pytest 998 passed/1 skip・contract・Tier1・scaffold smoke・パリティ 9。ゲート review🟢／qa🟢／security🟡ack（deps N/A）。版 1.12.0 据置。コミット f02680d/878af23/fb5c5d1/ffd5050/a710328。tests 緑化は record-test-result.py（trusted manual runner）。

### external_evidence: second-opinion-v0122-r6-r9 (v0.12.2 実装後 4 ラウンドレビュー, archived iter48 2026-06-26)

- **scope:** v0.12.2 実装後 4 ラウンドレビュー
- **findings:** Round 6 (P1×2, P2×1: pre-compact exit 2 / minimal-project / test rc), Round 7 (P1×1, P3×1: git add 漏れ / テスト件数表記), Round 8 (P2×1, P3×1: stale last_updated / grep 自己マッチ), Round 9 (P3×2: コメント不整合)
- **resolution:** 9件全反映。tier 1/2 PASS、134 tests PASS、本体と minimal-project 完全同期確認済み。STATUS external_evidence が 3 件上限のため iter48 rollover でアーカイブ（最古エントリ）。

### session-history: 2026-04 期 v0.7.0〜v0.12.0（STATUS body から移設 2026-07-12・iter66 rollover）

- 2026-04-15: v0.7.0-v0.7.2 実装。ネイティブ機能改善、scaffold自己完結性、信頼境界ハードニング。
- 2026-04-17: v0.8.0 Client モード強化 実装完了+全ゲート通過+コミット+プッシュ。48ファイル変更。
- 2026-04-18: v0.9.0-v0.10.0 integration-assist, browser-assist。全ゲート通過+コミット+プッシュ。
- 2026-04-22: v0.11.0 Hair Salon Bloom 振り返り7施策実装+コミット+プッシュ。
- 2026-04-22: v0.12.0 MCP gate + ref check + name lint + health check。48テスト全PASS。

### session-history: iteration 63 (v1.24.0 setup.sh self-heal unlock, 2026-07-08・archived iter66 docs 2026-07-12＝frontmatter ≤3 維持)

iter63 / v1.24.0（setup.sh self-heal unlock＝全体レビュー R3・正規 upgrade が OS-lock 済み install で cp: Permission denied 死する問題）を全 dev ゲート approved まで完走（M＝deploy skip・push 手前で停止）。動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R3・§4 Phase 0-3。実装: bin/setup.sh に selfheal_unlock_target（copy 前・aegis マーカー AND 実 lock 検出でのみ発火・対象は cp-lock 正本 CP 集合限定・symlink 非追従・再 lock は次回 session-start 任せ・NOTE 2行で窓可視）＋explain_unwritable_dst（mkdir/cp を if! → 帰属 abort 化・最近傍実在祖先の non-writable 帰属・誤帰属なし）＋opt-out AEGIS_SETUP_SELFHEAL=off は fail-closed＋回帰テスト tests/test_setup_locked_target_upgrade.py 4本（T1 self-heal/T2 fresh 無副作用/T3 opt-out fail-closed/T4 非 aegis 不介入）。brainstorm→plan(grill-plan 致命3=祖先遡り/ROOTUSER skip/bump3箇所目 反映)→implement(TDD RED-first)→grill-code→review(1次+盲検2次 approve_with_notes・Major0・full 1076 passed/2 skipped)→qa(B1 実 drill 7/7 caught・drill 後再実走 record〔pyc 教訓〕)→security(**1次を in-session 実施**＝1次委譲の 3×watchdog600s ハング〔インフラ故障〕を回避／盲検2次のみフレッシュ委譲 approve_with_notes・265s 完走。Findings HIGH/MEDIUM/LOW 0・🟡 dep監査N/A＋approve_with_notes notes〔OR marker・unlock窓〕を ack・Major0・両レビュー収束)→ship(v1.23→1.24 MINOR・bump 3箇所〔check_framework_contract.py/STATUS/STATUS.template〕・TO-CLIENT・README Upgrade note に self-heal 追記)→docs(LEARNINGS 2件)。実装未 push（push=gh auth switch --user yuuya-miyagaki）。**教訓核**: (1) 検証委譲がインフラ故障で詰まったら 1次を in-session に引き取り盲検2次だけ委譲（3失敗は goal で数える・security 1次は構造的に委譲必須でない）（conf7）。(2) 単一セッションで ship→docs 自走時、ゲート操作が無く snapshot が前フェーズ固定→phase-skip 誤 block＝aegis_write_snapshot で正規再同期（conf7）。

### session-history: iteration 64 (v1.25.0 fingerprint tree-hash 化, 2026-07-09・archived iter67 docs 2026-07-12＝frontmatter ≤3 維持)

iter64 / v1.25.0（fingerprint tree-hash 化＝全体レビュー R6 根1・§4 Phase 1「1-1」＋setup OR marker 厳格化＝iter63 LOW-1 解消）を全 dev ゲート approved まで完走（M＝deploy skip・push 手前で停止）。動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R6 根1・§4 Phase 1（1-1）／iter63 LOW-1。実装: hooks/lib/fingerprint.sh のハッシュ入力 `head:<sha>` を「非 docs/.claude の committed tree-hash」（`git ls-tree -r HEAD` を docs/・.claude/ 除外→sha256・char-class `[.]claude/` でリテラルドット固定）に置換＝docs-only コミットで green が無効化する罠 r を根切りしつつ code コミットで fp が動く silent-green 防止を完全保存・token 契約/consumer 不変＋bin/setup.sh selfheal 身元判定を `.aegis-install-version` OR cp-lock.sh から stamp 単独へ（stamp K-11 2026-06-13 が cp-lock 2026-06-21 より先行導入で正規 self-heal 不喪失）。新規テスト4（docs-only 不感/aclaude 誤除外回帰/root-docs ファイル包含/without-stamp fail-closed）RED-first。brainstorm→plan(grill-plan 致命1=escaping over-exclusion〔$'\t\.claude/' が bash で bare-dot 化〕→char-class を実 grep 実証で反映)→implement(TDD RED-first)→grill-code(致命0)→review(1次 in-session＋テスト強度 23 passed 無回帰＋盲検2次 approve_with_notes・mutant flip で歯・fix-forward: docs 非対称コメント＋root-docs テスト)→qa(B1 drill=**skip**〔実装コミット済 992ff4f・diff 空／純コメントハンクは coverage floor 除外の既知限界 §1-5〕＋代替実証: 4新規 RED-first＋4種一時変異 RED＋coverage 空白3件を実 git 安全確認・full 1080 recorded green)→security(1次 in-session＋盲検2次 security 動的実証〔injection 6種非実行・clean→clean pin・移行 fail-closed・OR marker 発火面縮小・date-ordering git log 裏取り〕・Findings HIGH/MEDIUM/LOW 0・両者 approve 収束・**iter63 LOW-1 をクローズ**・deps🟡 ack)→ship(v1.24→1.25 MINOR・bump 3箇所〔check_framework_contract.py/STATUS/STATUS.template〕・TO-CLIENT・README を stamp 単独に更新)→docs(LEARNINGS 3件＋iter57 conf9 罠 r を解消済みに更新)。実装コミット済（992ff4f・qa skip のため per-task commit・ship で bump 込み amend 予定）・未 push（push=gh auth switch --user yuuya-miyagaki）。**教訓核**: (1) シェルで組む grep のドットは `\.` でなく `[.]` で固定（ANSI-C クォートがバックスラッシュを剥がし bare-dot 化＝silent-green 穴・grill-plan 実 grep で捕捉）（conf8）。(2) コメント修正の孤立ハンクは B1 floor を満たせず commit→skip が sanctioned（conf7）。(3) gate ref は承認前に置くと pending→null-ref 不変条件違反で contract red＝record green→ref→承認を pytest 挟まず連続（conf8・全体レビュー 1-3 罠が実地顕在化）。

### session-history: iteration 65 (v1.26.0 S サイズ修復, 2026-07-12・archived iter68 docs 2026-07-13＝frontmatter ≤3 維持)

iter65 / v1.26.0（S サイズ修復＝全体レビュー §4 Phase 1 項目 1-4・R2🔴）を全 dev ゲート approved まで完走（M＝deploy skip・push 手前で停止）。動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §R2/§4 表 1-4。実装（工程別 model tiering: 疑う=Fable 5／書く=Opus 4.8）: Fix 1 check-gate.sh を pure-bash size-aware 化（S→brainstorm gate/他・未設定・不正値→plan gate・approved OR n/a 許容・python 委譲は fail-open 退行で不採用・task_size は frontmatter スコープ読み）＋Fix 2 check_phase_transition の terminal 空リスト穴を明示 deny（Fix 3a 後 dormant・将来 size 追加への defense in depth）＋Fix 3a SIZE_ALLOWED_PHASES[S] に docs 追加（罠 q 根絶・terminal 統一・純加算）＋drift-guard（bash の size→gate 複製が python SoT から drift したら赤・iter53 parity 型）＋guidance 同期（state-machine.md/architecture-overview.md 姉妹表）。三者不整合（rule 文書○/python○/bash hook ✗）を bash 側へ揃えた。brainstorm→plan(grill-plan 致命2=Task2 monkeypatch が subprocess ハーネスと矛盾→in-process import 明記/リスク3 S降格迂回の受容 stance 確定＋要検討5 全反映)→implement(TDD RED-first・implementer=opus per-task commit)→grill-code(Critical0・fix-forward=docstring 同期)→review(1次4角度 finder=opus→親 verify=fable・盲検2次=fable 収束 approve_with_notes・Major3件 fix-forward=b9c95f7 本文spoof封鎖〔frontmatter スコープ読み〕/89264c7 else分岐 n/a許容ピン/ef1cd9b 姉妹表同期)→qa(B1 drill=skip〔per-task committed・iter64 conf7〕＋qa一次 fresh 変異 M1-M4 全kill＋full suite 1096 passed/2 skipped 緑記録)→security(1次 in-session＋盲検2次=fable・injection/secrets/data-exposure なし実測・SF-010 residual ack〔severity Major→Medium 較正〕・両者 approve_with_notes 収束)→ship(v1.25→1.26 MINOR・bump 3箇所〔check_framework_contract.py/STATUS/STATUS.template〕・TO-CLIENT)→docs(LEARNINGS: S編集不能/framework-M唯一クリーンを解消済へ更新＋新3件〔設計核/gate 昇格の parser・audit 穴/flaky 切り分け〕＋ref-window conf8→9)。実装コミット済（c17be50〜31c816d）・未 push（push=gh auth switch --user yuuya-miyagaki）。**残存**: SF-010（task_size empty-baseline raw-Edit×migration-grace 穴・Medium・OPEN）はユーザー承認で次反復 iter66 分離（F-1/F-2 パーサ drift 同梱）。既知 flaky=test_update_gate_lock（lock 待ちタイミング・diff 不接触＝回帰外）。**教訓核**: (1) gate 判定に OPTIONAL フィールドを昇格させるとパーサの緩さ＋監査カバレッジ穴が初めて gate-bypass に転化（読取厳格性と監査を機能追加と同時に検証）。(2) 実装層だけの三者不整合は緩い bash を厳しい python に意味で揃え parity guard をセットに。(3) record red は ref-window 一過性→flaky の順で切り分け（機構不接触なら回帰外）。
