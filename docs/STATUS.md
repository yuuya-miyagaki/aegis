---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: ship
task_type: framework
task_size: L
task_size_rationale: "iteration 42 = 2026-06-24 全力レビュー Batch 2 のうち G1-G3 guard 網羅（確定・ユーザー承認『推奨で進めて』）。**I3 は iter43 へ繰延**（authorized-path 機構＝rollover の正当な task_type/size 編集と両立させる設計フォークが要・別イテレーションで方式合意）。スコープ: **G1** hooks/lib/patterns.sh に破壊コマンド dd of=/chmod -R/mkfs/shred/system-path truncate-redirect を AEGIS_DESTRUCTIVE_CMD_REGEX へ追加（check-destructive 自動適用）。**G3** patterns.sh に AEGIS_DEPLOY_REGEX を single-source 化し check-deploy-gate（挙動保存リファクタ）＋check-cron-gate（inline DANGER_RE を AEGIS_DESTRUCTIVE_*＋AEGIS_DEPLOY_REGEX に置換＝G1 の新破壊パターンも自動波及）で import。**G2** check-secrets.sh の staged-diff scan が `git -C <repo> commit` で CWD 不一致＝-C/--git-dir を抽出。対象＝patterns.sh・check-deploy-gate.sh・check-cron-gate.sh・check-secrets.sh＋tests＝L＝全ゲート必須。**out-of-scope（文書化）**: git push をデプロイ判定（通常 push と区別不能＝MCP push 除外と整合）／`$V deploy` 変数間接（SF-004 クラス＝受容）。check-control-plane 本体は触らない。"
iteration: 42
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
  plan: docs/plans/2026-06-24-iter42-guard-coverage-plan.md
  spec: docs/specs/2026-06-24-iter42-guard-coverage-design.md
  review: docs/qa-reports/iter42-review.md
  qa: docs/qa-reports/test-strength.md
  security: docs/qa-reports/iter42-security.md
  deploy: docs/qa-reports/iter42-deploy.md
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
next_action: "**【iteration 42 完了（framework・L・guard 網羅 G1-G3／review+qa+security+deploy 全 approved／commit 済・push 未＝yuuya-miyagaki で `git push`）／次は iteration 43・/clear 後 /recover 用アンカー・2026-06-24】** ◆**push 未了**: iter41（721388a・a0e403f）＋iter42 の commit がローカル ahead。tigereye credential は 403＝**yuuya-miyagaki アカウントで `git push`**。◆**まず rollover**: update-gate.sh で dev ゲートを pending（**bare 単独**）、STATUS を iteration=43・phase=brainstorm（ship→brainstorm backward で allow）・task_type/size/rationale 更新・current_refs null（requirements 保持）・**session_history 最古剪定（contract max 3）**。◆**iter43 本命＝I3 task_type/task_size の tamper-evidence**（SF-006・full-review I3）: post-status-audit に task_type/task_size 改竄検知を追加。**設計フォーク（着手前に方式決定）**: snapshot は現状 gate/phase/mode のみ＝task_type/size を snapshot に追加し authorized write path を用意（案: (a) update-task.sh 新設／(b) update-gate.sh 拡張／(c) iteration インクリメント時のみ task_type/size 変更許可）。**制約**: rollover/brainstorm が現状 Edit で task_type/size を変更＝authorized-path へ移行しないと rollover が自分でブロックされる。brainstorm で grill-premise（事故では task_type 書換えない＝価値は『非対称性解消』であって新規 moat でない・YAGNI 注意）。◆**Backlog**: C1（setup.sh `--profile` 空白）・C2-C4（heredoc/gate パーサ統一）・C5（ROOT 外 plan-gate false-positive）・G4（exfil 再評価）・iter42 既知限界（chmod の operand 後フラグ・quoted -C path-with-space）。**やらない**: check-control-plane 再設計。◆**罠（iter41-42 で確立）**: (a) gate 承認は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前設定（pending+ref は contract stale-ref FAIL→record red）。(c) judge は claims/2次意見を current_refs.<gate> report から読む＝承認前 ref 設定が必要（b と両立）。(d) record-test-result は全コード編集後1回（fp bind）。(e) framework 混在 diff は skip-drill＋RED-first TDD。(f) **hook が新 lib を source したら test scratch（TempProjectWithHooks 等）にも同 lib を追加**しないと scratch 経路で fail-closed 赤化（full suite でのみ出る）。(g) `${cmd%%word*}` は ` word`（前置スペース）で境界を取る（path に word 部分文字列が混ざる）。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 42（2026-06-24 全力レビュー Batch 2 のうち G1-G3 guard 網羅・framework・L・v1.14.0 据置）完了。ユーザー承認『推奨で進めて・慎重に・できるだけ自動で』で I3 を iter43 に分離し G1-G3 を先行。brainstorm→plan(grill-plan)→implement(TDD)→grill-code→review→qa→security→deploy→ship を完走。**実装した 3 fix**: G1 hooks/lib/patterns.sh の AEGIS_DESTRUCTIVE_CMD_REGEX に dd of=/recursive chmod(-R/-Rf/-fR/--recursive)/mkfs/shred/system-path truncate-redirect を追加（check-destructive が配列自動 iterate＝コード不変）。G3 patterns.sh に AEGIS_DEPLOY_REGEX を single-source 化（旧 DEPLOY_RE 逐語移設）＝check-deploy-gate が参照・check-cron-gate は inline DANGER_RE を撤去し AEGIS_DESTRUCTIVE_*＋AEGIS_DEPLOY_REGEX＋rm -r 特例の合成に置換（G1 の新破壊パターンを自動継承）。G2 check-secrets.sh に _aegis_git_dir_args を追加し `git -C/--git-dir commit` で対象 repo の staged-diff を scan（旧: hook CWD で空振り＝staged .env 見逃しの fail-open を解消）。**grill-code 由来の修正**: truncate regex を (^|[^0-9>]) に（2>/etc fd-redirect 誤検知）・/dev を一覧除外（>/dev/null）・quoted -C の引用符 strip。**test infra 修正**: TempProjectWithHooks に patterns.sh symlink 追加（G3 で deploy-gate が patterns.sh を source＝scratch 経路で fail-closed 赤化した・iter36/39 同 class）。**ゲート（L＝全必須）**: review🟢（盲検2次 maintainability+security とも approve_with_notes・指摘は承認前に反映）／qa🟡ack（skip-drill＝framework 混在 diff・代替 RED-first TDD）／security🟢ack（G2 は fail-open を塞ぐ純増・G1/G3 は既存 deny を弱めず＝deploy regex 逐語・cron は superset・F1 quoted-path-with-space は Low/baseline 同等）／deploy🟢ack。**検証**: full suite 1067 passed/1 skip（record green）・contract full PASS・status_doctor PASS・bash -n 全 hook・git mode-flip なし。**out-of-scope（文書化）**: git-push-deploy・$V deploy 変数間接（SF-004）・generic truncate。LEARNINGS 5件追記。push は yuuya-miyagaki（tigereye は 403）。"
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 41（2026-06-24 全力レビュー Batch 1・framework・L・v1.14.0 据置）完了。/clear→/recover で復帰し rollover（iteration 41・phase=brainstorm・task_size S→L・requirements ref を docs/full-review-2026-06-24-hooks-gates-distribution.md に更新）→ brainstorm→plan(grill-plan)→implement→grill-code→review→qa→security→deploy→ship を完走。**実装した 6 fix**: D1 standard profile に judge ツールチェーン依存閉包を同梱（build-judge-card+run-test-strength-drill=required・record-test-result+fingerprint.sh=recommended・README 件数 20/10 更新）＝standard で gate 承認可能化／D2 Task 完了強制 hook（check-task-created/completed）を standard profile（hooks_include+required_hook_scripts）・active settings・contract self-check（check_active_settings_core_hooks）に配線／D3 setup.sh が再 install で framework 所有（hooks/scripts/templates/.claude/{skills,agents,commands,rules}/bin）を diff-gated .bak つき上書き・user 所有は保全／D4 壊れ settings を無警告全消しせず stderr 警告／I1 post-status-audit を PostToolUse fail-closed 化（safety.sh に block 版 helper・別マーカー POSTTOOL で 12-hook byte-identity 非破壊）／I2 完了evidence を STATUS 不在/None-frontmatter で violation 化。**ゲート（L＝全必須）**: review🟢（盲検2次 security+maintainability とも approve_with_notes・Critical=契約が gitignored settings 依存で非再現→不在 skip 化で修正済）／qa🟡ack（skip-drill＝framework 混在 L diff に B1 構造的不適用・代替 RED-first TDD 実証）／security🟢ack（新規脆弱性なし・Low residual symlink=SF-004 受容）／deploy🟢ack（framework=main commit がデプロイ）。**検証**: full suite 1053 passed/1 skip（record green）・contract full PASS・status_doctor PASS・standard install で --profile=standard PASS 実機確認・git mode-flip なし。**罠を記録（next_action 参照）**: gate コマンドを head にパイプ→SIGPIPE で STATUS 書込み前中断／ref は承認直前設定／record は全コード編集後1回。SF-006 を I1/I2 対処済・I3 は Batch 2 へ。push は yuuya-miyagaki。"
  - date: "2026-06-23"
    mode: Dev
    phase: "ship"
    note: "iteration 40（moat 自動解錠バグ修正・framework・S・hooks/lib/cp-lock.sh・v1.14.0）完了・/recover で継続。**根本原因（iter39 発見→iter40 で bash -x 確証）**: post-status-audit は STATUS 編集で発火し aegis_cp_apply framework→aegis_cp_unlock→chmod -R u+w まで実行していた（＝hook 不発火説は反証）。真因は **Claude Code hook サンドボックスで `chmod -R <dir>` がトップ階層 CP ディレクトリのみ変更しネストファイルに再帰しない**（同 chmod -R を Bash ツールで呼ぶと完全再帰＝環境差）→ dir 解錠/nested 施錠の desync を dir-only sentinel `[ -w hooks ]` が解錠済と誤認し no-op 固定。**修正**: aegis_cp_lock/unlock の `chmod -R` を `find \"$p\" -exec chmod {} +` に変更（lock/unlock 両方向・hook 環境で完全再帰を lock→STATUS編集 trigger→full-unlock 再現で実証）。sentinel は完全再帰なら正確で据置（YAGNI）。ヘッダに『chmod -R 差し戻し禁止』明記。**ゲート（framework S＝review のみ必須・qa/security/deploy size-skip）**: review🟢（judge🟢 tests green・盲検 security 2次 approve＝挙動等価を nested/単一ファイル/空/space/symlink で実測一致・lock=a-w/unlock=u+w でセキュリティ無退行・既存 test_lock_blocks_all_write_forms/test_unlock_restores_writability が nested flip を被覆）。Minor 2件（stale 'chmod -R' 文言＝是正済／find nonexistent rc は [ -e ] ゲートで不発）。**検証**: bash -n PASS・cp-lock 15 tests・full suite 1038 passed/1 skip・record green・contract PASS（版 1.14.0）・git mode-flip なし。**罠を記録**: current_refs.<gate> をセットしたら approve まで suite/contract を走らせない（pending+ref は stale 判定で赤）。LEARNINGS 更新（conf6→conf9＝chmod -R は hook サンドボックスで再帰せず＝find -exec を使う）。push は yuuya-miyagaki。"
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
