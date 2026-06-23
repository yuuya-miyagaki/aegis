---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: ship
task_type: framework
task_size: L
task_size_rationale: "iteration 41 = 2026-06-24 全力レビュー Batch 1（配布正常化＋整合性 fail-closed 化・framework・L・6 finding）。要件＝docs/full-review-2026-06-24-hooks-gates-distribution.md（D1-D4 配布／I1-I2 整合性）＋SF-006。対象＝templates/profiles/standard.json（D1 build-judge-card.py 追加・D2 Task hooks 追加）／bin/setup.sh（D3 framework 資産 upgrade 上書き・D4 壊れ設定の無警告全消し是正）／hooks/post-status-audit.sh（I1 fail-closed 化）／scripts/check_status.py（I2 完了evidence fail-closed）／.claude/settings.local.json＋scripts/check_framework_contract.py（D2 active settings の Task hook 配線＋契約検査）＋tests。6+ ファイル＝L＝全ゲート（review+qa+security+deploy）必須。RC-1（STATUS 兼務）は I1+I2 で部分対処・I3 は Batch 2 繰延。check-control-plane 本体は触らない。"
iteration: 41
ui_surface: false
last_updated: "2026-06-24T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: approved
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/full-review-2026-06-24-hooks-gates-distribution.md
  plan: docs/plans/2026-06-24-iter41-batch1-implementation-plan.md
  spec: docs/specs/2026-06-24-iter41-batch1-distribution-integrity-design.md
  review: docs/qa-reports/iter41-review.md
  qa: docs/qa-reports/test-strength.md
  security: docs/qa-reports/iter41-security.md
  deploy: docs/qa-reports/iter41-deploy.md
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
  - type: "second-opinion-v0122-r6-r9"
    scope: "v0.12.2 実装後 4 ラウンドレビュー"
    findings: "Round 6 (P1×2, P2×1: pre-compact exit 2 / minimal-project / test rc), Round 7 (P1×1, P3×1: git add 漏れ / テスト件数表記), Round 8 (P2×1, P3×1: stale last_updated / grep 自己マッチ), Round 9 (P3×2: コメント不整合)"
    resolution: "9件全反映。tier 1/2 PASS、134 tests PASS、本体と minimal-project 完全同期確認済み。"
next_action: "**【iteration 41 完了（framework・L・配布正常化 D1-D4＋整合性 fail-closed I1-I2／review+qa+security+deploy 全 approved／commit 済 721388a・push 未実行＝現 shell の credential(tigereye) は 403・yuuya-miyagaki アカウントで `git push` 要）／次は iteration 42・/clear 後 /recover 用アンカー・2026-06-24】** ◆**まず iteration rollover**: update-gate.sh で dev ゲートを pending に戻し（**bare 単独**呼び出し・非 framework 下は chain/redirect 不可）、STATUS を iteration=42・phase=brainstorm（ship→brainstorm は backward で audit allow）・task_type/size/rationale 更新・current_refs を null（requirements 保持）。**session_history は contract が max 3 ＝rollover で最古を剪定**（長文 note は Edit の exact-match が脆く、ASCII マーカーで python script 剪定が安全）。◆**iter42 候補（優先度順）**: **(0) Batch 2＝I3 task_type/task_size の tamper-evidence**（post-status-audit に task_type/size 監査を追加＝authorized-path 経由のみ変更可。I1 fail-closed が前提＝達成済）＋**G1-G3 guard 網羅**（破壊コマンド dd of= / chmod -R / mkfs / shred / system-path truncate を `hooks/lib/patterns.sh` に single-source 化し check-destructive/deploy-gate/cron-gate 全 gate で import）。要件＝docs/full-review-2026-06-24-hooks-gates-distribution.md（I3/G1-G3）＋SF-006（I3）。(1) **Backlog**: C1（setup.sh `--profile` 空白形式）・C2-C4（heredoc/gate パーサ統一）・C5（ROOT 外 plan-gate false-positive＝auto-memory 等への摩擦）・G4（exfil リスク再評価）。**やらない**: check-control-plane 再設計。◆**iter41 で確立した罠（重要）**: (a) **gate 承認コマンドを `head` にパイプすると SIGPIPE で set -e 下の STATUS 書込み前に中断**＝`tail` を使う。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract の stale-ref FAIL＝suite の test_framework_contract_passes が赤化し record red になる）。(c) judge は claims/2次意見を current_refs.<gate> の report から読む＝承認前に ref 設定が必要だが (b) と両立（approve 自体は stale 検査を走らせない・間に suite/contract を挟まない）。(d) record-test-result は全コード編集完了後に1回（fingerprint bind）。(e) framework 混在 L diff は B1 drill 構造的不適用＝skip-drill＋RED-first TDD 実証。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 41（2026-06-24 全力レビュー Batch 1・framework・L・v1.14.0 据置）完了。/clear→/recover で復帰し rollover（iteration 41・phase=brainstorm・task_size S→L・requirements ref を docs/full-review-2026-06-24-hooks-gates-distribution.md に更新）→ brainstorm→plan(grill-plan)→implement→grill-code→review→qa→security→deploy→ship を完走。**実装した 6 fix**: D1 standard profile に judge ツールチェーン依存閉包を同梱（build-judge-card+run-test-strength-drill=required・record-test-result+fingerprint.sh=recommended・README 件数 20/10 更新）＝standard で gate 承認可能化／D2 Task 完了強制 hook（check-task-created/completed）を standard profile（hooks_include+required_hook_scripts）・active settings・contract self-check（check_active_settings_core_hooks）に配線／D3 setup.sh が再 install で framework 所有（hooks/scripts/templates/.claude/{skills,agents,commands,rules}/bin）を diff-gated .bak つき上書き・user 所有は保全／D4 壊れ settings を無警告全消しせず stderr 警告／I1 post-status-audit を PostToolUse fail-closed 化（safety.sh に block 版 helper・別マーカー POSTTOOL で 12-hook byte-identity 非破壊）／I2 完了evidence を STATUS 不在/None-frontmatter で violation 化。**ゲート（L＝全必須）**: review🟢（盲検2次 security+maintainability とも approve_with_notes・Critical=契約が gitignored settings 依存で非再現→不在 skip 化で修正済）／qa🟡ack（skip-drill＝framework 混在 L diff に B1 構造的不適用・代替 RED-first TDD 実証）／security🟢ack（新規脆弱性なし・Low residual symlink=SF-004 受容）／deploy🟢ack（framework=main commit がデプロイ）。**検証**: full suite 1053 passed/1 skip（record green）・contract full PASS・status_doctor PASS・standard install で --profile=standard PASS 実機確認・git mode-flip なし。**罠を記録（next_action 参照）**: gate コマンドを head にパイプ→SIGPIPE で STATUS 書込み前中断／ref は承認直前設定／record は全コード編集後1回。SF-006 を I1/I2 対処済・I3 は Batch 2 へ。push は yuuya-miyagaki。"
  - date: "2026-06-23"
    mode: Dev
    phase: "ship"
    note: "iteration 40（moat 自動解錠バグ修正・framework・S・hooks/lib/cp-lock.sh・v1.14.0）完了・/recover で継続。**根本原因（iter39 発見→iter40 で bash -x 確証）**: post-status-audit は STATUS 編集で発火し aegis_cp_apply framework→aegis_cp_unlock→chmod -R u+w まで実行していた（＝hook 不発火説は反証）。真因は **Claude Code hook サンドボックスで `chmod -R <dir>` がトップ階層 CP ディレクトリのみ変更しネストファイルに再帰しない**（同 chmod -R を Bash ツールで呼ぶと完全再帰＝環境差）→ dir 解錠/nested 施錠の desync を dir-only sentinel `[ -w hooks ]` が解錠済と誤認し no-op 固定。**修正**: aegis_cp_lock/unlock の `chmod -R` を `find \"$p\" -exec chmod {} +` に変更（lock/unlock 両方向・hook 環境で完全再帰を lock→STATUS編集 trigger→full-unlock 再現で実証）。sentinel は完全再帰なら正確で据置（YAGNI）。ヘッダに『chmod -R 差し戻し禁止』明記。**ゲート（framework S＝review のみ必須・qa/security/deploy size-skip）**: review🟢（judge🟢 tests green・盲検 security 2次 approve＝挙動等価を nested/単一ファイル/空/space/symlink で実測一致・lock=a-w/unlock=u+w でセキュリティ無退行・既存 test_lock_blocks_all_write_forms/test_unlock_restores_writability が nested flip を被覆）。Minor 2件（stale 'chmod -R' 文言＝是正済／find nonexistent rc は [ -e ] ゲートで不発）。**検証**: bash -n PASS・cp-lock 15 tests・full suite 1038 passed/1 skip・record green・contract PASS（版 1.14.0）・git mode-flip なし。**罠を記録**: current_refs.<gate> をセットしたら approve まで suite/contract を走らせない（pending+ref は stale 判定で赤）。LEARNINGS 更新（conf6→conf9＝chmod -R は hook サンドボックスで再帰せず＝find -exec を使う）。push は yuuya-miyagaki。"
  - date: "2026-06-22"
    mode: Dev
    phase: "ship"
    note: "iteration 39（check-gate.sh テスト分離バグ修正・framework・M・test-only・v1.14.0）完了・/recover で復帰し継続。**バグ**: test_failure_policy.py::test_python3_absent_behavior の check-gate.sh シナリオが check-gate.sh:24 の ROOT=SCRIPT_DIR/.. 解決（override/cwd 非対応）で実リポ STATUS を読み、iter38 rollover の plan=pending で deny→fail＝運頼み pass が露出（iter36 Bug-B 同クラス）。**修正（test-only・本番 hook 不変）**: check-gate.sh を _scenarios() ループから外し control-plane 同型の temp-root copy 専用メソッド test_python3_absent_check_gate_reads_scratch_status を追加（lib 4本 copy2・両極 approved→allow／pending→deny で scratch 追従＝live-STATUS 非依存を実証＝旧方式なら pending 極で FAIL する load-bearing 回帰ガード）。**分類の紆余曲折（重要）**: 当初 bugfix（plan=n/a で tests/ 編集可）にしたが**非 framework＝moat が control plane 施錠**し control-plane 書込みテスト（test_setup_distribution force-overwrite 等）を破壊＝full suite red 化を実体験→ユーザー承認(A)で framework-M に再分類（plan フェーズで plan 承認→tests/ 編集可・moat 解錠でスイート green）。check-control-plane は update-gate.sh を allowlist 済だが**非 framework 下は chain/redirect 付きだと弾く＝bare 単独呼び出し必須**も実体験。**発見した moat バグ（follow-up・LEARNINGS conf6）**: task_type を framework に戻しても post-status-audit が自動解錠せず手動 aegis_cp_unlock が必要だった（iter37 の解錠経路が task_type-change edit で不発の疑い）。**ゲート（framework M＝review+qa+security 必須・deploy size-skip）**: review🟢（judge🟢・tests green・盲検 reviewer-testing approve_with_notes 一致＝Minor2件は非アクション）／qa🟡ack（test-only skip-drill・両極アサート＝手動 mutation 同等）／security🟢（盲検 security approve＝subprocess arg-list・copy2・coverage 強化・secrets0・deps N/A ack。判定時 tests は fingerprint drift で unverified だが review ゲートで green 確認済＝実体 green）。**検証**: full suite 1038 passed/1 skip・record green・contract PASS（版 1.14.0）・git mode-flip なし。LEARNINGS 2件追記（framework 内部テスト修正は framework-M／moat 自動解錠 follow-up）。push は yuuya-miyagaki。"
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
