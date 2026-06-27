---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: M
task_size_rationale: "iteration 50（framework・(A) doc(CLAUDE.md/rules)→scripts/* 参照整合性 guard）= **M（確定）**。grill-premise で **実穴ゼロ**を実証＝本イテレーションは guard-only（honest framing 厳守）。実 footprint は test 1 ファイル（素直には S）だが、guard の歯＝『本当に違反を捕まえるか』の独立 qa mutation 実証を保持するため M を deliberate に採用（iter48/49 と同クラスの established practice。size gaming でなく検証リスクに基づく）。必須ゲート review+qa+security（deploy は M で size-exempt）。"
iteration: 50
ui_surface: false
last_updated: "2026-06-27T05:20:00Z"
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
  plan: docs/plans/2026-06-27-doc-script-ref-integrity-implementation-plan.md
  spec: docs/specs/2026-06-27-doc-script-ref-integrity-design.md
  review: docs/qa-reports/iter50-review.md
  qa: docs/qa-reports/iter50-qa.md
  security: docs/qa-reports/iter50-security.md
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
next_action: "**【iteration 50＝(A) doc(CLAUDE.md/rules)→scripts/* 参照整合性 guard（framework・M・v1.14.0 据置・phase=docs・全必須ゲート✅＋dev_ready_for_client✅・push 済 origin/main=15d464d・iter50 完全クローズ・2026-06-27）】** ◆**現在地**: phase=docs、**iteration 50 完全クローズ**。review✅(approve_with_notes)／qa✅(B1 drill PASS 3/3 caught・full suite 1157 passed/1 skip)／security✅(ack: tests=verified＋deps 新規ゼロ・盲検2次 approve)／dev_ready_for_client✅／deploy は M で size-exempt。commit 15d464d（feat）＋ status anchor・push 済（origin/main 同期・yuuya-miyagaki）・**iteration 50 完全クローズ・ツリー clean**。◆**成果（code 1 ファイル・guard-only）**: tests/test_profile_referential_integrity.py に iter50 doc→script 参照整合性検査を追加。install 実体（CLAUDE.md=templates/CLAUDE.template.md remap／rules=verbatim）を読む `_doc_install_source`＋明示 map（fail-closed）／setup.sh:resolve_source と一致を assert する**コメント耐性アンカー**（drift/dead-key/parse 失敗の3 mutation 全捕捉）／`_shipped_doc_surfaces`／`INTENTIONAL_UNSHIPPED_DOC`(3 profile×check_framework_contract.py・referrer 差明記・rot 検知)／本体 cross-check（allow-list トグルで RED→GREEN 手動実測）。`_doc_script_edges`/`_violations`/`_shipped_scripts_any` 再利用。production code・profile・README 無改変。◆**honest framing**: grill-premise で**実穴ゼロ**を実証＝guard-only（「実穴を直した」とは言わない・全 install surface 網羅＋maintainer 参照の allow-list 明示化）。◆**検証**: test file 36 passed・full suite 1157 passed/1 skip・B1 drill PASS(3/3)・contract/status_doctor PASS。LEARNINGS 3 件追記（tech1 doc-surface install 実体＋アンカー／process2 append-only で drill floor 充足・guard-only honest framing）。TO-CLIENT/MANUAL/RUNBOOK/UAT は internal framework iteration で N/A。◆**次アクション**: iter50 クローズ済。次は **/clear→/recover でコンテキスト刷新** → rollover（iter48 剪定・iteration=51・dev ゲット reset・requirements は新テーマで再定義 or 暫定[]）→ 次テーマ着手。◆**次イテレーション候補（未着手・参考）**: rules/CLAUDE.md 以外の新 doc surface が将来 script を参照したら同機構で別スライス（盲検 F2 の scope 境界）／v0.13.0 残項目〔Phase 0a 着手 GO 済〕。◆**罠（iter41-49 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-27"
    mode: Dev
    phase: "docs"
    note: "iteration 50（framework・(A) doc(CLAUDE.md/rules)→scripts/* 参照整合性 guard・M・v1.14.0 据置）work 完了。/clear→/recover→rollover（iter47 剪定・iteration 49→50・dev ゲット全 reset）→ brainstorm(grill-premise で premise を**実穴ゼロ**へ縮小＝install 実体では壊れた参照なし。CLAUDE.md は templates/CLAUDE.template.md へ remap で参照は check_framework_contract.py のみ＝maintainer 専用の意図的非同梱／rules/state-machine.md→update-task.sh は full+standard で充足済。guard-only と確定・honest framing)→plan→grill-plan(致命①=アンカー parse の fail-open／②allow-list vs template 編集の決定／③referrer 差明記／④surfaces 列挙＋dead-key／⑤qa 方針／YAGNI=_doc_script_edges 別名 を反映)→implement(TDD RED-first・各 helper RED→GREEN)→grill-code(🟡=_skill_script_edges を doc に当てる命名を `_doc_script_edges` 別名で自己説明化)→review(盲検2次 reviewer-testing=approve_with_notes・F1 quoted-comment parse の取りこぼし=fail-closed だが robustness gap→行コメント事前除去＋専用テスト RED→GREEN で解消／F2 scope 境界・F3 marginal=受容)→qa(B1 drill **PASS 3/3 caught**・baseline green＝append-only 単一ランで coverage-floor 充足・iter49 の docstring 別ラン skip を回避／full suite 1157 passed/1 skip)→security(盲検2次 security agent=approve・material finding ゼロ・path-traversal は whitelist で到達不能と end-to-end トレース・🟡 tests/deps を実証付き ack)→ship→docs を完走（deploy は M で size-exempt）。**実装（code 1 ファイル）**: tests/test_profile_referential_integrity.py に iter50 セクション＝`_DOC_TEMPLATE_REMAP`/`_doc_install_source`(install 実体解決・fail-closed)／`_setup_resolve_remap`+`_SETUP_CASE_RE`(コメント耐性 parse)／コメント耐性アンカー(drift/dead-key/parse 失敗 3 mutation 全捕捉)／`_shipped_doc_surfaces`／`INTENTIONAL_UNSHIPPED_DOC`(3 profile×check_framework_contract.py・referrer 差明記・rot 検知)／本体 cross-check／`_doc_script_edges` 別名＋12 単体。production code・profile・README 無改変。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢／qa🟢(drill PASS 3/3)／security🟡ack(tests=verified＋deps 新規ゼロ)。**検証**: test file 36 passed・full suite 1157 passed/1 skip・contract/status_doctor PASS。LEARNINGS 3 件追記（tech: doc-surface install 実体＋アンカー conf8／process: append-only で drill floor 充足 conf8・guard-only honest framing conf7）。TO-CLIENT/MANUAL/RUNBOOK/UAT は internal framework iteration で N/A。commit 15d464d・push 済 origin/main=15d464d（yuuya-miyagaki）・dev_ready_for_client approved＝**iteration 50 完全クローズ**。"
  - date: "2026-06-27"
    mode: Dev
    phase: "docs"
    note: "iteration 49（framework・配布 self-containment 射程拡大＝skill→script 参照整合性検査＋update-task.sh 同梱・M・v1.14.0 据置）完了。/clear→/recover→rollover（iter46 剪定）→ brainstorm(grill-premise で配布テーマの 3 穴候補を一次精査)→plan→**grill-plan で premise 訂正＝3 穴中 #1(validate)/#2(retro) は false positive**（setup.sh:resolve_source が templates/commands の scaffold-safe 版を install＝graceful degrade。grill-premise が dogfood .claude/commands を読んだ誤り）→実穴を #3 skill→update-task.sh の 1 件に縮小→implement(TDD RED-first)→grill-code(🟡3 反映: _shipped_skill_docs を全 skill .md に拡張／helper 整合テスト／agents 射程明記)→review(盲検2次 reviewer-maintainability=approve_with_notes・F3=standard update-task.sh 無保護を指摘)→qa(B1: coverage-floor が module-docstring 精度 hunk と衝突→auditable skip＋手動 mutation **4/4 caught** 実証・F3 を sibling-guard test で是正)→security(盲検2次 security agent=approve・material finding ゼロ・update-task.sh injection 不能を一次監査)→ship→docs を完走（deploy は M で size-exempt）。**実装（code 3 ファイル）**: tests/test_profile_referential_integrity.py に skill→script 検査追加（_skill_script_edges 抽出・_shipped_scripts_any・_shipped_skill_docs[全.md]・allow-list+rot・helper 整合・sibling-guard・6 単体）／templates/profiles/{full,standard}.json の required に update-task.sh／README standard 件数 20→21。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢(approve_with_notes)／qa🟢(drill auditable SKIP＋手動 mutation 4/4＋full suite green)／security🟡ack(deps 新規ゼロ)。**検証**: full suite green・contract PASS・test file 23 passed。LEARNINGS 2 件追記（conf8 resolve_source install 実体／conf7 B1 docstring 衝突 skip）。TO-CLIENT/MANUAL/RUNBOOK/UAT は内部 framework iteration で N/A。commit d7192d0・push 済 origin/main=d7192d0（yuuya-miyagaki）・dev_ready_for_client approved＝**iteration 49 完全クローズ**。"
  - date: "2026-06-26"
    mode: Dev
    phase: "docs"
    note: "iteration 48＝(c) 配布 self-containment（profile 参照整合性チェック＋JNY-07 実修正・framework・M・v1.14.0 据置）work 完了。/clear→/recover→rollover（iter45 剪定・external_evidence 最古アーカイブ）→ brainstorm(grill-premise で配布テーマの YAGNI 緊張を精査し、self-containment の 2 穴を**実証**＝D5: status_doctor→check_framework_contract 未同梱で version-drift 警告が full install で inert／JNY-07: check_status→_artifact_template_map 未同梱で client-gate テンプレヒントが空 degrade)→plan→grill-plan(致命3: F1 手動 KNOWN_EXTRA_EDGES→ast 自動検出／F2 negative-control 純関数／F3 install 実証 assertion を反映)→implement(TDD・RED-first)→grill-code(🟡2＋🟢1 反映: README no-op 判明で計画 reconcile／検出境界明記／allow-list rot 検知追加)→review(盲検2次 reviewer-maintainability=approve_with_notes・docstring 過検出を bare-expr 除外で解消＋境界テスト追加)→qa(B1 ドリル本物・3 mutant 全 caught)→security(盲検2次 security agent=approve・Low2 件 residual)→ship→docs を完走（deploy は M で size-exempt）。**実装（code 3 ファイル）**: 新規 tests/test_profile_referential_integrity.py（各 profile で shipped .py の依存辺＝ast static import＋文字列定数 sibling scan〔bare-expr/docstring 除外〕を自動抽出し『同梱 ∨ 理由付き INTENTIONAL_UNSHIPPED』を検査・`_violations` 純関数＋rot 検知＝13 テスト）／templates/profiles/full.json に scripts/_artifact_template_map.py 同梱（JNY-07 実修正・full のみ）／tests/test_profile_checker_parity.py に install e2e（full install→client-gate deny にテンプレパス出力を assert）。allow-list: minimal/standard=_artifact_template_map（Dev-lean・Client 経路なし）・minimal=build-judge-card/run-test-strength-drill（judge toolchain 非同梱）・full=check_framework_contract（maintainer 専用・D5 field no-op は by-design）。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢(approve_with_notes)／qa🟢(B1 3 mutant caught)／security🟡ack(deps unverified=新規依存ゼロ advisory)。**検証**: full suite 1134 passed/1 skip（record green）・contract PASS・scaffold smoke PASS・full install e2e でテンプレヒント実出力。**2 穴の RED→GREEN を full.json から map 除去で二重実測**。TO-CLIENT/MANUAL/RUNBOOK/UAT は内部 framework iteration（client 製品 user/operator/ACCEPTANCE なし）で N/A。LEARNINGS 3 件追記（conf8 配布 self-containment 横断検査／conf7 サブエージェント evidence-log 汚染／conf7 post-qa 編集回避）。**未コミット・未 push**＝ユーザーの dev_ready_for_client 承認＋push 承認待ち。"
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
