---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: M
task_size_rationale: "iteration 48（framework・配布 self-containment）= **M**（2-5 files）。slice 確定: profile 参照整合性チェック。変更想定 3 ファイル＝(1) tests/test_profile_referential_integrity.py 新規（横断検査＋INTENTIONAL_UNSHIPPED allow-list）・(2) templates/profiles/full.json に scripts/_artifact_template_map.py 追加（JNY-07 実修正）・(3) README.md の full profile 件数同期（test_readme_profile_counts.py）。M 根拠: 2-5 files・security-class（配布 moat/診断の整合性）・必須ゲート review+qa+security（deploy は M で size-exempt）。grill-premise で 2 穴を実証（D5 inert / JNY-07 hints inert）＝投機でなく一次情報。**やらない**: command→script/skill 散文参照の網羅・downgrade ガード・orphan 削除・contract ツールチェーンの install 同梱。"
iteration: 48
ui_surface: false
last_updated: "2026-06-27T00:05:00Z"
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
  requirements:
    - docs/requirements/iter48-distribution-self-containment.md
  plan: docs/plans/2026-06-26-distribution-self-containment-implementation-plan.md
  spec: docs/specs/2026-06-26-distribution-self-containment-design.md
  review: docs/qa-reports/iter48-review.md
  qa: docs/qa-reports/iter48-qa.md
  security: docs/qa-reports/iter48-security.md
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
next_action: "**【iteration 48＝(c) 配布 self-containment 完全クローズ（framework・M・v1.14.0 据置・push 済 origin/main=f8c11ba・dev_ready_for_client approved・/clear 後 /recover 用アンカー・2026-06-27）】** ◆**push 済**: origin/main=f8c11ba（yuuya-miyagaki／active gh が tigereye だと 403／`gh auth switch --user yuuya-miyagaki`）。本アンカーはその後の小コミットで更新。◆**全ゲート green＋iteration クローズ**: brainstorm✅plan✅review✅(approve_with_notes)qa✅(B1 3 mutant caught)security✅(🟡ack deps)dev_ready_for_client✅・deploy は M で size-exempt。◆**iter48 成果（code 3）**: tests/test_profile_referential_integrity.py 新規（profile 横断の参照整合性＝shipped .py の依存辺を ast 自動抽出〔static import＋文字列定数 sibling scan・docstring 除外〕し『同梱∨理由付き INTENTIONAL_UNSHIPPED』を検査・13 テスト・rot 検知付き）／templates/profiles/full.json に scripts/_artifact_template_map.py 同梱（JNY-07 実修正）／tests/test_profile_checker_parity.py に full install e2e。**D5（version-drift inert）と JNY-07（テンプレヒント空）の 2 穴を full install で実証→ map 除去で整合性＋e2e 両 RED 実測→修正で GREEN**。allow-list: minimal/standard=_artifact_template_map・minimal=judge toolchain・full=check_framework_contract（D5 maintainer 専用 by-design）。LEARNINGS 3 件（conf8 配布 self-containment 横断検査／conf7 サブエージェント evidence-log 汚染／conf7 post-qa 編集回避）。◆**次（iter49 候補・未確定）**: (a) security 2次の Low＝allow-list に security-class sign-off コメント（post-qa 編集回避で今回見送り・最小スライス）／(b) 配布 self-containment の射程拡大（command(.md)→script・skill→asset 参照の整合性検査＝本スライスの仕組みを拡張）／(c) v0.13.0 残項目〔Phase 0a 着手 GO 済〕／(d) future-proof 再アーキ。**まず /clear→/recover でコンテキスト刷新**（本セッションは iter48 フル完走で長大）→ rollover（iter46 剪定・iteration=49・dev ゲート reset・requirements は新テーマで再定義 or 暫定[]）。◆**やらない**: command→script を本スライスに後付けしない（別スライス）／downgrade ガード／orphan 削除（現アーキで害が投機的）／contract ツールチェーンの install 同梱。◆**罠（iter41-48 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-26"
    mode: Dev
    phase: "docs"
    note: "iteration 48＝(c) 配布 self-containment（profile 参照整合性チェック＋JNY-07 実修正・framework・M・v1.14.0 据置）work 完了。/clear→/recover→rollover（iter45 剪定・external_evidence 最古アーカイブ）→ brainstorm(grill-premise で配布テーマの YAGNI 緊張を精査し、self-containment の 2 穴を**実証**＝D5: status_doctor→check_framework_contract 未同梱で version-drift 警告が full install で inert／JNY-07: check_status→_artifact_template_map 未同梱で client-gate テンプレヒントが空 degrade)→plan→grill-plan(致命3: F1 手動 KNOWN_EXTRA_EDGES→ast 自動検出／F2 negative-control 純関数／F3 install 実証 assertion を反映)→implement(TDD・RED-first)→grill-code(🟡2＋🟢1 反映: README no-op 判明で計画 reconcile／検出境界明記／allow-list rot 検知追加)→review(盲検2次 reviewer-maintainability=approve_with_notes・docstring 過検出を bare-expr 除外で解消＋境界テスト追加)→qa(B1 ドリル本物・3 mutant 全 caught)→security(盲検2次 security agent=approve・Low2 件 residual)→ship→docs を完走（deploy は M で size-exempt）。**実装（code 3 ファイル）**: 新規 tests/test_profile_referential_integrity.py（各 profile で shipped .py の依存辺＝ast static import＋文字列定数 sibling scan〔bare-expr/docstring 除外〕を自動抽出し『同梱 ∨ 理由付き INTENTIONAL_UNSHIPPED』を検査・`_violations` 純関数＋rot 検知＝13 テスト）／templates/profiles/full.json に scripts/_artifact_template_map.py 同梱（JNY-07 実修正・full のみ）／tests/test_profile_checker_parity.py に install e2e（full install→client-gate deny にテンプレパス出力を assert）。allow-list: minimal/standard=_artifact_template_map（Dev-lean・Client 経路なし）・minimal=build-judge-card/run-test-strength-drill（judge toolchain 非同梱）・full=check_framework_contract（maintainer 専用・D5 field no-op は by-design）。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢(approve_with_notes)／qa🟢(B1 3 mutant caught)／security🟡ack(deps unverified=新規依存ゼロ advisory)。**検証**: full suite 1134 passed/1 skip（record green）・contract PASS・scaffold smoke PASS・full install e2e でテンプレヒント実出力。**2 穴の RED→GREEN を full.json から map 除去で二重実測**。TO-CLIENT/MANUAL/RUNBOOK/UAT は内部 framework iteration（client 製品 user/operator/ACCEPTANCE なし）で N/A。LEARNINGS 3 件追記（conf8 配布 self-containment 横断検査／conf7 サブエージェント evidence-log 汚染／conf7 post-qa 編集回避）。**未コミット・未 push**＝ユーザーの dev_ready_for_client 承認＋push 承認待ち。"
  - date: "2026-06-26"
    mode: Dev
    phase: "ship"
    note: "iteration 47（full-review backlog 最後の C1 をクローズし backlog を triaged-complete に・framework・**S**・docs-only・v1.14.0 据置）完了。rollover（iter44 剪定・push 済 origin/main=6e058a9）→ brainstorm(grill-premise で C1=forward-looking/現状到達不能と実証＝複数パス built-in tool が無く first-path-only 到達不能・matcher は現行 write-tool 全カバー＋stale_keys 機構あり)→implement(docs-only)→grill-code(SF-006 が I3=OPEN のまま stale＝triaged-complete と矛盾→ADDRESSED[I3=iter43] へ修正)→review(盲検2次 reviewer-maintainability=approve_with_notes・3 Minor〔節見出しに forward-looking 追加／stale_keys『カバー』→advisory 明記／line-ref 46-50〕全反映)→ship を完走（**size S＝SIZE_ALLOWED_PHASES に plan/qa/security/deploy/docs を含まず・terminal は ship**）。**成果物（docs 2 ファイル）**: security-followups.md に SF-009（C1=forward-looking）＋`## 調査済み・非該当` 見出しに forward-looking 追加＋`full-review backlog triaged-complete` 節＋SF-006 を ADDRESSED 化／full-review backlog 行＋C1 finding pointer。**ゲート（S＝review のみ必須）**: review🟢(approve_with_notes・tests=unverified は docs-only/S で ack＝qa 免除)。**検証**: status_doctor PASS・contract PASS（phase=docs は S で contract FAIL と判明→ship に留める）。**full-review 2026-06-24 backlog 全 16 項目 triaged-complete・残実コード修正タスク=ゼロ**。LEARNINGS: backlog 再評価=by-design 教訓を conf8 へ昇格（C1=3 件目）＋size-S terminal=ship の罠を追記。commit 7634fe3・push 済 origin/main=7634fe3（yuuya-miyagaki）・dev_ready_for_client approved＝**iteration 47 完全クローズ**。次は **iter48=(c) 配布強化（確定）**＝ユーザー『推奨で進めて』で委任。まず /clear→/recover でコンテキスト刷新。"
  - date: "2026-06-26"
    mode: Dev
    phase: "docs"
    note: "iteration 46（full-review backlog C4・G4 を検証済み verdict として docs/security-followups.md に明文化しクローズ・framework・M・docs-only・v1.14.0 据置）完了。/clear→/recover→rollover（iter43 剪定・push 済 origin/main=8a8fbbe）→ brainstorm(grill-premise＋/tmp probe で C4=NOT-A-VULN 実証→当初候補 C4 を security 課題として取り下げ・iter46 を『C4/G4 を境界明文化してクローズ』に再定義)→plan(grill-plan 致命3 反映: NOT-A-VULN 節を CLOSED と分離／C1 スコープ明示／最小再構築キット必須／README YAGNI skip)→implement(docs-only)→grill-code(SF-007 の clean-token enforcement 帰属精緻化・SF-008 に既存 Check 3 advisory を明記)→review(盲検2次 reviewer-maintainability=approve_with_notes・M1/M2/M4 反映・M3 は accuracy 優先で不採用)→qa(full suite 1120 passed/1 skip 実走・record green／B1 は docs-only で auditable SKIP)→security(盲検2次 security agent が一次資料で独立確認＝SF-007/008 とも AGREE・approve_with_notes／canonical 節の determinism 過大主張を初回指摘→Edit/Write path=決定論・Bash moat=閾値[SF-004] に切り分けて修正／Minor2件 反映)→ship→docs を完走（deploy は M で size-exempt）。**成果物（docs 4 ファイル）**: security-followups.md に `## 脅威モデル（canonical）`節＋`## 調査済み・非該当（NOT-A-VULN/by-design）`節（SF-007=C4・SF-008=G4）／full-review backlog 行＋C4/G4 finding に closure pointer／LEARNINGS 4件（C4 tech conf8＋record-test-result 実行注意＋judge 1次2次 verdict＋backlog 再評価=by-design 帰結 process）。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢(approve_with_notes ack: docs-only tests-unverified)／qa🟢(tests green・B1 SKIP)／security🟡ack(deps unverified=新規依存ゼロ advisory)。**検証**: full suite 1120 passed/1 skip・status_doctor PASS・contract PASS・secrets 検出なし。TO-CLIENT/MANUAL/RUNBOOK/UAT は内部 docs iteration（client 製品 user/operator/ACCEPTANCE なし）で N/A。commit 済（20edbde）・push 済 origin/main=20edbde（yuuya-miyagaki）・dev_ready_for_client approved＝**iteration 46 完全クローズ**。"
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
