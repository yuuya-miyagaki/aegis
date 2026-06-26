---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: ship
task_type: framework
task_size: S
task_size_rationale: "iteration 47（framework・**S**・docs-only）= full-review backlog 最後の C1 をクローズし backlog を triaged-complete に。C1=forward-looking/現状到達不能（grill-premise で実証＝複数パスを渡す built-in write-tool が無く first-path-only[extract-input.sh:20] は到達不能・MultiEdit 廃止／matcher は現行 write-tool 全カバー＋`stale_keys()` 再検証機構あり）。成果物: security-followups.md に SF-009＋triaged-complete 節＋SF-006 を ADDRESSED 化、full-review backlog 行＋C1 finding pointer（2 docs ファイル）。size=S 根拠: zero code/behavior/risk の forward-looking 整理（C4/G4=M より低 stakes）＝SIZE_ALLOWED_PHASES[S]={brainstorm,implement,review,ship}・必須ゲートは review のみ・terminal は ship（docs は S で contract FAIL）。**やらない**: 存在しない複数パス入力への防御コード／matcher 動的列挙（stale_keys と重複）／新規ファイル。"
iteration: 47
ui_surface: false
last_updated: "2026-06-26T01:30:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: pending
  review: approved
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: approved
current_refs:
  requirements:
    - docs/full-review-2026-06-24-hooks-gates-distribution.md
  plan: null
  spec: docs/specs/2026-06-26-iter47-c1-backlog-close-design.md
  review: docs/qa-reports/iter47-review.md
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
  - type: "second-opinion-v0122-r6-r9"
    scope: "v0.12.2 実装後 4 ラウンドレビュー"
    findings: "Round 6 (P1×2, P2×1: pre-compact exit 2 / minimal-project / test rc), Round 7 (P1×1, P3×1: git add 漏れ / テスト件数表記), Round 8 (P2×1, P3×1: stale last_updated / grep 自己マッチ), Round 9 (P3×2: コメント不整合)"
    resolution: "9件全反映。tier 1/2 PASS、134 tests PASS、本体と minimal-project 完全同期確認済み。"
next_action: "**【iteration 47 完全クローズ（full-review 最後の C1 をクローズ＝SF-009 forward-looking＋backlog triaged-complete・framework・S・docs-only・v1.14.0 据置／review🟢・dev_ready_for_client approved・commit 7634fe3・push 済 origin/main=7634fe3）。次は iteration 48＝実需テーマ選択（ユーザー相談待ち）・/clear 後 /recover 用アンカー・2026-06-26】** ◆**push 済**: origin/main=7634fe3（yuuya-miyagaki／active gh が tigereye だと 403／`gh auth switch --user yuuya-miyagaki`）。◆**iter47 成果**: SF-009（C1=forward-looking）＋**full-review 2026-06-24 backlog 全 16 項目 triaged-complete＝残実コード修正タスク=ゼロ**。◆**iter48 はテーマ選択から（backlog 枯渇）**: 「残っているから潰す」フェーズ終了。候補 (a) 保留中 v0.13.0 項目（外部レビューで Phase 0a 着手 GO） (b) future-proof 再アーキ（Opus 4.8 耐性・Foundation 続き） (c) 配布(standard profile)強化。**推し=(c) 配布強化 or (a) v0.13.0**。テーマ確定後に rollover（dev ゲート reset・iter48・phase=brainstorm・current_refs null〔requirements 保持〕・session_history 最古剪定＝iter45 を落とす・task_type/size は update-task.sh）。**やらない**: check-control-plane 再設計・curl exfil regex ブロック・gate_value strict 化（SF-007）・存在しない複数パス入力への防御（SF-009）。◆**罠（iter41-47 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-26"
    mode: Dev
    phase: "ship"
    note: "iteration 47（full-review backlog 最後の C1 をクローズし backlog を triaged-complete に・framework・**S**・docs-only・v1.14.0 据置）完了。rollover（iter44 剪定・push 済 origin/main=6e058a9）→ brainstorm(grill-premise で C1=forward-looking/現状到達不能と実証＝複数パス built-in tool が無く first-path-only 到達不能・matcher は現行 write-tool 全カバー＋stale_keys 機構あり)→implement(docs-only)→grill-code(SF-006 が I3=OPEN のまま stale＝triaged-complete と矛盾→ADDRESSED[I3=iter43] へ修正)→review(盲検2次 reviewer-maintainability=approve_with_notes・3 Minor〔節見出しに forward-looking 追加／stale_keys『カバー』→advisory 明記／line-ref 46-50〕全反映)→ship を完走（**size S＝SIZE_ALLOWED_PHASES に plan/qa/security/deploy/docs を含まず・terminal は ship**）。**成果物（docs 2 ファイル）**: security-followups.md に SF-009（C1=forward-looking）＋`## 調査済み・非該当` 見出しに forward-looking 追加＋`full-review backlog triaged-complete` 節＋SF-006 を ADDRESSED 化／full-review backlog 行＋C1 finding pointer。**ゲート（S＝review のみ必須）**: review🟢(approve_with_notes・tests=unverified は docs-only/S で ack＝qa 免除)。**検証**: status_doctor PASS・contract PASS（phase=docs は S で contract FAIL と判明→ship に留める）。**full-review 2026-06-24 backlog 全 16 項目 triaged-complete・残実コード修正タスク=ゼロ**。LEARNINGS: backlog 再評価=by-design 教訓を conf8 へ昇格（C1=3 件目）＋size-S terminal=ship の罠を追記。commit 7634fe3・push 済 origin/main=7634fe3（yuuya-miyagaki）・dev_ready_for_client approved＝**iteration 47 完全クローズ**。次は実需テーマ選択（v0.13.0/再アーキ/配布強化）＝ユーザー相談待ち。"
  - date: "2026-06-26"
    mode: Dev
    phase: "docs"
    note: "iteration 46（full-review backlog C4・G4 を検証済み verdict として docs/security-followups.md に明文化しクローズ・framework・M・docs-only・v1.14.0 据置）完了。/clear→/recover→rollover（iter43 剪定・push 済 origin/main=8a8fbbe）→ brainstorm(grill-premise＋/tmp probe で C4=NOT-A-VULN 実証→当初候補 C4 を security 課題として取り下げ・iter46 を『C4/G4 を境界明文化してクローズ』に再定義)→plan(grill-plan 致命3 反映: NOT-A-VULN 節を CLOSED と分離／C1 スコープ明示／最小再構築キット必須／README YAGNI skip)→implement(docs-only)→grill-code(SF-007 の clean-token enforcement 帰属精緻化・SF-008 に既存 Check 3 advisory を明記)→review(盲検2次 reviewer-maintainability=approve_with_notes・M1/M2/M4 反映・M3 は accuracy 優先で不採用)→qa(full suite 1120 passed/1 skip 実走・record green／B1 は docs-only で auditable SKIP)→security(盲検2次 security agent が一次資料で独立確認＝SF-007/008 とも AGREE・approve_with_notes／canonical 節の determinism 過大主張を初回指摘→Edit/Write path=決定論・Bash moat=閾値[SF-004] に切り分けて修正／Minor2件 反映)→ship→docs を完走（deploy は M で size-exempt）。**成果物（docs 4 ファイル）**: security-followups.md に `## 脅威モデル（canonical）`節＋`## 調査済み・非該当（NOT-A-VULN/by-design）`節（SF-007=C4・SF-008=G4）／full-review backlog 行＋C4/G4 finding に closure pointer／LEARNINGS 4件（C4 tech conf8＋record-test-result 実行注意＋judge 1次2次 verdict＋backlog 再評価=by-design 帰結 process）。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢(approve_with_notes ack: docs-only tests-unverified)／qa🟢(tests green・B1 SKIP)／security🟡ack(deps unverified=新規依存ゼロ advisory)。**検証**: full suite 1120 passed/1 skip・status_doctor PASS・contract PASS・secrets 検出なし。TO-CLIENT/MANUAL/RUNBOOK/UAT は内部 docs iteration（client 製品 user/operator/ACCEPTANCE なし）で N/A。commit 済（20edbde）・push 済 origin/main=20edbde（yuuya-miyagaki）・dev_ready_for_client approved＝**iteration 46 完全クローズ**。"
  - date: "2026-06-25"
    mode: Dev
    phase: "ship"
    note: "iteration 45（full-review C2+C3＝bin/setup.sh の引数パーサ両形式対応＋version heredoc argv 渡し・framework・M・v1.14.0 据置）完了。/clear→/recover→rollover（iter45・dev ゲート全 pending・push 済 origin/main=77383ff）→ brainstorm(grill-premise で C3 を機能影響ゼロ cleanup と再格付け・grep フォールバックが実値 1.14.0 を返すこと等を実測)→plan(grill-plan 致命2+要検討2 反映)→implement(TDD・RED 5 fail 実測)→grill-code(--force 無限ループ回帰テスト等3件追加)→review(盲検2次 testing+maintainability)→qa(本物 B1 drill 4 mutant PASS)→security(盲検2次 approve)→ship を完走（deploy は M で size-exempt）。**実装（1 file＋test）**: C2＝`for arg` を `while+shift` に置換し --profile/--target に =val/空白 両形式アーム＋`[ $# -ge 2 ]` 明示 guard（shift 終了コード非依存＝bash 版横断で決定的メッセージ）。C3＝version heredoc を argv 渡し（sys.argv[1]）に変え dead first path 解消（grep フォールバック存置）。新規 tests/test_setup_arg_version.py（13 ケース・RED-first）。**review 反映**: testing F1=positive-control の false-green→grep+sed 単独実行で誤値 0.0.0-grepwrong を返すことを self-validate／maintainability M2=shift 版依存→明示 guard 化／F2-F5=value-mistake/明示空値/help-hint テスト追加。**qa B1 drill（本物 PASS）**: 4 mutant（guard -ge2→-ge1／help echo text／unknown-arg echo text／argv→/dev/null）全 caught。純コメントハンク（fallback 説明）は冗長除去で coverable 化＝skip 回避。**ゲート（M＝review+qa+security 必須・deploy exempt）**: review🟢／qa🟢（B1 4 mutant caught）／security🟡ack（盲検 approve・finding ゼロ・deps 新規ゼロ advisory）。**検証**: full suite 1115 passed/1 skip（record・fp 一致）・bash -n OK・空白形式 smoke rc0 stamp1.14.0・git mode-flip なし。LEARNINGS 5件追記。push 未＝yuuya-miyagaki（gh auth switch）。"
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
