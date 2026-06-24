---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: ship
task_type: framework
task_size: M
task_size_rationale: "iteration 44 = full-review C5: check-gate.sh が ROOT 外の Edit/Write 対象にも plan-gate を適用し、auto-memory 等を false-positive deny する不具合の修正。size=M（production 1=check-gate.sh ＋ test 1=新規 behavioral test の 2 files）。緩和系の変更ゆえ security gate は必須＝S（security skip）不可。deploy は M の size routing で自動 exempt（hook ロジック修正で deploy 相互作用なし）。設計: docs/specs/2026-06-25-iter44-root-external-plan-gate-design.md。**やらない**: 相対 ROOT 外 allow 化・グローバル ~/.claude 設定保護・check-control-plane 変更。"
iteration: 44
ui_surface: false
last_updated: "2026-06-25T02:10:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/full-review-2026-06-24-hooks-gates-distribution.md
  plan: docs/plans/2026-06-25-iter44-root-external-plan-gate-implementation-plan.md
  spec: docs/specs/2026-06-25-iter44-root-external-plan-gate-design.md
  review: docs/qa-reports/iter44-review.md
  qa: docs/qa-reports/iter44-qa.md
  security: docs/qa-reports/iter44-security.md
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
  - type: "second-opinion-v0122-r6-r9"
    scope: "v0.12.2 実装後 4 ラウンドレビュー"
    findings: "Round 6 (P1×2, P2×1: pre-compact exit 2 / minimal-project / test rc), Round 7 (P1×1, P3×1: git add 漏れ / テスト件数表記), Round 8 (P2×1, P3×1: stale last_updated / grep 自己マッチ), Round 9 (P3×2: コメント不整合)"
    resolution: "9件全反映。tier 1/2 PASS、134 tests PASS、本体と minimal-project 完全同期確認済み。"
next_action: "**【iteration 44 完了（framework・M・C5 ROOT外 plan-gate/Client-mode false-positive 修正／review🟢+qa🟢+security🟡ack 全 approved・deploy は M で size-exempt／commit 済・push 未＝yuuya-miyagaki）／次は iteration 45・/clear 後 /recover 用アンカー・2026-06-25】** ◆**push**: iter44 commit がローカル ahead。`gh auth switch --user yuuya-miyagaki && git push`（tigereye は 403）。◆**まず rollover**: dev ゲートを pending（update-gate.sh reset 各）、iteration=45・phase=brainstorm・current_refs null（requirements 保持）・task_type/size は **update-task.sh 経由**・session_history 最古剪定（max 3）。◆**iter45 候補（full-review 残）**: C4（gate 値パーサ bash frontmatter.sh:69-73 vs python check_status.py:283 の乖離→strict allowlist 統一・整合性／**乖離の到達可能性を実証してから security 主張**）・C2（setup.sh:46 が --profile=* のみ受理・空白形式で即死）＋C3（setup.sh:100-111 heredoc <<'PY' で $FRAMEWORK_ROOT 非展開→version 常に unknown）・G4（Edit/Write の .env 生成・curl exfil 再評価・一部 by-design）。**やらない**: check-control-plane 再設計。◆**罠（iter41-44 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-25"
    mode: Dev
    phase: "ship"
    note: "iteration 44（full-review C5＝check-gate.sh の ROOT 外 plan-gate/Client-mode false-positive 修正・framework・M・v1.14.0 据置）完了。/clear→/recover→rollover（iter44・dev ゲート全 pending・push 済 origin/main=93fc166）→ brainstorm(grill-premise)→plan(grill-plan)→implement(TDD・RED-first)→grill-code→review→qa→security→ship を完走（deploy は M で size-exempt）。**実装（1 file ＋ test）**: hooks/check-gate.sh に control-file 判定後・mode/plan 判定前の short-circuit を追加＝`$ROOT/*`・`$ROOT_REAL/*` 以外の絶対パス→emit_allow。auto-memory（`~/.claude/.../memory/`）の false-positive deny を解消。control/templates/docs/project-code は不変。新規 tests/test_check_gate_root_external.py（10 ケース・RED-first）。**罠の発見/対処**: (1) 挿入位置が Client-mode deny も飛ばす→意図的決定（auto-memory は mode 非依存）＋test_e/f で担保（grill-plan #1）。(2) RED 厳密 assert（`{}`＝emit_allow）で空振り防止。(3) judge `read_test_result` の newest-observed-without-marker で security 直前に tests=unverified→対象 ref を null にして record-test-result 再実行で解消。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢（盲検2次 testing+maintainability とも approve_with_notes・Major=false-green→positive control test_i／Minor=sibling→test_j・全反映）／qa🟢（**本物の B1 mutation drill PASS**＝2 mutant caught・iter43 skip-drill と異なり成立）／security🟡ack（盲検 security＝net-positive・Low1=case-variant backstop 喪失の特徴づけ訂正・受容／deps 新規ゼロ advisory）。**検証**: full suite green（record・fp 一致）・新規 10 tests・bash -n OK・git mode-flip なし。LEARNINGS 6件追記。push 未＝yuuya-miyagaki（gh auth switch）。"
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 43（full-review I3＝task_type/task_size の tamper-evidence・framework・L・v1.14.0 据置）完了。/clear→/recover→rollover（iter43・dev ゲート全 pending・push 済 origin/main=e87174e）→ brainstorm(grill-premise)→plan(grill-plan)→implement(TDD)→grill-code→review→qa→security→deploy→ship を完走。**実装（6 task）**: T1 新規 hooks/lib/snapshot.sh＝`aegis_write_snapshot` 単一関数（gate/phase/mode＋**task_type/task_size**をアトミック書込み）。T2 3 writer（session-start/update-gate/post-status-audit）の inline snapshot 書込みを helper へ集約（iter37 単一関数＋複数発火点）。T3 新規 scripts/update-task.sh＝task_type/task_size の authorized writer（enum 検証・replace-or-insert・update-gate と同一ロック共有・task_type 変更時 aegis_cp_apply）。T4 post-status-audit に task tamper 検知ループ（gate と同型・`[ -n $OLD ]` 移行猶予）＋**aegis_cp_apply を tamper チェック後へ移動**（`_aegis_relock_from_status` helper＝改竄編集が moat 解錠する前に block／no-baseline first-edit と clean 経路でのみ発火）。T5 docs（CLAUDE.md/state-machine/aegis-brainstorm/bug-diagnosis）を update-task.sh 経由に。T6 snapshot.sh を contract REQUIRED_HOOK_FILES に登録（setup.sh は全 lib 無条件 copy＝配布自動）。**脅威モデル**: LLM self-bypass（外部 adversary 非対象）・tamper-evidence であって proof でない（cross-session re-bless 受容）。**grill-code Critical**: update-task.sh の task_size 行欠落時 silent no-op→replace-or-insert 化＋task_type 欠落は明示エラー。**盲検2次（review gate）**: maintainability＋testing とも approve_with_notes→全 notes 反映（authorized-path 非block の e2e test 追加・enum-parity test 追加・STATUS_FILE_CUR 撤去）。**ゲート（L＝全必須）**: review🟢／qa🟡ack（framework 混在 diff で coverage floor 不成立＝skip＋代替実証: RED-first TDD＋手動 mutant2件 tamper比較/cp_apply トリガを != →= で RED 実測・revert）／security🟢ack（盲検 security agent＝net 改善・raw task_type→framework 即時解錠経路を封鎖・依存監査 unverified は新規依存ゼロで advisory）／deploy🟢。**検証**: full suite 1097 passed/1 skip（record green）・contract full PASS・status_doctor PASS・context budget PASS・bash -n 全 hook/script・git mode-flip なし。**罠（追記）**: ref set→approve 間に record(=contract) を挟むと stale-ref FAIL→赤（qa で実体験）。LEARNINGS 7件追記。push は yuuya-miyagaki（gh auth switch で session から可）。"
  - date: "2026-06-24"
    mode: Dev
    phase: "ship"
    note: "iteration 42（2026-06-24 全力レビュー Batch 2 のうち G1-G3 guard 網羅・framework・L・v1.14.0 据置）完了。ユーザー承認『推奨で進めて・慎重に・できるだけ自動で』で I3 を iter43 に分離し G1-G3 を先行。brainstorm→plan(grill-plan)→implement(TDD)→grill-code→review→qa→security→deploy→ship を完走。**実装した 3 fix**: G1 hooks/lib/patterns.sh の AEGIS_DESTRUCTIVE_CMD_REGEX に dd of=/recursive chmod(-R/-Rf/-fR/--recursive)/mkfs/shred/system-path truncate-redirect を追加（check-destructive が配列自動 iterate＝コード不変）。G3 patterns.sh に AEGIS_DEPLOY_REGEX を single-source 化（旧 DEPLOY_RE 逐語移設）＝check-deploy-gate が参照・check-cron-gate は inline DANGER_RE を撤去し AEGIS_DESTRUCTIVE_*＋AEGIS_DEPLOY_REGEX＋rm -r 特例の合成に置換（G1 の新破壊パターンを自動継承）。G2 check-secrets.sh に _aegis_git_dir_args を追加し `git -C/--git-dir commit` で対象 repo の staged-diff を scan（旧: hook CWD で空振り＝staged .env 見逃しの fail-open を解消）。**grill-code 由来の修正**: truncate regex を (^|[^0-9>]) に（2>/etc fd-redirect 誤検知）・/dev を一覧除外（>/dev/null）・quoted -C の引用符 strip。**test infra 修正**: TempProjectWithHooks に patterns.sh symlink 追加（G3 で deploy-gate が patterns.sh を source＝scratch 経路で fail-closed 赤化した・iter36/39 同 class）。**ゲート（L＝全必須）**: review🟢（盲検2次 maintainability+security とも approve_with_notes・指摘は承認前に反映）／qa🟡ack（skip-drill＝framework 混在 diff・代替 RED-first TDD）／security🟢ack（G2 は fail-open を塞ぐ純増・G1/G3 は既存 deny を弱めず＝deploy regex 逐語・cron は superset・F1 quoted-path-with-space は Low/baseline 同等）／deploy🟢ack。**検証**: full suite 1067 passed/1 skip（record green）・contract full PASS・status_doctor PASS・bash -n 全 hook・git mode-flip なし。**out-of-scope（文書化）**: git-push-deploy・$V deploy 変数間接（SF-004）・generic truncate。LEARNINGS 5件追記。push は yuuya-miyagaki（tigereye は 403）。"
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
