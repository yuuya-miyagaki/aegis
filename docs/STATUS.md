---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: ship
task_type: framework
task_size: L
task_size_rationale: "iteration 43 = 2026-06-24 full-review I3: task_type/task_size の tamper-evidence（SF-006）。現状 post-status-audit は snapshot と gate/phase/mode のみ比較し、task_type/task_size は Edit で改竄しても無検知（例: framework→other で CP lock 回避、L→S で gate skip）。本 iteration で task_type/task_size を snapshot に取り込み、authorized write-path 経由のみ変更可能にする。**着手前に設計フォークを brainstorm/grill-premise で決定**（(a) update-task.sh 新設／(b) update-gate.sh 拡張／(c) iteration インクリメント時のみ task_type/size 変更許可）。**chicken-and-egg**: I3 実装後は rollover/brainstorm の Edit による task_type/size 変更が自分でブロックされるため、authorized-path が前提。task_size は plan で確定（暫定 L）。out-of-scope はブレインストームで確定。"
iteration: 43
ui_surface: false
last_updated: "2026-06-24T23:30:00Z"
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
  plan: docs/plans/2026-06-24-iter43-task-tamper-evidence-implementation-plan.md
  spec: docs/specs/2026-06-24-iter43-task-tamper-evidence-design.md
  review: docs/qa-reports/iter43-review.md
  qa: docs/qa-reports/test-strength.md
  security: docs/qa-reports/iter43-security.md
  deploy: docs/qa-reports/iter43-deploy.md
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
next_action: "**【iteration 43 完了（framework・L・I3 task_type/task_size tamper-evidence／review🟢+qa🟡ack+security🟢ack+deploy🟢 全 approved／commit 済・push 未＝yuuya-miyagaki で `git push`）／次は iteration 44・/clear 後 /recover 用アンカー・2026-06-24】** ◆**push**: iter43 の commit がローカル ahead。`gh auth switch --user yuuya-miyagaki && git push`（tigereye は 403）。◆**まず rollover**: dev ゲートを pending（update-gate.sh bare 単独）、STATUS を iteration=44・phase=brainstorm・**task_type/task_size は update-task.sh 経由で変更**（I3 実装後は raw Edit が tamper block される！rollover は update-task.sh --type/--size を使う）・current_refs null（requirements 保持）・session_history 最古剪定（contract max 3）。◆**iter44 候補（full-review 残）**: C1（setup.sh `--profile` 空白）・C2-C4（heredoc/gate パーサ統一）・C5（ROOT 外 plan-gate false-positive）・G4（exfil 再評価）。iter42 既知限界（chmod operand 後フラグ・quoted -C path-with-space）。**やらない**: check-control-plane 再設計。◆**I3 残留（受容・security report）**: cross-session re-bless（SF-004 class）／migration grace 窓／update-task lock orphan-reclaim なし（可用性）。◆**罠（iter41-43 で確立）**: (a) gate 承認出力は **tail**（head は SIGPIPE）。(b) current_refs.<gate> は承認直前設定（pending+ref は contract stale-ref FAIL→record red）。(c) **ref set→approve の間に record-test-result（=full suite→contract）を挟むと stale-ref で赤**（iter43 qa で実体験）＝set→approve を連続、record は approve 後。(d) record-test-result は全コード編集後1回（fp bind・手動 mutant の revert 後も再 record 要）。(e) framework 混在 diff は B1 coverage-floor 不成立→skip＋RED-first TDD＋手動 mutant 実測。(f) hook が新 lib を source したら test scratch（TempProjectWithHooks 等）にも同 lib を追加。(g) **task_type/task_size は update-task.sh 経由のみ（raw Edit は tamper block）**。(h) push は `gh auth switch --user yuuya-miyagaki` で session から可能。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 43（full-review I3＝task_type/task_size の tamper-evidence・framework・L・v1.14.0 据置）完了。/clear→/recover→rollover（iter43・dev ゲート全 pending・push 済 origin/main=e87174e）→ brainstorm(grill-premise)→plan(grill-plan)→implement(TDD)→grill-code→review→qa→security→deploy→ship を完走。**実装（6 task）**: T1 新規 hooks/lib/snapshot.sh＝`aegis_write_snapshot` 単一関数（gate/phase/mode＋**task_type/task_size**をアトミック書込み）。T2 3 writer（session-start/update-gate/post-status-audit）の inline snapshot 書込みを helper へ集約（iter37 単一関数＋複数発火点）。T3 新規 scripts/update-task.sh＝task_type/task_size の authorized writer（enum 検証・replace-or-insert・update-gate と同一ロック共有・task_type 変更時 aegis_cp_apply）。T4 post-status-audit に task tamper 検知ループ（gate と同型・`[ -n $OLD ]` 移行猶予）＋**aegis_cp_apply を tamper チェック後へ移動**（`_aegis_relock_from_status` helper＝改竄編集が moat 解錠する前に block／no-baseline first-edit と clean 経路でのみ発火）。T5 docs（CLAUDE.md/state-machine/aegis-brainstorm/bug-diagnosis）を update-task.sh 経由に。T6 snapshot.sh を contract REQUIRED_HOOK_FILES に登録（setup.sh は全 lib 無条件 copy＝配布自動）。**脅威モデル**: LLM self-bypass（外部 adversary 非対象）・tamper-evidence であって proof でない（cross-session re-bless 受容）。**grill-code Critical**: update-task.sh の task_size 行欠落時 silent no-op→replace-or-insert 化＋task_type 欠落は明示エラー。**盲検2次（review gate）**: maintainability＋testing とも approve_with_notes→全 notes 反映（authorized-path 非block の e2e test 追加・enum-parity test 追加・STATUS_FILE_CUR 撤去）。**ゲート（L＝全必須）**: review🟢／qa🟡ack（framework 混在 diff で coverage floor 不成立＝skip＋代替実証: RED-first TDD＋手動 mutant2件 tamper比較/cp_apply トリガを != →= で RED 実測・revert）／security🟢ack（盲検 security agent＝net 改善・raw task_type→framework 即時解錠経路を封鎖・依存監査 unverified は新規依存ゼロで advisory）／deploy🟢。**検証**: full suite 1097 passed/1 skip（record green）・contract full PASS・status_doctor PASS・context budget PASS・bash -n 全 hook/script・git mode-flip なし。**罠（追記）**: ref set→approve 間に record(=contract) を挟むと stale-ref FAIL→赤（qa で実体験）。LEARNINGS 7件追記。push は yuuya-miyagaki（gh auth switch で session から可）。"
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 42（2026-06-24 全力レビュー Batch 2 のうち G1-G3 guard 網羅・framework・L・v1.14.0 据置）完了。ユーザー承認『推奨で進めて・慎重に・できるだけ自動で』で I3 を iter43 に分離し G1-G3 を先行。brainstorm→plan(grill-plan)→implement(TDD)→grill-code→review→qa→security→deploy→ship を完走。**実装した 3 fix**: G1 hooks/lib/patterns.sh の AEGIS_DESTRUCTIVE_CMD_REGEX に dd of=/recursive chmod(-R/-Rf/-fR/--recursive)/mkfs/shred/system-path truncate-redirect を追加（check-destructive が配列自動 iterate＝コード不変）。G3 patterns.sh に AEGIS_DEPLOY_REGEX を single-source 化（旧 DEPLOY_RE 逐語移設）＝check-deploy-gate が参照・check-cron-gate は inline DANGER_RE を撤去し AEGIS_DESTRUCTIVE_*＋AEGIS_DEPLOY_REGEX＋rm -r 特例の合成に置換（G1 の新破壊パターンを自動継承）。G2 check-secrets.sh に _aegis_git_dir_args を追加し `git -C/--git-dir commit` で対象 repo の staged-diff を scan（旧: hook CWD で空振り＝staged .env 見逃しの fail-open を解消）。**grill-code 由来の修正**: truncate regex を (^|[^0-9>]) に（2>/etc fd-redirect 誤検知）・/dev を一覧除外（>/dev/null）・quoted -C の引用符 strip。**test infra 修正**: TempProjectWithHooks に patterns.sh symlink 追加（G3 で deploy-gate が patterns.sh を source＝scratch 経路で fail-closed 赤化した・iter36/39 同 class）。**ゲート（L＝全必須）**: review🟢（盲検2次 maintainability+security とも approve_with_notes・指摘は承認前に反映）／qa🟡ack（skip-drill＝framework 混在 diff・代替 RED-first TDD）／security🟢ack（G2 は fail-open を塞ぐ純増・G1/G3 は既存 deny を弱めず＝deploy regex 逐語・cron は superset・F1 quoted-path-with-space は Low/baseline 同等）／deploy🟢ack。**検証**: full suite 1067 passed/1 skip（record green）・contract full PASS・status_doctor PASS・bash -n 全 hook・git mode-flip なし。**out-of-scope（文書化）**: git-push-deploy・$V deploy 変数間接（SF-004）・generic truncate。LEARNINGS 5件追記。push は yuuya-miyagaki（tigereye は 403）。"
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 41（2026-06-24 全力レビュー Batch 1・framework・L・v1.14.0 据置）完了。/clear→/recover で復帰し rollover（iteration 41・phase=brainstorm・task_size S→L・requirements ref を docs/full-review-2026-06-24-hooks-gates-distribution.md に更新）→ brainstorm→plan(grill-plan)→implement→grill-code→review→qa→security→deploy→ship を完走。**実装した 6 fix**: D1 standard profile に judge ツールチェーン依存閉包を同梱（build-judge-card+run-test-strength-drill=required・record-test-result+fingerprint.sh=recommended・README 件数 20/10 更新）＝standard で gate 承認可能化／D2 Task 完了強制 hook（check-task-created/completed）を standard profile（hooks_include+required_hook_scripts）・active settings・contract self-check（check_active_settings_core_hooks）に配線／D3 setup.sh が再 install で framework 所有（hooks/scripts/templates/.claude/{skills,agents,commands,rules}/bin）を diff-gated .bak つき上書き・user 所有は保全／D4 壊れ settings を無警告全消しせず stderr 警告／I1 post-status-audit を PostToolUse fail-closed 化（safety.sh に block 版 helper・別マーカー POSTTOOL で 12-hook byte-identity 非破壊）／I2 完了evidence を STATUS 不在/None-frontmatter で violation 化。**ゲート（L＝全必須）**: review🟢（盲検2次 security+maintainability とも approve_with_notes・Critical=契約が gitignored settings 依存で非再現→不在 skip 化で修正済）／qa🟡ack（skip-drill＝framework 混在 L diff に B1 構造的不適用・代替 RED-first TDD 実証）／security🟢ack（新規脆弱性なし・Low residual symlink=SF-004 受容）／deploy🟢ack（framework=main commit がデプロイ）。**検証**: full suite 1053 passed/1 skip（record green）・contract full PASS・status_doctor PASS・standard install で --profile=standard PASS 実機確認・git mode-flip なし。**罠を記録（next_action 参照）**: gate コマンドを head にパイプ→SIGPIPE で STATUS 書込み前中断／ref は承認直前設定／record は全コード編集後1回。SF-006 を I1/I2 対処済・I3 は Batch 2 へ。push は yuuya-miyagaki。"
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
