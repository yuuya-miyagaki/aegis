---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: M
task_size_rationale: "iteration 52（framework・確認(permission prompt)交通整理＝allow-list の read-only 完全性ガード＋拡張）= M。footprint は templates/hooks.template.json（read-only スクリプト 3 件＋git show を allow 追加）＋tests（分類表＋完全性ガード）＋README＝3 ファイル。production code 無改変。必須ゲート review+qa+security（deploy は M で size-exempt）。"
iteration: 52
ui_surface: false
last_updated: "2026-06-28T13:25:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: pending
  dev_ready_for_client: approved
current_refs:
  requirements: []
  plan: docs/plans/2026-06-28-permission-allowlist-completeness-implementation-plan.md
  spec: docs/specs/2026-06-28-permission-allowlist-completeness-design.md
  review: docs/qa-reports/iter52-review.md
  qa: docs/qa-reports/iter52-qa.md
  security: docs/qa-reports/iter52-security.md
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
next_action: "**【iteration 52＝allow-list read-only 完全性ガード＋拡張（framework・M・v1.14.0 据置・phase=docs・全必須ゲート✅＋dev_ready_for_client✅・push 済 origin/main=5660f99・iter52 完全クローズ・2026-06-28）】** ◆**現在地**: phase=docs、**iteration 52 完全クローズ**。review✅(approve_with_notes・盲検 reviewer-testing)／qa✅(B1 DRILL 5/5 caught＋full suite 1172 passed/1 skip)／security✅(approve・盲検 security agent・deps ack)／dev_ready_for_client✅／deploy は M で size-exempt。commit 5660f99（feat）・push 済（origin/main 同期・yuuya-miyagaki）・ツリー clean。 ◆**成果**: tests/test_permission_allowlist_install.py に SCRIPT_CLASS（18 entrypoints）＋完全性ガード 6 テスト／templates/hooks.template.json allow 10→14（check_reference_drift/learnings_search/lint_names＋git show・context_budget は grill-code🔴で must_prompt 再分類除外）／README allow 節／LEARNINGS 2 件。 ◆**次アクション**: iter52 クローズ済。次は **/clear→/recover** → rollover（iter50 剪定・iteration=53・dev ゲット reset・requirements 暫定[]）→ 次テーマ。 ◆**次テーマ候補（参考・未着手）**: profile 別 allow（実在の第2 audience 出現時）／確認の平易化 slice2（実ユーザーの混乱を観測してから）／Edit/Write/MCP は moat 衝突で非推奨。 ◆**罠（iter41-49 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-28"
    mode: Dev
    phase: "docs"
    note: "iteration 52（framework・確認(permission prompt)交通整理＝allow-list read-only 完全性ガード＋拡張・M・v1.14.0 据置）完了。/clear→/recover→rollover（iter49 剪定・iteration=52・dev ゲット全 reset）→ brainstorm(grill-premise が当初 slice2『確認の平易化』を非実在ユーザー＆検証不能で却下→対抗馬『profile 別 reversible-write allow』も commit oversight 衝突＆価値薄で延期→『read-only 完全性ガード＋拡張』へ収束。emit_ask で reason 注入の足場が既在を実証し slice2 の悲観を訂正)→plan→grill-plan(致命3: ①commit timing×qa B1 drill 衝突→implement 中 commit 禁止 ②membership を substring→_matches 実証 ③SCRIPT_CLASS↔SHOULD リスト整合 cross-check 追加)→implement(TDD RED-first・6 テスト→allow 4 件 GREEN)→grill-code(🔴 context_budget は default check 読取でも --tighten/--seed が追跡 config 書込み＝must_prompt へ再分類し allow 除外／🟡 _rep_invocation の python3 固定を .sh 分岐)→review(盲検2次 reviewer-testing=approve_with_notes・分類を独自ソース照合で全件追認・Minor1 learnings_search 呼出例訂正)→qa(B1 DRILL PASS 5/5 caught・mutant は template allow 行＋テスト内 data 行(分類反転)＋import 行・README は docs 送りで floor 除外／full suite 1172 passed/1 skip・record-test-result green)→security(盲検2次 security agent=approve・新規 allow 4 件を全パス read-only 実証・mutator/exec/destructive 排除・moat 不変・secrets/deps clean／Low=exec-gadget guard の subprocess 非カバーは偽陽性で一般化不能を実証し受容・deps ack)→ship→docs。実装(code 2 ファイル＋docs): tests/test_permission_allowlist_install.py に SCRIPT_CLASS（18 entrypoints・3 分類）＋完全性ガード 6 テスト＋SHOULD_MATCH 拡張／templates/hooks.template.json allow 10→14／README allow 節更新。LEARNINGS 2 件追記（tech conf8 intent ベース分類＋mode 依存 write 全パス監査／process conf7 drill floor は tracked 非docs 全変更＝README docs 送り・test file も分類反転 mutant で drillable）。TO-CLIENT/MANUAL/RUNBOOK/UAT は internal framework iteration で N/A。全必須ゲート approved＋dev_ready_for_client approved。commit 5660f99・push 済 origin/main=5660f99（yuuya-miyagaki）＝iteration 52 完全クローズ。"
  - date: "2026-06-28"
    mode: Dev
    phase: "docs"
    note: "iteration 51（framework・確認(permission prompt)交通整理 第一スライス＝安全な読み取り/記録系の permissions.allow 同梱・M・v1.14.0 据置）完了。/clear→/recover→/retro→rollover（iter48 剪定・iteration=51・dev ゲット全 reset）→ brainstorm(grill-premise が当初テーマ dogfood を YAGNI で倒し、ユーザー一次痛『確認が多い・知識の乏しい人には技術的確認が理解不能』へ再方向付け。研究で emit_allow={} ＝settings allow が唯一のプロンプト抑制レバー／hook は allow と独立に常時実行＝moat 保全を確定。設計C＝読み取り/記録系のみ allow・状態変更/危険系はプロンプト維持・全プロファイル同梱)→plan→grill-plan(§0 マッチャ仕様確定／proxy テスト／dogfood local 適用／union 所有権／git 素 subcommand 形・pytest 2形・相対パス)→implement(TDD RED-first)→grill-code(🔴 record-test-result の exec gadget=args.command を drill._execute＝allow から除外＋guard テスト／🟡 run-test-strength-drill 除外／🟡 full の permissions 無条件再代入で将来 deny/ask clobber→fresh dict＋他キー保全／pytest residual は security で明記)→review(盲検2次 reviewer-maintainability=approve_with_notes・Finding2 独立指摘→解消・Finding1 build-judge-card 将来 exec を guard テストで固定)→qa(B1 DRILL PASS 3/3 caught・tracked task code の hunk ごとに mutant・新規 untracked テストは floor 対象外／full suite 1166 passed/1 skip)→security(盲検2次=approve・全 allow-listed script の exec sink 監査で gadget 不在・moat intact・secrets/deps clean・deps ack)→ship→docs 完走（deploy は M で size-exempt）。実装（code 3 ファイル）: templates/hooks.template.json に permissions.allow（10 entries・gadget 2件除外）／bin/setup.sh:generate_settings() を filtered carry＋union（fresh dict・冪等）／tests/test_permission_allowlist_install.py（9 テスト）。README に allow-list 節追記。本リポ local .claude/settings.local.json に allow set を union 適用済み（5→15・uncommitted/gitignored）。LEARNINGS 4 件追記（conf8 permission prompt 機構／conf8 exec gadget／conf7 settings 生成 install 実体／conf7 Bash matcher 仕様）。TO-CLIENT/MANUAL/RUNBOOK/UAT は internal framework iteration で N/A。全必須ゲート approved＋dev_ready_for_client approved。"
  - date: "2026-06-27"
    mode: Dev
    phase: "docs"
    note: "iteration 50（framework・(A) doc(CLAUDE.md/rules)→scripts/* 参照整合性 guard・M・v1.14.0 据置）work 完了。/clear→/recover→rollover（iter47 剪定・iteration 49→50・dev ゲット全 reset）→ brainstorm(grill-premise で premise を**実穴ゼロ**へ縮小＝install 実体では壊れた参照なし。CLAUDE.md は templates/CLAUDE.template.md へ remap で参照は check_framework_contract.py のみ＝maintainer 専用の意図的非同梱／rules/state-machine.md→update-task.sh は full+standard で充足済。guard-only と確定・honest framing)→plan→grill-plan(致命①=アンカー parse の fail-open／②allow-list vs template 編集の決定／③referrer 差明記／④surfaces 列挙＋dead-key／⑤qa 方針／YAGNI=_doc_script_edges 別名 を反映)→implement(TDD RED-first・各 helper RED→GREEN)→grill-code(🟡=_skill_script_edges を doc に当てる命名を `_doc_script_edges` 別名で自己説明化)→review(盲検2次 reviewer-testing=approve_with_notes・F1 quoted-comment parse の取りこぼし=fail-closed だが robustness gap→行コメント事前除去＋専用テスト RED→GREEN で解消／F2 scope 境界・F3 marginal=受容)→qa(B1 drill **PASS 3/3 caught**・baseline green＝append-only 単一ランで coverage-floor 充足・iter49 の docstring 別ラン skip を回避／full suite 1157 passed/1 skip)→security(盲検2次 security agent=approve・material finding ゼロ・path-traversal は whitelist で到達不能と end-to-end トレース・🟡 tests/deps を実証付き ack)→ship→docs を完走（deploy は M で size-exempt）。**実装（code 1 ファイル）**: tests/test_profile_referential_integrity.py に iter50 セクション＝`_DOC_TEMPLATE_REMAP`/`_doc_install_source`(install 実体解決・fail-closed)／`_setup_resolve_remap`+`_SETUP_CASE_RE`(コメント耐性 parse)／コメント耐性アンカー(drift/dead-key/parse 失敗 3 mutation 全捕捉)／`_shipped_doc_surfaces`／`INTENTIONAL_UNSHIPPED_DOC`(3 profile×check_framework_contract.py・referrer 差明記・rot 検知)／本体 cross-check／`_doc_script_edges` 別名＋12 単体。production code・profile・README 無改変。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢／qa🟢(drill PASS 3/3)／security🟡ack(tests=verified＋deps 新規ゼロ)。**検証**: test file 36 passed・full suite 1157 passed/1 skip・contract/status_doctor PASS。LEARNINGS 3 件追記（tech: doc-surface install 実体＋アンカー conf8／process: append-only で drill floor 充足 conf8・guard-only honest framing conf7）。TO-CLIENT/MANUAL/RUNBOOK/UAT は internal framework iteration で N/A。commit 15d464d・push 済 origin/main=15d464d（yuuya-miyagaki）・dev_ready_for_client approved＝**iteration 50 完全クローズ**。"
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
