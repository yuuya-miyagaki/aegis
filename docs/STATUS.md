---
framework: aegis
framework_version: "1.10.0"
project_name: "Aegis"
mode: Dev
phase: qa
task_type: framework
task_size: L
task_size_rationale: "暫定（brainstorm/plan は dogfood セッションで完了済み・本リポで承認取得予定）: ドッグフード由来 改善（OBS-001〜022）。Batch1=control-plane フック精度+git baseline 6 タスク／Batch2=skill/契約/配布整合 5／Batch3=Client 書込み 2＋横断 X.1/X.2。hooks/scripts/skills/tests 多数で 6+ ファイル＝L。plan: docs/plans/2026-06-15-dogfood-driven-improvements-plan.md。"
iteration: 31
ui_surface: false
last_updated: "2026-06-16T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/full-review-2026-06-13-context-futureproof.md
  plan: docs/plans/2026-06-15-dogfood-driven-improvements-plan.md
  spec: docs/specs/2026-06-16-dogfood-driven-improvements-spec-delta.md
  review: docs/qa-reports/iter31-batch1-review.md
  qa: docs/qa-reports/iter31-batch1-qa.md
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
next_action: "iteration 31（ドッグフード由来 改善）implement 進行中。**Batch1（配布ブロッカー＝control-plane フック精度＋git baseline）6 タスク完了・6 コミット（9177854 起動／52dff43 1.1／864786f 1.2／801bbaf 1.3／c4db78d 1.4／6895cbf 1.5／6d1b938 1.6）。** 各タスク Step0→TDD→commit、全 moat 回帰（var_expansion・patterns_parity・secrets・REDTEAM 18/18＋5/5）緑、フルスイート 821 passed/1 skip、contract 全 profile・drift・mirror・scaffold smoke 全 PASS。TDD が 2 つの穴を着手前に捕捉（1.5 パイプ最終セグメント fail-open＝`|| [ -n ]`／1.6 空マスク＝`local s=$1 n=${#s}` の同一行展開、＋クォート write-util 宛先穴をステップ(c)で封鎖）。**判断ポイント: (A) Batch1 を先に review→qa→security ゲート（1.5/1.6 の盲検2次をフレッシュなうちに）か (B) Batch2（skill/契約/配布整合5）+Batch3（Client書込み2）+X.1/X.2 を実装してから一括ゲートか — ユーザー確認待ち。** 残すべき勝ち OBS-010/014/016/019/021/022 維持。ハードゲート（review/qa/security/deploy）と push は明示承認まで禁止。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-14"
    mode: Dev
    phase: "deploy"
    note: "iteration 30（進化ロードマップ P3: skill 挙動圧力テスト・v1.10.0）実装完了: 比較レビュー由来の進化ロードマップ P3。Aegis の skill 検証が静的（reachability/frontmatter）のみで『skill 指示文が実際に遵守されるか』の空白を、hook で強制できない判断系 skill に限定して埋める（hook 強制済みの hard gate はテストせず＝重複回避）。2 層: 層1＝決定論 skill behavior contract。新規 scripts/skill_behavior_manifest.py（判断系 7 skill＝aegis-brainstorm/tdd/bug-diagnosis/aegis-review-gate/aegis-security-gate/qa-verification/subagent-dev → load-bearing 不変条件トークン 14・platform_manifest と同じ単一オーナー／root 専用／非ミラー流儀）＋check_reference_drift.check_skill_behavior_contract（sibling import・ALL_CHECKS 14→15・scripts/skill_behavior_manifest.py 存在ガードで installed/example は inert）＝skill 編集で核心命令が消えると FAIL（リグレッションガード）。layer1 は『accidental 削除を捕まえる ratchet（manifest 同時編集で回避可）』と限界を docstring に明記。層2＝extensions/skill-pressure-drill/（CONVENTIONS Rule1/2/5 準拠の手動 opt-in addon・contract 非登録・新 core skill 作らず churn ゼロ）に実 subagent 用 adversarial drill 足場（README/WORKFLOW/REPORT テンプレ/シード scenario×2）＋tests/test_skill_drill_format.py（シナリオ/テンプレ形式のみ決定論検査＝エージェント非実行で flake ゼロ）。版 1.9.0→1.10.0（contract 定数/template/example/live STATUS 統一）。arch-overview の drift-check 数を 14→15 同期（test_arch_overview_currency が機械突合）。file-count summary は既存 stale・未テスト・基準曖昧のため意図的に不変更。フロー全工程: brainstorm→設計書→writing-plans→grill-plan→TDD（RED 実証: 実装前 6 テスト FAIL）→grill-code。grill-plan 致命4（①14 トークンを grep -F 実在検証＋空白入り `2 段階レビュー`→`段階レビュー` に安定化②ALL_CHECKS 件数依存テスト洗い出し→arch-overview 15 同期③qa ドリル具体化④brainstorm/plan 含む全ゲート承認網羅）を着手前反映。grill-code 🔴0（install 配布経路 F6 死角を実査＝profile は check_status.py のみ配布で drift/manifest は installed 非配布＝import crash 不成立を確認）・🟡1（中核リグレッションテストを全 skill/全トークン網羅に強化＝bb40ed2）fix-forward・🟢3 許容。test-strength.drill は framework 混在 diff＋committed コードで B1 適用不能のため skip 宣言（代替＝test_missing_token_fails_for_every_skill_and_token が contract の守る回帰を全 7 skill・全 14 トークンで mutation 同等実証）。full suite 779 passed/1 skip（773→779＝新規 11・既知 flake 非発火）・contract 全 profile・drift 15・Tier2 scaffold smoke・Tier3 eval_scenario・make example 差分ゼロ＝全 PASS。コミット 6575d75（層1）/caf4e0e（層2）/848ae55（版）/bb40ed2（grill-code）＋close-out。**残: ユーザー確認の上 push（自動 push しない）。進化ロードマップ次は P4（実ブラウザ QA・someday）/P5（positioning・配布時）。**"
  - date: "2026-06-14"
    mode: Dev
    phase: "deploy"
    note: "iteration 29（P3/M2: 過程 docs アーカイブ・docs-only・版据え置き v1.8.0）実装完了: 第7回全力レビュー §2 P3『過程 docs の archive 化・空 scaffold 削除』＝最後の未消化項目。root docs/ の過程成果物を docs/archive/{plans,qa-reports,reviews} へ git mv（履歴保全）: plans 履歴 61・qa-reports 履歴 55・top-level 審査履歴 16＝計 132 移動＋空 .gitkeep dir 3（handover/requirements/decisions）削除。確立した不変条件は『root=運用ドキュ＋現イテレーションの active ref／archive=履歴』。設計の核は breakage ゼロ: current_refs が指す被参照ファイル（v162 qa-reports 4＋requirements=full-review-2026-06-13-context-futureproof）を一切動かさない＝契約（every declared ref exists）を編集せず満たす。plan/spec のみ P3 docs へ通常ローテ（P3 docs は元から root＝無移動）。test-strength.drill は run-test-strength-drill.py/test が参照する LIVE artifact のため *.md glob＋case 二重除外で root 温存。keep-list 8 load-bearing（STATUS/LEARNINGS/MIGRATION-FROM-v7/architecture-overview/evidence-archive/hook-failure-policy/perf-baseline/context-futureproof）root 維持。参照監査で『移動で壊れるのは root current_refs 6＋example 4 のみ』を事前確定、README/arch-overview に specific link 無し・placeholder 検査は example のみ走査・drill テストは tmp 使用を実証。grill-plan 要検討4件（①test_hook_output_schema の stale コメント2行を docs/archive パスへ更新②メモリ更新を実参照6件に是正③make example の git status 期待明確化④session_history iter26 削除明示）を着手前反映。各カテゴリ移動ごとに contract/drift 緑を確認、最終 full suite 750 passed/1 skip（既知の順序依存 flake test_python3_absent のみ＝Task1 ベースラインと同一＝新規回帰ゼロ）/ contract 全 profile / drift / make example 差分ゼロ（archive は root のみ＝example 非波及）/ PoC 18+5 全 PASS。MEMORY.md の history 参照 6 件（audit-charter/report-2026-06-06・evolution-review-2026-06-10・functional-integrity-audit-charter/report-2026-06-07・behavioral-review-report-2026-06-12）を docs/archive/reviews へ更新（context-futureproof は root 据え置き）。版は据え置き（コード挙動ゼロ変更＝SemVer 的に版を消費しない）。**これで第7回全力レビュー §2 のバックログを全消化＝完済。次タスク未定。**"
  - date: "2026-06-14"
    mode: Dev
    phase: "deploy"
    note: "iteration 28（v1.8.0 P2: volatile-truth マニフェスト）実装完了: 第7回全力レビュー §2 P2。プラットフォーム結合値（model id/effort・hook event 名・tool 名・hook 出力 schema 検証日）を新規 scripts/platform_manifest.py に隔離し『追従トレッドミルの税』を1箇所へ集約。M1 で実証した『生成と検証が同一マニフェストを import＝原理的に乖離不能』パターンの横展開。設計の核は2層分離: 機械強制できる内部整合（散在リテラルを import/drift で束ねる）＋機械強制できない現実整合（人手の検証日 PLATFORM_VERIFIED＋staleness advisory）。これで過去セカンドオピニオン R1/J-1 が警告した『沈黙する第3 declarative ミラー』を回避（実 import 消費者あり・現実検証は人手と明示）。スコープ: model（強制 import）/event（drift FAIL）/tool（registry WARN）/schema（検証日のみ＝emit.sh のフィールド名は移さず pure-bash 単一ソースを不可侵）。check_framework_contract が ALLOWED/FORBIDDEN/EFFORT/OPUS_ONLY を import 消費しリテラル置換＋新規 check_model_policy_manifest_consistency が MODEL_EFFORT_POLICY（aegis 設計）を許容集合に照合（platform 真実 vs aegis 設計の分離）。check_reference_drift が自己 bootstrap 付き import で check_platform_manifest（template event∈KNOWN_HOOK_EVENTS=FAIL／matcher token∈KNOWN_TOOL_NAMES=WARN／TOOL_MATCHING_EVENTS 限定で SessionStart の startup|resume を tool 誤検知しない）と check_platform_staleness（検証日超過=WARN・platform_manifest.py を持つ framework root のみ発火で二重発火防止）を追加（ALL_CHECKS 12→14・architecture-overview 同期）。CLAUDE.md Model Policy に値出典の一本化を明記（語数 599/650）。非ミラー checker のみが import＝新ミラー面ゼロを make example で実証。grill-plan が致命2件（①importlib ローダ test_skill_reachability 用に check_reference_drift へ self-bootstrap sys.path.insert を追加＝単独実行 collection error を封鎖／②staleness を check_platform_staleness に関数分離し template 検査を決定論化＝壁時計依存テストの時限爆弾を排除）を指摘→着手前反映。grill-code は 🔴ゼロ・🟡1（malformed template の null/非dict matcher で crash→報告に倒す＋sys.path 冪等化）を fix-forward。版数4箇所（contract 定数/template STATUS/example STATUS/本体 STATUS）を 1.8.0 統一。750 passed/1 skip（734→752・新規18）/ contract 全 profile / drift / v162 18 PoC / v163 5 PoC 全 PASS。既知の順序依存 flake test_python3_absent_advisory_hooks_do_not_crash（post-status-audit が実 docs/STATUS.md と .gate-snapshot の gate 差を tamper 検知＝共有状態のテスト分離問題）は単独実行で緑・本変更とは無関係（baseline でも同失敗）。残 backlog: P3 過程 docs archive 化・空 scaffold 削除（第7回レビュー最後の未消化項目）。"
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
