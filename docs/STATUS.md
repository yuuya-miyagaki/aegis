---
framework: aegis
framework_version: "1.5.0"
project_name: "Aegis"
mode: Dev
phase: review
task_type: framework
task_size: L
task_size_rationale: "確定（brainstorm Step D）: E1 activity verification（進化レビュー §5 E1・§6 ロードマップ 5 番）。観測一本化＝PostToolUse/PostToolUseFailure(Bash)→evidence-log.jsonl 記録、judge card テスト行を観測ログ読みに置換、fingerprint.sh 単一所有、record-test-result.py 手動フォールバック化。hooks×4・lib×3・scripts×2・setup/smoke/templates/gitignore/docs 横断 14+ ファイル＝L。"
iteration: 18
ui_surface: false
last_updated: "2026-06-10T17:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/evolution-review-2026-06-10.md
  plan: docs/plans/2026-06-10-e1-activity-verification-implementation-plan.md
  spec: docs/specs/2026-06-10-e1-activity-verification-design.md
  review: docs/qa-reports/v150-review.md
  qa: docs/qa-reports/v150-qa.md
  security: docs/qa-reports/v150-security.md
  deploy: docs/qa-reports/v150-deploy-checklist.md
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
next_action: "E1 実装 13 タスク完走＋grill-code（🔴1/🟡4 同セッション修正・436 tests/contract/drift/smoke 全 PASS）。次: review→qa→security→deploy をゲート承認（テスト行は record-test-result.py 手動記録）→ v1.5.0 タグ。origin push は別途ユーザー判断。grill 🟢残余（false-RED・ホットパスコスト等）は v150-security.md 記録済み・別バッチ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-07"
    mode: Dev
    phase: "docs"
    note: "機能整合性監査（charter 2026-06-07）を実行。Layer 0-4 で7 finding 実証検出（P1×1/P2×4/P3×2）。**F6（P1）＝setup.sh が hooks/lib/emit.sh・patterns.sh を配布せず install 先で全 hook が source 時に死＝決定論 moat 全死**を copy_hooks 全 lib コピーで修復。F3 retro graceful 配送／F2 judge 配布／F4 status_doctor 配布／F1 contract hook4件追跡／F5・F7 polish。各 TDD＋2段グリル。install 経路を scaffold smoke の hook 実発火で契約化（静的検査の死角を恒久封鎖）。再検証で Layer 0 全 green＋ライブ install の moat 実発火を実証。v1.3.2 patch で締め（298 tests・contract・drift・tier2・--strict 全 PASS・tag v1.3.2）。"
  - date: "2026-06-10"
    mode: Dev
    phase: "deploy"
    note: "進化レビュー（哲学×Web比較×欠陥監査の3軸、docs/evolution-review-2026-06-10.md）で新規 P1×2/P2×6/P3×6 を検出し、P1-1（control-plane の transcript_path 衝突で install 先のほぼ全 Bash deny）・P1-2（check-gate glob の src/hooks/ 等衝突)を fix-forward。TDD 2ラウンド（RED9→GREEN、grill 指摘のバイパス形 RED11→GREEN）＋grill-code（条件付き GO→条件充足で GO）。バイパス 13 形は全 deny 維持（v133-security.md）。**B1 ドリルが framework 混在 diff に構造的適用不能（38 ハンク>25・STATUS 簿記ハンク捕獲不能）と判明→§11 スキップ宣言＋LEARNINGS 所見化**。全ゲート承認後 v1.3.3 patch で締め（332 tests・contract full/standard・drift・smoke 全 PASS・README 移行節・tag v1.3.3）。"
  - date: "2026-06-10"
    mode: Dev
    phase: "deploy"
    note: "iteration 17（v1.4.0 fix batch）: T0〜T16 を TDD で完走（frontmatter.sh 新設、failure policy 表＋実発火突合テスト、check-task-completed closed 化、check-secrets 鍵種追加、WRITE_INDICATORS 語境界化、pre-compact env 改名、deploy gate RC 契約＋size-skip ask 化、update-gate mkdir ロック＋単一パス書込、contract lib 追跡＋版数同期、B1 ドリル docs/** 除外、standard Bash ガード4種、hooks $CLAUDE_PROJECT_DIR 化、K-2、v1.4.0 版数）。grill-code=マージ可（Critical 0）、🟡2件（実リポジトリミラーテスト不在／CLAUDE_PROJECT_DIR 未設定で moat silent fail-open）を同セッション修正。389 tests OK・contract・drift・smoke・--strict 全 PASS。証跡 v140-review/qa/security/deploy-checklist.md。review→qa→security→deploy を tri-state judge --ack で承認（current_refs 無傷＝update-gate 単一パス書込の実証、LEARNINGS の旧バグ記録を解消注記）。v1.4.0 minor で締め・tag v1.4.0。origin push は別途ユーザー判断。"
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
