---
framework: aegis
framework_version: "1.15.0"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: L
task_size_rationale: "iteration 54（framework・ドッグフード前 Critical バッチ修正）= L。footprint は hooks/lib/safety.sh＋hooks/check-control-plane.sh＋hooks/check-gate.sh＋hooks/check-secrets.sh＋hooks/check-destructive.sh＋bin/setup.sh＋scripts/run-test-strength-drill.py（＋build-judge-card.py 精査）＋新規テスト複数＝6+ ファイル。deny/ask 判定ロジック本体に触れる（case-fold・noglob）＝moat 変更を含むため全ゲート必須。"
iteration: 54
ui_surface: false
last_updated: "2026-07-02T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: approved
  dev_ready_for_client: approved
current_refs:
  requirements: []
  plan: docs/plans/2026-07-02-iter54-critical-batch-design.md
  spec: docs/plans/2026-07-02-iter54-critical-batch-design.md
  review: docs/qa-reports/iter54-review.md
  qa: docs/qa-reports/iter54-qa.md
  security: docs/qa-reports/iter54-security.md
  deploy: docs/qa-reports/iter54-deploy.md
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
next_action: "**【iter54 クローズ済（push 済 origin/main=8bf0a38）／iter55 テーマ選定完了＝実ドッグフード（repo 外・2026-07-02）】** ◆**現在地**: grill-premise でテーマ選定 → **A: 実ドッグフード開始を採択**（B: 構造リアーキ〔FS実解決/OS-lock 昇格・894行 check-control-plane 退役〕は『ドッグフード一周後の最有力テーマ』として保持＝実運用データで OS-lock 設計を裏打ちしてから）。ドッグフードは外部プロジェクトのため**本 repo の iter55 rollover は意図的に未実施**（次の aegis テーマ着手時に rollover してから iteration=55 とする）。 ◆**ドッグフード準備完了**: `~/Desktop/personal/yoga-tsukinowa-lp` に v1.15.0 を `--profile=full` で導入済（baseline 798a105・meta docs 4d4fec8）。正本＝同 dir の `DOGFOOD-BRIEF.md`（架空ペルソナ=ヨガスタジオ月の環・仮説 H1 完走/H2 qa-browser 実測〔P4 判断データ〕/H3 記録規律・ブラインド規律・blocking 以外の framework 修正禁止）＋`DOGFOOD-LOG.md`（フェーズ別観測ログ）。 ◆**次アクション**: **新ターミナル**で yoga-tsukinowa-lp を開き（1ターミナル=1repo）、BRIEF の『次の一手』どおり Client onboard から一周。完了後に LOG を aegis の iter55+ テーマへ変換。 ◆**罠（iter41-54 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-02"
    mode: Dev
    phase: "docs"
    note: "セッション復帰（/recover）→ iter55 テーマ選定→ドッグフード準備完了。status_doctor PASS・iter54 push 済（origin/main=8bf0a38）を確認。grill-premise で A=実ドッグフード vs B=構造リアーキをグリル → **A 採択**（根拠: ①ドッグフード前提条件〔Critical 4件〕は iter54 で消化済み ②54反復で実使用データゼロ＝情報価値はドッグフードが上〔iter48-54 で7回連続の内部改善＝トレッドミル症状・LEARNINGS が自ゲート機構との戦い一色というエコーチェンバー指摘〕 ③P4〔実ブラウザQA〕の要否は実案件データでしか判断不能〔再起動トリガ=実案件での見逃し1件〕 ④B は既知穴を iter54 で封鎖済みの負債返済＝待っても価値が減らない＋OS-lock 設計は macOS 実運用データで裏打ちしてからの方が精度が上がる。B は一周後の最有力テーマとして保持）。準備: repo 外 `~/Desktop/personal/yoga-tsukinowa-lp` に git init＋`setup.sh --profile=full` で v1.15.0 導入（baseline 798a105）→ `DOGFOOD-BRIEF.md`（架空ペルソナ=世田谷・ヨガスタジオ月の環／森本さやか43・初期要望逐語・仮説 H1完走/H2 qa-browser 実測/H3 記録規律・ブラインド規律=ヒアリングで聞き出した内容のみ要件化可・トイ化防止=空き/満席・成功/失敗・validation の複数状態＋ui_surface:true 必須）＋`DOGFOOD-LOG.md`（フェーズ別観測ログ＋集計欄〔迷子/ゲート戦闘/人手介入/[P4]見逃し/blocking〕）をコミット（4d4fec8）。**本 repo の iter55 rollover は意図的に未実施**（テーマが外部のため。次の aegis テーマ着手時に rollover）。次＝新ターミナルで yoga-tsukinowa-lp を開き Client onboard から一周。"
  - date: "2026-07-02"
    mode: Dev
    phase: "docs"
    note: "iteration 54（framework・ドッグフード前 Critical バッチ修正・L・v1.14.0→v1.15.0）完了・**push 未（ユーザー確認待ちで停止）**。2026-07-02 徹底グリル（6並列＋自己再現）由来の Critical 4＋Should 2 を1イテレーションで修正。brainstorm→plan→grill-plan(致命5反映: -ef プローブ〔`-d` 単独は case-sensitive の実在別 dir HOOKS/ 誤検知〕／bash 高速ゲートも fold 必須／required ループ rc 検査／対称 -i strip／quoted 残存 fail-closed)→implement(TDD RED-first・31 RED→全 GREEN)→grill-code(🔴 C-1b: post-status-audit の `*STATUS.md` filter も case-sensitive＝STATUS.MD の gate tamper が監査ごとスキップ〔C-1 同一クラス〕を自己検出→修正／🟡 check-secrets commit トリガの CMD_LC fold 漏れ→修正)→review(盲検2次=approve_with_notes・Minor-2〔Linux over-audit〕修正・Minor-1〔非ASCII homoglyph〕別テーマ受容)→qa(B1 SKIP〔tracked run 86≫25・framework 混在〕＋手動 mutation 実測 M2b/M3/M4/M5/M6 CAUGHT・M1 は `-ef` が case-sensitive Linux 専用判別で macOS skipIf／full suite 1232 passed・record green)→security(盲検2次=approve_with_notes・case-insensitive FS 実複製で moat 弱体化ベクタ不在を6形態＋env注入で実測・N-1〔fold プローブの CLAUDE_PROJECT_DIR 依存〕を PROBE_ROOT で env 非依存化して修正・N-2/.bak 予測名と非ASCII/大文字コマンド名は別テーマ受容)→deploy→ship→docs。実装: hooks/lib/safety.sh（aegis_fs_case_insensitive プローブ・strengthen-only FORCE）／check-control-plane・check-gate・check-secrets・post-status-audit（条件付き case-fold・deny-only）／check-destructive・check-gate（noglob）／bin/setup.sh（JSON 冒頭検証＋全 heredoc argv 化＋parse rc 検査＝fail-open install 封鎖／copy_file diff-gated .bak＝--force データ保全）／run-test-strength-drill.py（quotepath=off＋quoted 残存 DrillError）＋新規テスト4（test_case_insensitive_fs/test_setup_failclosed/test_drill_quotepath/test_glob_expansion_hooks）＋既存2更新（test_setup_arg_version の heredoc 契約複数化・test_cp_lock_contract の v1.15.0）＋v1.15.0 bump（contract/STATUS.template）。LEARNINGS 3件（tech conf9 ケース非依存FS moat バイパス封鎖型／process conf8 FS依存テストの2層戦略＋手動 mutant は変異有効性を先に確認）。構造リアーキ（FS実解決/OS-lock 昇格・894行 check-control-plane 退役）は非スコープ＝別テーマ（iter55 候補）。**feat 49a44cc＋close anchor push 済（origin/main=9a36d72・yuuya-miyagaki）＝iter54 完全クローズ**。"
  - date: "2026-06-29"
    mode: Dev
    phase: "docs"
    note: "iteration 53（framework・破壊的コマンド警告の日本語化＋ドリフトガード・M・v1.14.0 据置）完了。/clear→/recover→rollover（iter50 剪定・iteration=53・dev ゲット全 reset）→ brainstorm(grill-premise が当初『汎用平易化 slice2』を falsify＝reason 注入機構＋平易日本語の中身は control-plane/secrets/skill-gate/cron-gate/tdd/deploy-gate で既存＝YAGNI。実コード監査〔emit_ask 呼出元〕で『最高リスクの破壊的 WARN だけが英語』という客観的・検証可能・安全関連の言語不整合を発見し reframe。format A『破壊的: <コマンド>。<何が起きるか>（<復元可否>）。』確定)→plan→grill-plan(致命3: ①層3 の source 行マッチは翻訳でアンカー英語消滅＝vacuous pass の自己破壊的設計→truncated payload の behavioral 発火に置換〔既存 test_truncated_capital_r_fallback_asks が発火可能を実証〕 ②層2 ターゲットを /important で safe-artifact 回避 ③UTF-8 デコード明示)→implement(TDD RED-first・failures=21/errors=0→GREEN)→grill-code(🟡 REGEX↔WARN パリティ未検証＝将来 REGEX 追加で WARN 欠落→空の[careful]発火を配列ガードもハードコード件数も捕捉せず→test_warn_regex_parity 追加／🟢 distinctive トークン＋_has_japanese 限界コメント)→review(盲検2次 reviewer-testing=approve・moat byte-diff/JSON 透過/層分岐到達を自走確認・chmod 訳の過大表現〔元の権限は復元されません→控えていないと戻せません〕を独立指摘→正確化)→qa(B1 DRILL PASS 5/5 caught・mutant は tracked 3 ファイル〔patterns.sh LOWER/CMD・check-destructive fallback/inline・check-secrets fallback〕の全ハンク・新規 untracked テストは floor 対象外／full suite green・record-test-result manual newest green)→security(盲検2次 security agent=approve・moat byte-diff＋behavioral spot-check〔push --force/DROP/rm -rf /etc/mkfs→ask, node_modules/.env.example→allow〕で決定不変・全18 reason JSON round-trip valid 18/0・secrets/deps clean／tests=unverified〔qa ドリル後 stale〕＋deps を実証付き ack)→ship→docs。実装(code 3 ファイル＋tests 1): hooks/lib/patterns.sh の AEGIS_DESTRUCTIVE_{LOWER,CMD}_WARN 18件＋check-destructive.sh inline rm -r/抽出失敗フォールバック＋check-secrets.sh 抽出失敗フォールバックを日本語化（regex・ask/deny 発火・safe-targets 例外は byte-identical＝moat 不変）／新規 tests/test_destructive_warning_language.py 6テスト（配列 JP ドリフトガード＋REGEX↔WARN parity＋inline/destructive/secrets の behavioral 発火＋distinctive トークン）。既存テストは ask 決定のみ assert で英語本文未 pin＝更新不要（grep NONE 確認）。LEARNINGS 3件追記（tech conf7 hook 確認文の言語一貫性＋drift guard の真の fail-open=parity／process conf7 却下テーマの客観的不整合 reframe＋conf8 truncated payload で fallback behavioral 発火・脆い source 行マッチ回避）。TO-CLIENT/MANUAL/RUNBOOK/UAT は internal framework iteration で N/A。全必須ゲート approved＋dev_ready_for_client approved。feat commit 69632d0・push 済 origin/main=69632d0（yuuya-miyagaki）＝iteration 53 完全クローズ。"
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

- 2026-04-15: v0.7.0-v0.7.2 実装。ネイティブ機能改善、scaffold自己完結性、信頼境界ハードニング。
- 2026-04-17: v0.8.0 Client モード強化 実装完了+全ゲート通過+コミット+プッシュ。48ファイル変更。
- 2026-04-18: v0.9.0-v0.10.0 integration-assist, browser-assist。全ゲート通過+コミット+プッシュ。
- 2026-04-22: v0.11.0 Hair Salon Bloom 振り返り7施策実装+コミット+プッシュ。
- 2026-04-22: v0.12.0 MCP gate + ref check + name lint + health check。48テスト全PASS。
- 2026-06-05: future-proof 再アーキ着手。Phase 0b 確定 + Foundation（emit.sh 単一出力源 / patterns.sh / version owner）実装。Round 1/2 セカンドオピニオン反映。183 tests PASS、main マージ（未push）。
- 2026-06-06: Phase R 再配分を連続 ship（routing 0.12.3／context 0.12.4／model-effort／name-hygiene／TDD 0.12.5／evidence 完了強制 0.12.6）。続けて Phase D（仕上げ）: migration guide(v0.12.2→v1.0.0)＋README リフレッシュ＋安定契約/SemVer 明文化＋version **1.0.0**。各タスクで brainstorm→2段グリル→実装→grill-code を完走。195 tests green・tier1/2 PASS。**再アーキ F→R→A→D 全完了＝v1.0.0「トレッドミルから降りる」看板を掲示。**
- 2026-06-07: 機能整合性監査（charter 2026-06-07）。Layer 0-4 で 7 finding（P1×1/P2×4/P3×2）全修復。核心 F6（P1）＝setup.sh が hooks/lib を配布せず install 先で moat 全死→copy_hooks 修復＋scaffold smoke の hook 実発火で install 経路を契約化。v1.3.2 patch（298 tests・tag v1.3.2）。
- 2026-06-28: iter52（framework・permission prompt 交通整理＝read-only 完全性ガード＋allow 10→14・M）完了・push 済 origin/main=5660f99。詳細は git log 5660f99。
